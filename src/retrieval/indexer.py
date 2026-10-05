"""Build the Qdrant index from the frozen Phase 1 chunks.

    python3 -m src.retrieval.indexer            # first build
    python3 -m src.retrieval.indexer --recreate # explicitly replace an existing collection

Reads data/chunks/chunks.jsonl and data/manifests/documents.json (read-only), embeds every chunk whole,
writes vectors + provenance payloads to data/vector_store/qdrant/ and an index manifest next to it.
The manifest lives in data/vector_store/ (not data/manifests/) because the Phase 1 pipeline regenerates
data/manifests/ on every rebuild.
"""
import argparse
import hashlib
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np

from .embeddings import DEFAULT_MODEL, MODELS, load_model
from .vector_store import POINT_NAMESPACE, QdrantStore, point_id

CHUNKS = Path("data/chunks/chunks.jsonl")
DOCUMENTS = Path("data/manifests/documents.json")
STORE_DIR = Path("data/vector_store/qdrant")
MANIFEST = Path("data/vector_store/index_manifest.json")

REQUIRED = ("chunk_id", "document_id", "text", "filename", "relative_path", "text_hash")
CHUNK_FIELDS = ("chunk_id", "document_id", "chunk_index", "filename", "relative_path", "topic_area", "subtopics",
                "problem_types", "source", "document_type", "page_start", "page_end", "slide_start", "slide_end",
                "section", "section_path", "chunk_type", "content_type", "question_number", "has_answer",
                "refers_to_question", "part", "part_count", "token_count", "text_hash", "is_duplicate_document",
                "duplicate_of")
DOCUMENT_FIELDS = {"course": "course", "module": "module", "semester": "semester", "professor": "professor",
                   "document_subtopics": "subtopic", "document_title": "title", "file_type": "file_type"}


def collection_name(model_key):
    return "os_tutor_chunks__" + re.sub(r"[^a-z0-9]+", "_", model_key.lower()).strip("_")


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_chunks(path=CHUNKS):
    """Parse and validate chunks.jsonl; raises ValueError listing every problem."""
    chunks, problems, seen = [], [], set()
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        try:
            c = json.loads(line)
        except json.JSONDecodeError as e:
            problems.append(f"line {n}: invalid JSON ({e})")
            continue
        missing = [k for k in REQUIRED if not c.get(k)]
        if missing:
            problems.append(f"line {n}: missing {missing}")
        elif c["chunk_id"] in seen:
            problems.append(f"line {n}: duplicate chunk_id {c['chunk_id']}")
        elif hashlib.sha256(c["text"].encode()).hexdigest()[:16] != c["text_hash"]:
            problems.append(f"line {n}: text_hash does not match text")
        seen.add(c.get("chunk_id"))
        chunks.append(c)
    if problems:
        raise ValueError("invalid chunks file:\n  " + "\n  ".join(problems))
    return chunks


def build_payload(chunk, doc):
    """Provenance copied verbatim from Phase 1 (chunk fields + document-level fields joined by document_id).
    The chunk text itself is not stored: it is resolved from chunks.jsonl by chunk_id and checked by text_hash."""
    payload = {k: chunk.get(k) for k in CHUNK_FIELDS}
    payload.update({k: doc.get(src) for k, src in DOCUMENT_FIELDS.items()})
    payload["near_duplicate_documents"] = [n["document_id"] for n in doc.get("near_duplicates", [])]
    return payload


