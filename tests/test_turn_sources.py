"""Turn-level source provenance: every tutor `turn` carries the exact passages its reply was generated from.

Regression for the answer-first citation bug: after an off-topic question (A: Bakery Algorithm / CAS), a later answer
about sem_wait/sem_post (B) and its Check and Feedback must cite B, never A. No Ollama, no index.

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
from src.tutor.controller import TutorController
from src.tutor.conversations import ConversationStore
from src.tutor.service import NO_CONTEXT_MESSAGE, TutorService


def chunk(cid, text):
    return {"chunk_id": cid, "filename": "doc.pdf", "section": "Sec", "page_start": 3, "slide_start": None, "text": text,
            "metadata": {"subtopics": ["Semaphores"], "source": "VIT", "document_title": "Sync"}}


A = [chunk("vit::c0036", "Bakery Algorithm: take a number before entering."), chunk("vit::c0025", "compare and swap (CAS).")]
B = [chunk("sema::c0002", "sem_wait() decrements the value and blocks if it becomes negative."),
     chunk("sema::c0003", "sem_post() increments the value and wakes one waiting thread.")]
C = [chunk("bugs::c0012", "Deadlock needs mutual exclusion, hold-and-wait, no preemption and circular wait.")]
D = [chunk("sema::c0010", "```c\nsem_t m; sem_init(&m, 0, 1);\n```")]
ALL = A + B + C + D
ids = lambda srcs: [s["chunk_id"] for s in srcs]


class Retriever:
    """Off-topic questions retrieve A (and are rejected by the relevance gate), deadlock questions C, code requests D,
    everything else B."""
    def search(self, query, top_k=5):
        q = query.lower()
        return A if "sourdough" in q else C if "deadlock" in q else D if "code" in q else B

    def is_relevant(self, results):
        return results is not A

    def get_chunk(self, chunk_id):
        return next((c for c in ALL if c["chunk_id"] == chunk_id), None)


class Script:
    def __init__(self, levels=()):
        self.levels, self.prompts = list(levels), []

    def __call__(self, prompt, json_mode=False, on_token=None):
        self.prompts.append(prompt)
        if json_mode:
            return json.dumps({"level": self.levels.pop(0), "gap": "" if not self.levels else "the key idea"})
        reply = "It decrements and may block [S1]; the post wakes a waiter [S2]."
        if on_token:
            on_token(reply)
        return reply


def context_of(prompt):
    return prompt.split("COURSE CONTEXT", 1)[1].split("STUDENT QUESTION", 1)[0]


# ------------------------------------------------------------------ the service decides each turn's provenance
def test_check_and_feedback_cite_the_answer_they_check_never_an_earlier_question():
    llm, retriever = Script(levels=["solid"]), Retriever()
    tutor = TutorService(retriever, llm, top_k=5, is_relevant=retriever.is_relevant)
    session, t0 = tutor.start("How do I bake sourdough bread at home?")
    assert t0.stage == "NO_CONTEXT" and t0.message == NO_CONTEXT_MESSAGE and t0.sources == []  # A was rejected

    t1 = tutor.respond(session, "What do sem_wait and sem_post do?")
    t2 = tutor.respond(session, intent="test_me")
    t3 = tutor.respond(session, "sem_wait decrements and blocks when negative; sem_post increments and wakes a waiter.")
    assert [t.stage for t in (t1, t2, t3)] == ["ANSWER", "CHECK", "FEEDBACK"]
    for t in (t1, t2, t3):
        assert ids(t.sources) == ids(B) and [s["ref"] for s in t.sources] == ["S1", "S2"]
    # the sources each turn reports are the passages its prompt actually contained
    for prompt in [p for p in llm.prompts if "COURSE CONTEXT" in p]:
        ctx = context_of(prompt)
        assert all(c["text"] in ctx for c in B) and not any(c["text"] in ctx for c in A)


def test_a_side_question_and_a_re_explanation_cite_their_own_retrieval():
    llm, retriever = Script(levels=["solid"]), Retriever()
    tutor = TutorService(retriever, llm, top_k=5, is_relevant=retriever.is_relevant)
    session, t1 = tutor.start("What do sem_wait and sem_post do?")
    assert tutor.respond(session, intent="test_me").stage == "CHECK"
    aside = tutor.respond(session, "What is a deadlock?")  # asked while the check is pending
    assert aside.stage == "ANSWER" and ids(aside.sources) == ids(C)
    feedback = tutor.respond(session, "sem_wait decrements and blocks; sem_post increments and wakes.")
    assert feedback.stage == "FEEDBACK" and ids(feedback.sources) == ids(B)  # the check's own context, not the aside's
    code = tutor.respond(session, intent="code")
    assert code.stage == "ANSWER" and ids(code.sources) == ids(D)


def test_an_off_topic_side_question_reports_no_sources():
    llm, retriever = Script(), Retriever()
    tutor = TutorService(retriever, llm, top_k=5, is_relevant=retriever.is_relevant)
    session, _ = tutor.start("What do sem_wait and sem_post do?")
    tutor.respond(session, intent="test_me")
    turn = tutor.respond(session, "What about sourdough bread?")
    assert turn.stage == "NO_CONTEXT" and turn.sources == []


# ------------------------------------------------------------------ the SSE contract
@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "LOGS", tmp_path / "logs")
    started = []

    def build(mode, llm):
        settings = Settings.from_env({"LLM_PROVIDER": "mock", "TUTOR_MODE": mode})
        app = server.App(Retriever(), "mock", settings, LearnerModel(tmp_path / "l.json"),
                         ConversationStore(tmp_path / "c.json"))
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


def turn_of(events):
    assert events[-1]["type"] == "turn"  # a stream still ends with its turn
    return events[-1]["data"]


def test_the_turn_event_carries_its_own_sources_in_answer_first(api):
    url = api("answer_first", Script(levels=["solid"]))
    events = post(url + "/api/start", {"question": "How do I bake sourdough bread at home?"})
    assert [e["type"] for e in events][:2] == ["session", "sources"] and ids(events[1]["data"]) == ids(A)
    assert turn_of(events)["stage"] == "NO_CONTEXT" and turn_of(events)["sources"] == []  # A was shown, not used
    sid = events[0]["data"]["id"]
    stages = {}
    for body in ({"text": "What do sem_wait and sem_post do?"}, {"intent": "test_me"},
                 {"text": "sem_wait decrements and blocks when negative; sem_post increments and wakes one."}):
        turn = turn_of(post(url + "/api/reply", {"session_id": sid} | body))
        stages[turn["stage"]] = turn
    assert set(stages) == {"ANSWER", "CHECK", "FEEDBACK"}
    for turn in stages.values():
        assert ids(turn["sources"]) == ids(B) and not set(ids(turn["sources"])) & set(ids(A))
        assert [s["ref"] for s in turn["sources"]] == ["S1", "S2"]  # the refs its [S1], [S2] citations use
        assert [s["text"] for s in turn["sources"]] == [c["text"] for c in B]  # the canonical passage
        assert {"ref", "chunk_id", "filename", "section", "location", "label", "display", "preview"} <= set(turn["sources"][0])
        assert {"stage", "message", "analysis", "mode", "follow_up", "concepts", "tutor_state", "learner_update",
                "actions"} <= set(turn)  # every existing field is kept


def test_socratic_turns_carry_the_lesson_sources_and_side_answers_their_own(api):
    url = api("socratic", Script(levels=["partial"]))
    events = post(url + "/api/start", {"question": "What do sem_wait and sem_post do?"})
    assert [e["type"] for e in events][:2] == ["session", "sources"]
    lesson = ids(events[1]["data"])
    # the web app opens with an explanation (2026-10-10), then the check question; both cite the lesson's passages
    assert turn_of(events)["stage"] == "EXPLAIN" and ids(turn_of(events)["sources"]) == lesson == ids(B)
    sid = events[0]["data"]["id"]
    check = turn_of(post(url + "/api/reply", {"session_id": sid, "text": "quiz me"}))
    assert check["stage"] == "CHECK" and ids(check["sources"]) == lesson
    explain = turn_of(post(url + "/api/reply", {"session_id": sid, "text": "It frees the lock."}))
    assert explain["stage"] == "EXPLAIN" and ids(explain["sources"]) == lesson
    side = post(url + "/api/reply", {"session_id": sid, "text": "What is a deadlock?"})
    assert turn_of(side)["stage"] == "ANSWER" and ids(turn_of(side)["sources"]) == ids(C)
    assert ids(next(e for e in side if e["type"] == "sources")["data"]) == ids(C)  # same set the stream showed
