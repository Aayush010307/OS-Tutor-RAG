# OS-Tutor-RAG Project Log

This is the persistent development history of the project. It is a required project artifact.

**Rules for maintaining this log (all sessions, human or Claude Code):**

- Read this file before making architectural changes.
- Append new entries; do not rewrite or delete historical entries to make the file tidier. If an earlier
  statement turns out to be wrong, add a dated correction that points at it.
- Record, as they happen: decisions and their rationale, files created/modified, dependencies, commands,
  tests and validation results, failures and fixes, final results, and the current phase/status.
- Dates are absolute (YYYY-MM-DD). Statistics must come from the generated artifacts, not from memory.

---

## Project Overview

OS-Tutor-RAG (repository folder `OS-RAG/`) is an educational retrieval-augmented generation system for an
undergraduate Operating Systems course. The initial scope is two topic areas: **Threads** and
**Synchronisation**. The system is built in explicit phases; each phase must be completed, verified and
frozen before the next one starts.

The raw study corpus lives in `Docs/`, filed by topic folder (`Docs/Threads/`, `Docs/Synchronisation/`).
It mixes material from several sources: VIT course slides and handouts, IIT Bombay lectures, labs and
practice problems (Mythili Vutukuru), OSTEP (Operating Systems: Three Easy Pieces) textbook chapters,
and synchronization programming problems.

| Phase | Scope | Status |
| --- | --- | --- |
| 1 | Corpus ingestion and preprocessing (extraction, cleaning, metadata, chunking, dedup, validation) | COMPLETE / FROZEN (2026-09-21) |
| 2 | Embedding, Qdrant vector index, baseline dense retrieval, metadata filters | COMPLETE (2026-09-21) |
| 3A | Gold retrieval benchmark + baseline evaluation | COMPLETE (2026-09-21) |
| 3B-0 | Judgment expansion: benchmark v1.1 (pooled, manually judged) | COMPLETE / v1.1 FROZEN (2026-09-21) |
| 3B | Controlled retrieval experiments (advanced retrieval / reranking) | E1 (BM25 baseline) COMPLETE (2026-09-21); E2 (dense + BM25 RRF hybrid) COMPLETE (2026-10-04) |
| R2 | Review 2 preparation: tutor controller prototype, pre/post assessment framework, Review 2 report | COMPLETE (2026-10-04); tutor PARTIAL (no LLM connected) |
| 4 | RAG generation | NOT STARTED |
| 5 | Evaluation / research experiments | NOT STARTED |

---

## Reproducibility Baseline

Environment used to build and verify the Phase 1 baseline (2026-09-21):

| Item | Value |
| --- | --- |
| OS | macOS 27.0 (arm64) |
| Python | 3.13.7, `/usr/local/bin/python3` |
| PyMuPDF (`fitz`) | 1.25.1 (pre-installed) |
| python-pptx | 1.0.2 (pre-installed) |
| tiktoken | 0.14.0 (pre-installed); encoding `cl100k_base` cached under `$TMPDIR/data-gym-cache` |
| pytest | 8.3.4 (pre-installed) |
| olefile | 0.47 (installed during Phase 1: `python3 -m pip install olefile`) |
| Version control | none: the project is not a git repository |

`requirements.txt` lists minimum versions (`pymupdf>=1.24`, `python-pptx>=1.0`, `olefile>=0.46`,
`tiktoken>=0.7`, `pytest>=8`), not pinned versions. The exact versions above are the ones that produced
the baseline artifacts.

Commands:

```bash
# full rebuild of data/ from Docs/ (about 4 s on the baseline machine)
python3 -m src.ingestion.pipeline --source Docs --output data

# test suite (fixtures are generated at runtime; one test also reads the real .ppt if present)
python3 -m pytest tests -q
```

Baseline reference digests (2026-09-21):

- `data/chunks/chunks.jsonl` SHA-256: `90d1e88ef552dfb32b5a8c2d4845cd20399eca82f6669bd184d08eaad8fcbe16`
- Corpus digest = SHA-256 over sorted lines `"<relative path>\t<file sha256>\n"` for the 22 ingested
  documents (`.DS_Store` excluded): `1df92ddcda63baa62c107b10840f704ba610aedd2b6a0a8ef045e241530520f9`
- Per-file SHA-256 hashes: the `file_hash` field of each record in `data/manifests/documents.json`.

---

## Phase 1 — Corpus Ingestion and Preprocessing

**Status: COMPLETE / FROZEN** (implemented and verified 2026-09-21)

### Scope

Only: raw documents → extraction → cleaning → metadata → semantic chunking → deduplication → validation
→ structured data. The Phase 1 instructions excluded LLM API calls, embeddings, vector databases
(Chroma/FAISS/Pinecone/Qdrant/Weaviate), BM25/hybrid retrieval, reranking, generation, chat UI, agents
and query rewriting, and none of them were implemented.

### Starting state (inspected before any code was written)

- Repository contained only `Docs/` (22 source files + 2 `.DS_Store`). No code, no dependency files,
  no configuration, no git repository, no existing ingestion pipeline.
- Formats present: 16 PDF, 5 PPTX, 1 PPT; no DOCX, TXT or MD.
- Relevant corpus characteristics found during inspection (these drove the design):
  - OSTEP chapter PDFs (TeX): running headers/footers, code listings with tiny gutter line numbers,
    code set in a monospace font (NimbusMonL), numbered section headings in larger fonts, and
    underscores in inline code drawn as vector strokes instead of text.
  - IIT Bombay `lecture12–15.pdf` and `threads.pdf`: slide decks printed to landscape PDF pages
    (44 pt titles, slide numbers in the footer); code examples in lectures 12–15 are images.
  - `ps-concurrency.pdf`: 60 sequentially numbered questions with `Ans` markers; answers often continue
    on the next page.
  - `Thread_Synchronization_Lab_Problems.pdf`: 10 numbered problems whose sub-headings ("Problem",
    "Sample Input", "Sample Output", "Students must use") are bold at body size.
  - The legacy `.ppt` stores slide text inside slide drawings; slide order must be resolved through the
    PowerPoint persist directory.
  - VIT evidence exists only in filenames (VTOP pattern `FALLSEM2025-26_VL_BCSE303L_…`); slide masters
    of two VIT decks name "Silberschatz, Galvin and Gagne" / "Operating System Concepts".
  - PPTX core-property authors are template leftovers (e.g. "Marilyn Turnamian", "Lucent End User"),
    so embedded author fields are unreliable.

### Verified corpus statistics (from `data/manifests/`, pipeline run 2026-09-21T12:40:10Z)

| Metric | Value |
| --- | --- |
| Documents discovered | 22 (16 PDF, 5 PPTX, 1 PPT) |
| Ignored files | 2 `.DS_Store` (`Docs/.DS_Store`, `Docs/Synchronisation/.DS_Store`), listed in the manifest |
| Unsupported files | 0 |
| Successfully extracted | 22 / 22 |
| Extraction failures | 0 |
| Documents by topic folder | Synchronisation 17, Threads 5 |
| Documents by source | IIT Bombay 7, OSTEP 6, VIT 5, unknown 4 |
| PDF pages | 234 |
| Slides | 247 |
| Chunks | 463 |
| Chunks by type | 60 `qa_pair`, 13 `problem`, 186 `slide`, 204 `section` |
| Chunks by content | 277 text, 147 mixed, 39 code |
| Chunk tokens (tiktoken `cl100k_base`) | 99,322 total; min 21, median 186, mean 214.5, max 913 |
| Chunks > 512 tokens | 22 (4 of them `qa_pair`) |
| Exact duplicate documents | 0 |
| Near-duplicate documents | 1 pair: `Semaphore.ppt - Copy.pptx` ~ `lecture15.pdf` (Jaccard 0.949, containment 0.993; about 95% text overlap) |
| Chunks with an exact (normalized-text) duplicate | 4 (3 between VIT decks, 1 between `lecture15.pdf` and `Semaphore.ppt - Copy.pptx`; see correction below) |
| Validation | 0 errors, 7 warnings (`image_only_content`), 1 info (`near_duplicate`) |
| Tests | 15 / 15 passing |

Per-document inventory:

| File (under `Docs/`) | Source | Type | Pages/Slides | Chunks | Tokens |
| --- | --- | --- | --- | --- | --- |
| Synchronisation/Concurrency bugs.pptx | unknown | lecture | 13 s | 8 | 599 |
| Synchronisation/FALLSEM2025-26_VL_BCSE303L_00100_TH_2025-09-11_process-Synchronization_locks_semaphores_monitors.ppt | VIT | lecture | 59 s | 36 | 3754 |
| Synchronisation/FALLSEM2025-26_VL_BCSE303L_00100_TH_2025-09-16_Process-synchronization.pptx | VIT | lecture | 50 s | 37 | 3780 |
| Synchronisation/FALLSEM2025-26_VL_BCSE303L_00100_TH_2025-09-23_Classical-problem-of-synchronization.pdf | VIT | notes | 9 p | 12 | 2945 |
| Synchronisation/SUMSEM2025-26_VL_BCSE303L_00100_TH_2026-06-15_Module-4---Process-Synchronization.pptx | VIT | lecture | 83 s | 54 | 6491 |
| Synchronisation/Semaphore.ppt - Copy.pptx | unknown | lecture | 6 s | 2 | 224 |
| Synchronisation/Thread_Synchronization_Lab_Problems.pdf | unknown | lab | 11 p | 10 | 2429 |
| Synchronisation/dining philospher.pdf | unknown | programming_examples | 3 p | 1 | 425 |
| Synchronisation/lecture13.pdf | IIT Bombay | lecture | 12 p | 9 | 801 |
| Synchronisation/lecture14.pdf | IIT Bombay | lecture | 8 p | 5 | 471 |
| Synchronisation/lecture15.pdf | IIT Bombay | lecture | 6 p | 2 | 236 |
| Synchronisation/ps-concurrency.pdf | IIT Bombay | practice_problems | 50 p | 60 | 16374 |
| Synchronisation/pthreads-sync.pdf | IIT Bombay | lab | 6 p | 15 | 3927 |
| Synchronisation/threads-bugs.pdf | OSTEP | textbook | 16 p | 27 | 8098 |
| Synchronisation/threads-cv.pdf | OSTEP | textbook | 19 p | 28 | 8845 |
| Synchronisation/threads-locks.pdf | OSTEP | textbook | 22 p | 40 | 12295 |
| Synchronisation/threads-sema.pdf | OSTEP | textbook | 20 p | 33 | 10414 |
| Threads/FALLSEM2025-26_VL_BCSE303L_00100_TH_2025-08-03_Threads.pptx | VIT | lecture | 36 s | 17 | 1978 |
| Threads/lecture12.pdf | IIT Bombay | lecture | 11 p | 7 | 697 |
| Threads/threads-api.pdf | OSTEP | textbook | 12 p | 22 | 5610 |
| Threads/threads-intro.pdf | OSTEP | textbook | 16 p | 29 | 7867 |
| Threads/threads.pdf | IIT Bombay | lecture | 13 p | 9 | 1275 |

(Tokens here are whole-document tokens from `documents.json`; chunk tokens sum slightly differently
because chunk text is rendered per chunk.)

### Files created in Phase 1

| Path | Purpose |
| --- | --- |
| `requirements.txt` | dependency minimums |
| `src/__init__.py` | package marker |
| `src/ingestion/__init__.py` | package docstring |
| `src/ingestion/scanner.py` | corpus scan, document IDs, hashes |
| `src/ingestion/loaders.py` | format-specific extraction (PDF, PPTX, PPT, DOCX, TXT/MD) |
| `src/ingestion/cleaner.py` | artifact removal and block assembly |
| `src/ingestion/metadata.py` | evidence-based metadata and keyword topic classification |
| `src/ingestion/dedup.py` | document and chunk duplicate detection |
| `src/ingestion/chunker.py` | structural/semantic chunking |
| `src/ingestion/validate.py` | output validation |
| `src/ingestion/pipeline.py` | orchestration, CLI, manifest and report generation |
| `tests/test_ingestion.py` | 15 tests with runtime-generated fixtures |
| `data/…` | generated artifacts (see Output Artifacts) |

No files existed beforehand, so no files were modified; `Docs/` was only read.

### Dependencies

- Used as already installed: PyMuPDF, python-pptx, tiktoken, pytest.
- Added: `olefile` (legacy `.ppt` support: OLE compound-file access). Installed into the system
  Python with `python3 -m pip install olefile`.
- DOCX is parsed with the standard library (`zipfile` + `xml.etree`); python-docx was deliberately not
  added.
- LibreOffice/`soffice` is not installed, so `.ppt` is parsed directly rather than converted.
- No OCR engine is installed or used.

### Implementation (as built)

Pipeline order (`pipeline.py`): scan → extract → clean → classify metadata → dedup documents → chunk →
mark duplicate chunks → validate → write artifacts and report.

- **`scanner.py`**: walks `Docs/` recursively in sorted order. Skips hidden files (e.g. `.DS_Store`)
  and lists them as ignored. Lists files with unsupported extensions as unsupported (never silently
  dropped). For each supported file it records `document_id`, filename, relative/absolute path,
  extension, size, modification time, SHA-256 of the bytes, and `topic_area` = first folder under
  `Docs/`. Supported extensions: `.pdf .pptx .ppt .docx .txt .md`.
- **`loaders.py`**: one loader per format, all returning the same unit/line structure (units = pages
  or slides; lines carry a kind: heading/text/code/bullet/table/notes). Also holds the `extract()`
  dispatcher (the originally proposed `extractor.py` was merged here).
  - PDF (PyMuPDF): char-level extraction; visual-line reconstruction that merges only same-baseline,
    adjacent fragments so side-by-side text boxes keep their own reading order; removal of
    overprinted/shadow duplicate text; recovery of TeX underscores drawn as strokes; font-size-based
    heading levels; bold-only short lines as low-level headings; monospace-font code detection with a
    regex fallback for documents without monospace fonts; removal of tiny gutter line numbers;
    paragraph-break, hard-line-break and wrapped-line decisions from geometry. Landscape PDFs are
    treated as slide decks (the title is the largest line in the top quarter, or anywhere on page 1).
  - PPTX (python-pptx): slide number, title placeholder (or a short top text box as fallback title),
    shapes in reading order (top, left), group shapes flattened, bullet levels, tables as pipe rows,
    speaker notes, monospace/regex code detection. Footer, slide-number and date placeholders are
    skipped. Slide-master text is kept only as metadata evidence.
  - PPT (olefile): parses the "PowerPoint Document" record stream directly; slide order comes from
    SlideListWithText persist references resolved through the persist directory chain. Also reads
    title/body text types, notes via `notesIdRef`, and master text.
  - DOCX (stdlib): paragraph styles → headings/lists/code, tables as pipe rows; no pagination.
  - TXT/MD: Markdown headings, fenced code, paragraphs.
- **`cleaner.py`**: targeted character normalization (ligatures, NBSP, soft hyphens, Office
  private-use bullet glyphs, "c⃝" → ©). Removes running headers/footers: lines in the top 12% / bottom
  15% of a page whose digit-normalized text repeats on at least max(3, 30%) of pages, plus standalone
  page numbers there; answer lines are never removed. Assembles lines into blocks: heading, paragraph,
  list_item, code, table, notes. It also:
  - dehyphenates words broken across lines, checking a per-document vocabulary so compounds like
    "compare-and-swap" keep their hyphen;
  - rebuilds code indentation and straightens typographic quotes in code;
  - gives a short run of non-prose lines between code lines the code kind;
  - keeps figure captions and Q/A markers as standalone paragraph starts.

  It also renders blocks to Markdown-style text (fenced code, indented `-` bullets).
- **`metadata.py`**: evidence-based source/professor/author/semester/module/course code/lecture date/
  derived_from/document_type rules, each with a recorded reason (`metadata_evidence`). Keyword/regex
  taxonomy of 11 Threads and 19 Synchronization subtopics plus 6 problem types. Document-level
  subtopics require ≥ 3 mentions and ≥ 1 mention per 1,000 tokens; chunk-level subtopics require ≥ 1
  mention.
- **`dedup.py`**: exact file-hash duplicates, then identical normalized-text duplicates (the canonical
  copy is the first in corpus order, preferring names without "copy"). Near-duplicate/overlap detection
  compares 5-word shingles pairwise: `near_duplicate` when Jaccard ≥ 0.8, `overlap` when containment
  ≥ 0.5. Exact duplicate chunks get `duplicate_of` pointing at their first occurrence. Nothing is
  deleted.
- **`chunker.py`**: builds segments from headings (the section path comes from the heading stack) and
  from sequentially numbered questions/problems (Q&A mode when there are ≥ 3 sequential numbered items
  and the document type is practice_problems/question_paper/assignment/lab/tutorial or ≥ 3 answer
  markers). Merge and split rules:
  - A question ends at the next question or at a heading at or above the level that contained the
    questions. When questions are themselves headings, only a strictly shallower heading ends one.
  - Slide continuations ("X (cont)", "X (2)") merge with the previous segment.
  - Segments under `MIN_TOKENS`=40 merge forward, and Q&A never merges.
  - Sections up to `MAX_TOKENS`=600 stay whole. Larger ones split at block boundaries toward
    `TARGET_TOKENS`=350; a chunk never ends on a heading, and a block ending in ":" stays with what
    follows it.
  - A question with its answer stays whole up to `QA_MAX_TOKENS`=1000. Beyond that it is cut at the
    answer marker, and continuation parts get a "[Question N, continued: …]" stub.
  - Oversized single blocks split by lines (code/tables/lists) or sentences (prose).
  - Deterministic chunk IDs are `<document_id>::cNNNN`.
