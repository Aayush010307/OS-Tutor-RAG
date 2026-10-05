"""Local LLM backend for the tutor (Phase 4): Ollama's HTTP API, standard library only.

    llm = OllamaLLM("qwen3:8b")
    llm("prompt")                          # full reply as a string
    llm("prompt", json_mode=True)          # Ollama constrains the reply to valid JSON
    llm("prompt", on_token=print)          # streams tokens to the callback, returns the full reply

Temperature 0 and a fixed seed make replies repeatable for a given model, prompt and Ollama version.
`think: false` turns off qwen3's hidden reasoning (slow on a laptop); models without it ignore the flag.
"""
import json
import urllib.request

HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:8b"


class OllamaLLM:
    def __init__(self, model=DEFAULT_MODEL, host=HOST, temperature=0.0, seed=42, num_ctx=8192, timeout=600):
        self.model, self.host, self.timeout = model, host, timeout
        self.options = {"temperature": temperature, "seed": seed, "num_ctx": num_ctx}

    def __call__(self, prompt, json_mode=False, on_token=None):
        body = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "stream": on_token is not None,
                "think": False, "options": self.options} | ({"format": "json"} if json_mode else {})
        req = urllib.request.Request(f"{self.host}/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            if not body["stream"]:
                return json.load(resp)["message"]["content"].strip()
            parts = []
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
            return "".join(parts).strip()


def available_models(host=HOST):
    """Names of the chat models Ollama has installed (embedding-only models left out)."""
    with urllib.request.urlopen(f"{host}/api/tags", timeout=10) as resp:
        return sorted(m["name"] for m in json.load(resp)["models"] if "embed" not in m["name"])
