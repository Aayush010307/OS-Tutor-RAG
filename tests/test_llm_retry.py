"""Integration of PR #1 with the Phase 4.1 retry: the provider abstraction keeps retrying transient Ollama failures,
never after a token reached the student. Also: the reranker refuses weights that are not the pinned ones.

No network: urllib and the weights file are faked.

    python3 -m pytest tests -q
"""
import io
import json
import urllib.error

import pytest

from src.retrieval import reranker
from src.tutor import llm as llm_mod
from src.tutor.llm import RETRIES, LLMError, OllamaProvider


class Resp:
    def __init__(self, body=None, lines=None, fail_after=None):
        self.body, self.lines, self.fail_after = body, lines or [], fail_after

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return json.dumps(self.body).encode()

    def __iter__(self):
        for i, line in enumerate(self.lines):
            if self.fail_after is not None and i == self.fail_after:
                raise urllib.error.URLError(ConnectionResetError("connection reset by peer"))
            yield line


def chunk(text, done=False):
    return json.dumps({"message": {"content": text}, "done": done}).encode() + b"\n"


def http_error(code):
    return urllib.error.HTTPError("http://localhost:11434/api/chat", code, "err", {}, io.BytesIO(b"oops"))


@pytest.fixture
def ollama(monkeypatch):
    """Replace urlopen with a script of outcomes; record how many requests were made."""
    calls = []

    def install(*outcomes):
        script = list(outcomes)

        def fake_urlopen(req, timeout=None):
            calls.append(json.loads(req.data))
            out = script.pop(0)
            if isinstance(out, Exception):
                raise out
            return out
        monkeypatch.setattr(llm_mod.urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setattr(llm_mod.time, "sleep", lambda s: None)
        return calls
    return install


def test_a_transient_500_is_retried(ollama):
    calls = ollama(http_error(500), Resp({"message": {"content": "answer [S1]"}}))
    assert OllamaProvider("qwen3:8b")("p") == "answer [S1]" and len(calls) == 2


def test_persistent_server_errors_give_up_after_the_retries(ollama):
    calls = ollama(*[http_error(503)] * (RETRIES + 1))
    with pytest.raises(LLMError) as e:
        OllamaProvider("qwen3:8b")("p")
    assert e.value.kind == "bad_response" and len(calls) == RETRIES + 1


def test_a_missing_model_is_not_retried(ollama):
    calls = ollama(http_error(404))
    with pytest.raises(LLMError) as e:
        OllamaProvider("qwen3:8b")("p")
    assert e.value.kind == "model_missing" and len(calls) == 1


def test_a_drop_before_any_token_is_retried_and_tokens_arrive_once(ollama):
    calls = ollama(Resp(lines=[chunk("Hi")], fail_after=0), Resp(lines=[chunk("Hello "), chunk("there", True)]))
    seen = []
    assert OllamaProvider("qwen3:8b")("p", on_token=seen.append) == "Hello there"
    assert seen == ["Hello ", "there"] and len(calls) == 2


def test_no_retry_once_the_student_has_seen_tokens(ollama):
    calls = ollama(Resp(lines=[chunk("The lock "), chunk("is released")], fail_after=1), Resp(lines=[chunk("again", True)]))
    seen = []
    with pytest.raises(LLMError) as e:
        OllamaProvider("qwen3:8b")("p", on_token=seen.append)
    assert e.value.kind == "unavailable" and seen == ["The lock "] and len(calls) == 1


def test_settings_still_reach_ollama(ollama):
    calls = ollama(Resp({"message": {"content": '{"level": "solid", "gap": ""}'}}))
    OllamaProvider("qwen3:8b")("p", json_mode=True)
    assert calls[0]["options"] == {"temperature": 0.3, "seed": 42, "num_ctx": 8192} and calls[0]["think"] is False
    assert calls[0]["format"] == "json"


def test_reranker_refuses_weights_that_are_not_pinned(tmp_path, monkeypatch):
    fake = tmp_path / "model.onnx"
    fake.write_bytes(b"not the pinned weights")
    monkeypatch.setattr(reranker, "_fetch", lambda repo, name, rev: str(fake))
    with pytest.raises(ValueError, match="expected 5d3e70fd"):
        reranker.load_reranker()
