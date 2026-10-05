"""Phase 4 tests: the chat page's web server, with a fake retriever and a scripted model (no Ollama needed).

    python3 -m pytest tests -q
"""
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from src.tutor import server
from src.tutor.controller import TutorController


class FakeRetriever:
    def search(self, query, top_k=5):
        return [{"chunk_id": "doc::c0001", "filename": "doc.pdf", "section": "Sec", "page_start": 3,
                 "slide_start": None, "text": "context text"}]


def fake_llm(prompt, json_mode=False, on_token=None):
    out = '{"level": "misconception", "gap": "the gap"}' if json_mode else "What do you think? [S1]"
    if on_token:
        for word in out.split(" "):
            on_token(word + " ")
    return out


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "LOGS", tmp_path)
    app = server.App(FakeRetriever(), "fake-model")
    monkeypatch.setattr(app, "tutor", lambda model: TutorController(app.retriever, fake_llm))
    server.Handler.app = app
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}", tmp_path
    httpd.shutdown()


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return [json.loads(line[6:]) for line in r.read().decode().split("\n\n") if line.startswith("data: ")]


def test_page_and_full_dialogue_stream(base):
    url, logs = base
    with urllib.request.urlopen(url + "/") as r:
        assert b"OS Tutor" in r.read()
    events = post(url + "/api/start", {"question": "Why a mutex?"})
    kinds = [e["type"] for e in events]
    assert kinds[0] == "session" and kinds[1] == "sources" and "token" in kinds and kinds[-1] == "turn"
    assert events[1]["data"][0]["ref"] == "S1" and events[1]["data"][0]["text"] == "context text"
    assert events[-1]["data"]["stage"] == "DIAGNOSE"
    sid = events[0]["data"]["id"]
    events = post(url + "/api/reply", {"session_id": sid, "text": "my answer"})
    assert [e["type"] for e in events][0] == "analysis" and events[-1]["data"]["stage"] == "EXPLAIN"
    log = [json.loads(l) for f in logs.glob("*.jsonl") for l in f.read_text().splitlines()]
    assert [r["stage"] for r in log] == ["DIAGNOSE", "EXPLAIN"] and log[1]["student"] == "my answer"


def test_errors_are_reported_in_the_stream(base):
    url, _ = base
    assert post(url + "/api/start", {"question": "  "})[-1]["type"] == "error"
    assert post(url + "/api/reply", {"session_id": "nope", "text": "x"})[-1]["type"] == "error"
