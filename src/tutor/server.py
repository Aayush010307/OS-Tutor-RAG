"""Student chat page for the OS tutor: a standard-library web server around the tutor controller.

    /usr/local/bin/python3 -m src.tutor.server [--model qwen3:8b] [--port 8000]
    then open http://localhost:8000

Ollama must be running locally (`ollama serve`, or the Ollama app). Retrieval is the E2 hybrid retriever.

API (both POSTs answer with a server-sent event stream, one JSON object per `data:` line):
    GET  /                      the chat page (web/index.html)
    GET  /api/models            {"models": [...], "default": "<model>"}
    POST /api/start  {"question", "model"}    -> session, sources, tokens, turn
    POST /api/reply  {"session_id", "text"}   -> analysis, tokens, turn
Event types: session {id, model}, sources [{ref, chunk_id, filename, section, location, text}], analysis {level, gap},
token {text}, turn {stage, message, analysis}, error {message}.

Every finished turn is appended to data/tutor_logs/<date>.jsonl (question, reply, stage, analysis, sources) for the
pilot and the quality review. Sessions live in memory and are lost on restart.
"""
import argparse
import json
import sys
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src.retrieval.hybrid import HybridRRFRetriever

from .controller import TutorController, sources
from .llm import DEFAULT_MODEL, OllamaLLM, available_models

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "web" / "index.html"
LOGS = ROOT / "data" / "tutor_logs"


class Locked:
    """Serialises retrieval: the local Qdrant client and the ONNX model are shared by all request threads."""
    def __init__(self, retriever):
        self.retriever, self.lock = retriever, threading.Lock()

    def search(self, query, top_k=5):
        with self.lock:
            return self.retriever.search(query, top_k=top_k)


class App:
    def __init__(self, retriever, default_model):
        self.retriever, self.default_model = Locked(retriever), default_model
        self.sessions, self.lock = {}, threading.Lock()  # ponytail: in-memory, unbounded; fine for a demo or pilot

    def tutor(self, model):
        return TutorController(self.retriever, OllamaLLM(model))

    def log(self, session_id, model, session, turn, student_text):
        LOGS.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        rec = {"time": now.isoformat(timespec="seconds"), "session_id": session_id, "model": model,
               "question": session.question, "student": student_text, "stage": turn.stage, "tutor": turn.message,
               "analysis": turn.analysis, "sources": [s["chunk_id"] for s in turn.sources]}
        with self.lock, open(LOGS / f"{now.date()}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def source_cards(context):
    return [s | {"text": r["text"]} for s, r in zip(sources(context), context)]


class Handler(BaseHTTPRequestHandler):
    app: App = None

    def log_message(self, fmt, *args):  # quieter console: one line per API call
        if self.path.startswith("/api/"):
            sys.stderr.write(f"{self.command} {self.path} {args[1] if len(args) > 1 else ''}\n")

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = PAGE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/models":
            try:
                models = available_models()
            except OSError:
                models = []
            self._json(200, {"models": models, "default": self.app.default_model})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "body must be JSON"})
        if self.path not in ("/api/start", "/api/reply"):
            return self._json(404, {"error": "not found"})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def send(kind, payload):
            self.wfile.write(b"data: " + json.dumps({"type": kind, "data": payload}).encode() + b"\n\n")
            self.wfile.flush()

        def emit(kind, payload):
            send(kind, source_cards(payload) if kind == "sources" else {"text": payload} if kind == "token" else payload)

        app = self.app
        try:
            if self.path == "/api/start":
                question, model = str(data.get("question", "")).strip(), data.get("model") or app.default_model
                if not question:
                    return send("error", {"message": "Type a question first."})
                sid = uuid.uuid4().hex
                send("session", {"id": sid, "model": model})
                tutor = app.tutor(model)
                session, turn = tutor.start(question, emit=emit)
                with app.lock:
                    app.sessions[sid] = (tutor, session, model)
                student = None
            else:
                sid, student = data.get("session_id"), str(data.get("text", "")).strip()
                with app.lock:
                    found = app.sessions.get(sid)
                if not found:
                    return send("error", {"message": "This conversation has expired. Ask your question again."})
                tutor, session, model = found
                if session.stage == "DONE":
                    return send("error", {"message": "This topic is finished. Ask a new question to continue."})
                if not student:
                    return send("error", {"message": "Type an answer first."})
                turn = tutor.respond(session, student, emit=emit)
            send("turn", {"stage": turn.stage, "message": turn.message, "analysis": turn.analysis})
            app.log(sid, model, session, turn, student)
        except (BrokenPipeError, ConnectionResetError):
            pass  # the student closed the page mid-answer
        except OSError as e:  # Ollama not running, model missing, timeout
            send("error", {"message": f"The language model is not reachable ({e}). Start Ollama and try again."})
        except Exception as e:  # keep the stream well-formed for the page
            send("error", {"message": f"Something went wrong: {e}"})


def main(argv=None):
    ap = argparse.ArgumentParser(description="OS tutor chat page")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args(argv)
    with HybridRRFRetriever.open() as retriever:
        Handler.app = App(retriever, args.model)
        server = ThreadingHTTPServer((args.host, args.port), Handler)
        print(f"OS tutor running at http://{args.host}:{args.port}  (model {args.model}; Ctrl+C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
