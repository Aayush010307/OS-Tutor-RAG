"""Corpus validation. Errors mean broken outputs; warnings need a human look; info is recorded for later phases."""
from .chunker import MAX_TOKENS, QA_MAX_TOKENS

MIN_DOC_TOKENS = 100
TINY_CHUNK_TOKENS = 20
PAGED = {"pdf": "page_start", "pptx": "slide_start", "ppt": "slide_start"}


def validate(docs, chunks):
    issues = []

    def add(level, code, message, document_id=None, chunk_id=None):
        issues.append({"level": level, "code": code, "document_id": document_id, "chunk_id": chunk_id, "message": message})

    by_doc = {}
    for c in chunks:
        by_doc.setdefault(c["document_id"], []).append(c)
    doc_ids = {d["document_id"] for d in docs}
    types = {d["document_id"]: d["file_type"] for d in docs}

    for d in docs:
        did = d["document_id"]
        if d["extraction_status"] != "ok":
            add("error", "extraction_failed", d.get("extraction_error") or "extraction failed", did)
            continue
        if not d["char_count"]:
            add("error", "empty_document", "no text extracted", did)
        elif d["token_count"] < MIN_DOC_TOKENS:
            add("warning", "tiny_document", f"only {d['token_count']} tokens extracted", did)
        if d["char_count"] and not by_doc.get(did):
            add("error", "no_chunks", "document produced no chunks", did)
        if d["is_duplicate"]:
            add("info", "duplicate_document", f"{d['duplicate_type']} duplicate of {d['duplicate_of']}", did)
        for n in d["near_duplicates"]:
            if did < n["document_id"]:
                add("info", n["relation"], f"with {n['document_id']} (jaccard={n['jaccard']}, containment={n['containment']})", did)
        if d["image_only_units"]:
            add("warning", "image_only_content",
                f"{len(d['image_only_units'])} page(s)/slide(s) have images but almost no text (no OCR): {d['image_only_units']}", did)

    seen = set()
    for c in chunks:
        cid, did = c.get("chunk_id"), c.get("document_id")
        if cid in seen:
            add("error", "duplicate_chunk_id", "chunk id is not unique", did, cid)
        seen.add(cid)
        if not c.get("text", "").strip():
            add("error", "empty_chunk", "chunk has no text", did, cid)
        if not did or did not in doc_ids:
            add("error", "missing_document_id", "chunk has no valid document_id", did, cid)
        if not c.get("filename") or not c.get("relative_path"):
            add("error", "missing_source_reference", "chunk has no filename/relative_path", did, cid)
        loc = PAGED.get(types.get(did))
        if loc and c.get(loc) is None:
            add("error", "missing_location", f"{loc} is missing", did, cid)
        limit = QA_MAX_TOKENS if c.get("chunk_type") in ("qa_pair", "problem") else MAX_TOKENS
        if c.get("token_count", 0) > limit * 1.1:
            add("warning", "oversized_chunk", f"{c['token_count']} tokens (limit {limit})", did, cid)
        if c.get("token_count", 0) < TINY_CHUNK_TOKENS:
            add("warning", "tiny_chunk", f"only {c.get('token_count')} tokens", did, cid)
    return issues
