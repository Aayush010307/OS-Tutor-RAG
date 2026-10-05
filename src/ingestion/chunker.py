"""Semantic chunking: document -> page/slide -> section -> chunk.

Segments follow the document's own structure: headings (sections, slide titles) for teaching material,
numbered questions/problems for problem sets. A segment becomes one chunk when it fits; oversized
segments split at block boundaries (never inside a code block unless the block alone is too big);
tiny segments merge into their neighbour. Question + answer stay in one chunk up to QA_MAX_TOKENS.
"""
import hashlib
import re

from .cleaner import ANSWER, NUMBERED, render_block, render_blocks
from .metadata import QA_TYPES, chunk_subtopics, problem_types

TARGET_TOKENS = 350  # preferred size when a section must be split
MAX_TOKENS = 600  # sections up to this size stay whole
QA_MAX_TOKENS = 1000  # a question with its answer stays whole up to this size
MIN_TOKENS = 40  # smaller sections merge into a neighbour (Q&A pairs never merge)
TOKENIZER = "tiktoken cl100k_base"
PREVIOUS_Q = re.compile(r"\b(previous|above|preceding) (question|problem)\b|\bcontinu(ing|ation) (on|of) the previous\b", re.I)

_enc = None


def count_tokens(text):
    global _enc
    if _enc is None:
        import tiktoken
        _enc = tiktoken.get_encoding("cl100k_base")
    return len(_enc.encode(text, disallowed_special=()))


def _tok(items):
    return sum(it["tokens"] for it in items)


def _item(block, unit, kind):
    return {"block": block, "unit": unit, "kind": kind, "tokens": count_tokens(render_block(block))}


def question_starts(items):
    """Top-level numbered items with strictly sequential numbers 1, 2, 3, ... (nested lists restart and are skipped)."""
    starts, expected = [], 1
    for i, it in enumerate(items):
        b = it["block"]
        m = NUMBERED.match(b["text"]) if b["type"] in ("paragraph", "heading") else None
        if m and int(m.group(1)) == expected:
            starts.append((i, expected))
            expected += 1
    return starts


def _label(text, n=90):
    first = text.strip().split("\n")[0]
    return first if len(first) <= n else first[:n].rsplit(" ", 1)[0] + " ..."


def _is_answer(it):
    return it["block"]["type"] in ("paragraph", "heading") and bool(ANSWER.match(it["block"]["text"]))


def segment(items, starts):
    """Split at headings (section path from the heading stack) and at question starts.
    A question runs until the next question or a heading at/above the level that contained the questions;
    when questions are themselves headings, only a strictly shallower heading ends one."""
    qstart = dict(starts)
    end_level = None
    if starts:
        first = items[starts[0][0]]["block"]
        before = [it["block"]["level"] for it in items[:starts[0][0]] if it["block"]["type"] == "heading"]
        end_level = first["level"] - 1 if first["type"] == "heading" else (before[-1] if before else 99)
    segs, stack = [], []
    for i, it in enumerate(items):
        b = it["block"]
        if i in qstart:
            segs.append({"items": [it], "path": [t for _, t in stack] + [_label(b["text"])], "kind": "problem", "qnum": qstart[i]})
            continue
        if b["type"] == "heading" and (not segs or segs[-1]["qnum"] is None or b["level"] <= end_level):
            while stack and stack[-1][0] >= b["level"]:
                stack.pop()
            stack.append((b["level"], b["text"]))
            segs.append({"items": [it], "path": [t for _, t in stack], "kind": "section", "qnum": None})
            continue
        if not segs:
            segs.append({"items": [], "path": [], "kind": "section", "qnum": None})
        segs[-1]["items"].append(it)
    for sg in segs:
        if sg["qnum"] is not None and any(map(_is_answer, sg["items"])):
            sg["kind"] = "qa"
    return segs


def _base_title(path):
    t = path[-1] if path else ""
    return re.sub(r"\s*[(\[]?\s*(cont(d|inued)?\.?|part\s*\d+|\d+)\s*[)\]]?\s*$", "", t, flags=re.I).strip().lower()


def merge_small(segs):
    """Slide continuations ("X (cont)", "X (2)") join the previous segment; tiny segments join the next one."""
    out = []
    for s in segs:
        p = out[-1] if out else None
        if p and s["kind"] == p["kind"] == "section" and s["path"] and _base_title(s["path"]) == _base_title(p["path"]) \
                and _tok(p["items"]) + _tok(s["items"]) <= MAX_TOKENS:
            p["items"] += s["items"]
        else:
            out.append(s)
    res, i = [], 0
    while i < len(out):
        s, nxt = out[i], out[i + 1] if i + 1 < len(out) else None
        tiny = s["kind"] == "section" and _tok(s["items"]) < MIN_TOKENS
        limit = MAX_TOKENS if nxt and nxt["kind"] == "section" else QA_MAX_TOKENS
        # join the next segment if it fits, or if that segment gets split anyway (the tiny part rides with part 1)
        if tiny and nxt and (_tok(s["items"]) + _tok(nxt["items"]) <= limit or _tok(nxt["items"]) > limit):
            out[i + 1] = {**nxt, "items": s["items"] + nxt["items"]}
        elif tiny and res and res[-1]["kind"] == "section" and _tok(res[-1]["items"]) + _tok(s["items"]) <= MAX_TOKENS:
            res[-1]["items"] += s["items"]
        else:
            res.append(s)
        i += 1
    return res


