# OS-Tutor-RAG

- `PROJECT_LOG.md` (project root) is the required development history. Read it before making architectural
  changes, and append to it during meaningful work: decisions and rationale, files changed,
  dependencies, commands, test/validation results, failures and fixes, final results, phase status.
  Never rewrite or delete historical entries; add dated corrections instead.
- `Docs/` is the immutable raw corpus. Never modify, rename, move or delete anything in it, and never
  create files in it. The filesystem is case-insensitive: `docs/` is the same directory as `Docs/`, so
  never put project documentation in a `docs/` folder. Any `.md` placed there would be ingested as corpus.
- Work phase by phase. Check the current phase status in the log and do not start a new phase without
  explicit instruction from the project owner.
- Rebuild ingestion outputs: `python3 -m src.ingestion.pipeline --source Docs --output data`
- Build the vector index (Phase 2): `python3 -m src.retrieval.indexer` (add `--recreate` to replace it)
- Query it (debugging only): `python3 -m src.retrieval.search --query "..." --top-k 5`
- Evaluate retrieval against the gold benchmark (Phase 3A): `python3 -m src.evaluation.retrieval_evaluator`
  (`data/evaluation/retrieval_queries.json` is curated and frozen; never edit v1.0 judgments after seeing results)
- Benchmark v1.1 (Phase 3B-0): `data/evaluation/retrieval_queries_v1.1.json` is frozen: v1.0 plus judgments of the
  pooled dense top-20. Evaluate with `--benchmark data/evaluation/retrieval_queries_v1.1.json --name <run>`. Never edit
  v1.0 or v1.1; corrections go in a new version (v1.2), proposed in PROJECT_LOG.md first. Compare systems within one version.
- E1 BM25 baseline (Phase 3B): `--retriever bm25 --top-k 20 --deep-k 30` on the evaluator; compare runs with
  `python3 -m src.evaluation.compare <A_results.json> <B_results.json> --output <file.md>`. Outputs in `data/evaluation/e1_bm25/`.
- Tests: `python3 -m pytest tests -q`
- Configuration (PR #1): `src/config.py` reads environment variables / `.env` (copy `.env.example`). Defaults: `TUTOR_MODE=socratic`
  (owner decision 2026-10-10; `answer_first` is optional and unevaluated), `LLM_PROVIDER=ollama` (`mock` only for development and
  tests), `RERANKER_ENABLED=false` (E3 cross-encoder reranker stays off until it is evaluated beyond pooled-from-dense v1.1).
- E2 hybrid (Phase 3B): `--retriever hybrid --top-k 20 --deep-k 30` (RRF k=60, 50 candidates per system, untuned; fixed
  before evaluation). Outputs in `data/evaluation/e2_hybrid/`. BM25/hybrid v1.1 metrics are lower bounds (dense-only pooling).
- Tutor (Phase 4, approved 2026-10-04): `src/tutor/controller.py` + local Ollama (`src/tutor/llm.py`, default qwen3:8b).
  Chat page: `python3 -m src.tutor.server` then http://localhost:8000 (needs Ollama running; cannot run at the same time as
  other Qdrant users). Quality evaluation: qwen3:8b is the primary model, llama3.1:8b an optional comparison.
  Routine check: `tutor_eval run --model qwen3:8b --output-dir data/evaluation/tutor_eval_v2` then
  `tutor_eval report qwen3:8b --output-dir data/evaluation/tutor_eval_v2` (-> `report_qwen3_8b.md`). Name more models on
  `report` only for an explicit comparison (-> `report_<a>_vs_<b>.md`); only named models are read. Scenarios
  `data/evaluation/tutor_scenarios_v1.json` are frozen; Phase 4 results in `data/evaluation/tutor_eval/`, Phase 4.1 in `tutor_eval_v2/`.
- React frontend (2026-10-10): `frontend/` (React 19, TS, Vite, Tailwind 4). `cd frontend && npm run dev` -> http://localhost:5173,
  proxies `/api` to the tutor server on :8000 (`TUTOR_BACKEND` to change). Checks: `npm run typecheck`, `npm run lint`, `npm test`,
  `npm run build`. It consumes the server's SSE contract unchanged; `web/index.html` is kept. Product context: `PRODUCT.md`.
- Assessment framework: `data/assessment/` (DRAFT objectives and item bank; never report fabricated student results),
  analysis `python3 -m src.assessment.learning_gain responses.json`.
- Interpreter: plain `python3` may resolve to miniconda without the project's dependencies; use `/usr/local/bin/python3`
  (3.13.7, the baseline interpreter).
- Review 2 summary: `REVIEW2_REPORT.md`; case study submission: `OS-Tutor-RAG_Case_Study.docx`. Every number in them must come from project files.
- Future phases (v1.2 judgments, reranking/MMR, user study) require explicit approval.
