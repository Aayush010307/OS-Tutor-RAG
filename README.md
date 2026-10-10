# OS-Tutor-RAG

A grounded conversational tutor for two topics of undergraduate Operating Systems: **Threads** and **Synchronization**.
It answers a student's doubts from the course material and shows where each answer comes from, explains again in a
different way when something did not land, checks understanding when that helps, remembers which concepts the student
struggles with, and later turns those difficulties into a short personalised revision session.

It is not a general OS chatbot and not "a language model over some PDFs": the course material is the source of truth,
the model is the teacher that phrases it.

Course project for BCSE303P Operating Systems Lab: Aayush Jaiswal (24BCI0042), Satyam Bhalotia (24BCI0055).

## Two experiences

- **Tutor chat.** By default (`TUTOR_MODE=socratic`) the tutor teaches diagnose-first: it asks what you already know,
  explains only the missing idea with citations, checks, and wraps up. The optional answer-first mode
  (`TUTOR_MODE=answer_first`) answers first: ask a question, get a cited answer. "Explain differently" walks a ladder
  (definition, intuition, analogy, OS scenario, code) instead of repeating itself. "Test my understanding" asks one
  question; the answer is judged solid / partial / misconception / unclear and answered accordingly. Nothing is quizzed
  after every message.
- **Smart Revision.** The learner model picks a genuinely weak concept, says why, and runs a short adaptive session:
  recall, understanding, application, reasoning, code. Questions are built from the student's own earlier doubts, the
  misconceptions on record, prerequisite concepts and the retrieved course material. After two misses it steps back to
  the weakest prerequisite and returns to reassess. Every answer updates the learner model.

## Architecture

```
                         Student
                            |
                    Frontend (web page)
                            |  HTTP + server-sent events   (API_CONTRACT.md)
                      Backend (src/tutor/server.py)
             +--------------+---------------+
             |                              |
       Tutor service                 Revision service
       (src/tutor/service.py)        (src/revision/service.py)
             |                              |
             |            +---- Learner model (src/learner/): concept taxonomy, mastery, misconceptions
             |            |
             +------------+
                   |
             Retrieval pipeline (src/retrieval/pipeline.py)
                   |
   Dense (Nomic + Qdrant)  +  BM25  ->  RRF hybrid  ->  top 20 candidates
                   ->  [optional cross-encoder rerank]  ->  intent / identifier order  ->  best 5
                   |
             LLM provider (src/tutor/llm.py):  OllamaProvider | MockLLMProvider
                   |
             Grounded, cited answer  +  Sources
```

Three things are kept apart on purpose:

| | What it is | Where |
| --- | --- | --- |
| Course knowledge | what the material says | `Docs/` -> `data/chunks/` -> vector index, BM25 |
| Chat history | what was said | in the session; saved transcripts in `data/learner/conversations.json` |
| Learner model | what the system believes the student understands or needs to revise | `data/learner/learner.json` |

The model never sees raw chat history as "knowledge" and never writes to the learner model: a small deterministic
update rule does (see below).

### Two machines

```
 Windows laptop                              MacBook
 frontend + backend + RAG + learner  --HTTP-->  Ollama + qwen3:8b   (port 11434)
 + vector index + tests + Git                   http://<MACBOOK_IP>:11434
```

The Windows laptop never runs a model. The address of the Mac is configuration, never code: put it in `.env`
(git-ignored). If the Mac's address changes, edit `.env` and restart the backend.

## Retrieval pipeline

The corpus (22 documents, 463 chunks) and its retrieval results are frozen research artefacts; the pipeline wraps them and
never changes them.

1. **Dense** retrieval: Nomic Embed v1.5 (ONNX) over Qdrant.
2. **BM25**: lexical, with a tokenizer that keeps identifiers such as `pthread_mutex_lock` whole, so exact API names
   retrieve their chunks.
