"""Phase 2 tests: embeddings, Qdrant index, baseline retrieval, filters, smoke queries.

    python3 -m pytest tests -q

Index tests build a small index in a temp dir. Tests marked with the real index read the persisted
data/vector_store/ build (skipped if it has not been built yet).
"""
import json
from pathlib import Path

import numpy as np
import pytest

from src.retrieval import indexer
from src.retrieval.embeddings import MODELS, load_model
from src.retrieval.retriever import Retriever
from src.retrieval.search import parse_filters
from src.retrieval.search import main as search_main
from src.retrieval.vector_store import QdrantStore, point_id

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data/chunks/chunks.jsonl"
DOCUMENTS = ROOT / "data/manifests/documents.json"
MANIFEST = ROOT / "data/vector_store/index_manifest.json"
SMOKE = json.loads((Path(__file__).parent / "retrieval_smoke_queries.json").read_text())
needs_index = pytest.mark.skipif(not MANIFEST.exists(), reason="real index not built (python3 -m src.retrieval.indexer)")


@pytest.fixture(scope="module")
def model():
    return load_model()


@pytest.fixture(scope="module")
def chunks():
    return [json.loads(l) for l in CHUNKS.read_text().splitlines()]


@pytest.fixture(scope="module")
def small_index(tmp_path_factory, model, chunks):
    """First chunk of every document plus one Q&A chunk: covers pages, slides and questions."""
    tmp = tmp_path_factory.mktemp("index")
    picked, seen = [], set()
    for c in chunks:
        if c["document_id"] not in seen or (c["chunk_type"] == "qa_pair" and c["question_number"] == 21):
            picked.append(c)
            seen.add(c["document_id"])
    (tmp / "chunks.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in picked))
    manifest = indexer.build_index(tmp / "chunks.jsonl", DOCUMENTS, tmp / "qdrant", tmp / "manifest.json", model=model)
    return {"dir": tmp, "chunks": picked, "manifest": manifest}


@pytest.fixture(scope="module")
def retriever():
    if not MANIFEST.exists():
        pytest.skip("real index not built")
    r = Retriever.open(ROOT / "data/vector_store/qdrant", MANIFEST, CHUNKS)
    yield r
    r.close()


# ------------------------------------------------------------------ embeddings
def test_model_loads_with_expected_dimension(model):
    assert model.dim == MODELS["nomic-embed-text-v1.5"].dim == 768
    vecs = model.embed_documents(["A mutex provides mutual exclusion.", "Threads share an address space."])
    assert vecs.shape == (2, 768) and vecs.dtype == np.float32
    assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0, atol=1e-5)


def test_query_embedding_uses_query_prefix(model):
    text = "condition variables and missed wakeups"
    q, d = model.embed_query(text), model.embed_documents([text])[0]
    assert q.shape == (768,) and abs(float(np.linalg.norm(q)) - 1) < 1e-5
    assert not np.array_equal(q, d)  # "search_query: " vs "search_document: "


def test_empty_and_invalid_input_is_rejected(model):
    for bad in ["", "   ", None, 42]:
        with pytest.raises(ValueError):
            model.embed_query(bad)
    with pytest.raises(ValueError):
        model.embed_documents(["fine", ""])
    with pytest.raises(ValueError):
        model.embed_documents("a string, not a list")
    assert model.embed_documents([]).shape == (0, 768)


def test_overlong_input_is_refused_not_truncated(model):
    with pytest.raises(ValueError, match="refusing to truncate"):
        model.embed_documents(["semaphore " * 3000])


def test_embeddings_are_deterministic(model):
    text = "pthread_cond_wait() releases the mutex and sleeps atomically."
    assert model.embed_documents([text]).tobytes() == model.embed_documents([text]).tobytes()


def test_embedding_space_is_sane(model):
    q = model.embed_query("How do semaphores work?")
    near, far = model.embed_documents(["A semaphore has wait and signal operations on an integer counter.",
                                       "Page tables translate virtual addresses into physical frames."])
    assert float(q @ near) > float(q @ far)


