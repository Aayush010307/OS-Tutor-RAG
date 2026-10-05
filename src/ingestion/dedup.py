"""Duplicate detection. Nothing is deleted: relationships are recorded for later retrieval decisions."""
import hashlib
import re
from itertools import combinations

NEAR_JACCARD = 0.8  # near-identical text
OVERLAP_CONTAINMENT = 0.5  # one document largely contained in another (overlapping slides, re-exports)


def normalize(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def text_hash(text):
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def _shingles(text, k=5):
    w = normalize(text).split()
    return {" ".join(w[i:i + k]) for i in range(max(len(w) - k + 1, 1))} if w else set()


def find_duplicates(docs):
    """docs: [{"document_id", "filename", "file_hash", "text"}] in corpus order.
    Returns {document_id: {"is_duplicate", "duplicate_of", "duplicate_type", "near_duplicates"}}."""
    out = {d["document_id"]: {"is_duplicate": False, "duplicate_of": None, "duplicate_type": None, "near_duplicates": []}
           for d in docs}
    # canonical copy = first in corpus order, preferring names without "copy"
    ranked = sorted(docs, key=lambda d: "copy" in d["filename"].lower())
    seen = {}
    for kind, key in (("exact_file", lambda d: d["file_hash"]), ("identical_text", lambda d: text_hash(d["text"]))):
        for d in ranked:
            if out[d["document_id"]]["is_duplicate"] or (kind == "identical_text" and not d["text"].strip()):
                continue
            k = (kind, key(d))
            if k in seen:
                out[d["document_id"]].update(is_duplicate=True, duplicate_of=seen[k], duplicate_type=kind)
            else:
                seen[k] = d["document_id"]
    # ponytail: O(n^2) pairwise shingle comparison, fine for a course corpus; MinHash/LSH past ~5k docs
    sh = {d["document_id"]: _shingles(d["text"]) for d in docs}
    for a, b in combinations(docs, 2):
        sa, sb = sh[a["document_id"]], sh[b["document_id"]]
        if not sa or not sb:
            continue
        inter = len(sa & sb)
        jac, cont = inter / len(sa | sb), inter / min(len(sa), len(sb))
        if jac >= NEAR_JACCARD or cont >= OVERLAP_CONTAINMENT:
            rel = "near_duplicate" if jac >= NEAR_JACCARD else "overlap"
            for x, y in ((a, b), (b, a)):
                out[x["document_id"]]["near_duplicates"].append(
                    {"document_id": y["document_id"], "relation": rel, "jaccard": round(jac, 3), "containment": round(cont, 3)})
    return out


def mark_duplicate_chunks(chunks):
    """Exact (normalized-text) duplicate chunks point at their first occurrence."""
    first = {}
    for c in chunks:
        h = text_hash(c["text"])
        c["duplicate_of"] = first.get(h)
        first.setdefault(h, c["chunk_id"])
    return sum(c["duplicate_of"] is not None for c in chunks)
