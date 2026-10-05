# OS-Tutor-RAG — Review 2 Report

Date: 2026-10-04. Project root: `/Users/aayushjaiswal/Desktop/Projects/OS-RAG`.

Every number below comes from a file in this repository. The source is named next to each table. Nothing here
reports student results: no student has used the tutor or taken the tests yet.

Status labels used in this report:

- **IMPLEMENTED**: the code exists and is tested.
- **PARTIAL**: the code exists, but a required part is not wired in.
- **PLANNED**: designed only.

---

## A. System architecture

```
Docs/ (22 raw files, immutable)
  └─ Phase 1 ingestion ── extraction → cleaning → metadata → chunking → dedup → validation
       └─ data/chunks/chunks.jsonl (463 chunks, frozen)
            ├─ Phase 2 dense index ── nomic-embed-text-v1.5 (768-d, cosine) → Qdrant local
            ├─ E1 BM25 index ──────── in-memory Okapi BM25 (k1 1.2, b 0.75)
            └─ E2 hybrid ───────────── RRF(dense top 50, BM25 top 50), k = 60
                 └─ Tutor controller ── diagnose → analyse → explain/example → check → move on
                      └─ LLM (callable interface; no backend connected yet)
Evaluation: benchmark v1.1 (99 queries) → evaluator → compare (+ judged-only view)
Assessment: learning objectives + draft parallel-form item bank → learning-gain analysis
```

| Component | Code | Status |
| --- | --- | --- |
| Ingestion | `src/ingestion/` | IMPLEMENTED, frozen (Phase 1) |
| Dense retrieval | `src/retrieval/{embeddings,vector_store,indexer,retriever}.py` | IMPLEMENTED, frozen (Phase 2) |
| BM25 retrieval | `src/retrieval/bm25.py` | IMPLEMENTED (E1) |
| Hybrid RRF retrieval | `src/retrieval/hybrid.py` | IMPLEMENTED (E2, this session) |
| Retrieval evaluation | `src/evaluation/` | IMPLEMENTED |
| Tutor controller | `src/tutor/controller.py` | PARTIAL: the flow, prompts and provenance are done; no LLM is connected |
| Learning-gain analysis | `src/assessment/learning_gain.py` | IMPLEMENTED; it has never been run on real data |
| Item bank | `data/assessment/question_bank_draft.json` | DRAFT: not validated by the instructor and not piloted |
| Answer generation (RAG) | — | PLANNED (Phase 4, needs approval) |
| Student-facing frontend | — | PLANNED |

## B. Corpus statistics

Source: `PROJECT_LOG.md` (Phase 1) and `data/manifests/`.

| Item | Value |
| --- | --- |
| Documents | 22 (16 PDF, 5 PPTX, 1 PPT); Synchronisation 17, Threads 5 |
| Sources | IIT Bombay 7, OSTEP 6, VIT 5, unknown 4 |
| Units | 234 PDF pages, 247 slides |
| Chunks | 463 (204 section, 186 slide, 60 qa_pair, 13 problem) |
| Chunk tokens (cl100k_base) | 99,322 total; median 186, mean 214.5, max 913 |
| Duplicates | 1 near-duplicate document pair (lecture15 / Semaphore-copy); 4 exact-duplicate chunks |
| Frozen digests | `chunks.jsonl` `90d1e88e…fcbe16`; Docs/ corpus digest `1df92ddc…0520f9` (both re-verified 2026-10-04) |

## C. Retrieval architecture and evaluation protocol

All three systems share the following controls:

- the same 463 chunks;
- the same 99 queries;
- the same frozen benchmark v1.1 (`bfbbd033…bd5986`; 757 relevant and 1,395 explicit grade-0 judgments);
- the same metric code (`src/evaluation/metrics.py`);
- depth 20, with no metadata filters.

The three systems differ as follows:

- **Dense (Phase 2).** `nomic-embed-text-v1.5`, 768-d, cosine similarity, exact search in local Qdrant.
- **BM25 (E1).** Lowercased regex tokens; `pthread_create` stays one token. No stemming, no stopwords.
  k1 = 1.2 and b = 0.75 were fixed before any run.
