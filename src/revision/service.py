"""Smart Revision: a short, adaptive session on one weak concept, built from what the learner model knows.

    learner model -> weakest concept (+ why)  -> retrieve its course material once, reuse it
        -> question at a level that fits the student  (recall -> understanding -> application -> reasoning -> code)
        -> the student's answer is analysed (solid / partial / misconception / unclear)
              solid          -> confirm, then a harder or related question
              partial        -> acknowledge, name the gap, a follow-up on the gap
              misconception  -> correct it plainly, then a simpler question that re-tests the idea
              unclear        -> a simpler explanation and the question again in easier words
        -> two misses in a row on the concept -> step back to its weakest prerequisite, then come back and reassess
        -> every answer updates the learner model; the session ends with a deterministic summary of what changed

The session logic (which concept, which level, when to step back, when to stop) is plain code, so it is testable without
a model. The model only writes the words: the question, the feedback, the explanation. It is grounded exactly like the
tutor: same policy, same reference-material block, same citation validation. A question is built from the student's own
earlier doubts, the misconceptions on record, the concept's prerequisites and the retrieved course material, never from
nothing; questions already asked are listed so they are not repeated.

Like the tutor service, state changes are committed only after the model call succeeds, so a failed call can be retried.
"""
import re
from dataclasses import dataclass, field

from src.learner import taxonomy
from src.tutor.controller import ANALYZE, Session, build_prompt, is_unsure, parse_analysis, sources, validated
from src.tutor.service import TutorInputError, WANTS_ANSWER

LEVELS = ("recall", "understanding", "application", "reasoning", "code")
DIFFICULTY = {"recall": "easy", "understanding": "easy", "application": "medium", "reasoning": "hard", "code": "hard"}
DEFAULT_STEPS = 5
STEP_BACK_AFTER = 2  # consecutive non-solid answers on a concept before stepping back to a prerequisite
NO_WEAK_CONCEPTS = ("There is nothing to revise yet. Ask the tutor a few questions about threads and synchronization "
                    "first, and the concepts you struggle with will show up here.")

QUESTION = {
    "recall": "Ask the student ONE short recall question about the concept: what it is or what it does, answerable in "
              "one sentence. Do not include the answer.",
    "understanding": "Ask the student ONE question that makes them explain WHY or HOW the concept works in their own words, "
                     "not just define it. Do not include the answer.",
    "application": "Give a small concrete scenario (two or three named threads, a few steps) and ask the student ONE "
                   "question about what happens or what should be done. Do not include the answer.",
    "reasoning": "Ask the student ONE cross-question that probes a subtle point or a common misconception about the "
                 "concept: why something that looks sufficient is not, or what would break if a condition were removed. "
                 "Do not include the answer.",
    "code": "Show a short C/pthreads snippet (at most 12 lines) in a fenced code block, taken from the context when it has "
            "one, otherwise written to be consistent with the context and using only API behaviour the context states. "
            "Then ask ONE question about it: where the bug is, what the final value can be, or where the lock or "
            "semaphore belongs. Do not include the answer.",
}
FEEDBACK = {
    "solid": "The student's answer is correct. Confirm what is right in one or two sentences, citing the context as [S1], "
             "[S2], ... Then, as the last paragraph and nothing after it, {next}",
    "partial": "The student's answer is correct as far as it goes but misses the idea in the GAP below. Acknowledge what "
               "is right, name the missing idea and explain it in two or three sentences citing the context as [S1], "
               "[S2], ... Then, as the last paragraph and nothing after it, ask ONE short follow-up question about the "
               "missing idea.",
    "misconception": "The student's answer contains the misconception in the GAP below. Say plainly in your first sentence "
                     "that it is not correct, name what is wrong, and give the correct idea in two or three sentences "
                     "citing the context as [S1], [S2], ... Then, as the last paragraph and nothing after it, ask ONE "
                     "simpler question that re-tests the corrected idea.",
    "unclear": "The student could not answer or was unsure. Do not repeat your earlier wording: explain the idea more simply "
               "with one small example, citing the context as [S1], [S2], ... Then, as the last paragraph and nothing "
               "after it, ask the same question again in simpler words.",
    "final": "Give brief feedback on the student's last answer in two or three sentences, citing the context as [S1], "
             "[S2], ... If it was wrong or incomplete, state the correct idea. Do not ask a question.",
}
STEP_BACK = "We are stepping back to a concept this builds on: {label}. Say so in one short sentence before the question. "
COME_BACK = "We are returning to {label} to see whether it is clearer now. Say so in one short sentence before the question. "


