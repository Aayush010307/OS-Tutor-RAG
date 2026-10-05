"""E2 hybrid retrieval: dense (Phase 2, unchanged) + BM25 (E1, unchanged) fused with Reciprocal Rank Fusion.

    rrf(d) = sum over systems s in {dense, bm25} where d is in s's top `candidate_k` of  1 / (k + rank_s(d))

k = 60 (Cormack, Clarke & Buettcher, SIGIR 2009) and candidate_k = 50 per system, equal weights. All three were
fixed before the first evaluation run and are not tuned on the benchmark. RRF uses ranks only, so the two systems'
incomparable scores (cosine similarity, BM25) never meet. Ranking: fused score descending, ties broken by corpus
order (chunks.jsonl line order), as in BM25. No reranking, MMR, query rewriting or score normalisation.

Each result is the component retriever's result (same text, provenance and payload) with `rank` and `score` (the
RRF value) replaced and `component_ranks` {"dense": rank or None, "bm25": rank or None} added.
"""
from .bm25 import BM25Retriever
from .indexer import CHUNKS, DOCUMENTS
from .retriever import Retriever

RRF_K, CANDIDATE_K = 60, 50


class HybridRRFRetriever:
    def __init__(self, dense, bm25, k=RRF_K, candidate_k=CANDIDATE_K):
        self.dense, self.bm25, self.k, self.candidate_k = dense, bm25, k, candidate_k
        self.order = {c["chunk_id"]: i for i, c in enumerate(bm25.chunks)}  # corpus order, for ties

    @classmethod
    def open(cls, chunks_path=CHUNKS, documents_path=DOCUMENTS, **dense_kwargs):
        return cls(Retriever.open(chunks_path=chunks_path, **dense_kwargs), BM25Retriever.open(chunks_path, documents_path))

    def search(self, query, top_k=5):
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        depth = max(top_k, self.candidate_k)
        fused, ranks, by_id = {}, {}, {}
        for name, system in (("dense", self.dense), ("bm25", self.bm25)):
            for r in system.search(query, top_k=depth):
                cid = r["chunk_id"]
                fused[cid] = fused.get(cid, 0.0) + 1 / (self.k + r["rank"])
                ranks.setdefault(cid, {"dense": None, "bm25": None})[name] = r["rank"]
                by_id.setdefault(cid, r)
        ranked = sorted(fused, key=lambda c: (-fused[c], self.order[c]))[:top_k]
        return [by_id[c] | {"rank": i, "score": round(fused[c], 6), "component_ranks": ranks[c]}
                for i, c in enumerate(ranked, 1)]

    def config(self):
        return {"type": "hybrid dense + bm25, reciprocal rank fusion (E2)", "rrf_k": self.k,
                "candidate_k_per_system": self.candidate_k, "weights": {"dense": 1, "bm25": 1},
                "fusion": "sum of 1 / (rrf_k + rank) over systems; ties by corpus order",
                "bm25": self.bm25.config()}

    def close(self):
        self.dense.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
