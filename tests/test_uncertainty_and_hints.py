"""Uncertainty, explanation requests and hints are not wrong answers.

Regression for the Socratic failure seen with real qwen3:8b: a student who replied "i am not sure" was told "The
student's answer is not correct". Saying you do not know is not a technical error, so:

- a reply that is only uncertainty ("i am not sure", "I don't know what join does") or a request to have the idea
  explained is recognised by rule, without the model; it gets a supportive explanation that never calls the student
  wrong, and it does not use one of the explanation rounds. Still unsure after that, or with the rounds already spent,
  the student gets the full answer instead of another question.
- a partially correct answer is acknowledged before the gap is named; only a misconception is called wrong.
- a hint request gets a hint: the lesson stage, the pending question and the rounds stay as they were.

No Ollama, no index.

    python3 -m pytest tests -q
"""
import json

import pytest

from src.tutor import server
from src.tutor.controller import (STAGE_INSTRUCTIONS, TutorController, is_hint_request, is_new_question, is_unsure,
                                  wants_explanation)
from src.tutor.service import TASKS, TutorService

SCENARIOS = json.load(open("data/evaluation/tutor_scenarios_v1.json"))
WRONG_FIRST = "say plainly in your first sentence that it is not correct"


class Retriever:
    def __init__(self):
        self.queries = []

    def search(self, query, top_k=5):
        self.queries.append(query)
        return [{"chunk_id": f"doc::c000{i}", "filename": "doc.pdf", "section": f"Sec {i}", "page_start": i,
                 "slide_start": None, "text": f"context text {i} about {query}"} for i in range(1, top_k + 1)]


class Script:
    def __init__(self, levels=()):
        self.levels, self.prompts, self.json_calls = list(levels), [], 0

    def __call__(self, prompt, json_mode=False, on_token=None):
        if json_mode:
            self.json_calls += 1
            return json.dumps({"level": self.levels.pop(0), "gap": "the key idea"})
        self.prompts.append(prompt)
        reply = "tutor text [S1]"
        if on_token:
            on_token(reply)
        return reply


def task(prompt):
    return prompt.split("\nTASK\n", 1)[1].split("\n\nCOURSE CONTEXT\n", 1)[0]


def lesson(levels=()):
    llm, retriever = Script(levels), Retriever()
    tutor = TutorController(retriever, llm, top_k=2)
    session, _ = tutor.start("Why does cond_wait take a mutex?")
    return tutor, llm, retriever, session


UNSURE = ["i am not sure", "I am not sure.", "I'm not sure", "not sure, sorry", "I don't know", "i dont know", "idk",
          "no idea", "Sorry, no idea.", "No, I don't know.", "I still don't understand.", "i dont get it",
          "I'm still confused, sorry.", "I don't know what join does.", "I'm not sure what a flag lock is.",
          "I don't remember how semaphores work.", "I'm not sure, I don't really know why.", "No, I still don't get it."]
NOT_UNSURE = ["not sure, but I think it releases the lock", "I'm not sure, I thought if and while do the same thing here.",
              "I don't know why but it keeps the lock", "No idea, maybe the computer is too slow?", "I'm not sure it releases the lock",
              "hmm", "it keeps the lock", "Maybe it is something to do with memory being faster?", "I think it releases the mutex"]
HINTS = ["give me a hint", "can you give me a hint", "Can I get a hint?", "hint please", "hint", "any hints?", "a clue?",
         "I need a hint", "could you give me a small hint please"]
EXPLAIN_REQUESTS = ["explain it to me", "Can you explain it directly?", "just explain it", "please explain",
                    "Can you explain that again?"]


# ------------------------------------------------------------------ the rules
@pytest.mark.parametrize("text", UNSURE)
def test_pure_uncertainty_is_recognised(text):
    assert is_unsure(text) and not is_new_question(text) and not is_hint_request(text)


@pytest.mark.parametrize("text", NOT_UNSURE)
def test_an_answer_with_content_is_not_mistaken_for_uncertainty(text):
    assert not is_unsure(text)  # a hedged answer is still an answer: the model judges it


@pytest.mark.parametrize("text", HINTS)
def test_hint_requests_are_recognised(text):
    assert is_hint_request(text) and not is_unsure(text)


@pytest.mark.parametrize("text", ["What is a hint?", "the hint is that it releases the lock while it waits",
                                  "explain semaphores", "What is a semaphore?"])
def test_questions_and_answers_mentioning_hints_or_explain_are_not_requests(text):
    assert not is_hint_request(text) and not wants_explanation(text)


