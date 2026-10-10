"""Product upgrade tests: environment configuration, the LLM provider layer (Ollama over HTTP, mock), LLM errors and the
health check. Nothing here needs Ollama: transport failures are provoked on purpose or the transport is replaced.

    python3 -m pytest tests -q
"""
import io
import json
import socket
import urllib.error

import pytest

from src.config import ConfigError, Settings, load_dotenv
from src.tutor import llm as llm_mod
from src.tutor.llm import LLMError, OllamaLLM, OllamaProvider, available_models, health_check, make_llm
from src.tutor.mock_llm import MockLLM


# ------------------------------------------------------------------ configuration
def test_defaults_need_nothing_from_the_environment():
    s = Settings.from_env({})
    assert (s.llm_provider, s.ollama_model, s.tutor_mode) == ("ollama", "qwen3:8b", "socratic")  # owner decision 2026-10-10
    assert s.ollama_base_url == "http://localhost:11434"
    assert (s.retrieval_top_k, s.reranker_top_k, s.final_context_k, s.reranker_enabled) == (20, 20, 5, False)


def test_the_ollama_laptop_is_configured_by_environment_not_code():
    s = Settings.from_env({"OLLAMA_BASE_URL": "http://192.168.1.50:11434/", "OLLAMA_MODEL": "llama3.1:8b",
                           "LLM_PROVIDER": "OLLAMA", "RERANKER_ENABLED": "yes", "FINAL_CONTEXT_K": "6", "DEBUG": "1",
                           "APP_PORT": "9000", "RERANK_MIN_SCORE": "-4.5"})
    assert s.ollama_base_url == "http://192.168.1.50:11434"  # trailing slash removed
    assert (s.ollama_model, s.llm_provider, s.reranker_enabled, s.final_context_k) == ("llama3.1:8b", "ollama", True, 6)
    assert (s.debug, s.app_port, s.rerank_min_score) == (True, 9000, -4.5)
    assert make_llm(s).host == "http://192.168.1.50:11434"
    assert make_llm(s, "qwen3:8b").model == "qwen3:8b"  # the page's model picker overrides OLLAMA_MODEL


@pytest.mark.parametrize("env,needle", [
    ({"OLLAMA_BASE_URL": "192.168.1.50"}, "OLLAMA_BASE_URL"),
    ({"LLM_PROVIDER": "openai"}, "LLM_PROVIDER"),
    ({"TUTOR_MODE": "chatty"}, "TUTOR_MODE"),
    ({"RERANKER_ENABLED": "maybe"}, "RERANKER_ENABLED"),
    ({"FINAL_CONTEXT_K": "zero"}, "FINAL_CONTEXT_K"),
    ({"FINAL_CONTEXT_K": "0"}, "FINAL_CONTEXT_K"),
    ({"RERANKER_TOP_K": "50"}, "RERANKER_TOP_K"),
    ({"FINAL_CONTEXT_K": "30"}, "FINAL_CONTEXT_K"),
    ({"RERANK_MIN_SCORE": "high"}, "RERANK_MIN_SCORE"),
])
def test_a_bad_value_is_refused_with_the_variable_name(env, needle):
    with pytest.raises(ConfigError, match=needle):
        Settings.from_env(env)


def test_dotenv_fills_gaps_but_never_overrides_the_environment(tmp_path):
    f = tmp_path / ".env"
    f.write_text("# comment\nOLLAMA_MODEL='llama3.1:8b'\n\nLLM_PROVIDER=mock\nbad line\n", encoding="utf-8")
    env = {"LLM_PROVIDER": "ollama"}
    assert load_dotenv(f, env) == ["OLLAMA_MODEL"]
    assert env == {"LLM_PROVIDER": "ollama", "OLLAMA_MODEL": "llama3.1:8b"}
    assert load_dotenv(tmp_path / "missing.env", env) == []


def test_no_ip_address_is_hardcoded_in_the_source():
    import re
    from pathlib import Path
    for path in Path("src").rglob("*.py"):
        assert not re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", path.read_text(encoding="utf-8").replace("127.0.0.1", "")), path


# ------------------------------------------------------------------ Ollama errors are student-safe
def test_unreachable_server_is_a_clear_error_not_a_stack_trace():
    port = socket.socket()
    port.bind(("127.0.0.1", 0))
    free = port.getsockname()[1]
    port.close()  # nothing listens here now
    with pytest.raises(LLMError) as e:
        OllamaLLM("m", host=f"http://127.0.0.1:{free}", timeout=3)("hello")
    assert e.value.kind == "unavailable" and "Check that Ollama is running" in str(e.value)
    assert str(free) not in str(e.value) and "127.0.0.1" not in str(e.value)  # the address stays out of student text


