"""Phase 3A tests: gold benchmark integrity, metric correctness, evaluator output and determinism.

    python3 -m pytest tests -q
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from src.evaluation import metrics
from src.evaluation.retrieval_evaluator import HEADLINE, run, validate_benchmark

ROOT = Path(__file__).resolve().parents[1]
BENCH_PATH = ROOT / "data/evaluation/retrieval_queries.json"
CHUNKS = ROOT / "data/chunks/chunks.jsonl"
MANIFEST = ROOT / "data/vector_store/index_manifest.json"
needs_index = pytest.mark.skipif(not MANIFEST.exists(), reason="real index not built")


@pytest.fixture(scope="module")
def bench():
    return json.loads(BENCH_PATH.read_text())


@pytest.fixture(scope="module")
def chunk_ids():
    return {json.loads(l)["chunk_id"] for l in CHUNKS.read_text().splitlines()}


# ------------------------------------------------------------------ benchmark integrity
def test_benchmark_schema_is_valid(bench, chunk_ids):
    assert validate_benchmark(bench, chunk_ids) == []
    assert bench["version"] == "1.0" and 60 <= len(bench["queries"]) <= 100


def test_benchmark_is_tied_to_the_frozen_corpus(bench):
    assert bench["corpus"]["chunks_sha256"] == hashlib.sha256(CHUNKS.read_bytes()).hexdigest()


def test_query_ids_unique_and_every_query_has_direct_evidence(bench, chunk_ids):
    ids = [q["query_id"] for q in bench["queries"]]
    assert len(ids) == len(set(ids))
    for q in bench["queries"]:
        grades = [r["relevance"] for r in q["relevant_chunks"]]
        assert grades and set(grades) <= {1, 2} and 2 in grades, q["query_id"]
        assert all(r["chunk_id"] in chunk_ids for r in q["relevant_chunks"]), q["query_id"]


def test_benchmark_covers_both_topics_and_all_difficulties(bench):
    assert {q["topic"] for q in bench["queries"]} == {"Threads", "Synchronisation"}
    assert {q["difficulty"] for q in bench["queries"]} == {"easy", "medium", "hard"}


def test_validator_reports_broken_benchmarks(bench, chunk_ids):
    broken = copy.deepcopy(bench)
    broken["queries"][1]["query_id"] = broken["queries"][0]["query_id"]
    broken["queries"][2]["relevant_chunks"] = []
    broken["queries"][3]["relevant_chunks"][0]["relevance"] = 3
    broken["queries"][4]["relevant_chunks"][0]["chunk_id"] = "no-such-doc::c0000"
    problems = "\n".join(validate_benchmark(broken, chunk_ids))
    for expected in ("duplicate query_id", "no relevant chunks", "relevance must be 1 or 2", "unknown chunk"):
        assert expected in problems


# ------------------------------------------------------------------ metrics
QRELS = {"a": 2, "b": 1, "c": 2}  # three relevant chunks, graded


def test_recall_precision_hit_mrr():
    ranked = ["x", "a", "y", "b", "z"]
    assert metrics.recall_at_k(ranked, QRELS, 1) == 0
    assert metrics.recall_at_k(ranked, QRELS, 5) == pytest.approx(2 / 3)
    assert metrics.precision_at_k(ranked, QRELS, 5) == pytest.approx(2 / 5)
    assert metrics.precision_at_k(["a"], QRELS, 5) == pytest.approx(1 / 5)  # K is the denominator
    assert metrics.hit_at_k(ranked, QRELS, 1) == 0 and metrics.hit_at_k(ranked, QRELS, 2) == 1
    assert metrics.mrr_at_k(ranked, QRELS, 5) == pytest.approx(1 / 2)
    assert metrics.mrr_at_k(ranked, QRELS, 1) == 0


def test_ndcg_uses_graded_relevance():
    ideal = 2 / 1 + 2 / 1.5849625007 + 1 / 2  # grades sorted 2, 2, 1 at ranks 1..3
    got = (2 / 1.5849625007 + 1 / 2.3219280949) / ideal  # "a" at rank 2, "b" at rank 4
    assert metrics.ndcg_at_k(["x", "a", "y", "b"], QRELS, 5) == pytest.approx(got, rel=1e-6)
    assert metrics.ndcg_at_k(["a", "c", "b"], QRELS, 3) == pytest.approx(1.0)
    assert metrics.ndcg_at_k(["c", "a", "b"], QRELS, 3) == pytest.approx(1.0)  # equal grades: order is irrelevant
    assert metrics.ndcg_at_k(["b", "a", "c"], QRELS, 3) < 1.0  # grade 1 ranked above grade 2


def test_average_precision_uses_full_relevant_set():
    assert metrics.average_precision_at_k(["a", "x", "b"], QRELS, 5) == pytest.approx((1 / 1 + 2 / 3) / 3)
    assert metrics.average_precision_at_k(["x", "y"], QRELS, 5) == 0


def test_metrics_handle_empty_inputs():
    assert all(v == 0 for v in metrics.all_metrics([], QRELS).values())
    assert all(v == 0 for v in metrics.all_metrics(["a"], {}).values())


# ------------------------------------------------------------------ evaluator (runs the real Phase 2 retriever)
@pytest.fixture(scope="module")
def small_run(tmp_path_factory, bench):
    if not MANIFEST.exists():
        pytest.skip("real index not built")
    tmp = tmp_path_factory.mktemp("eval")
    subset = dict(bench, queries=bench["queries"][::20])  # 5 queries spread over the benchmark
    (tmp / "bench.json").write_text(json.dumps(subset))
    first = run(tmp / "bench.json", tmp / "a", "subset")
    second = run(tmp / "bench.json", tmp / "b", "subset")
    return {"dir": tmp, "subset": subset, "first": first, "second": second}


@needs_index
def test_evaluator_output_schema_and_valid_metrics(small_run, chunk_ids):
    out = small_run["first"]
    assert {"run", "configuration", "summary", "per_query"} <= set(out)
    assert out["configuration"]["retriever"]["filters"] is None and out["configuration"]["retriever"]["top_k"] == 10
    assert len(out["per_query"]) == len(small_run["subset"]["queries"])
    for r in out["per_query"]:
        assert all(0.0 <= v <= 1.0 for v in r["metrics"].values())
        assert [x["rank"] for x in r["retrieved"]] == list(range(1, 11))
        for x in r["retrieved"]:
            assert x["chunk_id"] in chunk_ids and x["relevance"] in (None, 1, 2)
            assert {"score", "source", "section", "page_start", "slide_start", "filename"} <= set(x)
    assert all(0.0 <= out["summary"]["overall"][k] <= 1.0 for k in HEADLINE)
    assert (small_run["dir"] / "a" / "subset_report.md").read_text().startswith("# Baseline Dense Retrieval")


@needs_index
def test_evaluation_is_deterministic(small_run):
    a, b = copy.deepcopy(small_run["first"]), copy.deepcopy(small_run["second"])
    a["run"].pop("generated_at"), b["run"].pop("generated_at")
    assert a == b


@needs_index
def test_evaluator_refuses_benchmark_for_another_corpus(tmp_path, bench):
    other = dict(bench, corpus=dict(bench["corpus"], chunks_sha256="0" * 64))
    (tmp_path / "b.json").write_text(json.dumps(other))
    with pytest.raises(RuntimeError, match="corpus hash mismatch"):
        run(tmp_path / "b.json", tmp_path / "out")


@needs_index
def test_saved_baseline_matches_the_frozen_benchmark(bench):
    saved = json.loads((ROOT / "data/evaluation/baseline_dense_results.json").read_text())
    assert saved["configuration"]["benchmark"]["sha256"] == hashlib.sha256(BENCH_PATH.read_bytes()).hexdigest()
    assert [r["query_id"] for r in saved["per_query"]] == [q["query_id"] for q in bench["queries"]]
