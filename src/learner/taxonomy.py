"""Controlled concept taxonomy for the course scope (Threads and Synchronization) and the relations between concepts.

Course knowledge, chat history and the learner model are three different things; this module is the vocabulary that
lets the last one speak about the first. A concept is something a student can understand, misunderstand or need to
revise. Every concept here is covered by the indexed material (checked against chunks.jsonl when the taxonomy was
written); `pthread_exit` and thread termination are deliberately absent because no chunk mentions them, and nothing
outside the corpus is invented.

    detect_concepts("Why does counter++ cause a race condition?")  -> ["race_condition"]
    concepts_from_results(results)                                -> concepts of the retrieved chunks (chunk subtopics)
    prerequisite_chain("condition_variable")                      -> ["mutex", "critical_section", ...]

Detection is deterministic (regular expressions over the student's words, and the corpus's own `subtopics` labels for
retrieved chunks): no model call, so it is cheap, testable and the same on every machine.
"""
import re
from dataclasses import dataclass, field

THREADS, SYNC = "threads", "synchronization"


@dataclass(frozen=True)
class Concept:
    id: str
    label: str
    topic: str
    pattern: str  # regular expression over lower-cased student text
    subtopics: tuple = ()  # the corpus's own chunk subtopic labels that mean this concept
    prerequisites: tuple = ()
    query: str = ""  # what to ask the retriever when revising this concept
    generic: bool = False  # too broad to count when a more specific concept matched
    regex: re.Pattern = field(init=False, repr=False, compare=False, default=None)

    def __post_init__(self):
        object.__setattr__(self, "regex", re.compile(self.pattern, re.I))


def _c(id, label, topic, pattern, subtopics=(), prerequisites=(), query="", generic=False):
    return Concept(id, label, topic, pattern, tuple(subtopics), tuple(prerequisites), query or label, generic)


CONCEPTS = {c.id: c for c in (
    # ---- threads
    _c("thread_basics", "Thread basics", THREADS, r"\bthreads?\b", ["Thread Fundamentals"], [],
       "what is a thread and how does it differ from a process", generic=True),
    _c("process_vs_thread", "Process vs thread", THREADS,
       r"process(?:es)?\s*(?:vs\.?|versus|and|or)\s*threads?|threads?\s*(?:vs\.?|versus|and|or)\s*process|"
       r"difference between (?:a )?(?:process|thread)", [], ["thread_basics"], "difference between a process and a thread"),
    _c("user_level_threads", "User-level threads", THREADS, r"user[- ]?(?:level|space) threads?|\bults?\b",
       ["User-Level Threads"], ["thread_basics"], "user-level threads"),
    _c("kernel_level_threads", "Kernel-level threads", THREADS, r"kernel[- ]?(?:level|supported)? ?threads?|\bklts?\b",
       ["Kernel Threads"], ["thread_basics"], "kernel-level threads"),
    _c("multithreading", "Multithreading and thread models", THREADS,
       r"multi-?thread\w*|many[- ]to[- ](?:one|many)|one[- ]to[- ]one|thread models?|parallelism",
       ["Multithreading", "Thread Models", "Parallelism"], ["thread_basics"], "multithreading models"),
    _c("thread_lifecycle", "Thread lifecycle", THREADS,
       r"thread (?:life ?cycle|states?)|(?:new|ready|runnable|running|blocked|terminated) state",
       [], ["thread_basics"], "thread states and lifecycle"),
    _c("thread_creation", "Thread creation (pthread_create)", THREADS,
       r"pthread_create|creat(?:e|es|ing) (?:a )?threads?|thread creation", ["Thread Creation"], ["thread_basics"],
       "pthread_create creating a thread"),
    _c("thread_join", "Waiting for threads (pthread_join)", THREADS, r"pthread_join|\bjoin(?:s|ing)?\b",
       ["Thread Join"], ["thread_creation"], "pthread_join waiting for a thread to finish"),
    # ---- synchronization
    _c("concurrency", "Concurrency", SYNC, r"concurren(?:t|cy)", ["Concurrency"], ["thread_basics"],
       "concurrency and concurrent execution", generic=True),
    _c("shared_data", "Shared data", SYNC, r"shared (?:data|variables?|memory|resources?|counter|state)|global variables?",
       [], ["thread_basics"], "threads sharing data and global variables", generic=True),
    _c("race_condition", "Race condition", SYNC,
       r"race conditions?|data races?|\brace\b|counter\s*(?:\+\+|\+=)|lost updates?|non-?determinis\w+",
       ["Race Conditions"], ["shared_data"], "race condition: counter++ with two threads gives the wrong result"),
    _c("atomicity", "Atomic operations", SYNC,
       r"atomic(?:ity|ally)?|test[- ]and[- ]set|compare[- ]and[- ]swap|\btas\b|\bcas\b|read-modify-write",
       ["Test-and-Set", "Compare-and-Swap"], ["race_condition"], "atomic operations test-and-set compare-and-swap"),
    _c("concurrency_bugs", "Concurrency bugs", SYNC, r"concurrency bugs?|atomicity violation|order violation",
       ["Concurrency Bugs"], ["race_condition"], "common concurrency bugs atomicity violation order violation"),
    _c("critical_section", "Critical section", SYNC, r"critical (?:sections?|regions?)", ["Critical Sections"],
       ["race_condition"], "critical section"),
    _c("mutual_exclusion", "Mutual exclusion", SYNC, r"mutual exclusion|peterson", ["Mutual Exclusion", "Peterson's Solution"],
       ["critical_section"], "mutual exclusion requirement for critical sections"),
    _c("locks_spinlocks", "Locks and spinlocks", SYNC, r"\block(?:s|ing|ed)?\b|spin ?locks?", ["Locks", "Spinlocks"],
       ["mutual_exclusion", "atomicity"], "locks and spinlocks"),
    _c("mutex", "Mutex", SYNC, r"mutex(?:es)?|pthread_mutex_\w+", ["Mutex"], ["critical_section", "mutual_exclusion"],
       "mutex pthread_mutex_lock pthread_mutex_unlock"),
    _c("semaphore", "Semaphore", SYNC, r"semaphores?|sem_(?:wait|post|init)", ["Semaphores"],
       ["critical_section", "mutual_exclusion"], "semaphore wait and post operations"),
    _c("binary_semaphore", "Binary semaphore", SYNC, r"binary semaphores?", [], ["semaphore"], "binary semaphore"),
    _c("counting_semaphore", "Counting semaphore", SYNC, r"counting semaphores?", [], ["semaphore"], "counting semaphore"),
    _c("condition_variable", "Condition variable", SYNC, r"condition variables?|pthread_cond_\w+|\bcvs?\b",
       ["Condition Variables"], ["mutex"], "condition variable pthread_cond_wait pthread_cond_signal"),
    _c("monitor", "Monitor", SYNC, r"monitors?", ["Monitors"], ["mutex", "condition_variable"], "monitor"),
    _c("producer_consumer", "Producer-consumer", SYNC, r"producer[- /]*consumer|bounded[- ]buffer", ["Producer-Consumer"],
       ["semaphore", "condition_variable"], "producer-consumer bounded buffer"),
    _c("readers_writers", "Readers-writers", SYNC, r"readers?[- ]?(?:and|/|-)?[- ]?writers?", ["Readers-Writers"],
       ["semaphore", "mutex"], "readers-writers problem"),
    _c("deadlock", "Deadlock", SYNC, r"deadlocks?", ["Deadlock"], ["mutex"], "deadlock"),
    _c("dining_philosophers", "Dining philosophers", SYNC, r"dining philosophers?", ["Dining Philosophers"],
       ["deadlock", "semaphore"], "dining philosophers problem"),
    _c("starvation", "Starvation", SYNC, r"starvation|starve[sd]?", ["Starvation"], ["deadlock"], "starvation"),
    _c("synchronization_primitives", "Synchronization primitives", SYNC,
       r"synchroni[sz]ation (?:primitives|tools|mechanisms|constructs)", [], ["critical_section"],
       "synchronization primitives locks semaphores monitors", generic=True),
)}

