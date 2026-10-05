"""Review 2 tests: tutor controller flow (scripted LLM stand-in) and the pre/post assessment framework.

The data in these tests is synthetic test input, not participant results.

    python3 -m pytest tests -q
"""
import json
from pathlib import Path

import pytest

from src.assessment.learning_gain import analyze, gain
from src.tutor.controller import TutorController, parse_analysis

ROOT = Path(__file__).resolve().parents[1]
BANK = json.loads((ROOT / "data/assessment/question_bank_draft.json").read_text())
LOS = json.loads((ROOT / "data/assessment/learning_objectives.json").read_text())
CHUNK_IDS = {json.loads(l)["chunk_id"] for l in (ROOT / "data/chunks/chunks.jsonl").read_text().splitlines()}


# ------------------------------------------------------------------ tutor
class FakeRetriever:
    def search(self, query, top_k=5):
        return [{"chunk_id": f"doc::c000{i}", "filename": "doc.pdf", "section": f"Sec {i}", "page_start": i,
                 "slide_start": None, "text": f"context text {i}"} for i in range(1, top_k + 1)]


class Script:
    """LLM stand-in: answers analysis prompts from a queue of levels, echoes the stage otherwise."""
    def __init__(self, levels):
        self.levels, self.prompts = list(levels), []

    def __call__(self, prompt, **kw):  # kw: json_mode / on_token, as OllamaLLM takes
        self.prompts.append(prompt)
        if "Reply with JSON only" in prompt:
            return json.dumps({"level": self.levels.pop(0), "gap": "the lock is released while waiting"})
        return "tutor says: " + prompt.rsplit("TASK\n", 1)[1][:20]


def test_diagnose_first_with_grounded_prompt_and_provenance():
    llm = Script([])
    session, turn = TutorController(FakeRetriever(), llm, top_k=3).start("Why does cond_wait take a mutex?")
    assert turn.stage == "DIAGNOSE" and session.stage == "DIAGNOSE"
    p = llm.prompts[0]
    assert "Do NOT answer the question yet" in p and "[S1] doc.pdf (p.1) Sec 1\ncontext text 1" in p and "[S3]" in p
    assert [s["ref"] for s in turn.sources] == ["S1", "S2", "S3"] and turn.sources[0]["chunk_id"] == "doc::c0001"


def test_gap_leads_to_explanation_then_check_then_move_on():
    llm = Script(["misconception", "solid"])
    tutor = TutorController(FakeRetriever(), llm)
    session, _ = tutor.start("q")
    t = tutor.respond(session, "it keeps the lock")
    assert t.stage == "EXPLAIN" and t.analysis["level"] == "misconception"
    assert "GAP\nthe lock is released while waiting" in llm.prompts[-1] and "example" in llm.prompts[-1]
    t = tutor.respond(session, "it releases it atomically")
    assert t.stage == "DONE" and session.gaps == ["the lock is released while waiting"]
    assert [w for w, _ in session.history] == ["Tutor", "Student", "Tutor", "Student", "Tutor"]  # last = wrap-up
    assert "answered the check correctly" in llm.prompts[-1] and t.message.startswith("tutor says")
    with pytest.raises(ValueError):
        tutor.respond(session, "more")


def test_solid_diagnosis_goes_to_formative_check():
    tutor = TutorController(FakeRetriever(), Script(["solid", "solid"]))
    session, _ = tutor.start("q")
    assert tutor.respond(session, "good answer").stage == "CHECK"
    assert tutor.respond(session, "good again").stage == "DONE"


def test_emit_streams_sources_analysis_and_tokens():
    events = []
    class Streaming(Script):
        def __call__(self, prompt, json_mode=False, on_token=None):
            out = super().__call__(prompt)
            if on_token:
                on_token(out)
            assert json_mode == ("Reply with JSON only" in prompt)  # analysis calls ask for JSON mode
            return out
    tutor = TutorController(FakeRetriever(), Streaming(["partial"]), top_k=2)
    session, _ = tutor.start("q", emit=lambda k, d: events.append(k))
    tutor.respond(session, "half an answer", emit=lambda k, d: events.append(k))
    assert events == ["sources", "token", "analysis", "token"]
    with pytest.raises(ValueError):
        tutor.respond(session, "  ")


