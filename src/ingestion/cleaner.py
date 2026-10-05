"""Conservative cleaning: fix extraction artifacts, then assemble lines into structural blocks.

Block: {"type": heading|paragraph|list_item|code|table|notes, "text", "level"}.
Only clear artifacts are removed (running headers/footers, standalone page numbers, ligatures,
line-wrap hyphenation). Code, equations, bullets and Q/A markers are kept verbatim.
"""
import re
from collections import Counter

from .loaders import BULLET_START

CHAR_MAP = {
    "\ufb01": "fi", "\ufb02": "fl", "\ufb00": "ff", "\ufb03": "ffi", "\ufb04": "ffl",
    "\u00a0": " ", "\u00ad": "", "\u200b": "", "\ufeff": "", "c\u20dd": "\u00a9", "\u20dd": "",
    # Symbol/Wingdings private-use glyphs used as bullets and arrows by Office exports
    "\uf0b7": "\u2022", "\uf0a7": "\u25aa", "\uf0d8": "\u27a2", "\uf076": "\u2756", "\uf0fc": "\u2713",
    "\uf0e0": "\u2192", "\uf0e8": "\u2794", "\uf06e": "\u25a0", "\uf071": "\u2751", "\uf0a8": "\u25a1",
}
CHAR_RE = re.compile("|".join(map(re.escape, sorted(CHAR_MAP, key=len, reverse=True))))
QUOTES = str.maketrans({"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'"})

PAGE_NUMBER = re.compile(r"^(page\s*)?\d{1,4}(\s*(of|/)\s*\d{1,4})?$", re.I)
NUMBERED = re.compile(r"^\s*(\d{1,3})[.)](\s+|(?=[A-Za-z]))")
SUBITEM = re.compile(r"^\s*\(([a-z]|[ivx]{1,4})\)\s")
ANSWER = re.compile(r"^\s*(ans(wer)?|solution|sol)\s*([:.\-\u2013]|$)", re.I)
SUB_BULLET_O = re.compile(r"^o\s+(?=\S)")  # Word's "o" sub-bullet glyph
CAPTION = re.compile(r"^\s*(Figure|Fig\.|Table|Listing)\s+\d+(\.\d+)*\s*:")


def normalize(text):
    return CHAR_RE.sub(lambda m: CHAR_MAP[m.group(0)], text)


def strip_margins(units):
    """Drop running headers/footers: lines in the top 12% / bottom 15% of a page whose digit-normalized text
    repeats on many pages, plus standalone page numbers there. PDFs only (lines carry 'top')."""
    pages = [u for u in units if any("top" in l for l in u["lines"])]
    zone = lambda l: "top" in l and (l["top"] < 0.12 or l["top"] > 0.85) and not ANSWER.match(l["text"])
    key = lambda l: re.sub(r"\d+", "#", l["text"].lower()).strip()
    counts = Counter(k for u in pages for k in {key(l) for l in u["lines"] if zone(l)})
    repeated = {k for k, n in counts.items() if len(pages) >= 3 and n >= max(3, 0.3 * len(pages))}
    removed = 0
    for u in pages:
        keep = [l for l in u["lines"] if not (zone(l) and (key(l) in repeated or PAGE_NUMBER.match(l["text"].strip())))]
        removed += len(u["lines"]) - len(keep)
        u["lines"] = keep
    return removed


def _vocab(units):
    words = Counter()
    for u in units:
        for l in u["lines"]:
            words.update(w.lower() for w in re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)*", l["text"]))
    return words


def _join(prev, cur, vocab):
    m = re.search(r"([A-Za-z][A-Za-z-]*)-$", prev)
    t = re.match(r"[a-z][A-Za-z]*", cur)
    if m and t:  # word broken across lines
        head, tail = m.group(1), t.group(0)
        keep = "-" in head or (f"{head}-{tail}".lower() in vocab and f"{head}{tail}".lower() not in vocab)
        return prev + cur if keep else prev[:-1] + cur
    return prev + " " + cur


def _starts_new(text):
    return bool(NUMBERED.match(text) or SUBITEM.match(text) or ANSWER.match(text) or CAPTION.match(text))


def _code_text(lines):
    """Rebuild code indentation from x offsets (PDF) and straighten typographic quotes."""
    xs = [l["x0"] for l in lines if "x0" in l]
    base = min(xs) if xs else 0
    out = []
    for l in lines:
        text = l["text"].translate(QUOTES).rstrip()
        if "x0" in l and l.get("cw"):  # indentation = x offset + any leading space glyphs
            lead = len(text) - len(text.lstrip(" "))
            text = " " * min(int(round((l["x0"] - base) / l["cw"])) + lead, 40) + text.strip()
        out.append(text)
    return "\n".join(out)


