"""Evidence-based document metadata and keyword topic classification.

Rule: a field is filled only when the document (its text, filename or embedded slide masters) supports it.
Every inferred field records its evidence in `metadata_evidence`; everything else stays null/"unknown".
"""
import re

COURSE = "Operating Systems"

# ponytail: keyword/regex taxonomy. Transparent and deterministic; swap for an embedding classifier in a
# later phase if recall on paraphrased text matters.
SUBTOPICS = {
    "Threads": {
        "Thread Fundamentals": r"\bthread control block|\blight-?weight process|\bsingle[- ]threaded|\bthread (state|stack)s?\b|\beach thread has\b|\bthreads? (of a process )?share\b|\bper-thread\b",
        "Multithreading": r"\bmulti-?\s?thread(ing|ed)\b",
        "Concurrency": r"\bconcurren(t|cy)\b",
        "Parallelism": r"\bparallel(ism|ly|ize|ization)?\b|\bmulti-?\s?core\b|\bmultiprocessors?\b",
        "Pthreads": r"\bpthreads?\b|\bPOSIX threads?\b|\bpthread_\w+",
        "Thread Creation": r"\bpthread_create\b|\bthread creation\b|\bcreat(e|es|ing|ed) (a |new |multiple |two |the )?(child )?threads?\b",
        "Thread Join": r"\bpthread_join\b|\bthr_join\b|\bjoin(s|ed|ing)? (the |a |child |all )?threads?\b|\bthread join\b",
        "Thread Models": r"\bmany[- ]to[- ]one\b|\bone[- ]to[- ]one\b|\bmany[- ]to[- ]many\b|\btwo[- ]level model\b|\b(multi)?threading models?\b",
        "User-Level Threads": r"\buser[- ]level threads?\b|\buser threads?\b|\bgreen threads?\b|\buser[- ]level threading\b",
        "Kernel Threads": r"\bkernel[- ]level threads?\b|\bkernel threads?\b",
        "Thread Scheduling": r"\bthread scheduling\b|\bscheduler\b|\bcontext switch(es|ed|ing)?\b|\bpreempt(ed|ion|ive|s)?\b",
    },
    "Synchronization": {
        "Race Conditions": r"\brace conditions?\b|\bdata races?\b",
        "Critical Sections": r"\bcritical[- ]sections?\b",
        "Mutual Exclusion": r"\bmutual(ly)? exclusi(on|ve)\b",
        "Locks": r"\b(un)?lock(s|ed|ing)?\b(?!-free)",
        "Mutex": r"\bmutex(es)?\b|\bpthread_mutex_\w+",
        "Spinlocks": r"\bspin[- ]?locks?\b|\bspin(ning|s)?\b|\bbusy[- ]wait(ing|s)?\b",
        "Test-and-Set": r"\btest[- ]and[- ]set\b|\bTestAndSet\b|\bxchg\b|\batomic exchange\b",
        "Compare-and-Swap": r"\bcompare[- ]and[- ](swap|exchange)\b|\bCompareAndSwap\b|\bcmpxchg\b",
        "Condition Variables": r"\bcondition variables?\b|\bpthread_cond_\w+|\bcond_(wait|signal|broadcast)\b",
        "Semaphores": r"\bsemaphores?\b|\bsem_(wait|post|init|t)\b",
        "Monitors": r"\bmonitors?\b",
        "Peterson's Solution": r"\bpeterson'?s?\b",
        "Barriers": r"\bbarriers?\b",
        "Producer-Consumer": r"\bproducers?\b|\bbounded[- ]buffer\b",
        "Readers-Writers": r"\breaders?[- /]*(and[- ])?writers?\b|\breader-writer\b|\brwlock\b",
        "Dining Philosophers": r"\bphilosoph",
        "Deadlock": r"\bdeadlock(s|ed)?\b|\bcircular wait\b|\bhold[- ]and[- ]wait\b|\bbanker'?s algorithm\b",
        "Starvation": r"\bstarv(e|es|ed|ation|ing)\b|\bbounded waiting\b",
        "Concurrency Bugs": r"\bconcurrency bugs?\b|\batomicity[- ]violation\b|\border[- ]violation\b|\bnon-?\s?deadlock bugs?\b|\batomicity bugs?\b",
    },
}
PROBLEM_TYPES = {
    "True/False": r"\[T/F\]|\bTrue\s*/\s*False\b|\bT/F\b",
    "MCQs": r"(?s)(?=.*\(a\).*\(b\).*\(c\))(?=.*(\bwhich of the following\b|\bAns\w*[:.]?\s*\(?[a-d]\)))",
    "Conceptual Questions": r"\bexplain\b|\bdescribe\b|\bwhy\b|\(Yes/No\)|\byes/no\b|\bstate (one|the|two)\b|\bwhat is\b|\bjustify\b",
    "Programming Problems": r"\bwrite (the |a )?(code|pseudocode|program|function|solution)\b|\bstudents must use\b|\bsample (input|output)\b|\bimplement\b",
    "Synchronization Problems": r"\busing (only )?(locks|semaphores|condition variables|mutex(es)?)\b|\bsynchroniz(e|ation) (problem|primitive)s?\b|\bmust use only\b",
    "Debugging Problems": r"\bbug(s|gy)?\b|\bwhat (is|are|went) wrong\b|\bidentify the (bug|problem|error)\b|\bis (this|the (above|following)) (code|solution) correct\b|\bcan deadlock\b",
}
ACRONYMS = {"Thread Fundamentals": r"\bTCB\b", "Compare-and-Swap": r"\bCAS\b", "Condition Variables": r"\bCVs?\b"}  # case-sensitive
_SUB_RE = {name: (re.compile(p, re.I), re.compile(ACRONYMS[name]) if name in ACRONYMS else None)
           for subs in SUBTOPICS.values() for name, p in subs.items()}
