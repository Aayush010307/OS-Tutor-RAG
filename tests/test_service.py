"""Product upgrade tests: the answer-first tutor service with a scripted LLM (no Ollama, no index).

    python3 -m pytest tests -q
"""
import json

import pytest

from src.learner.model import LearnerModel
from src.tutor import service as svc
from src.tutor.controller import is_new_question
from src.tutor.llm import LLMError
from src.tutor.service import (INTENT_RULES, LADDER, NO_CONTEXT_MESSAGE, REPRESENTATIONS, TASKS, TutorInputError,
                               TutorService, detect_intent)


def chunk(i, text, subtopics=("Race Conditions",)):
    return {"chunk_id": f"doc::c{i:04d}", "filename": "doc.pdf", "section": f"Sec {i}", "page_start": i, "slide_start": None,
            "text": text, "metadata": {"subtopics": list(subtopics), "source": "VIT", "document_title": "Sync"}}


class Retriever:
    def __init__(self, results=None):
        self.results, self.queries = results, []

    def search(self, query, top_k=5):
        self.queries.append(query)
        if self.results is not None:
            return self.results
        return [chunk(i, f"passage {i} about {query}") for i in range(1, 4)]


class Script:
    """Records prompts; analysis levels are popped from `levels`; text replies are `reply`."""
    def __init__(self, levels=(), reply="An explanation [S1]."):
        self.levels, self.reply, self.prompts, self.json_calls = list(levels), reply, [], 0

    def __call__(self, prompt, json_mode=False, on_token=None):
        self.prompts.append(prompt)
        if json_mode:
            self.json_calls += 1
            return json.dumps({"level": self.levels.pop(0), "gap": "the key idea"})
        if on_token:
            on_token(self.reply)
        return self.reply


def task_of(prompt):
    return prompt.split("\nTASK\n", 1)[1].split("\n\nCOURSE CONTEXT", 1)[0]


def make(levels=(), results=None, learner=None, **kw):
    llm, retriever = Script(levels, **kw), Retriever(results)
    return TutorService(retriever, llm, learner=learner, top_k=3), llm, retriever


# ------------------------------------------------------------------ normal answer
def test_a_question_is_answered_not_quizzed():
    tutor, llm, _ = make()
    session, turn = tutor.start("What is a race condition?")
    assert turn.stage == "ANSWER" and turn.message == "An explanation [S1]." and turn.mode == "answer_first"
    assert task_of(llm.prompts[0]) == TASKS["ANSWER"] and "Do not ask the student a question" in TASKS["ANSWER"]
    assert llm.json_calls == 0 and not session.pending_check and turn.tutor_state["open"]
    assert [s["ref"] for s in turn.sources] == ["S1", "S2", "S3"]
    assert turn.concepts[0]["id"] == "race_condition"
    assert {a["id"] for a in turn.actions} == {"got_it", "explain_differently", "test_me"}


def test_a_check_is_offered_on_the_first_answer_then_only_every_third():
    tutor, _, _ = make()
    session, first = tutor.start("What is a mutex?")
    offers = [first.follow_up is not None]
    for q in ("What is a semaphore?", "What is a monitor?", "What is deadlock?", "What is starvation?"):
        offers.append(tutor.respond(session, q).follow_up is not None)
    assert offers == [True, False, False, True, False]  # nothing is forced after every message


def test_citations_the_model_invents_never_reach_the_student():
    tutor, _, _ = make(reply="Locks help [S1] [S9]. See [Wikipedia].")
    _, turn = tutor.start("What is a lock?")
    assert turn.message == "Locks help [S1]. See." and "[S9]" not in turn.message and "Wikipedia" not in turn.message


def test_stream_callbacks_see_sources_before_tokens():
    tutor, _, _ = make()
    seen = []
    tutor.start("What is a lock?", emit=lambda k, d: seen.append(k))
    assert seen == ["sources", "token"]


def test_blank_input_is_refused_with_a_safe_message():
    tutor, _, _ = make()
    with pytest.raises(TutorInputError):
        tutor.start("   ")
    session, _ = tutor.start("What is a lock?")
    with pytest.raises(TutorInputError):
        tutor.respond(session, "  ")
    with pytest.raises(TutorInputError, match="intent"):
        tutor.respond(session, "x", intent="shout")


