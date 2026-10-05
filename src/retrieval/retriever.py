"""Baseline dense retriever: embed the query, search Qdrant, return ranked chunks with provenance.

No reranking, no hybrid search, no generation. Chunk text comes from the canonical chunks.jsonl.
"""
import hashlib
import json
from pathlib import Path

from .embeddings import load_model
from .indexer import CHUNKS, MANIFEST, STORE_DIR, load_chunks, sha256_file
from .vector_store import QdrantStore

# Exact-match filters over payload fields (list fields such as subtopics match if any element matches).
FILTERABLE = ("topic_area", "document_type", "source", "professor", "module", "semester", "content_type", "chunk_type",
              "course", "document_id", "filename", "subtopics", "problem_types")


def check_filters(filters):
    """Validate a {field: value | [values]} filter. Values are used verbatim; nothing is inferred."""
    if not filters:
        return None
    unknown = sorted(set(filters) - set(FILTERABLE))
    if unknown:
        raise ValueError(f"unknown filter field(s) {unknown}; filterable: {list(FILTERABLE)}")
    for k, v in filters.items():
        values = v if isinstance(v, (list, tuple)) else [v]
        if not values or any(not isinstance(x, str) or not x for x in values):
            raise ValueError(f"filter {k!r} needs non-empty string value(s); null/unknown metadata cannot be filtered on")
    return dict(filters)


class Retriever:
    def __init__(self, model, store, collection, chunks):
        self.model, self.store, self.collection = model, store, collection
        self.chunks = {c["chunk_id"]: c for c in chunks}

    @classmethod
    def open(cls, store_dir=STORE_DIR, manifest_path=MANIFEST, chunks_path=CHUNKS):
        """Open the persisted index and refuse to serve results from a stale or mismatched index."""
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        if sha256_file(chunks_path) != manifest["corpus"]["chunks_sha256"]:
            raise RuntimeError(f"{chunks_path} changed since the index was built; rebuild with "
                               "`python3 -m src.retrieval.indexer --recreate`")
        model = load_model(manifest["embedding"]["model"])
        if (model.spec.revision, model.dim) != (manifest["embedding"]["revision"], manifest["embedding"]["dim"]):
            raise RuntimeError("embedding model spec differs from the one recorded in the index manifest")
        store = QdrantStore(store_dir)
        name = manifest["vector_store"]["collection"]
        if not store.exists(name) or store.count(name) != manifest["counts"]["indexed"]:
            store.close()
            raise RuntimeError(f"collection {name!r} is missing or incomplete in {store_dir}")
        return cls(model, store, name, load_chunks(chunks_path))

    def search(self, query, top_k=5, filters=None):
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        hits = self.store.search(self.collection, self.model.embed_query(query), top_k, check_filters(filters))
        results = []
        for rank, (_, score, payload) in enumerate(hits, 1):
            chunk = self.chunks[payload["chunk_id"]]
            results.append({
                "rank": rank,
                "score": round(float(score), 6),
                "chunk_id": payload["chunk_id"],
                "document_id": payload["document_id"],
                "filename": payload["filename"],
                "relative_path": payload["relative_path"],
                "page_start": payload["page_start"], "page_end": payload["page_end"],
                "slide_start": payload["slide_start"], "slide_end": payload["slide_end"],
                "section": payload["section"],
                "text": chunk["text"],
                "text_verified": hashlib.sha256(chunk["text"].encode()).hexdigest()[:16] == payload["text_hash"],
                "metadata": payload,
            })
        return results

    def close(self):
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
