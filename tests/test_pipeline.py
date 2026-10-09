"""Product upgrade tests: query intent, content-type and identifier preference, reranking (fail soft), caching and the
relevance gate. Fake component retrievers and a fake scorer: no index, no model, no Ollama.

    python3 -m pytest tests -q
"""
import pytest

from src.retrieval import intent
from src.retrieval.pipeline import RagRetriever


def cand(cid, text="text", **meta):
    return {"rank": 0, "score": 0.0, "chunk_id": cid, "text": text, "filename": "f.pdf", "metadata": meta}


class Hybrid:
    """Returns a fixed ranked list; records the depth it was asked for."""
    def __init__(self, items):
        self.items, self.depths, self.calls = items, [], 0
        self.bm25 = type("B", (), {"chunks": [{"chunk_id": c["chunk_id"], "document_id": "d", "filename": "f.pdf",
                                                "relative_path": "p", "page_start": 1, "page_end": 1, "slide_start": None,
                                                "slide_end": None, "section": "S", "text": c["text"]} for c in items],
                                   "payloads": [c["metadata"] for c in items]})()

    def search(self, query, top_k=5):
        self.depths.append(top_k)
        self.calls += 1
        return [dict(c, rank=i) for i, c in enumerate(self.items[:top_k], 1)]

    def config(self):
        return {"type": "fake"}

    def close(self):
        self.closed = True


class Scorer:
    def __init__(self, scores):
        self.scores, self.seen = scores, []

    def score(self, query, texts):
        self.seen.append(list(texts))
        return [self.scores[t] for t in texts]

    def config(self):
        return {"model": "fake"}


LECTURE = dict(document_type="lecture", chunk_type="slide", content_type="text")
CODE = dict(document_type="textbook", chunk_type="section", content_type="code")
QA = dict(document_type="practice_problems", chunk_type="qa_pair", content_type="text")


# ------------------------------------------------------------------ query intent
@pytest.mark.parametrize("query,kind", [
    ("What is a semaphore?", "conceptual"), ("Explain the producer-consumer problem", "conceptual"),
    ("What is the dining philosophers problem?", "conceptual"),
    ("How does pthread_mutex_lock work?", "code"), ("Why do we use pthread_join?", "code"),
    ("What does pthread_cond_wait do?", "code"), ("What's wrong with this mutex code?", "code"),
    ("What does sem_wait() return?", "code"),
    ("Give me a problem on race conditions", "practice"), ("quiz me on deadlock", "practice"),
    ("any practice questions on semaphores?", "practice"), ("I need some exercises", "practice"),
])
def test_queries_are_classified(query, kind):
    assert intent.classify(query) == kind


def test_api_identifiers_are_extracted_exactly():
    assert intent.identifiers("Compare pthread_cond_wait and sem_wait(), then pthread_cond_wait again") == \
        ["pthread_cond_wait", "sem_wait"]
    assert intent.identifiers("what is a mutex") == []


def test_preferred_material_moves_up_a_few_places_but_nothing_is_dropped():
    items = [cand("a", **QA), cand("b", **QA), cand("c", **QA), cand("d", **QA), cand("e", **LECTURE)]
    out = [r["chunk_id"] for r in intent.reorder(items, "conceptual", prefer=intent.ALL_TYPES)]
    # e was 5th, moves up 3 places to an effective position of 2; a tie keeps the chunk that was ahead first
    assert out == ["a", "b", "e", "c", "d"]
    assert sorted(out) == list("abcde")  # a reorder, never a filter


def test_a_preferred_chunk_cannot_leap_to_the_top_on_its_own():
    items = [cand(str(i), **QA) for i in range(10)] + [cand("lec", **LECTURE)]
    out = [r["chunk_id"] for r in intent.reorder(items, "conceptual", prefer=intent.ALL_TYPES)]
    assert out.index("lec") == 11 - intent.SHIFT["type"]  # from 11th to 9th: three places, no more


