"""Phase 1 ingestion pipeline: scan -> extract -> clean -> classify -> chunk -> dedup -> validate -> report.

    python -m src.ingestion.pipeline [--source Docs] [--output data]

Deterministic: re-running on the same corpus reproduces document IDs, hashes, chunk IDs and chunk
boundaries; only timestamps change. Raw files under --source are only ever read.
"""
import argparse
import json
import shutil
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import chunker, cleaner, dedup, loaders, metadata, scanner, validate

SUBDIRS = ("raw_extracted", "cleaned", "chunks", "manifests")
PIPELINE_VERSION = "1.0.0"


def _dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _image_only_units(cleaned):
    """Pages/slides with pictures but (almost) no text besides the title: content likely lives in the image."""
    out = []
    for u in cleaned["units"]:
        body = " ".join(b["text"] for b in u["blocks"] if b["type"] != "heading")
        if u["images"] and chunker.count_tokens(body) < 15 and u["number"] != 1:  # title slides are expected to be sparse
            out.append(u["number"])
    return out


def process_document(rec, out_dir, run_ts):
    """Extract, clean and classify one document. Returns (record, cleaned) — cleaned is None on failure."""
    doc = {
        "document_id": rec["document_id"], "filename": rec["filename"], "relative_path": rec["relative_path"],
        "file_type": rec["file_type"], "source": "unknown", "course": metadata.COURSE, "topic_area": rec["topic_area"],
        "subtopic": [], "document_type": "unknown", "module": None, "semester": None, "professor": None,
        "page_count": None, "slide_count": None, "content_hash": None, "file_hash": rec["file_hash"],
        "ingestion_timestamp": run_ts, "absolute_path": rec["absolute_path"], "file_size_bytes": rec["file_size_bytes"],
        "modified_time": rec["modified_time"], "extraction_status": "ok", "extraction_error": None,
    }
    try:
        ext = loaders.extract(rec["absolute_path"], rec["file_type"])
    except Exception as e:  # recorded, never silently skipped
        doc.update(extraction_status="failed", extraction_error=f"{type(e).__name__}: {e}", char_count=0, token_count=0,
                   is_duplicate=False, duplicate_of=None, duplicate_type=None, near_duplicates=[], image_only_units=[])
        return doc, None
    _dump(out_dir / "raw_extracted" / f"{rec['document_id']}.json", {"document_id": rec["document_id"], **ext})
    cleaned, stats = cleaner.clean(ext)
    _dump(out_dir / "cleaned" / f"{rec['document_id']}.json", {"document_id": rec["document_id"], **cleaned})
    (out_dir / "cleaned" / f"{rec['document_id']}.md").write_text(cleaner.to_markdown(cleaned, rec["filename"]), encoding="utf-8")

    blocks = [b for u in cleaned["units"] for b in u["blocks"]]
    text = cleaner.render_blocks(blocks)
    code_chars = sum(len(b["text"]) for b in blocks if b["type"] == "code")
    tokens = chunker.count_tokens(text)
    meta = metadata.classify(rec, ext, text, code_chars, tokens)
    doc.update({k: meta[k] for k in ("source", "subtopic", "document_type", "module", "semester", "professor")})
    doc.update({
        "page_count": ext["page_count"], "slide_count": ext["slide_count"],
        "content_hash": dedup.text_hash(text),
        "title": min((b for b in blocks if b["type"] == "heading"), key=lambda b: b["level"], default={}).get("text"),
        "author": meta["author"], "course_code": meta["course_code"], "lecture_date": meta["lecture_date"],
        "derived_from": meta["derived_from"], "problem_types": meta["problem_types"],
        "layout": ext["layout"], "char_count": len(text), "token_count": tokens,
        "code_char_ratio": round(code_chars / max(len(text), 1), 3),
        "image_only_units": _image_only_units(cleaned),
        "margin_lines_removed": stats["margin_lines_removed"],
        "subtopic_scores": meta["subtopic_scores"],
        "metadata_evidence": meta["metadata_evidence"],
        "file_properties": ext["properties"],  # embedded author/title as found in the file; unverified
    })
    doc["_text"] = text
    return doc, cleaned