def smooth_code(lines, max_run=4):
    """Short non-prose lines sandwiched between code lines are code too ("While true", "Take_fork (Ri)")."""
    cand = lambda l: l["kind"] == "text" and len(l["text"].strip()) <= 60 and not l["text"].rstrip().endswith((".", ":")) \
        and not BULLET_START.match(l["text"])
    i = 1
    while i < len(lines):
        j = i
        while j < len(lines) and cand(lines[j]):
            j += 1
        if j > i and j - i <= max_run and j < len(lines) and lines[i - 1]["kind"] == "code" and lines[j]["kind"] == "code":
            for l in lines[i:j]:
                l["kind"] = "code"
        i = j + 1


def assemble(unit, vocab, word_bullets):
    smooth_code(unit["lines"])
    blocks, code = [], []
    xs = sorted({round(l["x0"] / 8) for l in unit["lines"] if "x0" in l and BULLET_START.match(l["text"])})

    def flush_code():
        if code:
            blocks.append({"type": "code", "text": _code_text(code), "level": 0})
            code.clear()

    for l in unit["lines"]:
        text, kind = l["text"].strip(), l["kind"]
        if not text:
            continue
        if kind == "code":
            code.append(l)
            continue
        flush_code()
        last = blocks[-1] if blocks else None
        if kind == "heading":
            if last and last["type"] == "heading" and (last["text"].isdigit() or
                                                       (last["level"] == l["level"] and not l["para_break"])):
                last["text"] += " " + text  # "30" + "Condition Variables", or a title wrapped over two lines
                last["level"] = min(last["level"], l["level"])
            else:
                blocks.append({"type": "heading", "text": text, "level": l["level"]})
        elif kind in ("table", "notes"):
            blocks.append({"type": kind, "text": l["text"].strip(), "level": 0})
        elif kind == "bullet" or BULLET_START.match(text) or (word_bullets and SUB_BULLET_O.match(text)):
            level = l["level"]
            if "x0" in l and BULLET_START.match(text) and xs:
                level = xs.index(round(l["x0"] / 8)) if round(l["x0"] / 8) in xs else 0
            if SUB_BULLET_O.match(text) and kind != "bullet":
                level = max(level, 1)
            body = SUB_BULLET_O.sub("", BULLET_START.sub("", text, count=1), count=1)
            if body:
                blocks.append({"type": "list_item", "text": body, "level": level})
        elif last and last["type"] in ("paragraph", "list_item") and l["para_break"] is not True and not _starts_new(text) \
                and not CAPTION.match(last["text"]):  # captions stand alone
            last["text"] = last["text"] + "\n" + text if l["para_break"] == "line" else _join(last["text"], text, vocab)
        else:
            blocks.append({"type": "paragraph", "text": text, "level": 0})
    flush_code()
    for b in blocks:
        if b["type"] in ("paragraph", "list_item", "heading"):
            b["text"] = re.sub(r"[ \t]{2,}", " ", b["text"])
    return blocks


def clean(extracted):
    """Return (cleaned_doc, stats). Input is the loader output; it is not mutated."""
    units = [{**u, "lines": [{**l, "text": normalize(l["text"])} for l in u["lines"]]} for u in extracted["units"]]
    removed = strip_margins(units)
    vocab = _vocab(units)
    word_bullets = extracted["layout"] == "document"
    out = []
    for u in units:
        blocks = assemble(u, vocab, word_bullets)
        out.append({"kind": u["kind"], "number": u["number"], "title": normalize(u["title"]) if u["title"] else None,
                    "images": u["images"], "blocks": blocks})
    return {"layout": extracted["layout"], "units": out}, {"margin_lines_removed": removed}


def render_block(b):
    if b["type"] == "heading":
        return "#" * max(1, min(b["level"], 6)) + " " + b["text"]
    if b["type"] == "list_item":
        return "  " * b["level"] + "- " + b["text"]
    if b["type"] == "code":
        return "```\n" + b["text"] + "\n```"
    if b["type"] == "notes":
        return "Speaker notes: " + b["text"]
    return b["text"]


def render_blocks(blocks):
    """Markdown-ish rendering; consecutive list items stay on adjacent lines."""
    out = ""
    for i, b in enumerate(blocks):
        if i:
            out += "\n" if b["type"] == "list_item" and blocks[i - 1]["type"] == "list_item" else "\n\n"
        out += render_block(b)
    return out


def to_markdown(cleaned, filename):
    parts = [f"<!-- {filename} -->"]
    for u in cleaned["units"]:
        label = f"{u['kind']} {u['number']}" if u["number"] is not None else u["kind"]
        parts.append(f"\n<!-- {label} -->\n" + render_blocks(u["blocks"]))
    return "\n".join(parts) + "\n"
