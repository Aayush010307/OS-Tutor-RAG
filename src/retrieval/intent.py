"""Query intent and content-type preference, from the metadata the chunks already carry.

Different questions want different material. "What is a semaphore?" is best answered by lecture or textbook
explanation; "How does pthread_mutex_lock work?" by code and API material; "Give me a problem on race conditions" by
exercises. No chunk is ever dropped: a chunk of the preferred kind simply moves up the candidate list by a few places
(`SHIFT`), and a chunk that contains an identifier the student typed (`pthread_join`, `sem_wait`) moves up further.
Working in rank space keeps this independent of any score scale (RRF values, cross-encoder logits) and easy to reason
about: a preferred chunk can overtake at most `SHIFT` chunks ahead of it, never leap to the top on its own.

Metadata used (all from chunks.jsonl, unchanged): document_type, chunk_type, content_type.
"""
import re

CONCEPTUAL, CODE, PRACTICE = "conceptual", "code", "practice"
SHIFT = {"type": 3, "identifier": 3}  # places a preferred chunk / an exact identifier match moves up
MAX_SHIFT = 6

IDENTIFIER = re.compile(r"\b(?:pthread_\w+|sem_\w+|mutex_\w+|cond_\w+|[a-z_]\w*\(\))", re.I)
CODE_WORDS = re.compile(r"\b(?:code|program|snippet|syntax|segfault|compile[sd]?|implement(?:ation|ed)?|"
                        r"function call|api|(?:what'?s|what is) wrong with (?:this|my)|bug in)\b|```", re.I)
PRACTICE_REQUEST = re.compile(r"\b(?:(?:give|show|need|want|any|some|more)\b.*\b(?:problems?|exercises?|questions?|practice)|"
                              r"practice|quiz|exercises?|mcq|test me|true or false)\b", re.I)

PREFERRED = {
    CONCEPTUAL: lambda m: m.get("document_type") in ("lecture", "textbook", "notes") and m.get("chunk_type") in ("section", "slide"),
    CODE: lambda m: m.get("content_type") in ("code", "mixed") or m.get("document_type") in ("lab", "programming_examples"),
    PRACTICE: lambda m: m.get("chunk_type") in ("qa_pair", "problem") or m.get("document_type") in ("practice_problems", "lab"),
}


def classify(query):
    """'practice' when the student asks for problems or a quiz, 'code' when they name an API identifier or talk about
    code, otherwise 'conceptual'."""
    query = query or ""
    if PRACTICE_REQUEST.search(query):
        return PRACTICE
    if IDENTIFIER.search(query) or CODE_WORDS.search(query):
        return CODE
    return CONCEPTUAL


def identifiers(query):
    """API identifiers named in the query, lower-cased, without the trailing '()'."""
    return sorted({m.group(0).lower().removesuffix("()") for m in IDENTIFIER.finditer(query or "")})


ALL_TYPES = frozenset(PREFERRED)
# Which intents may prefer a content type. 'conceptual' is off by default: measured on benchmark v1.1 (E3), preferring
# lecture/textbook chunks for conceptual queries lowered nDCG@10 by 0.028 on those 80 queries, because many of them are
# answered best by exercises and lab problems. A student who asks for code or for problems has said what they want, so
# those two stay on; an exact API identifier match always counts.
DEFAULT_PREFER = frozenset({CODE, PRACTICE})


def shift_for(intent, result, names, prefer=DEFAULT_PREFER):
    """How many places this candidate moves up: a preferred content type and/or an exact identifier match."""
    meta = result.get("metadata") or {}
    shift = SHIFT["type"] if intent in prefer and PREFERRED[intent](meta) else 0
    text = (result.get("text") or "").lower()
    if names and any(n in text for n in names):
        shift += SHIFT["identifier"]
    return min(shift, MAX_SHIFT)


def reorder(candidates, intent, names=(), prefer=DEFAULT_PREFER):
    """Stable reorder of an already ranked list: position minus shift, ties keep the original order."""
    keyed = [(pos - shift_for(intent, r, names, prefer), pos, r) for pos, r in enumerate(candidates, 1)]
    return [r for _, _, r in sorted(keyed, key=lambda k: (k[0], k[1]))]