def test_each_intent_prefers_its_own_material():
    deep = [cand(str(i), **LECTURE) for i in range(4)]
    assert [r["chunk_id"] for r in intent.reorder(deep + [cand("code", **CODE)], "code")][2] == "code"
    assert [r["chunk_id"] for r in intent.reorder(deep + [cand("qa", **QA)], "practice")][2] == "qa"
    lec = [r["chunk_id"] for r in intent.reorder(deep + [cand("lec2", **LECTURE)], "conceptual")]
    assert lec == ["0", "1", "2", "3", "lec2"]  # already the preferred kind: order unchanged
    near = intent.reorder([cand("x", **LECTURE), cand("y", **CODE)], "code")
    assert [r["chunk_id"] for r in near] == ["y", "x"]  # from 2nd, three places is enough to reach 1st


def test_an_exact_identifier_match_beats_a_vaguer_neighbour():
    items = [cand("v1", "threads share memory", **LECTURE), cand("v2", "about locks", **LECTURE),
             cand("v3", "about condition variables", **LECTURE), cand("v4", "general threads text", **LECTURE),
             cand("exact", "call pthread_join(t, NULL) to wait", **LECTURE)]
    out = [r["chunk_id"] for r in intent.reorder(items, "code", ["pthread_join"])]
    assert out == ["v1", "v2", "exact", "v3", "v4"]  # 5th -> 3rd


# ------------------------------------------------------------------ the pipeline
def test_the_pipeline_asks_the_hybrid_for_candidates_then_returns_the_final_k():
    items = [cand(f"c{i}", f"t{i}", **LECTURE) for i in range(30)]
    hybrid = Hybrid(items)
    out = RagRetriever(hybrid, retrieval_top_k=20, final_k=5).search("What is a lock?")
    assert hybrid.depths == [20] and [r["rank"] for r in out] == [1, 2, 3, 4, 5]
    assert [r["chunk_id"] for r in out] == ["c0", "c1", "c2", "c3", "c4"]
    assert out[0]["intent"] == "conceptual" and out[0]["rrf_rank"] == 1 and "rerank_score" not in out[0]
    assert len(RagRetriever(Hybrid(items), final_k=5).search("q", top_k=8)) == 8
    with pytest.raises(ValueError):
        RagRetriever(Hybrid(items)).search("q", top_k=0)


def test_the_reranker_reorders_only_the_candidates_it_is_given():
    items = [cand(f"c{i}", f"t{i}", **LECTURE) for i in range(30)]
    scorer = Scorer({f"t{i}": float(i) for i in range(30)})  # later candidates score higher
    out = RagRetriever(Hybrid(items), scorer, retrieval_top_k=25, rerank_top_k=10, final_k=3, intent_aware=False).search("q")
    assert len(scorer.seen[0]) == 10  # RERANKER_TOP_K, not the whole list
    assert [r["chunk_id"] for r in out] == ["c9", "c8", "c7"] and out[0]["rerank_score"] == 9.0
    assert [r["rrf_rank"] for r in out] == [10, 9, 8]


def test_reranker_ties_fall_back_to_the_hybrid_order():
    items = [cand(f"c{i}", f"t{i}", **LECTURE) for i in range(6)]
    out = RagRetriever(Hybrid(items), Scorer({f"t{i}": 1.0 for i in range(6)}), final_k=3, intent_aware=False).search("q")
    assert [r["chunk_id"] for r in out] == ["c0", "c1", "c2"]


def test_a_failing_reranker_degrades_to_hybrid_instead_of_failing_the_student():
    class Broken:
        def score(self, query, texts):
            raise RuntimeError("onnx exploded")
    items = [cand(f"c{i}", f"t{i}", **LECTURE) for i in range(8)]
    pipe = RagRetriever(Hybrid(items), Broken(), final_k=3, intent_aware=False)
    out = pipe.search("q")
    assert [r["chunk_id"] for r in out] == ["c0", "c1", "c2"] and "onnx exploded" in pipe.status()["reranker_error"]


def test_intent_reorder_applies_after_reranking_and_is_reported():
    items = [cand(f"c{i}", f"t{i}", **LECTURE) for i in range(5)] + [cand("code", "t_code", **CODE)]
    scorer = Scorer({f"t{i}": 5.0 - i for i in range(5)} | {"t_code": 0.0})
    out = RagRetriever(Hybrid(items), scorer, final_k=6).search("How does pthread_mutex_lock work?")
    assert out[0]["intent"] == "code" and out[0]["chunk_id"] != "code" and out[3]["chunk_id"] == "code"
    assert out[3]["intent_shift"] > 0 and out[3]["rerank_score"] == 0.0


