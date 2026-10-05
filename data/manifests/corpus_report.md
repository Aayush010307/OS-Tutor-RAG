# Corpus Ingestion Report

Generated 2026-09-21T12:40:10+00:00 by pipeline v1.0.0 from `Docs/`.

## Summary

| Metric | Value |
| --- | --- |
| Documents discovered | 22 |
| Successfully extracted | 22 |
| Extraction failures | 0 |
| Exact duplicate documents | 0 |
| Near-duplicate / overlapping pairs | 1 |
| PDF pages | 234 |
| Slides | 247 |
| Chunks | 463 |
| Chunks with an exact duplicate elsewhere | 4 |
| Chunk tokens | 99322 (tiktoken cl100k_base) |
| Validation | 0 errors, 7 warnings, 1 info |

### Documents by topic

- Synchronisation: 17
- Threads: 5

### Documents by source

- IIT Bombay: 7
- OSTEP (Operating Systems: Three Easy Pieces): 6
- VIT: 5
- unknown: 4

### Documents by type

- lab: 2
- lecture: 11
- notes: 1
- practice_problems: 1
- programming_examples: 1
- textbook: 6

### Documents by file format

- pdf: 16
- ppt: 1
- pptx: 5

### Chunks by type

- problem: 13
- qa_pair: 60
- section: 204
- slide: 186

### Chunks by content

- code: 39
- mixed: 147
- text: 277

Chunk tokens: min 21, median 186, mean 214.5, max 913. Limits: target 350, max 600, Q&A max 1000, merge below 40.

## Documents

| Document ID | File | Topic | Source | Type | Pages/Slides | Chunks | Tokens | Professor | Duplicate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| concurrency-bugs-e8a8fced | Docs/Synchronisation/Concurrency bugs.pptx | Synchronisation | unknown | lecture | 13 s | 8 | 599 | - | - |
| fallsem2025-26-vl-bcse303l-00100-th-2025-3f6ce962 | Docs/Synchronisation/FALLSEM2025-26_VL_BCSE303L_00100_TH_2025-09-11_process-Synchronization_locks_semaphores_monitors.ppt | Synchronisation | VIT | lecture | 59 s | 36 | 3754 | - | - |
| fallsem2025-26-vl-bcse303l-00100-th-2025-975bc607 | Docs/Synchronisation/FALLSEM2025-26_VL_BCSE303L_00100_TH_2025-09-16_Process-synchronization.pptx | Synchronisation | VIT | lecture | 50 s | 37 | 3780 | - | - |
| fallsem2025-26-vl-bcse303l-00100-th-2025-fd173a9e | Docs/Synchronisation/FALLSEM2025-26_VL_BCSE303L_00100_TH_2025-09-23_Classical-problem-of-synchronization.pdf | Synchronisation | VIT | notes | 9 p | 12 | 2945 | - | - |
| sumsem2025-26-vl-bcse303l-00100-th-2026-02c11114 | Docs/Synchronisation/SUMSEM2025-26_VL_BCSE303L_00100_TH_2026-06-15_Module-4---Process-Synchronization.pptx | Synchronisation | VIT | lecture | 83 s | 54 | 6491 | - | - |
| semaphore-ppt-copy-0dcb4a42 | Docs/Synchronisation/Semaphore.ppt - Copy.pptx | Synchronisation | unknown | lecture | 6 s | 2 | 224 | - | - |
| thread-synchronization-lab-problems-e871e8ad | Docs/Synchronisation/Thread_Synchronization_Lab_Problems.pdf | Synchronisation | unknown | lab | 11 p | 10 | 2429 | - | - |
| dining-philospher-d60a5fa0 | Docs/Synchronisation/dining philospher.pdf | Synchronisation | unknown | programming_examples | 3 p | 1 | 425 | - | - |
| lecture13-0af66874 | Docs/Synchronisation/lecture13.pdf | Synchronisation | IIT Bombay | lecture | 12 p | 9 | 801 | Mythili Vutukuru | - |
| lecture14-a8135675 | Docs/Synchronisation/lecture14.pdf | Synchronisation | IIT Bombay | lecture | 8 p | 5 | 471 | Mythili Vutukuru | - |
| lecture15-918b182c | Docs/Synchronisation/lecture15.pdf | Synchronisation | IIT Bombay | lecture | 6 p | 2 | 236 | Mythili Vutukuru | - |
| ps-concurrency-381f1b77 | Docs/Synchronisation/ps-concurrency.pdf | Synchronisation | IIT Bombay | practice_problems | 50 p | 60 | 16374 | Mythili Vutukuru | - |
| pthreads-sync-9017cfef | Docs/Synchronisation/pthreads-sync.pdf | Synchronisation | IIT Bombay | lab | 6 p | 15 | 3927 | Mythili Vutukuru | - |
| threads-bugs-e5dff53b | Docs/Synchronisation/threads-bugs.pdf | Synchronisation | OSTEP (Operating Systems: Three Easy Pieces) | textbook | 16 p | 27 | 8098 | - | - |
| threads-cv-3156a56b | Docs/Synchronisation/threads-cv.pdf | Synchronisation | OSTEP (Operating Systems: Three Easy Pieces) | textbook | 19 p | 28 | 8845 | - | - |
| threads-locks-cb67d3bd | Docs/Synchronisation/threads-locks.pdf | Synchronisation | OSTEP (Operating Systems: Three Easy Pieces) | textbook | 22 p | 40 | 12295 | - | - |
| threads-sema-d8fb1c00 | Docs/Synchronisation/threads-sema.pdf | Synchronisation | OSTEP (Operating Systems: Three Easy Pieces) | textbook | 20 p | 33 | 10414 | - | - |
| fallsem2025-26-vl-bcse303l-00100-th-2025-170d2f74 | Docs/Threads/FALLSEM2025-26_VL_BCSE303L_00100_TH_2025-08-03_Threads.pptx | Threads | VIT | lecture | 36 s | 17 | 1978 | - | - |
| lecture12-4288650c | Docs/Threads/lecture12.pdf | Threads | IIT Bombay | lecture | 11 p | 7 | 697 | Mythili Vutukuru | - |
| threads-api-8ce54688 | Docs/Threads/threads-api.pdf | Threads | OSTEP (Operating Systems: Three Easy Pieces) | textbook | 12 p | 22 | 5610 | - | - |
| threads-intro-c1df7202 | Docs/Threads/threads-intro.pdf | Threads | OSTEP (Operating Systems: Three Easy Pieces) | textbook | 16 p | 29 | 7867 | - | - |
| threads-4d568260 | Docs/Threads/threads.pdf | Threads | IIT Bombay | lecture | 13 p | 9 | 1275 | Mythili Vutukuru | - |

