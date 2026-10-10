"""Answer-first conversational tutor (product mode). The Socratic `TutorController` stays as the research mode.

    student question -> retrieve -> ANSWER (grounded, cited)            the conversation stays open
       "I still don't understand" / "simpler" / "give me an analogy"   -> the same idea in a different representation
       "test my understanding"                                          -> CHECK (one question, stays pending)
       the student's answer to a check                                  -> FEEDBACK
             solid -> confirm   partial -> clarify   misconception -> correct
             unclear -> simplify: a nudge and an easier first-step question, never the check's answer
       a hint request while a check is pending                          -> HINT; the check stays pending
       a new question while a check is pending                          -> answered on its own; the check stays pending

Nothing is forced: no question follows an answer unless the student asks for one or the deterministic rule offers one
(the first answer, then at most every third). Which of these a message is, is decided by rules (`detect_intent`,
`is_new_question`), never by the model, so the flow is testable without an LLM. The model only writes the words and,
for a check answer, judges understanding (the same analysis prompt as the Socratic tutor).

When nothing relevant is retrieved the service says so itself instead of calling the model, so it cannot invent an
answer. Explanations are grounded exactly like the Socratic mode: same policy, grounding, style and citation
validation (`controller.build_prompt`, `controller.validated`).

State changes are committed only after the model call succeeds, so a failed call (Ollama down) leaves the session as it
was and the student can simply retry.

The learner model (optional) is updated only by meaningful events: a question that names a course concept (a doubt),
a request to have something explained again (`simpler` / `explain_differently`), and the analysed answer to a check.
"""
import re
from dataclasses import dataclass, field

from src.learner import taxonomy

from .controller import (ANALYZE, STAGE_INSTRUCTIONS, WANTS_ANSWER, Session, Turn, ask_again, build_prompt, hint_extra,
                         is_hint_request, is_new_question, is_unsure, parse_analysis, sources, validated,
                         wants_explanation)

MODE = "answer_first"


class TutorInputError(ValueError):
    """The request cannot be handled in the conversation's current state; the message is safe to show a student."""


LADDER = ("definition", "intuition", "analogy", "scenario", "code")  # "explain differently" walks down this
MAX_CHECK_ROUNDS = 2  # non-solid replies to one check before the full answer is given
OFFER_EVERY = 3  # a check is offered on the first answer, then at most once every third answer

NO_CONTEXT_MESSAGE = ("I couldn't find enough relevant material in the current Threads/Synchronization knowledge base to "
                      "answer that confidently. Try rephrasing it, or ask about threads, locks, mutexes, semaphores, "
                      "condition variables or deadlock.")
GOT_IT_MESSAGE = "Glad that made sense. Ask me the next question, or try a quick check whenever you like."
OFFER_TEXT = "Want to test your understanding with a quick scenario?"
NO_HINT_MESSAGE = ("There's no question waiting for your answer right now, so there is nothing to hint at. Ask me "
                   "anything, or try a quick check whenever you like.")