- **Hybrid (E2).** Reciprocal Rank Fusion: `rrf(d) = Σ_s 1/(60 + rank_s(d))` over the dense top 50 and the
  BM25 top 50. The weights are equal. Ties go to corpus order. The parameters k = 60 and depth 50 were
  fixed before the first run and were not tuned. The method uses ranks only, so the incomparable cosine
  and BM25 scores are never mixed.

**Pooling caveat.** v1.1 was judged from the dense top 20 only. A result outside that pool counts as
non-relevant, so BM25 and hybrid scores are **lower bounds**. Each comparison therefore reports two
supplementary measures:

- the unjudged count;
- a judged-only ("condensed list") view, in which unjudged results are dropped before scoring.

## D–F. Results: Dense vs BM25 vs Hybrid

Sources:

- `data/evaluation/e1_bm25/dense_v1.1_top20_results.json`. Its top 10 is identical to the frozen
  `baseline_dense_v1.1_results.json`.
- `data/evaluation/e1_bm25/bm25_v1.1_results.json`
- `data/evaluation/e2_hybrid/hybrid_rrf_v1.1_results.json`

Comparisons: `data/evaluation/e2_hybrid/comparison_*.md`.

| Metric | Dense v1.1 | BM25 E1 | Hybrid E2 |
| --- | --- | --- | --- |
| Precision@5 | 0.598 | 0.517 | **0.632** |
| Precision@10 | 0.458 | 0.378 | **0.470** |
| Recall@5 | 0.436 | 0.401 | **0.471** |
| Recall@10 | 0.624 | 0.543 | **0.645** |
| MRR@5 | 0.914 | 0.852 | **0.921** |
| nDCG@5 | 0.695 | 0.629 | **0.725** |
| nDCG@10 | 0.706 | 0.631 | **0.727** |
| MAP@5 | 0.404 | 0.361 | **0.433** |

(The dense Recall@10 is 0.624 here because it is averaged from unrounded per-query values. The frozen report
shows 0.625. The per-query values are identical.)

| Queries with a relevant chunk in the top K (of 99) | Dense | BM25 | Hybrid |
| --- | --- | --- | --- |
| top 1 | **87** | 79 | 86 |
| top 3 | 95 | 89 | **97** |
| top 5 | 97 | 92 | **98** |
| top 10 | 97 | 96 | **99** |
| top 20 | 99 | 99 | 99 |

| Failures | Dense | BM25 | Hybrid |
| --- | --- | --- | --- |
| No relevant chunk in the top 5 | q009, q020 | q002, q008, q046, q055, q059, q060, q081 | q008 |
| No relevant chunk in the top 10 | q009, q020 | q008, q046, q060 | none |

| Unjudged results (lower-bound effect) | Dense | BM25 | Hybrid |
| --- | --- | --- | --- |
| top 5 | 0 (0.0%) | 152 (30.7%) | 11 (2.2%) |
| top 10 | 0 (0.0%) | 418 (42.2%) | 108 (10.9%) |
| top 20 | 0 (0.0%) | 1,118 (56.5%) | 667 (33.7%) |

| Judged-only (condensed list), supplementary | Dense | BM25 | Hybrid |
| --- | --- | --- | --- |
| Precision@5 | 0.598 | 0.659 | 0.646 |
| nDCG@10 | 0.706 | 0.731 | 0.751 |
| MAP@5 | 0.404 | 0.453 | 0.439 |

The judged-only view lets a system skip past every chunk nobody judged. It therefore favours the system with
the most unjudged results, which is BM25. It is an upper-bound-style view, not a replacement for the main table.

**Per-query paired comparison (nDCG@10).** Each cell gives the queries where the second system is higher /
lower / equal, then the two-sided exact sign-test p-value over the non-tied queries. These are computed from
the saved per-query metrics. They are lower-bound metrics, so the comparisons carry the pooling bias.

| Comparison | Higher / lower / equal | Sign-test p |
| --- | --- | --- |
| Hybrid vs dense | 58 / 32 / 9 | 0.008 |
| Hybrid vs BM25 | 77 / 16 / 6 | < 0.0001 |
| BM25 vs dense | 33 / 60 / 6 | 0.007 |

For Precision@5, hybrid vs dense is 32 / 17 / 50 (p = 0.044). For MAP@5 it is 42 / 26 / 31 (p = 0.068).

**What the data supports:**