## Metadata evidence

Fields are filled only with evidence from the file; everything else is null/unknown.

- `concurrency-bugs-e8a8fced` - document_type: slide deck
  - embedded file author (unverified, not used as professor): lingam
- `fallsem2025-26-vl-bcse303l-00100-th-2025-3f6ce962` - source: filename follows the VIT VTOP course-material pattern (semester_slot_BCSE303L_..._date); semester: VTOP filename fields; course_code: VTOP filename fields; lecture_date: VTOP filename fields; document_type: slide deck
  - embedded file author (unverified, not used as professor): Marilyn Turnamian
- `fallsem2025-26-vl-bcse303l-00100-th-2025-975bc607` - source: filename follows the VIT VTOP course-material pattern (semester_slot_BCSE303L_..._date); semester: VTOP filename fields; course_code: VTOP filename fields; lecture_date: VTOP filename fields; derived_from: slide master text; document_type: slide deck
  - derived_from: Silberschatz, Galvin and Gagne ©2018; Operating System Concepts – 10th Edition
  - embedded file author (unverified, not used as professor): Lucent End User
- `fallsem2025-26-vl-bcse303l-00100-th-2025-fd173a9e` - source: filename follows the VIT VTOP course-material pattern (semester_slot_BCSE303L_..._date); semester: VTOP filename fields; course_code: VTOP filename fields; lecture_date: VTOP filename fields; document_type: VIT theory-course (TH) handout in document form
  - embedded file author (unverified, not used as professor): DEEPA SARAVANAKUMAR
- `sumsem2025-26-vl-bcse303l-00100-th-2026-02c11114` - source: filename follows the VIT VTOP course-material pattern (semester_slot_BCSE303L_..._date); semester: VTOP filename fields; course_code: VTOP filename fields; lecture_date: VTOP filename fields; module: filename; document_type: slide deck
  - embedded file author (unverified, not used as professor): amuth
- `semaphore-ppt-copy-0dcb4a42` - document_type: slide deck
  - embedded file author (unverified, not used as professor): Admin
- `thread-synchronization-lab-problems-e871e8ad` - document_type: filename matches '(^|[^a-z])lab([^a-z]|$)'
  - embedded file author (unverified, not used as professor): Microsoft account
- `dining-philospher-d60a5fa0` - document_type: 78% of text is code
  - embedded file author (unverified, not used as professor): Admin
