# OS Tutor HTTP API contract (v2)

Owner: backend (`src/`). Consumer: the student frontend (`frontend/` builds to `web/index.html`).
Status: **v2 is additive over v1.** Everything the v1 page uses keeps working; new fields and endpoints are marked *(new)*.
Unknown fields must be ignored by the client. Every endpoint below is implemented (checked against a running server on
2026-10-10).

Run without Ollama: `LLM_PROVIDER=mock python -m src.tutor.server` (scripted replies; retrieval is real).
Same origin as the page, no CORS. A Vite dev server should proxy `/api` to `http://127.0.0.1:8000`.

## Environment (server side only; the page never sees these)

`LLM_PROVIDER` (ollama|mock), `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_CONNECT_TIMEOUT`, `OLLAMA_READ_TIMEOUT`
(`LLM_TIMEOUT_SECONDS` is accepted as the old name), `TUTOR_MODE` (socratic, the default | answer_first), `REVISION_STEPS`,
`RETRIEVAL_TOP_K`, `RERANKER_ENABLED` (default false), `RERANKER_TOP_K`, `RERANK_MIN_SCORE`, `FINAL_CONTEXT_K`,
`VECTOR_STORE_DIR`, `LEARNER_DB_PATH`, `APP_HOST`, `APP_PORT`, `DEBUG`. CLI flags `--model --host --port` still work and win over env.

## JSON endpoints

| Method | Path | Response |
| --- | --- | --- |
| GET | `/api/models` | `{"models": [...], "default": "<model>"}` unchanged. *(new)* also `"provider": "ollama"\|"mock"`, `"error": "<message>"` (only when Ollama is unreachable; `models` is then `[]`) |
| GET | `/api/health/llm` *(new)* | `{"ok", "provider", "model", "reachable", "model_available", "message", "models"?, "error"?}`. Never contains the Ollama address. Use for the status pill. |
| GET | `/api/learner/profile` *(new)* | `{"summary": {"weak","developing","strong","unknown"}, "concepts": [Concept], "recent_doubts": [{"concept_id","text","time"}]}` |
| GET | `/api/revision/topics` *(new)* | `{"count": n, "concepts": [{"id","label","topic","level","confidence","reason"}]}` sorted most-needed first; `count` is what the sidebar shows ("3 concepts to review") |
| GET | `/api/sources/{chunk_id}` *(new)* | one source with its full text: `Source` + `"text"` |
| GET | `/api/conversations` *(new)* | `{"conversations": [{"id","title","mode","updated"}]}` newest first |
| GET | `/api/conversations/{id}` *(new)* | `{"id","title","mode","turns": [{"role": "student"\|"tutor","text","stage","sources": [Source]}]}` |

`Concept`: `{"id","label","topic": "threads"|"synchronization","level": "unknown"|"weak"|"developing"|"strong","confidence": 0..1|null,"attempts","misconceptions": [str],"last_interaction"}`

## Streaming endpoints (server-sent events)

`POST` with a JSON body; the response is `text/event-stream`, one `data: {"type": ..., "data": ...}` per event, blank line
between. Event types: `session`, `sources`, `analysis`, `token`, `turn`, `error`. A stream ends after `turn` or `error`.

### `POST /api/start` `{"question", "model"?}`

Events: `session` `{"id", "model"}` *(new: also `"mode"`)* -> `sources` [Source] -> `token` `{"text"}` ... -> `turn`.

### `POST /api/reply` `{"session_id", "text"?, "intent"?}`

`intent` *(new)* is optional and is what the "Explain differently" / "Test my understanding" buttons send; `text` may then
be empty. Intents: `simpler`, `detailed`, `example`, `analogy`, `code`, `scenario`, `explain_differently`, `test_me`,
`got_it`. Events: *(optional `analysis` {"level","gap"})* -> `sources` (only when a new retrieval happened, e.g. a new
question) -> `token`... -> `turn`.

### `turn` event

