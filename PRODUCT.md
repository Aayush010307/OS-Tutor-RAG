# Product

<!-- impeccable:product-schema 1 -->
<!-- Reconciled 2026-10-10 from the owner's local PRODUCT.md (approved frontend direction) and the PR #1 version.
     Originals preserved in OS-RAG-backups/2026-10-10-pr1-integration/ (PRODUCT.local.md, PRODUCT.pr1.md). -->

## Platform

web

## Stack

React + TypeScript + Vite + Tailwind CSS, Lucide icons (`frontend/`). `npm run dev` serves the source with an `/api`
proxy to the Python tutor server (`src/tutor/server.py`, the backend of record), so the browser talks to one origin and no
CORS is needed. The production build currently goes to `frontend/dist`; wiring it into the `web/index.html` that the
server serves at `/` is still to do. The Python backend (retrieval, tutor controller, Ollama client) is not part of the
frontend work.

## Users

- Primary: undergraduate students of BCSE303P Operating Systems (VIT) studying threads and synchronization, usually
  alone on a laptop, in sessions that can run long (revision before labs and exams).
- Secondary: course staff and reviewers (professor demonstration, project reviews, viva) and the evaluator who turns on
  the tutor's analysis view during the pilot to see how the tutor judged each student answer. They judge in the first
  minute whether the tool teaches rather than answers, and whether its answers are grounded in the course material.

## Product Purpose

OS-Tutor teaches the idea behind a student's question instead of handing over the answer. By default (Socratic mode) it
asks what the student already knows (DIAGNOSE), judges the reply (solid, partial, misconception, unclear), explains only
the missing or wrong idea (EXPLAIN, at most two rounds), checks understanding (CHECK) and wraps up (DONE). Success is a
student who can explain and apply the concept, an evaluator who can see why the tutor took each step, and every
explanation traceable to a lecture slide or textbook page.

An optional answer-first mode exists on the backend (`TUTOR_MODE=answer_first`): a grounded answer first, then an
optional comprehension check. It has not been evaluated and the frontend does not support it yet.

## Positioning

A curriculum-grounded Socratic tutor: every explanation comes from the course's own slides, lecture notes and textbook
chapters (`Docs/`, 22 documents), retrieved by hybrid search (dense + BM25, reciprocal rank fusion), cited as [S1],
[S2], ... and the citations are validated against what the retriever actually returned. The teaching flow is a
deterministic state machine (diagnose, explain, check, done), not a model's whim, and a new question asked mid-lesson is
routed by rule to a side answer that keeps the tutor's pending question open. A general chatbot can answer; it cannot
show which slide of this course each sentence came from.

## Operating Context

- Runs fully locally: Python tutor server (port 8000) plus Ollama (default `qwen3:8b`; `llama3.1:8b` optional,
  evaluated as a comparison). The Ollama server may run on another machine (`OLLAMA_BASE_URL`). Replies stream over
  server-sent events and take seconds on a laptop.
- Tutor sessions live in server memory and are lost on restart. There is no account system. The backend also keeps a
  learner model and saved conversations on disk (git-ignored, they hold the student's own words); the frontend does not
  use them yet.
- Every finished turn is logged to `data/tutor_logs/` for the pilot and quality review.

## Capabilities and Constraints

- The authoritative API is `API_CONTRACT.md` (v2, additive over v1, owned by the backend). The frontend uses the v1
  subset: `GET /api/models`, `POST /api/start {question, model}`, `POST /api/reply {session_id, text}`; streamed
  events `session`, `sources`, `analysis`, `token`, `turn`, `error`. No cancel endpoint. v2 adds a health check, intent
  buttons, learner profile, Smart Revision, conversation history and source lookup; the UI shows them only once it uses
  them and they respond.
- Stages a student sees (Socratic mode): DIAGNOSE, EXPLAIN (at most 2 rounds), CHECK, DONE; a new question asked
  mid-lesson is answered on the side (stage `ANSWER`) and the tutor's pending question stays pending.
- Analysis (level `solid | partial | misconception | unclear` and a one-sentence gap) is for the evaluator view.
- Source metadata available: ref (S1..S5), document label, location (page or slide, never guessed), section, filename,
  topic and subtopics, preview and passage text. No retrieval scores; nothing may be invented.
- Not supported by the backend: topic filtering, stopping generation server-side, accounts.
- Scope of the corpus: threads and synchronization (pthreads, mutexes, semaphores, condition variables, race
  conditions, deadlock, classic problems, concurrency bugs).

## Brand Commitments

- Name: OS-Tutor (repository: OS-Tutor-RAG). The page must contain the text "OS Tutor" (asserted by
  `tests/test_server.py`).
- Visual direction pinned by the owner (2026-10-10): premium dark workspace, deep charcoal surfaces, restrained blue
  accents, plus a light theme. Lucide icons.
- The tutor writes in English, warmly and plainly, and never praises a wrong answer.

## Evidence on Hand

- Retrieval benchmark v1.1 (99 queries): hybrid nDCG@10 0.727 (`data/evaluation/`).
- Tutor evaluation (24 scripted dialogues): Phase 4 in `data/evaluation/tutor_eval/`, Phase 4.1 (current behaviour) in
  `data/evaluation/tutor_eval_v2/`.
- Draft learning objectives LO1 to LO8 in `data/assessment/learning_objectives.json` (DRAFT, not instructor-reviewed).
- No student study has been run: never show learning-gain claims, usage numbers or testimonials.

## Product Principles

1. Teach, don't tell: the interface supports answering the tutor and makes the diagnose, explain, check rhythm
   visible; it never shortcuts it.
2. Provenance is visible: every cited claim leads to the passage it came from.
3. Honest state: show only what the backend reports; never fake health, stages, sources, progress or persistence.
4. Calm for long sessions: reading comfort beats decoration.

## Accessibility & Inclusion

WCAG 2.2 AA in both themes: keyboard-complete, visible focus, screen-reader announcements for streaming state (not per
token), reduced motion respected. Students may write informal or Hinglish English; the tutor always replies in English.