- `lecture13-0af66874` - source: document text names 'IIT Bombay'; professor: name printed next to the institution: 'Mythili Vutukuru
IIT Bombay'; document_type: first page/slide text matches '(^|\n)\s*lecture\s*\d+'
- `lecture14-a8135675` - source: document text names 'IIT Bombay'; professor: name printed next to the institution: 'Mythili Vutukuru
IIT Bombay'; document_type: first page/slide text matches '(^|\n)\s*lecture\s*\d+'
- `lecture15-918b182c` - source: document text names 'IIT Bombay'; professor: name printed next to the institution: 'Mythili Vutukuru
IIT Bombay'; document_type: first page/slide text matches '(^|\n)\s*lecture\s*\d+'
- `ps-concurrency-381f1b77` - source: document text names 'IIT Bombay'; professor: name printed next to the institution: 'Mythili Vutukuru, IIT Bombay'; document_type: first page/slide text matches '\bpractice problems\b'
- `pthreads-sync-9017cfef` - source: document text names 'IIT Bombay'; professor: name printed next to the institution: 'Mythili Vutukuru, IIT Bombay'; document_type: first page/slide text matches '(^|\n)\s*lab\s*:'
- `threads-bugs-e5dff53b` - source: page footers contain THREE EASY PIECES / ARPACI-DUSSEAU / WWW.OSTEP.ORG; author: copyright footer '(c) 2008-19, ARPACI-DUSSEAU'; document_type: OSTEP textbook chapter
- `threads-cv-3156a56b` - source: page footers contain THREE EASY PIECES / ARPACI-DUSSEAU / WWW.OSTEP.ORG; author: copyright footer '(c) 2008-19, ARPACI-DUSSEAU'; document_type: OSTEP textbook chapter
- `threads-locks-cb67d3bd` - source: page footers contain THREE EASY PIECES / ARPACI-DUSSEAU / WWW.OSTEP.ORG; author: copyright footer '(c) 2008-19, ARPACI-DUSSEAU'; document_type: OSTEP textbook chapter
- `threads-sema-d8fb1c00` - source: page footers contain THREE EASY PIECES / ARPACI-DUSSEAU / WWW.OSTEP.ORG; author: copyright footer '(c) 2008-19, ARPACI-DUSSEAU'; document_type: OSTEP textbook chapter
- `fallsem2025-26-vl-bcse303l-00100-th-2025-170d2f74` - source: filename follows the VIT VTOP course-material pattern (semester_slot_BCSE303L_..._date); semester: VTOP filename fields; course_code: VTOP filename fields; lecture_date: VTOP filename fields; derived_from: slide master text; document_type: slide deck
  - derived_from: Silberschatz, Galvin and Gagne ©2009; Operating System Concepts – 8th Edition
  - embedded file author (unverified, not used as professor): Marilyn Turnamian
- `lecture12-4288650c` - source: document text names 'IIT Bombay'; professor: name printed next to the institution: 'Mythili Vutukuru
IIT Bombay'; document_type: first page/slide text matches '(^|\n)\s*lecture\s*\d+'
- `threads-api-8ce54688` - source: page footers contain THREE EASY PIECES / ARPACI-DUSSEAU / WWW.OSTEP.ORG; author: copyright footer '(c) 2008-19, ARPACI-DUSSEAU'; document_type: OSTEP textbook chapter
- `threads-intro-c1df7202` - source: page footers contain THREE EASY PIECES / ARPACI-DUSSEAU / WWW.OSTEP.ORG; author: copyright footer '(c) 2008-19, ARPACI-DUSSEAU'; document_type: OSTEP textbook chapter
- `threads-4d568260` - source: document text names 'IIT Bombay'; professor: name printed next to the institution: 'Mythili Vutukuru
CSE, IIT Bombay'; document_type: slide deck
  - embedded file author (unverified, not used as professor): Mythili Vutukuru

## Subtopics

