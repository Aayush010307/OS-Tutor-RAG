"""The first turn of a Socratic lesson answers the student's question.

Product decision (2026-10-10): asked "What are threads?", the app's tutor used to reply with a diagnostic question
("What is the main difference between a process and a thread?"). The first reply now explains, with citations and no
question, unless the student asked to be quizzed. After it the Socratic flow continues: the student's next message
leads to a check question (or is answered, if it is a new question), and from there the usual rounds apply.

The controller keeps the diagnose-first opening by default: the tutor evaluation's frozen scenarios script answers to
a diagnostic question. The web app opts into the explaining opening (`App.tutor`). No Ollama, no index.

    python3 -m pytest tests -q
"""
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from src.config import Settings
from src.learner.model import LearnerModel
from src.tutor import server
from src.tutor.controller import QUIZ_REQUEST, STAGE_INSTRUCTIONS, TutorController
from src.tutor.conversations import ConversationStore
from src.tutor.service import TASKS, TutorService

CONCEPTUAL = ["What are threads?", "Explain process synchronization.", "What is a semaphore?",
              "What is the difference between a process and a thread?", "Teach me about semaphores.",
              "Why does pthread_cond_wait take a mutex?"]
QUIZ = ["Quiz me on threads.", "Test my understanding of synchronization.", "Ask me questions about synchronization.",
        "Give me a quiz on deadlock", "quiz me"]


class Retriever:
    def __init__(self, empty=False):
        self.queries, self.empty = [], empty

    def search(self, query, top_k=5):
        self.queries.append(query)
        if self.empty:
            return []
        return [{"chunk_id": f"{query[:12]}::c{i}", "filename": "doc.pdf", "section": f"Sec {i}", "page_start": i,
                 "slide_start": None, "text": f"context text {i} about {query}"} for i in range(1, top_k + 1)]

    def is_relevant(self, results):
        return bool(results)

    def get_chunk(self, chunk_id):
        return None


class Script:
    """Tutor replies end with a question, as real DIAGNOSE / EXPLAIN / CHECK turns do; analyses follow `levels`."""
    def __init__(self, levels=()):
        self.levels, self.prompts, self.json_calls = list(levels), [], 0

    def __call__(self, prompt, json_mode=False, on_token=None):
        if json_mode:
            self.json_calls += 1
            return json.dumps({"level": self.levels.pop(0), "gap": "the key idea"})
        self.prompts.append(prompt)
        reply = f"Some text [S1]. What is question number {len(self.prompts)}?"
        if on_token:
            on_token(reply)
        return reply


def task(prompt):
    return prompt.split("\nTASK\n", 1)[1].split("\n\nCOURSE CONTEXT\n", 1)[0]


def opened(question="What are threads?", levels=(), **kw):
    llm, retriever = Script(levels), Retriever(**kw)
    tutor = TutorController(retriever, llm, top_k=2, opening="explain")
    session, turn = tutor.start(question)
    return tutor, llm, retriever, session, turn


# ------------------------------------------------------------------ the rule
@pytest.mark.parametrize("text", CONCEPTUAL)
def test_a_conceptual_question_is_not_a_quiz_request(text):
    assert not QUIZ_REQUEST.search(text)


@pytest.mark.parametrize("text", QUIZ)
def test_quiz_requests_are_recognised(text):
    assert QUIZ_REQUEST.search(text)


# ------------------------------------------------------------------ 1-4: the first reply explains
@pytest.mark.parametrize("question", CONCEPTUAL)
def test_the_first_reply_explains_with_no_question(question):
    tutor, llm, retriever, session, turn = opened(question)
    prompt = task(llm.prompts[-1])
    assert prompt == STAGE_INSTRUCTIONS["INTRODUCE"] and "DIAGNOSE" not in prompt
    assert "Do not ask the student any question" in prompt and "do not end with a question" in prompt
    assert "Do NOT answer" not in llm.prompts[-1]  # the diagnose task is not in the prompt at all
    assert turn.stage == "EXPLAIN" and turn.analysis is None and llm.json_calls == 0
    assert turn.tutor_state == {"rounds": 0, "max_rounds": 2, "awaiting_answer": False}
    assert retriever.queries == [question]