- Hybrid E2 scores higher than dense on every headline metric, even though it is the system penalised by
  pooling. It also removes both dense top-10 failures.
- BM25 alone scores below dense on the main metrics.
- BM25's judged-only scores are higher than dense's. With 42% of BM25's top 10 unjudged, the true
  dense-vs-BM25 ordering is therefore **not established**.
- Hybrid is not uniformly better. It is lower than dense on 32 queries, including q092, q008, q059,
  q046 and q027 (section G).

## G. Error analysis

### q009: "I pass &i from my for loop to pthread_create and the threads print the wrong numbers. Why?"

| Judged relevant chunk | Grade | Dense rank | BM25 rank | Hybrid rank |
| --- | --- | --- | --- | --- |
| ps-concurrency c0019 | 2 | 19 | 2 | **3** |
| pthreads-sync c0003 | 2 | >30 | 1 | 11 |
| threads-api c0018 | 1 | >30 | 26 | 17 |
| threads-api c0003 | 1 | >30 | >30 | >30 |

Per-system metrics:

| | nDCG@10 | MRR@5 |
| --- | --- | --- |
| Dense | 0.000 | 0 |
| BM25 | 0.778 | 1.0 |
| Hybrid | 0.239 | 0.333 |

- **BM25 recovers both grade-2 chunks.** Dense misses one of them entirely: pthreads-sync c0003 is not
  in its top 30.
- **Hybrid also recovers ps-concurrency c0019, at rank 3.** pthreads-sync c0003 drops to rank 11 in
  hybrid, because dense does not rank it at all.
- **The dense failure is mainly candidate generation.** One grade-2 chunk is absent from the dense top 30.
  The other sits at rank 19, which is a ranking failure.
- **Hybrid ranks 1–2 are judged irrelevant.** They are threads-intro c0010 and c0009 (grade 0), chunks
  both systems rank mid-list (dense 7 and 11, BM25 6 and 5).

### q020: "speed up a CPU-heavy loop … 10 threads … need locks?"

| Judged relevant chunk | Grade | Dense rank | BM25 rank | Hybrid rank |
| --- | --- | --- | --- | --- |
| pthreads-sync c0006 | 2 | 21 | 1 | **6** |
| threads-intro c0003 | 1 | 16 | 4 | **5** |
| pthreads-sync c0005 | 1 | 24 | 8 | **9** |
| pthreads-sync c0007, threads c0003 | 1 | >30 | >30 | >30 |

Per-system nDCG@10: dense 0.000, BM25 0.695, hybrid 0.355.

- **BM25 places the grade-2 chunk at rank 1.** It shares 18 distinct query tokens with the query.
- **Hybrid lifts all three found relevant chunks into the top 10.** This removes the dense top-10 failure.
- **The top 4 is still "locks" material, all judged 0.** It holds three Locks-chapter chunks (two of them
  ranked 2–3 by dense) and a practice problem that both systems put in their top 7.
- **This is a ranking failure for dense, not a candidate failure.** The relevant chunks sit at ranks 16–24.
  Hybrid repairs it only partly.

### q091: "How can the atomic swap instruction be used to implement mutual exclusion?"

| Judged relevant chunk | Grade | Dense rank | BM25 rank | Hybrid rank |
| --- | --- | --- | --- | --- |
| SUMSEM c0024 (background) | 1 | 3 | 1 | **2** |
| ps-concurrency c0023 | 2 | 9 | 5 | **5** |
| VIT 975bc607 c0017 "Solution using swap" | 2 | 11 | >30 | >30 |
| VIT 3f6ce962 c0019 "Solution using Swap" | 2 | 15 | >30 | >30 |
| VIT 3f6ce962 c0018 "Swap Instruction" | 1 | 13 | 21 | 10 |

Per-system nDCG@10: dense 0.173, BM25 0.278, hybrid 0.265.

- **Hybrid brings a grade-2 chunk into the top 5.** That chunk is ps-concurrency c0023.
- **The two short VIT "Solution using swap" code slides fall out of the hybrid top 30.** BM25 does not rank
  them, because their mutual exclusion is written in code, not in the query's words. Their dense ranks
  (11 and 15) give an RRF score too low on its own.
- **Rank 1 is unchanged in all three systems.** It is threads-bugs c0014, OSTEP deadlock prevention,
  judged 0.