- `concurrency-bugs-e8a8fced`: Concurrency, Locks, Deadlock, Concurrency Bugs
- `fallsem2025-26-vl-bcse303l-00100-th-2025-3f6ce962`: Critical Sections, Locks, Mutex, Spinlocks, Test-and-Set, Semaphores, Monitors, Producer-Consumer, Readers-Writers, Dining Philosophers
- `fallsem2025-26-vl-bcse303l-00100-th-2025-975bc607`: Critical Sections, Mutual Exclusion, Locks, Mutex, Spinlocks, Condition Variables, Semaphores, Monitors
- `fallsem2025-26-vl-bcse303l-00100-th-2025-fd173a9e`: Pthreads, Critical Sections, Mutex, Semaphores, Producer-Consumer, Readers-Writers, Dining Philosophers
- `sumsem2025-26-vl-bcse303l-00100-th-2026-02c11114`: Race Conditions, Critical Sections, Mutual Exclusion, Locks, Mutex, Spinlocks, Test-and-Set, Compare-and-Swap, Condition Variables, Semaphores, Monitors, Peterson's Solution, Producer-Consumer, Readers-Writers, Dining Philosophers, Deadlock
- `semaphore-ppt-copy-0dcb4a42`: Mutex, Semaphores, Producer-Consumer
- `thread-synchronization-lab-problems-e871e8ad`: Pthreads, Thread Creation, Thread Join, Mutex, Condition Variables | problem types: Programming Problems
- `dining-philospher-d60a5fa0`: Locks, Mutex, Dining Philosophers
- `lecture13-0af66874`: Locks, Mutex, Spinlocks, Test-and-Set, Compare-and-Swap
- `lecture14-a8135675`: Multithreading, Locks, Condition Variables, Producer-Consumer
- `lecture15-918b182c`: Mutex, Semaphores, Producer-Consumer
- `ps-concurrency-381f1b77`: Locks, Mutex, Spinlocks, Condition Variables, Semaphores, Barriers, Deadlock | problem types: True/False, MCQs, Conceptual Questions, Programming Problems, Synchronization Problems, Debugging Problems
- `pthreads-sync-9017cfef`: Thread Fundamentals, Multithreading, Parallelism, Pthreads, Critical Sections, Locks, Condition Variables, Semaphores, Producer-Consumer, Readers-Writers | problem types: Programming Problems, Synchronization Problems, Debugging Problems
- `threads-bugs-e5dff53b`: Concurrency, Pthreads, Locks, Mutex, Deadlock, Concurrency Bugs
- `threads-cv-3156a56b`: Pthreads, Locks, Mutex, Condition Variables, Producer-Consumer
- `threads-locks-cb67d3bd`: Thread Scheduling, Critical Sections, Locks, Mutex, Spinlocks, Test-and-Set
- `threads-sema-d8fb1c00`: Concurrency, Critical Sections, Locks, Mutex, Condition Variables, Semaphores, Producer-Consumer, Readers-Writers, Dining Philosophers
- `fallsem2025-26-vl-bcse303l-00100-th-2025-170d2f74`: Thread Fundamentals, Multithreading, Parallelism, Pthreads, Thread Models, User-Level Threads, Kernel Threads, Thread Scheduling
- `lecture12-4288650c`: Thread Fundamentals, Concurrency, Parallelism, User-Level Threads, Kernel Threads, Race Conditions, Critical Sections
- `threads-api-8ce54688`: Multithreading, Pthreads, Thread Creation, Thread Join, Locks, Mutex, Condition Variables
- `threads-intro-c1df7202`: Multithreading, Concurrency, Pthreads, Thread Creation, Thread Scheduling, Race Conditions, Critical Sections
- `threads-4d568260`: Thread Fundamentals, Concurrency, Parallelism, Pthreads, Thread Creation, User-Level Threads, Thread Scheduling, Race Conditions, Critical Sections, Mutual Exclusion

## Duplicates

- No exact duplicate documents.
- near_duplicate: `lecture15-918b182c` ~ `semaphore-ppt-copy-0dcb4a42` (jaccard 0.949, containment 0.993)

## Files not ingested

- ignored hidden/system file: `.DS_Store`
- ignored hidden/system file: `Synchronisation/.DS_Store`

## Validation issues

- info `near_duplicate`: 1
- warning `image_only_content`: 7

### Warnings

- `image_only_content` fallsem2025-26-vl-bcse303l-00100-th-2025-975bc607: 4 page(s)/slide(s) have images but almost no text (no OCR): [5, 7, 34, 36]
- `image_only_content` sumsem2025-26-vl-bcse303l-00100-th-2026-02c11114: 8 page(s)/slide(s) have images but almost no text (no OCR): [12, 22, 23, 28, 33, 40, 42, 70]
- `image_only_content` lecture14-a8135675: 2 page(s)/slide(s) have images but almost no text (no OCR): [4, 8]
- `image_only_content` lecture15-918b182c: 1 page(s)/slide(s) have images but almost no text (no OCR): [5]
- `image_only_content` fallsem2025-26-vl-bcse303l-00100-th-2025-170d2f74: 9 page(s)/slide(s) have images but almost no text (no OCR): [4, 7, 8, 9, 14, 16, 18, 20, 33]
- `image_only_content` lecture12-4288650c: 3 page(s)/slide(s) have images but almost no text (no OCR): [7, 8, 10]
- `image_only_content` threads-4d568260: 1 page(s)/slide(s) have images but almost no text (no OCR): [7]