def test_the_explaining_task_is_beginner_friendly_grounded_and_never_judges_the_student():
    t = STAGE_INSTRUCTIONS["INTRODUCE"]
    assert "beginner" in t and "example" in t and "[S1]" in t and "course material does not specify" in t
    assert "do not judge" in t.lower()


# ------------------------------------------------------------------ 5-6: asking to be quizzed still diagnoses
@pytest.mark.parametrize("question", QUIZ)
def test_asking_to_be_quizzed_starts_with_a_question(question):
    _, llm, _, session, turn = opened(question)
    assert turn.stage == "DIAGNOSE" and task(llm.prompts[-1]) == STAGE_INSTRUCTIONS["DIAGNOSE"]
    assert turn.tutor_state["awaiting_answer"] is True and session.stage == "DIAGNOSE"


def test_the_controller_still_diagnoses_first_by_default():
    # the tutor evaluation (`tutor_eval.run`) builds TutorController(retriever, llm): its scripted replies answer a
    # diagnostic question, so its opening must not change
    tutor = TutorController(Retriever(), Script(), top_k=2)
    assert tutor.start("What are threads?")[1].stage == "DIAGNOSE"


# ------------------------------------------------------------------ 7: after the explanation the Socratic flow continues
@pytest.mark.parametrize("reply", ["Give me a quiz.", "quiz me", "ok", "got it, thanks"])
def test_the_next_message_leads_to_a_check_question(reply):
    tutor, llm, _, session, _ = opened()
    turn = tutor.respond(session, reply)
    assert turn.stage == "CHECK" and task(llm.prompts[-1]) == STAGE_INSTRUCTIONS["CHECK"] and llm.json_calls == 0
    assert turn.tutor_state["awaiting_answer"] is True and session.rounds == 0


def test_an_answer_to_the_check_follows_the_usual_rounds():
    tutor, llm, _, session, _ = opened(levels=["partial", "misconception", "partial"])
    tutor.respond(session, "quiz me")
    stages = [tutor.respond(session, a).stage for a in ("half an answer", "a wrong answer", "still half")]
    assert stages == ["EXPLAIN", "EXPLAIN", "DONE"] and llm.json_calls == 3


def test_a_correct_answer_to_the_check_wraps_up():
    tutor, llm, _, session, _ = opened(levels=["solid"])
    tutor.respond(session, "quiz me")
    turn = tutor.respond(session, "threads share the address space but each has its own stack")
    assert turn.stage == "DONE" and task(llm.prompts[-1]) == STAGE_INSTRUCTIONS["WRAP_UP"]
    assert turn.tutor_state["awaiting_answer"] is False


# ------------------------------------------------------------------ 8: new questions
def test_a_follow_up_question_after_the_explanation_is_answered_without_a_question():
    tutor, llm, retriever, session, first = opened()
    turn = tutor.respond(session, "What is a process?")
    assert turn.stage == "ANSWER" and retriever.queries[-1] == "What is a process?"
    assert task(llm.prompts[-1]) == STAGE_INSTRUCTIONS["INTRODUCE"]  # not the aside task: no question to come back to
    assert [s["chunk_id"] for s in turn.sources] != [s["chunk_id"] for s in first.sources]
    assert session.stage == "INTRODUCED" and session.question == "What are threads?"


def test_a_side_question_during_a_check_keeps_the_check_pending():
    tutor, llm, _, session, _ = opened()
    tutor.respond(session, "quiz me")
    turn = tutor.respond(session, "What is a semaphore?")
    assert turn.stage == "ANSWER" and task(llm.prompts[-1]) == STAGE_INSTRUCTIONS["ASIDE"]
    assert session.stage == "CHECK" and turn.tutor_state["awaiting_answer"] is True


# ------------------------------------------------------------------ 9: uncertainty
def test_unsure_after_the_explanation_gets_a_simpler_one_without_a_round():
    tutor, llm, _, session, _ = opened()
    turn = tutor.respond(session, "I don't understand")
    assert turn.stage == "EXPLAIN" and task(llm.prompts[-1]) == STAGE_INSTRUCTIONS["SUPPORT"] and llm.json_calls == 0
    assert session.rounds == 0 and turn.tutor_state["awaiting_answer"] is True  # it ends with an easier question