def _raise(exc):
    def urlopen(req, timeout=None):
        raise exc
    return urlopen


@pytest.mark.parametrize("exc,kind", [
    (socket.timeout("slow"), "timeout"),
    (urllib.error.URLError(socket.timeout("slow")), "timeout"),
    (urllib.error.HTTPError("u", 404, "nf", {}, io.BytesIO(b'{"error":"model not found"}')), "model_missing"),
    (urllib.error.HTTPError("u", 500, "boom", {}, io.BytesIO(b"x")), "bad_response"),
    (ConnectionResetError("reset"), "unavailable"),
])
def test_transport_failures_map_to_typed_errors(monkeypatch, exc, kind):
    monkeypatch.setattr(llm_mod.urllib.request, "urlopen", _raise(exc))
    with pytest.raises(LLMError) as e:
        OllamaLLM("m")("p")
    assert e.value.kind == kind and str(e.value) == llm_mod.MESSAGES[kind]


class _Resp:
    def __init__(self, lines=None, body=b""):
        self.lines, self.body = lines or [], body
    def __enter__(self): return self
    def __exit__(self, *e): pass
    def read(self): return self.body
    def __iter__(self): return iter(self.lines)


def test_malformed_and_empty_replies_are_bad_responses(monkeypatch):
    monkeypatch.setattr(llm_mod.urllib.request, "urlopen", lambda req, timeout=None: _Resp(body=b"not json"))
    monkeypatch.setattr(llm_mod.json, "load", lambda r: json.loads(r.read()))
    with pytest.raises(LLMError) as e:
        OllamaLLM("m")("p")
    assert e.value.kind == "bad_response"
    monkeypatch.setattr(llm_mod.urllib.request, "urlopen",
                        lambda req, timeout=None: _Resp(body=b'{"message": {"content": "  "}}'))
    with pytest.raises(LLMError, match="unusable"):
        OllamaLLM("m")("p")
    monkeypatch.setattr(llm_mod.urllib.request, "urlopen",
                        lambda req, timeout=None: _Resp(lines=[b'{"error": "model \'x\' not found"}']))
    with pytest.raises(LLMError) as e:
        OllamaLLM("m")("p", on_token=lambda t: None)
    assert e.value.kind == "model_missing"


# ------------------------------------------------------------------ health check
def _tags(monkeypatch, names):
    body = json.dumps({"models": [{"name": n} for n in names]}).encode()
    monkeypatch.setattr(llm_mod.urllib.request, "urlopen", lambda req, timeout=None: _Resp(body=body))
    monkeypatch.setattr(llm_mod.json, "load", lambda r: json.loads(r.read()))


def test_health_reports_a_ready_server_and_a_missing_model(monkeypatch):
    s = Settings.from_env({"OLLAMA_BASE_URL": "http://10.1.2.3:11434"})
    _tags(monkeypatch, ["qwen3:8b", "nomic-embed-text:latest"])
    ok = health_check(s)
    assert ok["ok"] and ok["reachable"] and ok["model_available"] and ok["models"] == ["qwen3:8b"]
    _tags(monkeypatch, ["llama3.2:3b"])
    miss = health_check(s)
    assert not miss["ok"] and miss["reachable"] and not miss["model_available"] and "not installed" in miss["message"]
    assert "10.1.2.3" not in json.dumps(ok) + json.dumps(miss)


def test_health_never_raises_when_ollama_is_down(monkeypatch):
    monkeypatch.setattr(llm_mod.urllib.request, "urlopen", _raise(ConnectionRefusedError("no")))
    h = health_check(Settings.from_env({}))
    assert not h["ok"] and not h["reachable"] and h["error"] == "unavailable" and "unavailable" in h["message"]
    with pytest.raises(LLMError):
        available_models()


def test_mock_provider_is_always_healthy():
    h = health_check(Settings.from_env({"LLM_PROVIDER": "mock"}))
    assert h["ok"] and h["provider"] == "mock"
    assert isinstance(make_llm(Settings.from_env({"LLM_PROVIDER": "mock"})), MockLLM)


# ------------------------------------------------------------------ the mock behaves like the real callable
def test_mock_streams_and_returns_valid_analysis_json():
    mock, seen = MockLLM(), []
    out = mock("TASK\nx\n\nCOURSE CONTEXT\nREFERENCE MATERIAL>>>", on_token=seen.append)
    assert "".join(seen).strip() == out and out
    analysis = json.loads(mock("STUDENT'S LAST MESSAGE\ni am not sure", json_mode=True))
    assert analysis["level"] == "unclear"


