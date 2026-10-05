"""Phase 3B E1 tests: BM25 lexical baseline, evaluator compatibility and frozen inputs.

    python3 -m pytest tests -q
"""
import copy
import hashlib
import json
import math
from pathlib import Path

import pytest

from src.evaluation import metrics
from src.evaluation.compare import build as build_comparison
from src.evaluation.retrieval_evaluator import run
from src.retrieval.bm25 import BM25Retriever, tokenize
from src.retrieval.indexer import build_payload

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data/chunks/chunks.jsonl"
DOCUMENTS = ROOT / "data/manifests/documents.json"
V11 = ROOT / "data/evaluation/retrieval_queries_v1.1.json"
E1 = ROOT / "data/evaluation/e1_bm25"
V11_SHA256 = "bfbbd033021a154f969d284483b73416c4c7b9b3f1afc126b1609dd650bd5986"
CHUNKS_SHA256 = "90d1e88ef552dfb32b5a8c2d4845cd20399eca82f6669bd184d08eaad8fcbe16"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def bm25():
    return BM25Retriever.open(CHUNKS, DOCUMENTS)


@pytest.fixture(scope="module")
def canonical():
    return [json.loads(l) for l in CHUNKS.read_text(encoding="utf-8").splitlines()]


def toy(texts):
    chunks = [{"chunk_id": f"toy::c{i:04d}", "document_id": "toy", "text": t, "filename": "toy.pdf",
               "relative_path": "Docs/toy.pdf", "page_start": 1, "page_end": 1, "slide_start": None,
               "slide_end": None, "section": None} for i, t in enumerate(texts)]
    return BM25Retriever(chunks, [{"document_id": "toy"}])


# ------------------------------------------------------------------ frozen inputs
def test_frozen_benchmark_and_chunks_unchanged():
    assert sha(V11) == V11_SHA256
    assert sha(CHUNKS) == CHUNKS_SHA256


# ------------------------------------------------------------------ BM25 index and scoring
def test_tokenizer_is_simple_and_keeps_identifiers():
    assert tokenize("Pass &i to pthread_create(): Peterson's test-and-set!") == \
        ["pass", "i", "to", "pthread_create", "peterson", "s", "test", "and", "set"]


def test_scores_match_hand_computed_bm25():
    r = toy(["lock lock mutex", "semaphore wait", "lock semaphore semaphore semaphore"])  # avgdl 3
    idf = math.log(1 + (3 - 2 + 0.5) / (2 + 0.5))  # "lock" and "semaphore" both have df 2
    expected = {0: idf * 2 * 2.2 / (2 + 1.2 * (0.25 + 0.75 * 3 / 3)),
                1: idf * 1 * 2.2 / (1 + 1.2 * (0.25 + 0.75 * 2 / 3)),
                2: idf * 1 * 2.2 / (1 + 1.2 * (0.25 + 0.75 * 4 / 3)) + idf * 3 * 2.2 / (3 + 1.2 * (0.25 + 0.75 * 4 / 3))}
    got = r.scores("Lock, semaphore?")
    assert got.keys() == expected.keys() and all(got[i] == pytest.approx(v, rel=1e-12) for i, v in expected.items())
    assert [x["chunk_id"] for x in r.search("lock semaphore", 3)] == ["toy::c0002", "toy::c0000", "toy::c0001"]


def test_ties_follow_corpus_order_and_only_matching_chunks_return():
    r = toy(["mutex lock", "condition variable", "mutex lock"])
    assert [x["chunk_id"] for x in r.search("mutex", 10)] == ["toy::c0000", "toy::c0002"]  # fewer than top_k
    assert r.search("semaphore", 5) == []


def test_index_is_built_over_the_exact_frozen_chunks(bm25, canonical):
    assert [c["chunk_id"] for c in bm25.chunks] == [c["chunk_id"] for c in canonical]
    assert [c["text"] for c in bm25.chunks] == [c["text"] for c in canonical]  # text not altered
    cfg = bm25.config()
    assert cfg["documents"] == 463 and cfg["vocabulary"] > 0 and (cfg["k1"], cfg["b"]) == (1.2, 0.75)
    assert bm25.lengths == [len(tokenize(c["text"])) for c in canonical]


# ------------------------------------------------------------------ retrieval contract
def test_search_returns_ranked_traceable_results(bm25, canonical):
    by_id = {c["chunk_id"]: c for c in canonical}
    docs = {d["document_id"]: d for d in json.loads(DOCUMENTS.read_text())}
    results = bm25.search("How does Peterson's solution provide mutual exclusion?", top_k=20)
    assert [r["rank"] for r in results] == list(range(1, 21))
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True) and scores[-1] > 0
    for r in results:
        c = by_id[r["chunk_id"]]
        assert r["text"] == c["text"] and r["text_verified"] and r["document_id"] == c["document_id"]
        assert r["metadata"] == build_payload(c, docs[c["document_id"]])


