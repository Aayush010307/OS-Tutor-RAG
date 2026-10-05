"""Phase 3B E2 tests: dense + BM25 hybrid with Reciprocal Rank Fusion, evaluator compatibility, frozen inputs.

    python3 -m pytest tests -q
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from src.evaluation.compare import build as build_comparison, condensed
from src.evaluation.retrieval_evaluator import run
from src.retrieval.hybrid import HybridRRFRetriever

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data/chunks/chunks.jsonl"
DOCUMENTS = ROOT / "data/manifests/documents.json"
V11 = ROOT / "data/evaluation/retrieval_queries_v1.1.json"
E1, E2 = ROOT / "data/evaluation/e1_bm25", ROOT / "data/evaluation/e2_hybrid"
V11_SHA256 = "bfbbd033021a154f969d284483b73416c4c7b9b3f1afc126b1609dd650bd5986"
CHUNKS_SHA256 = "90d1e88ef552dfb32b5a8c2d4845cd20399eca82f6669bd184d08eaad8fcbe16"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Fixed:
    """A component retriever returning a fixed ranking (ignores the query)."""
    def __init__(self, ids):
        self.ids, self.closed = ids, False

    def search(self, query, top_k=5):
        return [{"rank": i, "score": 1.0, "chunk_id": c} for i, c in enumerate(self.ids[:top_k], 1)]

    def close(self):
        self.closed = True


def fused(dense_ids, bm25_ids, corpus, **kw):
    bm25 = Fixed(bm25_ids)
    bm25.chunks = [{"chunk_id": c} for c in corpus]
    return HybridRRFRetriever(Fixed(dense_ids), bm25, **kw)


def test_frozen_benchmark_and_chunks_unchanged():
    assert sha(V11) == V11_SHA256
    assert sha(CHUNKS) == CHUNKS_SHA256


# ------------------------------------------------------------------ RRF
def test_rrf_scores_and_component_ranks():
    h = fused(["a", "b", "c"], ["c", "d", "a"], "abcd")
    got = {r["chunk_id"]: r for r in h.search("q", 4)}
    assert got["a"]["score"] == round(1 / 61 + 1 / 63, 6) and got["c"]["score"] == round(1 / 63 + 1 / 61, 6)
    assert got["b"]["score"] == round(1 / 62, 6) and got["d"]["score"] == round(1 / 62, 6)
    assert got["a"]["component_ranks"] == {"dense": 1, "bm25": 3} and got["d"]["component_ranks"] == {"dense": None, "bm25": 2}
    # a and c tie, b and d tie: corpus order decides
    assert [r["chunk_id"] for r in h.search("q", 4)] == ["a", "c", "b", "d"]
    assert [r["rank"] for r in h.search("q", 4)] == [1, 2, 3, 4]


def test_candidate_depth_limits_each_system():
    h = fused(list("abc"), list("xyz"), "abcxyz", candidate_k=1)  # only rank 1 of each system enters
    assert [r["chunk_id"] for r in h.search("q", 1)] == ["a"]
    assert {r["chunk_id"] for r in h.search("q", 6)} == set("abcxyz")  # top_k beyond candidate_k widens the pool


def test_rejects_bad_top_k_and_closes_dense():
    h = fused(["a"], ["a"], "a")
    for bad in (0, -1, "5", None):
        with pytest.raises(ValueError):
            h.search("q", bad)
    with h:
        pass
    assert h.dense.closed


# ------------------------------------------------------------------ real components
@pytest.fixture  # function scope: local Qdrant allows one client at a time
def hybrid():
    with HybridRRFRetriever.open(CHUNKS, DOCUMENTS) as h:
        yield h


def test_real_hybrid_is_traceable_prefix_stable_and_deterministic(hybrid):
    q = "How does the atomic swap instruction implement mutual exclusion?"
    top30 = hybrid.search(q, 30)
    assert hybrid.search(q, 20) == top30[:20] and hybrid.search(q, 30) == top30
    assert [r["rank"] for r in top30] == list(range(1, 31))
    assert [r["score"] for r in top30] == sorted((r["score"] for r in top30), reverse=True)
    canonical = {c["chunk_id"]: c["text"] for c in hybrid.bm25.chunks}
    assert all(r["text"] == canonical[r["chunk_id"]] and r["text_verified"] for r in top30)
    assert all(any(v is not None for v in r["component_ranks"].values()) for r in top30)
    assert hybrid.config()["rrf_k"] == 60 and hybrid.config()["candidate_k_per_system"] == 50


# ------------------------------------------------------------------ evaluator and saved E2 outputs
def test_saved_e2_run_matches_frozen_inputs_and_a_fresh_run(tmp_path):
    saved = json.loads((E2 / "hybrid_rrf_v1.1_results.json").read_text())
    c = saved["configuration"]
    assert c["benchmark"]["sha256"] == V11_SHA256 and c["corpus"]["chunks_sha256"] == CHUNKS_SHA256
    assert c["retriever"]["type"].startswith("hybrid") and c["retriever"]["top_k"] == 20
    dense = json.loads((E1 / "dense_v1.1_top20_results.json").read_text())
    assert c["retriever"]["dense"]["vectors_sha256"] == dense["configuration"]["retriever"]["vectors_sha256"]
    fresh = run(V11, tmp_path, "hybrid", retriever="hybrid", top_k=20, deep_k=30)
    a, b = copy.deepcopy(saved), copy.deepcopy(fresh)
    a["run"], b["run"] = {}, {}
    a["configuration"]["benchmark"].pop("path"), b["configuration"]["benchmark"].pop("path")  # absolute here
    assert a == b  # rankings, scores, judgments and metrics reproduce exactly
    assert (tmp_path / "hybrid_report.md").read_text().startswith("# Hybrid Dense + BM25 (RRF)")
    for r in fresh["per_query"]:
        assert all("component_ranks" in x for x in r["retrieved"])


def test_comparison_and_condensed_metrics():
    dense = json.loads((E1 / "dense_v1.1_top20_results.json").read_text())
    hyb = json.loads((E2 / "hybrid_rrf_v1.1_results.json").read_text())
    assert "Judged-only" in build_comparison(dense, hyb, "Dense v1.1", "Hybrid E2")
    for r in dense["per_query"]:  # dense top 20 is fully judged, so condensed == standard
        assert condensed(r)["ndcg@10"] == pytest.approx(r["metrics"]["ndcg@10"], abs=1e-6)  # saved values are rounded
    r = {"retrieved": [{"chunk_id": "u", "relevance": None}, {"chunk_id": "a", "relevance": 2}],
         "expected": [{"chunk_id": "a", "relevance": 2}]}
    assert condensed(r)["ndcg@10"] == 1.0  # the unjudged result is skipped