- **This remains a ranking problem.** Every relevant chunk is a dense candidate, but none reaches rank 1.

### Query-type and subtopic groups (nDCG@10; Dense / BM25 / Hybrid)

| Group (queries) | Dense | BM25 | Hybrid | Hybrid unjudged @10 (mean) |
| --- | --- | --- | --- | --- |
| Code queries (13) | 0.611 | 0.628 | 0.634 | — |
| Mechanism queries (16) | 0.631 | 0.517 | 0.653 | — |
| Classical problems (10) | 0.755 | 0.722 | 0.815 | — |
| Conceptual (26) | 0.779 | 0.608 | 0.747 | — |
| Comparative (11) | 0.725 | 0.608 | 0.778 | — |
| Scenario (11) | 0.748 | 0.791 | 0.806 | — |
| Algorithm (12) | 0.656 | 0.633 | 0.694 | — |
| Subtopic Semaphores (16) | 0.694 | 0.548 | 0.702 | 1.19 |
| Subtopic Thread API: Pthreads / Creation / Join (9) | 0.551 | 0.660 | 0.641 | 1.11 |
| Subtopic Condition Variables (19) | 0.687 | 0.569 | 0.703 | 1.47 |
| Subtopics Classical: P-C / R-W / Dining (13) | 0.717 | 0.732 | 0.767 | 0.15 |

Observations:

- **Thread-API queries are dense's weakest group.** Lexical matching on identifiers such as
  `pthread_create` helps there. BM25 leads, and hybrid recovers most of BM25's gain.
- **Conceptual queries are the one query type where hybrid trails dense** (0.747 vs 0.779). BM25 adds
  OSTEP "Questions"/homework chunks and reference lists that share question words with the query.
  - Homework/questions chunks in the top 10: dense 7, hybrid 19.
  - Reference-list chunks in the top 10: dense 7, hybrid 11.
  - All of these that were judged are grade 0.
- **Hybrid's largest losses against dense** are on q092 (monitors), q008 (thread return value), q059
  (semaphore mistakes), q046 (cond_wait mutex) and q027 (lock basics). On each, BM25's own nDCG@10 is
  ≤ 0.13, so the BM25 list drags good dense results down.
  - q008 is hybrid's only top-5 failure. Dense has a relevant chunk in its top 5 there.
- **Duplicates.** Queries with duplicate content in the top 10: dense 4, BM25 7, hybrid 5.
- **Candidate sources of the hybrid top 10.** Over the 990 hybrid top-10 slots:

  | Chunk was in the top 10 of | Slots |
  | --- | --- |
  | both dense and BM25 | 413 |
  | dense only | 224 |
  | BM25 only | 199 |
  | neither (fusion of mid ranks) | 154 |

## H. Interactive tutor architecture

`src/tutor/controller.py`. Status: **PARTIAL**. The logic is implemented and tested. Text generation is
not connected.

```
Student question
  → retrieval (top 5; CLI uses the E2 hybrid retriever — provisional choice)
  → DIAGNOSE: one probing question, explicitly not the answer
  → student reply → ANALYSE (LLM returns JSON {level: solid|partial|misconception|unclear, gap})
       solid         → CHECK: formative check question on a new situation
       otherwise     → EXPLAIN: targeted explanation of the gap + example / counterexample + check question
  → student reply → ANALYSE
       solid         → DONE (move on)
       otherwise     → EXPLAIN again (≤ max_rounds = 2), then ANSWER: full grounded answer → DONE
```

| Element | Status |
| --- | --- |
| State machine, stage transitions, bounded remediation loop | IMPLEMENTED (tests: `tests/test_tutor_assessment.py`) |
| Grounding: every prompt carries the retrieved chunks as [S1]…[Sn] with file, page/slide, section | IMPLEMENTED |
| Source provenance returned with every tutor turn (chunk_id, filename, location, section) | IMPLEMENTED |
| Stage prompts (diagnose / analyse / explain + example / check / answer) | IMPLEMENTED; not yet tried with a real model |
| Robust parsing of the understanding analysis (malformed → "unclear" → explanation) | IMPLEMENTED |
| LLM backend | NOT IMPLEMENTED. The controller takes any `llm(prompt) -> str`. Choosing a model is Phase 4 and needs approval. |
| Quality of diagnosis, explanations and examples; faithfulness to sources | NOT EVALUATED |
| Learner model across sessions, topic sequencing, frontend | PLANNED |