@dataclass
class RevisionSession:
    concept: str  # what the session is about
    reason: str
    total: int = DEFAULT_STEPS
    focus: str = ""  # the concept being asked about right now (differs from `concept` during a prerequisite detour)
    level: str = "recall"
    answered: int = 0
    misses: int = 0  # consecutive non-solid answers on the current focus
    detoured: bool = False
    returning: bool = False
    question: str = ""  # the open question
    history: list = field(default_factory=list)
    asked: list = field(default_factory=list)
    context: list = field(default_factory=list)
    contexts: dict = field(default_factory=dict)  # (concept, wants_code) -> retrieved results, reused within the session
    start_confidence: dict = field(default_factory=dict)
    results: list = field(default_factory=list)  # [{"concept", "level", "analysis"}] one per answered question
    stage: str = "QUESTION"
    kind: str = "revision"

    def __post_init__(self):
        self.focus = self.focus or self.concept


@dataclass
class RevisionTurn:
    stage: str  # QUESTION | FEEDBACK | SUMMARY
    message: str
    feedback: str | None = None
    question: str | None = None
    concept: dict = field(default_factory=dict)
    reason: str = ""
    level: str = "recall"
    difficulty: str = "easy"
    progress: dict = field(default_factory=dict)
    analysis: dict | None = None
    learner_update: dict | None = None
    sources: list = field(default_factory=list)
    done: bool = False
    summary: dict | None = None


def split_question(message):
    """(feedback, question): the question is the last paragraph when it asks something; code blocks stay in the feedback."""
    text = (message or "").strip()
    fences = text.count("```")
    tail_start = text.rfind("```") + 3 if fences and fences % 2 == 0 else 0
    paras = [p for p in re.split(r"\n\s*\n", text[tail_start:]) if p.strip()]
    if not paras or "?" not in paras[-1]:
        return text or None, None
    question = paras[-1].strip()
    return (text[: text.rfind(question)].strip() or None), question


def start_level(confidence):
    """Where a session begins: unseen or weak concepts at recall, then understanding, application, reasoning."""
    if confidence is None or confidence < 0.4:
        return "recall"
    return "understanding" if confidence < 0.6 else "application" if confidence < 0.75 else "reasoning"


def _concept_info(cid):
    c = taxonomy.get(cid)
    return {"id": cid, "label": c.label, "topic": c.topic}