# ------------------------------------------------------------------ index
def test_small_index_counts_dims_and_manifest(small_index):
    m = small_index["manifest"]
    n = len(small_index["chunks"])
    assert m["counts"] == {"source_chunks": n, "embedded": n, "indexed": n, "failures": []}
    assert (m["vector_store"]["dim"], m["vector_store"]["distance"]) == (768, "Cosine")
    assert m["embedding"]["revision"] == MODELS["nomic-embed-text-v1.5"].revision


def test_index_reopens_and_payload_is_preserved(small_index):
    name = small_index["manifest"]["vector_store"]["collection"]
    with QdrantStore(small_index["dir"] / "qdrant") as store:  # a fresh client: reads what was persisted
        assert store.count(name) == len(small_index["chunks"])
        assert store.config(name) == {"dim": 768, "distance": "Cosine"}
        points = {p.payload["chunk_id"]: p for p in store.all_points(name)}
    docs = {d["document_id"]: d for d in json.loads(DOCUMENTS.read_text())}
    assert len(points) == len(small_index["chunks"])
    for c in small_index["chunks"]:
        p = points[c["chunk_id"]]
        assert str(p.id) == point_id(c["chunk_id"]) and len(p.vector) == 768
        for k in indexer.CHUNK_FIELDS:
            assert p.payload[k] == c[k], k
        d = docs[c["document_id"]]
        assert (p.payload["course"], p.payload["professor"], p.payload["module"], p.payload["semester"]) == \
               (d["course"], d["professor"], d["module"], d["semester"])
        assert "text" not in p.payload  # canonical text lives only in chunks.jsonl


def test_existing_collection_is_not_replaced_without_recreate(small_index, model):
    d = small_index["dir"]
    with pytest.raises(FileExistsError):
        indexer.build_index(d / "chunks.jsonl", DOCUMENTS, d / "qdrant", d / "other.json", model=model)


def test_invalid_chunks_are_rejected(tmp_path, chunks):
    bad = dict(chunks[0], text="tampered text")  # text no longer matches text_hash
    (tmp_path / "c.jsonl").write_text(json.dumps(chunks[1]) + "\n" + json.dumps(bad) + "\n" + json.dumps(chunks[1]) + "\n")
    with pytest.raises(ValueError) as e:
        indexer.load_chunks(tmp_path / "c.jsonl")
    assert "text_hash" in str(e.value) and "duplicate chunk_id" in str(e.value)


def test_retriever_refuses_stale_index(small_index, tmp_path):
    stale = tmp_path / "chunks.jsonl"
    stale.write_text((small_index["dir"] / "chunks.jsonl").read_text() + "\n")
    with pytest.raises(RuntimeError, match="changed since the index was built"):
        Retriever.open(small_index["dir"] / "qdrant", small_index["dir"] / "manifest.json", stale)


@needs_index
def test_real_index_is_complete_and_matches_chunks(chunks):
    m = json.loads(MANIFEST.read_text())
    assert m["counts"]["source_chunks"] == m["counts"]["embedded"] == m["counts"]["indexed"] == len(chunks) == 463
    assert m["counts"]["failures"] == [] and m["embedding"]["input_tokens"]["over_max"] == 0
    assert len({c["chunk_id"] for c in chunks}) == len(chunks)


# ------------------------------------------------------------------ retrieval
@needs_index
def test_search_returns_ranked_traceable_results(retriever, chunks):
    by_id = {c["chunk_id"]: c for c in chunks}
    results = retriever.search("What is a race condition?", top_k=7)
    assert len(results) == 7 and [r["rank"] for r in results] == list(range(1, 8))
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True) and all(-1 <= s <= 1 for s in scores)
    for r in results:
        c = by_id[r["chunk_id"]]
        assert r["text"] == c["text"] and r["text_verified"]
        assert (r["document_id"], r["filename"], r["relative_path"], r["section"]) == \
               (c["document_id"], c["filename"], c["relative_path"], c["section"])
        assert r["page_start"] is not None or r["slide_start"] is not None