3. **Hybrid RRF** (k=60, equal weights): the established result, nDCG@10 0.727 on the 99-query benchmark v1.1.
4. **Reranker** (optional, `RERANKER_ENABLED`): the fused top `RERANKER_TOP_K` (20) are re-scored jointly with the query by a
   cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`, ONNX, pinned revision, no new dependency). If the model cannot
   load, or a call fails, the pipeline serves the hybrid order and says so.
5. **Intent and identifier order**: the query is classified as conceptual, code or practice from simple rules. A chunk that
   contains an API identifier the student typed moves up three places; for *code* and *practice* requests, chunks of the
   matching content type (code/lab material, exercises) move up three places. Nothing is ever dropped. Content-type
   preference for *conceptual* queries exists but is **off by default**, because it measurably hurt (see Evaluation).
6. The best `FINAL_CONTEXT_K` (5) chunks go to the model. Results are cached per query: the corpus is frozen.

Chunk metadata (already present, reused unchanged): topic, subtopics, document type, content type, source, filename,
page or slide, section, chunk id. The page shows readable citations such as *Lecture 15: Semaphores (IIT Bombay) — p.18*,
built only from that metadata; a missing page is shown as missing, never guessed.

## Grounding and safety

- The retrieved context is the only source of OS facts. If it does not cover the question the tutor says so; with nothing
  retrieved (or, with the reranker on and `RERANK_MIN_SCORE` set, nothing relevant enough) the answer is a fixed message
  and **no model is called**.
- Citations `[S1]` are validated against the retrieved sources before the student sees them; invented ones are removed.
- Prompts keep four things apart: instructions, the retrieved reference block (marked as data), the conversation, and the
  learner context. Text in a chunk or a student message cannot pose as a prompt section or close the reference block.
- Only the model's final answer is used: Ollama's `thinking` field and any inline `<think>` block are dropped inside the
  provider, so reasoning never reaches the history, the learner model, the logs or the page.
- Errors shown to students are fixed messages (no exception text, addresses or paths).

## Tutor flow

**Default: `TUTOR_MODE=socratic`** (diagnose first; the flow the tutor evaluation measures):

```
question -> retrieve -> DIAGNOSE (one probing question, no answer yet)
   reply judged solid -> CHECK -> solid -> DONE (wrap-up)
   otherwise          -> EXPLAIN the gap, cited (at most 2 rounds) -> DONE with the full grounded answer
   a new question while the tutor's question is pending -> side ANSWER; the pending question stays pending
```

**Optional: `TUTOR_MODE=answer_first`** (conversational; not yet evaluated, and the React frontend does not yet handle its
`FEEDBACK` / `NO_CONTEXT` stages):

```
question -> retrieve -> grounded ANSWER (conversation stays open)
   "I still don't understand" / "simpler" / "analogy" / "code"   -> same idea, new representation
   "test my understanding"                                        -> CHECK (one question, pending)
   answer to the check -> solid: confirm | partial: clarify | misconception: correct | unclear: simplify and re-ask
   a new question while a check is pending -> answered on its own; the check stays pending
