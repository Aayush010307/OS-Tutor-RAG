"""Local LLM backend for the tutor (Phase 4): Ollama's HTTP API, standard library only.

    llm = OllamaLLM("qwen3:8b")
    llm("prompt")                          # full reply as a string
    llm("prompt", json_mode=True)          # Ollama constrains the reply to valid JSON
    llm("prompt", on_token=print)          # streams tokens to the callback, returns the full reply

Generation settings live in one place (the constants below) so every caller gets the same production defaults.
TEMPERATURE 0.3 (Phase 4.1; was 0.0) keeps answers controlled but lets the tutor phrase an explanation naturally
instead of reciting the source. The fixed seed keeps a given model, prompt and Ollama version reproducible, so the
quality evaluation stays comparable between runs. `think: false` turns off qwen3's hidden reasoning (slow on a
laptop); models without it ignore the flag.
"""
import json
import time
import urllib.error
import urllib.request

HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:8b"
TEMPERATURE = 0.3  # production default for tutor generation and analysis
SEED = 42
NUM_CTX = 8192
RETRIES = 2  # Ollama occasionally answers 500 mid-run (model evicted, out of memory); retry before giving up


class OllamaLLM:
    def __init__(self, model=DEFAULT_MODEL, host=HOST, temperature=TEMPERATURE, seed=SEED, num_ctx=NUM_CTX, timeout=600):
        self.model, self.host, self.timeout = model, host, timeout
        self.options = {"temperature": temperature, "seed": seed, "num_ctx": num_ctx}

    def __call__(self, prompt, json_mode=False, on_token=None):
        """Retries a transient Ollama failure, but never after tokens have already been streamed to the caller."""
        for attempt in range(RETRIES + 1):
            try:
                return self._chat(prompt, json_mode, on_token)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                streamed = getattr(e, "streamed", False)
                if attempt == RETRIES or streamed:
                    raise
                time.sleep(2 * (attempt + 1))

    def _chat(self, prompt, json_mode=False, on_token=None):
        body = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "stream": on_token is not None,
                "think": False, "options": self.options} | ({"format": "json"} if json_mode else {})
        req = urllib.request.Request(f"{self.host}/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            if not body["stream"]:
                return json.load(resp)["message"]["content"].strip()
            parts = []
            try:
                for line in resp:
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if chunk.get("error"):
                        raise RuntimeError(chunk["error"])
                    if text := chunk.get("message", {}).get("content", ""):
                        parts.append(text)
                        on_token(text)
                    if chunk.get("done"):
                        break
            except (urllib.error.URLError, TimeoutError) as e:
                e.streamed = bool(parts)  # a half-streamed reply must not be retried: the caller already saw it
                raise
            return "".join(parts).strip()


def available_models(host=HOST):
    """Names of the chat models Ollama has installed (embedding-only models left out)."""
    with urllib.request.urlopen(f"{host}/api/tags", timeout=10) as resp:
        return sorted(m["name"] for m in json.load(resp)["models"] if "embed" not in m["name"])