@needs_index
def test_top_k_is_validated(retriever):
    assert len(retriever.search("deadlock", top_k=1)) == 1
    for bad in (0, -3, 2.5):
        with pytest.raises(ValueError):
            retriever.search("deadlock", top_k=bad)


@needs_index
def test_metadata_filters(retriever):
    for filters, check in [
        ({"topic_area": "Threads"}, lambda m: m["topic_area"] == "Threads"),
        ({"document_type": "practice_problems"}, lambda m: m["filename"] == "ps-concurrency.pdf"),
        ({"professor": "Mythili Vutukuru"}, lambda m: m["professor"] == "Mythili Vutukuru"),
        ({"source": ["VIT", "OSTEP (Operating Systems: Three Easy Pieces)"]}, lambda m: m["source"] in ("VIT", "OSTEP (Operating Systems: Three Easy Pieces)")),
        ({"subtopics": "Semaphores", "content_type": "code"}, lambda m: "Semaphores" in m["subtopics"] and m["content_type"] == "code"),
        ({"module": "Module 4"}, lambda m: m["module"] == "Module 4"),
    ]:
        results = retriever.search("How do threads synchronize?", top_k=5, filters=filters)
        assert results and all(check(r["metadata"]) for r in results), filters


@needs_index
def test_nonexistent_and_invalid_filters_are_safe(retriever):
    assert retriever.search("semaphores", filters={"professor": "Nobody Known"}) == []
    with pytest.raises(ValueError, match="unknown filter field"):
        retriever.search("semaphores", filters={"colour": "blue"})
    with pytest.raises(ValueError, match="null/unknown"):
        retriever.search("semaphores", filters={"professor": None})


@needs_index
def test_duplicate_chunks_stay_indexed_and_identifiable(retriever, chunks):
    dups = [c for c in chunks if c["duplicate_of"]]
    assert len(dups) == 4
    dup = dups[-1]  # lecture15.pdf chunk duplicating a Semaphore.ppt - Copy.pptx chunk
    ids = {r["chunk_id"] for r in retriever.search(dup["text"][:300], top_k=5)}
    assert {dup["chunk_id"], dup["duplicate_of"]} <= ids  # both copies are retrievable


@needs_index
@pytest.mark.parametrize("case", SMOKE["queries"], ids=[q["id"] for q in SMOKE["queries"]])
def test_retrieval_smoke(retriever, case):
    results = retriever.search(case["query"], top_k=SMOKE["top_k"])
    hit = any(set(case["expect_subtopics"]) & set(r["metadata"]["subtopics"]) or
              any(t in r["text"].lower() for t in case["expect_terms"]) for r in results)
    assert hit, [(r["chunk_id"], r["metadata"]["subtopics"]) for r in results]


# ------------------------------------------------------------------ CLI
def test_cli_filter_parsing():
    assert parse_filters(["topic_area=Threads", "source=VIT", "source=IIT Bombay"]) == \
           {"topic_area": "Threads", "source": ["VIT", "IIT Bombay"]}
    with pytest.raises(ValueError):
        parse_filters(["no-equals-sign"])


def test_cli_prints_results(capsys, small_index):
    d = small_index["dir"]  # own index: Qdrant local mode allows one open client per store directory
    paths = ["--store", str(d / "qdrant"), "--manifest", str(d / "manifest.json"), "--chunks", str(d / "chunks.jsonl")]
    assert search_main(["--query", "pthread_join", "--top-k", "2", "--json"] + paths) == 0
    out = json.loads(capsys.readouterr().out)
    assert len(out) == 2 and all(r["chunk_id"] and r["relative_path"] and r["text_verified"] for r in out)
    assert search_main(["--query", "semaphore wait", "--top-k", "1", "--filter", "topic_area=Threads"] + paths) == 0
    text = capsys.readouterr().out
    assert "#1  score" in text and "text verified against chunks.jsonl: True" in text