_PROB_RE = {name: re.compile(p, re.I) for name, p in PROBLEM_TYPES.items()}


def subtopic_counts(text):
    out = {}
    for name, (rx, acro) in _SUB_RE.items():
        n = len(rx.findall(text)) + (len(acro.findall(text)) if acro else 0)
        if n:
            out[name] = n
    return out


def chunk_subtopics(text):
    return list(subtopic_counts(text))


def doc_subtopics(counts, tokens):
    """A subtopic applies to the whole document when mentioned >= 3 times and >= 1 per 1k tokens."""
    return [k for k, n in counts.items() if n >= 3 and n * 1000 / max(tokens, 1) >= 1.0]


def problem_types(text):
    return [name for name, rx in _PROB_RE.items() if rx.search(text)]


VIT_NAME = re.compile(r"^(?P<sem>(FALL|WINTER|SUM(MER)?)SEM\d{4}-\d{2})_[A-Z]+_(?P<code>[A-Z]{3,5}\d{3}[A-Z]?)_\d+_(?P<kind>[A-Z]+)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<title>.+)$")
INSTITUTIONS = {"IIT Bombay": r"IIT\s*Bombay|Indian Institute of Technology,?\s*Bombay",
                "VIT": r"\bVIT\b|Vellore Institute of Technology"}
PERSON_AT = r"(?:Prof(?:essor)?\.?[ \t]+|Dr\.?[ \t]+)?([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){1,3})\s*[,(]?\s*(?:CSE|Dept\.?[^,]{0,40})?\s*,?\s*(?:%s)"