SUBTOPIC_TO_CONCEPT = {}
for _concept in CONCEPTS.values():
    for _sub in _concept.subtopics:
        SUBTOPIC_TO_CONCEPT[_sub.lower()] = _concept.id
# corpus subtopics that point at the nearest concept without being one themselves
SUBTOPIC_TO_CONCEPT.update({"pthreads": "thread_creation"})


def get(concept_id):
    return CONCEPTS[concept_id]


def label(concept_id):
    return CONCEPTS[concept_id].label if concept_id in CONCEPTS else concept_id


def detect_concepts(text, limit=3):
    """Concepts the student's own words name, most specific first. Generic concepts ("thread", "concurrent",
    "shared data") are returned only when nothing more specific matched."""
    text = text or ""
    hits = []
    for c in CONCEPTS.values():
        found = c.regex.findall(text)
        if found:
            hits.append((c, len(found)))
    specific = [(c, n) for c, n in hits if not c.generic]
    chosen = specific or hits
    chosen.sort(key=lambda cn: -cn[1])  # stable: ties keep the taxonomy's order
    return [c.id for c, _ in chosen][:limit]


def concepts_from_results(results, limit=2):
    """The concepts of retrieved chunks, through the corpus's own subtopic labels, most frequent first. Used when the
    question names no concept (e.g. a follow-up like "I don't understand why that is unsafe")."""
    counts = {}
    for rank, r in enumerate(results or []):
        for sub in ((r.get("metadata") or {}).get("subtopics") or []):
            cid = SUBTOPIC_TO_CONCEPT.get(str(sub).lower())
            if cid:
                counts[cid] = counts.get(cid, 0) + 1.0 / (1 + rank)  # earlier ranks count more
    return [c for c, _ in sorted(counts.items(), key=lambda kv: -kv[1])][:limit]


def prerequisites(concept_id):
    return list(CONCEPTS[concept_id].prerequisites)


def prerequisite_chain(concept_id):
    """All transitive prerequisites, nearest first, without repeats."""
    seen, order, frontier = {concept_id}, [], list(CONCEPTS[concept_id].prerequisites)
    while frontier:
        nxt = []
        for p in frontier:
            if p not in seen:
                seen.add(p)
                order.append(p)
                nxt.extend(CONCEPTS[p].prerequisites)
        frontier = nxt
    return order


def dependents(concept_id):
    """Concepts that list this one as a direct prerequisite (where understanding it leads next)."""
    return [c.id for c in CONCEPTS.values() if concept_id in c.prerequisites]


def related(concept_id):
    """Direct prerequisites and direct dependents: the neighbourhood used for cross-questions."""
    return prerequisites(concept_id) + dependents(concept_id)