def test_no_scripted_evaluation_reply_is_taken_for_a_hint_or_an_explanation_request():
    replies = [r for sc in SCENARIOS["scenarios"] for rs in sc["replies"].values() for r in rs]
    assert not [r for r in replies if is_hint_request(r) or wants_explanation(r)]
    assert not [r for sc in SCENARIOS["scenarios"] for p in ("solid", "misconception") for r in sc["replies"][p] if is_unsure(r)]


# ------------------------------------------------------------------ Socratic: uncertainty
@pytest.mark.parametrize("text", UNSURE + EXPLAIN_REQUESTS)
def test_uncertainty_gets_a_supportive_explanation_without_the_model_and_without_a_round(text):
    tutor, llm, retriever, session = lesson()
    events = []
    turn = tutor.respond(session, text, emit=lambda k, d: events.append((k, d)))
    assert llm.json_calls == 0 and len(retriever.queries) == 1  # no analysis call, no side-question retrieval
    assert turn.stage == "EXPLAIN" and turn.analysis["level"] == "unclear" and events[0] == ("analysis", turn.analysis)
    assert session.rounds == 0 and turn.tutor_state == {"rounds": 0, "max_rounds": 2, "awaiting_answer": True}
    prompt = task(llm.prompts[-1])
    assert prompt.startswith(STAGE_INSTRUCTIONS["SUPPORT"]) and WRONG_FIRST not in prompt and "not correct" not in prompt
    assert [s["chunk_id"] for s in turn.sources] == ["doc::c0001", "doc::c0002"]  # the lesson's own passages


def test_still_unsure_after_support_gets_the_full_answer_not_another_question():
    tutor, llm, _, session = lesson()
    assert tutor.respond(session, "I don't know").stage == "EXPLAIN"
    final = tutor.respond(session, "I still don't get it")
    assert final.stage == "DONE" and task(llm.prompts[-1]) == STAGE_INSTRUCTIONS["ANSWER"] and session.rounds == 0


def test_uncertainty_after_the_rounds_are_spent_gets_the_full_answer():
    tutor, llm, _, session = lesson(["partial", "misconception"])
    assert [tutor.respond(session, r).stage for r in ("half an answer", "a wrong answer")] == ["EXPLAIN", "EXPLAIN"]
    assert session.rounds == 2 and tutor.respond(session, "I still don't know.").stage == "DONE"


def test_uncertainty_does_not_use_up_an_explanation_round():
    tutor, _, _, session = lesson(["partial", "partial", "partial"])
    tutor.respond(session, "I'm not sure")
    stages = [tutor.respond(session, "half an answer").stage for _ in range(3)]
    assert stages == ["EXPLAIN", "EXPLAIN", "DONE"]  # both rounds are still there for real attempts


@pytest.mark.parametrize("sc", SCENARIOS["scenarios"], ids=lambda sc: sc["query_id"])
def test_the_frozen_unsure_scenarios_keep_their_expected_flow(sc):
    # tutor_eval EXPECTED["unsure"]: stages EXPLAIN, EXPLAIN, DONE when the middle reply is not solid
    tutor, _, _, session = lesson(["unclear", "partial", "unclear"])
    assert [tutor.respond(session, r).stage for r in sc["replies"]["unsure"]] == ["EXPLAIN", "EXPLAIN", "DONE"]


# ------------------------------------------------------------------ Socratic: answers the model judges
def test_a_partial_answer_is_acknowledged_not_called_wrong():
    tutor, llm, _, session = lesson(["partial"])
    turn = tutor.respond(session, "it releases the lock")
    prompt = task(llm.prompts[-1])
    assert turn.stage == "EXPLAIN" and session.rounds == 1 and turn.tutor_state == {"rounds": 1, "max_rounds": 2, "awaiting_answer": True}
    assert "correct as far as it goes" in prompt and "Do not call it wrong" in prompt and "first sentence" not in prompt.split("LEVEL")[1]


def test_a_misconception_is_still_called_wrong_plainly():
    tutor, llm, _, session = lesson(["misconception"])
    tutor.respond(session, "it keeps holding the mutex the whole time it sleeps")
    level = task(llm.prompts[-1]).split("\nLEVEL\n")[1]
    assert "technically wrong" in level and "first sentence" in level


def test_a_vague_reply_the_model_finds_unclear_is_supported_but_uses_a_round():
    tutor, llm, _, session = lesson(["unclear"])
    turn = tutor.respond(session, "something with memory")
    assert llm.json_calls == 1 and turn.stage == "EXPLAIN" and session.rounds == 1
    assert task(llm.prompts[-1]).startswith(STAGE_INSTRUCTIONS["SUPPORT"])