def build_index(chunks_path=CHUNKS, documents_path=DOCUMENTS, store_dir=STORE_DIR, manifest_path=MANIFEST,
                model_key=DEFAULT_MODEL, recreate=False, model=None):
    chunks = load_chunks(chunks_path)
    docs = {d["document_id"]: d for d in json.loads(Path(documents_path).read_text(encoding="utf-8"))}
    orphans = sorted({c["document_id"] for c in chunks} - set(docs))
    if orphans:
        raise ValueError(f"chunks reference documents missing from {documents_path}: {orphans}")
    model = model or load_model(model_key)
    name = collection_name(model.spec.key)

    Path(store_dir).mkdir(parents=True, exist_ok=True)
    with QdrantStore(store_dir) as store:
        if store.exists(name) and not recreate:
            raise FileExistsError(f"collection {name!r} already exists in {store_dir}; pass --recreate to replace it")

        vectors, ok, failures, tokens = [], [], [], []
        for c in chunks:
            try:
                vectors.append(model.embed_documents([c["text"]])[0])
                tokens.append(model.token_count(c["text"]))
                ok.append(c)
            except Exception as e:  # recorded, never silently dropped
                failures.append({"chunk_id": c["chunk_id"], "error": f"{type(e).__name__}: {e}"})
        vectors = np.array(vectors, dtype=np.float32).reshape(len(ok), model.dim)
        payloads = [build_payload(c, docs[c["document_id"]]) for c in ok]

        store.recreate(name, model.dim)
        store.upsert(name, [point_id(c["chunk_id"]) for c in ok], vectors, payloads)
        indexed, cfg = store.count(name), store.config(name)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "phase": 2,
        "corpus": {"chunks_path": str(chunks_path), "chunks_sha256": sha256_file(chunks_path),
                   "documents_path": str(documents_path), "source_chunks": len(chunks)},
        "embedding": {
            "model": model.spec.key, "repo": model.spec.repo, "revision": model.spec.revision,
            "weights_file": model.spec.onnx_file, "weights_sha256": model.weights_sha256(),
            "dim": model.dim, "max_tokens": model.spec.max_tokens, "license": model.spec.license,
            "document_prefix": model.spec.document_prefix, "query_prefix": model.spec.query_prefix,
            "pooling": "mean over tokens, then L2 normalisation",
            "embedded_text": "document_prefix + canonical chunk text, unmodified (no truncation, no added context)",
            "runtime": {"onnxruntime": version("onnxruntime"), "tokenizers": version("tokenizers"),
                        "numpy": version("numpy"), "provider": "CPUExecutionProvider",
                        "intra_op_threads": model.threads, "batch_size": 1},
            "input_tokens": {"max": max(tokens, default=0), "median": statistics.median(tokens) if tokens else 0,
                             "over_512": sum(t > 512 for t in tokens), "over_max": sum(t > model.spec.max_tokens for t in tokens)},
        },
        "vector_store": {
            "engine": "qdrant", "mode": "local embedded mode (QdrantClient(path=...)), persisted on disk",
            "client": "qdrant-client " + version("qdrant-client"), "path": str(store_dir), "collection": name,
            "dim": cfg["dim"], "distance": cfg["distance"],
            "point_id": f"uuid5({POINT_NAMESPACE}, 'os-tutor-rag:' + chunk_id)",
            "text_storage": "not in payload; resolved from chunks.jsonl by chunk_id and verified against text_hash",
        },
        "counts": {"source_chunks": len(chunks), "embedded": len(ok), "indexed": indexed, "failures": failures},
        "digests": {"vectors_sha256": hashlib.sha256(vectors.tobytes()).hexdigest(),
                    "payloads_sha256": hashlib.sha256(json.dumps(payloads, sort_keys=True).encode()).hexdigest()},
    }
    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(manifest_path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description="Embed Phase 1 chunks and build the local Qdrant index")
    ap.add_argument("--model", default=DEFAULT_MODEL, choices=sorted(MODELS))
    ap.add_argument("--recreate", action="store_true", help="replace the collection if it already exists")
    ap.add_argument("--chunks", default=CHUNKS, type=Path)
    ap.add_argument("--documents", default=DOCUMENTS, type=Path)
    ap.add_argument("--store", default=STORE_DIR, type=Path)
    ap.add_argument("--manifest", default=MANIFEST, type=Path)
    args = ap.parse_args(argv)
    try:
        m = build_index(args.chunks, args.documents, args.store, args.manifest, args.model, args.recreate)
    except (FileExistsError, ValueError) as e:
        sys.exit(str(e))
    c, e, v = m["counts"], m["embedding"], m["vector_store"]
    print(f"""Chunks read: {c['source_chunks']}
Embeddings generated: {c['embedded']}
Vectors indexed: {c['indexed']}
Failures: {len(c['failures'])}
Model: {e['model']} @ {e['revision'][:12]} (dim {e['dim']}, max input tokens {e['input_tokens']['max']})
Collection: {v['collection']} ({v['distance']}) at {v['path']}
Manifest: {args.manifest}""")
    return 1 if c["failures"] or c["indexed"] != c["source_chunks"] else 0


if __name__ == "__main__":
    sys.exit(main())