Demo (no LLM needed): `python3 -m src.tutor.controller "Why does pthread_cond_wait take a mutex?"`. It prints
the grounded DIAGNOSE prompt the tutor would send, with its cited sources.

## I. Pre-test / post-test evaluation methodology

Status: **framework only**. No participant data exists, and no results are reported.

- **Learning objectives.** `data/assessment/learning_objectives.json` defines 8 objectives:
  - LO1: threads fundamentals
  - LO2: thread APIs
  - LO3: race conditions
  - LO4: locks / mutexes
  - LO5: semaphores
  - LO6: condition variables
  - LO7: classical synchronization problems
  - LO8: concurrency bugs

  Each objective is mapped to corpus subtopic labels.
- **Item bank.** `data/assessment/question_bank_draft.json` is a DRAFT of 16 items.
  - Each objective has one pre item and one post item. These are parallel forms: the same concept with a
    different surface.
  - Every item records its topic, objective, difficulty (the author's estimate), question type
    (mcq / short_answer / code_reasoning), expected concept, max score, answer key or rubric, and
    grounding chunk IDs. The grounding IDs come from v1.1 grade-2 judgments and are checked to exist.
  - Open items: instructor review, piloting, difficulty calibration, and a parallel-form equivalence check.
- **Protocol (planned).**
  1. Pre-test (form "pre").
  2. Tutoring session on the objectives.
  3. Post-test (form "post").
  4. Optionally, a control condition, for example reading the same retrieved material without the tutor
     dialogue.
- **Analysis.** `src/assessment/learning_gain.py`. It is implemented and tested on synthetic inputs only.

  | Measure | Definition |
  | --- | --- |
  | Score | % of max points |
  | Absolute gain | post − pre |
  | Normalized gain | g = (post − pre) / (100 − pre), Hake 1998; undefined at pre = 100 |
  | Class gain | ⟨g⟩ from the class means, plus the mean of individual g |

  It reports these per condition and per objective (concept-wise improvement).

## J. Current limitations

1. **Pooling bias.** v1.1 judgments come from the dense top 20 only.
   - Hybrid has 108 unjudged top-10 results; BM25 has 418.
   - The BM25 and hybrid metrics are lower bounds.
   - The dense-vs-BM25 ordering is unresolved.
2. **Single annotator.** One annotator wrote all benchmark judgments and the draft test items. There is no
   agreement measure.
3. **One fusion configuration.** E2 used RRF with k = 60 and depth 50 at equal weights. These values were
   not tuned, and tuning them on v1.1 would overfit the test set.
4. **Distractors entering through BM25.** BM25 brings homework/"Questions" sections and reference lists into
   the hybrid top 10. Hybrid also loses to dense on 32 queries.
5. **q091 code slides.** Short code-only slides (the VIT swap solutions) are missed by BM25 and ranked
   mid-list by dense.
6. **No text generation.** The tutor cannot yet hold a real conversation. No LLM is connected, and there is
   no answer-faithfulness evaluation.
7. **No educational evidence yet.** The item bank is an unvalidated draft. No student data exists.
8. **Environment.** `python3` on this machine now resolves to miniconda, which lacks the project's
   dependencies. Use `/usr/local/bin/python3` (3.13.7), the interpreter the baselines were built with.

## K. Future work (each item needs approval)

1. **v1.2 judgments.** Pool the unjudged BM25 and hybrid top-10 results (about 418 and 108 pairs, with
   overlap) into a v1.2 benchmark, so the three systems can be compared without the pooling bias. This is
   the prerequisite for any further retrieval claim.
2. **Phase 4: connect an LLM to the tutor controller.**
   - Choose the model.
   - Run a small faithfulness and pedagogy check of DIAGNOSE / EXPLAIN / CHECK outputs against the cited
     chunks.
3. **Validate the assessment.**
   - Instructor review of the item bank.
   - A pilot to calibrate difficulty and check parallel-form equivalence.
   - Ethics/consent if real students take part.
4. **Later retrieval experiments.** Each would be one controlled experiment:
   - filtering or down-weighting homework/reference-list sections;
   - reranking;
   - duplicate collapsing.
