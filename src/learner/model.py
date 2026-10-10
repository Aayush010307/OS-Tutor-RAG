"""The learner model: what the system believes the student understands, misunderstands or needs to revise.

This is neither the course material (that is the retriever's job) nor the chat history (what was said). It keeps one
small record per concept from `taxonomy`, updated only by meaningful interactions:

    doubt      the student asked about the concept          -> remembered, mastery barely moves
    evidence   the student answered a check / revision question, or asked for another explanation

A deterministic exponential update is enough (no ML): each piece of evidence has a score in [0, 1] and moves the
confidence a fixed fraction of the way towards it.

    confidence' = confidence + ALPHA * (score - confidence)        start 0.5 (PRIOR); a doubt alone starts at 0.4

    solid 1.0   partial 0.55   unclear 0.15   misconception 0.0   re_explain 0.25 (lower weight)

so one solid answer gives 0.70 (developing) and two give 0.82 (strong); one misconception gives 0.30 (weak).
Levels: unknown (never seen) | weak < 0.40 | developing < 0.75 | strong. Everything is stored in one JSON file,
written atomically, safe for the threaded server. `clock` is injectable so tests control time.
"""
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import taxonomy

PRIOR, DOUBT_START, ALPHA = 0.5, 0.4, 0.4
EVIDENCE = {"solid": (1.0, ALPHA), "partial": (0.55, ALPHA), "unclear": (0.15, ALPHA),
            "misconception": (0.0, ALPHA), "re_explain": (0.25, 0.2)}
WEAK_BELOW, STRONG_FROM = 0.40, 0.75
KEEP = {"evidence": 20, "doubts": 10, "misconceptions": 5}
VERSION = 1


def level_of(confidence):
    if confidence is None:
        return "unknown"
    return "weak" if confidence < WEAK_BELOW else "strong" if confidence >= STRONG_FROM else "developing"


def _now():
    return datetime.now(timezone.utc)


