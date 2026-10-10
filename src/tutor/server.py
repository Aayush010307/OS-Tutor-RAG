"""Student web app for the OS tutor: a standard-library web server around the tutor service. Contract: API_CONTRACT.md.

    python3 -m src.tutor.server [--model qwen3:8b] [--host 127.0.0.1] [--port 8000]
    then open http://localhost:8000

Configuration comes from the environment (`src/config.py`, optional `.env` file): which LLM (a local or remote Ollama via
OLLAMA_BASE_URL, or LLM_PROVIDER=mock), tutor mode, retrieval and reranker settings, where the learner data lives. Command
line flags override the environment. The Ollama server may be on another machine; nothing here assumes localhost.

JSON endpoints:
    GET  /                          the page (web/index.html)
    GET  /api/models                {"models": [...], "default": "<model>", "provider"}  (+ "error" if Ollama is unreachable)
    GET  /api/health/llm            is the configured LLM usable? (never contains the Ollama address)
    GET  /api/learner/profile       what the learner model believes, per concept
    GET  /api/revision/topics       concepts worth revising, with the reason for each
    GET  /api/sources/<chunk_id>    one retrieved passage in full
    GET  /api/conversations[/<id>]  saved conversations
Streaming endpoints (server-sent events, one JSON object per `data:` line; POST):
    /api/start  {"question", "model"}              session, sources, token..., turn
    /api/reply  {"session_id", "text", "intent"}   analysis, sources, token..., turn
    /api/revision/start  {"concept"?, "model"?}      session, sources, token..., turn   (Smart Revision)
    /api/revision/answer {"session_id", "text"}      analysis, sources, token..., turn
Event types: session {id, model, mode}, sources [Source], analysis {level, gap}, token {text}, turn {...}, error
{message, code}. Error messages are safe to show: they never carry exception text, addresses or paths.

Every finished turn is appended to data/tutor_logs/<date>.jsonl (question, reply, stage, analysis, sources) for the
pilot and the quality review. Sessions live in memory and are lost on restart; transcripts and the learner model persist.
"""
import argparse
import json
import sys
import threading
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from src.config import ROOT, ConfigError, Settings, load_dotenv
from src.learner import taxonomy
from src.learner.model import LearnerModel
from src.revision.service import RevisionService

from .controller import TutorController, sources
from .conversations import ConversationStore
from .llm import LLMError, available_models, health_check, make_llm
from .service import TutorInputError, TutorService

PAGE = ROOT / "web" / "index.html"
LOGS = ROOT / "data" / "tutor_logs"
LLM_CODES = {"unavailable": "llm_unavailable", "timeout": "llm_timeout", "model_missing": "model_missing",
             "bad_response": "llm_bad_response"}
MAX_BODY = 64 * 1024


def error_payload(exc):
    """What the student sees for a failure: a fixed, safe message and a machine-readable code. Exception text, addresses
    and file paths never leave the server (they go to its log)."""
    if isinstance(exc, LLMError):
        return {"message": str(exc), "code": LLM_CODES[exc.kind]}
    if isinstance(exc, TutorInputError):
        return {"message": str(exc), "code": "bad_request"}
    return {"message": "Something went wrong on our side. Please try again.", "code": "internal"}


class Locked:
    """Serialises retrieval: the local Qdrant client and the ONNX model are shared by all request threads."""
    def __init__(self, retriever):
        self.retriever, self.lock = retriever, threading.Lock()

    def search(self, query, top_k=5):
        with self.lock:
            return self.retriever.search(query, top_k=top_k)

    def is_relevant(self, results):
        check = getattr(self.retriever, "is_relevant", None)
        return check(results) if check else bool(results)

    def get_chunk(self, chunk_id):
        finder = getattr(self.retriever, "get_chunk", None)
        with self.lock:
            return finder(chunk_id) if finder else None


@dataclass
class Live:
    tutor: object  # TutorService / TutorController, or RevisionService when kind == "revision"
    session: object
    model: str
    kind: str = "tutor"


