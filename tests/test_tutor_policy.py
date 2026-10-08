"""Phase 4.1 tests: generation settings, the shared prompt policy, citation validation and new-question routing.

These check what the controller guarantees deterministically (settings, prompt policy, provenance, routing). Whether
a model actually follows the policy is measured by the tutor quality evaluation, not here.

    python3 -m pytest tests -q
"""
import json

import pytest

from src.tutor import llm as llm_mod
from src.tutor.controller import (ANALYZE, STAGE_INSTRUCTIONS, TutorController, build_prompt, is_new_question,
                                  validated)
from src.tutor.llm import NUM_CTX, SEED, TEMPERATURE, OllamaLLM

SCENARIOS = json.load(open("data/evaluation/tutor_scenarios_v1.json"))


class FakeRetriever:
    def search(self, query, top_k=5):
        return [{"chunk_id": f"doc::c000{i}", "filename": "doc.pdf", "section": f"Sec {i}", "page_start": i,
                 "slide_start": None, "text": f"context text {i} about {query}"} for i in range(1, top_k + 1)]


class Script:
    def __init__(self, levels, reply="tutor text [S1]"):
        self.levels, self.reply, self.prompts = list(levels), reply, []

    def __call__(self, prompt, json_mode=False, on_token=None):
        self.prompts.append(prompt)
        if json_mode:
            return json.dumps({"level": self.levels.pop(0), "gap": "a gap"})
        if on_token:
            on_token(self.reply)
        return self.reply


def prompts_for(stage, **kw):
    llm = Script([])
    session, _ = TutorController(FakeRetriever(), llm, top_k=2).start("Why does cond_wait take a mutex?")
    return build_prompt(session, STAGE_INSTRUCTIONS[stage], **kw)


# ------------------------------------------------------------------ generation settings
def test_production_defaults_are_central():
    assert (TEMPERATURE, SEED, NUM_CTX) == (0.3, 42, 8192)
    assert OllamaLLM("m").options == {"temperature": 0.3, "seed": 42, "num_ctx": 8192}


@pytest.mark.parametrize("json_mode,stream", [(False, False), (True, False), (False, True)])
def test_ollama_request_carries_the_settings(monkeypatch, json_mode, stream):
    sent = {}

    class Resp:
        def __enter__(self): return self
        def __exit__(self, *e): pass
        def read(self): return b'{"message": {"content": "hi"}}'
        def __iter__(self): return iter([b'{"message": {"content": "hi"}, "done": true}'])

    def fake_urlopen(req, timeout=None):
        sent.update(json.loads(req.data))
        return Resp()

    monkeypatch.setattr(llm_mod.json, "load", lambda r: json.loads(r.read()))
    monkeypatch.setattr(llm_mod.urllib.request, "urlopen", fake_urlopen)
    OllamaLLM("qwen3:8b")("p", json_mode=json_mode, on_token=(lambda t: None) if stream else None)
    assert sent["options"] == {"temperature": 0.3, "seed": 42, "num_ctx": 8192}
    assert sent["think"] is False and sent["stream"] is stream and ("format" in sent) is json_mode


# ------------------------------------------------------------------ shared prompt policy
@pytest.mark.parametrize("stage", list(STAGE_INSTRUCTIONS))
def test_every_student_facing_prompt_carries_one_shared_policy(stage):
    p = prompts_for(stage)
    order = [p.index(h) for h in ("TUTOR POLICY\n", "\nGROUNDING\n", "\nHOW TO WRITE TO THE STUDENT\n", "\nTASK\n",
                                  "\nCOURSE CONTEXT\n", "\nSTUDENT QUESTION\n", "\nSTUDENT'S LAST MESSAGE\n")]
    assert order == sorted(order)
    assert "English only" in p and "do not mirror the student's language" in p.lower()
    assert "Never invent a definition" in p and "the course material does not" in p
    assert "Never call a wrong statement right" in p and "at most 120 words" in p
    assert "never quote the section names" in p and "never write any other kind of citation" in p
    assert "[S1] doc.pdf (p.1) Sec 1" in p and STAGE_INSTRUCTIONS[stage] in p


def test_analysis_prompt_is_grounded_but_not_student_facing():
    session, _ = TutorController(FakeRetriever(), Script([]), top_k=2).start("q")
    p = build_prompt(session, ANALYZE, student_facing=False)
    assert "Reply with JSON only" in p and "GROUNDING" in p
    assert "HOW TO WRITE TO THE STUDENT" not in p and "at most 120 words" not in p
    assert "do not mark a correct answer down" in p  # a correct but brief answer is solid, not partial
    assert "misconception = it states something technically wrong" in p


