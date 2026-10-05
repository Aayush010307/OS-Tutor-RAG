# OS-Tutor-RAG

An interactive retrieval-augmented tutor for undergraduate Operating Systems (Threads and Synchronization).
Instead of just answering, it asks what the student already knows, explains the gap with an example, checks
understanding, and cites the lecture slide or textbook page each explanation comes from. It runs fully locally
with Ollama models.

Course project for BCSE303P Operating Systems Lab: Aayush Jaiswal (24BCI0042), Satyam Bhalotia (24BCI0055).

## What is in the repo

| Path | Contents |
| --- | --- |
| `Docs/` | Raw course corpus (22 PDF/PPT/PPTX files). Never modified by the code. |
| `src/ingestion/` | Extraction, cleaning, metadata, chunking, deduplication, validation |
| `src/retrieval/` | Dense (Nomic Embed v1.5 + Qdrant), BM25, and hybrid RRF retrievers |
| `src/evaluation/` | Retrieval evaluator, run comparison, tutor quality evaluation |
| `src/tutor/` | Tutor controller (diagnose, analyse, explain, check), Ollama client, web server |
| `src/assessment/` | Pre-test / post-test learning-gain analysis |
| `web/index.html` | Student chat page |
| `data/` | Processed chunks, vector index, benchmarks, evaluation results, draft assessment items |
| `tests/` | 96 automated tests |
| `PROJECT_LOG.md` | Full development history, decisions and results |
| `OS-Tutor-RAG_Case_Study.docx` | Case study report |

## Results so far

- Retrieval (99-query benchmark v1.1): hybrid RRF nDCG@10 0.727 vs dense 0.706 vs BM25 0.631.
- Tutor (24 scripted dialogues, qwen3:8b): expected teaching path in 21/24 dialogues; understanding judged
  correctly (solid / not solid) in 93% of replies; 62/80 turns fully correct on manual review.
- No student study has been run yet. Details: `data/evaluation/` and `PROJECT_LOG.md`.

## Run it

Requires Python 3.13 and [Ollama](https://ollama.com).

```bash
python3 -m pip install -r requirements.txt
ollama pull qwen3:8b
python3 -m src.tutor.server        # then open http://localhost:8000
```

The first start downloads the embedding model. Other commands:

```bash
python3 -m pytest tests -q                                   # tests
python3 -m src.retrieval.search --query "What is a semaphore?" --top-k 5
python3 -m src.evaluation.retrieval_evaluator --retriever hybrid --top-k 20 \
    --benchmark data/evaluation/retrieval_queries_v1.1.json --output-dir /tmp/eval --name hybrid
python3 -m src.evaluation.tutor_eval run --model qwen3:8b
```

## Corpus note

`Docs/` contains third-party teaching material (VIT course slides, IIT Bombay lectures and practice problems,
chapters of *Operating Systems: Three Easy Pieces* by R. and A. Arpaci-Dusseau). It is included for academic
reproducibility of this course project; all rights belong to the original authors.