TASKS = {
    "ANSWER": "Answer the student's question directly and teach the idea behind it: explain it, do not just define it. "
              "Cite the context as [S1], [S2], ... If the context does not cover part of what they ask, say plainly that "
              "the course material does not specify it and explain only what it does establish. If code helps and the "
              "context contains it, show it in a fenced code block exactly as the material writes it. Do not ask the "
              "student a question.",
    "CHECK": "Ask the student ONE short question that tests whether they understood the idea just explained: have them "
             "apply it to a small new scenario, predict what happens, or say why something fails. Do not repeat the "
             "explanation, do not hint at the answer and write nothing after the question.",
    "CONFIRM": "The student answered the check correctly. In one or two sentences confirm what they got right and add "
               "the one detail that deepens it, citing the context as [S1], [S2], ... Do not ask a question.",
    "CLARIFY": "The student's answer is correct as far as it goes but misses a key idea (the GAP below). Acknowledge "
               "what is right, name the missing idea, explain it in a few sentences citing the context as [S1], [S2], "
               "... and end with ONE short follow-up question about it.",
    "CORRECT": "The student's answer contains a misconception (the GAP below). Say plainly in your first sentence that "
               "it is not correct, name what is wrong, then give the correct idea in a few sentences citing the context "
               "as [S1], [S2], ... with a counterexample if one helps. End with ONE short question that tests the "
               "corrected idea.",
    "SIMPLIFY": "The student could not answer your check question or was unsure. Help them get there themselves; do not "
                "answer it for them: never state or imply its result, and do not work through its scenario, not even "
                "inside a question. In one simple sentence, name what to think about, not the conclusion. Cite the "
                "context as [S1], [S2], ... where it supports that sentence. Then ask ONE easier question that is a first "
                "step toward the check, not the check itself, and whose wording does not contain the answer.",
    "RESOLVE": "Give the student the complete answer to your check question, concisely, citing the context as [S1], "
               "[S2], ... Do not ask another question.",
}
REPRESENTATIONS = {
    "definition": "Explain the idea plainly: what it is and what it is for.",
    "intuition": "Explain the intuition in simpler words, shorter and with no jargon beyond the key term. Say why the "
                 "idea is needed, not what it is called.",
    "analogy": "Explain it through one everyday analogy, then say exactly where the analogy matches the Operating "
               "Systems idea and where it stops matching.",
    "scenario": "Walk through one concrete Operating Systems scenario with two or three named threads, step by step, "
                "showing what happens and why.",
    "example": "Give one small concrete worked example (a short trace or a few lines), then say what it shows.",
    "code": "Show a short C/pthreads code illustration taken from or consistent with the context, in a fenced code "
            "block, then explain line by line what matters. If the context has no code for this idea, say the course "
            "material shows none and explain it in words instead.",
    "detailed": "Give a fuller, deeper explanation covering the mechanism, the reason for it and a common pitfall. It "
                "may run up to about 250 words (this overrides the 120-word limit), as a compact structure of short "
                "paragraphs or a list.",
}
REEXPLAIN = ("The student did not get your earlier explanation, or asked for another one. Do NOT repeat it or reuse its "
             "wording. {rep} Cite the context as [S1], [S2], ... where it supports a claim. Do not ask the student a "
             "question.")
INTENT_REP = {"simpler": "intuition", "analogy": "analogy", "example": "example", "scenario": "scenario",
              "code": "code", "detailed": "detailed"}
INTENTS = set(INTENT_REP) | {"explain_differently", "test_me", "got_it"}
DIFFICULTY_INTENTS = {"simpler", "explain_differently"}  # asking again signals trouble; wanting an example does not

_P = re.compile
INTENT_RULES = (
    ("got_it", _P(r"^\s*(?:(?:ok(?:ay)?|alright|got it|makes sense|understood|i understand|clear now|thanks?|thank you|"
                  r"cool|great|nice|perfect)\b[\s,.!;:-]*)+$", re.I)),
    ("test_me", _P(r"\b(?:test (?:my|me)|quiz me|check my understanding|ask me (?:a )?(?:question|something)|"
                   r"give me (?:a |an )?(?:problem|question|exercise|practice)|practice (?:problem|question)s?)\b", re.I)),
    ("simpler", _P(r"\b(?:simpl(?:er|e|ify)|easier|eli5|in simple (?:words|terms)|layman|dumb it down|"
                   r"(?:too|so) (?:hard|complicated|technical))\b", re.I)),
    ("analogy", _P(r"\banalog(?:y|ies)\b", re.I)),
    ("code", _P(r"\b(?:code example|(?:show|give)(?: me)?(?: the| some)? code|in code|as code|pthread code)\b", re.I)),
    ("scenario", _P(r"\b(?:real[- ]world|real[- ]life|scenario)\b", re.I)),
    ("example", _P(r"\b(?:(?:give|show|need|want)(?: me)?(?: an?| another| one)? (?:example|instance)|"
                   r"example please|for instance)\b|^\s*(?:an? )?example\W*$", re.I)),
    ("detailed", _P(r"\b(?:in (?:more )?detail|detailed|deeper|elaborate|more depth|go deeper)\b", re.I)),
    ("explain_differently", _P(r"(?:\b(?:still )?(?:don'?t|do not|didn'?t|can'?t) (?:really )?(?:understand|get|follow)|"
                               r"\bnot (?:clear|getting)|\bconfus\w+|doesn'?t make sense|"
                               r"\b(?:explain|say|put) (?:it |that )?(?:differently|again|another way)|\banother way\b|"
                               r"\bre-?explain|\bi'?m lost\b|samajh (?:nahi|nhi)|nahi samajh|nhi samajh)", re.I)),
)


