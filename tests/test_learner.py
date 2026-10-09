"""Product upgrade tests: the concept taxonomy and the learner model (deterministic mastery, persistence, weak concepts).

    python3 -m pytest tests -q
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.learner import taxonomy
from src.learner.model import ALPHA, DOUBT_START, LearnerModel, level_of


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, **kw):
        self.now += timedelta(**kw)


# ------------------------------------------------------------------ taxonomy
def test_the_taxonomy_is_a_consistent_acyclic_graph():
    for c in taxonomy.CONCEPTS.values():
        assert c.topic in (taxonomy.THREADS, taxonomy.SYNC)
        assert all(p in taxonomy.CONCEPTS for p in c.prerequisites), c.id
        assert c.id not in taxonomy.prerequisite_chain(c.id), f"cycle through {c.id}"
    assert "thread_basics" in taxonomy.prerequisite_chain("race_condition")
    assert taxonomy.prerequisite_chain("condition_variable")[0] == "mutex"
    assert "condition_variable" in taxonomy.dependents("mutex") and "mutex" in taxonomy.related("condition_variable")


def test_every_corpus_subtopic_is_covered_or_deliberately_skipped():
    """The taxonomy follows what the indexed material actually teaches: each subtopic label in chunks.jsonl maps to a
    concept, except a short list of labels that are not concepts a student revises."""
    skipped = {"pthreads", "thread scheduling", "barriers", "concurrency bugs"} - set(taxonomy.SUBTOPIC_TO_CONCEPT)
    labels = set()
    for line in Path("data/chunks/chunks.jsonl").read_text(encoding="utf-8").splitlines():
        labels |= {s.lower() for s in json.loads(line)["subtopics"]}
    unmapped = labels - set(taxonomy.SUBTOPIC_TO_CONCEPT)
    assert unmapped <= {"thread scheduling", "barriers"}, f"corpus subtopics with no concept: {sorted(unmapped)}"
    assert skipped <= {"thread scheduling", "barriers"}


def test_nothing_unsupported_is_in_the_taxonomy():
    # no chunk mentions pthread_exit, so it must not be a concept (the brief says: do not invent unsupported concepts)
    assert not any("pthread_exit" in c.pattern or c.id == "thread_termination" for c in taxonomy.CONCEPTS.values())


@pytest.mark.parametrize("text,expected", [
    ("What is a race condition?", ["race_condition"]),
    ("I don't understand why counter++ is unsafe.", ["race_condition"]),
    ("Why do we use pthread_join?", ["thread_join"]),
    ("What does pthread_cond_wait do?", ["condition_variable"]),
    ("What's wrong with this mutex code?", ["mutex"]),
    ("difference between a mutex and a semaphore", ["mutex", "semaphore"]),
    ("explain deadlock and the dining philosophers problem", ["deadlock", "dining_philosophers"]),
    ("what is a binary semaphore", ["binary_semaphore", "semaphore"]),
    ("why does a thread have its own stack", ["thread_basics"]),  # generic only when nothing specific matched
    ("what is the weather", []),
])
def test_concepts_are_detected_from_the_students_words(text, expected):
    assert sorted(taxonomy.detect_concepts(text)) == sorted(expected)


def test_concepts_of_retrieved_chunks_come_from_the_corpus_subtopics():
    results = [{"metadata": {"subtopics": ["Semaphores", "Locks"]}}, {"metadata": {"subtopics": ["Semaphores"]}},
               {"metadata": {"subtopics": ["Deadlock"]}}, {"metadata": None}, {}]
    assert taxonomy.concepts_from_results(results) == ["semaphore", "locks_spinlocks"]
    assert taxonomy.concepts_from_results([]) == []


# ------------------------------------------------------------------ mastery arithmetic
def test_levels():
    assert [level_of(c) for c in (None, 0.0, 0.39, 0.4, 0.74, 0.75, 1.0)] == \
        ["unknown", "weak", "weak", "developing", "developing", "strong", "strong"]


def test_evidence_moves_confidence_a_fixed_fraction_towards_the_score():
    m = LearnerModel(clock=Clock())
    assert m.level("mutex") == "unknown" and m.confidence("mutex") is None
    first = m.record_evidence("mutex", "solid")
    assert first["confidence"] == pytest.approx(0.5 + ALPHA * 0.5) and first["level"] == "developing"
    second = m.record_evidence("mutex", "solid")
    assert second["confidence"] > 0.75 and second["level"] == "strong" and second["change"] > 0
    wrong = m.record_evidence("mutex", "misconception", "thinks a mutex counts permits")
    assert wrong["change"] < 0 and m.concept_state("mutex")["misconceptions"] == ["thinks a mutex counts permits"]
    assert m.concept_state("mutex")["attempts"] == 3


@pytest.mark.parametrize("kind,start,direction", [("solid", 0.5, 1), ("partial", 0.3, 1), ("partial", 0.9, -1),
                                                  ("unclear", 0.5, -1), ("misconception", 0.5, -1)])
def test_each_kind_of_evidence_pushes_the_expected_way(kind, start, direction):
    m = LearnerModel(clock=Clock())
    m.data["users"]["default"] = {"concepts": {"semaphore": {"confidence": start, "attempts": 1, "correct": 0,
                                                              "misconceptions": [], "doubts": [], "evidence": [],
                                                              "last_interaction": None}}}
    assert (m.record_evidence("semaphore", kind)["change"] > 0) == (direction > 0)


def test_asking_again_counts_less_than_answering_and_is_not_an_attempt():
    m = LearnerModel(clock=Clock())
    m.record_doubt(["race_condition"], "what is it?")
    again = m.record_evidence("race_condition", "re_explain")
    assert again["confidence"] < DOUBT_START and m.concept_state("race_condition")["attempts"] == 0
    wrong = LearnerModel(clock=Clock()).record_evidence("race_condition", "unclear")
    assert again["confidence"] > wrong["confidence"]  # re_explain moves less than an unclear answer would


def test_a_doubt_is_remembered_without_changing_existing_mastery():
    m = LearnerModel(clock=Clock())
    new = m.record_doubt(["deadlock"], "what is deadlock?")[0]
    assert new["confidence"] == DOUBT_START and new["change"] == 0
    m.record_evidence("deadlock", "solid")
    before = m.confidence("deadlock")
    m.record_doubt(["deadlock"], "one more question about deadlock")
    assert m.confidence("deadlock") == before and m.concept_state("deadlock")["doubts"] == 2


def test_unknown_concepts_and_kinds_are_refused():
    m = LearnerModel(clock=Clock())
    with pytest.raises(KeyError):
        m.record_evidence("paging", "solid")
    with pytest.raises(ValueError):
        m.record_evidence("mutex", "brilliant")


# ------------------------------------------------------------------ weak concepts
def test_review_candidates_rank_the_weakest_first_and_skip_strong_and_unseen():
    clock = Clock()
    m = LearnerModel(clock=clock)
    m.record_evidence("mutex", "solid"), m.record_evidence("mutex", "solid")  # strong -> not a candidate
    m.record_evidence("race_condition", "misconception", "thinks races need processes")  # weak with a misconception
    m.record_doubt(["semaphore"], "what is a semaphore?")  # developing
    clock.advance(days=3)
    got = m.review_candidates()
    assert [c["id"] for c in got] == ["race_condition", "semaphore"]
    assert "misconception: thinks races need processes" in got[0]["reason"]
    assert got[1]["reason"] == "You asked about it 1 time." and got[0]["priority"] > got[1]["priority"]
    assert m.review_candidates(limit=1)[0]["id"] == "race_condition"


def test_recent_struggle_outranks_an_equally_weak_old_one():
    clock = Clock()
    m = LearnerModel(clock=clock)
    m.record_evidence("monitor", "misconception")
    clock.advance(days=5)
    m.record_evidence("deadlock", "misconception")
    assert [c["id"] for c in m.review_candidates()] == ["deadlock", "monitor"]


def test_profile_summarises_the_whole_taxonomy():
    m = LearnerModel(clock=Clock())
    m.record_evidence("mutex", "solid"), m.record_evidence("mutex", "solid")
    m.record_evidence("deadlock", "misconception")
    m.record_doubt(["semaphore"], "q")
    p = m.profile()
    assert p["summary"] == {"weak": 1, "developing": 1, "strong": 1, "unknown": len(taxonomy.CONCEPTS) - 3}
    assert p["concepts"][0]["id"] == "deadlock" and p["recent_doubts"][0]["concept_id"] == "semaphore"
    assert "related_concepts" in p["concepts"][0]


# ------------------------------------------------------------------ persistence
def test_the_model_survives_a_restart_and_is_written_atomically(tmp_path):
    path = tmp_path / "learner" / "learner.json"
    a = LearnerModel(path, clock=Clock())
    a.record_evidence("semaphore", "partial")
    assert path.exists() and not path.with_suffix(".tmp").exists()
    b = LearnerModel(path, clock=Clock())
    assert b.concept_state("semaphore")["attempts"] == 1 and b.confidence("semaphore") == a.confidence("semaphore")


def test_a_damaged_file_is_set_aside_not_overwritten(tmp_path):
    path = tmp_path / "learner.json"
    path.write_text("{not json", encoding="utf-8")
    m = LearnerModel(path, clock=Clock())
    assert m.profile()["summary"]["weak"] == 0
    assert path.with_suffix(".corrupt").read_text(encoding="utf-8") == "{not json"


def test_users_are_kept_apart(tmp_path):
    path = tmp_path / "learner.json"
    LearnerModel(path, "ann", Clock()).record_evidence("mutex", "solid")
    assert LearnerModel(path, "bob", Clock()).level("mutex") == "unknown"
    assert LearnerModel(path, "ann", Clock()).level("mutex") == "developing"


def test_evidence_history_is_bounded():
    m = LearnerModel(clock=Clock())
    for _ in range(40):
        m.record_evidence("mutex", "solid")
    assert len(m._entry("mutex")["evidence"]) == 20
