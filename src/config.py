"""Central configuration, read from environment variables (and an optional `.env` file at the repository root).

Nothing here is secret and nothing is machine-specific: the Ollama laptop's address is only ever an environment
value, never source code. `Settings.from_env()` reads the environment at call time, so tests can pass their own dict.

    LLM_PROVIDER        ollama (default) | mock        mock needs no Ollama: scripted, deterministic replies
    OLLAMA_BASE_URL     http://localhost:11434         e.g. http://<OLLAMA_LAPTOP_IP>:11434 for a second laptop
    OLLAMA_MODEL        qwen3:8b
    OLLAMA_CONNECT_TIMEOUT 5                           seconds to reach the Ollama server (also used by the health check)
    OLLAMA_READ_TIMEOUT 120                            seconds to wait for the model's reply (LLM_TIMEOUT_SECONDS is the old name)
    TUTOR_MODE          socratic (default: diagnose first, the evaluated flow) | answer_first (optional)
    REVISION_STEPS      5      questions in one Smart Revision session
    RETRIEVAL_TOP_K     20     fused hybrid candidates handed to the next stage
    RERANKER_ENABLED    false  rerank the candidates with a cross-encoder (falls back to hybrid if it cannot load)
    RERANKER_TOP_K      20     how many candidates are reranked (at most RETRIEVAL_TOP_K)
    RERANK_MIN_SCORE    unset  with the reranker on: if no candidate scores at least this, answer "not enough material"
    FINAL_CONTEXT_K     5      chunks the LLM actually sees
    VECTOR_STORE_DIR    data/vector_store/qdrant
    LEARNER_DB_PATH     data/learner/learner.json
    APP_HOST, APP_PORT  127.0.0.1, 8000
    DEBUG               false
"""
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TRUE, FALSE = {"1", "true", "yes", "on"}, {"0", "false", "no", "off", ""}
PROVIDERS, TUTOR_MODES = ("ollama", "mock"), ("answer_first", "socratic")


class ConfigError(ValueError):
    """A configuration value is unusable; the message names the variable and what it should be."""


def _bool(env, name, default):
    raw = env.get(name)
    if raw is None:
        return default
    if raw.strip().lower() in TRUE:
        return True
    if raw.strip().lower() in FALSE:
        return False
    raise ConfigError(f"{name} must be true or false, got {raw!r}")


def _int(env, name, default, minimum=1):
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from None
    if value < minimum:
        raise ConfigError(f"{name} must be at least {minimum}, got {value}")
    return value


def _float(env, name):
    raw = env.get(name)
    if raw is None or not raw.strip():
        return None
    try:
        return float(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from None


def _choice(env, name, default, choices):
    value = (env.get(name) or default).strip().lower()
    if value not in choices:
        raise ConfigError(f"{name} must be one of {', '.join(choices)}, got {value!r}")
    return value


def _path(env, name, default):
    raw = (env.get(name) or "").strip()
    p = Path(raw) if raw else Path(default)
    return p if p.is_absolute() else ROOT / p


def _base_url(raw):
    url = (raw or "").strip().rstrip("/")
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ConfigError(f"OLLAMA_BASE_URL must look like http://<host>:11434, got {raw!r}")
    return url


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    ollama_connect_timeout: int = 5
    ollama_read_timeout: int = 120
    tutor_mode: str = "socratic"
    revision_steps: int = 5
    retrieval_top_k: int = 20
    reranker_enabled: bool = False
    reranker_top_k: int = 20
    rerank_min_score: float | None = None
    final_context_k: int = 5
    vector_store_dir: Path = ROOT / "data/vector_store/qdrant"
    learner_db_path: Path = ROOT / "data/learner/learner.json"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    debug: bool = False

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        retrieval_top_k = _int(env, "RETRIEVAL_TOP_K", cls.retrieval_top_k)
        reranker_top_k = _int(env, "RERANKER_TOP_K", cls.reranker_top_k)
        final_context_k = _int(env, "FINAL_CONTEXT_K", cls.final_context_k)
        if reranker_top_k > retrieval_top_k:
            raise ConfigError(f"RERANKER_TOP_K ({reranker_top_k}) cannot exceed RETRIEVAL_TOP_K ({retrieval_top_k})")
        if final_context_k > retrieval_top_k:
            raise ConfigError(f"FINAL_CONTEXT_K ({final_context_k}) cannot exceed RETRIEVAL_TOP_K ({retrieval_top_k})")
        return cls(
            llm_provider=_choice(env, "LLM_PROVIDER", cls.llm_provider, PROVIDERS),
            ollama_base_url=_base_url(env.get("OLLAMA_BASE_URL") or cls.ollama_base_url),
            ollama_model=(env.get("OLLAMA_MODEL") or cls.ollama_model).strip(),
            ollama_connect_timeout=_int(env, "OLLAMA_CONNECT_TIMEOUT", cls.ollama_connect_timeout),
            ollama_read_timeout=_int({"OLLAMA_READ_TIMEOUT": env.get("OLLAMA_READ_TIMEOUT") or env.get("LLM_TIMEOUT_SECONDS")},
                                     "OLLAMA_READ_TIMEOUT", cls.ollama_read_timeout),
            tutor_mode=_choice(env, "TUTOR_MODE", cls.tutor_mode, TUTOR_MODES),
            revision_steps=_int(env, "REVISION_STEPS", cls.revision_steps),
            retrieval_top_k=retrieval_top_k,
            reranker_enabled=_bool(env, "RERANKER_ENABLED", cls.reranker_enabled),
            reranker_top_k=reranker_top_k,
            rerank_min_score=_float(env, "RERANK_MIN_SCORE"),
            final_context_k=final_context_k,
            vector_store_dir=_path(env, "VECTOR_STORE_DIR", "data/vector_store/qdrant"),
            learner_db_path=_path(env, "LEARNER_DB_PATH", "data/learner/learner.json"),
            app_host=(env.get("APP_HOST") or cls.app_host).strip(),
            app_port=_int(env, "APP_PORT", cls.app_port),
            debug=_bool(env, "DEBUG", cls.debug),
        )


def load_dotenv(path=ROOT / ".env", environ=None):
    """Load KEY=VALUE lines from a `.env` file into the environment without overriding variables that are already
    set. Standard library only; comments and blank lines are ignored, surrounding quotes are stripped."""
    environ = os.environ if environ is None else environ
    path = Path(path)
    if not path.is_file():
        return []
    loaded = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in environ:
            environ[key] = value
            loaded.append(key)
    return loaded