class RevisionService:
    def __init__(self, retriever, llm, learner, top_k=5, steps=DEFAULT_STEPS, is_relevant=None):
        self.retriever, self.llm, self.learner, self.top_k, self.steps = retriever, llm, learner, top_k, steps
        self.is_relevant = is_relevant or bool

    # ---------------------------------------------------------------- choosing what to revise
    def topics(self, limit=8):
        return self.learner.review_candidates(limit=limit)

    def choose(self, concept=None):
        """(concept id, why it was selected): the student's pick, or the weakest concept on record."""
        if concept:
            if concept not in taxonomy.CONCEPTS:
                raise TutorInputError("That concept is not part of this course.")
            reason = next((c["reason"] for c in self.learner.review_candidates(limit=50) if c["id"] == concept),
                          "You chose this concept to revise.")
            return concept, reason
        candidates = self.learner.review_candidates(limit=1)
        if not candidates:
            raise TutorInputError(NO_WEAK_CONCEPTS)
        return candidates[0]["id"], candidates[0]["reason"]

    def start(self, concept=None, emit=None):
        concept, reason = self.choose(concept)
        conf = self.learner.confidence(concept)
        session = RevisionSession(concept, reason, total=self.steps, level=start_level(conf))
        session.start_confidence = {concept: conf}
        return session, self._ask(session, session.focus, session.level, "", emit)

    # ---------------------------------------------------------------- answering
    def answer(self, session, text, emit=None):
        text = (text or "").strip()
        if session.stage == "SUMMARY":
            raise TutorInputError("This revision session is finished. Start a new one to continue.")
        if not text:
            raise TutorInputError("Type an answer first.")
        history = session.history + [("Student", text)]
        view = Session(taxonomy.label(session.focus), session.context, history=history)
        gives_up = bool(WANTS_ANSWER.search(text)) or is_unsure(text)
        analysis = ({"level": "unclear", "gap": "the student did not know"} if gives_up else
                    parse_analysis(self.llm(build_prompt(view, ANALYZE, student_facing=False,
                                                         learner=self._learner_context(session.focus)), json_mode=True)))
        if emit:
            emit("analysis", analysis)
        kind = analysis["level"]
        nxt = self._plan_next(session, kind, session.answered + 1)

        def commit():  # runs only after the model call has succeeded
            update = self.learner.record_evidence(session.focus, kind, analysis["gap"])
            session.answered += 1
            session.results.append({"concept": session.focus, "level": session.level, "analysis": analysis,
                                    "update": update})
            return update

        if nxt is None:  # the session ends: feedback on the last answer, then the summary
            return self._finish(session, view, analysis, commit, emit)
        return self._ask(session, nxt["focus"], nxt["level"], nxt["note"], emit, analysis=analysis, commit=commit,
                         feedback_kind=kind, history=history, gap=analysis["gap"], misses=nxt["misses"],
                         detoured=nxt["detoured"], returning=nxt["returning"])

    # ---------------------------------------------------------------- the deterministic part: what comes next
    def _plan_next(self, s, kind, answered):
        """The next (focus, level), or None when the session is over. Pure function of the state and the result."""
        misses = 0 if kind == "solid" else s.misses + 1
        if answered >= s.total:
            return None
        top = LEVELS[-1]
        if kind == "solid" and s.level == top and not s.returning and s.focus == s.concept:
            return None  # solid at the hardest level on the concept itself: nothing harder to ask
        # coming back from a prerequisite: reassess the original concept at application level
        if s.focus != s.concept:
            return {"focus": s.concept, "level": "application", "note": COME_BACK.format(label=taxonomy.label(s.concept)),
                    "misses": 0, "detoured": True, "returning": True}
        # two misses in a row: step back to the weakest prerequisite, once per session
        if misses >= STEP_BACK_AFTER and not s.detoured:
            prereq = self._weakest_prerequisite(s.concept)
            if prereq:
                return {"focus": prereq, "level": "understanding", "note": STEP_BACK.format(label=taxonomy.label(prereq)),
                        "misses": 0, "detoured": True, "returning": False}
        i = LEVELS.index(s.level)
        if kind == "solid":
            level = LEVELS[min(i + 1, len(LEVELS) - 1)]
        elif kind == "partial":
            level = s.level
        else:  # misconception, unclear: one level easier
            level = LEVELS[max(i - 1, 0)]
        return {"focus": s.focus, "level": level, "note": "", "misses": misses, "detoured": s.detoured, "returning": False}

    def _weakest_prerequisite(self, concept):
        """The direct prerequisite the learner is least sure of (unseen ones count as 0.45, between weak and developing)."""
        best = None
        for p in taxonomy.prerequisites(concept):
            conf = self.learner.confidence(p)
            conf = 0.45 if conf is None else conf
            if conf < 0.75 and (best is None or conf < best[0]):
                best = (conf, p)
        return best[1] if best else None

    # ---------------------------------------------------------------- the part that needs words
    def _context_for(self, session, concept, level, emit=None):
        wants_code = level == "code"
        key = (concept, wants_code)
        if key not in session.contexts:
            query = taxonomy.get(concept).query + (" code example" if wants_code else "")
            session.contexts[key] = self.retriever.search(query, top_k=self.top_k)
            if emit and session.contexts[key]:
                emit("sources", session.contexts[key])
        return session.contexts[key]

    def _learner_context(self, concept):
        s = self.learner.concept_state(concept)
        lines = [f"- {s['label']}: confidence {s['level']}"]
        if s["misconceptions"]:
            lines.append(f"- earlier misconception on record: {s['misconceptions'][-1]}")
        doubts = self.learner.doubt_texts(concept)
        if doubts:
            lines.append(f"- the student once asked: {doubts[-1]}")
        return "\n".join(lines)

    def _ask(self, session, focus, level, note, emit, analysis=None, commit=None, feedback_kind=None, history=None,
             gap="", misses=0, detoured=None, returning=None):
        context = self._context_for(session, focus, level, emit)
        if not self.is_relevant(context):
            raise TutorInputError("I couldn't find enough relevant course material to build a question on this concept.")
        next_task = QUESTION[level]
        if feedback_kind:
            task = FEEDBACK[feedback_kind].format(next=note + next_task) if feedback_kind == "solid" else note + FEEDBACK[feedback_kind]
        else:
            task = note + next_task
        extra = f"\n\nGAP\n{gap}" if gap and feedback_kind in ("partial", "misconception") else ""
        if feedback_kind in ("partial", "misconception", "unclear"):
            extra += f"\n\nQUESTION LEVEL\n{level}: {QUESTION[level]}"
        if session.asked:
            extra += "\n\nQUESTIONS ALREADY ASKED (do not repeat them)\n" + "\n".join(f"- {q}" for q in session.asked[-4:])
        view = Session(taxonomy.label(focus), context, history=list(history if history is not None else session.history))
        message = validated(self._generate(build_prompt(view, task, extra, learner=self._learner_context(focus)), len(context), emit),
                            len(context))
        feedback, question = split_question(message)
        if analysis is None:  # the very first question: the whole message is the question
            feedback, question = None, message
        # the model call succeeded: commit (learner evidence and counters first, then the new question)
        update = commit() if commit else None
        session.focus, session.level, session.context = focus, level, context
        session.question = question or message
        session.asked.append(session.question)
        session.history = view.history + [("Tutor", session.question)]
        if analysis is not None:
            session.misses, session.detoured, session.returning = misses, detoured, returning
        else:
            session.detoured = session.returning = False
        session.stage = "QUESTION"
        return RevisionTurn("QUESTION" if analysis is None else "FEEDBACK", message, feedback, question,
                            _concept_info(focus), session.reason, level, DIFFICULTY[level], self._progress(session),
                            analysis, update, sources(context))

    def _finish(self, session, view, analysis, commit, emit):
        message = validated(self._generate(build_prompt(view, FEEDBACK["final"], learner=self._learner_context(session.focus)),
                                           len(session.context), emit), len(session.context))
        update = commit()
        summary = self.summary(session)
        session.history = view.history + [("Tutor", message)]
        session.stage = "SUMMARY"
        return RevisionTurn("SUMMARY", f"{message}\n\n{summary['text']}", message, None, _concept_info(session.concept),
                            session.reason, session.level, DIFFICULTY[session.level], self._progress(session, done=True),
                            analysis, update, sources(session.context), True, summary)

    def _generate(self, prompt, n_sources, emit):
        return self.llm(prompt, on_token=lambda t: emit("token", t)) if emit else self.llm(prompt)

    def _progress(self, session, done=False):
        return {"step": min(session.answered + (0 if done else 1), session.total), "total": session.total}

    # ---------------------------------------------------------------- deterministic summary
    def summary(self, session):
        """What the session did to the learner model, in words built from recorded facts only."""
        solid = sum(r["analysis"]["level"] == "solid" for r in session.results)
        concepts = []
        for cid in dict.fromkeys(r["concept"] for r in session.results):
            before = session.start_confidence.get(cid)
            if before is None:
                first = next(r["update"] for r in session.results if r["concept"] == cid)
                before = round(first["confidence"] - first["change"], 4)
            after = self.learner.confidence(cid)
            concepts.append({"id": cid, "label": taxonomy.label(cid), "before": before, "after": after,
                             "level": self.learner.level(cid)})
        lines = [f"Revision complete: {solid} of {session.answered} answers were fully correct."]
        for c in concepts:
            lines.append(f"- {c['label']}: confidence {c['before']:.2f} → {c['after']:.2f} ({c['level']})")
        remaining = [c for c in self.learner.review_candidates(limit=3) if c["id"] != session.concept]
        if self.learner.level(session.concept) != "strong":
            lines.append(f"{taxonomy.label(session.concept)} is not strong yet; another round is worth it.")
        elif remaining:
            lines.append(f"Next worth revising: {remaining[0]['label']}.")
        return {"text": "\n".join(lines), "correct": solid, "answered": session.answered, "concepts": concepts}