```

Which of these a message is, is decided by rules, not by the model, so the flow is testable without an LLM. A check is
offered on the first answer and then at most every third; the student can always ask for one.

## Learner model

`src/learner/taxonomy.py` is a controlled vocabulary of 28 concepts (threads, race condition, critical section, mutex,
semaphore, condition variable, monitor, producer-consumer, deadlock, ...) with prerequisite links, mapped onto the corpus's
own subtopic labels. `pthread_exit` is absent because no chunk mentions it. Detection is regular expressions over the
student's words plus the subtopics of retrieved chunks.

`src/learner/model.py` keeps one record per concept: confidence, attempts, misconceptions, doubts, last interaction.

```
confidence' = confidence + alpha * (score - confidence)     alpha 0.4 (0.2 for "asked again"), prior 0.5
solid 1.0   partial 0.55   unclear 0.15   misconception 0.0   asked-again 0.25
levels: weak < 0.40 <= developing < 0.75 <= strong       a question alone starts a concept at 0.40
```

Only meaningful events update it: a question that names a course concept, a request to have something explained again
(not a request for an analogy), and the analysed answer to a check or revision question. Greetings, "thanks" and "got it" do
not. Stored in `data/learner/learner.json` (git-ignored: it holds the student's own words).

## Smart Revision

`src/revision/service.py`. Pick the weakest concept (`/api/revision/topics` lists them with the reason), ask at a level that
fits the student, adapt:

| answer | next question |
| --- | --- |
| solid | one level harder (recall -> understanding -> application -> reasoning -> code) |
| partial | same level, aimed at the missing idea |
| misconception | corrected plainly, then one level easier on the same idea |
| unclear | simpler explanation, same question in easier words |

Two misses in a row step back to the concept's weakest prerequisite (once per session) and then return to the original
concept at application level to reassess. A session is `REVISION_STEPS` (5) questions, or ends early when the hardest
level is answered correctly. The closing summary is built from recorded facts (before and after confidence per concept), not
generated. Course material is retrieved once per concept and reused for the session.

## Configuration

Everything is an environment variable, read once in `src/config.py`; a `.env` file in the repository root is loaded by the
server (variables already set in the environment win). Copy `.env.example` to `.env`; `.env` is git-ignored.

| Variable | Default | Meaning |
| --- | --- | --- |
| `LLM_PROVIDER` | `ollama` | `ollama` or `mock` (scripted, never contacts Ollama) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | the Ollama server, e.g. `http://<MACBOOK_IP>:11434` |
| `OLLAMA_MODEL` | `qwen3:8b` | model name |
| `OLLAMA_CONNECT_TIMEOUT` / `OLLAMA_READ_TIMEOUT` | 5 / 120 | seconds to reach the server / to wait for a reply |
| `TUTOR_MODE` | `socratic` | or `answer_first` (optional, not yet evaluated) |
| `RETRIEVAL_TOP_K` / `RERANKER_TOP_K` / `FINAL_CONTEXT_K` | 20 / 20 / 5 | candidates / reranked / shown to the model |
| `RERANKER_ENABLED` | `false` | see Evaluation |
| `RERANK_MIN_SCORE` | unset | with the reranker on, below this the tutor says it lacks material |
| `REVISION_STEPS` | 5 | questions per revision session |
| `VECTOR_STORE_DIR`, `LEARNER_DB_PATH` | `data/vector_store/qdrant`, `data/learner/learner.json` | storage |
| `APP_HOST`, `APP_PORT`, `DEBUG` | `127.0.0.1`, 8000, `false` | server |

### Remote Ollama (the Mac)

