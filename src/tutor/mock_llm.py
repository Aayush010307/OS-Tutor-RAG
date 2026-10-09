"""Mock LLM for development and tests: `LLM_PROVIDER=mock`. No Ollama, no network, deterministic.

It reads the prompt the real model would get, works out which task it is (the task texts are the controller's, the
service's and the revision service's own constants), and answers in the right shape: valid analysis JSON for the analysis
call, and short cited prose for everything else (with a next question where the task asks for one). The prose quotes the
first retrieved passage so the page shows real, traceable content, and it is labelled as a mock so nobody mistakes it for
a model answer. It exists to exercise retrieval, the API, the tutor flow, the learner model, Smart Revision and the page;
it says nothing about the quality of a real model.
"""
import json
import re

from src.revision import service as revision

from . import controller, service
from .llm import LLMProvider

TASKS = {**{f"controller.{k}": v for k, v in controller.STAGE_INSTRUCTIONS.items()},
         **{f"service.{k}": v for k, v in service.TASKS.items()},
         **{f"rep.{k}": v for k, v in service.REPRESENTATIONS.items()}}
REVISION_TASKS = {**{f"rf.{k}": v for k, v in revision.FEEDBACK.items()},  # feedback first: it can embed a question task
                  **{f"rq.{k}": v for k, v in revision.QUESTION.items()}}
REVISION_QUESTIONS = {
    "recall": "In one sentence, what is the key idea here?",
    "understanding": "In your own words, why does this matter when two threads share data?",
    "application": "Thread A and thread B both run this step at the same time. What can happen, and why?",
    "reasoning": "Why is making the data shared not enough to make the operation safe?",
    "code": ("Here is a short pthread example:\n\n```c\nint counter = 0;\nvoid *inc(void *a) { counter++; return NULL; }\n```"
             "\n\nWhere would you place the mutex?"),
}
STUDENT = re.compile(r"STUDENT'S LAST MESSAGE\n(.*)\Z", re.S)
FIRST_SOURCE = re.compile(r"^\[S1\][^\n]*\n(.*?)(?:\n\n\[S2\]|\nREFERENCE MATERIAL>>>)", re.S | re.M)
WRONG = re.compile(r"\b(?:only (?:for |in |with )?processes|always safe|never (?:happens|occurs)|no need|cannot happen|"
                   r"does ?n[o']t matter|wrong)\b", re.I)
UNSURE = re.compile(r"\b(?:don'?t know|no idea|not sure|idk|dunno)\b", re.I)


def _snippet(prompt, limit=220):
    block = prompt.split("<<<REFERENCE MATERIAL", 1)[-1]  # only the retrieved passages, not the policy text above
    m = FIRST_SOURCE.search(block.split("\n", 1)[-1])
    text = " ".join((m.group(1) if m else "").split())
    return (text[:limit].rsplit(" ", 1)[0] + "...") if len(text) > limit else text


def _task_text(prompt):
    return prompt.split("\nTASK\n", 1)[-1].split("\n\nCOURSE CONTEXT", 1)[0]


def _task(prompt):
    """Which task the prompt asks for: the TASK section starts with one of the known task texts (a re-explanation
    carries one of the representation texts inside it, a revision task may follow a 'stepping back' note)."""
    task = _task_text(prompt)
    for name, text in REVISION_TASKS.items():
        if text[:50] in task:
            return name
    if task.startswith(service.REEXPLAIN[:40]):
        return next((n for n, t in TASKS.items() if n.startswith("rep.") and t in task), "service.ANSWER")
    return next((n for n, t in TASKS.items() if not n.startswith("rep.") and task.startswith(t[:60])), "service.ANSWER")


class MockLLM(LLMProvider):
    """Callable like OllamaProvider: llm(prompt, json_mode=False, on_token=None) -> str."""
    name = "mock"
    options = {"temperature": 0.0, "seed": 0, "num_ctx": 0}
    model = "mock"

    def __init__(self):
        self.calls = []

    def __call__(self, prompt, json_mode=False, on_token=None):
        self.calls.append(prompt)
        out = self._analysis(prompt) if json_mode else self._text(prompt)
        if on_token:
            for word in re.findall(r"\S+\s*", out):
                on_token(word)
        return out

    @staticmethod
    def _analysis(prompt):
        m = STUDENT.search(prompt)
        answer = (m.group(1) if m else "").strip()
        if UNSURE.search(answer) or len(answer.split()) < 3:
            level, gap = "unclear", "the student was unsure or gave too little to judge"
        elif WRONG.search(answer):
            level, gap = "misconception", "the stated claim contradicts the course material"
        elif len(answer.split()) < 9:
            level, gap = "partial", "the answer leaves out the reason, which the question asked for"
        else:
            level, gap = "solid", ""
        return json.dumps({"level": level, "gap": gap})

    def _revision(self, name, prompt, body):
        if name.startswith("rq."):
            return REVISION_QUESTIONS[name[3:]]
        if name == "rf.final":
            return f"Thanks, that gives a clear picture. {body}"
        task = _task_text(prompt)
        asked = next((lvl for lvl, t in revision.QUESTION.items() if t in task), None)
        question = REVISION_QUESTIONS[asked] if asked else "Can you explain that part once more in your own words?"
        lead = {"rf.solid": "Yes, that is right.", "rf.partial": "Part of that is right, but one idea is missing.",
                "rf.misconception": "That is not correct.", "rf.unclear": "Let's make it simpler."}[name]
        return f"{lead} {body}\n\n{question}"

    def _text(self, prompt):
        name = _task(prompt)
        snip = _snippet(prompt)
        body = f"{snip} [S1]" if snip else "The course material does not specify this."
        rep = name.split(".", 1)[1] if name.startswith("rep.") else None
        if name.startswith(("rq.", "rf.")):
            return self._revision(name, prompt, body)
        if name == "controller.DIAGNOSE":
            return "What do you already know about this idea, in your own words?"
        if name in ("service.CHECK", "controller.CHECK"):
            return "Two threads run this code at the same time. What could go wrong, and why?"
        if name == "service.CONFIRM" or name == "controller.WRAP_UP":
            return f"Yes, that is right. {body}"
        if name in ("service.CLARIFY", "controller.EXPLAIN"):
            return f"You have part of it, but one idea is missing. {body} Can you say why that matters?"
        if name == "service.CORRECT":
            return f"That is not correct. {body} How would you restate it now?"
        if name == "service.SIMPLIFY":
            return f"Let's make it simpler. {body} In your own words, what happens?"
        if name in ("service.RESOLVE", "controller.ANSWER"):
            return f"Here is the full answer. {body}"
        if name == "controller.ASIDE":
            return f"{body} Back to your earlier question whenever you are ready."
        if rep:
            return f"({rep.capitalize()} view) {body}"
        return f"[mock tutor] {body}"

    def health(self):
        return {"provider": "mock", "model": "mock", "reachable": True, "model_available": True, "ok": True,
                "message": "Mock LLM: scripted replies, no Ollama needed."}


MockLLMProvider = MockLLM
