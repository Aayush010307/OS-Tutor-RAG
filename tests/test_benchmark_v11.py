"""Phase 3B-0 tests: benchmark v1.1 is a pure judgment expansion of the frozen v1.0.

    python3 -m pytest tests -q
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from src.evaluation.retrieval_evaluator import validate_benchmark

ROOT = Path(__file__).resolve().parents[1]
V10 = ROOT / "data/evaluation/retrieval_queries.json"
V11 = ROOT / "data/evaluation/retrieval_queries_v1.1.json"
CHUNKS = ROOT / "data/chunks/chunks.jsonl"
V10_SHA256 = "370b7c3393079fe30ef9cff5402aa23a2762736b24227a6cde572e926f57abb1"
CHUNKS_SHA256 = "90d1e88ef552dfb32b5a8c2d4845cd20399eca82f6669bd184d08eaad8fcbe16"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def v10():
    return json.loads(V10.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def v11():
    return json.loads(V11.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def chunk_ids():
    return {json.loads(l)["chunk_id"] for l in CHUNKS.read_text().splitlines()}


def test_v10_and_corpus_are_unchanged():
    assert sha(V10) == V10_SHA256
    assert sha(CHUNKS) == CHUNKS_SHA256


def test_v11_header_links_parent_and_corpus(v10, v11):
    assert v11["version"] == "1.1" and v11["parent_version"] == "1.0"
    assert v11["parent"] == {"path": "data/evaluation/retrieval_queries.json", "sha256": V10_SHA256}
    assert v11["corpus"] == v10["corpus"] and v11["corpus"]["chunks_sha256"] == sha(CHUNKS)
    assert v11["annotation"]["1.0"] == v10["annotation"]
    assert v11["pooling"]["depth"] == 20 and v11["pooling"]["deep_pool"] == {"depth": 30, "queries": ["q009", "q020", "q091"]}


def test_v11_schema_is_valid(v11, chunk_ids):
    assert validate_benchmark(v11, chunk_ids) == []


def test_every_v10_query_and_judgment_is_preserved(v10, v11):
    assert [q["query_id"] for q in v11["queries"]] == [q["query_id"] for q in v10["queries"]]
    for old, new in zip(v10["queries"], v11["queries"]):
        assert {k: v for k, v in new.items() if k not in ("relevant_chunks", "nonrelevant_chunks")} == \
               {k: v for k, v in old.items() if k != "relevant_chunks"}, old["query_id"]
        carried = [{"chunk_id": r["chunk_id"], "relevance": r["relevance"]}
                   for r in new["relevant_chunks"] if r["added_in"] == "1.0"]
        assert carried == old["relevant_chunks"], old["query_id"]


def test_judgment_ids_grades_and_provenance(v11, chunk_ids):
    ids = [q["query_id"] for q in v11["queries"]]
    assert len(ids) == len(set(ids))
    for q in v11["queries"]:
        rel, non = q["relevant_chunks"], q["nonrelevant_chunks"]
        judged = [r["chunk_id"] for r in rel + non]
        assert len(judged) == len(set(judged)) and set(judged) <= chunk_ids, q["query_id"]
        assert all(r["relevance"] in (1, 2) and r["added_in"] in ("1.0", "1.1") for r in rel), q["query_id"]
        assert all(r["relevance"] == 0 and r["added_in"] == "1.1" for r in non), q["query_id"]
        assert all(r["relevance"] == 1 for r in rel if r["added_in"] == "1.1"), q["query_id"]  # no new grade 2 in v1.1


def test_serialization_is_canonical(v11):
    raw = V11.read_text(encoding="utf-8")
    assert json.dumps(v11, ensure_ascii=False, indent=2) + "\n" == raw
    for q in v11["queries"]:
        assert q["relevant_chunks"] == sorted(q["relevant_chunks"], key=lambda r: (-r["relevance"], r["chunk_id"]))
        assert q["nonrelevant_chunks"] == sorted(q["nonrelevant_chunks"], key=lambda r: r["chunk_id"])


def test_validator_reports_broken_nonrelevant_judgments(v11, chunk_ids):
    broken = copy.deepcopy(v11)
    qs = [q for q in broken["queries"] if q["nonrelevant_chunks"]]
    qs[0]["nonrelevant_chunks"][0]["relevance"] = 1
    qs[1]["nonrelevant_chunks"][0]["chunk_id"] = qs[1]["relevant_chunks"][0]["chunk_id"]
    qs[2]["nonrelevant_chunks"][0]["chunk_id"] = "no-such-doc::c0000"
    problems = "\n".join(validate_benchmark(broken, chunk_ids))
    for expected in ("nonrelevant relevance must be 0", "duplicate chunk in judgments", "unknown chunk"):
        assert expected in problems


def test_v11_baseline_scores_the_unchanged_retriever():
    old = json.loads((ROOT / "data/evaluation/baseline_dense_results.json").read_text())
    new = json.loads((ROOT / "data/evaluation/baseline_dense_v1.1_results.json").read_text())
    assert new["configuration"]["benchmark"]["sha256"] == sha(V11)
    assert new["configuration"]["retriever"] == old["configuration"]["retriever"]
    for a, b in zip(old["per_query"], new["per_query"], strict=True):
        assert [(x["chunk_id"], x["score"]) for x in a["retrieved"]] == [(x["chunk_id"], x["score"]) for x in b["retrieved"]]
        assert all(x["relevance"] in (0, 1, 2) for x in b["retrieved"]), b["query_id"]  # top 10 fully judged
