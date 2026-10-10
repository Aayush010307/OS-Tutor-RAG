# OS Tutor HTTP API contract (v2)

Owner: backend (`src/`). Consumer: the React student frontend (`frontend/`, built to `frontend/dist`). The legacy page
`web/index.html` (served at `/`) is kept as is: a prebuilt bundle with no source in the repository, not updated for
changes after 2026-10-10 (see "Uncertainty and hints").
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
 *(new)* "tutor_state": {"open": bool, "pending_check": bool, "representation": str | null}   // answer_first
                 | {"rounds": int, "max_rounds": int},                                        // socratic (2026-10-10)
 *(new)* "learner_update": {"concept_id","label","level","confidence","change"} | null,
 *(new)* "actions": [{"id": <intent>, "label": str}],  // suggested buttons for this turn; empty = show none
 *(new)* "sources": [Source]                         // this turn's own provenance, see "Citations and turn sources"
}
```

`stage` values.
- `socratic` mode (**the default**): `DIAGNOSE`, `EXPLAIN`, `CHECK`, `DONE`, `ANSWER` (the side answer to a new
  question keeps `ANSWER`), and *(new, 2026-10-10)* `HINT` (see "Uncertainty and hints" below).
- `answer_first` mode *(new, optional: `TUTOR_MODE=answer_first`)*: `ANSWER` (grounded explanation; the conversation stays open), `CHECK` (the tutor
  asked a comprehension question; `tutor_state.pending_check` is true), `FEEDBACK` (reaction to the student's answer to a
  check; `analysis` is set), `NO_CONTEXT` (nothing relevant retrieved; fixed message, no model call). `DONE` is never sent in
  this mode and `/api/reply` keeps working after any turn. *(new, 2026-10-10)* `HINT` while a check is pending. A
  client written for v1 / socratic stages must handle `FEEDBACK` and `NO_CONTEXT` before this mode is switched on.

### Uncertainty and hints *(new, 2026-10-10)*

Replies that answer nothing are recognised by deterministic rules (`is_unsure`, `wants_explanation`,
`is_hint_request` in `src/tutor/controller.py`), never by the model. Not knowing is not a wrong answer.

- **Uncertainty** (the whole reply only says the student does not know, e.g. "i am not sure", "I don't know what join
  does", "Sorry, no idea") or **a request for the explanation** ("explain it to me", "Can you explain that again?"):
  the `analysis` event is `{"level": "unclear", ...}` without a model call.
  - socratic: `EXPLAIN`, a supportive explanation that never calls the student wrong, which does **not** use an
    explanation round (`tutor_state.rounds` is unchanged). Still unsure after that, or with the rounds already used,
    the student gets the full answer (`DONE`).
  - answer_first: at a pending check, `FEEDBACK` with a nudge and an easier first-step question, prompted not to give
    the check's answer (the check stays pending; after two misses the full answer, as before); with no check pending, the
    last answer explained differently (`ANSWER`).
  - A hedged answer with content ("not sure, but I think it releases the lock") is an answer: the model judges it.
- **A hint request** ("give me a hint", "Can I get a hint?"): `HINT`, a short nudge toward the answer of the pending
  question, citing the passages that question is about (`turn.sources`), ending with "Try the question again: <pending
  question>", which the server adds itself. No `analysis`; the lesson stage, the rounds and
  the pending question or check are unchanged. In answer_first with nothing pending, a fixed message with
  `sources: []` and no model call.
- `tutor_state.rounds` / `max_rounds` (socratic) are the explanation rounds used; after `max_rounds` the tutor gives the
  full answer. Clients should show this count instead of counting `EXPLAIN` turns.
- Compatibility: additive. A client that does not know `HINT` shows it as an unknown stage and should not treat it as a
  lesson stage; a client that ignores `tutor_state` and counts `EXPLAIN` turns overcounts after "I'm not sure".
  The legacy `web/index.html` is such a client: it shows a hint with no stage label, moves its state track to an
  unknown stage for that turn, and counts a supportive explanation as a round. It is legacy-only and not maintained
  (no source in the repository); the React frontend handles all of this.

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

### Citations and turn sources *(new, 2026-10-10)*

- **`turn.sources` is the turn's provenance:** exactly the passages its reply was generated from, in the `Source` schema
  above (with `text`), numbered as the prompt numbered them. Every `[Sn]` in `turn.message` refers to the entry with
  `ref` `Sn` in **that turn's** `sources`. Resolve citations against it, never against an earlier event.
- **A response's sources are not always the latest `sources` event.** The `sources` event is what a retrieval found while
  the request ran; the turn says what was used:
  - a new question's grounded answer (`ANSWER`), a re-explanation and a side answer cite their own retrieval;
  - `CHECK` and `FEEDBACK` (answer-first) cite the context kept from the last successful answer, which they do not
    re-send as a `sources` event; a side answer or a no-context reply in between does not replace that context;
  - Socratic turns cite the lesson's context; a side answer cites its own;
  - `NO_CONTEXT` and the "got it" reply used no passage: `sources` is `[]`, even if a `sources` event listed rejected
    candidates during the same request.
- **Backward compatibility:** `sources` is additive; the existing fields and the event order (`session`, `sources`,
  `analysis`, `token`..., `turn`) are unchanged. A client talking to an older server that omits `turn.sources` falls
  back to the previous rule: the latest `sources` event of the request, or the topic's sources from `/api/start`.

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
