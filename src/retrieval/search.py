"""Retrieval debugging CLI (not a chatbot: prints ranked chunks, never generates answers).

    python3 -m src.retrieval.search --query "How does Peterson's solution provide mutual exclusion?" --top-k 5
    python3 -m src.retrieval.search --query "..." --filter topic_area=Threads --filter document_type=lecture
"""
import argparse
import json
import sys
from pathlib import Path

from .indexer import CHUNKS, MANIFEST, STORE_DIR
from .retriever import FILTERABLE, Retriever


def parse_filters(items):
    filters = {}
    for item in items or []:
        key, sep, value = item.partition("=")
        if not sep:
            raise ValueError(f"filter {item!r} must look like field=value")
        filters.setdefault(key.strip(), []).append(value.strip())
    return {k: v[0] if len(v) == 1 else v for k, v in filters.items()}


def location(r):
    if r["page_start"] is not None:
        return f"pages {r['page_start']}-{r['page_end']}" if r["page_end"] != r["page_start"] else f"page {r['page_start']}"
    if r["slide_start"] is not None:
        return f"slides {r['slide_start']}-{r['slide_end']}" if r["slide_end"] != r["slide_start"] else f"slide {r['slide_start']}"
    return "no page/slide"


def show(r, max_chars):
    m = r["metadata"]
    extra = [f"{k}: {m[k]}" for k in ("professor", "module", "semester") if m.get(k)]
    if m.get("question_number") is not None:
        extra.append(f"question {m['question_number']} (answer in chunk: {m['has_answer']})")
    if m.get("duplicate_of"):
        extra.append(f"duplicate_of: {m['duplicate_of']}")
    if m.get("near_duplicate_documents"):
        extra.append(f"near-duplicate documents: {', '.join(m['near_duplicate_documents'])}")
    text = r["text"] if max_chars <= 0 or len(r["text"]) <= max_chars else r["text"][:max_chars] + f" … [{len(r['text'])} chars]"
    print(f"""#{r['rank']}  score {r['score']:.4f}  {r['chunk_id']}
    {r['relative_path']}  |  {location(r)}
    section: {r['section']}
    {m['source']} · {m['document_type']} · {m['topic_area']} · {m['chunk_type']}/{m['content_type']}{' · ' + ' · '.join(extra) if extra else ''}
    subtopics: {', '.join(m['subtopics']) or '-'}
    text verified against chunks.jsonl: {r['text_verified']}
    ----
{chr(10).join('    ' + line for line in text.splitlines())}
""")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Dense retrieval over the Phase 1 chunks (debugging tool)")
    ap.add_argument("--query", required=True)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--filter", action="append", metavar="FIELD=VALUE",
                    help=f"repeatable; same field twice means either value. Fields: {', '.join(FILTERABLE)}")
    ap.add_argument("--max-chars", type=int, default=800, help="truncate displayed text (0 = full text)")
    ap.add_argument("--json", action="store_true", help="print results as JSON")
    ap.add_argument("--store", default=STORE_DIR, type=Path)
    ap.add_argument("--manifest", default=MANIFEST, type=Path)
    ap.add_argument("--chunks", default=CHUNKS, type=Path)
    args = ap.parse_args(argv)
    try:
        filters = parse_filters(args.filter)
        with Retriever.open(args.store, args.manifest, args.chunks) as retriever:
            results = retriever.search(args.query, top_k=args.top_k, filters=filters)
    except (ValueError, RuntimeError, FileNotFoundError) as e:
        sys.exit(f"error: {e}")
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    print(f"query: {args.query!r}  top_k={args.top_k}  filters={filters or 'none'}  results={len(results)}\n")
    for r in results:
        show(r, args.max_chars)
    return 0


if __name__ == "__main__":
    sys.exit(main())