def classify(record, extracted, cleaned_text, code_chars, tokens):
    raw = "\n".join(l["text"] for u in extracted["units"] for l in u["lines"])  # before header removal
    first = "\n".join(l["text"] for l in extracted["units"][0]["lines"]) if extracted["units"] else ""
    masters = "\n".join(extracted.get("master_text", []))
    stem = record["filename"].rsplit(".", 1)[0]
    ev = {}
    meta = {"source": "unknown", "professor": None, "author": None, "semester": None, "module": None,
            "course_code": None, "lecture_date": None, "derived_from": None}

    vit = VIT_NAME.match(stem)
    # OSTEP page furniture (running footer), not mere citations like "Image credit: OSTEP"
    if re.search(r"THREE\s+EASY\s+PIECES|ARPACI-DUSSEAU|WWW\.OSTEP\.ORG", raw):
        meta["source"] = "OSTEP (Operating Systems: Three Easy Pieces)"
        ev["source"] = "page footers contain THREE EASY PIECES / ARPACI-DUSSEAU / WWW.OSTEP.ORG"
        if re.search(r"ARPACI-DUSSEAU", raw):
            meta["author"] = "Arpaci-Dusseau"
            ev["author"] = "copyright footer '(c) 2008-19, ARPACI-DUSSEAU'"
    for name, rx in INSTITUTIONS.items():
        if meta["source"] == "unknown" and re.search(rx, first + "\n" + raw[:3000]):
            meta["source"] = name
            ev["source"] = f"document text names '{name}'"
            m = re.search(PERSON_AT % rx, first + "\n" + raw[:3000])
            if m:
                meta["professor"] = m.group(1)
                ev["professor"] = f"name printed next to the institution: '{m.group(0).strip()}'"
    if vit:
        if meta["source"] == "unknown":
            meta["source"] = "VIT"
            ev["source"] = f"filename follows the VIT VTOP course-material pattern (semester_slot_{vit['code']}_..._date)"
        meta["semester"], meta["course_code"], meta["lecture_date"] = vit["sem"], vit["code"], vit["date"]
        ev["semester"] = ev["course_code"] = ev["lecture_date"] = "VTOP filename fields"
    mod = re.search(r"\bModule[-_ ]+(\d+)\b", stem, re.I) or re.search(r"\bModule\s*[-:]?\s*(\d+)\s*:", first)
    if mod:
        meta["module"] = f"Module {mod.group(1)}"
        ev["module"] = "filename" if re.search(r"Module[-_ ]+\d", stem, re.I) else "first slide/page text"
    books = [t for t in masters.split("\n") if re.search(r"Silberschatz|Operating System Concepts|Galvin", t)]
    if books:
        meta["derived_from"] = "; ".join(books)
        ev["derived_from"] = "slide master text"

    dtype, why = _doc_type(record, extracted, first, stem, meta, vit, code_chars, len(cleaned_text))
    meta["document_type"] = dtype
    ev["document_type"] = why
    counts = subtopic_counts(cleaned_text)
    meta["subtopic"] = doc_subtopics(counts, tokens)
    meta["subtopic_scores"] = counts
    meta["problem_types"] = problem_types(cleaned_text) if dtype in QA_TYPES else []
    meta["metadata_evidence"] = ev
    return meta


QA_TYPES = {"practice_problems", "question_paper", "assignment", "lab", "tutorial"}


def _doc_type(record, extracted, first, stem, meta, vit, code_chars, total_chars):
    head = first[:600]
    for rx, t in [(r"\bpractice problems\b", "practice_problems"), (r"(^|\n)\s*lab\s*:", "lab"),
                  (r"\bassignment\b", "assignment"), (r"\btutorial\b", "tutorial"),
                  (r"\b(question paper|mid[- ]?term|end[- ]?sem(ester)? exam|final exam)\b", "question_paper"),
                  (r"(^|\n)\s*lecture\s*\d+", "lecture")]:
        if re.search(rx, head, re.I):
            return t, f"first page/slide text matches '{rx}'"
    for rx, t in [(r"(^|[^a-z])lab([^a-z]|$)", "lab"), (r"lecture[-_ ]?\d+", "lecture"), (r"assignment", "assignment"),
                  (r"tutorial", "tutorial"), (r"question[-_ ]?paper|exam|quiz", "question_paper"), (r"practice", "practice_problems")]:
        if re.search(rx, stem, re.I):
            return t, f"filename matches '{rx}'"
    if meta["source"].startswith("OSTEP"):
        return "textbook", "OSTEP textbook chapter"
    if extracted["layout"] == "slides":
        return "lecture", "slide deck"
    if total_chars and code_chars / total_chars >= 0.5:
        return "programming_examples", f"{code_chars / total_chars:.0%} of text is code"
    if vit and vit["kind"] == "TH":
        return "notes", "VIT theory-course (TH) handout in document form"
    return "unknown", "no evidence"