class App:
    def __init__(self, retriever, default_model, settings=None, learner=None, conversations=None):
        self.settings = settings or Settings()
        self.retriever, self.default_model = Locked(retriever), default_model
        self.learner = learner if learner is not None else LearnerModel()
        self.conversations = conversations if conversations is not None else ConversationStore()
        self.sessions, self.lock = {}, threading.Lock()  # in-memory, unbounded; fine for a demo or pilot

    def tutor(self, model):
        llm = make_llm(self.settings, model)
        if self.settings.tutor_mode == "socratic":
            return TutorController(self.retriever, llm, top_k=self.settings.final_context_k)
        return TutorService(self.retriever, llm, learner=self.learner, top_k=self.settings.final_context_k,
                            is_relevant=self.retriever.is_relevant)

    def revision(self, model):
        return RevisionService(self.retriever, make_llm(self.settings, model), self.learner,
                               top_k=self.settings.final_context_k, steps=self.settings.revision_steps,
                               is_relevant=self.retriever.is_relevant)

    def log_revision(self, session_id, model, session, turn, student_text):
        LOGS.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        rec = {"time": now.isoformat(timespec="seconds"), "session_id": session_id, "model": model, "kind": "revision",
               "concept": session.concept, "focus": session.focus, "level": turn.level, "student": student_text,
               "stage": turn.stage, "tutor": turn.message, "analysis": turn.analysis,
               "sources": [x["chunk_id"] for x in turn.sources]}
        with self.lock, open(LOGS / f"{now.date()}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

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


def concept_info(concept_id):
    c = taxonomy.get(concept_id)
    return {"id": concept_id, "label": c.label, "topic": c.topic}


def revision_payload(turn):
    return {"stage": turn.stage, "message": turn.message, "feedback": turn.feedback, "question": turn.question,
            "concept": turn.concept, "reason": turn.reason, "level": turn.level, "difficulty": turn.difficulty,
            "progress": turn.progress, "analysis": turn.analysis, "learner_update": turn.learner_update,
            "sources": turn.sources, "done": turn.done, "summary": turn.summary}


def turn_payload(turn, get_chunk=None):
    """`sources` is this turn's own provenance: exactly the passages its reply was generated from, numbered as its
    [S1], [S2], ... citations, in the `sources` event's card schema (passage text looked up by chunk_id). It is [] when
    the reply used no passage (NO_CONTEXT, "got it")."""
    def card(s):
        chunk = get_chunk(s["chunk_id"]) if get_chunk else None
        return dict(s) | ({"text": chunk["text"]} if chunk else {})
    return {"stage": turn.stage, "message": turn.message, "analysis": turn.analysis, "mode": turn.mode,
            "follow_up": turn.follow_up, "concepts": turn.concepts, "tutor_state": turn.tutor_state,
            "learner_update": turn.learner_update, "actions": turn.actions,
            "sources": [card(s) for s in turn.sources]}


class Handler(BaseHTTPRequestHandler):
    app: App = None

    def log_message(self, fmt, *args):  # quieter console: one line per API call
        if self.path.startswith("/api/"):
            sys.stderr.write(f"{self.command} {self.path} {args[1] if len(args) > 1 else ''}\n")

    def _bytes(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._bytes(code, json.dumps(obj).encode(), "application/json")

    # ------------------------------------------------------------------ GET
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        app = self.app
        try:
            if path in ("/", "/index.html"):
                return self._bytes(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if path == "/api/models":
                try:
                    models, err = available_models(app.settings.ollama_base_url), None
                except LLMError as e:
                    models, err = [], str(e)
                if app.settings.llm_provider == "mock":
                    models, err = ["mock"], None
                return self._json(200, {"models": models, "default": app.default_model,
                                        "provider": app.settings.llm_provider} | ({"error": err} if err else {}))
            if path in ("/api/health/llm", "/health/llm"):
                return self._json(200, health_check(app.settings))
            if path == "/api/learner/profile":
                return self._json(200, app.learner.profile())
            if path == "/api/revision/topics":
                cands = app.learner.review_candidates(limit=8)
                return self._json(200, {"count": len(cands), "concepts": [
                    {k: c[k] for k in ("id", "label", "topic", "level", "confidence", "reason")} for c in cands]})
            if path.startswith("/api/sources/"):
                chunk = app.retriever.get_chunk(unquote(path[len("/api/sources/"):]))
                if not chunk:
                    return self._json(404, {"error": "unknown source"})
                return self._json(200, source_cards([chunk])[0])
            if path == "/api/conversations":
                return self._json(200, {"conversations": app.conversations.list()})
            if path.startswith("/api/conversations/"):
                conv = app.conversations.get(unquote(path[len("/api/conversations/"):]))
                return self._json(200, conv) if conv else self._json(404, {"error": "unknown conversation"})
            return self._json(404, {"error": "not found"})
        except Exception as e:  # a failing GET must not take the page down
            self._fail(e)
            self._json(500, error_payload(e))

    def _fail(self, exc):
        sys.stderr.write(f"error: {exc.__class__.__name__}: {getattr(exc, 'detail', '') or exc}\n")
        if self.app.settings.debug:
            traceback.print_exc()

    # ------------------------------------------------------------------ POST (server-sent events)
    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", 0))
            if size > MAX_BODY:
                return self._json(413, {"error": "request too large"})
            data = json.loads(self.rfile.read(size) or b"{}")
            if not isinstance(data, dict):
                raise json.JSONDecodeError("object expected", "", 0)
        except (json.JSONDecodeError, ValueError):
            return self._json(400, {"error": "body must be a JSON object"})
        if self.path not in ("/api/start", "/api/reply", "/api/revision/start", "/api/revision/answer"):
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

        try:
            if self.path.startswith("/api/revision/"):
                self._revision_turn(data, send, emit)
            else:
                self._tutor_turn(data, send, emit)
        except (BrokenPipeError, ConnectionResetError):
            pass  # the student closed the page mid-answer
        except Exception as e:  # keep the stream well-formed for the page
            self._fail(e)
            send("error", error_payload(e))

    def _revision_turn(self, data, send, emit):
        """Smart Revision: /api/revision/start {"concept"?, "model"?} and /api/revision/answer {"session_id", "text"}."""
        app = self.app
        if self.path == "/api/revision/start":
            model = data.get("model") or app.default_model
            service = app.revision(model)
            concept, reason = service.choose(data.get("concept") or None)
            sid = uuid.uuid4().hex
            send("session", {"id": sid, "kind": "revision", "model": model, "concept": concept_info(concept),
                             "reason": reason, "total_steps": service.steps})
            session, turn = service.start(concept, emit=emit)
            with app.lock:
                app.sessions[sid] = Live(service, session, model, "revision")
            student = None
        else:
            sid, student = data.get("session_id"), str(data.get("text") or "").strip()
            with app.lock:
                live = app.sessions.get(sid)
            if not live or live.kind != "revision":
                return send("error", {"message": "This revision session has expired. Start a new one.", "code": "expired"})
            if not student:
                return send("error", {"message": "Type an answer first.", "code": "bad_request"})
            service, session, model = live.tutor, live.session, live.model
            turn = service.answer(session, student, emit=emit)
        send("turn", revision_payload(turn))
        app.log_revision(sid, model, session, turn, student)

    def _tutor_turn(self, data, send, emit):
        app = self.app
        if self.path == "/api/start":
            question, model = str(data.get("question", "")).strip(), data.get("model") or app.default_model
            if not question:
                return send("error", {"message": "Type a question first.", "code": "bad_request"})
            sid = uuid.uuid4().hex
            tutor = app.tutor(model)
            send("session", {"id": sid, "model": model, "mode": app.settings.tutor_mode})
            session, turn = tutor.start(question, emit=emit)
            with app.lock:
                app.sessions[sid] = Live(tutor, session, model)
            student = None
        else:
            sid, student = data.get("session_id"), str(data.get("text") or "").strip()
            intent = data.get("intent") or None
            with app.lock:
                live = app.sessions.get(sid)
            if not live or live.kind != "tutor":
                return send("error", {"message": "This conversation has expired. Ask your question again.",
                                      "code": "expired"})
            tutor, session, model = live.tutor, live.session, live.model
            if session.stage == "DONE":
                return send("error", {"message": "This topic is finished. Ask a new question to continue.",
                                      "code": "bad_request"})
            if not student and not intent:
                return send("error", {"message": "Type an answer first.", "code": "bad_request"})
            if isinstance(tutor, TutorService):
                turn = tutor.respond(session, student, intent=intent, emit=emit)
            else:
                turn = tutor.respond(session, student, emit=emit)
        send("turn", turn_payload(turn, app.retriever.get_chunk))
        app.log(sid, model, session, turn, student)
        if student is None:  # first turn: the question itself is the student's message
            said = question
        else:
            said = student or f"({intent.replace('_', ' ')})"
        app.conversations.append(sid, turn.mode, question if student is None else session.question, said, turn)


def build_app(settings, default_model=None):
    from src.retrieval.pipeline import build_retriever
    retriever = build_retriever(settings)
    return retriever, App(retriever, default_model or settings.ollama_model, settings,
                          LearnerModel(settings.learner_db_path),
                          ConversationStore(settings.learner_db_path.with_name("conversations.json")))


def main(argv=None):
    load_dotenv()
    try:
        settings = Settings.from_env()
    except ConfigError as e:
        sys.exit(f"configuration error: {e}")
    ap = argparse.ArgumentParser(description="OS tutor web app")
    ap.add_argument("--model", default="mock" if settings.llm_provider == "mock" else settings.ollama_model)
    ap.add_argument("--host", default=settings.app_host)
    ap.add_argument("--port", type=int, default=settings.app_port)
    args = ap.parse_args(argv)
    retriever, app = build_app(settings, args.model)
    try:
        Handler.app = app
        server = ThreadingHTTPServer((args.host, args.port), Handler)
        health = health_check(settings)
        print(f"OS tutor running at http://{args.host}:{args.port}  (mode {settings.tutor_mode}, "
              f"LLM {health['provider']}:{args.model}; Ctrl+C to stop)")
        if not health["ok"]:
            print(f"warning: {health['message']}", file=sys.stderr)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    finally:
        retriever.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