- **`validate.py`**:
  - Errors: extraction failures, empty documents, documents without chunks, duplicate chunk IDs,
    empty chunks, missing/unknown document IDs, missing source references, and missing page (PDF) or
    slide (PPT/PPTX) locations.
  - Warnings: tiny documents (< 100 tokens), oversized chunks (> 110% of their limit), tiny chunks
    (< 20 tokens), and pages/slides with images but almost no text.
  - Info: duplicates and near-duplicates.
- **`pipeline.py`**: CLI `--source` (default `Docs`) and `--output` (default `data`). It refuses to write
  inside the source directory. Each run deletes and regenerates only `raw_extracted/`, `cleaned/`,
  `chunks/` and `manifests/` under the output directory. Per-document extraction errors are caught and
  recorded, never skipped. It writes all artifacts, prints the summary, and exits 1 if any validation
  error exists.
- **`tests/test_ingestion.py`**: 15 tests covering PDF extraction (pages, heading, code, header
  removal), PPTX extraction (slides, titles, bullet levels, notes, code), DOCX extraction (heading,
  list, table), legacy PPT on the real corpus file (skipped if absent), unsupported-file reporting,
  evidence-based metadata, deterministic IDs/chunks, exact duplicate detection, near-duplicate
  recording, chunk splitting/merging, code preservation, Q&A preservation across pages, chunk
  traceability, raw-corpus immutability, and refusal to write output inside the source.

### Output Artifacts

| Path | Content |
| --- | --- |
| `data/raw_extracted/<document_id>.json` | loader output before cleaning: units (pages/slides) with typed lines, PDF geometry, embedded file properties, slide-master text |
| `data/cleaned/<document_id>.json` | cleaned structural blocks per page/slide |
| `data/cleaned/<document_id>.md` | human-readable rendering of the cleaned document with page/slide markers (for inspection) |
| `data/chunks/chunks.jsonl` | one chunk per line (463 lines, 29 fields each) |
| `data/manifests/documents.json` | one metadata record per document (22) |
| `data/manifests/corpus_manifest.json` | totals, breakdowns by topic/source/type/format, chunking config, token stats, supported/unsupported/ignored files, duplicates, near-duplicates, extraction failures |
| `data/manifests/corpus_report.md` | human-readable report of exactly what was ingested, metadata evidence, subtopics, duplicates and validation issues |
| `data/manifests/validation.json` | list of validation issues (level, code, document_id, chunk_id, message) |

Chunk fields: `chunk_id`, `document_id`, `chunk_index`, `text`, `token_count`, `char_count`, `filename`,
`relative_path`, `source`, `document_type`, `topic_area`, `subtopics`, `problem_types`, `page_start`,
`page_end`, `slide_start`, `slide_end`, `section`, `section_path`, `chunk_type`
(`section`/`slide`/`qa_pair`/`problem`), `content_type` (`text`/`mixed`/`code`), `question_number`,
`has_answer`, `refers_to_question`, `part`, `part_count`, `text_hash`, `is_duplicate_document`,
`duplicate_of`. Fields that do not apply are `null`. Every chunk traces back to document → filename →
page or slide range → section.

### Metadata Strategy

Rule: a field is filled only when the file supports it, and the reason is written to
`metadata_evidence`. Everything else stays `null` or `"unknown"`.

| Field | How it is set |
| --- | --- |
| `document_id` | readable slug of the filename stem (≤ 40 chars) + first 8 hex chars of SHA-1 of the relative path |
| `filename`, `relative_path`, `file_type` | from the filesystem |
| `course` | constant "Operating Systems" (project scope) |
| `topic_area` | the corpus folder the file is filed under (`Threads` / `Synchronisation`), not the filename |
| `subtopic` | keyword/regex counts over the cleaned text (thresholds above); raw counts in `subtopic_scores` |
| `source`, `professor`, `author`, `semester`, `module`, `course_code`, `lecture_date`, `derived_from`, `document_type` | evidence rules, see the three categories below |
| `page_count` / `slide_count` | from the file (PDF pages; PPT/PPTX slides) |
| `file_hash` | SHA-256 of the raw file bytes |
| `content_hash` | SHA-256 of the normalized extracted text (lowercase alphanumerics) |
| `file_properties` | embedded author/title/creator exactly as stored in the file; unverified and never used for professor |

**1. Supported directly by document content**

- OSTEP source (6 chapters): running footers contain THREE EASY PIECES / ARPACI-DUSSEAU /
  WWW.OSTEP.ORG. Author "Arpaci-Dusseau" comes from the copyright footer. A mere citation such as
  "Image credit: OSTEP" does not count.
- IIT Bombay source and professor "Mythili Vutukuru" (7 documents): the name is printed next to
  "IIT Bombay" on the first page/slide.
