"""E1 lexical baseline: Okapi BM25 over the frozen Phase 1 chunks.

Pure BM25: no stemming, stopword list, query expansion or rewriting, embeddings, reranking or hybrid scoring.
The index is built in memory from chunks.jsonl on open (463 chunks, milliseconds). Chunk text is tokenized,
never modified; results resolve the canonical text and provenance exactly like the dense `Retriever`.

    score(q, d) = sum over query tokens t (repeated tokens count again) of
                  idf(t) * tf(t, d) * (k1 + 1) / (tf(t, d) + k1 * (1 - b + b * |d| / avgdl))
    idf(t)      = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))     (Lucene's BM25 idf; never negative)

k1 = 1.2 and b = 0.75 are the standard defaults, fixed before evaluation and not tuned on the benchmark.
Ranking: score descending, ties broken by corpus order (chunks.jsonl line order). Only chunks sharing at least
one token with the query are returned, so a query can yield fewer than top_k results.
"""
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

from .indexer import CHUNKS, DOCUMENTS, build_payload, load_chunks

K1, B = 1.2, 0.75
TOKEN = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")  # lowercase alphanumeric runs; pthread_create stays one token


def tokenize(text):
    return TOKEN.findall(text.lower())


class BM25Retriever:
    def __init__(self, chunks, documents, k1=K1, b=B):
        self.k1, self.b = k1, b
        self.chunks = list(chunks)
        docs = {d["document_id"]: d for d in documents}
        self.payloads = [build_payload(c, docs[c["document_id"]]) for c in self.chunks]
        tfs = [Counter(tokenize(c["text"])) for c in self.chunks]
        self.lengths = [sum(tf.values()) for tf in tfs]
        self.avgdl = sum(self.lengths) / len(tfs)
        self.postings = {}  # token -> [(chunk position, term frequency)] in corpus order
        for i, tf in enumerate(tfs):
            for t, f in tf.items():
                self.postings.setdefault(t, []).append((i, f))
        n = len(tfs)
        self.idf = {t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}

    @classmethod
    def open(cls, chunks_path=CHUNKS, documents_path=DOCUMENTS):
        return cls(load_chunks(chunks_path), json.loads(Path(documents_path).read_text(encoding="utf-8")))

    def scores(self, query):
        """{chunk position: BM25 score} for every chunk sharing a token with the query."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        k1, b, avgdl, out = self.k1, self.b, self.avgdl, {}
        for t in tokenize(query):
            for i, f in self.postings.get(t, ()):
                out[i] = out.get(i, 0.0) + self.idf[t] * f * (k1 + 1) / (f + k1 * (1 - b + b * self.lengths[i] / avgdl))
        return out

    def search(self, query, top_k=5):
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        ranked = sorted(self.scores(query).items(), key=lambda x: (-x[1], x[0]))[:top_k]
        results = []
        for rank, (i, score) in enumerate(ranked, 1):
            chunk, payload = self.chunks[i], self.payloads[i]
            results.append({
                "rank": rank,
                "score": round(score, 6),
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "filename": chunk["filename"],
                "relative_path": chunk["relative_path"],
                "page_start": chunk["page_start"], "page_end": chunk["page_end"],
                "slide_start": chunk["slide_start"], "slide_end": chunk["slide_end"],
                "section": chunk["section"],
                "text": chunk["text"],
                "text_verified": hashlib.sha256(chunk["text"].encode()).hexdigest()[:16] == payload["text_hash"],
                "metadata": payload,
            })
        return results

    def config(self):
        return {"type": "bm25 (E1 lexical baseline)", "k1": self.k1, "b": self.b,
                "idf": "ln(1 + (N - df + 0.5) / (df + 0.5))",
                "tokenizer": "lowercase, regex [a-z0-9]+(?:_[a-z0-9]+)*; no stemming, no stopword list",
                "indexed_text": "canonical chunk text from chunks.jsonl, unmodified",
                "ties": "corpus order", "documents": len(self.chunks), "vocabulary": len(self.idf),
                "avgdl": round(self.avgdl, 4)}

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
