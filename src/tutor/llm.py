"""LLM providers for the tutor: one abstraction, Ollama (local or on another machine) and a mock.

    llm = make_llm()                       # from the environment: LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL
    llm = OllamaProvider("qwen3:8b", host="http://<OLLAMA_HOST>:11434")
    llm("prompt")                          # full reply as a string
    llm("prompt", json_mode=True)          # Ollama constrains the reply to valid JSON
    llm("prompt", on_token=print)          # streams tokens to the callback, returns the full reply
    llm.health()                           # {"provider", "model", "reachable", ...}; never raises

    LLMProvider (the callable the tutor depends on)
        +-- OllamaProvider (alias OllamaLLM)   HTTP to an Ollama server; the Mac's address is configuration, never code
        +-- MockLLMProvider (alias MockLLM)    scripted, no network (src/tutor/mock_llm.py)

Only the model's final answer is ever returned. Ollama's reasoning ("thinking" field, or a <think>...</think> block that
an older server leaves in the content) is dropped here, so it can never reach the chat history, the learner model, the log
or the page. Every failure (server unreachable, timeout, model not pulled, malformed or empty reply) surfaces as `LLMError`
with a message that is safe to show a student; the technical detail stays in `.detail` for the server log.

Generation settings live in one place (the constants below) so every caller gets the same production defaults.
TEMPERATURE 0.3 (Phase 4.1; was 0.0) keeps answers controlled but lets the tutor phrase an explanation naturally
instead of reciting the source. The fixed seed keeps a given model, prompt and Ollama version reproducible, so the
quality evaluation stays comparable between runs. `think: false` turns off qwen3's hidden reasoning (slow); models
without it ignore the flag.
"""
import json
import re
import socket
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from urllib.parse import urlparse

from src.config import Settings

_DEFAULTS = Settings()
HOST = _DEFAULTS.ollama_base_url
DEFAULT_MODEL = _DEFAULTS.ollama_model
TEMPERATURE = 0.3  # production default for tutor generation and analysis
SEED = 42
NUM_CTX = 8192

MESSAGES = {
    "unavailable": "The AI service is currently unavailable. Check that Ollama is running and that the configured "
                   "Ollama server address is reachable from this machine.",
    "timeout": "The AI service took too long to answer. Try again, or check the load on the Ollama server.",
    "model_missing": "The configured model is not installed on the Ollama server. Pull it there (ollama pull <model>) "
                     "or change OLLAMA_MODEL.",
    "bad_response": "The AI service returned an unusable reply. Try again.",
}
THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.S | re.I)


class LLMError(Exception):
    """A model call failed. `str(e)` is safe to show a student; `.kind` is one of MESSAGES; `.detail` is for logs."""

    def __init__(self, kind, detail=""):
        super().__init__(MESSAGES[kind])
        self.kind, self.detail = kind, str(detail)


def _translate(exc):
    """Map a transport failure onto an LLMError."""
    if isinstance(exc, urllib.error.HTTPError):
        body = ""
        try:
            body = exc.read().decode("utf-8", "replace")
        except Exception:
            pass
        kind = "model_missing" if exc.code == 404 else "bad_response"
        return LLMError(kind, f"HTTP {exc.code} {body[:200]}")
    if isinstance(exc, (socket.timeout, TimeoutError)) or (
            isinstance(exc, urllib.error.URLError) and isinstance(exc.reason, (socket.timeout, TimeoutError))):
        return LLMError("timeout", exc)
    if isinstance(exc, (OSError, urllib.error.URLError)):
        return LLMError("unavailable", exc)
    return LLMError("bad_response", repr(exc))


def final_answer(text):
    """The model's visible answer: any inline reasoning block removed, surrounding whitespace trimmed."""
    return THINK_BLOCK.sub("", text or "").strip()