def test_repeated_queries_are_served_from_the_cache_without_aliasing():
    hybrid = Hybrid([cand(f"c{i}", f"t{i}", **LECTURE) for i in range(8)])
    pipe = RagRetriever(hybrid, final_k=3)
    first = pipe.search("What is a lock?")
    first[0]["text"] = "mutated by a caller"
    second = pipe.search("What is a lock?")
    assert hybrid.calls == 1 and second[0]["text"] != "mutated by a caller"
    pipe.search("What is a semaphore?")
    assert hybrid.calls == 2 and pipe.status()["cache"] == 2


def test_the_cache_is_bounded():
    pipe = RagRetriever(Hybrid([cand("a", **LECTURE)]), cache_size=3)
    for i in range(10):
        pipe.search(f"query {i}")
    assert pipe.status()["cache"] == 3


# ------------------------------------------------------------------ relevance gate and chunk lookup
def test_relevance_gate():
    pipe = RagRetriever(Hybrid([cand("a", **LECTURE)]))
    assert not pipe.is_relevant([]) and pipe.is_relevant([{"x": 1}])  # no reranker: something came back
    gated = RagRetriever(Hybrid([cand("a", "t", **LECTURE)]), Scorer({"t": -9.0}), min_rerank_score=-3.0)
    assert not gated.is_relevant(gated.search("q"))
    assert RagRetriever(Hybrid([cand("a", "t", **LECTURE)]), Scorer({"t": 4.0}), min_rerank_score=-3.0).is_relevant(
        [{"rerank_score": 4.0}])
    assert RagRetriever(Hybrid([cand("a", **LECTURE)]), Scorer({}), min_rerank_score=None).is_relevant([{"x": 1}])


def test_get_chunk_returns_a_retriever_shaped_result_or_none():
    pipe = RagRetriever(Hybrid([cand("a", "alpha text", document_type="lecture")]))
    chunk = pipe.get_chunk("a")
    assert chunk["text"] == "alpha text" and chunk["page_start"] == 1 and chunk["metadata"]["document_type"] == "lecture"
    assert pipe.get_chunk("missing") is None


def test_config_and_status_describe_the_pipeline():
    pipe = RagRetriever(Hybrid([cand("a", **LECTURE)]), Scorer({}), retrieval_top_k=20, final_k=5)
    cfg = pipe.config()
    assert "cross-encoder" in cfg["type"] and cfg["final_k"] == 5 and cfg["reranker"] == {"model": "fake"}
    assert pipe.status()["reranker"] is True


def test_conceptual_queries_have_no_content_type_preference_by_default():
    """Measured on benchmark v1.1 (E3): preferring lecture/textbook chunks for conceptual queries lowered nDCG@10."""
    items = [cand("a", **QA), cand("b", **QA), cand("c", **QA), cand("d", **QA), cand("e", **LECTURE)]
    assert [r["chunk_id"] for r in intent.reorder(items, "conceptual")] == list("abcde")
    assert intent.CODE in intent.DEFAULT_PREFER and intent.PRACTICE in intent.DEFAULT_PREFER
    assert intent.CONCEPTUAL not in intent.DEFAULT_PREFER and intent.CONCEPTUAL in intent.ALL_TYPES
    pipe = RagRetriever(Hybrid([cand(f"c{i}", **QA) for i in range(5)] + [cand("lec", **LECTURE)]), final_k=6)
    assert [r["chunk_id"] for r in pipe.search("What is a semaphore?")][-1] == "lec"
    assert pipe.config()["type_preference"] == ["code", "practice"]
    all_types = RagRetriever(Hybrid([cand(f"c{i}", **QA) for i in range(5)] + [cand("lec", **LECTURE)]), final_k=6,
                             prefer=intent.ALL_TYPES)
    assert [r["chunk_id"] for r in all_types.search("What is a semaphore?")].index("lec") == 3


def test_an_exact_identifier_still_promotes_when_no_content_type_is_preferred():
    items = [cand("v1", "text", **LECTURE), cand("v2", "text", **LECTURE), cand("v3", "text", **LECTURE),
             cand("exact", "pthread_join waits", **LECTURE)]
    assert [r["chunk_id"] for r in intent.reorder(items, "code", ["pthread_join"], prefer=frozenset())][1] == "exact"