def _explode(it, target):
    """Split one oversized block: code/tables/lists by lines, prose by sentences."""
    b = it["block"]
    pieces = b["text"].split("\n") if b["type"] in ("code", "table", "list_item") or "\n" in b["text"] \
        else re.split(r"(?<=[.!?])\s+(?=[A-Z(\"'])", b["text"])
    sep = "\n" if b["type"] in ("code", "table", "list_item") or "\n" in b["text"] else " "
    out, cur = [], []
    for p in pieces:
        if cur and count_tokens(sep.join(cur + [p])) > target:
            out.append(sep.join(cur))
            cur = []
        cur.append(p)
    if cur:
        out.append(sep.join(cur))
    return [_item({**b, "text": t}, it["unit"], it["kind"]) for t in out]


def split_items(items, target, limit):
    ex = []
    for it in items:
        ex += _explode(it, target) if it["tokens"] > limit else [it]
    parts, cur = [], []
    for it in ex:
        if cur and _tok(cur) + it["tokens"] > target:
            keep_together = cur[-1]["block"]["text"].rstrip().endswith(":") and _tok(cur) + it["tokens"] <= limit
            if not keep_together:
                carry = []
                while cur and cur[-1]["block"]["type"] == "heading":  # never end a chunk on a heading
                    carry.insert(0, cur.pop())
                if cur:
                    parts.append(cur)
                cur = carry
        cur.append(it)
    if cur:
        if parts and _tok(cur) < MIN_TOKENS and _tok(parts[-1]) + _tok(cur) <= limit:
            parts[-1] += cur
        else:
            parts.append(cur)
    return parts


def split_segment(seg):
    items = seg["items"]
    if seg["kind"] in ("qa", "problem"):
        if _tok(items) <= QA_MAX_TOKENS:
            return [items]
        k = next((i for i, it in enumerate(items) if _is_answer(it)), None)
        halves = [items[:k], items[k:]] if k else [items]
        return [p for h in halves for p in ([h] if _tok(h) <= QA_MAX_TOKENS else split_items(h, MAX_TOKENS, QA_MAX_TOKENS))]
    return [items] if _tok(items) <= MAX_TOKENS else split_items(items, TARGET_TOKENS, MAX_TOKENS)


def content_type(blocks, text):
    code = [b for b in blocks if b["type"] == "code"]
    ratio = sum(len(b["text"]) for b in code) / max(len(text), 1)
    if ratio >= 0.6:
        return "code"
    if code and (ratio >= 0.1 or sum(b["text"].count("\n") + 1 for b in code) >= 3):
        return "mixed"
    return "text"


def chunk_document(doc, cleaned):
    """doc: document metadata record. Returns the list of chunk dicts."""
    items = [_item(b, u["number"], u["kind"]) for u in cleaned["units"] for b in u["blocks"]]
    if not items:
        return []
    starts = question_starts(items)
    qa_mode = len(starts) >= 3 and (doc["document_type"] in QA_TYPES or sum(map(_is_answer, items)) >= 3)
    segs = merge_small(segment(items, starts if qa_mode else []))
    slides = cleaned["layout"] == "slides"
    chunks = []
    for seg in segs:
        parts = split_segment(seg)
        for pi, part in enumerate(parts, 1):
            blocks = [it["block"] for it in part]
            text = render_blocks(blocks)
            if seg["qnum"] is not None and pi > 1:  # keep the answer traceable to its question
                text = f"[Question {seg['qnum']}, continued: {_label(seg['items'][0]['block']['text'], 150)}]\n\n" + text
            units = [it["unit"] for it in part if it["unit"] is not None]
            kind = part[0]["kind"]
            idx = len(chunks)
            is_q = seg["kind"] in ("qa", "problem")
            chunks.append({
                "chunk_id": f"{doc['document_id']}::c{idx:04d}",
                "document_id": doc["document_id"],
                "chunk_index": idx,
                "text": text,
                "token_count": count_tokens(text),
                "char_count": len(text),
                "filename": doc["filename"],
                "relative_path": doc["relative_path"],
                "source": doc["source"],
                "document_type": doc["document_type"],
                "topic_area": doc["topic_area"],
                "subtopics": chunk_subtopics(text),
                "problem_types": problem_types(text) if is_q else [],
                "page_start": min(units) if kind == "page" and units else None,
                "page_end": max(units) if kind == "page" and units else None,
                "slide_start": min(units) if kind == "slide" and units else None,
                "slide_end": max(units) if kind == "slide" and units else None,
                "section": " > ".join(seg["path"]) or None,
                "section_path": seg["path"],
                "chunk_type": {"qa": "qa_pair", "problem": "problem"}.get(seg["kind"], "slide" if slides else "section"),
                "content_type": content_type(blocks, text),
                "question_number": seg["qnum"],
                "has_answer": any(map(_is_answer, part)) if is_q else None,
                # "Repeat the previous question ..." only makes sense next to that question
                "refers_to_question": seg["qnum"] - 1 if is_q and seg["qnum"] > 1 and PREVIOUS_Q.search(text) else None,
                "part": pi,
                "part_count": len(parts),
                "text_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
            })
    return chunks