# ------------------------------------------------------------------ insufficient context
def test_no_retrieval_means_no_model_call_and_a_fixed_honest_message():
    tutor, llm, _ = make(results=[])
    session, turn = tutor.start("How do I bake bread?")
    assert turn.stage == "NO_CONTEXT" and turn.message == NO_CONTEXT_MESSAGE and turn.sources == []
    assert llm.prompts == [] and "Threads/Synchronization knowledge base" in turn.message
    assert tutor.respond(session, "What is a mutex?").stage == "NO_CONTEXT"  # the conversation stays open


def test_a_relevance_gate_can_reject_results_that_exist():
    retriever, llm = Retriever(), Script()
    tutor = TutorService(retriever, llm, is_relevant=lambda results: False)
    _, turn = tutor.start("What is paging?")
    assert turn.stage == "NO_CONTEXT" and llm.prompts == []


def test_the_prompt_tells_the_model_what_to_do_with_thin_material():
    tutor, llm, _ = make()
    tutor.start("What is a lock?")
    assert "the course material does not specify it" in task_of(llm.prompts[0]) or \
        "course material does not specify" in llm.prompts[0]


# ------------------------------------------------------------------ follow-ups
def test_a_short_follow_up_is_searched_with_the_conversations_concepts():
    tutor, _, retriever = make()
    session, _ = tutor.start("What is a race condition?")
    tutor.respond(session, "why though?")
    assert retriever.queries[1].startswith("why though?") and "race condition" in retriever.queries[1]
    tutor.respond(session, "What exactly is a semaphore and how is it used?")
    assert retriever.queries[2] == "What exactly is a semaphore and how is it used?"  # long enough to stand alone


# ------------------------------------------------------------------ explaining differently
def test_explain_differently_walks_the_ladder_and_never_repeats_the_same_view():
    tutor, llm, _ = make()
    session, _ = tutor.start("What is a race condition?")
    used = []
    for _ in range(len(LADDER) - 1):
        turn = tutor.respond(session, "I still don't understand")
        used.append(turn.tutor_state["representation"])
        assert "Do NOT repeat it" in task_of(llm.prompts[-1])
        assert REPRESENTATIONS[used[-1]] in task_of(llm.prompts[-1])
    assert used == list(LADDER[1:])  # intuition -> analogy -> scenario -> code
    assert tutor.respond(session, "explain it differently").tutor_state["representation"] == "intuition"  # loops, gently


@pytest.mark.parametrize("text,rep", [("give me an analogy", "analogy"), ("explain in simple words", "intuition"),
                                      ("can you give an example", "example"), ("show me the code", "code"),
                                      ("a real-world scenario please", "scenario"), ("explain in more detail", "detailed")])
def test_the_student_can_ask_for_a_specific_style(text, rep):
    tutor, llm, _ = make()
    session, _ = tutor.start("What is a mutex?")
    turn = tutor.respond(session, text)
    assert turn.tutor_state["representation"] == rep and REPRESENTATIONS[rep] in task_of(llm.prompts[-1])


def test_code_and_example_requests_search_for_code_and_examples():
    tutor, _, retriever = make()
    session, _ = tutor.start("What is a mutex?")
    tutor.respond(session, "show me the code")
    assert retriever.queries[-1].endswith("code example")
    tutor.respond(session, "give me an example")
    assert retriever.queries[-1].endswith("example")


def test_the_buttons_send_intents_and_need_no_text():
    tutor, _, _ = make()
    session, _ = tutor.start("What is a mutex?")
    assert tutor.respond(session, "", intent="analogy").tutor_state["representation"] == "analogy"
    assert "Glad that made sense" in tutor.respond(session, "", intent="got_it").message


def test_got_it_costs_no_model_call_and_no_learner_change():
    learner = LearnerModel()
    tutor, llm, _ = make(learner=learner)
    session, _ = tutor.start("What is a race condition?")
    calls, before = len(llm.prompts), learner.profile()
    turn = tutor.respond(session, "got it, thanks")
    assert len(llm.prompts) == calls and turn.learner_update is None and learner.profile() == before