def test_stage_tasks_state_their_hard_requirements():
    assert "Do NOT answer the question yet" in STAGE_INSTRUCTIONS["DIAGNOSE"]
    assert "must not contain, restate or hint at the answer" in STAGE_INSTRUCTIONS["DIAGNOSE"]
    assert "exactly ONE short question" in STAGE_INSTRUCTIONS["DIAGNOSE"]
    assert "MUST end with ONE short check question" in STAGE_INSTRUCTIONS["EXPLAIN"]
    assert "never call a wrong statement right" in STAGE_INSTRUCTIONS["EXPLAIN"]
    assert "apply it" in STAGE_INSTRUCTIONS["CHECK"] and "repeat the explanation" in STAGE_INSTRUCTIONS["CHECK"]
    assert "Introduce no new material" in STAGE_INSTRUCTIONS["WRAP_UP"]
    for stage in ("EXPLAIN", "WRAP_UP", "ANSWER", "ASIDE"):
        assert "citing the context as [S1], [S2]" in STAGE_INSTRUCTIONS[stage]


# ------------------------------------------------------------------ citations
def test_only_citations_of_retrieved_sources_survive():
    assert validated("A [S1] and B [S2].", 2) == "A [S1] and B [S2]."
    assert validated("A [S9] B [S1] C [Wikipedia] D [Source] E [general knowledge].", 2) == "A B [S1] C D E."
    assert validated("Both hold [S1, S2].", 3) == "Both hold [S1] [S2]."
    assert validated("Padded [S4] .", 1) == "Padded."


def test_controller_strips_invented_citations_from_what_the_student_sees():
    llm = Script(["misconception"], reply="The lock is released [S9] while waiting [S1]. [Wikipedia]")
    tutor = TutorController(FakeRetriever(), llm, top_k=2)
    session, turn = tutor.start("q")
    assert turn.message == "The lock is released while waiting [S1]."
    assert tutor.respond(session, "it keeps the lock").message == "The lock is released while waiting [S1]."


# ------------------------------------------------------------------ new question while a question is pending
@pytest.mark.parametrize("text", ["What is a semaphore?", "how is a mutex different from a semaphore",
                                  "Can you explain that again?", "Compare spinlocks and mutexes.",
                                  "sir semaphore ka wait signal kaise work karta hai?", "mujhe deadlock samjhao"])
def test_new_questions_are_recognised(text):
    assert is_new_question(text)


@pytest.mark.parametrize("text", [
    "it releases the mutex while waiting", "Because each thread has its own call stack", "the lock is held?",
    "I'm not sure, I don't really know why.", "Maybe it is something to do with memory being faster?",
    "just tell me the answer", "skip",
    "When a waiting thread wakes up, the condition may no longer be true, so it rechecks it in a while loop.",
])
def test_answers_are_not_mistaken_for_new_questions(text):
    assert not is_new_question(text)


def test_no_scripted_student_answer_is_routed_away():
    replies = [r for sc in SCENARIOS["scenarios"] for rs in sc["replies"].values() for r in rs]
    assert len(replies) == 56 and not [r for r in replies if is_new_question(r)]


def test_a_new_question_is_answered_and_the_pending_question_stays_pending():
    llm = Script(["solid", "solid"], reply="A semaphore counts permits [S1].")
    tutor = TutorController(FakeRetriever(), llm, top_k=2)
    session, _ = tutor.start("Why does cond_wait take a mutex?")
    turn = tutor.respond(session, "it releases the lock")  # solid -> CHECK pending
    assert turn.stage == "CHECK" and session.stage == "CHECK"
    before = (session.stage, session.rounds, list(session.gaps), session.question)
    aside = tutor.respond(session, "What is a semaphore?")
    assert aside.stage == "ANSWER" and aside.message == "A semaphore counts permits [S1]."
    assert (session.stage, session.rounds, session.gaps, session.question) == before  # check still pending
    assert "new question" in llm.prompts[-1] and "context text 1 about What is a semaphore?" in llm.prompts[-1]
    assert [who for who, _ in session.history][-2:] == ["Student", "Tutor"]
    assert tutor.respond(session, "it would block until a permit is free").stage == "DONE"  # the check still runs


def test_aside_emits_its_own_sources_and_tokens():
    events = []
    tutor = TutorController(FakeRetriever(), Script([], reply="Answer [S1]"), top_k=2)
    session, _ = tutor.start("q")
    turn = tutor.respond(session, "What is a mutex?", emit=lambda k, d: events.append(k))
    assert events == ["sources", "token"] and [s["ref"] for s in turn.sources] == ["S1", "S2"]