class LLMProvider(ABC):
    """What the tutor depends on: a callable that turns a prompt into the model's final answer."""
    name = "provider"
    model = ""

    @abstractmethod
    def __call__(self, prompt, json_mode=False, on_token=None):
        """Return the final answer (a string). `json_mode` asks for valid JSON; `on_token(text)` streams the answer."""

    @abstractmethod
    def health(self):
        """{"provider", "model", "reachable", ...}. Never raises, never contains the server address."""


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, model=DEFAULT_MODEL, host=HOST, temperature=TEMPERATURE, seed=SEED, num_ctx=NUM_CTX, timeout=120,
                 connect_timeout=None):
        """`timeout` is how long to wait for the model's reply. With `connect_timeout` set, an unreachable server (Mac
        asleep or off the network) is reported after that many seconds instead of after the full reply timeout."""
        self.model, self.host, self.timeout = model, host.rstrip("/"), timeout
        self.connect_timeout = connect_timeout
        self.options = {"temperature": temperature, "seed": seed, "num_ctx": num_ctx}

    def _probe(self):
        parts = urlparse(self.host)
        port = parts.port or (443 if parts.scheme == "https" else 80)
        try:
            socket.create_connection((parts.hostname, port), timeout=self.connect_timeout).close()
        except OSError as exc:  # includes connect timeouts: nothing answered, so the service is unavailable
            raise LLMError("unavailable", exc) from exc

    def __call__(self, prompt, json_mode=False, on_token=None):
        body = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "stream": on_token is not None,
                "think": False, "options": self.options} | ({"format": "json"} if json_mode else {})
        req = urllib.request.Request(f"{self.host}/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        if self.connect_timeout:
            self._probe()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                text = self._read(resp, body["stream"], on_token)
        except LLMError:
            raise
        except Exception as exc:
            raise _translate(exc) from exc
        text = final_answer(text)
        if not text and not json_mode:
            raise LLMError("bad_response", "empty reply")
        return text

    @staticmethod
    def _read(resp, stream, on_token):
        """Collect the answer from `message.content` only; the reasoning field (`message.thinking`) is never read."""
        if not stream:
            return json.load(resp)["message"]["content"]
        parts, in_think = [], False
        for line in resp:
            if not line.strip():
                continue
            chunk = json.loads(line)
            if chunk.get("error"):
                raise LLMError("model_missing" if "not found" in str(chunk["error"]) else "bad_response", chunk["error"])
            if text := chunk.get("message", {}).get("content", ""):
                parts.append(text)
                # an older server may stream a <think> block inside the content: keep it out of the live stream too
                if "<think>" in text.lower():
                    in_think = True
                if not in_think:
                    on_token(text)
                if "</think>" in text.lower():
                    in_think = False
            if chunk.get("done"):
                break
        return "".join(parts)

    def health(self):
        out = {"provider": self.name, "model": self.model, "reachable": False, "model_available": False}
        try:
            models = available_models(self.host, timeout=self.connect_timeout or 5)
        except LLMError as e:
            return out | {"ok": False, "message": str(e), "error": e.kind}
        present = any(m == self.model or m.split(":")[0] == self.model for m in models)
        message = "Ollama is reachable and the model is installed." if present else MESSAGES["model_missing"]
        return out | {"reachable": True, "model_available": present, "ok": present, "models": models, "message": message}


OllamaLLM = OllamaProvider


def available_models(host=HOST, timeout=10):
    """Names of the chat models Ollama has installed (embedding-only models left out)."""
    try:
        with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=timeout) as resp:
            return sorted(m["name"] for m in json.load(resp)["models"] if "embed" not in m["name"])
    except Exception as exc:
        raise _translate(exc) from exc


def make_llm(settings=None, model=None):
    """The provider the settings ask for. `model` overrides OLLAMA_MODEL (the page's model picker). With
    LLM_PROVIDER=mock nothing is ever sent over the network."""
    s = settings or Settings.from_env()
    if s.llm_provider == "mock":
        from .mock_llm import MockLLM
        return MockLLM()
    return OllamaProvider(model or s.ollama_model, host=s.ollama_base_url, timeout=s.ollama_read_timeout,
                          connect_timeout=s.ollama_connect_timeout)


def health_check(settings=None, timeout=None):
    """Is the configured LLM usable? Never raises. The Ollama address is deliberately not part of the answer."""
    s = settings or Settings.from_env()
    if s.llm_provider == "mock":
        return make_llm(s).health()
    provider = make_llm(s)
    provider.connect_timeout = timeout or s.ollama_connect_timeout
    return provider.health()