class LearnerModel:
    def __init__(self, path=None, user_id="default", clock=_now):
        self.path, self.user_id, self.clock = (Path(path) if path else None), user_id, clock
        self.lock = threading.RLock()
        self.data = self._load()

    # ------------------------------------------------------------ persistence
    def _load(self):
        if self.path and self.path.is_file():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if data.get("version") == VERSION and isinstance(data.get("users"), dict):
                    return data
            except (OSError, json.JSONDecodeError):
                pass
            try:  # unreadable or foreign file: keep it aside rather than overwrite it
                self.path.replace(self.path.with_suffix(".corrupt"))
            except OSError:
                pass
        return {"version": VERSION, "users": {}}

    def _save(self):
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
        os.replace(tmp, self.path)

    def _concepts(self):
        return self.data["users"].setdefault(self.user_id, {"concepts": {}})["concepts"]

    def _entry(self, concept_id, create=False):
        if concept_id not in taxonomy.CONCEPTS:
            raise KeyError(f"unknown concept {concept_id!r}")
        concepts = self._concepts()
        if concept_id not in concepts and create:
            concepts[concept_id] = {"confidence": None, "attempts": 0, "correct": 0, "misconceptions": [], "doubts": [],
                                    "evidence": [], "last_interaction": None}
        return concepts.get(concept_id)

    def _stamp(self, entry):
        entry["last_interaction"] = self.clock().isoformat(timespec="seconds")
        return entry["last_interaction"]

    # ------------------------------------------------------------ updates
    def record_doubt(self, concept_ids, text):
        """The student asked about these concepts. Remembers the doubt; creates the concept at DOUBT_START if it is new,
        otherwise leaves its confidence alone. Returns one update per concept."""
        updates = []
        with self.lock:
            for cid in concept_ids:
                entry = self._entry(cid, create=True)
                before = entry["confidence"]
                if before is None:
                    entry["confidence"] = DOUBT_START
                entry["doubts"] = (entry["doubts"] + [{"text": (text or "").strip()[:300], "time": self._stamp(entry)}])[-KEEP["doubts"]:]
                updates.append(self._update(cid, entry, before))
            self._save()
        return updates

    def record_evidence(self, concept_id, kind, gap=""):
        """The student showed (or failed to show) understanding of a concept. `kind` is an EVIDENCE key; for a
        misconception the model's one-sentence `gap` is remembered as the misconception."""
        if kind not in EVIDENCE:
            raise ValueError(f"unknown evidence kind {kind!r}; expected one of {sorted(EVIDENCE)}")
        score, alpha = EVIDENCE[kind]
        with self.lock:
            entry = self._entry(concept_id, create=True)
            before = entry["confidence"]
            base = PRIOR if before is None else before
            entry["confidence"] = round(base + alpha * (score - base), 4)
            if kind != "re_explain":
                entry["attempts"] += 1
                entry["correct"] += kind == "solid"
            if kind == "misconception" and (gap or "").strip():
                gap = gap.strip()[:240]
                entry["misconceptions"] = ([m for m in entry["misconceptions"] if m != gap] + [gap])[-KEEP["misconceptions"]:]
            entry["evidence"] = (entry["evidence"] + [{"kind": kind, "time": self._stamp(entry)}])[-KEEP["evidence"]:]
            update = self._update(concept_id, entry, before)
            self._save()
        return update

    @staticmethod
    def _update(concept_id, entry, before):
        after = entry["confidence"]
        return {"concept_id": concept_id, "label": taxonomy.label(concept_id), "level": level_of(after),
                "confidence": after, "change": round(after - (before if before is not None else after), 4)}

    # ------------------------------------------------------------ reading
    def concept_state(self, concept_id):
        with self.lock:
            entry = self._entry(concept_id) or {}
        c = taxonomy.get(concept_id)
        conf = entry.get("confidence")
        return {"id": concept_id, "label": c.label, "topic": c.topic, "level": level_of(conf), "confidence": conf,
                "attempts": entry.get("attempts", 0), "misconceptions": list(entry.get("misconceptions", [])),
                "doubts": len(entry.get("doubts", [])), "last_interaction": entry.get("last_interaction"),
                "related_concepts": taxonomy.related(concept_id)}

    def profile(self):
        with self.lock:
            seen = list(self._concepts())
            states = [self.concept_state(cid) for cid in seen]
            doubts = sorted(({"concept_id": cid, **d} for cid in seen for d in self._concepts()[cid]["doubts"]),
                            key=lambda d: d["time"], reverse=True)[:10]
        summary = {lv: sum(s["level"] == lv for s in states) for lv in ("weak", "developing", "strong")}
        summary["unknown"] = len(taxonomy.CONCEPTS) - len(states)
        return {"summary": summary, "concepts": sorted(states, key=lambda s: (s["confidence"] is None, s["confidence"] or 0)),
                "recent_doubts": doubts}

    def doubt_texts(self, concept_id, n=2):
        """The student's own most recent questions about a concept (newest last): material for a revision question."""
        with self.lock:
            entry = self._entry(concept_id) or {}
        return [d["text"] for d in entry.get("doubts", [])][-n:]

    def level(self, concept_id):
        return self.concept_state(concept_id)["level"]

    def confidence(self, concept_id):
        return self.concept_state(concept_id)["confidence"]

    def review_candidates(self, limit=5):
        """Concepts worth revising, most needed first, each with the reason in plain words. A concept qualifies when it
        has been seen and is not yet strong. Priority = how low the confidence is, plus a bump per remembered
        misconception, plus a small bump for recent activity (so what the student just struggled with comes first)."""
        now, out = self.clock(), []
        with self.lock:
            for cid, entry in self._concepts().items():
                conf = entry["confidence"]
                if conf is None or conf >= STRONG_FROM:
                    continue
                last = datetime.fromisoformat(entry["last_interaction"]) if entry["last_interaction"] else None
                recent = 0.1 if last and now - last <= timedelta(days=1) else 0.0
                priority = (1 - conf) + 0.15 * min(len(entry["misconceptions"]), 3) + recent
                state = self.concept_state(cid)
                out.append(state | {"priority": round(priority, 4), "reason": self._reason(state, entry)})
        out.sort(key=lambda s: (-s["priority"], s["last_interaction"] or "", s["id"]))
        return out[:limit]

    @staticmethod
    def _reason(state, entry):
        facts = []
        if entry["misconceptions"]:
            facts.append(f"you had a misconception: {entry['misconceptions'][-1]}")
        wrong = sum(e["kind"] in ("misconception", "unclear") for e in entry["evidence"])
        if wrong:
            facts.append(f"{wrong} of your answers on it {'was' if wrong == 1 else 'were'} wrong or unsure")
        if entry["evidence"] and any(e["kind"] == "re_explain" for e in entry["evidence"]):
            facts.append("you asked for it to be explained again")
        if entry["doubts"]:
            n = len(entry["doubts"])
            facts.append(f"you asked about it {n} time{'s' if n != 1 else ''}")
        if not facts:
            facts.append(f"your confidence in it is {state['level']}")
        return facts[0][0].upper() + facts[0][1:] + ("; " + "; ".join(facts[1:]) if len(facts) > 1 else "") + "."
