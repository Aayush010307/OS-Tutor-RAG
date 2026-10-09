"""The product retrieval pipeline: hybrid candidates -> intent-aware order -> optional cross-encoder rerank -> final context.

    query -> HybridRRFRetriever (dense + BM25, RRF)          top RETRIEVAL_TOP_K candidates   (frozen, unchanged)
          -> reranker (optional)                              the best RERANKER_TOP_K reordered by cross-encoder score
          -> intent reorder                                   content-type and identifier preference, a few places
          -> top FINAL_CONTEXT_K                              what the LLM sees

`HybridRRFRetriever` is the project's established retrieval result and is used as is; this class wraps it, so the frozen
benchmark runs and their tests are unaffected. The reranker is optional and fails soft: if the model cannot be loaded,
or a call fails, the pipeline serves the hybrid order and says so in `status()` (never an exception for the student).

Each result is the hybrid result with `rank` renumbered and added fields: `rrf_rank` (position in the hybrid list),
`rerank_score` (cross-encoder logit, when reranked), `intent` and `intent_shift`. Results are cached per (query, depth):
the corpus is frozen, so the same query always gives the same answer, and revision sessions re-ask the same topics.
"""
import sys
from collections import OrderedDict

from . import intent as intent_mod
from .hybrid import HybridRRFRetriever


class RagRetriever:
    def __init__(self, hybrid, reranker=None, retrieval_top_k=20, rerank_top_k=20, final_k=5, min_rerank_score=None,
                 intent_aware=True, cache_size=256, prefer=intent_mod.DEFAULT_PREFER):
        self.hybrid, self.reranker = hybrid, reranker
        self.retrieval_top_k, self.rerank_top_k, self.final_k = retrieval_top_k, rerank_top_k, final_k
        self.min_rerank_score, self.intent_aware, self.prefer = min_rerank_score, intent_aware, frozenset(prefer)
        self.cache, self.cache_size = OrderedDict(), cache_size
        self.rerank_error = None  # last reranker failure, for status()
        self.by_id = {c["chunk_id"]: i for i, c in enumerate(hybrid.bm25.chunks)} if hasattr(hybrid, "bm25") else {}

    # ------------------------------------------------------------------ search
    def search(self, query, top_k=None):
        top_k = self.final_k if top_k is None else top_k
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        key = (query, top_k)
        if key in self.cache:
            self.cache.move_to_end(key)
            return [dict(r) for r in self.cache[key]]
        results = self._run(query, top_k)
        self.cache[key] = results
        if len(self.cache) > self.cache_size:
            self.cache.popitem(last=False)
        return [dict(r) for r in results]

    def _run(self, query, top_k):
        candidates = self.hybrid.search(query, top_k=max(top_k, self.retrieval_top_k))
        for pos, r in enumerate(candidates, 1):
            r["rrf_rank"] = pos
        ordered = candidates
        if self.reranker is not None:
            head = candidates[:max(top_k, self.rerank_top_k)]
            try:
                scores = self.reranker.score(query, [r["text"] for r in head])
                for r, s in zip(head, scores):
                    r["rerank_score"] = round(s, 4)
                ordered = sorted(head, key=lambda r: (-r["rerank_score"], r["rrf_rank"]))
                self.rerank_error = None
            except Exception as exc:  # fail soft: the hybrid order is still a good answer
                self.rerank_error = f"{exc.__class__.__name__}: {exc}"
                ordered = candidates
        kind = intent_mod.classify(query)
        names = intent_mod.identifiers(query)
        if self.intent_aware:
            ordered = intent_mod.reorder(ordered, kind, names, self.prefer)
        out = []
        for rank, r in enumerate(ordered[:top_k], 1):
            out.append(r | {"rank": rank, "intent": kind,
                            "intent_shift": intent_mod.shift_for(kind, r, names, self.prefer) if self.intent_aware else 0})
        return out

    # ------------------------------------------------------------------ helpers for the tutor and the API
    def is_relevant(self, results):
        """Is there enough material to answer from? Without a reranker the only honest signal is 'something came back';
        with one, the best cross-encoder score must reach `min_rerank_score` (when configured)."""
        if not results:
            return False
        if self.reranker is not None and self.min_rerank_score is not None:
            scores = [r["rerank_score"] for r in results if "rerank_score" in r]
            return not scores or max(scores) >= self.min_rerank_score
        return True

    def get_chunk(self, chunk_id):
        """One chunk in retriever-result shape (rank None), or None for an unknown id."""
        i = self.by_id.get(chunk_id)
        if i is None:
            return None
        bm25, chunk = self.hybrid.bm25, self.hybrid.bm25.chunks[i]
        return {"rank": None, "score": None, "chunk_id": chunk_id, "document_id": chunk["document_id"],
                "filename": chunk["filename"], "relative_path": chunk["relative_path"],
                "page_start": chunk["page_start"], "page_end": chunk["page_end"],
                "slide_start": chunk["slide_start"], "slide_end": chunk["slide_end"], "section": chunk["section"],
                "text": chunk["text"], "metadata": bm25.payloads[i]}

    def status(self):
        return {"reranker": self.reranker is not None, "reranker_error": self.rerank_error,
                "intent_aware": self.intent_aware, "cache": len(self.cache)}

    def config(self):
        stages = (["cross-encoder rerank"] if self.reranker else []) + (["intent-aware order"] if self.intent_aware else [])
        return {"type": " + ".join(["hybrid"] + stages),
                "retrieval_top_k": self.retrieval_top_k, "rerank_top_k": self.rerank_top_k, "final_k": self.final_k,
                "intent_aware": self.intent_aware, "intent_shift": intent_mod.SHIFT, "type_preference": sorted(self.prefer),
                "min_rerank_score": self.min_rerank_score,
                "reranker": self.reranker.config() if self.reranker else None, "hybrid": self.hybrid.config()}

    def close(self):
        self.hybrid.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def build_retriever(settings, warn=lambda m: print(m, file=sys.stderr)):
    """Open the product pipeline from the settings. A reranker that cannot be loaded is reported once and skipped."""
    hybrid = HybridRRFRetriever.open(store_dir=settings.vector_store_dir)
    reranker = None
    if settings.reranker_enabled:
        try:
            from .reranker import load_reranker
            reranker = load_reranker()
        except Exception as exc:
            warn(f"warning: reranker unavailable, using hybrid retrieval only ({exc.__class__.__name__}: {exc})")
    return RagRetriever(hybrid, reranker, settings.retrieval_top_k, settings.reranker_top_k, settings.final_context_k,
                        settings.rerank_min_score)