def test_unsure_during_a_check_still_gets_support_without_a_round():
    tutor, llm, _, session, _ = opened()
    tutor.respond(session, "quiz me")
    turn = tutor.respond(session, "i am not sure")
    assert turn.stage == "EXPLAIN" and session.rounds == 0 and llm.json_calls == 0


# ------------------------------------------------------------------ 10: hints
def test_a_hint_with_nothing_pending_says_so_without_the_model():
    tutor, llm, retriever, session, _ = opened()
    calls = len(llm.prompts)
    turn = tutor.respond(session, "give me a hint")
    assert turn.stage == "HINT" and turn.sources == [] and len(llm.prompts) == calls and len(retriever.queries) == 1
    assert "no question" in turn.message.lower() and session.stage == "INTRODUCED"


def test_a_hint_during_the_check_restates_the_check_question():
    tutor, llm, _, session, _ = opened()
    tutor.respond(session, "quiz me")  # the check is question number 2
    turn = tutor.respond(session, "Can I get a hint?")
    assert turn.stage == "HINT" and turn.message.endswith("Try the question again: What is question number 2?")
    assert session.stage == "CHECK"


# ------------------------------------------------------------------ 12, 14: sources
def test_the_explanation_cites_its_own_retrieval():
    _, llm, _, session, turn = opened("What is a semaphore?")
    assert [s["chunk_id"] for s in turn.sources] == ["What is a se::c1", "What is a se::c2"]
    assert "context text 1 about What is a semaphore?" in llm.prompts[-1]


def test_with_no_course_material_the_explanation_cites_nothing_and_must_say_so():
    _, llm, _, _, turn = opened("How do I bake sourdough bread?", empty=True)
    assert turn.sources == [] and "(no course material was found)" in llm.prompts[-1]
    assert "course material does not specify" in task(llm.prompts[-1])


# ------------------------------------------------------------------ the web app (SSE), both modes
@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "LOGS", tmp_path / "logs")
    started = []

    def build(mode, llm):
        settings = Settings.from_env({"LLM_PROVIDER": "mock", "TUTOR_MODE": mode})
        app = server.App(Retriever(), "mock", settings, LearnerModel(tmp_path / "l.json"), ConversationStore(tmp_path / "c.json"))
        monkeypatch.setattr(server, "make_llm", lambda s, model=None: llm)
        server.Handler.app = app
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started.append(httpd)
        return f"http://127.0.0.1:{httpd.server_port}"

    yield build
    for httpd in started:
        httpd.shutdown()


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return [json.loads(l[5:]) for b in r.read().decode().split("\n\n") for l in b.split("\n") if l.startswith("data:")]


def test_the_web_app_opens_a_socratic_lesson_with_an_explanation(api):
    llm = Script(["solid"])
    url = api("socratic", llm)
    events = post(url + "/api/start", {"question": "What are threads?"})
    turn = events[-1]["data"]
    assert [e["type"] for e in events][:2] == ["session", "sources"] and turn["stage"] == "EXPLAIN"
    assert turn["tutor_state"] == {"rounds": 0, "max_rounds": 2, "awaiting_answer": False}
    assert [s["chunk_id"] for s in turn["sources"]] == [s["chunk_id"] for s in events[1]["data"]]  # same set as shown
    assert task(llm.prompts[-1]) == STAGE_INSTRUCTIONS["INTRODUCE"]
    sid = events[0]["data"]["id"]
    assert post(url + "/api/reply", {"session_id": sid, "text": "quiz me"})[-1]["data"]["stage"] == "CHECK"
    quiz = post(url + "/api/start", {"question": "Quiz me on threads."})[-1]["data"]
    assert quiz["stage"] == "DIAGNOSE" and quiz["tutor_state"]["awaiting_answer"] is True


def test_answer_first_still_answers_directly(api):
    llm = Script()
    url = api("answer_first", llm)
    turn = post(url + "/api/start", {"question": "What are threads?"})[-1]["data"]
    assert turn["stage"] == "ANSWER" and turn["mode"] == "answer_first"
    assert task(llm.prompts[-1]).startswith(TASKS["ANSWER"])


def test_answer_first_service_is_unchanged_by_the_opening_option():
    tutor = TutorService(Retriever(), Script(), top_k=2)
    assert tutor.start("What are threads?")[1].stage == "ANSWER"