def detect_intent(text):
    """The request a free-text message makes about the explanation, or None. Deterministic; the first rule that
    matches wins, in the order above. A message that merely mentions a word ("what is an example of deadlock?") is a
    question, not a request: a question mark with a leading wh-word is never an intent except 'explain again'."""
    text = (text or "").strip()
    if not text:
        return None
    for name, rule in INTENT_RULES:
        if rule.search(text):
            if name in ("example", "scenario", "code", "detailed", "analogy") and is_new_question(text) and "?" in text \
                    and not re.search(r"\b(?:give|show|need|want)\b", text, re.I):
                continue
            return name
    return None


@dataclass
class ChatSession(Session):
    """Session with the answer-first conversation state. Inherits question/context/history from the Socratic Session
    so the shared prompt builder works on it unchanged."""
    stage: str = "ANSWER"
    mode: str = MODE
    concepts: list = field(default_factory=list)  # taxonomy ids this conversation is about
    representation: str | None = None
    ladder_index: int = 0
    answers: int = 0
    last_offer: int = -OFFER_EVERY
    pending_check: str | None = None  # the check question being waited on
    check_context: list = field(default_factory=list)
    check_rounds: int = 0
    last_context: list = field(default_factory=list)


def _view(session, question=None, context=None, history=None):
    return Session(question if question is not None else session.question,
                   context if context is not None else session.context, stage=session.stage,
                   history=list(history if history is not None else session.history))


