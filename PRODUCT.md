# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + TypeScript + Vite + Tailwind CSS (user decision, 2026-10-08). Source lives in `frontend/`; `npm run build`
compiles it into the single `web/index.html` that the Python tutor server (`src/tutor/server.py`) already serves at
`/`, so the backend serves the app unchanged and the demo runs without Node. `npm run dev` serves the source with an
`/api` proxy to the tutor server. The Python backend (retrieval, tutor controller, Ollama client) is not part of the
frontend work.

## Users

- Undergraduate students of the BCSE303P/BCSE303L Operating Systems course studying threads and synchronization,
  usually alone at a laptop, often before a lab or exam, in sessions that can last an hour.
- Course staff and reviewers (professor demonstration, Review 2/3, viva) judging in the first minute whether the tool
  teaches rather than answers, and whether its answers are grounded in the course material.

## Product Purpose

OS-Tutor-RAG is a one-to-one tutor for Operating Systems that teaches rather than only answers. In its default
answer-first mode it gives a grounded explanation, then checks understanding with a question and gives feedback on the
student's answer. In Socratic mode it first asks what the student already knows (DIAGNOSE), judges the reply (solid,
partial, misconception, unclear), explains only the gap (EXPLAIN, at most two rounds), checks (CHECK) and wraps up
(DONE). Success is a student who can apply the idea, with every explanation traceable to a lecture slide or textbook
page.

## Positioning

Source-grounded Socratic tutoring over this course's own material: retrieval is hybrid (dense + BM25, RRF) over 22
course documents, citations are validated against the retrieved sources before text reaches the student, and new
questions asked mid-flow are routed deterministically to a side answer that keeps the tutor's pending question open.
A general chatbot can answer; it cannot show which slide of this course each sentence came from.

## Operating Context

- Runs locally: Python standard-library HTTP server, Qdrant local index, Ollama for generation. The Ollama server may
  be on another machine (`OLLAMA_BASE_URL`); the model is configurable (`OLLAMA_MODEL`, default qwen3:8b,
  llama3.1:8b also evaluated). Replies stream over server-sent events and can take seconds to minutes on a laptop.
- Sessions live in server memory and are lost on restart; nothing is saved per student.
- Every finished turn is logged to `data/tutor_logs/` for the pilot and quality review.

## Capabilities and Constraints

- The authoritative API is `API_CONTRACT.md` (owned by the backend). v2: `GET /api/models`, `GET /api/health/llm`,
  `POST /api/start {question, model?}`, `POST /api/reply {session_id, text?, intent?}`; SSE events `session`,
  `sources`, `analysis`, `token`, `turn`, `error` (errors carry a `code`). Learner profile, Smart Revision,
  conversation history and source lookup endpoints are planned, not live; the UI shows them only once they respond.
- Two tutor modes chosen server-side (`TUTOR_MODE`): `answer_first` (default; stages ANSWER, CHECK, FEEDBACK,
  NO_CONTEXT; the conversation stays open) and `socratic` (DIAGNOSE, EXPLAIN, CHECK, DONE; ANSWER for a side
  question). Turns may carry suggested intent buttons, a follow-up hint, the concepts covered and a learner-model update.
- Source metadata available: ref (S1..S5), document label and display string, location (page or slide, never
  guessed), section, filename, topic and subtopics, preview and passage text. No retrieval scores; nothing may be
  invented.
- Not supported by the backend: topic filtering, stopping generation server-side, accounts.
- Scope of the corpus: Threads and Synchronization (threads, pthread API, race conditions, locks, semaphores,
  condition variables, classical problems, concurrency bugs and deadlock).

## Brand Commitments

- Product name: OS-Tutor-RAG; the page must contain the text "OS Tutor" (asserted by `tests/test_server.py`).
- Tutor writes in English, warmly and plainly; no praise for wrong answers.

## Evidence on Hand

- Retrieval benchmark v1.1 (99 queries): hybrid nDCG@10 0.727 (`data/evaluation/`).
- Tutor evaluation (24 scripted dialogues, qwen3:8b), `data/evaluation/tutor_eval/report.md`.
- Draft learning objectives LO1 to LO8 in `data/assessment/learning_objectives.json` (DRAFT, not instructor-reviewed).
- No student study has been run; no learning-gain, usage or satisfaction claims may be shown.

## Product Principles

1. Teach, don't answer: the interface makes the diagnose, explain, check rhythm visible and never shortcuts it.
2. Provenance is the product: every cited claim leads to its real file, page or slide and passage.
3. Show only what the backend knows: no invented stages, sources, titles, progress or capabilities.
4. Calm for an hour of study: reading comfort and focus over spectacle.

## Accessibility & Inclusion

WCAG 2.2 AA: keyboard-only use, visible focus, screen-reader announcements for streaming state (not per token),
reduced motion, sufficient contrast in light and dark themes. Students may write informal or Hinglish questions.