```
{"stage": str, "message": str, "analysis": {"level","gap"} | null,
 *(new)* "mode": "answer_first" | "socratic",
 *(new)* "follow_up": str | null,                  // a short offer / next step the page may render as a hint
 *(new)* "concepts": [{"id","label","topic"}],     // concepts this turn is about
 *(new)* "tutor_state": {"open": bool, "pending_check": bool, "representation": str | null},
 *(new)* "learner_update": {"concept_id","label","level","confidence","change"} | null,
 *(new)* "actions": [{"id": <intent>, "label": str}]   // suggested buttons for this turn; empty = show none
}
```

`stage` values.
- `socratic` mode (**the default**, unchanged): `DIAGNOSE`, `EXPLAIN`, `CHECK`, `DONE`, `ANSWER` (the side answer to a new
  question keeps `ANSWER`).
- `answer_first` mode *(new, optional: `TUTOR_MODE=answer_first`)*: `ANSWER` (grounded explanation; the conversation stays open), `CHECK` (the tutor
  asked a comprehension question; `tutor_state.pending_check` is true), `FEEDBACK` (reaction to the student's answer to a
  check; `analysis` is set), `NO_CONTEXT` (nothing relevant retrieved; fixed message, no model call). `DONE` is never sent in
  this mode and `/api/reply` keeps working after any turn. A client written for v1 / socratic stages must handle
  `FEEDBACK` and `NO_CONTEXT` before this mode is switched on.

`representation` is the explanation style used: `definition`, `intuition`, `analogy`, `scenario`, `code`, or `null`.

### `Source` (the `sources` event is a list of these)

```
{"ref": "S1", "chunk_id", "label", "display", "location", "section", "filename", "preview",
 "text"?, "source", "document_type", "content_type", "chunk_type", "topic", "subtopics": [...],
 "page_start", "slide_start"}
```

- `label` is the document title and origin, e.g. `"Lecture 15: Semaphores (IIT Bombay)"`; `display` adds the place:
  `"Lecture 15: Semaphores (IIT Bombay) — p.18"`. `location` is `"p.18"`, `"slide 5"` or `""`. Page and slide are never
  guessed: any field the retriever does not have is `null`/`""`.
- `preview` is the first ~280 characters; `text` is the full chunk (the `sources` event includes it, as in v1).
- Render all text as text, never as HTML (retrieved material is untrusted).
- `[S1]` markers in `message` always refer to refs in the most recent `sources` event for that turn (a new-question
  answer sends its own `sources`).

### `error` event

`{"message": str, "code": str}` *(new: `code`)*. `message` is safe to show as is. Codes: `bad_request` (empty input),
`expired` (unknown session), `llm_unavailable`, `llm_timeout`, `model_missing`, `llm_bad_response`, `no_context`, `internal`.

Messages that exist today and keep their wording: "Type a question first.", "Type an answer first.",
"This conversation has expired. Ask your question again." The v1 strings "The language model is not reachable (...)" and
"Something went wrong: ..." are **replaced** by fixed messages such as "The AI service is currently unavailable. Check that
Ollama is running and that the configured Ollama server address is reachable from this machine." (no exception text, no
address, no paths). Branch on `code`, not on message text.

## Smart Revision *(new)*

### `POST /api/revision/start` `{"concept"?: id, "model"?}`

No `concept` = the server picks the most-needed one. Events: `session` `{"id", "kind": "revision", "model", "concept":
{"id","label","topic"}, "reason", "total_steps"}` -> `sources` -> `token`... -> `turn`.

### `POST /api/revision/answer` `{"session_id", "text"}`

Events: `analysis` -> `token`... -> `turn`.

### revision `turn`

```
{"stage": "QUESTION" | "FEEDBACK" | "SUMMARY",
 "message": str,                 // full text to show: feedback then the next question
 "feedback": str | null, "question": str | null,
 "concept": {"id","label","topic"}, "reason": str,
 "level": "recall"|"understanding"|"application"|"reasoning"|"code",
 "difficulty": "easy"|"medium"|"hard",
 "progress": {"step": int, "total": int},
 "analysis": {"level","gap"} | null,
 "learner_update": {...} | null, "sources": [Source], "done": bool}
```

`SUMMARY` is the last turn (`done: true`): what was covered and how the confidence changed.