def test_rounds_are_bounded_then_full_answer():
    llm = Script(["partial"] * 4)
    tutor = TutorController(FakeRetriever(), llm, max_rounds=2)
    session, _ = tutor.start("q")
    stages = [tutor.respond(session, "hmm").stage for _ in range(3)]
    assert stages == ["EXPLAIN", "EXPLAIN", "DONE"] and "complete answer" in llm.prompts[-1]


def test_malformed_analysis_is_unclear():
    assert parse_analysis("not json") == {"level": "unclear", "gap": ""}
    assert parse_analysis('{"level": "genius"}')["level"] == "unclear"
    assert parse_analysis('Sure: {"level": "partial", "gap": "x"}') == {"level": "partial", "gap": "x"}
    with pytest.raises(ValueError):
        TutorController(FakeRetriever(), Script([])).start("  ")


# ------------------------------------------------------------------ assessment framework
def test_question_bank_is_well_formed_and_grounded():
    lo_ids = {o["objective_id"] for o in LOS["objectives"]}
    assert len(lo_ids) == 8
    items = BANK["items"]
    assert len({i["item_id"] for i in items}) == len(items)
    for lo in lo_ids:  # one pre and one post item per objective (parallel forms)
        assert sorted(i["form"] for i in items if i["objective_id"] == lo) == ["post", "pre"]
    for i in items:
        assert i["objective_id"] in lo_ids and i["difficulty"] in ("easy", "medium", "hard")
        assert i["question_type"] in ("mcq", "short_answer", "code_reasoning") and i["expected_concept"]
        assert i["max_score"] == (1 if i["question_type"] == "mcq" else 2)
        if i["question_type"] == "mcq":
            assert i["answer"] in i["options"]
        assert i["grounding_chunks"] and set(i["grounding_chunks"]) <= CHUNK_IDS
    assert "DRAFT" in BANK["status"] and "DRAFT" in LOS["status"]


def test_gain_formulas():
    assert gain(40, 70) == {"pre": 40, "post": 70, "absolute_gain": 30, "normalized_gain": 0.5}
    assert gain(100, 100)["normalized_gain"] is None
    assert gain(50, 25)["normalized_gain"] == -0.5


def test_analyze_synthetic_responses():
    pre_ids = [i["item_id"] for i in BANK["items"] if i["form"] == "pre"]
    post_ids = [i["item_id"] for i in BANK["items"] if i["form"] == "post"]
    full = lambda ids: {i["item_id"]: i["max_score"] for i in BANK["items"] if i["item_id"] in ids}
    responses = {"participants": [
        {"participant_id": "s1", "condition": "tutor", "pre": {}, "post": full(post_ids)},           # 0 -> 100
        {"participant_id": "s2", "condition": "tutor", "pre": full(pre_ids), "post": full(post_ids)},  # 100 -> 100
    ]}
    out = analyze(BANK, responses)
    assert out["participants"][0]["normalized_gain"] == 1.0 and out["participants"][1]["normalized_gain"] is None
    assert out["class"] == {"n": 2, "pre": 50.0, "post": 100.0, "absolute_gain": 50.0, "normalized_gain": 1.0,
                            "mean_individual_normalized_gain": 1.0}
    assert set(out["by_objective"]) == {f"LO{i}" for i in range(1, 9)} and out["by_condition"]["tutor"]["n"] == 2
    with pytest.raises(ValueError):
        analyze(BANK, {"participants": [{"participant_id": "x", "pre": {"nope": 1}, "post": {}}]})
    with pytest.raises(ValueError):
        analyze(BANK, {"participants": [{"participant_id": "x", "pre": {pre_ids[0]: 9}, "post": {}}]})