@pytest.mark.parametrize("text,intent", [
    ("I still don't understand", "explain_differently"), ("i dont get it", "explain_differently"),
    ("this is confusing", "explain_differently"), ("samajh nahi aaya", "explain_differently"),
    ("explain that again", "explain_differently"), ("quiz me", "test_me"), ("test my understanding", "test_me"),
    ("give me a problem on race conditions", "test_me"), ("thanks", "got_it"), ("Got it", "got_it"),
    ("make it simpler", "simpler"), ("ELI5", "simpler"), ("any analogy?", "analogy"),
    ("What is an example of deadlock?", None), ("What is the difference between a mutex and a semaphore?", None),
    ("Why does counter++ race?", None), ("What does pthread_join do?", None), ("", None),
])
def test_requests_are_recognised_by_rules_not_by_the_model(text, intent):
    assert detect_intent(text) == intent


# ------------------------------------------------------------------ checking understanding
def start_check(levels=(), **kw):
    tutor, llm, retriever = make(levels, **kw)
    session, _ = tutor.start("What is a race condition?")
    turn = tutor.respond(session, "", intent="test_me")
    assert turn.stage == "CHECK" and session.pending_check and turn.tutor_state["pending_check"]
    return tutor, llm, session


def test_solid_answer_confirms_and_clears_the_check():
    tutor, llm, session = start_check(["solid"])
    turn = tutor.respond(session, "Both threads read the old value, so one increment is lost.")
    assert turn.stage == "FEEDBACK" and turn.analysis["level"] == "solid" and not turn.tutor_state["pending_check"]
    assert task_of(llm.prompts[-1]) == TASKS["CONFIRM"] and turn.follow_up and turn.actions[0]["id"] == "test_me"


@pytest.mark.parametrize("level,task", [("partial", "CLARIFY"), ("misconception", "CORRECT"), ("unclear", "SIMPLIFY")])
def test_other_answers_get_a_targeted_reply_and_the_check_stays_open(level, task):
    tutor, llm, session = start_check([level])
    turn = tutor.respond(session, "Races only happen between processes, I think.")
    prompt = llm.prompts[-1]
    assert turn.analysis["level"] == level and task_of(prompt).startswith(TASKS[task]) and turn.tutor_state["pending_check"]
    assert ("GAP\nthe key idea" in prompt) == (task in ("CLARIFY", "CORRECT"))
    assert "not correct" in TASKS["CORRECT"] and "never call a wrong statement right" in prompt.lower() or task != "CORRECT"


def test_after_two_missed_rounds_the_answer_is_given_and_the_check_ends():
    tutor, llm, session = start_check(["partial", "partial", "partial"])
    tutor.respond(session, "one thing"), tutor.respond(session, "another thing")
    final = tutor.respond(session, "a third thing")
    assert task_of(llm.prompts[-1]) == TASKS["RESOLVE"] and not final.tutor_state["pending_check"]
    assert final.stage == "FEEDBACK" and session.check_rounds == 0


def test_dont_know_skips_the_model_and_just_tell_me_reveals_the_answer():
    tutor, llm, session = start_check()
    calls = llm.json_calls
    turn = tutor.respond(session, "I don't know")
    assert llm.json_calls == calls and turn.analysis["level"] == "unclear"
    turn = tutor.respond(session, "just tell me the answer")
    assert task_of(llm.prompts[-1]) == TASKS["RESOLVE"] and not turn.tutor_state["pending_check"]


def test_a_garbled_analysis_counts_as_unclear_not_a_crash():
    tutor, llm, session = start_check()
    llm.levels = []
    original = llm.__call__
    session_llm = tutor.llm
    tutor.llm = lambda prompt, json_mode=False, on_token=None: "<<<garbage" if json_mode else original(prompt, json_mode, on_token)
    turn = tutor.respond(session, "Maybe the scheduler decides something about memory")
    assert turn.analysis["level"] == "unclear" and task_of(session_llm.prompts[-1]).startswith(TASKS["SIMPLIFY"])


