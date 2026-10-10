"""Saved conversations for the "recent conversations" list: a small JSON file of transcripts.

This is chat history only. It is a different thing from the learner model (what the system believes the student
knows), which stores structured concept records, not messages. Transcripts hold the student's own words, so the file
lives under data/learner/ (git-ignored). Writes are atomic and thread-safe; a missing or unreadable file is an empty
history, never an error for the student.
"""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

KEEP_CONVERSATIONS = 50
SOURCE_FIELDS = ("ref", "chunk_id", "label", "display", "location", "section", "preview")


class ConversationStore:
    def __init__(self, path=None, clock=lambda: datetime.now(timezone.utc)):
        self.path, self.clock, self.lock = (Path(path) if path else None), clock, threading.RLock()
        self.data = self._load()

    def _load(self):
        if self.path and self.path.is_file():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data.get("conversations"), dict):
                    return data
            except (OSError, json.JSONDecodeError):
                pass
        return {"version": 1, "conversations": {}}

    def _save(self):
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8", newline="\n")
        os.replace(tmp, self.path)

    def append(self, conv_id, mode, title, student_text, turn):
        """Add the student's message (if any) and the tutor's turn to a conversation, creating it on first use."""
        now = self.clock().isoformat(timespec="seconds")
        with self.lock:
            conv = self.data["conversations"].setdefault(
                conv_id, {"id": conv_id, "title": " ".join(title.split())[:80], "mode": mode, "created": now, "turns": []})
            if student_text:
                conv["turns"].append({"role": "student", "text": student_text, "time": now})
            conv["turns"].append({"role": "tutor", "text": turn.message, "stage": turn.stage, "time": now,
                                  "sources": [{k: s.get(k) for k in SOURCE_FIELDS} for s in turn.sources]})
            conv["updated"] = now
            if len(self.data["conversations"]) > KEEP_CONVERSATIONS:
                oldest = sorted(self.data["conversations"].values(), key=lambda c: c["updated"])[0]["id"]
                del self.data["conversations"][oldest]
            self._save()

    def list(self, limit=20):
        with self.lock:
            convs = sorted(self.data["conversations"].values(), key=lambda c: c["updated"], reverse=True)[:limit]
            return [{k: c[k] for k in ("id", "title", "mode", "updated")} for c in convs]

    def get(self, conv_id):
        with self.lock:
            conv = self.data["conversations"].get(conv_id)
            return json.loads(json.dumps(conv)) if conv else None
