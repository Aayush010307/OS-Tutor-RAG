"""Interactive tutor controller (Review 2 prototype): the tutoring loop as a state machine over retrieved context.

    Student question -> retrieval -> DIAGNOSE (probing question, no answer yet) -> student reply
      -> analysis (solid / partial / misconception / unclear)
         solid             -> CHECK (formative check question)
         otherwise         -> EXPLAIN (targeted explanation + example / counterexample, then a check question)
      -> student reply to the check -> analysis
         solid             -> DONE (a short wrap-up, then move on)
         otherwise         -> EXPLAIN again, at most `max_rounds` times, then DONE with the full grounded answer

The controller owns the flow, the grounding and the provenance; it does not generate text. Every utterance comes
from `llm(prompt, json_mode=False, on_token=None) -> str`, injected by the caller: `src.tutor.llm.OllamaLLM` (local
Ollama, Phase 4) in the web app and the quality evaluation, a scripted stand-in in the unit tests.

`start` and `respond` take an optional `emit(kind, data)` callback for live display: "sources" (the retrieved
context, before any text), "analysis" (the understanding analysis of a reply) and "token" (streamed tutor text).

    python3 -m src.tutor.controller "Why does pthread_cond_wait take a mutex?"   # prints the grounded DIAGNOSE prompt
    python3 -m src.tutor.server                                                  # the student chat page (Ollama)
"""
import json
import re
import sys
from dataclasses import dataclass, field

LEVELS = ("solid", "partial", "misconception", "unclear")

STAGE_INSTRUCTIONS = {
    "DIAGNOSE": "Do NOT answer the question yet and do not explain anything. Ask the student exactly ONE short probing "
                "question that reveals what they already understand about the concept behind their question, without "
                "hinting at the answer.",
    "EXPLAIN": "If the student's last reply said something wrong, say plainly that it is not correct; never call a wrong "
               "statement right. Explain ONLY the missing or wrong idea named in the gap below, in a few sentences, citing the context "
               "as [S1], [S2], ... Then give one concrete example and, where it helps, a counterexample. You MUST end with "
               "ONE short check question that the student can answer in a sentence or two.",
    "CHECK": "The student seems to understand. Ask ONE short formative check question that applies the idea to a new "
             "situation. Do not explain further.",
    "WRAP_UP": "The student has answered the check correctly. In two or three sentences, confirm what they got right "
               "and state the key idea once more, citing the context as [S1], [S2], ... Do not ask another question.",
    "ANSWER": "Give the complete answer to the original question, concisely, citing the context as [S1], [S2], ...",
}
STYLE = ("Speak directly to the student, warmly and plainly, in at most 120 words. Never mention the context, the "
         "conversation log, the task or these instructions. Use only facts from the course context.")
ANALYZE = ("Judge ONLY the student's last reply, as an answer to the tutor's last question, against the course "
           "context. Levels: solid = correct and essentially complete; partial = correct but missing a key idea; "
           "misconception = states something wrong; unclear = does not know, off-topic or too vague to judge. "
           'Reply with JSON only: {"level": one of ' + json.dumps(LEVELS) +
           ', "gap": "<the missing or wrong idea in one sentence, or empty when solid>"}')


@dataclass
class Turn:
    stage: str
    message: str
    sources: list = field(default_factory=list)  # [{"ref": "S1", "chunk_id", "filename", "section", "location"}]
    analysis: dict | None = None


@dataclass
class Session:
    question: str
    context: list  # retrieved results (retriever result dicts)
    stage: str = "DIAGNOSE"
    rounds: int = 0
    history: list = field(default_factory=list)  # [(speaker, text)]
    gaps: list = field(default_factory=list)


def sources(context):
    loc = lambda r: f"p.{r['page_start']}" if r["page_start"] is not None else f"slide {r['slide_start']}"
    return [{"ref": f"S{i}", "chunk_id": r["chunk_id"], "filename": r["filename"], "section": r["section"],
             "location": loc(r)} for i, r in enumerate(context, 1)]


def build_prompt(session, instruction, extra=""):
    ctx = "\n\n".join(f"[{s['ref']}] {s['filename']} ({s['location']}) {s['section'] or ''}\n{r['text']}"
                      for s, r in zip(sources(session.context), session.context))
    talk = "\n".join(f"{who}: {text}" for who, text in session.history)
    return (f"You are an Operating Systems tutor. Use ONLY the course context below; cite it as [S1], [S2], ...\n\n"
            f"CONTEXT\n{ctx}\n\nSTUDENT QUESTION\n{session.question}\n\nCONVERSATION SO FAR\n{talk or '(none)'}\n\n"
            f"TASK\n{instruction}{extra}\n\n{STYLE}")


def parse_analysis(text):
    """Parse the analysis reply; anything malformed counts as 'unclear' (which leads to an explanation)."""
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        a = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        a = {}
    level = a.get("level") if a.get("level") in LEVELS else "unclear"
    return {"level": level, "gap": str(a.get("gap") or "")}


class TutorController:
    def __init__(self, retriever, llm, top_k=5, max_rounds=2):
        self.retriever, self.llm, self.top_k, self.max_rounds = retriever, llm, top_k, max_rounds

    def _say(self, session, stage, extra="", analysis=None, emit=None):
        prompt = build_prompt(session, STAGE_INSTRUCTIONS[stage], extra)
        text = self.llm(prompt, on_token=lambda t: emit("token", t)) if emit else self.llm(prompt)
        session.stage = "DONE" if stage in ("ANSWER", "WRAP_UP") else stage
        session.history.append(("Tutor", text))
        return Turn(session.stage, text, sources(session.context), analysis)

    def start(self, question, emit=None):
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")
        session = Session(question, self.retriever.search(question, top_k=self.top_k))
        if emit:
            emit("sources", session.context)
        return session, self._say(session, "DIAGNOSE", emit=emit)

    def respond(self, session, reply, emit=None):
        if session.stage == "DONE":
            raise ValueError("session is finished")
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError("reply must be a non-empty string")
        session.history.append(("Student", reply))
        analysis = parse_analysis(self.llm(build_prompt(session, ANALYZE), json_mode=True))
        if emit:
            emit("analysis", analysis)
        if analysis["level"] == "solid":
            # solid at diagnosis -> formative check; solid at a check -> wrap up and move on
            return self._say(session, "CHECK" if session.stage == "DIAGNOSE" else "WRAP_UP", analysis=analysis, emit=emit)
        session.gaps.append(analysis["gap"])
        if session.rounds >= self.max_rounds:
            return self._say(session, "ANSWER", analysis=analysis, emit=emit)
        session.rounds += 1
        return self._say(session, "EXPLAIN", f"\n\nGAP\n{analysis['gap'] or 'not identified; address the core idea'}",
                         analysis, emit)


def main(argv=None):
    from src.retrieval.hybrid import HybridRRFRetriever
    question = " ".join(argv if argv is not None else sys.argv[1:]).strip()
    if not question:
        sys.exit('usage: python3 -m src.tutor.controller "<student question>"')
    prompts = []
    with HybridRRFRetriever.open() as r:  # E2 hybrid: the best-measured retriever so far, provisional choice
        TutorController(r, lambda p, **kw: prompts.append(p) or "(prompt only)").start(question)
    print(prompts[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