def test_every_tutor_prompt_says_to_talk_to_the_student_directly():
    tutor, llm, _, session = lesson(["partial"])
    tutor.respond(session, "half an answer")
    assert all('never call them "the student"' in p for p in llm.prompts)


# ------------------------------------------------------------------ Socratic: hints
@pytest.mark.parametrize("stage_levels", [[], ["partial"], ["solid"]], ids=["at-diagnose", "at-explain", "at-check"])
def test_a_hint_keeps_the_lesson_where_it_was(stage_levels):
    tutor, llm, retriever, session = lesson(stage_levels)
    if stage_levels:
        tutor.respond(session, "an answer")
    before = (session.stage, session.rounds, session.supports, list(session.gaps), len(retriever.queries))
    turn = tutor.respond(session, "Can I get a hint?")
    assert turn.stage == "HINT" and turn.analysis is None and llm.json_calls == len(stage_levels)
    assert (session.stage, session.rounds, session.supports, session.gaps, len(retriever.queries)) == before
    assert task(llm.prompts[-1]).startswith(STAGE_INSTRUCTIONS["HINT"]) and session.history[-2] == ("Student", "Can I get a hint?")
    assert [s["chunk_id"] for s in turn.sources] == ["doc::c0001", "doc::c0002"]
    assert turn.tutor_state == {"rounds": session.rounds, "max_rounds": 2, "awaiting_answer": True}


def test_after_a_hint_the_answer_is_judged_as_usual():
    tutor, llm, _, session = lesson(["solid"])
    tutor.respond(session, "give me a hint")
    turn = tutor.respond(session, "it releases the mutex while it waits")
    assert turn.stage == "CHECK" and llm.json_calls == 1


def test_the_hint_task_holds_the_answer_back():
    assert "without giving it away" in STAGE_INSTRUCTIONS["HINT"] and "Do not explain the full idea" in STAGE_INSTRUCTIONS["HINT"]


def test_a_real_new_question_is_still_answered_on_the_side():
    tutor, _, retriever, session = lesson()
    turn = tutor.respond(session, "What is a semaphore?")
    assert turn.stage == "ANSWER" and retriever.queries[-1] == "What is a semaphore?"


# ------------------------------------------------------------------ the SSE turn carries the round count
def test_the_turn_payload_reports_the_socratic_rounds():
    tutor, _, _, session = lesson(["partial"])
    payload = server.turn_payload(tutor.respond(session, "half an answer"))
    assert payload["stage"] == "EXPLAIN" and payload["tutor_state"] == {"rounds": 1, "max_rounds": 2, "awaiting_answer": True}


# ------------------------------------------------------------------ answer-first
def check_pending(levels=()):
    llm, retriever = Script(levels), Retriever()
    tutor = TutorService(retriever, llm, top_k=2)
    session, _ = tutor.start("What do sem_wait and sem_post do?")
    tutor.respond(session, intent="test_me")
    return tutor, llm, retriever, session


@pytest.mark.parametrize("text", ["i am not sure", "I am not sure.", "Sorry, no idea.", "explain it to me"])
def test_answer_first_uncertainty_at_a_check_is_simplified_without_the_model(text):
    tutor, llm, retriever, session = check_pending()
    turn = tutor.respond(session, text)
    assert llm.json_calls == 0 and len(retriever.queries) == 1
    assert turn.stage == "FEEDBACK" and turn.analysis["level"] == "unclear" and task(llm.prompts[-1]).startswith(TASKS["SIMPLIFY"])


def test_answer_first_hedged_misconception_still_reaches_the_model():
    tutor, llm, _, session = check_pending(["misconception"])
    turn = tutor.respond(session, "I'm not sure, I thought sem_post blocks the caller.")
    assert llm.json_calls == 1 and turn.analysis["level"] == "misconception"


def test_answer_first_hint_at_a_check_keeps_the_check_pending():
    tutor, llm, retriever, session = check_pending()
    rounds, check = session.check_rounds, session.pending_check
    turn = tutor.respond(session, "can you give me a hint")
    assert turn.stage == "HINT" and turn.tutor_state["pending_check"] and llm.json_calls == 0
    assert (session.check_rounds, session.pending_check, len(retriever.queries)) == (rounds, check, 1)
    assert task(llm.prompts[-1]).startswith(STAGE_INSTRUCTIONS["HINT"])
    assert [s["chunk_id"] for s in turn.sources] == [c["chunk_id"] for c in session.check_context]