# ------------------------------------------------------------------ provider abstraction, reasoning, timeouts
def test_providers_share_one_abstraction():
    from src.tutor.llm import LLMProvider, OllamaProvider
    from src.tutor.mock_llm import MockLLMProvider
    assert issubclass(OllamaProvider, LLMProvider) and issubclass(MockLLMProvider, LLMProvider) and OllamaLLM is OllamaProvider
    assert MockLLM().health()["provider"] == "mock"


def test_mock_mode_never_touches_the_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("the mock provider must not use the network")
    monkeypatch.setattr(llm_mod.urllib.request, "urlopen", boom)
    monkeypatch.setattr(llm_mod.socket, "create_connection", boom)
    s = Settings.from_env({"LLM_PROVIDER": "mock", "OLLAMA_BASE_URL": "http://172.16.0.9:11434"})
    assert make_llm(s)("TASK\nx\n\nCOURSE CONTEXT\nREFERENCE MATERIAL>>>")
    assert health_check(s)["ok"]


def test_the_reasoning_field_is_never_returned(monkeypatch):
    body = json.dumps({"model": "qwen3:8b", "message": {"role": "assistant", "content": "The answer.",
                                                        "thinking": "SECRET CHAIN OF THOUGHT"}, "done": True}).encode()
    monkeypatch.setattr(llm_mod.urllib.request, "urlopen", lambda req, timeout=None: _Resp(body=body))
    monkeypatch.setattr(llm_mod.json, "load", lambda r: json.loads(r.read()))
    assert OllamaProvider("qwen3:8b")("p") == "The answer."


def test_an_inline_think_block_is_removed_from_replies_and_from_the_live_stream(monkeypatch):
    from src.tutor.llm import final_answer
    assert final_answer("<think>private\nreasoning</think>\n\nVisible answer.") == "Visible answer."
    assert final_answer(None) == ""
    chunks = [{"message": {"content": "<think>hidden "}}, {"message": {"content": "thoughts</think>"}},
              {"message": {"content": "Shown."}, "done": True}]
    monkeypatch.setattr(llm_mod.urllib.request, "urlopen",
                        lambda req, timeout=None: _Resp(lines=[json.dumps(c).encode() for c in chunks]))
    streamed = []
    out = OllamaProvider("m")("p", on_token=streamed.append)
    assert out == "Shown." and "".join(streamed) == "Shown." and "hidden" not in out + "".join(streamed)


def test_a_reply_without_the_message_field_is_a_bad_response(monkeypatch):
    monkeypatch.setattr(llm_mod.urllib.request, "urlopen", lambda req, timeout=None: _Resp(body=b'{"done": true}'))
    monkeypatch.setattr(llm_mod.json, "load", lambda r: json.loads(r.read()))
    with pytest.raises(LLMError) as e:
        OllamaProvider("m")("p")
    assert e.value.kind == "bad_response"


def test_connect_and_read_timeouts_are_separate_settings():
    s = Settings.from_env({"OLLAMA_CONNECT_TIMEOUT": "3", "OLLAMA_READ_TIMEOUT": "90"})
    assert (s.ollama_connect_timeout, s.ollama_read_timeout) == (3, 90)
    assert Settings.from_env({"LLM_TIMEOUT_SECONDS": "200"}).ollama_read_timeout == 200  # the old name still works
    assert (Settings.from_env({}).ollama_connect_timeout, Settings.from_env({}).ollama_read_timeout) == (5, 120)
    p = make_llm(s)
    assert (p.connect_timeout, p.timeout) == (3, 90)
    with pytest.raises(ConfigError, match="OLLAMA_READ_TIMEOUT"):
        Settings.from_env({"OLLAMA_READ_TIMEOUT": "soon"})


def test_an_unreachable_mac_is_reported_at_the_connect_timeout_not_the_read_timeout(monkeypatch):
    seen = {}

    def refuse(addr, timeout=None):
        seen["addr"], seen["timeout"] = addr, timeout
        raise socket.timeout("timed out")
    monkeypatch.setattr(llm_mod.socket, "create_connection", refuse)
    monkeypatch.setattr(llm_mod.urllib.request, "urlopen", lambda *a, **k: pytest.fail("must not wait for a reply"))
    p = OllamaProvider("m", host="http://172.16.9.9:11434", timeout=120, connect_timeout=2)
    with pytest.raises(LLMError) as e:
        p("hello")
    assert e.value.kind == "unavailable" and seen == {"addr": ("172.16.9.9", 11434), "timeout": 2}
    assert "172.16.9.9" not in str(e.value)