def test_top_k_behaviour(bm25):
    q = "What is a semaphore?"
    assert [len(bm25.search(q, top_k=k)) for k in (1, 5, 20, 30)] == [1, 5, 20, 30]
    assert bm25.search(q, top_k=30)[:20] == bm25.search(q, top_k=20)
    for bad in (0, -1, "5", None):
        with pytest.raises(ValueError):
            bm25.search(q, top_k=bad)
    for bad in ("", "   ", None):
        with pytest.raises(ValueError):
            bm25.search(bad)


def test_repeated_retrieval_is_deterministic(bm25):
    other = BM25Retriever.open(CHUNKS, DOCUMENTS)
    for q in json.loads(V11.read_text())["queries"]:
        assert bm25.search(q["query"], top_k=30) == other.search(q["query"], top_k=30)


# ------------------------------------------------------------------ evaluator compatibility
def test_default_metric_set_unchanged_and_depth_20_adds_p10_hit20():
    ranked, qrels = ["x", "a"] + ["y"] * 18, {"a": 2}
    assert list(metrics.all_metrics(ranked, qrels)) == [
        "recall@1", "recall@3", "recall@5", "recall@10", "hit@1", "hit@3", "hit@5", "hit@10",
        "precision@5", "mrr@5", "mrr@10", "ndcg@5", "ndcg@10", "map@5"]
    deep = metrics.all_metrics(ranked, qrels, 20)
    assert deep["precision@10"] == pytest.approx(0.1) and deep["hit@20"] == 1.0


@pytest.fixture(scope="module")
def bm25_runs(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("e1")
    return [run(V11, tmp / d, "bm25", retriever="bm25", top_k=20, deep_k=30) for d in ("a", "b")] + [tmp]


def test_evaluator_runs_bm25_on_v11(bm25_runs):
    out, _, tmp = bm25_runs
    c = out["configuration"]
    assert c["benchmark"]["sha256"] == V11_SHA256 and c["corpus"]["chunks_sha256"] == CHUNKS_SHA256
    assert c["retriever"]["type"].startswith("bm25") and c["retriever"]["top_k"] == 20 and c["retriever"]["deep_k"] == 30
    assert len(out["per_query"]) == 99
    for r in out["per_query"]:
        assert [x["rank"] for x in r["retrieved"]] == list(range(1, 21))
        assert {"precision@10", "hit@20"} <= set(r["metrics"]) and "unjudged_in_top20" in r
        assert all(x["relevance"] in (None, 0, 1, 2) for x in r["retrieved"])
        deep = [x["rank"] for x in r.get("retrieved_deep", [])]
        assert deep == (list(range(21, 31)) if r["query_id"] in ("q009", "q020", "q091") else [])
    assert (tmp / "a" / "bm25_report.md").read_text().startswith("# BM25 Lexical Retrieval")


def test_bm25_evaluation_is_deterministic(bm25_runs):
    a, b = copy.deepcopy(bm25_runs[0]), copy.deepcopy(bm25_runs[1])
    a["run"].pop("generated_at"), b["run"].pop("generated_at")
    assert a == b


def test_saved_e1_runs_match_frozen_inputs_and_dense_baseline():
    bm = json.loads((E1 / "bm25_v1.1_results.json").read_text())
    dense = json.loads((E1 / "dense_v1.1_top20_results.json").read_text())
    frozen = json.loads((ROOT / "data/evaluation/baseline_dense_v1.1_results.json").read_text())
    for out in (bm, dense):
        assert out["configuration"]["benchmark"]["sha256"] == V11_SHA256
        assert [r["query_id"] for r in out["per_query"]] == [r["query_id"] for r in frozen["per_query"]]
    assert dense["configuration"]["retriever"]["vectors_sha256"] == frozen["configuration"]["retriever"]["vectors_sha256"]
    for f, d in zip(frozen["per_query"], dense["per_query"]):  # the depth-20 dense run extends the frozen top 10
        assert d["retrieved"][:10] == f["retrieved"]


def test_comparison_refuses_runs_on_different_benchmarks():
    bm = json.loads((E1 / "bm25_v1.1_results.json").read_text())
    dense = json.loads((E1 / "dense_v1.1_top20_results.json").read_text())
    assert "| ndcg@10 |" in build_comparison(dense, bm, "Dense v1.1", "BM25 E1")
    other = copy.deepcopy(bm)
    other["configuration"]["benchmark"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="benchmark differs"):
        build_comparison(dense, other, "Dense v1.1", "BM25 E1")