def test_answer_first_hint_with_nothing_pending_says_so_without_the_model():
    llm, retriever = Script(), Retriever()
    tutor = TutorService(retriever, llm, top_k=2)
    session, _ = tutor.start("What do sem_wait and sem_post do?")
    calls = len(llm.prompts)
    turn = tutor.respond(session, "give me a hint")
    assert len(llm.prompts) == calls and turn.sources == [] and len(retriever.queries) == 1
    assert "no question" in turn.message.lower()


def test_answer_first_unsure_after_an_answer_explains_differently():
    llm, retriever = Script(), Retriever()
    tutor = TutorService(retriever, llm, top_k=2)
    session, _ = tutor.start("What do sem_wait and sem_post do?")
    turn = tutor.respond(session, "i am not sure")
    assert turn.stage == "ANSWER" and turn.tutor_state["representation"] == "intuition"
    assert len(retriever.queries) == 1  # the same passages, not a search for "i am not sure"


def test_answer_first_simplify_helps_without_answering_the_check():
    # Live, qwen3:8b worked through the check's own scenario, stated its result, then asked the same check again
    # (5 of 6 topics): the old task asked for "one small concrete example" and nothing kept the check unanswered.
    tutor, llm, _, session = check_pending()
    check = session.pending_check
    turn = tutor.respond(session, "i am not sure")
    prompt = task(llm.prompts[-1])
    assert prompt.startswith(TASKS["SIMPLIFY"]) and "do not answer it for them" in prompt
    assert "never state or imply its result" in prompt and "do not work through its scenario, not even inside a question" in prompt
    assert "name what to think about, not the conclusion" in prompt and "wording does not contain the answer" in prompt
    assert "first step toward the check, not the check itself" in prompt and "the same check again" not in prompt
    assert turn.stage == "FEEDBACK" and turn.tutor_state["pending_check"] and session.check_rounds == 1  # still pending
    assert session.history[-3] == ("Tutor", check)  # the check it must not answer is in the conversation


class Asking(Script):
    """Every tutor message ends with its own question, as real DIAGNOSE / EXPLAIN / CHECK turns do."""
    def __call__(self, prompt, json_mode=False, on_token=None):
        if json_mode:
            return super().__call__(prompt, json_mode)
        self.prompts.append(prompt)
        reply = f"Some explanation [S1]. What is the initial value of lock number {len(self.prompts)}?"
        if on_token:
            on_token(reply)
        return reply


def test_a_hint_names_the_tutors_pending_question_not_the_students_original_one():
    # Live, qwen3:8b ended a hint with "Try the question again: What does sem_wait do?" (the student's own opening
    # question) instead of the tutor's pending one, and the student's next answer was then judged against the wrong question.
    llm = Asking(["partial"])
    tutor = TutorController(Retriever(), llm, top_k=2)
    session, _ = tutor.start("What does sem_wait do?")
    tutor.respond(session, "half an answer")  # EXPLAIN ends with question number 2
    events = []
    turn = tutor.respond(session, "give me a hint", emit=lambda k, d: events.append((k, d)))
    hint_task = task(llm.prompts[-1])
    assert "QUESTION TO HINT AT\nWhat is the initial value of lock number 2?" in hint_task
    assert "not the student's original question" in STAGE_INSTRUCTIONS["HINT"]
    # the restatement is added by the code, not left to the model, so it is always the pending question
    assert "Do not ask a question and do not restate it" in STAGE_INSTRUCTIONS["HINT"]
    assert turn.message.endswith("Try the question again: What is the initial value of lock number 2?")
    assert session.history[-1] == ("Tutor", turn.message)  # what the next answer is judged against
    assert "".join(d for k, d in events if k == "token") == turn.message  # the stream shows the same text


def test_two_hints_in_a_row_restate_the_same_pending_question():
    llm = Asking(["partial"])
    tutor = TutorController(Retriever(), llm, top_k=2)
    session, _ = tutor.start("What does sem_wait do?")
    tutor.respond(session, "half an answer")
    first, second = tutor.respond(session, "give me a hint"), tutor.respond(session, "another hint please")
    pending = "What is the initial value of lock number 2?"
    assert first.message.endswith(pending) and second.message.endswith(pending)


def test_answer_first_hint_names_the_pending_check():
    llm, retriever = Asking(), Retriever()
    tutor = TutorService(retriever, llm, top_k=2)
    session, _ = tutor.start("What do sem_wait and sem_post do?")
    tutor.respond(session, intent="test_me")  # the check is question number 2
    tutor.respond(session, "give me a hint")
    turn = session.history[-1][1]
    assert "QUESTION TO HINT AT\nWhat is the initial value of lock number 2?" in task(llm.prompts[-1])
    assert turn.endswith("Try the question again: What is the initial value of lock number 2?")