- `derived_from` for two VIT PPTX decks: slide-master text ("Silberschatz, Galvin and Gagne ©2018;
  Operating System Concepts – 10th Edition" and the ©2009 / 8th Edition equivalent).
- `document_type` from first-page text ("Lecture N", "Lab:", "Practice Problems").
- SUMSEM `module` = "Module 4": slide 1 text "Module 4:" (the filename agrees).

**2. Inferred from filenames**

- `source` = "VIT" for 5 documents: the VTOP course-material filename pattern
  `<SEM>_<slot>_BCSE303L_<n>_TH_<date>_<title>`. No file text contains "VIT".
- `semester`, `course_code` (BCSE303L) and `lecture_date` for the same 5 documents.
- SUMSEM `module` (the evidence string records "filename"; slide 1 also supports it).
- `document_type` = lab for `Thread_Synchronization_Lab_Problems.pdf` (filename contains "Lab").

**3. Structural/format evidence (not source identity)**

- `document_type` = lecture for slide decks without other cues.
- textbook for OSTEP chapters.
- programming_examples when ≥ 50% of the text is code (`dining philospher.pdf`: 78%).
- notes for the VIT theory-course (TH) document-form handout.

**4. Currently unknown**

- `source` for 4 documents: `Concurrency bugs.pptx`, `Semaphore.ppt - Copy.pptx`,
  `Thread_Synchronization_Lab_Problems.pdf`, `dining philospher.pdf`.
- `professor` for all VIT, OSTEP and unknown-source documents.
- `module` for everything except the SUMSEM deck. The VIT `.ppt` says "Module 6: Process
  Synchronization" on slide 2. Modules are only read from the filename or the first slide, so it stays
  null; this number appears to follow textbook chapter numbering, not the VIT course module.
- `semester` for all non-VIT documents.

### Validation and Reproducibility

- `Docs/` is an immutable input: the pipeline only reads it, refuses to write outputs inside it, and
  the test suite checks that fixture corpus hashes are unchanged after a run.
- Document IDs, chunk IDs, content hashes and chunk boundaries are deterministic.
  - IDs derive from relative paths and chunk indices, not random values.
  - Iteration order is sorted and no timing data is used.
  - The only run-dependent values are `ingestion_timestamp` (documents.json), `generated_at`
    (corpus_manifest.json) and the "Generated …" line in corpus_report.md.
- `chunks.jsonl` contains no timestamps and is expected to be byte-identical across runs.
- Validation of the baseline:
  - 0 errors.
  - 7 `image_only_content` warnings (see Known Limitations 2).
  - 1 `near_duplicate` info (`Semaphore.ppt - Copy.pptx` ~ `lecture15.pdf`).
  - No oversized-chunk, tiny-chunk, missing-location or missing-reference issues.

### Phase 1 Decisions

- **`Docs/` is immutable.** It is the raw evidence that citations point back to. Keeping it read-only
  keeps file hashes stable, makes every artifact reproducible from the same inputs, and avoids data
  loss. All generated data goes to `data/`.
- **Stable IDs and SHA-256 hashes.** Future citation generation needs chunk → document → page/slide
  links that survive re-runs. Path-based document IDs keep identical copies distinct while byte hashes
  detect them; content hashes detect re-exports with identical text.
- **Structural/semantic chunks instead of fixed token windows.** The corpus is teaching material in
  which a section, slide or question is the unit a student asks about. Chunks follow headings, slides
  and questions; size limits only split what is too large and merge what is too small.
- **Q&A pairs stay together.** A question without its answer (or the reverse) is useless for
  retrieval and answer grounding. Q&A mode keeps them together up to 1,000 tokens, across page breaks
  (e.g. question 44, pages 30–31). Continuation parts carry a question stub, and `refers_to_question`
  links "repeat the previous question" items.
- **Code blocks are preserved.** API names (`pthread_create()`, `pthread_cond_wait()`, `sem_wait()`, …)
  and line structure matter for OS questions. Code is detected, fenced, kept intact, indentation is
  rebuilt, and TeX underscores are recovered.
- **Duplicates are detected, not deleted.** Retrieval policy for duplicates belongs to a later phase;
  deleting would lose provenance. Relationships are recorded (`is_duplicate`, `duplicate_of`,
  `near_duplicates`, chunk `duplicate_of`).
- **Provenance is retained.** Every chunk carries filename, relative path, page/slide range and section
  path, and every inferred metadata field carries its evidence, so later phases can cite sources and
  audit metadata.
- **Evidence-only metadata.** Required by the Phase 1 instructions (no invented professor, semester or
  module). Embedded file authors are kept visible but unused because they were found to be unreliable.

### Deviations from the Original Phase 1 Specification

- `extractor.py` was merged into `loaders.py` (it would only have been a dispatcher).
- `--force` and `--report` were not implemented: the pipeline always does a full rebuild (about 4 s)
  and always writes the report.
- DOCX page numbers are `null` (no fixed pagination in the current DOCX extraction).
- `chunks.json` (optional) was not produced; `chunks.jsonl` is the chunk output.
- Additional outputs beyond the spec: `data/cleaned/*.md` renderings and `data/manifests/validation.json`.
- Additional metadata beyond the minimum schema: `file_hash`, `title`, `author`, `course_code`,
  `lecture_date`, `derived_from`, `problem_types`, `subtopic_scores`, `metadata_evidence`,
  `file_properties`, `layout`, `code_char_ratio`, `image_only_units`, and duplicate fields.

### Problems Encountered and Resolved During Phase 1

Found while inspecting cleaned output against the real corpus, or by the test suite:

1. The OSTEP monospace font (`NimbusMonL`) was not recognized as monospace, so code detection fell back
   to the regex. Fixed by adding `monl` to the monospace font pattern.
2. OSTEP gutter line numbers glued onto code lines ("1 void *child…"). Fixed: tiny leading digit spans
   are stripped.
3. Prose starting with "solution will…" was treated as an answer marker. Fixed: markers must be
   followed by punctuation or end of line.
4. OSTEP page numbers at about 89% of page height escaped header/footer removal. Fixed: margin zones
   widened to top 12% / bottom 15%.
5. Inline-code underscores in TeX PDFs were lost (`pthread cond t`). Fixed: underscores recovered from
   vector strokes inside space glyphs (`pthread_cond_t`, `thr_join()`).
6. Overlapping line boxes split every wrapped line into separate paragraphs; sample input/output lines
   were merged into prose. Fixed: gap thresholds scale with font size, and short lines become hard line
   breaks inside a block.
7. Title slides of slide PDFs had no heading. Fixed: page 1 allows the title anywhere on the page.
8. Word-exported pseudocode lines without C punctuation ("Take_fork (Ri)") broke code blocks. Fixed:
   run-based code smoothing, excluding label lines ending in ":".
9. The professor regex spanned line breaks ("Locks\nMythili Vutukuru"). Fixed: names are matched within
   one line.
10. `threads.pdf` and `pthreads-sync.pdf` were labelled OSTEP because they cite OSTEP. Fixed: only OSTEP
    page furniture counts; both are now IIT Bombay.
11. Document titles picked a page header over the main title. Fixed: prefer the top-level heading.
12. In `pthreads-sync.pdf`, all sections after warm-up item 3 were glued into question 3. Fixed: the
    hybrid heading/question segmentation described in Implementation.
13. Title slides raised false image-only warnings. Fixed: unit 1 is exempt.
14. Code indentation encoded as leading space glyphs was lost. Found by a test; fixed.
15. A heading-only segment before a section large enough to split became a stranded 3-token chunk.
    Found by a test; fixed: it rides with part 1.
16. Figure captions merged with the next paragraph. Fixed: captions stand alone.
17. Overprinted glyph fragments on `lecture13.pdf` page 7 ("E l f i i i d"). Fixed: all overlapped
    shorter fragments on a baseline are dropped.

### Known Limitations (Phase 1 baseline)

1. Code and diagrams that exist only as images are not OCR'd (no OCR engine is used).
2. Image-only content is flagged in 7 documents, 28 pages/slides in total (from `validation.json`):
   - `FALLSEM2025-26_VL_BCSE303L_00100_TH_2025-09-16_Process-synchronization.pptx`: slides 5, 7, 34, 36
   - `SUMSEM2025-26_VL_BCSE303L_00100_TH_2026-06-15_Module-4---Process-Synchronization.pptx`: slides 12, 22, 23, 28, 33, 40, 42, 70
   - `lecture14.pdf`: pages 4, 8
   - `lecture15.pdf`: page 5
   - `FALLSEM2025-26_VL_BCSE303L_00100_TH_2025-08-03_Threads.pptx`: slides 4, 7, 8, 9, 14, 16, 18, 20, 33
   - `lecture12.pdf`: pages 7, 8, 10
   - `threads.pdf`: page 7
3. VIT source metadata (5 documents) is inferred from the filename; the documents themselves do not
   contain "VIT".
4. Four documents have unknown source metadata: `Concurrency bugs.pptx`, `Semaphore.ppt - Copy.pptx`,
   `Thread_Synchronization_Lab_Problems.pdf`, `dining philospher.pdf`.
5. The Classical-problems PDF (`FALLSEM2025-26_…_2025-09-23_Classical-problem-of-synchronization.pdf`)
   has embedded author metadata "DEEPA SARAVANAKUMAR". The text does not identify the author as
   professor, so the name is kept only in `file_properties` and `professor` is null.
6. The SUMSEM synchronization deck has conflicting module information: the filename and title slide
   say Module 4, slide 2 says "Module 3: Process Synchronization". The current implementation uses
   Module 4.
7. 22 chunks exceed 512 tokens, 4 of them Q&A chunks (all are within the pipeline's own limits of
   600/1000).
8. Subtopic classification is keyword/regex based.
9. Code detection in Word/PowerPoint exports is pattern based (TeX PDFs use the monospace-font signal).
10. DOCX page numbers are null because the current DOCX extraction has no fixed pagination.
11. tiktoken downloads its `cl100k_base` encoding on first use (network needed once; cached afterwards).
12. `olefile` was added for legacy `.ppt` support.
13. `extractor.py` was merged into `loaders.py`.
14. `--force` and `--report` were not implemented: every run is a full rebuild and always writes the report.

### Unresolved Questions (for the project owner)

1. May the VIT source continue to be inferred from the VTOP filename pattern, or should those 5
   documents become `unknown` until confirmed?
2. What is the authoritative source of the 4 unknown-source documents?
3. Is DEEPA SARAVANAKUMAR the faculty member for the Classical-problems handout?
4. Which module number is authoritative for the SUMSEM deck (Module 4 or Module 3)?
5. How should retrieval treat the near-duplicate pair and the 4 duplicate chunks (drop, down-weight,
   or keep with provenance)?

### Phase 2 Design Considerations (deferred on purpose; not implemented)

These were explicitly deferred at the Phase 1 freeze. They are recorded here so Phase 2 decides them
deliberately:

- OCR for the 28 image-only pages/slides (IITB lecture code screenshots, VIT diagrams).
- Chunk size limits vs the chosen embedding model's context window: 22 chunks exceed 512 tokens. Any
  change must preserve Q&A integrity, not just fit the model.
- Duplicate handling at retrieval time (near-duplicate pair, 4 duplicate chunks).
- Whether embeddings should include `section` / `section_path` context in the text that is embedded
  (chunk `text` currently contains only the chunk's own content).
- Resolution of the metadata questions above, ideally through an explicit override file (proposal
  below).
- Pinning dependency versions (the baseline versions are recorded above).

### Metadata Override Mechanism: proposed, not implemented

Checked on 2026-09-21: no override mechanism exists. None was added at the freeze, for two reasons:

- Wiring it in would change pipeline code, which the freeze excludes.
- No authoritative corrections have been provided yet, so the file would be empty.

Proposed design for when the project owner supplies verified values: a file `metadata_overrides.json`
at the project root (outside `Docs/`), keyed by `relative_path`:

```json
{
  "Docs/Synchronisation/Thread_Synchronization_Lab_Problems.pdf": {
    "source": "<value confirmed by the project owner>",
    "_provided_by": "<name>",
    "_date": "YYYY-MM-DD",
    "_note": "<why this value is authoritative>"
  }
}
```

Intended behavior when implemented:

- The pipeline applies overrides after automatic classification.
- It records `metadata_evidence[field] = "manual override by <_provided_by> on <_date>"`.
- It keeps the automatically inferred value alongside for audit.
- It never applies placeholder values.

---

## 2026-09-21 — Phase 1 Finalization (freeze, document, verify)

Work performed in this session (no pipeline code or corpus changes):

1. Inspected the repository, `src/ingestion/`, tests, `requirements.txt`, `corpus_report.md`,
   `validation.json` and the `chunks.jsonl` structure. The implementation matches the description in
   this log. There is still no git repository.
2. Hashed all 24 files under `Docs/` (22 documents + 2 `.DS_Store`) before verification. All 22 hashes
   match `file_hash` in `documents.json`, which was produced by the Phase 1 run.
3. Ran `python3 -m pytest tests -q` → **15 passed**.
4. Ran the pipeline twice into scratch directories (not `data/`):
   `python3 -m src.ingestion.pipeline --source Docs --output <scratch>/runA` and `…/runB`. Both exited
   0 with 22/22 extracted, 463 chunks, 99,322 tokens, and 0 errors / 7 warnings / 1 info.
5. Compared all 71 output files of runA vs runB, and of runA vs the existing `data/`, after masking only
   `ingestion_timestamp`, `generated_at` and the report's "Generated …" line: **no differences**.
   `chunks.jsonl` is **byte-identical** across runA, runB and `data/` (SHA-256 `90d1e88e…fcbe16`).
6. Checked `chunks.jsonl` integrity:
   - 463 lines, all valid JSON, all with the same 29 fields.
   - Unique chunk IDs in `<document_id>::cNNNN` format.
   - Every chunk's document ID, filename and relative path match `documents.json`.
   - Every PDF chunk has a page and every PPT/PPTX chunk has a slide.
   - Per-document `chunk_count` equals the actual number of chunks.
7. Checked `validation.json`: 7 warnings + 1 info, consistent with the manifest totals and identical to
   a fresh run.
8. Re-hashed `Docs/` after verification: identical to the pre-verification hashes.
9. `data/manifests/corpus_report.md` already reflects the verified state (generated by the baseline
   run) and was left unchanged.
10. Created `PROJECT_LOG.md` (this file) at the project root, and a `CLAUDE.md` at the project root that
    tells future sessions to read and append to this log.

**Incident during finalization (2026-09-21), resolved:** the log was first written to the requested path
`docs/PROJECT_LOG.md`. The macOS filesystem here is case-insensitive, so `docs/` *is* `Docs/`, and the
file landed inside the raw corpus as `Docs/PROJECT_LOG.md`. The final hash check caught it: the file set
differed from the pre-session baseline. The file was moved to the project root; no original corpus file
was modified, and the pipeline was not run while the stray file existed, so it was never ingested.
After the move, all 24 files under `Docs/` (22 documents + 2 `.DS_Store`) have exactly the pre-session
SHA-256 hashes. Only the `Docs/` directory's own modification time changed, because an entry was added
and removed.

Consequences and decisions:

- Project documentation must not live in a directory named `docs/` (in any letter case) in this
  repository. The log lives at the root as `PROJECT_LOG.md`.
- Because `.md` is a supported corpus format, anything placed under `Docs/` would be ingested as course
  material. That is another reason to keep all project files outside it.

**Correction to the Phase 1 hand-off summary (2026-09-21):** the chat summary at the end of Phase 1
said the 4 duplicate chunks were "shared between the VIT decks". Verified from `chunks.jsonl`, the
split is 3 VIT-to-VIT duplicates plus 1 between `lecture15.pdf` and `Semaphore.ppt - Copy.pptx`:

- `fallsem…975bc607::c0016` → `fallsem…3f6ce962::c0018`
- `sumsem…02c11114::c0004` → `fallsem…3f6ce962::c0001`
- `sumsem…02c11114::c0049` → `fallsem…975bc607::c0033`
- `lecture15-918b182c::c0001` → `semaphore-ppt-copy-0dcb4a42::c0001`

The generated artifacts were always correct; only the prose summary was imprecise.

Result: **Phase 1 = COMPLETE + DOCUMENTED + VERIFIED + FROZEN.**

---

## Phase 2 — Embedding, Vector Indexing and Baseline Dense Retrieval

**Status: COMPLETE** (started and completed 2026-09-21 on explicit instruction from the project owner; see Phase 2 Final Status)

Phase plan as defined by the project owner at Phase 2 start (supersedes the tentative table in Project
Overview): Phase 3 = advanced retrieval / reranking, Phase 4 = RAG generation, Phase 5 = evaluation /
research experiments. All three are NOT STARTED.

### 2026-09-21 — Phase 2 start: inspection

- Read `CLAUDE.md` and this log. No conflict between `CLAUDE.md` and the Phase 2 instructions.
- Read-only Phase 2 inputs: `Docs/`, `data/chunks/chunks.jsonl`, `data/manifests/documents.json`,
  `data/manifests/corpus_manifest.json`. Phase 1 code is not modified.
- Confirmed the `chunks.jsonl` schema: 463 chunks, 29 fields, unchanged from the Phase 1 description.
  - The chunk records do not carry `course`, `module`, `semester`, `professor` or document-level
    `subtopic`; those exist only in `documents.json` and must be joined by `document_id`.
  - Nulls in `documents.json`: `module` 21/22, `semester` 17/22, `professor` 15/22.
  - Nulls in the chunks: `page_*` for 154 slide chunks, `slide_*` for 309 page chunks,
    `question_number` for 390 chunks, `section` for 1 chunk.
- Environment: Apple M3, 16 GB RAM, macOS 27.0 arm64, Python 3.13.7 (`/usr/local/bin/python3`).
  - Already installed: `qdrant-client` 1.19.0, `huggingface_hub` 1.31.0, `numpy` 2.5.3.
  - Not installed: torch, transformers, sentence-transformers, onnxruntime, tokenizers, fastembed.
  - The Hugging Face cache already holds `BAAI/bge-small-en-v1.5` and `BAAI/bge-large-en` (from outside
    this project).
  - Docker is installed but not needed.

### Embedding model decision

Criteria: local execution with no API key, open licence, English retrieval quality, input length vs
current chunk sizes (max 913 `cl100k` tokens; WordPiece counts are higher for code), embedding size,
and reproducibility (pinned weights, no remote code execution).

| Candidate | Dim | Max input tokens | Licence | Notes |
| --- | --- | --- | --- | --- |
| **nomic-ai/nomic-embed-text-v1.5** (selected) | 768 | 8192 | Apache-2.0 | Strong English retrieval model. Official ONNX export in the repo, so no remote Python code runs. Requires task prefixes `search_document: ` / `search_query: `. |
| BAAI/bge-small-en-v1.5 | 384 | 512 | MIT | Already cached. The 512-token limit would truncate long chunks. |
| BAAI/bge-base-en-v1.5 | 768 | 512 | MIT | Same truncation problem. |
| Snowflake/snowflake-arctic-embed-m-v1.5 | 768 | 512 | Apache-2.0 | Same truncation problem. |
| Alibaba-NLP/gte-base-en-v1.5 | 768 | 8192 | Apache-2.0 | Long context, but running it through sentence-transformers needs `trust_remote_code`. A reasonable later alternative. |
| BAAI/bge-m3 | 1024 | 8192 | MIT | Multilingual and about 4x larger (568M parameters; the ONNX weights are about 2.2 GB of external data). Heavier than needed for an English-only baseline. |

Selected: `nomic-ai/nomic-embed-text-v1.5`, `onnx/model.onnx` (fp32), pinned to revision
`e9b6763023c676ca8431644204f50c2b100d9aab`. It runs through `onnxruntime` + `tokenizers` instead of
fastembed or sentence-transformers, so that truncation, pooling, normalisation and prefixes are
explicit in project code and not hidden library defaults. The long context means every Phase 1 chunk
can be embedded whole, with no truncation and no Phase 1 change. This is to be verified with the
model's own tokenizer before indexing. The multi-model benchmark is out of scope for Phase 2.

### 2026-09-21 — Dependencies and chunk-length verification

- Installed: `onnxruntime==1.30.0`, `tokenizers==0.23.2` (`python3 -m pip install onnxruntime==1.30.0
  tokenizers==0.23.2`). Reused, already installed: `qdrant-client==1.19.0`, `huggingface_hub==1.31.0`,
  `numpy==2.5.3`. Not installed on purpose: torch, transformers, sentence-transformers, fastembed.
- Downloaded the pinned model files (`onnx/model.onnx` 548 MB, `tokenizer.json`, `config.json`,
  `tokenizer_config.json`) to the Hugging Face cache (about 243 s). Later loads use the cache
  (`local_files_only=True` first).
  - `onnx/model.onnx` SHA-256:
    `147d5aa88c2101237358e17796cf3a227cead1ec304ec34b465bb08e9d952965`.
  - ONNX inputs: `input_ids`, `token_type_ids`, `attention_mask`. Output: `last_hidden_state`
    (…, 768).
- **Input limit finding:** `config.json` has `n_positions=8192` but `max_position_embeddings=2048` and no
  `rotary_scaling_factor`. Nomic's long-context mode needs rotary scaling that this ONNX graph does not
  apply, so the project treats **2,048 tokens** as the model's limit, not 8,192.
- **Chunk lengths with the model's own tokenizer** (BERT uncased WordPiece, including the
  `search_document: ` prefix and [CLS]/[SEP]):
  - max 1,045 (`ps-concurrency-381f1b77::c0025`), median 204.
  - 31 chunks over 512, 1 over 1,024, **0 over 2,048**. The median WordPiece/cl100k ratio is 1.08.
  - Decision: every chunk is embedded whole. No truncation, windowing or Phase 1 change is needed. The
    embedder has truncation disabled and raises an error for any input above 2,048 tokens instead of
    cutting it.
  - Note: a 512-token model would have truncated 31 chunks, not the 22 counted with cl100k.

### 2026-09-21 — Architecture as implemented

New package `src/retrieval/` (Phase 1 code untouched):

| File | Responsibility |
| --- | --- |
| `embeddings.py` | `EmbeddingModel` interface (`embed_documents`, `embed_query`, `dim`). `ModelSpec` registry `MODELS` holds repo, pinned revision, weights file, dim, max tokens, prefixes and licence. `OnnxEmbeddingModel` runs on the CPU provider with 4 threads, one text per call (no padding): mean pooling then L2 normalisation. Empty or non-string input and over-limit input raise `ValueError`. `load_model(key)`. |
| `vector_store.py` | `QdrantStore`, the only module importing `qdrant_client`: local embedded mode (`QdrantClient(path=…)`), create/recreate a cosine collection, upsert, exact count, config, filtered search via `query_points`, scroll. Deterministic point IDs = `uuid5(NAMESPACE_URL, "os-tutor-rag:" + chunk_id)`. |
| `indexer.py` | CLI `python3 -m src.retrieval.indexer [--recreate]`. Validates `chunks.jsonl` (JSON, required fields, unique IDs, `text_hash` matches text) and that every chunk's document exists in `documents.json`. Embeds each chunk, records per-chunk failures, builds payloads, (re)creates the collection, upserts, and writes the index manifest. It refuses to replace an existing collection without `--recreate`. |
| `retriever.py` | `Retriever.open()` checks that the current `chunks.jsonl` SHA-256 equals the manifest's, that the model revision and dim match, and that the collection exists with the recorded count. `search(query, top_k=5, filters=None)` returns ranked results with score, chunk ID, provenance, payload metadata, canonical text from `chunks.jsonl`, and `text_verified` (`text_hash` check). |
| `search.py` | Debugging CLI `python3 -m src.retrieval.search --query … [--top-k N] [--filter field=value …] [--max-chars N] [--json]`. |

Decisions:

- **Vector store:** Qdrant local embedded mode, persisted in `data/vector_store/qdrant/` (3.9 MB for 463
  × 768 vectors). No Docker, server or cloud account. Local mode searches by exact brute force, so
  results have no approximate-nearest-neighbour randomness. Only one client may open the path at a
  time (Qdrant's local-mode lock).
- **Distance:** cosine. The model is trained for cosine similarity, and its vectors are L2-normalised
  anyway.
- **Collection name:** `os_tutor_chunks__nomic_embed_text_v1_5`, derived from the model key so that
  indexes of different models can coexist later.
- **Canonical text is not stored in the payload.** Results resolve text from `chunks.jsonl` by
  `chunk_id` and verify it against the payload's `text_hash`. There is only one editable copy of the
  text, and a stale index is detected, not silently served.
- **Payload:** Phase 1 values are copied verbatim.
  - Chunk fields: `chunk_id`, `document_id`, `chunk_index`, `filename`, `relative_path`,
    `topic_area`, `subtopics`, `problem_types`, `source`, `document_type`, `page_start/end`,
    `slide_start/end`, `section`, `section_path`, `chunk_type`, `content_type`, `question_number`,
    `has_answer`, `refers_to_question`, `part`, `part_count`, `token_count`, `text_hash`,
    `is_duplicate_document`, `duplicate_of`.
  - Joined from `documents.json`: `course`, `module`, `semester`, `professor`, `document_subtopics`
    (document-level `subtopic`), `document_title`, `file_type`, `near_duplicate_documents`.
  - Nulls stay null; nothing is inferred.
- **Embedded text:** `search_document: ` + the unmodified chunk text. Section context is not
  prepended in the baseline. Contextual embedding is a candidate experiment for a later phase.
- **Index manifest location:** `data/vector_store/index_manifest.json`, not the suggested
  `data/manifests/index_manifest.json` (deviation). The Phase 1 pipeline deletes and regenerates
  `data/manifests/` on every rebuild; that would silently remove the manifest while the index survived.
- **Filters:** exact match on `topic_area`, `document_type`, `source`, `professor`, `module`,
  `semester`, `content_type`, `chunk_type`, `course`, `document_id`, `filename`, `subtopics`,
  `problem_types`.
  - A list value matches any of its values; different fields must all match.
  - Unknown fields and null/empty values raise `ValueError`.
  - A value that matches nothing returns an empty list.
  - Null metadata never matches a value filter.
- **Duplicates:** all 463 chunks are indexed, including the 4 exact-duplicate chunks and both documents
  of the near-duplicate pair. Results expose `chunk_id`, `document_id`, `duplicate_of`,
  `is_duplicate_document` and `near_duplicate_documents`, so duplicate retrieval can be analysed later.
  No deduplication policy has been invented.

### 2026-09-21 — Index build

Command: `python3 -m src.retrieval.indexer` (2 min 56 s wall time on the M3 CPU).

- Chunks read 463, embedded 463, indexed 463, failures 0.
- Collection `os_tutor_chunks__nomic_embed_text_v1_5`: dim 768, Cosine.
- Corpus identity: `chunks.jsonl` SHA-256 `90d1e88e…fcbe16`, identical to the Phase 1 baseline.
- Digests: vectors `1d65a777…71d99f`, payloads `3885d239…d4b12e`.
- A second run without `--recreate` exited 1 with "collection … already exists …; pass --recreate",
  as designed.
- The CLI query "How does Peterson's solution provide mutual exclusion?" ranked a VIT slide
  "Correctness of Peterson's Solution" first, with verified text.
- Observation for later phases (not changed): OSTEP "References" chunks can rank high because they
  cite the same concepts.

Determinism check before the build (41 chunks, including the longest): embeddings were byte-identical
across repeated calls and across 1, 4 and 8 intra-op threads.

### 2026-09-21 — Tests

- New: `tests/test_retrieval.py` (29 tests) and `tests/retrieval_smoke_queries.json`.
  - Embeddings: model loads; dim 768; float32; unit norm; the query prefix differs from the document
    prefix.
  - Invalid input: empty, whitespace, `None`, non-string, a bare string instead of a list, and `[]`
    all handled.
  - Over-limit input is refused, not truncated. Embeddings are byte-deterministic. A basic
    embedding-space sanity check passes.
  - Index, using a temporary index of 23 chunks: counts and manifest; the reopened store keeps
    count, dim and distance; payload equals the Phase 1 values field by field (including the joined
    document fields); no text in the payload; deterministic point IDs; existing collection not
    replaced without `--recreate`.
  - Invalid chunk files are rejected (`text_hash` mismatch, duplicate ID). The retriever refuses a
    stale `chunks.jsonl`.
  - Real index: 463 = source = embedded = indexed, 0 failures, 0 inputs over the limit.
  - Retrieval: ranked results; top-k respected and validated; scores descending within [-1, 1];
    every result traced to `chunks.jsonl` (text identical and `text_verified`, provenance equal).
  - Filters: `topic_area`, `document_type`, `professor`, a list-valued `source`,
    `subtopics` + `content_type`, and `module` all return only matching chunks. A nonexistent value
    returns `[]`. An unknown field and a `None` value raise `ValueError`.
  - Duplicates: both copies of a duplicate chunk are retrievable. 10 parametrised smoke queries. CLI
    filter parsing and CLI JSON/text output, run against the temporary index.
- Fix during testing: the CLI test first opened the real index while the module-scoped retriever
  fixture held Qdrant's local-mode lock on it. Resolved by adding `--store/--manifest/--chunks` to the
  CLI and testing it against the temporary index.
- Results: `python3 -m pytest tests -q` → **44 passed** (15 Phase 1 + 29 Phase 2), about 13 s once the
  model is cached. `python3 -m pytest tests/test_ingestion.py -q` → 15 passed. An unrelated
  `pytest-asyncio` configuration warning comes from a plugin installed in the system Python.

### 2026-09-21 — Retrieval smoke tests (smoke only, not an evaluation)

Each query passes if at least one top-5 result carries an expected Phase 1 chunk subtopic or
contains an expected term. The expectations were written before any query was run. All 10 pass.
Observations below are what was returned, not relevance judgements.

| Query id | First rank with expected subtopic | Top-1 result (score) |
| --- | --- | --- |
| threads-vs-processes | 2 | VIT Threads.pptx "Comparison Between Process and Threads" (0.848) |
| pthread-create-join | 1 | OSTEP threads-api.pdf "27.2 Thread Completion" (0.813) |
| mutex-locks | 1 | VIT Process-synchronization.pptx "Mutex Locks" (0.809) |
| condition-variables | 1 | OSTEP threads-api.pdf "27.4 Condition Variables" (0.788) |
| semaphores | 1 | VIT SUMSEM deck "Semaphore Implementation" (0.835) |
| peterson | 1 | VIT Process-synchronization.pptx "Correctness of Peterson's Solution" (0.752) |
| producer-consumer | 1 | VIT Classical-problems PDF "1.Producer & Consumer problem using Semaphores" (0.872) |
| dining-philosophers | 1 | VIT SUMSEM deck "Deadlock situation and Solution" (0.859) |
| concurrency-bugs | 1 | Concurrency bugs.pptx "Order violation bug: example" (0.795) |
| spinlock-test-and-set | 1 | OSTEP threads-locks.pdf "28.7 Building Working Spin Locks with Test-And-Set" (0.799) |

Noted for later phases, not acted on:

- An OSTEP "References" chunk ranked #2 for the Peterson query.
- VIT slide decks dominate several top-5 lists.
- Top-5 lists can contain several chunks from one document.

### 2026-09-21 — Reproducibility

- Rebuilt the full index into a scratch directory
  (`python3 -m src.retrieval.indexer --store <scratch>/qdrant --manifest <scratch>/index_manifest.json`,
  2 min 43 s). The vectors digest and payloads digest are **identical** to the `data/vector_store`
  build, and the manifests are equal apart from `generated_at` and `path`.
- What is deterministic:
  - Point IDs (uuid5 of `chunk_id`), payloads, and the collection name/configuration.
  - Embedded text (prefix + unmodified chunk text) and vectors, given the same model revision, weights
    (SHA-256 recorded), onnxruntime/tokenizers/numpy versions, and CPU provider.
  - Vectors do not depend on batch composition (batch size 1, no padding) or on thread count
    (1/4/8 verified).
  - Search results: Qdrant local mode does exact brute-force cosine search, so there is no ANN
    randomness.
- Not guaranteed or not verified:
  - Bit-identical vectors on other CPUs, OS versions or runtime versions. Floating-point kernels may
    differ, which is why the Phase 2 runtime versions are pinned in `requirements.txt`.
  - The CoreML/GPU execution providers were deliberately not used.
  - `generated_at` in the index manifest changes on every build.
- The model weights are not stored in the repository. They are fetched once from Hugging Face at the
  pinned revision into the user-level cache (network needed the first time) and verified by the
  recorded SHA-256 in the manifest.

### 2026-09-21 — Phase 1 integrity checks (Phase 2 end)

- SHA-256 of all 24 `Docs/` files, `data/chunks/chunks.jsonl`, `data/manifests/documents.json` and
  `data/manifests/corpus_manifest.json` taken before the first Phase 2 build and again at the end:
  **identical** (27 files). `chunks.jsonl` is still `90d1e88e…fcbe16`, and every `Docs/` file still
  matches `file_hash` in `documents.json`.
- No `docs/` directory was created; `Docs/` still contains only `Synchronisation/` and `Threads/`.
- No Phase 1 code was changed, and no Phase 1 bug was found.
- A grep of `src/retrieval/` and the Phase 2 tests for LLM, generation, chat, UI, reranking and BM25
  code finds only docstrings stating their absence and manifest labels.

### Phase 2 files

Created:

- `src/retrieval/__init__.py`, `embeddings.py`, `vector_store.py`, `indexer.py`, `retriever.py`,
  `search.py`
- `tests/test_retrieval.py`, `tests/retrieval_smoke_queries.json`
- Generated: `data/vector_store/qdrant/` (Qdrant local storage), `data/vector_store/index_manifest.json`

Modified:

- `requirements.txt`: appended the pinned Phase 2 section (`numpy==2.5.3`, `onnxruntime==1.30.0`,
  `tokenizers==0.23.2`, `huggingface_hub==1.31.0`, `qdrant-client==1.19.0`). The Phase 1 lines are
  unchanged and still minimum-version.
- `CLAUDE.md`: added the Phase 2 commands.
- `PROJECT_LOG.md`: this section, plus the updated phase table in Project Overview.

### Deviations from the Phase 2 instructions

- The index manifest is `data/vector_store/index_manifest.json`, not `data/manifests/index_manifest.json`
  (reason in Architecture: the Phase 1 pipeline wipes `data/manifests/`).
- The smoke set lives in `tests/retrieval_smoke_queries.json` and runs as a parametrised pytest test;
  there is no separate smoke CLI.
- Filters with `None`/null values are rejected (`ValueError`) rather than translated into
  "is null" queries. This keeps filters to exact values from Phase 1 metadata.
- Extra CLI options beyond the example: `--filter`, `--max-chars`, `--json`, `--store`,
  `--manifest`, `--chunks`.

### Phase 2 Known Limitations

1. The model's usable input limit is 2,048 tokens (its trained context), not the advertised 8,192.
   All current chunks fit (max 1,045). A future longer chunk would be refused with an error, never
   truncated.
2. Qdrant local mode allows one open client per store directory (a file lock) and uses brute-force
   search. That is fine at this corpus size; a Qdrant server would be needed for concurrent access or
   much larger corpora.
3. Embedding runs on the CPU only (about 3 minutes for 463 chunks on the M3). Accelerators were not
   used, to keep results deterministic.
4. The baseline embeds only the chunk text. OSTEP continuation chunks whose heading is only in
   `section` metadata get no heading context. The effect is unmeasured.
5. The smoke tests rely on Phase 1 keyword labels and terms. They detect broken retrieval but say
   nothing about retrieval quality. No relevance-judged evaluation exists yet (Phase 5).
6. Filters are exact, case-sensitive matches on Phase 1 values, with no null filtering. Filter values
   inherit the Phase 1 metadata uncertainties (VIT from the filename, 4 unknown sources, SUMSEM
   module).
7. Duplicate and near-duplicate content is indexed and can occupy several top-k slots. The retrieval
   policy is deferred.
8. Image-only pages/slides (28, from Phase 1) have no text and cannot be retrieved.
9. Vector reproducibility is verified on this machine and runtime only.

### Phase 2 Final Status

**COMPLETE** (2026-09-21).

- Chunks read 463, embeddings 463, vectors indexed 463, failures 0.
- Collection `os_tutor_chunks__nomic_embed_text_v1_5`, dim 768, Cosine, Qdrant local mode in
  `data/vector_store/qdrant/`.
- 44/44 tests pass. Phase 1 artifacts are unchanged.

Commands:

```bash
python3 -m src.retrieval.indexer              # build (refuses to overwrite)
python3 -m src.retrieval.indexer --recreate   # explicit rebuild
python3 -m src.retrieval.search --query "How does Peterson's solution provide mutual exclusion?" --top-k 5
python3 -m pytest tests -q
```

## Phase 3 — Advanced Retrieval / Reranking

**STATUS: NOT STARTED.** Requires explicit approval. Candidate topics already noted:

- reranking, hybrid BM25, and query rewriting (all excluded from Phase 2);
- contextual embeddings (`section` + text);
- duplicate handling in top-k;
- down-weighting reference-list chunks;
- comparing additional embedding models (add a `ModelSpec`; the index name is per model).

## Phase 4 — RAG Generation

**STATUS: NOT STARTED.**

## Phase 5 — Evaluation / Research Experiments

**STATUS: NOT STARTED.** A relevance-judged retrieval evaluation set will be needed. The Phase 2
smoke set is not one.

---

## Phase 3A — Retrieval Evaluation Framework + Gold Query Set

**Status: COMPLETE** (started and completed 2026-09-21 on explicit instruction from the project owner; see Phase 3A Final Status)

Phase naming from the project owner at Phase 3A start: 3A = gold retrieval benchmark + baseline
evaluation; 3B = controlled retrieval experiments (NOT STARTED); 4 = RAG generation (NOT STARTED).
Phase 1 and Phase 2 are frozen, and nothing in them may change during 3A: code, chunks, metadata,
embedding model, collection, retrieval algorithm.

### 2026-09-21 — Phase 3A start

- Read `CLAUDE.md` and this log. There is no conflict with the Phase 3A instructions.
- The Phase 2 API used by the evaluator is `Retriever.open()` → `Retriever.search(query, top_k,
  filters)`. No retrieval logic is duplicated.
- Frozen-artifact snapshot taken before any Phase 3A work: SHA-256 of 31 files (`Docs/` 24,
  `data/vector_store/` 4 including the Qdrant storage files and the index manifest, `chunks.jsonl`,
  `documents.json`, `corpus_manifest.json`). It is compared again at the end of the phase.
- Annotation plan, fixed before any evaluation run:
  1. Read the whole chunk corpus (463 chunks, document by document).
  2. Write the queries and graded judgments from the chunk text.
  3. Freeze the benchmark file and record its hash.
  4. Only then run the dense retriever.

  The judgments are never edited after seeing retrieval results. Incompleteness is measured instead
  (unjudged chunks in the top-k).

### 2026-09-21 — Benchmark design and annotation (frozen before any evaluation run)

**Reading.** All 463 chunks were read in full, document by document, from `chunks.jsonl`. Per-chunk
notes of what each chunk actually supports were kept as annotation working notes (outside the repo).

**Query design.**
- 104 queries were drafted. 5 were then dropped as narrow, redundant or single-chunk (signal delivery,
  semaphore initial-value rule, flag spinning vs CV, Peterson on modern hardware, thread libraries),
  leaving **99**.
- Queries are student-style questions and paraphrases, not document titles: for example "I pass &i
  from my for loop to pthread_create and the threads print the wrong numbers. Why?".
- Only topics present in the corpus are used.
- Fields: `query_id`, `query`, `topic`, `subtopic` (list), `difficulty`, `query_type`, and
  `relevant_chunks` [{`chunk_id`, `relevance`}].

**Relevance scale.**
- 2 = directly relevant: the chunk itself answers or substantially explains the query.
- 1 = somewhat relevant / background: partial, supporting or example material.
- Unlisted = 0.

Judgments use Phase 1 chunk IDs. Near-duplicate copies are judged on their own text, so both
`lecture15.pdf` and `Semaphore.ppt - Copy.pptx` chunks appear where relevant.

**Ground truth independence.**
- The dense retriever and the embedding model were never consulted while writing queries or
  judgments.
- A **keyword audit** (regex search over chunk text) then listed unjudged chunks containing each
  query's key terms. The 75 narrower queries had all their candidates reviewed (491). For the 24 broad
  queries, the section-title-matched candidates were reviewed.
- 52 queries received additions: 92 judgments, almost all grade 1, each decided by reading the chunk.
- Every grade-2 judgment was re-checked against its chunk's section title to catch off-by-one chunk
  indexing; none was found.

**Difficulty.**
- easy = direct concept or definition.
- medium = paraphrased, comparative or mechanism.
- hard = multi-concept, scenario, code or reasoning.

Difficulty is an analysis dimension, not a performance label.

**Frozen benchmark `data/evaluation/retrieval_queries.json` (version 1.0).**
- SHA-256 `370b7c3393079fe30ef9cff5402aa23a2762736b24227a6cde572e926f57abb1`.
- Tied to the corpus by `corpus.chunks_sha256` = `90d1e88e…fcbe16`. This is the deterministic
  `chunks.jsonl` hash; `corpus_manifest.json` contains a timestamp, so its hash is not a stable
  identity.

| Dimension | Distribution |
| --- | --- |
| Queries | 99 |
| Topic | Synchronisation 78, Threads 21 (the corpus is 17 Synchronisation documents vs 5 Threads documents) |
| Difficulty | easy 23, medium 48, hard 28 |
| Query type | conceptual 26, mechanism 16, algorithm 12, code 13, comparative 11, scenario 11, classical 10 |
| Judgments | 616 (grade 2: 322, grade 1: 294) |
| Relevant chunks per query | min 1, median 6, max 16 |
| Coverage | 357 distinct chunks, all 22 documents, 30 subtopic labels |

Rule from here on: v1.0 judgments are **not edited after seeing retrieval results**. Missing
judgments are measured as unjudged results in the top-k. Any corrections go into a new benchmark
version, logged with its reason.

### 2026-09-21 — Evaluator

New package `src/evaluation/`:

- `metrics.py`: pure functions for per-query metrics (definitions below). Implemented here and not
  taken from BEIR / pytrec_eval, because the formulas are short and this way they are visible and
  tested. No dependency was added.
- `retrieval_evaluator.py`: CLI `python3 -m src.evaluation.retrieval_evaluator [--benchmark]
  [--output-dir] [--name]`. It:
  1. validates the benchmark schema;
  2. refuses to run if the benchmark's corpus hash differs from the current `chunks.jsonl`;
  3. opens the frozen Phase 2 index through `Retriever.open()`;
  4. calls only `Retriever.search(query, top_k=10)` with no filters;
  5. computes metrics, macro-averages them overall and by topic / difficulty / query type;
  6. runs the analyses listed under Error analysis;
  7. writes `<name>_results.json` and `<name>_report.md`.
- The evaluator contains no retrieval logic, and nothing in Phases 1–2 was changed.

**Metric definitions** (relevant = grade ≥ 1, unjudged = 0; per query, then macro-averaged):
- Recall@K = |relevant ∩ top K| / |relevant|.
- Hit@K = 1 if any relevant chunk is in the top K. This is reported separately and is not recall.
- Precision@K = |relevant ∩ top K| / K.
- MRR@K = 1 / rank of the first relevant chunk within K.
- nDCG@K = DCG/IDCG with linear gains equal to the grades and a log2(rank + 1) discount (the
  trec_eval / BEIR convention).
- MAP@K = the sum of Precision@i at relevant ranks i ≤ K, divided by |relevant| (the trec_eval
  map_cut convention).
- Reported: Recall@1/3/5/10, Hit@1/3/5/10, Precision@5, MRR@5, MRR@10, nDCG@5, nDCG@10, MAP@5.

**Error analysis** (automatic heuristics, recorded per result and per query):
- Per non-relevant top-5 result: `reference_list`, `exercise_section`, `duplicate_result`,
  `neighboring_chunk` (±1 chunk from a relevant chunk in the same document),
  `topically_related_unjudged` (shares a Phase 1 subtopic label with the query), and
  `image_only_unit`.
- Per failed query (no relevant chunk in the top 5): `exact_terminology_miss` (an identifier from
  the query is absent from all top-5 texts), `relevant_near_image_only_unit`, or else
  `semantic_mismatch`. `metadata/filter issue` does not apply because the baseline uses no filters.
- Also measured: judgment coverage (unjudged results in the top-k), and duplicate content in the
  top-k (exact duplicate chunks and near-duplicate-document pairs).

### 2026-09-21 — Baseline results (Phase 2 dense retriever, unchanged)

Run: `python3 -m src.evaluation.retrieval_evaluator` (about 3 s once the model is cached).

Configuration:
- Benchmark v1.0 (SHA-256 `370b7c33…57abb1`).
- Corpus `90d1e88e…fcbe16`.
- `nomic-embed-text-v1.5` @ `e9b67630`, collection `os_tutor_chunks__nomic_embed_text_v1_5` (Cosine),
  vectors `1d65a777…71d99f`.
- top_k 10, no filters.

| Metric | Value |
| --- | --- |
| Recall@1 | 0.193 |
| Recall@3 | 0.405 |
| Recall@5 | 0.486 |
| Recall@10 | 0.647 |
| Precision@5 | 0.539 |
| MRR@5 | 0.904 |
| nDCG@5 | 0.682 |
| nDCG@10 | 0.708 |
| MAP@5 | 0.451 |
| Hit@1 / @3 / @5 / @10 | 0.869 / 0.950 / 0.970 / 0.980 |

Breakdowns (full tables in `data/evaluation/baseline_dense_report.md`):

- **Topic:** Threads nDCG@10 0.709, Synchronisation 0.708.
- **Difficulty (nDCG@10):** easy 0.765, medium 0.686, hard 0.699.
- **Difficulty (Precision@5):** easy 0.678, medium 0.546, hard 0.414.
- **Query type (nDCG@10):** conceptual 0.788, scenario 0.771, classical 0.733, comparative 0.716,
  algorithm 0.658, mechanism 0.622, code 0.621.
- **Failures:**
  - No relevant chunk in the top 5: 3 queries (q009, q020, q091).
  - No relevant chunk in the top 10: 2 queries (q009, q020).
  - All 3 are tagged `semantic_mismatch` by the heuristic; none were tagged `exact_terminology_miss`.
- **Judgment coverage:**
  - 2.30 of the top 5 and 6.17 of the top 10 results per query are unjudged (61.7% of all top-10
    results).
  - 178 of the 228 unjudged top-5 results share a subtopic label with their query.
  - Because unjudged counts as non-relevant, the Recall / Precision / nDCG values are lower bounds
    with respect to judgment completeness.
- **Duplicates:**
  - 0 queries with duplicate content in the top 5; 4 queries (q053, q059, q061, q064) in the top 10.
  - All 4 involve the `lecture15.pdf` / `Semaphore.ppt - Copy.pptx` pair: 2 exact-duplicate-chunk
    pairs and 2 near-duplicate-document pairs.
- **Tags on non-relevant top-5 results:** `topically_related_unjudged` 178, `neighboring_chunk` 34,
  `image_only_unit` 10, `reference_list` 2.

**Observed error patterns** (from reading the lowest-nDCG queries; evidence for Phase 3B, not fixed
here):

1. **General chunks outrank the specific answer.** q009 (`&i` passed to pthread_create) ranks general
   Thread API / pthread_create chunks above the Q&A answer (ps-concurrency Q20) and the lab note that
   explain the bug. q055, q057 and q060 rank semaphore definition chunks above the chunks about
   ordering, implementation or comparison.
2. **A keyword pulls in the wrong material.** q020 (parallelising a loop; "do the threads need
   locks?") returns OSTEP Locks-chapter chunks in the top 4. The relevant lab chunk (pthreads-sync
   Part A) is not in the top 10.
3. **Neighbouring / continuation chunks.** Adjacent chunks of relevant material rank high (34
   top-5 occurrences), e.g. "Correctness of the Software Solution" next to Peterson's slides.
   Continuation chunks without their heading compete with the chunk that carries it.
4. **Reference lists.** OSTEP chapter 26 References ranks #2 for the Peterson query (q087); there
   are 2 top-5 occurrences in total.
5. **Near-duplicate slides.** The lecture15 / Semaphore-copy pair shows up in top-10 lists (4
   queries), taking two slots for the same content.
6. **Image-only slides.** 10 top-5 results are slides flagged image-only. Their embedded text is the
   title plus little body.
7. **Hardest query types.** Code and mechanism queries have the lowest nDCG@10 (about 0.62) and
   code the lowest Precision@5 (0.339). Hard queries have the lowest Precision@5 (0.414), but the
   highest Recall@1 because their relevant sets are small.

### 2026-09-21 — Tests and reproducibility (Phase 3A)

- New `tests/test_evaluation.py` (13 tests):
  - benchmark schema valid; version 1.0; 60–100 queries;
  - benchmark tied to the current `chunks.jsonl` hash;
  - unique query IDs; every query has ≥ 1 grade-2 chunk; grades only 1/2; all chunk IDs exist;
  - both topics and all difficulties present;
  - the validator catches duplicate IDs, empty judgments, invalid grades and unknown chunks;
  - hand-computed checks of recall, precision (K denominator), hit, MRR, graded nDCG and MAP (full
    relevant set), plus empty inputs;
  - the evaluator on a 5-query subset against the real index: output schema, metrics in [0, 1],
    ranks 1–10, traceable chunk IDs;
  - determinism (two runs identical apart from `generated_at`);
  - refusal on a corpus-hash mismatch;
  - the saved baseline matches the frozen benchmark hash and query order.
- `python3 -m pytest tests -q`: **57 passed** (Phase 1: 15, Phase 2: 29, Phase 3A: 13). No existing
  Phase 1 or Phase 2 test was modified.
- **Determinism:** two full evaluator runs into scratch directories and the saved `data/evaluation`
  run are identical, including rankings, scores, metrics and analyses, apart from
  `run.generated_at`. The reports are identical apart from their timestamp line.
  - Deterministic: benchmark, query order, retrieval rankings and scores, metrics, analyses.
  - Runtime metadata: `run.generated_at`.
  - Inherited from Phase 2: bit-identical rankings are verified on this machine and runtime only.
- **Frozen-artifact check:** all 31 files hashed at Phase 3A start (`Docs/`, `data/vector_store/`
  including the Qdrant storage, `chunks.jsonl`, `documents.json`, `corpus_manifest.json`) are
  byte-identical at the end.

### Phase 3A files

Created:
- `src/evaluation/__init__.py`, `src/evaluation/metrics.py`, `src/evaluation/retrieval_evaluator.py`
- `tests/test_evaluation.py`
- Curated benchmark: `data/evaluation/retrieval_queries.json`. This is the source of truth, not
  generated data, and must not be regenerated. The Phase 1 pipeline does not touch
  `data/evaluation/`.
- Generated: `data/evaluation/baseline_dense_results.json`, `data/evaluation/baseline_dense_report.md`

Modified:
- `PROJECT_LOG.md` (this section and the phase table).
- `CLAUDE.md` (evaluator command).

Not modified: `requirements.txt` (no dependency added), all Phase 1 and Phase 2 code, data and tests.

### Phase 3A limitations

1. **Single annotator.** The queries and judgments were written by one annotator (Claude). There is
   no inter-annotator agreement measure. The project owner should review the judgments before they
   are used for publication-grade claims.
2. **Incomplete judgments.** 61.7% of top-10 results are unjudged. Metrics are lower bounds, and
   comparisons between retrievers can be biased toward systems that retrieve the judged chunks.
   Mitigation for Phase 3B: pooled judging of new systems' top-k results into a new benchmark
   version.
3. **Recall@K ceiling.** Recall@K depends on the size of each query's judged relevant set (1–16
   chunks, median 6, grade-1 background included). Small K has a low ceiling.
4. **Topic balance.** The topic split (78 Synchronisation / 21 Threads) follows corpus composition,
   so Threads breakdowns rest on 21 queries.
5. **Heuristic error tags.** They are indicators for inspection, not verified root causes.
6. **Image-only content.** Unretrievable content (Phase 1 image-only slides) could not be judged.
   Queries were written only where the text supports them.
7. **Benchmark authorship.** The benchmark was written by the same agent that built Phases 1–2;
   phrasing may unconsciously mirror corpus wording despite the paraphrasing intent.

### Deviations from the Phase 3A instructions

- The query count (99) is at the top of the requested 60–100 range.
- The benchmark uses `corpus.chunks_sha256` (the deterministic `chunks.jsonl` hash) instead of the
  suggested `corpus_manifest_hash`: `corpus_manifest.json` contains a timestamp and changes on every
  Phase 1 rebuild.
- Additions beyond the requested schema: `query_type`, and the benchmark-level relevance scale and
  annotation description.
- Extra metrics reported: Hit@1/3/5/10 and MRR@10. MAP@5 is implemented (it was optional).
- The query-level `metadata/filter issue` category is reported as not applicable (no filters are
  used in the baseline).

### Phase 3A Final Status

**COMPLETE** (2026-09-21).
- Benchmark v1.0 frozen: 99 queries, 616 judgments.
- Baseline measured and reproducible.
- 57/57 tests pass. Phase 1 and Phase 2 artifacts are unchanged.

## Phase 3B — Controlled Retrieval Experiments

**STATUS: NOT STARTED.** Requires explicit approval.

Candidates motivated by the Phase 3A evidence:
- hybrid BM25 + dense retrieval (general-over-specific drift, keyword pull);
- heading/section-aware embeddings (continuation chunks);
- reranking;
- handling of duplicates and reference lists in the top-k.

Each experiment should be run with this evaluator against benchmark v1.0. New systems' unjudged
top-k results should be pooled for judging into a benchmark v1.1 before strong claims are made.

---

## Phase 3B-0 — Expand and Freeze the Retrieval Evaluation Judgments (benchmark v1.1)

**Status: COMPLETE — v1.1 FROZEN** (started and completed 2026-09-21 on explicit instruction from the project owner; see Phase 3B-0 Final Status)

### 2026-09-21 — Why v1.1

At the end of Phase 3A, 61.7% of the baseline's top-10 results had no judgment. Metrics computed
against v1.0 are therefore lower bounds, and comparisons between future retrieval systems could be
distorted by which chunks happen to be judged. Before any retrieval experiment, the judgment pool is
widened by pooling and manual judging. The result is a new version, v1.1. v1.0 stays untouched.

Frozen at start of this phase:

- Docs/, data/vector_store/ (including the Qdrant storage), chunks.jsonl, documents.json and
  corpus_manifest.json.
- Benchmark v1.0 (retrieval_queries.json, SHA-256 370b7c33…57abb1).
- baseline_dense_results.json and baseline_dense_report.md.

A SHA-256 snapshot of these 34 files was taken before any work. It is compared again at the end.

Out of scope for this phase: no retrieval change, no BM25, hybrid search, RRF, MMR, reranking,
heading-aware embeddings, query expansion or generation.

### 2026-09-21 — Pooling

- Pool source: the frozen Phase 2 dense retriever, unchanged: `nomic-embed-text-v1.5` @ `e9b67630…`,
  collection `os_tutor_chunks__nomic_embed_text_v1_5`, vectors SHA-256 `1d65a777…`, no filters.
  Qdrant was only read.
- Depth: top 20 for every query. Top 30 for the three Phase 3A top-5 failures (q009, q020, q091), to
  look further for evidence they might have.
- Unjudged pairs in the pool (retrieved, not in the v1.0 judgments): **1,536**, covering 376
  distinct chunks. v1.0 left 228 of the top-5, 611 of the top-10 and 1,509 of the top-20 results
  unjudged.

### 2026-09-21 — Annotation method

- Review was rank-blind. The review sheet grouped candidates by chunk. No rank, score or retrieval
  order was shown.
- Every candidate was graded 0/1/2 on the v1.0 scale, by reading the chunk text against the query.
  The same single annotator (Claude) did this.
- Rule: a grade does not follow from embedding score, a shared topic or subtopic, or a shared document.
- Per-chunk content notes were written from a full reading of the text. For less obvious
  positives, the full text was read again before freezing: VT16, TC2, TB6, VT3, VT5, PC13, PC15,
  TC0, PC51, VS20, TC1, SU7, VP26, TC22, PC32, SU37, TB16, SU24, SU48, PC52, PC25, PC29, TL22, VP15,
  L131, TB9 and VC9. All support grade 1.
- Result: 141 candidates graded 1. 0 graded 2: no pooled chunk answers a query better than, or as
  directly as, the v1.0 grade-2 set. The other 1,395 candidates were graded 0.
- Grade-0 judgments are stored explicitly in each query's `nonrelevant_chunks` (`added_in: "1.1"`).
  This separates "read, not relevant" from "never judged".
- Categories that needed special care:
  - Reference lists (17) and homework/question sections (23): all graded 0.
  - Chunks adjacent to a v1.0 relevant chunk: 39 of 190 graded 1. Adjacency alone was not enough.
  - Chunks from the same document as a v1.0 relevant chunk: 104 of 724 graded 1.
  - Chunks sharing a query subtopic: 122 of 1,063 graded 1.
  - Duplicate chunks: lecture15 and "Semaphore - Copy" carry the same grade in every query where
    either is judged. An automatic check found no disagreement between the exact-duplicate and
    near-duplicate pairs.
  - General pthread API chunks retrieved for specific bug or mechanism questions were graded 0
    unless they carry the asked-for explanation.
  - Semaphore definitions retrieved for ordering or implementation questions were graded 0 unless
    they carry the asked-for explanation.
- Phase 3A failures:
  - **q009** (the `&i` argument race): none of its top-30 candidates explains the bug. No new
    positive. It remains a top-10 failure.
  - **q020** (splitting a CPU-heavy loop across 10 threads, and whether disjoint writes need
    locks): all pooled candidates are lock-chapter or unrelated chunks, graded 0. It remains a
    top-10 failure.
  - **q091** (atomic swap for mutual exclusion): two background chunks graded 1:
    - TL10: OSTEP test-and-set, described as "atomic exchange" / x86 `xchg`.
    - SU24: "swap the contents of two words atomically" and building mutual exclusion on a boolean
      lock. This is the same content as VS13, which v1.0 already grades 1.
    - These grades were set rank-blind. SU24 sits at baseline rank 3, so q091 now has a relevant
      chunk in the top 5. It is a grade-1 background chunk.
    - q091's grade-2 chunks still rank 9, 11 and 15. The underlying retrieval weakness is unchanged.

### 2026-09-21 — Benchmark v1.1 built and frozen

- `data/evaluation/retrieval_queries_v1.1.json`, SHA-256
  `bfbbd033021a154f969d284483b73416c4c7b9b3f1afc126b1609dd650bd5986`.
- Header:
  - `version` "1.1", `parent_version` "1.0", `parent` {path, sha256 `370b7c33…57abb1`}.
  - `corpus` copied from v1.0 (chunks.jsonl SHA-256 `90d1e88e…cbe16`, 463 chunks).
  - `relevance_scale`: grades 2 and 1 verbatim from v1.0; the text for grade 0 now defines
    `nonrelevant_chunks`.
  - `annotation` {"1.0": verbatim v1.0 text, "1.1": this method}.
  - `pooling` block: retriever identity, depth, deep-pool queries, method, limitation.
- Per query:
  - Every v1.0 field is unchanged: wording, topic, subtopic, difficulty and query_type.
  - `relevant_chunks`: each v1.0 entry is carried unchanged, with provenance `added_in: "1.0"`. New
    entries have `added_in: "1.1"`. Sorted by (-relevance, chunk_id), as in v1.0.
  - `nonrelevant_chunks`: grade-0 entries, sorted by chunk_id.
- Serialisation is the same as v1.0: `json.dumps(indent=2, ensure_ascii=False)` plus a trailing newline.
- The build is deterministic: two builds gave the same SHA-256. The build script is session tooling
  and is not part of the project. The frozen file is the source of truth and must not be
  regenerated.

**Counts**

| | v1.0 | v1.1 |
| --- | --- | --- |
| Queries | 99 | 99 (unchanged) |
| Relevant judgments (grade 2 / grade 1) | 616 (322 / 294) | 757 (322 / 435) |
| New relevant judgments | — | 141 (all grade 1) |
| Explicit grade-0 judgments | 0 | 1,395 |
| All judgments | 616 | 2,152 |
| Distinct chunks judged relevant | 357 | 372 |
| Distinct chunks judged at any grade | 357 | 417 |
| Relevant chunks per query (min / median / max) | 1 / 6 / 16 | 1 / 8 / 18 |
| Unjudged baseline results, top 5 / top 10 / top 20 | 228 / 611 / 1,509 | 0 / 0 / 0 |
| Unjudged baseline results, top 30 (q009, q020, q091) | — | 0 |

- 68 queries gained at least one relevant chunk. 31 gained none.
- Baseline rank bands of the new positives: 1–5: 29, 6–10: 45, 11–20: 67.

**Per-topic coverage**

| Topic | Queries | v1.0 judgments | New grade 1 | New grade 0 | Queries with new positives | Top-10 unjudged, v1.0 → v1.1 |
| --- | --- | --- | --- | --- | --- | --- |
| Threads | 21 | 115 | 26 | 321 | 15 | 138/210 (65.7%) → 0 |
| Synchronisation | 78 | 501 | 115 | 1,074 | 53 | 473/780 (60.6%) → 0 |

### 2026-09-21 — Evaluator support for v1.1 (backward compatible)

`src/evaluation/retrieval_evaluator.py` changes:
- `validate_benchmark` also validates the optional `nonrelevant_chunks`: known chunk IDs, grade
  exactly 0, no duplicates, and no overlap with `relevant_chunks`.
- A retrieved chunk found in `nonrelevant_chunks` gets `relevance: 0` instead of `null`. `null`
  still means unjudged, so the unjudged counts now exclude judged-0 chunks.
- The top-5 non-relevant count uses `not relevance`, so it covers both unjudged and grade 0. The
  report label says so.
- When a benchmark has grade-0 judgments, the report adds their count.
- Metrics code is unchanged. Grade 0 already contributes nothing to any metric.

Backward compatibility was verified. A fresh v1.0 run into a scratch directory gives a results JSON
identical to the saved `baseline_dense_results.json`, apart from `generated_at`. The report differs
only in its timestamp and the reworded label. The value is still 228. The frozen v1.0 outputs were
not regenerated.

### 2026-09-21 — Frozen baseline re-scored against v1.1

`python3 -m src.evaluation.retrieval_evaluator --benchmark data/evaluation/retrieval_queries_v1.1.json --name baseline_dense_v1.1`
wrote `data/evaluation/baseline_dense_v1.1_{results.json,report.md}`.

The retriever, index, rankings and scores are identical to the v1.0 run: all 99 × 10 (chunk_id,
score) pairs were checked. Every difference below comes from judgment expansion, not from a system
change.

| Metric | v1.0 | v1.1 |
| --- | --- | --- |
| Recall@1 | 0.193 | 0.160 |
| Recall@3 | 0.405 | 0.346 |
| Recall@5 | 0.486 | 0.436 |
| Recall@10 | 0.647 | 0.625 |
| Precision@5 | 0.539 | 0.598 |
| MRR@5 | 0.904 | 0.914 |
| nDCG@5 | 0.682 | 0.695 |
| nDCG@10 | 0.708 | 0.706 |
| MAP@5 | 0.451 | 0.404 |
| Hit@5 | 0.970 | 0.980 |
| Hit@10 | 0.980 | 0.980 |

- **Precision rises.** The newly judged top-10 chunks include relevant ones.
- **Recall and MAP fall.** Relevant sets grew by chunks the baseline ranks mostly at 11–20, so the
  denominator grew faster than the top-K hits.
- **nDCG changes little.** All new positives are grade 1.
- **Failures.** Top-5 failures: q009, q020, q091 → q009, q020 (q091 as explained above). Top-10
  failures: q009, q020 in both versions.
- **Pooling bias.** Every new judgment comes from this dense system's own top 20. For any future
  system, its results outside this pool are still unjudged. The v1.1 numbers are therefore biased
  toward the pooled baseline. Future systems should report their unjudged top-k count, which is 0
  for the baseline.

### 2026-09-21 — Proposed corrections for v1.2

**None.** No v1.0 judgment looked incorrect during the v1.1 review, and none was changed. The review
was not a systematic re-audit of v1.0: pooled candidates were compared against the v1.0 set, and the
duplicate-consistency check found no conflict. Corrections found later belong in v1.2, recorded here
first.

### 2026-09-21 — Tests and validation (Phase 3B-0)

- New `tests/test_benchmark_v11.py` (8 tests):
  - v1.0 immutability: SHA-256 equals `370b7c33…57abb1`; chunks.jsonl hash unchanged.
  - v1.1 header: version, parent version, parent SHA-256, corpus block equal to v1.0 and matching
    the chunks.jsonl hash, v1.0 annotation kept verbatim, pooling depth.
  - v1.1 passes `validate_benchmark`.
  - v1.0 → v1.1 preservation: same query IDs and order, every non-judgment field identical, and the
    `added_in: "1.0"` entries equal to the v1.0 `relevant_chunks` exactly, including order.
  - Judgment validity: unique query IDs, known chunk IDs, no duplicate or overlapping judgments,
    grades 1/2 relevant and 0 non-relevant, valid provenance, and no new grade 2.
  - Canonical, deterministic serialisation: re-serialising the file reproduces its bytes; lists are
    sorted.
  - The validator catches a wrong grade in `nonrelevant_chunks`, an overlap with a relevant chunk,
    and an unknown chunk.
  - The v1.1 baseline run references the v1.1 hash, has the same retriever configuration and
    rankings as the v1.0 run, and its top 10 is fully judged.
- `python3 -m pytest tests -q`: **65 passed** (Phase 1: 15, Phase 2: 29, Phase 3A: 13, Phase 3B-0:
  8). No existing test was modified.
- **Frozen-artifact check:** the 34 files hashed at phase start are byte-identical at the end.
  These are `Docs/`, `data/vector_store/` including Qdrant, chunks.jsonl, documents.json,
  corpus_manifest.json, retrieval_queries.json v1.0, and the v1.0 baseline results and report.
- No `docs/` directory was created. `Docs/` is the only entry at the root.

### Phase 3B-0 files

Created:
- `data/evaluation/retrieval_queries_v1.1.json`. Curated and frozen; the source of truth.
- `data/evaluation/baseline_dense_v1.1_results.json`, `data/evaluation/baseline_dense_v1.1_report.md`.
  Generated.
- `tests/test_benchmark_v11.py`

Modified:
- `src/evaluation/retrieval_evaluator.py`: grade-0 support, backward compatible.
- `PROJECT_LOG.md`: this section, the phase table and the status line.
- `CLAUDE.md`: note on v1.1.

Not modified: `Docs/`, all Phase 1 and Phase 2 code, data and index, `retrieval_queries.json`
v1.0, the v1.0 baseline outputs, `src/evaluation/metrics.py`, existing tests, `requirements.txt`.

### Phase 3B-0 limitations

1. **Single annotator.** The same agent wrote v1.0 and v1.1. There is no agreement measure.
2. **Dense-only pooling bias.** The pool comes from one system. Chunks outside every pooled top 20
   stay unjudged, and new systems will surface such chunks. Pool their unjudged top-k into v1.2
   before making strong comparative claims.
3. **Grade-0 judgments are pool-specific.** An explicit 0 says the chunk was read and judged
   not relevant for that query. It says nothing about chunks that were never pooled.
4. **Recall is not comparable across versions.** v1.1 relevant sets are larger. Compare systems
   only within one benchmark version.
5. **Judging basis.** Judgments rest on per-chunk content notes written from the full text. Less
   obvious positives were re-read in full before freezing, but not every grade-0 decision was.

### Phase 3B-0 Final Status

**PHASE 3B-0 = COMPLETE / EVALUATION v1.1 = FROZEN / RETRIEVAL SYSTEM = UNCHANGED** (2026-09-21).
- v1.1: 99 queries, 757 relevant judgments (616 carried + 141 new grade 1), and 1,395 explicit
  grade-0 judgments. The baseline's top 20 (top 30 for q009, q020, q091) is fully judged.
- No retrieval change was made. No BM25, hybrid search, RRF, MMR, reranking, query expansion or
  generation. Qdrant was not modified.
- Phase 3B experiments: NOT STARTED. They need explicit approval.

---

## Phase 3B — Experiment E1: BM25 Lexical Retrieval Baseline

**Status: COMPLETE** (started and completed 2026-09-21 on explicit instruction from the project owner; see E1 Final Status)

E1 builds a pure BM25 lexical retriever over the same 463 frozen chunks and evaluates it on benchmark v1.1.
It is compared with the frozen dense baseline. The two systems share the corpus, queries, judgments and
metric definitions.

Out of scope for E1: hybrid retrieval, reranking, MMR/diversity, the tutor, and changes to the embedding
model, corpus or benchmark. E2 needs explicit approval.

### 2026-09-21 — E1 start: checks before any change

- Read this log in full and `CLAUDE.md`, and inspected `src/retrieval/`, `src/evaluation/`, `tests/`,
  benchmark v1.1 and `chunks.jsonl`.
  - The evaluator's `evaluate()` only needs an object with `search(query, top_k)` returning the dense
    result shape.
  - `run()` opens the dense `Retriever` directly and records dense-only configuration. This is the part
    to refactor.
- Frozen hashes match the values recorded in this log:
  - `chunks.jsonl` SHA-256 `90d1e88e…fcbe16`, which equals `corpus.chunks_sha256` in v1.1.
  - `retrieval_queries_v1.1.json` SHA-256 `bfbbd033…bd5986`. Its `parent.sha256` equals the v1.0 hash.
- Frozen-artifact snapshot: 47 files.
  - `Docs/`, `data/vector_store/` (Qdrant and the manifest), `chunks.jsonl`, `documents.json` and
    `corpus_manifest.json`.
  - Benchmarks v1.0 and v1.1, and the v1.0 and v1.1 dense outputs.
  - The dense retrieval code: `embeddings.py`, `vector_store.py`, `indexer.py`, `retriever.py`,
    `search.py`.
  - All existing test files.

  The 34 files of the Phase 3B-0 end snapshot are unchanged.
- The dense baseline is unchanged. Re-running
  `python3 -m src.evaluation.retrieval_evaluator --benchmark data/evaluation/retrieval_queries_v1.1.json`
  into a scratch directory reproduces `baseline_dense_v1.1_results.json` exactly, apart from
  `generated_at`.
- Test suite before any change: `python3 -m pytest tests -q` gives **65 passed** (Phase 1: 15, Phase 2: 29,
  Phase 3A: 13, Phase 3B-0: 8).

### 2026-09-21 — E1 design: BM25 retriever

`src/retrieval/bm25.py`, class `BM25Retriever`. It has the same interface and result shape as the dense
`Retriever`: `open()`, `search(query, top_k)`, context manager.

**Dependencies.** None added; `requirements.txt` is unchanged. Okapi BM25 is about 20 lines of stdlib
code. As with `metrics.py`, writing it in the project keeps the formula visible and tested, and avoids a
dependency such as `rank_bm25` with its own IDF handling.

**Scoring.**
- `score(q, d) = Σ over query tokens t of idf(t) · tf(t, d) · (k1 + 1) / (tf(t, d) + k1 · (1 − b + b · |d| / avgdl))`.
  A repeated query token counts again.
- `idf(t) = ln(1 + (N − df + 0.5) / (df + 0.5))`: Lucene's BM25 idf, which is never negative.
- `k1 = 1.2`, `b = 0.75`: the standard defaults. They were fixed before the first run and **not tuned on the
  benchmark**; tuning on the test queries would leak the judgments into the system.

**Tokenization.**
- Lowercase, then the regex `[a-z0-9]+(?:_[a-z0-9]+)*`, so identifiers such as `pthread_create` and
  `sem_wait` stay one token.
- No stemming and no stopword list, as instructed to keep normalization simple.
- No query expansion or rewriting, embeddings, reranking or hybrid scoring.

**Index.**
- Built in memory on `open()` from `chunks.jsonl` through the Phase 2 `load_chunks` (which validates
  `text_hash`). Takes 23 ms.
- 463 chunks, vocabulary 4,408 tokens, average length 149.19 tokens.
- Chunk text is only tokenized, never altered. Nothing is written to disk.
- Results carry the canonical text, `text_verified`, and the same provenance payload as the dense
  index, via the Phase 2 `build_payload`. The evaluator's error analysis therefore works unchanged.

**Ranking.**
- Sorted by the unrounded score, descending. Ties are broken by corpus order (`chunks.jsonl` line order).
- Scores are stored rounded to 6 decimals, as in the dense results.
- Only chunks sharing a token with the query are returned. Every benchmark query matches at least 301
  chunks, so every top-30 list is full.

### 2026-09-21 — E1 evaluator changes (minimal, backward compatible)

- `retrieval_evaluator.run()` takes:
  - `retriever="dense" | "bm25"`. The dense configuration block is built exactly as before.
  - `top_k`.
  - `deep_k`: the benchmark's `pooling.deep_pool` queries (q009, q020, q091) are also retrieved to this
    depth. The extra results go to `retrieved_deep`, for inspection only; they never enter metrics or
    counts.

  The CLI gained `--retriever`, `--top-k` and `--deep-k`.
- Changes in `evaluate()`:
  - Top-10 counts use `retrieved[:10]`.
  - `unjudged_in_top20` is recorded for depth-20 runs.
  - The report title and retriever line follow the retriever type.
- `metrics.all_metrics(ranked, qrels, depth=10)`: runs with depth ≥ 20 also get Precision@10 and Hit@20.
  - No metric definition changed. The module docstring with the definitions is untouched, and
    Precision@K / Hit@K were already defined for any K.
  - Depth-10 runs keep the Phase 3A metric set.
- **Backward compatibility, verified.** Default dense runs on v1.0 and v1.1, written to a scratch
  directory, reproduce the frozen `baseline_dense_results.json` and `baseline_dense_v1.1_results.json`
  exactly, apart from `generated_at`. The v1.1 report is identical apart from its timestamp. The v1.0
  report differs only by the label reworded in Phase 3B-0.
- New `src/evaluation/compare.py` writes a side-by-side report of two runs.
  - It refuses runs that differ in benchmark hash, corpus hash, metric definitions, depth or query set.
  - It reports numbers only and declares no winner.

### 2026-09-21 — E1 runs

```bash
python3 -m src.evaluation.retrieval_evaluator --retriever bm25 --top-k 20 --deep-k 30 \
    --benchmark data/evaluation/retrieval_queries_v1.1.json --output-dir data/evaluation/e1_bm25 --name bm25_v1.1
python3 -m src.evaluation.retrieval_evaluator --retriever dense --top-k 20 --deep-k 30 \
    --benchmark data/evaluation/retrieval_queries_v1.1.json --output-dir data/evaluation/e1_bm25 --name dense_v1.1_top20
python3 -m src.evaluation.compare data/evaluation/e1_bm25/dense_v1.1_top20_results.json \
    data/evaluation/e1_bm25/bm25_v1.1_results.json --output data/evaluation/e1_bm25/comparison.md
```

- **Dense at depth 20.** The frozen dense v1.1 output stops at top 10, so Hit@20 cannot be computed
  from it. The unchanged dense retriever was run again at depth 20 into `e1_bm25/`; the frozen output was
  not overwritten.
  - Its top 10 is identical to `baseline_dense_v1.1_results.json`: ranks, chunk IDs, scores, grades and
    tags.
  - Every metric the two share is equal.
- **Controls.** Both systems use the same 99 queries, the same 463 chunks (`90d1e88e…`), the same v1.1
  judgments (`bfbbd033…`), the same metric code and the same depth. No filters.

| Metric | Dense v1.1 | BM25 E1 | Difference |
| --- | --- | --- | --- |
| Precision@5 | 0.598 | 0.517 | −0.081 |
| Precision@10 | 0.458 | 0.378 | −0.080 |
| Recall@5 | 0.436 | 0.401 | −0.036 |
| Recall@10 | 0.624 | 0.543 | −0.082 |
| MRR@5 | 0.914 | 0.852 | −0.062 |
| nDCG@5 | 0.695 | 0.629 | −0.066 |
| nDCG@10 | 0.706 | 0.631 | −0.075 |
| MAP@5 | 0.404 | 0.361 | −0.043 |

| Queries with a relevant result in the top K (of 99) | Dense v1.1 | BM25 E1 | Difference |
| --- | --- | --- | --- |
| top 1 | 87 | 79 | −8 |
| top 3 | 95 | 89 | −6 |
| top 5 | 97 | 92 | −5 |
| top 10 | 97 | 96 | −1 |
| top 20 | 99 | 99 | 0 |

(The dense Recall@10 here is 0.624 because it is averaged from unrounded per-query values; the frozen
report shows 0.625. The per-query values are identical.)

- **Per query:** BM25 nDCG@10 is higher on 33 queries, equal on 6 and lower on 60.
- **Breakdowns** are in `e1_bm25/comparison.md`. Selected nDCG@10 values, dense → BM25:
  - Topic: Threads 0.702 → 0.681, Synchronisation 0.707 → 0.617.
  - Difficulty: easy 0.767 → 0.618, medium 0.690 → 0.613, hard 0.683 → 0.671.
  - Query type: conceptual 0.779 → 0.608, comparative 0.725 → 0.608, mechanism 0.631 → 0.517, code
    0.611 → 0.628, scenario 0.748 → 0.791, algorithm 0.656 → 0.633, classical 0.755 → 0.722.
- **Failures:**
  - Top 5, dense: q009, q020. Top 5, BM25: q002, q008, q046, q055, q059, q060, q081.
  - Top 10, dense: q009, q020. Top 10, BM25: q008, q046, q060.
  - Top 20: none for either system.
- **Overlap:**
  - Mean shared chunks per query: 4.17 of the top 10, 8.18 of the top 20.
  - Judged-relevant chunks in the top 20: dense only 176, BM25 only 48, both 436.

**Judgment coverage: the main caveat.** v1.1 was pooled from the dense top 20, so all unjudged results
fall on BM25.

| Unjudged results | Dense v1.1 | BM25 E1 |
| --- | --- | --- |
| top 5 | 0 (0.0%) | 152 of 495 (30.7%) |
| top 10 | 0 (0.0%) | 418 of 990 (42.2%) |
| top 20 | 0 (0.0%) | 1,118 of 1,980 (56.5%) |

- Only 7 queries have a fully judged BM25 top 10, which is too few for a judged-only comparison.
- Unjudged counts as non-relevant, so every BM25 number above is a lower bound. The differences mix
  retrieval behaviour with judgment coverage. The "BM25 only 48" overlap count is deflated for the same
  reason.
- The size of the gap cannot be read as a quality difference until BM25's unjudged results are judged.
  That would mean pooling them into a v1.2 benchmark, which needs approval.

### 2026-09-21 — E1 error analysis (from retrieved chunks and v1.1 judgments)

**q009** (code, hard) "I pass &i from my for loop to pthread_create … wrong numbers. Why?"

| | Dense | BM25 |
| --- | --- | --- |
| pthreads-sync c0003 (grade 2) | beyond rank 30 | 1 |
| ps-concurrency c0019 (grade 2) | 19 | 2 |
| threads-api c0018 (grade 1) | beyond rank 30 | 26 |
| threads-api c0003 (grade 1) | beyond rank 30 | beyond rank 30 |

- Dense ranks 1–18 are general thread-API and thread-intro chunks, all judged 0.
- Term overlap: ps-concurrency c0019 contains the query tokens `i`, `loop`, `pthread_create`, `threads`
  and `print`; pthreads-sync c0003 contains `i`, `pass`, `threads` and `print`.
- **BM25 recovered the missed grade-2 chunks and improved the ranking.** Its top 10 also holds different
  material from dense:
  - 5 unjudged chunks: pthreads-sync Part A and Part B, a Traffic-Intersection lab problem, an OSTEP
    chapter-26 "Questions" chunk (another one is at rank 11) and a condition-variable chunk.
  - 3 chunks judged 0.

**q020** (scenario, hard) "speed up a CPU-heavy loop … 10 threads … need locks …?"

| | Dense | BM25 |
| --- | --- | --- |
| pthreads-sync c0006 (grade 2) | 21 | 1 |
| threads-intro c0003 (grade 1) | 16 | 4 |
| pthreads-sync c0005 (grade 1) | 24 | 8 |
| pthreads-sync c0007 (grade 1) | beyond rank 30 | beyond rank 30 |
| threads c0003 (grade 1) | beyond rank 30 | beyond rank 30 |

- Dense ranks 1–15 are Locks-chapter and similar chunks, all judged 0.
- pthreads-sync c0006 shares 18 of the query's distinct tokens, including `speed`, `across`, `10`,
  `different`, `each` and `array`.
- **BM25 recovered the grade-2 chunk and improved the ranking.** Part of the "locks" pull remains:
  threads-locks c0016 and c0023 are in its top 10, judged 0.
- It adds OSTEP "Questions" chunks. "28 Locks > Questions" at rank 2 (judged 0) shares 16 query tokens,
  mostly question words (`how`, `would`, `you`, `if`, `each`) plus `cpu` and `loop`. A condition-variable
  "Questions" chunk is at rank 5 (unjudged).

**q091** (algorithm, medium) "How can the atomic swap instruction be used to implement mutual exclusion?"

| | Dense | BM25 |
| --- | --- | --- |
| SUMSEM c0024 (grade 1) | 3 | 1 |
| ps-concurrency c0023 (grade 2) | 9 | 5 |
| VIT 3f6ce962 c0019 "Solution using Swap" (grade 2) | 15 | beyond rank 30 |
| VIT 975bc607 c0017 "Solution using swap" (grade 2) | 11 | beyond rank 30 |
| threads-locks c0010 (grade 1) | 18 | beyond rank 30 |

- **Mixed result.** BM25 puts a grade-2 chunk in the top 5, which dense does not. But it drops the two
  grade-2 code slides out of its top 30.
- Those slides are short (35 and 27 tokens). They contain only `swap` and `to` of the query's tokens: the
  mutual exclusion is expressed in code (`lock`, `key`, critical section), not in the query's words.
- Both systems rank threads-bugs c0014 (OSTEP deadlock prevention, "Mutual Exclusion", judged 0) at
  rank 1 or 2. It contains 9 of the query's tokens.
- A BM25-only distractor: a VIT "Objectives" slide at rank 4 (unjudged), which contains `how`, `can`,
  `atomic`, `swap`, `used` and `to`.

**Result categories.** Counts are over all queries' top 10. The split is relevant / judged 0 / unjudged;
top-5 counts are in the comparison file.

| Category | Dense top 10 | BM25 top 10 |
| --- | --- | --- |
| Reference lists | 7 (0 / 7 / 0) | 12 (0 / 3 / 9) |
| OSTEP homework / "Questions" sections | 7 (0 / 7 / 0) | 73 (0 / 8 / 65) |
| ps-concurrency practice problems | 123 (51 / 72 / 0) | 103 (38 / 22 / 43) |

- **Reference lists.** Top 5: dense 2, BM25 5. None is judged relevant in either system.
- **Homework / "Questions" sections.** This is the largest category shift. Top 5: dense 0, BM25 34.
  - The questions share question words with student-style queries. With no stopword list those words
    still score: for example `idf(how) = 1.76`.
  - Every one of these chunks that has been judged is grade 0. The other 65 are unjudged.
- **Practice problems.** Top 5: dense 63, BM25 54.
- **lecture15 / Semaphore-copy.** Both documents appear in the top 10 of 4 queries for dense (q053, q059,
  q061, q064) and 7 for BM25 (q053, q059, q063, q064, q066, q082, q096). In BM25's top 10 these chunks
  total 16: 8 relevant, 8 unjudged.
  - The exact-duplicate pair `lecture15::c0001` / `semaphore-ppt-copy::c0001` has identical text. BM25
    therefore scores the two identically, and they sit on adjacent ranks in all 6 BM25 top-10 lists
    containing both.
- **Code queries** (13): nDCG@10 0.611 → 0.628, Precision@5 0.415 → 0.492, MRR@5 0.821 → 0.885.
  - Large gains: q009 (0.000 → 0.778), q057 (0.307 → 0.613), q073 (0.431 → 0.823).
  - Large losses: q008 (0.714 → 0.000) and q070 (0.847 → 0.539).
  - q008's grade-2 threads-api chunks (c0006, c0007) are beyond rank 20 for BM25. Its top 10 has 7
    unjudged results: deadlock prevention, fetch-and-add, queue locks and similar.
- **Classical queries** (10): nDCG@10 0.755 → 0.722, Precision@5 0.740 → 0.720.
  - BM25 has a relevant chunk at rank ≤ 2 for all 10. Dense does for 9; its first relevant chunk for
    q065 is at rank 4.
  - q065 rises (0.197 → 0.402). q099 falls (1.000 → 0.631), with 8 unjudged results in BM25's top 10.
- **BM25-only top-10 failures** (q008, q046, q060). Their BM25 top 10s contain 7, 9 and 9 unjudged
  results, so these failures are partly a coverage effect.
  - q046: the grade-2 chunks rank 19 and beyond 20. The top 10 is led by a semaphore chunk and OSTEP
    "Questions" chunks.
  - q060: the top two results are the OSTEP "Semaphores: A Definition" chunks (unjudged). The VIT
    grade-2 chunks rank 16 and beyond 20.

### 2026-09-21 — E1 reproducibility

- The BM25 evaluation was run twice: into `data/evaluation/e1_bm25/` and into a scratch directory.
  - Rankings and scores are identical for all 99 queries, including the top-30 deep lists.
  - The results JSON is identical apart from `run.generated_at`, and so is its serialisation with that
    field fixed. The report is identical apart from its timestamp line.
- Floating-point determinism: BM25 uses Python float arithmetic in a fixed order (query-token order,
  then postings in corpus order), with no parallelism or randomness.
  - It is bit-identical for the same interpreter and platform.
  - On other platforms `math.log` may differ in the last bit. Stored scores are rounded to 6 decimals,
    and ranking uses the unrounded value with a corpus-order tie-break.

### 2026-09-21 — E1 tests and validation

- New `tests/test_bm25.py` (13 tests):
  - v1.1 and `chunks.jsonl` hashes unchanged.
  - The tokenizer.
  - BM25 scores equal a hand computation on a toy corpus.
  - Ties follow corpus order, and only matching chunks are returned.
  - The index covers exactly the 463 frozen chunks, with text unaltered and lengths correct.
  - Results are ranked, have positive descending scores, and are traceable: text, `text_verified`,
    and payload equal to `build_payload`.
  - Top-k: lengths 1/5/20/30, the top 20 is a prefix of the top 30, and invalid `top_k` or query is
    rejected.
  - Repeated retrieval over all 99 queries at top 30 is deterministic.
  - The default metric set is unchanged; depth 20 adds P@10 and Hit@20.
  - Evaluator compatibility: a BM25 run on v1.1 has ranks 1–20, the new metrics, and deep lists only
    for q009, q020 and q091.
  - Two BM25 evaluations are identical.
  - Saved E1 runs match the frozen inputs, and the dense depth-20 top 10 equals the frozen dense v1.1
    output.
  - The comparison refuses runs on different benchmarks.
- `python3 -m pytest tests -q`: **78 passed**.
  - Phase 1: 15, Phase 2: 29, Phase 3A: 13, Phase 3B-0: 8, E1: 13.
  - No existing test was modified or removed.
- **Frozen-artifact check:** the 47 files hashed at E1 start are byte-identical at the end. These
  include `Docs/`, the Qdrant index, `chunks.jsonl`, both benchmarks, the v1.0 and v1.1 dense outputs,
  the dense retrieval code and all existing tests.
- No `docs/` directory was created.

### E1 files

Created:
- `src/retrieval/bm25.py`
- `src/evaluation/compare.py`
- `tests/test_bm25.py`
- `data/evaluation/e1_bm25/`: `bm25_v1.1_{results.json,report.md}`, `dense_v1.1_top20_{results.json,report.md}`
  and `comparison.md`. All generated.

Modified:
- `src/evaluation/retrieval_evaluator.py`: retriever choice, depth and deep-pool options.
- `src/evaluation/metrics.py`: `depth` argument adding P@10 and Hit@20.
- `PROJECT_LOG.md` and `CLAUDE.md`.

Not modified: `Docs/`, `chunks.jsonl`, both benchmarks, the Qdrant index, the dense retriever code, the
frozen dense outputs, existing tests, `requirements.txt`.

### E1 limitations

1. **Pooling bias.** v1.1 has no judgments for 42.2% of BM25's top-10 results, against 0% for dense. The
   comparison therefore understates BM25 by an unknown amount.
2. **One configuration.** k1 = 1.2, b = 0.75, with no stemming and no stopwords. Morphological variants
   such as `lock` / `locks` do not match. Other settings were not explored; tuning them on this benchmark
   would overfit it.
3. **Chunk text only.** As with dense, no section or heading text is indexed.
4. **Single annotator.** The v1.1 judgments come from one annotator (see Phase 3B-0).
5. **Truncated instructions.** The E1 instructions arrived cut off after "Run the FULL test". The full
   suite was run. Any later instructions were not received.

### E1 Final Status

**E1 COMPLETE** (2026-09-21): BM25 lexical baseline implemented, evaluated on v1.1, and compared with
the frozen dense baseline. No winner is declared.
- Retrieval system unchanged: the dense retriever, index, corpus and benchmarks are untouched.
- Not implemented: hybrid retrieval, RRF, reranking, MMR, query expansion, generation.
- Next steps need explicit approval: **E2**, and optionally pooling BM25's unjudged results into a v1.2
  benchmark.

---

## Phase 3B — Experiment E2: Dense + BM25 Hybrid (RRF), and Review 2 Preparation

**Status: COMPLETE** (2026-10-04). This was started on explicit instruction from the project owner, with three
goals:

- bring the project to a demonstrable Review 2 state;
- run E2 as one controlled hybrid experiment;
- build the tutor architecture and the pre/post assessment framework.

Reranking, MMR, v1.2 judgments, an LLM backend and a frontend were explicitly out of scope.

Project root, located by a filesystem search for `retrieval_queries_v1.1.json` / `PROJECT_LOG.md`:
`/Users/aayushjaiswal/Desktop/Projects/OS-RAG`.

### 2026-10-04 — Start: checks before any change

- Read this log in full and `CLAUDE.md`, and inspected `src/`, `tests/` and `data/evaluation/`.
- **E1 already existed and was complete.** It was not rebuilt. It was validated instead:
  - its saved results reproduce exactly (see Tests);
  - its 13 tests pass.
- **Environment change found.** `python3` on PATH now resolves to `/opt/miniconda3/bin/python3`, which has no
  pytest or project dependencies. All commands in this session used `/usr/local/bin/python3` (3.13.7), the
  interpreter recorded in the Reproducibility Baseline. Nothing was installed.
- **Test suite before any change:** `/usr/local/bin/python3 -m pytest tests -q` gives **78 passed**.
- **Frozen snapshot.** 71 files were hashed before any change: `Docs/`, `data/vector_store/` including Qdrant,
  `data/chunks/`, `data/manifests/`, `data/evaluation/` (both benchmarks, all dense outputs, all E1 outputs),
  `src/`, `tests/`, `CLAUDE.md` and `requirements.txt`.
- **Frozen hashes match the values recorded earlier:**
  - `chunks.jsonl` `90d1e88e…fcbe16`
  - `retrieval_queries_v1.1.json` `bfbbd033…bd5986`
  - Docs/ corpus digest `1df92ddc…0520f9` (22 files)
  - index vectors `1d65a777…71d99f`

### 2026-10-04 — E2 design (fixed before the first run)

`src/retrieval/hybrid.py` defines `HybridRRFRetriever`. It has the same `search(query, top_k)` interface and
result shape as the other two retrievers.

- **Composition.** It wraps the unchanged dense `Retriever` and the unchanged E1 `BM25Retriever`. Neither
  class was modified.
- **Fusion.** Reciprocal Rank Fusion: `rrf(d) = Σ over {dense, bm25} of 1 / (k + rank_s(d))`, over each
  system's top `candidate_k`.
  - k = 60, from Cormack, Clarke & Büttcher (SIGIR 2009).
  - candidate_k = 50 per system.
  - Equal weights.
  - These values were chosen before any E2 run and **not tuned on the benchmark**.
- **Why RRF.** It uses ranks only, so it needs no calibration between cosine and BM25 scores.
- **Ties** follow corpus order, as in BM25.
- **Result format.** Each result is the component result (canonical text, `text_verified`, payload) with
  three changes: `rank` is replaced, `score` is replaced by the RRF value, and `component_ranks`
  `{dense, bm25}` is added.
- **Excluded:** reranking, MMR, score normalisation, query rewriting, LLMs.
- **Dependencies:** none added; `requirements.txt` is unchanged.

Evaluator changes, minimal and backward compatible:

- `retrieval_evaluator.run(retriever="hybrid")` builds the dense configuration exactly as before and wraps it.
- The CLI accepts `--retriever hybrid`.
- Per-result `component_ranks` are copied into the results JSON only when the retriever provides them. Dense
  and BM25 outputs are therefore byte-identical in content.
- The report title and retriever line follow the retriever type.

`src/evaluation/compare.py` gained a supplementary "judged-only (condensed-list)" section. It computes
P@5, nDCG@10 and MAP@5 after dropping unjudged results from each top-20 list. It uses the unchanged metric
functions; no metric definition changed.

### 2026-10-04 — E2 runs

```bash
/usr/local/bin/python3 -m src.evaluation.retrieval_evaluator --retriever hybrid --top-k 20 --deep-k 30 \
    --benchmark data/evaluation/retrieval_queries_v1.1.json --output-dir data/evaluation/e2_hybrid --name hybrid_rrf_v1.1
/usr/local/bin/python3 -m src.evaluation.compare data/evaluation/e1_bm25/dense_v1.1_top20_results.json \
    data/evaluation/e2_hybrid/hybrid_rrf_v1.1_results.json --names "Dense v1.1" "Hybrid E2" \
    --output data/evaluation/e2_hybrid/comparison_dense_vs_hybrid.md
/usr/local/bin/python3 -m src.evaluation.compare data/evaluation/e1_bm25/bm25_v1.1_results.json \
    data/evaluation/e2_hybrid/hybrid_rrf_v1.1_results.json --names "BM25 E1" "Hybrid E2" \
    --output data/evaluation/e2_hybrid/comparison_bm25_vs_hybrid.md
/usr/local/bin/python3 -m src.evaluation.compare data/evaluation/e1_bm25/dense_v1.1_top20_results.json \
    data/evaluation/e1_bm25/bm25_v1.1_results.json --output data/evaluation/e2_hybrid/comparison_dense_vs_bm25.md
```

The last command regenerates the E1 comparison with the new judged-only section, written into `e2_hybrid/`.
`e1_bm25/comparison.md` was not touched.

| Metric | Dense v1.1 | BM25 E1 | Hybrid E2 |
| --- | --- | --- | --- |
| Precision@5 | 0.598 | 0.517 | 0.632 |
| Precision@10 | 0.458 | 0.378 | 0.470 |
| Recall@5 | 0.436 | 0.401 | 0.471 |
| Recall@10 | 0.624 | 0.543 | 0.645 |
| MRR@5 | 0.914 | 0.852 | 0.921 |
| nDCG@5 | 0.695 | 0.629 | 0.725 |
| nDCG@10 | 0.706 | 0.631 | 0.727 |
| MAP@5 | 0.404 | 0.361 | 0.433 |
| Hit queries top 1 / 3 / 5 / 10 / 20 (of 99) | 87 / 95 / 97 / 97 / 99 | 79 / 89 / 92 / 96 / 99 | 86 / 97 / 98 / 99 / 99 |
| Unjudged top 5 / 10 / 20 | 0 / 0 / 0 | 152 / 418 / 1,118 | 11 / 108 / 667 |
| Judged-only P@5 / nDCG@10 / MAP@5 | 0.598 / 0.706 / 0.404 | 0.659 / 0.731 / 0.453 | 0.646 / 0.751 / 0.439 |

**Failures.**

| | Top 5 | Top 10 |
| --- | --- | --- |
| Hybrid | q008 | none |
| Dense | q009, q020 | q009, q020 |

**Per-query nDCG@10 and exact two-sided sign tests.** Session analysis computed from the saved per-query
metrics. Counts are second system higher / lower / equal.

| Comparison | Higher / lower / equal | p |
| --- | --- | --- |
| Hybrid vs dense | 58 / 32 / 9 | 0.008 |
| Hybrid vs BM25 | 77 / 16 / 6 | < 0.0001 |
| BM25 vs dense | 33 / 60 / 6 | 0.007 |

Hybrid vs dense on other metrics: P@5 32 / 17 / 50 (p 0.044), MAP@5 42 / 26 / 31 (p 0.068).

**Reading.**

- Hybrid scores higher than dense on every headline metric, even though it carries the pooling penalty:
  108 unjudged top-10 results against 0 for dense.
- BM25 alone scores lower than dense on the main metrics but higher on the judged-only view. The
  dense-vs-BM25 ordering therefore stays unresolved (see E1 limitations).
- The judged-only view favours the system with the most unjudged results, so it is supplementary only.

### 2026-10-04 — E2 error analysis

Ranks are dense / BM25 / hybrid; the source is the deep-pool lists and `component_ranks`.

**q009 (the `&i` argument race).**

| Chunk | Grade | Dense | BM25 | Hybrid |
| --- | --- | --- | --- | --- |
| ps-concurrency c0019 | 2 | 19 | 2 | 3 |
| pthreads-sync c0003 | 2 | >30 | 1 | 11 |
| threads-api c0018 | 1 | >30 | 26 | 17 |

- nDCG@10: dense 0.000, BM25 0.778, hybrid 0.239.
- BM25 recovers both grade-2 chunks. Hybrid recovers one into the top 5.
- Dense fails partly at candidate generation (one grade-2 chunk is beyond its top 30) and partly at ranking
  (the other is at rank 19).
- Hybrid ranks 1–2 are threads-intro c0010 and c0009, judged 0.

**q020 (CPU-heavy loop across 10 threads).**

| Chunk | Grade | Dense | BM25 | Hybrid |
| --- | --- | --- | --- | --- |
| pthreads-sync c0006 | 2 | 21 | 1 | 6 |
| threads-intro c0003 | 1 | 16 | 4 | 5 |
| pthreads-sync c0005 | 1 | 24 | 8 | 9 |

- nDCG@10: dense 0.000, BM25 0.695, hybrid 0.355.
- The dense failure is ranking: all three chunks are dense candidates.
- Hybrid fixes the top-10 failure. Its ranks 1–4 are still Locks-chapter or practice-problem chunks,
  judged 0.

**q091 (atomic swap for mutual exclusion).**

| Chunk | Grade | Dense | BM25 | Hybrid |
| --- | --- | --- | --- | --- |
| ps-concurrency c0023 | 2 | 9 | 5 | 5 |
| SUMSEM c0024 | 1 | 3 | 1 | 2 |
| VIT "Solution using swap" 975bc607 c0017 | 2 | 11 | >30 | >30 |
| VIT "Solution using Swap" 3f6ce962 c0019 | 2 | 15 | >30 | >30 |

- nDCG@10: dense 0.173, BM25 0.278, hybrid 0.265.
- Hybrid gains a grade-2 chunk in the top 5 but loses the two short code slides.
- Rank 1 in all three systems is threads-bugs c0014 (judged 0).
- This is a ranking problem; every relevant chunk is a dense candidate.

**Groups (nDCG@10, dense / BM25 / hybrid).**

| Group | Queries | Dense | BM25 | Hybrid |
| --- | --- | --- | --- | --- |
| code | 13 | 0.611 | 0.628 | 0.634 |
| mechanism | 16 | 0.631 | 0.517 | 0.653 |
| classical | 10 | 0.755 | 0.722 | 0.815 |
| conceptual | 26 | 0.779 | 0.608 | 0.747 |
| Semaphores subtopic | 16 | 0.694 | 0.548 | 0.702 |
| Thread-API subtopics (Pthreads / Thread Creation / Thread Join) | 9 | 0.551 | 0.660 | 0.641 |
| Condition Variables | 19 | 0.687 | 0.569 | 0.703 |

**Distractors.**

- Homework/"Questions" chunks in the top 10: dense 7, hybrid 19.
- Reference-list chunks in the top 10: dense 7, hybrid 11.
- Every one of these chunks that has been judged is grade 0.

**Largest hybrid losses vs dense.** q092, q008, q059, q046 and q027. BM25's own nDCG@10 on each is ≤ 0.13.

**Hybrid top-10 slot origin** (990 slots):

| Chunk was in the top 10 of | Slots |
| --- | --- |
| both systems | 413 |
| dense only | 224 |
| BM25 only | 199 |
| neither | 154 |

### 2026-10-04 — Tutor controller (Review 2 prototype; PARTIAL)

`src/tutor/controller.py`:

- **`TutorController(retriever, llm, top_k=5, max_rounds=2)`.** A state machine:
  - DIAGNOSE: a probing question, explicitly not the answer.
  - ANALYSE: the LLM returns JSON with `level` and `gap`.
  - solid → CHECK. Otherwise → EXPLAIN: the targeted gap, an example or counterexample, and a check question.
  - After a check: solid → DONE. Otherwise EXPLAIN again, at most `max_rounds` times, then ANSWER → DONE.
- **Grounding.** Each prompt carries the retrieved chunks as [S1]…[Sn], with filename, page or slide, and
  section. Every `Turn` returns the sources (chunk_id, filename, location, section).
- **Malformed analysis replies** are treated as `unclear`, which leads to an explanation.
- **No LLM backend.** `llm` is an injected `callable(prompt) -> str`. Choosing and connecting a model is
  Phase 4 and was not approved. No LLM dependency was added.
- **CLI demo:** `python3 -m src.tutor.controller "<question>"`. It prints the grounded DIAGNOSE prompt using the
  E2 hybrid retriever. That retriever choice is provisional.

### 2026-10-04 — Pre/post assessment framework (no participant data)

- `data/assessment/learning_objectives.json` (DRAFT): LO1–LO8 and their corpus subtopic labels.
  - LO1 threads fundamentals, LO2 thread APIs, LO3 race conditions, LO4 locks/mutexes.
  - LO5 semaphores, LO6 condition variables, LO7 classical problems, LO8 concurrency bugs.
- `data/assessment/question_bank_draft.json` (DRAFT, UNVALIDATED). 16 items written by Claude: one pre and
  one post parallel item per objective.
  - Each item records topic, objective, difficulty estimate, question type, expected concept, max score,
    answer key or rubric, and grounding chunk IDs.
  - The grounding chunks are taken from v1.1 grade-2 judgments of matching queries. They were spot-checked
    and are verified to exist by a test.
  - The bank has not been reviewed by the instructor, piloted, or calibrated.
  - `data/assessment/` is outside the ingestion pipeline's regenerated subdirectories, so a rebuild does not
    delete it.
- `src/assessment/learning_gain.py`. Per participant, per condition and per objective it computes:
  - score %;
  - absolute gain;
  - Hake normalized gain g, which is None at pre = 100;
  - class ⟨g⟩ and the mean of individual g.

  CLI: `python3 -m src.assessment.learning_gain responses.json`. It was tested on synthetic inputs only.
  **No participant results exist.**

### 2026-10-04 — Review 2 report

`REVIEW2_REPORT.md` (project root; not `docs/`) has sections A–K:

- A architecture, B corpus, C retrieval protocol;
- D–F Dense / BM25 / Hybrid results;
- G error analysis;
- H tutor status;
- I assessment method;
- J limitations, K future work.

Each component carries a status label: implemented, partial or planned.

### 2026-10-04 — Tests, reproducibility and frozen artifacts

**New tests.**

- `tests/test_hybrid.py` (7 tests):
  - frozen hashes;
  - RRF scores, component ranks and tie order on a toy;
  - the candidate-depth limit;
  - bad `top_k` rejected, and the dense client closed;
  - real hybrid results: traceable, top-20 a prefix of top-30, deterministic;
  - the saved E2 run equals a fresh run, apart from the timestamp and the benchmark path string;
  - the comparison's judged-only section, and condensed equals standard for the fully judged dense run.
- `tests/test_tutor_assessment.py` (8 tests):
  - diagnose-first prompt with grounding and provenance;
  - gap → explain → check → done;
  - solid → check;
  - bounded rounds → full answer;
  - malformed analysis handling;
  - item bank well formed and grounded in existing chunks;
  - gain formulas;
  - synthetic analysis with input validation.

**Full suite.** `/usr/local/bin/python3 -m pytest tests -q` gives **93 passed**, 0 failed (78 before + 15
new). No existing test was modified or removed.

**Reproducibility.**

- The E2 evaluation was run twice: into `e2_hybrid/` and into a scratch directory.
  - The results JSON is identical apart from `run.generated_at`, including its serialisation.
  - The report is identical apart from its timestamp line.
- **Evaluator backward compatibility.** After the evaluator edits, fresh runs reproduce the saved outputs
  exactly, apart from `generated_at`:
  - the default dense v1.1 run reproduces `baseline_dense_v1.1_results.json`, and its report matches apart
    from the timestamp;
  - the BM25 E1 run reproduces `e1_bm25/bm25_v1.1_results.json`;
  - the dense depth-20 run reproduces `e1_bm25/dense_v1.1_top20_results.json`.

**Frozen artifacts.** The 71-file snapshot was compared at the end.

- Every pre-existing file is byte-identical except the two intentionally edited source files,
  `src/evaluation/retrieval_evaluator.py` and `src/evaluation/compare.py`.
- Unchanged: `Docs/`, `chunks.jsonl`, both benchmarks, the Qdrant index and its manifest, all dense outputs,
  all E1 outputs, the dense retriever code, `bm25.py`, `metrics.py` and all existing tests.
- No `docs/` directory was created.

### E2 / Review 2 files

**Created:**

- `src/retrieval/hybrid.py`
- `src/tutor/__init__.py`, `src/tutor/controller.py`
- `src/assessment/__init__.py`, `src/assessment/learning_gain.py`
- `tests/test_hybrid.py`, `tests/test_tutor_assessment.py`
- `data/evaluation/e2_hybrid/`, all generated:
  - `hybrid_rrf_v1.1_{results.json,report.md}`
  - `comparison_dense_vs_hybrid.md`, `comparison_bm25_vs_hybrid.md`, `comparison_dense_vs_bm25.md`
- `data/assessment/learning_objectives.json`, `data/assessment/question_bank_draft.json` (drafts)
- `REVIEW2_REPORT.md`

**Modified:**

- `src/evaluation/retrieval_evaluator.py`: the hybrid option, and `component_ranks` passthrough.
- `src/evaluation/compare.py`: the judged-only section.
- `PROJECT_LOG.md`: the phase table and this section.
- `CLAUDE.md`

**Dependencies added:** none.

### E2 / Review 2 limitations

1. **Pooling bias.** v1.1 has 108 unjudged hybrid top-10 results and 418 for BM25. Their metrics are lower
   bounds, and the dense-vs-BM25 ordering is unresolved. A v1.2 judgment round is the prerequisite for
   stronger retrieval claims.
2. **One configuration.** E2 used one fusion configuration and no tuning. The sign tests use lower-bound
   metrics, and no correction for multiple comparisons was applied.
3. **BM25 distractors.** BM25 brings homework/"Questions" sections and reference lists into the hybrid top 10.
   Hybrid is below dense on 32 queries.
4. **Tutor not yet a working conversation.** No LLM is connected, and the prompts have not been tried on a
   model. Its pedagogy and faithfulness are unevaluated.
5. **Draft item bank and single annotator.** The item bank is unvalidated. The same agent wrote the judgments
   and the items, with no agreement measure.
6. **No student data.** The learning-gain code has only run on synthetic test inputs.

### E2 / Review 2 Final Status

**E2 COMPLETE; REVIEW 2 PREPARATION COMPLETE** (2026-10-04).

- The hybrid RRF retriever was implemented, evaluated on frozen v1.1, and compared with dense and BM25.
- The tutor controller is a PARTIAL prototype: logic, grounding and provenance are done; there is no LLM.
- The pre/post framework exists, with a draft item bank and no data.
- Frozen corpus, benchmarks, index and baselines are unchanged.
- Next steps need explicit approval:
  - (1) v1.2 pooled judgments of the BM25/hybrid unjudged results;
  - (2) Phase 4 LLM integration for the tutor;
  - (3) instructor validation and piloting of the item bank.

### 2026-10-04 — Review 2 submission document (Word)

- Created `Review2_OS-Tutor-RAG.docx` at the project root (not `docs/`). It is the Review 2 case-study
  submission.
- Its structure follows the instructor's requested sections:
  1. Introduction
  2. Literature review
  3. Objective
  4. Dataset collection
  5. Dataset processing
  6. Model architecture design
  7. Conclusion
  It adds a cover page in the Review 1 format and a reference list.
- It reuses the Review 1 objectives with a per-objective status.
- All numbers are taken from `REVIEW2_REPORT.md` and this log. It contains three figures (architecture,
  tutor flow, metrics chart), rendered from SVG by session tooling.
- The document states that no LLM is connected and that no student data exists.
- Validated with the docx skill's XSD validator: PASSED.
- No project code, data or frozen artifact was touched.

---

## Phase 4 (started) — Local LLM, Student Chat Page, Tutor Quality Evaluation

**Status: IN PROGRESS** (2026-10-04). Started on explicit instruction from the project owner, who asked for a
1-week finish. The approved scope is three items: local Ollama models for the demonstration, a student chat page,
and a check of the tutor's answer quality.

- **Ollama.** Version 0.32.7. The machine is an Apple M3 with 16 GB of memory.
  - Installed models: `qwen3:8b` and `llama3.1:8b`.
  - Measured speed: about 17 tokens/s, so roughly 10 s per tutor turn.
- **New `src/tutor/llm.py`: `OllamaLLM`.**
  - Standard library only: it calls Ollama's HTTP API with `urllib`.
  - Settings: temperature 0, seed 42, `think` turned off, `num_ctx` 8192.
  - It supports JSON mode and streaming.
- **`src/tutor/controller.py` changes.**
  - A new `emit(kind, data)` callback reports `sources`, `analysis` and `token` events as they happen.
  - The analysis call uses JSON mode.
  - New WRAP_UP stage: after a correct answer to a check, the tutor writes a short wrap-up before DONE.
  - A shared STYLE instruction: speak to the student, at most 120 words, never mention the context.
  - Clearer analysis levels.
  - Prompts were tuned on ONE dev question only ("Why do we need a thread pool?", q017). The tuning made two
    changes:
    - EXPLAIN must say when the student is wrong and must end with a check question.
    - DIAGNOSE must not hint at the answer.
- **New `src/tutor/server.py`.**
  - A standard-library threaded web server: `/usr/local/bin/python3 -m src.tutor.server`, then open
    http://localhost:8000.
  - It streams server-sent events.
  - It logs every turn to `data/tutor_logs/<date>.jsonl`.
  - The page lets the user choose the model.
- **New `web/index.html`.**
  - A single-file chat page.
  - A live state track (Diagnose / Explain / Check / Done) shows where the dialogue is.
  - Citation chips open the matching source card.
  - A toggle shows the tutor's analysis of each answer, for the teacher.
  - It has a dark mode and a mobile layout.
  - It was checked in the browser: a full DIAGNOSE → EXPLAIN dialogue with `qwen3:8b` works.
- **Quality evaluation.**
  - `data/evaluation/tutor_scenarios_v1.json` was frozen before any run. It holds 8 benchmark questions, one per
    learning objective, each with 3 scripted student profiles: solid, misconception and unsure.
  - The runner and checks are in `src/evaluation/tutor_eval.py`:
    - `run --model` writes the transcripts;
    - `report <models>` writes the automatic checks, plus manual rubric grades when they exist.
  - Runs for `qwen3:8b` and `llama3.1:8b` were started in the background. Their output goes to
    `data/evaluation/tutor_eval/`.
- **Early observations from dev and smoke tests**, not evaluation results:
  - `qwen3:8b` once agreed with a wrong student claim before the EXPLAIN prompt was fixed.
  - `llama3.1:8b` once left out the check question.
  - In the browser test, an explanation cited no source and missed the key idea (the lock is released atomically
    while the thread sleeps).
- **Tests.** 94 passed. `tests/test_tutor_assessment.py` was updated:
  - its stub accepts the new keyword arguments;
  - the wrap-up turn is now expected;
  - a new test covers streaming events.
- **Still to do:**
  - generate `report` once both runs finish;
  - grade the transcripts by hand with the rubric (`manual_grades_<model>.json`);
  - choose the demo model;
  - add server tests;
  - update `REVIEW2_REPORT.md` / `CLAUDE.md`.

### 2026-10-05 — Phase 4: tutor quality evaluation results, server tests, case study document

**Evaluation runs.** Both runs completed:

- `data/evaluation/tutor_eval/qwen3_8b_transcripts.json`
- `data/evaluation/tutor_eval/llama3.1_8b_transcripts.json`

The report was generated with `/usr/local/bin/python3 -m src.evaluation.tutor_eval report qwen3:8b llama3.1:8b` and
written to `data/evaluation/tutor_eval/report.md`.

**Automatic checks.**

| Check | qwen3:8b | llama3.1:8b |
| --- | --- | --- |
| Expected path followed | 21/24 | 19/24 |
| Analysis: exact level | 39/48 | 34/46 |
| Analysis: solid / not-solid | 52/56 | 46/54 |
| Valid JSON | 56/56 | 54/54 |
| DIAGNOSE asks one question | 24/24 | 12/24 |
| EXPLAIN ends with a question | 28/28 | 20/21 |
| Cites a source (EXPLAIN / WRAP_UP / ANSWER) | 16/49 | 41/43 |
| Citations valid | 80/80 | 78/78 |
| Within 120 words | 78/80 | 60/78 |
| Grade-2 chunk in the context | 24/24 | 24/24 |
| Median seconds per tutor turn | 8.9 | 11.7 |

**Manual rubric.** One annotator (Claude) graded all 158 turns on a 0–2 scale, with a note on every deduction.
Files: `manual_grades_qwen3_8b.json` and `manual_grades_llama3.1_8b.json`.

| Criterion | qwen3:8b | llama3.1:8b |
| --- | --- | --- |
| Correct (mean) | 1.76 | 1.51 |
| Grounded (mean) | 1.94 | 1.77 |
| Pedagogy (mean) | 1.39 | 1.26 |
| Turns with a factual error | 18/80 | 30/78 |
| Turns fully wrong | 1 | 8 |

**Decision: `qwen3:8b` stays the demo default.**

**Weaknesses found.**
- The tutor agrees with wrong answers ("You're right that…").
- `qwen3` often leaves out citations.
- A correct answer labelled "partial" sends the dialogue off its expected path. This explains all 3 of qwen's
  path failures.
- For q047, the explanations cover spurious wakeups only.
- DIAGNOSE questions are weak: they restate the student's question or hint at the answer.

**Prompts.** No prompt was changed after the evaluation.

**New tests.** `tests/test_server.py` (2 tests) uses a fake retriever and a scripted model:
- the page is served;
- the SSE stream for start and reply has the right shape;
- turn logging works;
- errors arrive in the stream.

Full suite: **96 passed**.

**Frozen inputs.** Hashes are unchanged: `chunks.jsonl` `90d1e88e…`, v1.1 `bfbbd033…`.

**Case study document.** Created `OS-Tutor-RAG_Case_Study.docx` at the project root, using the instructor's
7 sections. It includes every Phase 4 result and a screenshot of the chat page. It passed the docx XSD validator.
`Review2_OS-Tutor-RAG.docx` was kept unchanged. The generator script is session tooling and is not part of the
project.

**Operational notes.**
- Ollama was not running on 2026-10-05. It was started with `ollama serve`.
- The chat page needs Ollama running.
- The tutor server and the evaluation runner cannot run at the same time, because the local Qdrant index allows
  one process at a time.

**Phase 4 status.** LLM integration, chat page and quality evaluation are COMPLETE.

**Still to do:**
- prompt fixes for the weaknesses above, then a re-run of the 24 dialogues;
- instructor review of the item bank;
- a pilot;
- the pre/post study.

### 2026-10-05 — Version control and GitHub

- The project was not a git repository until now. On the owner's instruction it was initialised with git (branch
  `main`) and pushed to a new **public** repository: https://github.com/Aayush010307/OS-Tutor-RAG
- On the owner's explicit choice, `Docs/` is included. It is third-party course material; the README notes that
  rights belong to the original authors.
- `.gitignore` excludes:
  - caches and `.DS_Store`;
  - `.claude/`;
  - the Qdrant `.lock` file;
  - `data/tutor_logs/`, because chat transcripts may contain student answers.
- Added `README.md`, covering what the project is, its results, how to run it and the corpus note.
- Initial commit: `5f1342c`, 167 files.