def test_a_new_question_during_a_check_is_answered_and_the_check_stays_pending():
    tutor, llm, session = start_check()
    pending, ctx, rounds = session.pending_check, session.check_context, session.check_rounds
    turn = tutor.respond(session, "What is a semaphore?")
    assert turn.stage == "ANSWER" and turn.tutor_state["pending_check"]
    assert (session.pending_check, session.check_context, session.check_rounds) == (pending, ctx, rounds)
    assert "new question" in llm.prompts[-1]


def test_hinglish_questions_are_understood_but_replies_stay_english():
    assert is_new_question("sir deadlock kaise hota hai?")
    tutor, llm, session = start_check()
    tutor.respond(session, "mujhe semaphore samjhao")
    assert "every word you write is English" in llm.prompts[-1]


# ------------------------------------------------------------------ the learner model
def test_only_meaningful_interactions_reach_the_learner_model():
    learner = LearnerModel()
    tutor, _, _ = make(learner=learner)
    session, turn = tutor.start("What is a race condition?")
    assert turn.learner_update["concept_id"] == "race_condition" and learner.concept_state("race_condition")["doubts"] == 1
    tutor.respond(session, "ok cool")  # chit-chat: no concept, not a question
    tutor.respond(session, "thanks"), tutor.respond(session, "", intent="got_it")
    assert learner.profile()["summary"]["unknown"] == 27 and learner.concept_state("race_condition")["doubts"] == 1


def test_asking_for_it_again_is_a_weak_signal_but_wanting_an_analogy_is_not():
    learner = LearnerModel()
    tutor, _, _ = make(learner=learner)
    session, _ = tutor.start("What is a race condition?")
    start = learner.confidence("race_condition")
    tutor.respond(session, "give me an analogy")
    assert learner.confidence("race_condition") == start
    tutor.respond(session, "I still don't understand")
    assert learner.confidence("race_condition") < start


def test_check_results_update_mastery_and_misconceptions():
    learner = LearnerModel()
    tutor, _, session = start_check(["misconception", "solid"], learner=learner)
    session.concepts = ["race_condition"]
    turn = tutor.respond(session, "Race conditions only happen with processes.")
    assert turn.learner_update["level"] == "weak" and learner.concept_state("race_condition")["misconceptions"]
    turn = tutor.respond(session, "Two threads interleave the read and write of the shared counter.")
    assert turn.learner_update["change"] > 0 and learner.concept_state("race_condition")["attempts"] == 2


def test_learner_context_reaches_the_prompt_but_only_for_concepts_already_seen():
    learner = LearnerModel()
    learner.record_evidence("race_condition", "misconception", "thinks only processes race")
    tutor, llm, _ = make(learner=learner)
    tutor.start("What is a race condition?")
    assert "LEARNER CONTEXT" in llm.prompts[0] and "thinks only processes race" in llm.prompts[0]
    tutor2, llm2, _ = make(learner=learner)
    tutor2.start("What is a monitor?")
    assert "LEARNER CONTEXT" not in llm2.prompts[0]


# ------------------------------------------------------------------ failures leave the conversation intact
def test_a_failed_model_call_changes_nothing_so_the_student_can_retry():
    tutor, llm, session = start_check(["solid"])
    snapshot = (list(session.history), session.pending_check, session.answers)
    good = tutor.llm

    def down(prompt, json_mode=False, on_token=None):
        raise LLMError("unavailable", "refused")
    tutor.llm = down
    with pytest.raises(LLMError):
        tutor.respond(session, "Both threads read the old value, so one update is lost.")
    with pytest.raises(LLMError):
        tutor.respond(session, "What is a semaphore?")
    assert (session.history, session.pending_check, session.answers) == snapshot
    tutor.llm = good
    assert tutor.respond(session, "Both threads read the old value, so one update is lost.").stage == "FEEDBACK"


def test_every_intent_rule_has_a_name_the_service_understands():
    assert {name for name, _ in INTENT_RULES} <= svc.INTENTS