def run(source="Docs", output="data"):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.is_dir():
        sys.exit(f"source directory not found: {source}")
    if output == source or source in output.parents:
        sys.exit("refusing to write outputs inside the raw corpus directory")
    for sub in SUBDIRS:  # outputs are fully regenerated each run; never touches the source
        shutil.rmtree(output / sub, ignore_errors=True)
        (output / sub).mkdir(parents=True)
    run_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    records, unsupported, ignored = scanner.scan(source)
    docs, cleaned_by_id = [], {}
    for rec in records:
        doc, cleaned = process_document(rec, output, run_ts)
        docs.append(doc)
        if cleaned is not None:
            cleaned_by_id[doc["document_id"]] = cleaned
        print(f"  [{doc['extraction_status']:6}] {doc['relative_path']}", flush=True)

    ok = [d for d in docs if d["extraction_status"] == "ok"]
    dups = dedup.find_duplicates([{"document_id": d["document_id"], "filename": d["filename"], "file_hash": d["file_hash"],
                                   "text": d["_text"]} for d in ok])
    for d in ok:
        d.update(dups[d["document_id"]])

    chunks = []
    for d in ok:
        cs = chunker.chunk_document(d, cleaned_by_id[d["document_id"]])
        for c in cs:
            c["is_duplicate_document"] = d["is_duplicate"]
        d["chunk_count"] = len(cs)
        chunks += cs
    dup_chunks = dedup.mark_duplicate_chunks(chunks)
    for d in docs:
        d.pop("_text", None)
        d.setdefault("chunk_count", 0)

    issues = validate.validate(docs, chunks)
    manifest = build_manifest(docs, chunks, unsupported, ignored, issues, dup_chunks, run_ts, source)

    _dump(output / "manifests" / "documents.json", docs)
    with open(output / "chunks" / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    _dump(output / "manifests" / "validation.json", issues)
    _dump(output / "manifests" / "corpus_manifest.json", manifest)
    (output / "manifests" / "corpus_report.md").write_text(build_report(docs, chunks, manifest, issues), encoding="utf-8")

    t = manifest["totals"]
    print(f"""
Documents discovered: {t['documents']}
Successfully extracted: {t['extracted']}
Failed: {t['failed']}
Duplicates: {t['duplicate_documents']} exact, {t['near_duplicate_pairs']} near-duplicate/overlap pairs
Total pages/slides: {t['pages']} pages / {t['slides']} slides
Total chunks: {t['chunks']}
Total tokens: {t['chunk_tokens']} ({chunker.TOKENIZER})
Validation: {t['errors']} errors, {t['warnings']} warnings, {t['infos']} info
Outputs: {output}""")
    return 1 if t["errors"] else 0


def build_manifest(docs, chunks, unsupported, ignored, issues, dup_chunks, run_ts, source):
    ok = [d for d in docs if d["extraction_status"] == "ok"]
    levels = Counter(i["level"] for i in issues)
    pairs = sorted({tuple(sorted((d["document_id"], n["document_id"]))) + (n["relation"], n["jaccard"], n["containment"])
                    for d in ok for n in d["near_duplicates"]})
    toks = [c["token_count"] for c in chunks]
    return {
        "generated_at": run_ts,
        "pipeline_version": PIPELINE_VERSION,
        "source_root": source.name,
        "chunking": {"tokenizer": chunker.TOKENIZER, "target_tokens": chunker.TARGET_TOKENS, "max_tokens": chunker.MAX_TOKENS,
                     "qa_max_tokens": chunker.QA_MAX_TOKENS, "min_tokens": chunker.MIN_TOKENS},
        "totals": {
            "documents": len(docs), "extracted": len(ok), "failed": len(docs) - len(ok),
            "duplicate_documents": sum(d["is_duplicate"] for d in ok), "near_duplicate_pairs": len(pairs),
            "pages": sum(d["page_count"] or 0 for d in ok), "slides": sum(d["slide_count"] or 0 for d in ok),
            "chunks": len(chunks), "duplicate_chunks": dup_chunks, "chunk_tokens": sum(toks), "document_tokens": sum(d["token_count"] for d in ok),
            "errors": levels["error"], "warnings": levels["warning"], "infos": levels["info"],
        },
        "documents_by_topic": dict(sorted(Counter(d["topic_area"] for d in docs).items())),
        "documents_by_source": dict(sorted(Counter(d["source"] for d in docs).items())),
        "documents_by_type": dict(sorted(Counter(d["document_type"] for d in docs).items())),
        "documents_by_file_type": dict(sorted(Counter(d["file_type"] for d in docs).items())),
        "chunks_by_type": dict(sorted(Counter(c["chunk_type"] for c in chunks).items())),
        "chunks_by_content_type": dict(sorted(Counter(c["content_type"] for c in chunks).items())),
        "chunk_token_stats": {"min": min(toks), "median": statistics.median(toks), "mean": round(statistics.mean(toks), 1),
                              "max": max(toks)} if toks else {},
        "supported_files": [d["relative_path"] for d in docs],
        "unsupported_files": unsupported,
        "ignored_files": ignored,
        "duplicate_files": [{"document_id": d["document_id"], "duplicate_of": d["duplicate_of"], "type": d["duplicate_type"]}
                            for d in ok if d["is_duplicate"]],
        "near_duplicates": [{"a": a, "b": b, "relation": r, "jaccard": j, "containment": c} for a, b, r, j, c in pairs],
        "extraction_failures": [{"document_id": d["document_id"], "relative_path": d["relative_path"], "error": d["extraction_error"]}
                                for d in docs if d["extraction_status"] != "ok"],
    }


def _row(*cells):
    return "| " + " | ".join(str(c).replace("|", "\\|") for c in cells) + " |"


def build_report(docs, chunks, m, issues):
    t = m["totals"]
    L = [f"# Corpus Ingestion Report", "",
         f"Generated {m['generated_at']} by pipeline v{m['pipeline_version']} from `{m['source_root']}/`.", "",
         "## Summary", "", _row("Metric", "Value"), _row("---", "---")]
    for k, v in [("Documents discovered", t["documents"]), ("Successfully extracted", t["extracted"]), ("Extraction failures", t["failed"]),
                 ("Exact duplicate documents", t["duplicate_documents"]), ("Near-duplicate / overlapping pairs", t["near_duplicate_pairs"]),
                 ("PDF pages", t["pages"]), ("Slides", t["slides"]), ("Chunks", t["chunks"]),
                 ("Chunks with an exact duplicate elsewhere", t["duplicate_chunks"]),
                 ("Chunk tokens", f"{t['chunk_tokens']} ({m['chunking']['tokenizer']})"),
                 ("Validation", f"{t['errors']} errors, {t['warnings']} warnings, {t['infos']} info")]:
        L.append(_row(k, v))
    for title, key in [("Documents by topic", "documents_by_topic"), ("Documents by source", "documents_by_source"),
                       ("Documents by type", "documents_by_type"), ("Documents by file format", "documents_by_file_type"),
                       ("Chunks by type", "chunks_by_type"), ("Chunks by content", "chunks_by_content_type")]:
        L += ["", f"### {title}", ""] + [f"- {k}: {v}" for k, v in m[key].items()]
    s = m["chunk_token_stats"]
    if s:
        L += ["", f"Chunk tokens: min {s['min']}, median {s['median']}, mean {s['mean']}, max {s['max']}. "
                  f"Limits: target {m['chunking']['target_tokens']}, max {m['chunking']['max_tokens']}, "
                  f"Q&A max {m['chunking']['qa_max_tokens']}, merge below {m['chunking']['min_tokens']}."]

    L += ["", "## Documents", "", _row("Document ID", "File", "Topic", "Source", "Type", "Pages/Slides", "Chunks", "Tokens", "Professor", "Duplicate"),
          _row(*["---"] * 10)]
    for d in docs:
        units = f"{d['page_count']} p" if d.get("page_count") else (f"{d['slide_count']} s" if d.get("slide_count") else "-")
        L.append(_row(d["document_id"], d["relative_path"], d["topic_area"], d["source"], d["document_type"], units,
                      d.get("chunk_count", 0), d.get("token_count", 0), d.get("professor") or "-",
                      f"of {d['duplicate_of']}" if d.get("is_duplicate") else "-"))

    L += ["", "## Metadata evidence", "", "Fields are filled only with evidence from the file; everything else is null/unknown.", ""]
    for d in docs:
        if d.get("metadata_evidence"):
            ev = "; ".join(f"{k}: {v}" for k, v in d["metadata_evidence"].items())
            L.append(f"- `{d['document_id']}` - {ev}")
            if d.get("derived_from"):
                L.append(f"  - derived_from: {d['derived_from']}")
            if d.get("file_properties", {}).get("author"):
                L.append(f"  - embedded file author (unverified, not used as professor): {d['file_properties']['author']}")

    L += ["", "## Subtopics", ""]
    for d in docs:
        if d["extraction_status"] == "ok":
            L.append(f"- `{d['document_id']}`: {', '.join(d['subtopic']) or '-'}"
                     + (f" | problem types: {', '.join(d['problem_types'])}" if d.get("problem_types") else ""))

    L += ["", "## Duplicates", ""]
    L += [f"- `{x['document_id']}` is a {x['type']} duplicate of `{x['duplicate_of']}`" for x in m["duplicate_files"]] or ["- No exact duplicate documents."]
    L += [f"- {x['relation']}: `{x['a']}` ~ `{x['b']}` (jaccard {x['jaccard']}, containment {x['containment']})" for x in m["near_duplicates"]] \
        or ["- No near-duplicate or overlapping document pairs."]

    L += ["", "## Files not ingested", ""]
    L += [f"- extraction failure: `{x['relative_path']}` - {x['error']}" for x in m["extraction_failures"]]
    L += [f"- unsupported format: `{x['relative_path']}`" for x in m["unsupported_files"]]
    L += [f"- ignored hidden/system file: `{x}`" for x in m["ignored_files"]]

    L += ["", "## Validation issues", ""]
    by = Counter((i["level"], i["code"]) for i in issues)
    L += [f"- {lvl} `{code}`: {n}" for (lvl, code), n in sorted(by.items())] or ["- None."]
    for lvl in ("error", "warning"):
        rows = [i for i in issues if i["level"] == lvl]
        if rows:
            L += ["", f"### {lvl.title()}s", ""]
            L += [f"- `{i['code']}` {i['chunk_id'] or i['document_id']}: {i['message']}" for i in rows]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="OS-Tutor-RAG Phase 1 ingestion pipeline")
    ap.add_argument("--source", default="Docs", help="raw corpus directory (read-only)")
    ap.add_argument("--output", default="data", help="output directory for generated artifacts")
    args = ap.parse_args(argv)
    return run(args.source, args.output)


if __name__ == "__main__":
    sys.exit(main())