On the Mac: install [Ollama](https://ollama.com), `ollama pull qwen3:8b`, and make it listen on the network
(`OLLAMA_HOST=0.0.0.0:11434 ollama serve`, or set `OLLAMA_HOST` for the app and restart it). Allow port 11434 through the Mac's
firewall; both machines must be on the same network. Find the Mac's address with `ipconfig getifaddr en0`.

On the Windows laptop, in `.env`:

```
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://<MACBOOK_IP>:11434
OLLAMA_MODEL=qwen3:8b
```

Check it: `curl http://<MACBOOK_IP>:11434/api/tags` from the laptop, or open `http://localhost:8000/health/llm` once the backend
runs. If the Mac is asleep or unreachable the tutor says "The AI service is currently unavailable..." and invents nothing.
Automated tests never need the Mac: they use `LLM_PROVIDER=mock` or scripted models.

## Run it

Requires Python 3.12+ (3.13 is the project baseline). Windows: set `PYTHONUTF8=1`.

```bash
python -m pip install -r requirements.txt
cp .env.example .env               # then edit it
python -m src.tutor.server         # http://localhost:8000
LLM_PROVIDER=mock python -m src.tutor.server     # no Ollama needed (scripted replies, development only)
python -m pytest tests -q
python -m src.evaluation.tutor_eval run --model qwen3:8b --output-dir data/evaluation/tutor_eval_v2
python -m src.evaluation.tutor_eval report qwen3:8b --output-dir data/evaluation/tutor_eval_v2   # qwen only
```

Only one process may open the local Qdrant index at a time: do not run the server, an evaluation and the tests together.
The first start downloads the embedding model (and the reranker if enabled) from Hugging Face.

### Frontend

<!-- The frontend section is maintained by the frontend session; text below ported from its 2026-10-10 notes. -->

The React frontend (`frontend/`, Node 20+) runs beside the server and proxies `/api` to it:

```bash
cd frontend && npm install
npm run dev            # http://localhost:5173 (needs the tutor server on :8000)
npm run typecheck && npm run lint && npm test && npm run build
```

Lesson history in the React app is kept in the browser only; tutor sessions live in server memory. The original
single-file page `web/index.html` is still served by the backend at http://localhost:8000.

## HTTP API

See `API_CONTRACT.md`: `/api/start`, `/api/reply`, `/api/revision/start`, `/api/revision/answer` (server-sent events),
`/api/models`, `/health/llm`, `/api/learner/profile`, `/api/revision/topics`, `/api/sources/<chunk_id>`,
`/api/conversations`.

## Evaluation

All numbers below are measured and stored under `data/evaluation/`; nothing is estimated.

**Retrieval** (99-query benchmark v1.1, frozen; judgments were pooled from the dense top 20, so every figure is a lower bound):

| Retriever | nDCG@10 | MRR@5 | Recall@10 |
| --- | --- | --- | --- |
| BM25 | 0.631 | 0.852 | 0.543 |
| Dense | 0.706 | 0.914 | 0.625 |
| Hybrid RRF (E2) | 0.727 | 0.921 | 0.645 |
| Hybrid + reranker (E3) | 0.744 | 0.938 | 0.657 |
| Hybrid + intent order, all content types preferred (E3) | 0.703 | 0.883 | 0.642 |
| Hybrid + reranker + intent order, all types (E3) | 0.722 | 0.901 | 0.660 |

E3 runs are in `data/evaluation/e3_rerank/`, run on the Windows laptop together with a fresh hybrid rerun (nDCG@10 0.727;
the saved E2 file says 0.7274 and the rerun 0.7272: floating-point drift in the ONNX runtime, which is why
`test_saved_e2_run_matches_frozen_inputs_and_a_fresh_run` can fail on this machine).
Preferring lecture and textbook chunks for conceptual queries lowered nDCG@10 by 0.028 on the 80 conceptual queries,
because many are answered best by exercises or lab problems; that preference is therefore off by default.

**Tutor** (24 scripted dialogues, 8 questions x 3 student profiles, the Socratic tutor). Phase 4 (temperature 0): expected
teaching path 21/24 for qwen3:8b. Phase 4.1 (temperature 0.3, shared grounding policy, citation validation;
`data/evaluation/tutor_eval_v2/`): qwen3:8b expected path 23/24, exact analysis level 46/48, explanations citing a source
40/48, manual rubric correct 1.98 / grounded 1.89 / pedagogy 1.38 (single annotator); median 21 s per tutor call.
llama3.1:8b is an optional comparison. The answer-first mode has **not** been evaluated.

**Pending (infrastructure exists, no numbers yet):** groundedness and hallucination rate of answer-first answers, misconception
correction, revision question relevance, adaptation to prior weakness, improvement within a revision session. No student study
has been run.

## Repository

| Path | Contents |
| --- | --- |
| `Docs/` | Raw course corpus (22 PDF/PPT/PPTX files). Never modified by the code. |
| `src/ingestion/` | Extraction, cleaning, metadata, chunking, deduplication, validation |
| `src/retrieval/` | Dense, BM25, hybrid RRF, cross-encoder reranker, intent order, the product pipeline |
| `src/tutor/` | LLM providers, answer-first tutor service, Socratic controller, mock LLM, web server |
| `frontend/` | React chat app (Vite, TypeScript, Tailwind) for the tutor server |
| `web/index.html` | Original single-file chat page (still served at http://localhost:8000) |
| `src/learner/` | Concept taxonomy and the learner model |
| `src/revision/` | Smart Revision |
| `src/evaluation/` | Retrieval evaluator, run comparison, tutor quality evaluation |
| `src/assessment/` | Pre-test / post-test learning-gain analysis |
| `data/` | Processed chunks, vector index, benchmarks, evaluation results, draft assessment items |
| `tests/` | 359 automated tests (no Ollama needed) |
| `PROJECT_LOG.md` | Full development history, decisions and results |
| `OS-Tutor-RAG_Case_Study.docx` | Case study report |

## Corpus note

`Docs/` contains third-party teaching material (VIT course slides, IIT Bombay lectures and practice problems,
chapters of *Operating Systems: Three Easy Pieces* by R. and A. Arpaci-Dusseau). It is included for academic
reproducibility of this course project; all rights belong to the original authors.
