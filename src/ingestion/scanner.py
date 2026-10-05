"""Recursive corpus scanner: finds source files and assigns stable document IDs."""
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

SUPPORTED = {".pdf", ".pptx", ".ppt", ".docx", ".txt", ".md"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def make_doc_id(relative_path):
    """Readable slug + hash of the relative path. Stable across runs; distinct for identical copies."""
    stem = Path(relative_path).stem
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")[:40].strip("-")
    return f"{slug}-{hashlib.sha1(relative_path.encode()).hexdigest()[:8]}"


def scan(source):
    """Return (documents, unsupported, ignored), each sorted by relative path."""
    source = Path(source).resolve()
    docs, unsupported, ignored = [], [], []
    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        rel = path.relative_to(source).as_posix()
        if any(part.startswith(".") for part in path.relative_to(source).parts):
            ignored.append(rel)  # .DS_Store and other hidden/system files
            continue
        ext = path.suffix.lower()
        if ext not in SUPPORTED:
            unsupported.append({"relative_path": rel, "extension": ext, "reason": "unsupported file format"})
            continue
        stat = path.stat()
        parts = path.relative_to(source).parts
        docs.append({
            "document_id": make_doc_id(rel),
            "filename": path.name,
            "relative_path": f"{source.name}/{rel}",
            "absolute_path": str(path),
            "file_type": ext.lstrip("."),
            "file_size_bytes": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds"),
            "file_hash": sha256_file(path),
            # topic_area comes from the corpus folder the file was filed under, not from its filename
            "topic_area": parts[0] if len(parts) > 1 else "unknown",
        })
    return docs, unsupported, ignored