class TutorService:
    def __init__(self, retriever, llm, learner=None, top_k=5, is_relevant=None):
        self.retriever, self.llm, self.learner, self.top_k = retriever, llm, learner, top_k
        self.is_relevant = is_relevant or bool

    # ---------------------------------------------------------------- plumbing
    def _generate(self, prompt, n_sources, emit=None):
        text = self.llm(prompt, on_token=lambda t: emit("token", t)) if emit else self.llm(prompt)
        return validated(text, n_sources)

    def _retrieve(self, query, emit=None):
        results = self.retriever.search(query, top_k=self.top_k)
        if emit and results:
            emit("sources", results)
        return results

    def _learner_context(self, concepts):
        if not self.learner or not concepts:
            return None
        lines = []
        for cid in concepts[:3]:
            s = self.learner.concept_state(cid)
            if s["level"] == "unknown":
                continue
            line = f"- {s['label']}: confidence {s['level']}"
            if s["misconceptions"]:
                line += f"; earlier misconception: {s['misconceptions'][-1]}"
            lines.append(line)
        return "\n".join(lines) or None

    def _state(self, session):
        return {"open": True, "pending_check": bool(session.pending_check), "representation": session.representation}

    def _concept_info(self, ids):
        return [{"id": c, "label": taxonomy.label(c), "topic": taxonomy.get(c).topic} for c in ids if c in taxonomy.CONCEPTS]

    def _turn(self, session, stage, message, srcs, **kw):
        return Turn(stage, message, srcs, mode=MODE, concepts=self._concept_info(session.concepts),
                    tutor_state=self._state(session), **kw)

    @staticmethod
    def _answer_actions(offer):
        acts = [{"id": "got_it", "label": "Got it"}, {"id": "explain_differently", "label": "Explain differently"}]
        return acts + ([{"id": "test_me", "label": "Test my understanding"}] if offer else [])

    # ---------------------------------------------------------------- entry points
    def start(self, question, emit=None):
        if not isinstance(question, str) or not question.strip():
            raise TutorInputError("question must be a non-empty string")
        session = ChatSession(question.strip(), [])
        return session, self._answer(session, question.strip(), emit)

    def respond(self, session, reply="", intent=None, emit=None):
        reply = reply if isinstance(reply, str) else ""
        if intent is not None and intent not in INTENTS:
            raise TutorInputError(f"unknown intent {intent!r}")
        if not reply.strip() and not intent:
            raise TutorInputError("reply must be a non-empty string")
        text = reply.strip()
        intent = intent or detect_intent(text)
        if intent == "got_it":
            return self._got_it(session, text)
        if intent == "test_me":
            return self._check(session, emit)
        if intent in INTENT_REP or intent == "explain_differently":
            return self._reexplain(session, intent, emit)
        if is_hint_request(text):
            return self._hint(session, text, emit) if session.pending_check else self._no_hint(session, text)
        if session.pending_check:
            if is_new_question(text) and not wants_explanation(text):
                return self._aside(session, text, emit)
            return self._grade(session, text, emit)
        if is_unsure(text) and session.last_context:  # "I'm not sure" after an answer: the same idea, explained differently
            return self._reexplain(session, "explain_differently", emit)
        return self._answer(session, text, emit)

    # ---------------------------------------------------------------- turns
    def _query_for(self, session, text):
        """Short follow-ups ("why not?") carry no topic of their own: add the conversation's concepts to the query."""
        if len(text.split()) <= 6 and not taxonomy.detect_concepts(text) and session.concepts:
            return f"{text} {' '.join(taxonomy.get(c).query for c in session.concepts[:2])}"
        return text

    def _answer(self, session, text, emit=None):
        results = self._retrieve(self._query_for(session, text), emit)
        if not self.is_relevant(results):
            session.history += [("Student", text), ("Tutor", NO_CONTEXT_MESSAGE)]
            session.question = text
            # the fixed message was generated from no passage: rejected candidates are not this turn's provenance
            return self._turn(session, "NO_CONTEXT", NO_CONTEXT_MESSAGE, [], follow_up=None)
        named = taxonomy.detect_concepts(text)
        concepts = named or taxonomy.concepts_from_results(results) or list(session.concepts)
        view = _view(session, text, results, session.history + [("Student", text)])
        offer = session.answers == 0 or session.answers + 1 - session.last_offer >= OFFER_EVERY
        message = self._generate(build_prompt(view, TASKS["ANSWER"], learner=self._learner_context(concepts)),
                                 len(results), emit)
        # the model call succeeded: commit
        session.question, session.context, session.last_context = text, results, results
        session.history = view.history + [("Tutor", message)]
        session.concepts, session.representation, session.ladder_index = concepts, "definition", 0
        session.answers += 1
        if offer:
            session.last_offer = session.answers
        update = self._doubt(session, text, named, results)
        return self._turn(session, "ANSWER", message, sources(results), follow_up=OFFER_TEXT if offer else None,
                          learner_update=update, actions=self._answer_actions(offer))

    def _doubt(self, session, text, named, results):
        """A doubt is meaningful when the question names a course concept, or is a real question about material the
        retriever tied to one. Greetings and chit-chat leave the learner model alone."""
        if not self.learner or not session.concepts:
            return None
        question_like = is_new_question(text) or "?" in text
        if not (question_like or any(not taxonomy.get(c).generic for c in named)):
            return None
        updates = self.learner.record_doubt(session.concepts[:2], text)
        return updates[0] if updates else None

    def _got_it(self, session, text):
        session.history += [("Student", text or "Got it"), ("Tutor", GOT_IT_MESSAGE)]
        return self._turn(session, "ANSWER", GOT_IT_MESSAGE, [], actions=[{"id": "test_me", "label": "Test my understanding"}])

    def _reexplain(self, session, intent, emit=None):
        if not session.last_context:
            raise TutorInputError("nothing to explain yet; ask a question first")
        if intent == "explain_differently":
            index = min(session.ladder_index + 1, len(LADDER) - 1)
            if index == session.ladder_index:  # every representation has been used: start the loop again, gently
                index = 1
            rep = LADDER[index]
        else:
            rep = INTENT_REP[intent]
            index = LADDER.index(rep) if rep in LADDER else session.ladder_index
        if intent == "simpler" and rep == session.representation:
            rep, index = LADDER[2], 2  # already simplified once: go to an analogy
        query = {"code": "code example", "example": "example", "scenario": "example"}.get(rep)
        results = self._retrieve(f"{session.question} {query}", emit) if query else session.last_context
        if not self.is_relevant(results):
            results = session.last_context
        view = _view(session, session.question, results, session.history + [("Student", f"(asks for: {intent})")])
        message = self._generate(
            build_prompt(view, REEXPLAIN.format(rep=REPRESENTATIONS[rep]), learner=self._learner_context(session.concepts)),
            len(results), emit)
        session.context = results
        session.history = view.history + [("Tutor", message)]
        session.representation, session.ladder_index = rep, index
        update = None
        if self.learner and session.concepts and intent in DIFFICULTY_INTENTS:
            update = self.learner.record_evidence(session.concepts[0], "re_explain")
        return self._turn(session, "ANSWER", message, sources(results), learner_update=update,
                          actions=self._answer_actions(True))

    def _check(self, session, emit=None):
        if not session.last_context:
            raise TutorInputError("nothing to check yet; ask a question first")
        view = _view(session, session.question, session.last_context, session.history)
        message = self._generate(build_prompt(view, TASKS["CHECK"], learner=self._learner_context(session.concepts)),
                                 len(session.last_context), emit)
        session.history = view.history + [("Tutor", message)]
        session.pending_check, session.check_context, session.check_rounds = message, session.last_context, 0
        session.stage = "CHECK"
        return self._turn(session, "CHECK", message, sources(session.last_context),
                          actions=[{"id": "explain_differently", "label": "Explain differently"}])

    def _hint(self, session, text, emit=None):
        """A hint on the pending check: it stays pending, its rounds unchanged, nothing graded."""
        ctx = session.check_context
        view = _view(session, session.question, ctx, session.history + [("Student", text)])
        message = self._generate(build_prompt(view, STAGE_INSTRUCTIONS["HINT"], hint_extra(session.history),
                                              learner=self._learner_context(session.concepts)), len(ctx), emit)
        message = ask_again(message, session.history, emit)
        session.history = view.history + [("Tutor", message)]
        return self._turn(session, "HINT", message, sources(ctx),
                          actions=[{"id": "explain_differently", "label": "Explain differently"}])

    def _no_hint(self, session, text):
        session.history += [("Student", text), ("Tutor", NO_HINT_MESSAGE)]
        return self._turn(session, "ANSWER", NO_HINT_MESSAGE, [], actions=[{"id": "test_me", "label": "Test my understanding"}])

    def _aside(self, session, text, emit=None):
        """A new question while a check is pending: answer it from its own context; the check stays pending."""
        results = self._retrieve(text, emit)
        if not self.is_relevant(results):
            session.history += [("Student", text), ("Tutor", NO_CONTEXT_MESSAGE)]
            return self._turn(session, "NO_CONTEXT", NO_CONTEXT_MESSAGE, [])  # no passage used (see _answer)
        aside = Session(text, results, stage=session.stage, history=list(session.history) + [("Student", text)])
        message = self._generate(build_prompt(aside, STAGE_INSTRUCTIONS["ASIDE"]), len(results), emit)
        session.history = aside.history + [("Tutor", message)]
        named = taxonomy.detect_concepts(text)
        update = None
        if self.learner and named:
            update = self.learner.record_doubt(named[:2], text)[0]
        return self._turn(session, "ANSWER", message, sources(results), learner_update=update,
                          actions=[{"id": "explain_differently", "label": "Explain differently"}])

    def _grade(self, session, text, emit=None):
        ctx = session.check_context
        view = _view(session, session.question, ctx, session.history + [("Student", text)])
        gives_up = bool(WANTS_ANSWER.search(text))  # "just tell me the answer": reveal it, count it as not knowing
        if gives_up or is_unsure(text) or wants_explanation(text):  # no model needed to see that
            analysis = {"level": "unclear", "gap": "the student did not know"}
        else:
            analysis = parse_analysis(self.llm(build_prompt(view, ANALYZE, student_facing=False), json_mode=True))
        if emit:
            emit("analysis", analysis)
        level = analysis["level"]
        final = gives_up or (level != "solid" and session.check_rounds + 1 > MAX_CHECK_ROUNDS)
        task = "RESOLVE" if final else {"solid": "CONFIRM", "partial": "CLARIFY", "misconception": "CORRECT",
                                        "unclear": "SIMPLIFY"}[level]
        extra = f"\n\nGAP\n{analysis['gap'] or 'not identified; address the core idea'}" if task in ("CLARIFY", "CORRECT") else ""
        message = self._generate(
            build_prompt(view, TASKS[task], extra, learner=self._learner_context(session.concepts)), len(ctx), emit)
        session.history = view.history + [("Tutor", message)]
        update = None
        if self.learner and session.concepts:
            update = self.learner.record_evidence(session.concepts[0], level, analysis["gap"])
        if level == "solid" or final:
            session.pending_check, session.check_rounds, session.stage = None, 0, "ANSWER"
        else:
            session.pending_check, session.check_rounds = message, session.check_rounds + 1
        offer = level == "solid"
        return self._turn(session, "FEEDBACK", message, sources(ctx), analysis=analysis,
                          follow_up="Want a harder one?" if offer else None, learner_update=update,
                          actions=([{"id": "test_me", "label": "Another check"}] if offer else
                                   [{"id": "explain_differently", "label": "Explain differently"}]))
