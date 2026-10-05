# Retrieval comparison — BM25 E1 (A) vs Hybrid E2 (B)

Same benchmark, corpus, queries, judgments and metric definitions (checked). Differences are B − A. Measurements only; no winner is declared.

## Configuration

- **BM25 E1**: bm25 (E1 lexical baseline), top_k=20; benchmark v1.1 `bfbbd033021a…`; corpus `90d1e88ef552…`
- **Hybrid E2**: hybrid dense + bm25, reciprocal rank fusion (E2), top_k=20; benchmark v1.1 `bfbbd033021a…`; corpus `90d1e88ef552…`

## Overall (macro-averaged over queries)

| Metric | BM25 E1 | Hybrid E2 | Difference |
| --- | --- | --- | --- |
| precision@5 | 0.517 | 0.632 | +0.115 |
| precision@10 | 0.378 | 0.470 | +0.092 |
| recall@5 | 0.401 | 0.471 | +0.070 |
| recall@10 | 0.543 | 0.645 | +0.103 |
| mrr@5 | 0.852 | 0.921 | +0.070 |
| ndcg@5 | 0.629 | 0.725 | +0.096 |
| ndcg@10 | 0.631 | 0.727 | +0.097 |
| map@5 | 0.361 | 0.433 | +0.072 |

| Queries with a relevant result in top K (of 99) | BM25 E1 | Hybrid E2 | Difference |
| --- | --- | --- | --- |
| top 1 | 79 | 86 | +7 |
| top 3 | 89 | 97 | +8 |
| top 5 | 92 | 98 | +6 |
| top 10 | 96 | 99 | +3 |
| top 20 | 99 | 99 | +0 |

## Judgment coverage

Unjudged results count as non-relevant. Benchmark v1.1 was pooled from the dense system's top 20, so unjudged results fall almost entirely on the other system and its scores are lower bounds.

| Unjudged results | BM25 E1 | Hybrid E2 |
| --- | --- | --- |
| top 5 | 152 of 495 (30.7%) | 11 of 495 (2.2%) |
| top 10 | 418 of 990 (42.2%) | 108 of 990 (10.9%) |
| top 20 | 1118 of 1980 (56.5%) | 667 of 1980 (33.7%) |

Queries where Hybrid E2 has at least one unjudged result in the top 5: 8.

### Judged-only (condensed-list) metrics, supplementary

Unjudged results are dropped from each top-20 list before scoring with the same metric functions. This removes the pooling penalty but also lets a system skip past chunks nobody judged, so it favours the system with more unjudged results. Read it together with the main table, not instead of it.

| Metric (judged only) | BM25 E1 | Hybrid E2 | Difference |
| --- | --- | --- | --- |
| precision@5 | 0.659 | 0.646 | -0.012 |
| ndcg@10 | 0.731 | 0.751 | +0.020 |
| map@5 | 0.453 | 0.439 | -0.014 |

## By topic (BM25 E1 / Hybrid E2)

| Topic | Queries | precision@5 | precision@10 | recall@5 | recall@10 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threads | 21 | 0.505 / 0.562 | 0.367 / 0.448 | 0.434 / 0.447 | 0.581 / 0.688 | 0.873 / 0.883 | 0.654 / 0.690 | 0.681 / 0.737 | 0.413 / 0.422 |
| Synchronisation | 78 | 0.521 / 0.651 | 0.381 / 0.476 | 0.392 / 0.477 | 0.532 / 0.634 | 0.846 / 0.932 | 0.622 / 0.734 | 0.617 / 0.725 | 0.347 / 0.435 |

## By difficulty (BM25 E1 / Hybrid E2)

| Difficulty | Queries | precision@5 | precision@10 | recall@5 | recall@10 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| easy | 23 | 0.557 / 0.713 | 0.430 / 0.557 | 0.367 / 0.445 | 0.517 / 0.638 | 0.853 / 0.978 | 0.634 / 0.763 | 0.618 / 0.756 | 0.333 / 0.428 |
| medium | 48 | 0.521 / 0.675 | 0.388 / 0.483 | 0.384 / 0.481 | 0.530 / 0.644 | 0.823 / 0.924 | 0.601 / 0.733 | 0.613 / 0.723 | 0.350 / 0.434 |
| hard | 28 | 0.479 / 0.493 | 0.318 / 0.375 | 0.456 / 0.474 | 0.585 / 0.654 | 0.900 / 0.870 | 0.672 / 0.679 | 0.671 / 0.712 | 0.403 / 0.434 |

## By query type (BM25 E1 / Hybrid E2)

| Query type | Queries | precision@5 | precision@10 | recall@5 | recall@10 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| conceptual | 26 | 0.500 / 0.685 | 0.346 / 0.477 | 0.386 / 0.492 | 0.506 / 0.647 | 0.863 / 0.981 | 0.622 / 0.755 | 0.608 / 0.747 | 0.362 / 0.477 |
| comparative | 11 | 0.509 / 0.673 | 0.409 / 0.500 | 0.398 / 0.456 | 0.550 / 0.634 | 0.655 / 0.939 | 0.577 / 0.793 | 0.608 / 0.778 | 0.365 / 0.435 |
| mechanism | 16 | 0.537 / 0.700 | 0.400 / 0.544 | 0.291 / 0.374 | 0.422 / 0.568 | 0.729 / 0.875 | 0.530 / 0.668 | 0.517 / 0.653 | 0.253 / 0.332 |
| code | 13 | 0.492 / 0.462 | 0.300 / 0.346 | 0.414 / 0.398 | 0.486 / 0.565 | 0.885 / 0.821 | 0.652 / 0.606 | 0.628 / 0.634 | 0.374 / 0.342 |
| scenario | 11 | 0.436 / 0.473 | 0.318 / 0.345 | 0.510 / 0.593 | 0.706 / 0.793 | 1.000 / 0.927 | 0.753 / 0.748 | 0.791 / 0.806 | 0.488 / 0.539 |
| algorithm | 12 | 0.467 / 0.600 | 0.350 / 0.392 | 0.454 / 0.554 | 0.622 / 0.648 | 0.917 / 0.917 | 0.587 / 0.723 | 0.633 / 0.694 | 0.373 / 0.488 |
| classical | 10 | 0.720 / 0.780 | 0.590 / 0.690 | 0.415 / 0.446 | 0.621 / 0.716 | 0.950 / 0.950 | 0.749 / 0.792 | 0.722 / 0.815 | 0.352 / 0.411 |

## Failures (no relevant chunk within the cutoff)

| Cutoff | BM25 E1 | Hybrid E2 |
| --- | --- | --- |
| top 5 | q002, q008, q046, q055, q059, q060, q081 | q008 |
| top 10 | q008, q046, q060 | none |
| top 20 | none | none |

## Overlap

- Mean shared chunks per query: top 10 6.18, top 20 12.31
- Judged-relevant chunks in the top 20 of only one system: BM25 E1 only 13, Hybrid E2 only 111, both 471
- Queries with a relevant chunk in the top 5 for Hybrid E2 but not BM25 E1: q002, q046, q055, q059, q060, q081; the reverse: none

## Result categories in the top 5 / top 10

Counts of retrieved results over all queries. Top 10 split: relevant (grade ≥ 1) / judged 0 / unjudged.

| Category | BM25 E1 top 5 | BM25 E1 top 10 (rel / 0 / unjudged) | Hybrid E2 top 5 | Hybrid E2 top 10 (rel / 0 / unjudged) |
| --- | --- | --- | --- | --- |
| reference list (section 'References') | 5 | 12 (0 / 3 / 9) | 1 | 11 (0 / 6 / 5) |
| homework / questions section | 34 | 73 (0 / 8 / 65) | 7 | 19 (0 / 13 / 6) |
| practice problems (document_type) | 54 | 103 (38 / 22 / 43) | 57 | 118 (47 / 57 / 14) |
| lecture15 / Semaphore-copy chunk | 5 | 16 (8 / 0 / 8) | 5 | 14 (12 / 0 / 2) |

Queries with chunks from both lecture15 and Semaphore-copy in the top 10: BM25 E1 q053, q059, q063, q064, q066, q082, q096; Hybrid E2 q052, q053, q055, q059, q064

## Deep-pool queries (top 30)

Grades: 2 / 1 relevant, 0 judged not relevant, — unjudged.

### q009 (hard, code): I pass &i from my for loop to pthread_create and the threads print the wrong numbers. Why?

| Judged relevant chunk | Grade | Rank BM25 E1 | Rank Hybrid E2 |
| --- | --- | --- | --- |
| ps-concurrency-381f1b77::c0019 | 2 | 2 | 3 |
| pthreads-sync-9017cfef::c0003 | 2 | 1 | 11 |
| threads-api-8ce54688::c0003 | 1 | >30 | >30 |
| threads-api-8ce54688::c0018 | 1 | 26 | 17 |

| Rank | BM25 E1 chunk | Grade | Hybrid E2 chunk | Grade | Hybrid E2 section |
| --- | --- | --- | --- | --- | --- |
| 1 | pthreads-sync-9017cfef::c0003 | 2 | threads-intro-c1df7202::c0010 | 0 | 26 Concurrency: An Introduction > 26.3 Why It Gets Worse: Sh |
| 2 | ps-concurrency-381f1b77::c0019 | 2 | threads-intro-c1df7202::c0009 | 0 | 26 Concurrency: An Introduction > 26.3 Why It Gets Worse: Sh |
| 3 | pthreads-sync-9017cfef::c0008 | — | ps-concurrency-381f1b77::c0019 | 2 | Practice Problems: Concurrency > 20. Describe the output of  |
| 4 | pthreads-sync-9017cfef::c0004 | 0 | threads-api-8ce54688::c0001 | 0 | 27 Interlude: Thread API > 27.1 Thread Creation |
| 5 | threads-intro-c1df7202::c0009 | 0 | threads-api-8ce54688::c0005 | 0 | 27 Interlude: Thread API > 27.2 Thread Completion |
| 6 | threads-intro-c1df7202::c0010 | 0 | pthreads-sync-9017cfef::c0004 | 0 | Lab: Pthreads Synchronization > Warm-up exercises > 3. You a |
| 7 | pthreads-sync-9017cfef::c0005 | — | threads-api-8ce54688::c0004 | 0 | 27 Interlude: Thread API > 27.2 Thread Completion |
| 8 | thread-synchroniza…e871e8ad::c0008 | — | threads-api-8ce54688::c0008 | 0 | 27 Interlude: Thread API > 27.2 Thread Completion |
| 9 | threads-intro-c1df7202::c0027 | — | fallsem2025-26-vl-…170d2f74::c0009 | 0 | Why Pthreads |
| 10 | threads-cv-3156a56b::c0009 | — | threads-4d568260::c0004 | 0 | POSIX threads |
| 11 | threads-intro-c1df7202::c0026 | — | pthreads-sync-9017cfef::c0003 | 2 | Lab: Pthreads Synchronization > Warm-up exercises > 2. Write |
| 12 | threads-locks-cb67d3bd::c0028 | — | threads-api-8ce54688::c0002 | 0 | 27 Interlude: Thread API > 27.1 Thread Creation |
| 13 | threads-sema-d8fb1c00::c0015 | — | threads-cv-3156a56b::c0018 | — | 30 Condition Variables > The Single Buffer Producer/Consumer |
| 14 | sumsem2025-26-vl-b…02c11114::c0021 | — | threads-api-8ce54688::c0007 | 0 | 27 Interlude: Thread API > 27.2 Thread Completion |
| 15 | threads-api-8ce54688::c0002 | 0 | thread-synchroniza…e871e8ad::c0009 | 0 | 10. Shared Resource Pool |
| 16 | threads-intro-c1df7202::c0003 | — | pthreads-sync-9017cfef::c0009 | 0 | Lab: Pthreads Synchronization > Part B: Master-Worker Thread |
| 17 | threads-cv-3156a56b::c0018 | — | threads-api-8ce54688::c0018 | 1 | 27 Interlude: Thread API > 27.6 Summary |
| 18 | fallsem2025-26-vl-…170d2f74::c0009 | 0 | threads-cv-3156a56b::c0014 | 0 | 30 Condition Variables > A Broken Solution |
| 19 | fallsem2025-26-vl-…fd173a9e::c0006 | — | pthreads-sync-9017cfef::c0010 | — | Lab: Pthreads Synchronization > Part B: Master-Worker Thread |
| 20 | lecture12-4288650c::c0003 | — | lecture12-4288650c::c0005 | 0 | Threads with shared data: what happens? |
| 21 | threads-api-8ce54688::c0005 | 0 | pthreads-sync-9017cfef::c0008 | — | Lab: Pthreads Synchronization > Part B: Master-Worker Thread |
| 22 | lecture14-a8135675::c0002 | — | pthreads-sync-9017cfef::c0005 | — | Lab: Pthreads Synchronization > Part A: Speeding up computat |
| 23 | thread-synchroniza…e871e8ad::c0009 | 0 | thread-synchroniza…e871e8ad::c0008 | — | 9. Traffic Intersection Synchronization |
| 24 | threads-api-8ce54688::c0001 | 0 | threads-intro-c1df7202::c0005 | 0 | 26 Concurrency: An Introduction > 26.2 An Example: Thread Cr |
| 25 | ps-concurrency-381f1b77::c0048 | — | threads-api-8ce54688::c0017 | 0 | 27 Interlude: Thread API > 27.6 Summary |
| 26 | threads-api-8ce54688::c0018 | 1 | threads-intro-c1df7202::c0027 | — | 26 Concurrency: An Introduction > Questions |
| 27 | threads-cv-3156a56b::c0010 | — | pthreads-sync-9017cfef::c0001 | 0 | Lab: Pthreads Synchronization > Before you begin |
| 28 | threads-api-8ce54688::c0007 | 0 | threads-cv-3156a56b::c0009 | — | 30 Condition Variables > 30.2 The Producer/Consumer (Bounded |
| 29 | threads-api-8ce54688::c0004 | 0 | threads-intro-c1df7202::c0026 | — | 26 Concurrency: An Introduction > Questions |
| 30 | ps-concurrency-381f1b77::c0047 | — | threads-locks-cb67d3bd::c0028 | — | 28 Locks > 28.14 Using Queues: Sleeping Instead Of Spinning |

### q020 (hard, scenario): How would you speed up a CPU-heavy loop by splitting it across 10 threads, and do the threads need locks if each writes a different part of the array?

| Judged relevant chunk | Grade | Rank BM25 E1 | Rank Hybrid E2 |
| --- | --- | --- | --- |
| pthreads-sync-9017cfef::c0006 | 2 | 1 | 6 |
| pthreads-sync-9017cfef::c0005 | 1 | 8 | 9 |
| pthreads-sync-9017cfef::c0007 | 1 | >30 | >30 |
| threads-4d568260::c0003 | 1 | >30 | >30 |
| threads-intro-c1df7202::c0003 | 1 | 4 | 5 |

| Rank | BM25 E1 chunk | Grade | Hybrid E2 chunk | Grade | Hybrid E2 section |
| --- | --- | --- | --- | --- | --- |
| 1 | pthreads-sync-9017cfef::c0006 | 2 | threads-locks-cb67d3bd::c0016 | 0 | 28 Locks > 28.8 Evaluating Spin Locks |
| 2 | threads-locks-cb67d3bd::c0039 | 0 | threads-locks-cb67d3bd::c0023 | 0 | 28 Locks > 28.13 A Simple Approach: Just Yield, Baby |
| 3 | pthreads-sync-9017cfef::c0002 | — | ps-concurrency-381f1b77::c0022 | 0 | Practice Problems: Concurrency > 23. Consider a multithreade |
| 4 | threads-intro-c1df7202::c0003 | 1 | threads-locks-cb67d3bd::c0039 | 0 | 28 Locks > Questions |
| 5 | threads-cv-3156a56b::c0026 | — | threads-intro-c1df7202::c0003 | 1 | 26 Concurrency: An Introduction > 26.1 Why Use Threads? |
| 6 | threads-locks-cb67d3bd::c0016 | 0 | pthreads-sync-9017cfef::c0006 | 2 | Lab: Pthreads Synchronization > Part A: Speeding up computat |
| 7 | ps-concurrency-381f1b77::c0022 | 0 | pthreads-sync-9017cfef::c0002 | — | Lab: Pthreads Synchronization > Warm-up exercises > 1. Write |
| 8 | pthreads-sync-9017cfef::c0005 | 1 | pthreads-sync-9017cfef::c0004 | 0 | Lab: Pthreads Synchronization > Warm-up exercises > 3. You a |
| 9 | threads-4d568260::c0001 | — | pthreads-sync-9017cfef::c0005 | 1 | Lab: Pthreads Synchronization > Part A: Speeding up computat |
| 10 | threads-locks-cb67d3bd::c0023 | 0 | threads-locks-cb67d3bd::c0038 | 0 | 28 Locks > Questions |
| 11 | threads-intro-c1df7202::c0009 | — | threads-locks-cb67d3bd::c0022 | 0 | 28 Locks > 28.12 Too Much Spinning: What Now? |
| 12 | threads-locks-cb67d3bd::c0038 | 0 | threads-locks-cb67d3bd::c0004 | 0 | 28 Locks > 28.4 Evaluating Locks |
| 13 | threads-bugs-e5dff53b::c0026 | — | threads-api-8ce54688::c0017 | 0 | 27 Interlude: Thread API > 27.6 Summary |
| 14 | threads-bugs-e5dff53b::c0018 | — | threads-sema-d8fb1c00::c0025 | 0 | 31 Semaphores > 31.7 Thread Throttling |
| 15 | ps-concurrency-381f1b77::c0048 | — | threads-locks-cb67d3bd::c0006 | — | 28 Locks > 28.5 Controlling Interrupts |
| 16 | threads-intro-c1df7202::c0028 | — | threads-locks-cb67d3bd::c0029 | — | 28 Locks > 28.15 Different OS, Different Support |
| 17 | pthreads-sync-9017cfef::c0008 | — | pthreads-sync-9017cfef::c0013 | — | Lab: Pthreads Synchronization > Part C: Reader-Writer Locks |
| 18 | ps-concurrency-381f1b77::c0053 | — | sumsem2025-26-vl-b…02c11114::c0050 | — | Solaris Synchronization |
| 19 | threads-api-8ce54688::c0017 | 0 | threads-locks-cb67d3bd::c0024 | 0 | 28 Locks > 28.14 Using Queues: Sleeping Instead Of Spinning |
| 20 | ps-concurrency-381f1b77::c0037 | — | threads-cv-3156a56b::c0026 | — | 30 Condition Variables > Questions |
| 21 | threads-locks-cb67d3bd::c0004 | 0 | threads-locks-cb67d3bd::c0009 | 0 | 28 Locks > 28.6 A Failed Attempt: Just Using Loads/Stores >  |
| 22 | threads-api-8ce54688::c0015 | — | ps-concurrency-381f1b77::c0018 | 0 | Practice Problems: Concurrency > 19. Multiple threads of a p |
| 23 | threads-sema-d8fb1c00::c0002 | — | threads-locks-cb67d3bd::c0008 | 0 | 28 Locks > 28.6 A Failed Attempt: Just Using Loads/Stores |
| 24 | ps-concurrency-381f1b77::c0049 | — | threads-4d568260::c0001 | — | What are threads? |
| 25 | threads-intro-c1df7202::c0002 | — | threads-locks-cb67d3bd::c0000 | 0 | 28 Locks |
| 26 | threads-intro-c1df7202::c0017 | — | pthreads-sync-9017cfef::c0011 | 0 | Lab: Pthreads Synchronization > Part C: Reader-Writer Locks |
| 27 | threads-locks-cb67d3bd::c0006 | — | threads-intro-c1df7202::c0009 | — | 26 Concurrency: An Introduction > 26.3 Why It Gets Worse: Sh |
| 28 | threads-sema-d8fb1c00::c0025 | 0 | threads-api-8ce54688::c0009 | 0 | 27 Interlude: Thread API > 27.3 Locks |
| 29 | pthreads-sync-9017cfef::c0004 | 0 | threads-bugs-e5dff53b::c0026 | — | 32 Common Concurrency Problems > Questions |
| 30 | pthreads-sync-9017cfef::c0013 | — | threads-bugs-e5dff53b::c0018 | — | 32 Common Concurrency Problems > Deadlock Avoidance via Sche |

### q091 (medium, algorithm): How can the atomic swap instruction be used to implement mutual exclusion?

| Judged relevant chunk | Grade | Rank BM25 E1 | Rank Hybrid E2 |
| --- | --- | --- | --- |
| fallsem2025-26-vl-…3f6ce962::c0019 | 2 | >30 | >30 |
| fallsem2025-26-vl-…975bc607::c0017 | 2 | >30 | >30 |
| ps-concurrency-381f1b77::c0023 | 2 | 5 | 5 |
| fallsem2025-26-vl-…3f6ce962::c0015 | 1 | >30 | 25 |
| fallsem2025-26-vl-…3f6ce962::c0018 | 1 | 21 | 10 |
| fallsem2025-26-vl-…975bc607::c0013 | 1 | 18 | 18 |
| fallsem2025-26-vl-…975bc607::c0016 | 1 | 22 | 14 |
| sumsem2025-26-vl-b…02c11114::c0024 | 1 | 1 | 2 |
| threads-locks-cb67d3bd::c0010 | 1 | >30 | 22 |

| Rank | BM25 E1 chunk | Grade | Hybrid E2 chunk | Grade | Hybrid E2 section |
| --- | --- | --- | --- | --- | --- |
| 1 | sumsem2025-26-vl-b…02c11114::c0024 | 1 | threads-bugs-e5dff53b::c0014 | 0 | 32 Common Concurrency Problems > Prevention > Mutual Exclusi |
| 2 | threads-bugs-e5dff53b::c0014 | 0 | sumsem2025-26-vl-b…02c11114::c0024 | 1 | Test and Set |
| 3 | sumsem2025-26-vl-b…02c11114::c0025 | 0 | sumsem2025-26-vl-b…02c11114::c0025 | 0 | compare and swap() instruction (CAS) |
| 4 | fallsem2025-26-vl-…975bc607::c0001 | — | threads-locks-cb67d3bd::c0005 | 0 | 28 Locks > 28.5 Controlling Interrupts |
| 5 | ps-concurrency-381f1b77::c0023 | 2 | ps-concurrency-381f1b77::c0023 | 2 | Practice Problems: Concurrency > 24. Consider the atomic har |
| 6 | threads-locks-cb67d3bd::c0005 | 0 | ps-concurrency-381f1b77::c0020 | 0 | Practice Problems: Concurrency > 21. Recall that the atomic  |
| 7 | fallsem2025-26-vl-…3f6ce962::c0021 | — | lecture13-0af66874::c0006 | 0 | Alternative to spinning |
| 8 | lecture12-4288650c::c0006 | — | threads-locks-cb67d3bd::c0017 | 0 | 28 Locks > 28.9 Compare-And-Swap |
| 9 | lecture13-0af66874::c0006 | 0 | threads-sema-d8fb1c00::c0015 | 0 | 31 Semaphores > A Solution: Adding Mutual Exclusion |
| 10 | threads-locks-cb67d3bd::c0003 | — | fallsem2025-26-vl-…3f6ce962::c0018 | 1 | Swap Instruction |
| 11 | ps-concurrency-381f1b77::c0020 | 0 | threads-locks-cb67d3bd::c0009 | 0 | 28 Locks > 28.6 A Failed Attempt: Just Using Loads/Stores >  |
| 12 | threads-locks-cb67d3bd::c0017 | 0 | threads-intro-c1df7202::c0019 | 0 | 26 Concurrency: An Introduction > 26.5 The Wish For Atomicit |
| 13 | fallsem2025-26-vl-…fd173a9e::c0008 | — | threads-intro-c1df7202::c0022 | 0 | 26 Concurrency: An Introduction > References |
| 14 | threads-4d568260::c0008 | — | fallsem2025-26-vl-…975bc607::c0016 | 1 | Swap Instruction |
| 15 | lecture13-0af66874::c0002 | — | lecture12-4288650c::c0006 | — | Race conditions and synchronization |
| 16 | sumsem2025-26-vl-b…02c11114::c0036 | — | fallsem2025-26-vl-…975bc607::c0008 | 0 | Correctness of the Software Solution |
| 17 | threads-locks-cb67d3bd::c0039 | — | lecture13-0af66874::c0004 | 0 | Solution: Hardware atomic instructions |
| 18 | fallsem2025-26-vl-…975bc607::c0013 | 1 | fallsem2025-26-vl-…975bc607::c0013 | 1 | Hardware Instructions |
| 19 | threads-intro-c1df7202::c0019 | 0 | threads-4d568260::c0008 | — | Race conditions, critical sections |
| 20 | fallsem2025-26-vl-…975bc607::c0018 | — | sumsem2025-26-vl-b…02c11114::c0036 | — | Dining-Philosophers Problem Algorithm |
| 21 | fallsem2025-26-vl-…3f6ce962::c0018 | 1 | threads-locks-cb67d3bd::c0014 | 0 | 28 Locks > 28.7 Building Working Spin Locks with Test-And-Se |
| 22 | fallsem2025-26-vl-…975bc607::c0016 | 1 | threads-locks-cb67d3bd::c0010 | 1 | 28 Locks > 28.7 Building Working Spin Locks with Test-And-Se |
| 23 | lecture13-0af66874::c0004 | 0 | threads-locks-cb67d3bd::c0039 | — | 28 Locks > Questions |
| 24 | threads-intro-c1df7202::c0022 | 0 | threads-intro-c1df7202::c0017 | 0 | 26 Concurrency: An Introduction > 26.4 The Heart Of The Prob |
| 25 | threads-sema-d8fb1c00::c0021 | — | fallsem2025-26-vl-…3f6ce962::c0015 | 1 | Synchronization Hardware |
| 26 | threads-locks-cb67d3bd::c0002 | — | sumsem2025-26-vl-b…02c11114::c0001 | — | Objectives |
| 27 | threads-locks-cb67d3bd::c0014 | 0 | threads-intro-c1df7202::c0020 | 0 | 26 Concurrency: An Introduction > 26.6 One More Problem: Wai |
| 28 | sumsem2025-26-vl-b…02c11114::c0001 | — | lecture14-a8135675::c0000 | — | Another type of sychronization |
| 29 | threads-locks-cb67d3bd::c0009 | 0 | fallsem2025-26-vl-…975bc607::c0001 | — | Objectives |
| 30 | ps-concurrency-381f1b77::c0030 | — | fallsem2025-26-vl-…3f6ce962::c0021 | — | Semaphore as General Synchronization Tool |

## Per query

| Query | Type | Difficulty | First relevant rank BM25 E1 | First relevant rank Hybrid E2 | nDCG@10 BM25 E1 | nDCG@10 Hybrid E2 | Unjudged@10 Hybrid E2 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| q001 | conceptual | easy | 1 | 1 | 0.353 | 0.501 | 4 |
| q002 | comparative | medium | 6 | 1 | 0.252 | 0.793 | 2 |
| q003 | conceptual | easy | 1 | 1 | 0.435 | 0.664 | 3 |
| q004 | comparative | easy | 1 | 1 | 0.908 | 0.908 | 0 |
| q005 | mechanism | medium | 1 | 1 | 0.776 | 0.783 | 0 |
| q006 | mechanism | easy | 1 | 1 | 0.557 | 0.663 | 2 |
| q007 | mechanism | easy | 3 | 1 | 0.537 | 0.905 | 1 |
| q008 | code | hard | 14 | 6 | 0.000 | 0.147 | 2 |
| q009 | code | hard | 1 | 3 | 0.778 | 0.239 | 0 |
| q010 | conceptual | medium | 1 | 1 | 0.928 | 0.922 | 1 |
| q011 | mechanism | medium | 1 | 1 | 0.839 | 0.909 | 0 |
| q012 | comparative | easy | 1 | 1 | 0.888 | 0.948 | 0 |
| q013 | scenario | medium | 1 | 1 | 0.735 | 0.865 | 0 |
| q014 | conceptual | easy | 1 | 1 | 0.739 | 0.789 | 6 |
| q015 | scenario | medium | 1 | 1 | 0.532 | 0.721 | 2 |
| q016 | conceptual | medium | 1 | 1 | 0.930 | 0.930 | 0 |
| q017 | conceptual | medium | 1 | 1 | 0.666 | 0.743 | 2 |
| q018 | conceptual | easy | 1 | 1 | 1.000 | 1.000 | 1 |
| q019 | mechanism | easy | 1 | 1 | 0.894 | 0.821 | 2 |
| q020 | scenario | hard | 1 | 5 | 0.695 | 0.355 | 1 |
| q021 | scenario | hard | 1 | 1 | 0.870 | 0.880 | 0 |
| q022 | conceptual | easy | 1 | 1 | 0.649 | 0.910 | 0 |
| q023 | mechanism | medium | 1 | 1 | 0.616 | 0.627 | 2 |
| q024 | conceptual | easy | 1 | 1 | 0.494 | 0.712 | 0 |
| q025 | conceptual | easy | 1 | 1 | 0.646 | 0.700 | 0 |
| q026 | conceptual | medium | 1 | 1 | 0.589 | 0.898 | 1 |
| q027 | mechanism | easy | 3 | 2 | 0.117 | 0.459 | 0 |
| q028 | code | medium | 1 | 1 | 0.722 | 0.840 | 2 |
| q029 | comparative | medium | 1 | 1 | 1.000 | 0.867 | 2 |
| q030 | conceptual | medium | 1 | 1 | 0.536 | 0.670 | 2 |
| q031 | algorithm | medium | 1 | 1 | 0.710 | 0.722 | 1 |
| q032 | algorithm | easy | 2 | 1 | 0.491 | 0.787 | 0 |
| q033 | algorithm | medium | 2 | 1 | 0.361 | 0.622 | 0 |
| q034 | algorithm | medium | 1 | 1 | 0.699 | 0.897 | 1 |
| q035 | algorithm | hard | 1 | 1 | 0.569 | 0.628 | 1 |
| q036 | algorithm | medium | 1 | 1 | 1.000 | 1.000 | 1 |
| q037 | algorithm | hard | 1 | 1 | 0.791 | 0.695 | 2 |
| q038 | conceptual | medium | 1 | 1 | 0.632 | 0.833 | 0 |
| q039 | comparative | medium | 1 | 1 | 0.591 | 0.607 | 1 |
| q040 | conceptual | hard | 1 | 1 | 0.584 | 0.811 | 1 |
| q041 | mechanism | hard | 1 | 1 | 0.880 | 0.935 | 1 |
| q042 | conceptual | medium | 1 | 1 | 0.979 | 0.695 | 3 |
| q043 | conceptual | medium | 1 | 1 | 0.733 | 0.728 | 2 |
| q044 | conceptual | easy | 4 | 1 | 0.126 | 0.577 | 3 |
| q045 | mechanism | easy | 1 | 1 | 0.497 | 0.569 | 1 |
| q046 | mechanism | medium | 14 | 1 | 0.000 | 0.283 | 4 |
| q047 | code | medium | 1 | 1 | 0.655 | 0.777 | 0 |
| q048 | conceptual | hard | 1 | 1 | 0.647 | 0.813 | 2 |
| q049 | comparative | medium | 2 | 1 | 0.564 | 0.824 | 1 |
| q050 | code | hard | 1 | 1 | 0.826 | 0.874 | 0 |
| q051 | mechanism | medium | 2 | 2 | 0.226 | 0.405 | 4 |
| q052 | mechanism | easy | 1 | 1 | 0.365 | 0.671 | 3 |
| q053 | comparative | easy | 1 | 1 | 0.982 | 0.923 | 0 |
| q054 | mechanism | medium | 1 | 1 | 0.532 | 0.689 | 0 |
| q055 | mechanism | medium | 7 | 2 | 0.108 | 0.372 | 3 |
| q056 | mechanism | medium | 1 | 1 | 0.918 | 0.921 | 0 |
| q057 | code | hard | 1 | 1 | 0.613 | 0.613 | 2 |
| q058 | scenario | medium | 1 | 1 | 0.760 | 0.907 | 3 |
| q059 | conceptual | medium | 6 | 2 | 0.127 | 0.395 | 1 |
| q060 | comparative | medium | 12 | 3 | 0.000 | 0.258 | 2 |
| q061 | comparative | hard | 5 | 1 | 0.233 | 0.754 | 2 |
| q062 | classical | easy | 1 | 1 | 0.878 | 0.869 | 0 |
| q063 | classical | medium | 1 | 1 | 0.931 | 0.967 | 0 |
| q064 | code | hard | 1 | 1 | 0.769 | 0.790 | 0 |
| q065 | classical | hard | 1 | 2 | 0.402 | 0.493 | 0 |
| q066 | classical | medium | 1 | 1 | 0.729 | 0.811 | 0 |
| q067 | classical | easy | 1 | 1 | 0.768 | 0.858 | 0 |
| q068 | classical | medium | 1 | 1 | 0.632 | 0.668 | 0 |
| q069 | classical | hard | 1 | 1 | 0.778 | 0.781 | 0 |
| q070 | code | hard | 2 | 1 | 0.539 | 0.716 | 2 |
| q071 | classical | easy | 1 | 1 | 0.780 | 0.863 | 0 |
| q072 | classical | medium | 1 | 1 | 0.694 | 0.843 | 0 |
| q073 | code | hard | 1 | 3 | 0.823 | 0.526 | 0 |
| q074 | conceptual | easy | 1 | 1 | 1.000 | 1.000 | 0 |
| q075 | mechanism | medium | 2 | 2 | 0.417 | 0.438 | 0 |
| q076 | scenario | medium | 1 | 1 | 0.822 | 0.826 | 1 |
| q077 | conceptual | hard | 1 | 1 | 0.605 | 0.732 | 1 |
| q078 | comparative | medium | 2 | 1 | 0.403 | 0.745 | 2 |
| q079 | comparative | medium | 1 | 1 | 0.871 | 0.933 | 0 |
| q080 | code | hard | 1 | 1 | 0.621 | 0.638 | 2 |
| q081 | conceptual | medium | 9 | 1 | 0.185 | 0.610 | 3 |
| q082 | scenario | hard | 1 | 1 | 1.000 | 1.000 | 2 |
| q083 | conceptual | medium | 1 | 1 | 0.786 | 0.776 | 0 |
| q084 | conceptual | medium | 1 | 1 | 0.615 | 0.876 | 0 |
| q085 | conceptual | medium | 1 | 1 | 0.706 | 0.859 | 1 |
| q086 | code | hard | 1 | 1 | 0.639 | 0.776 | 3 |
| q087 | algorithm | medium | 1 | 1 | 0.508 | 0.551 | 0 |
| q088 | algorithm | hard | 1 | 1 | 0.817 | 0.819 | 0 |
| q089 | algorithm | medium | 1 | 2 | 0.617 | 0.478 | 0 |
| q090 | algorithm | medium | 1 | 1 | 0.754 | 0.860 | 0 |
| q091 | algorithm | medium | 1 | 2 | 0.278 | 0.265 | 0 |
| q092 | conceptual | easy | 5 | 1 | 0.111 | 0.288 | 1 |
| q093 | scenario | medium | 1 | 1 | 0.778 | 0.682 | 1 |
| q094 | scenario | hard | 1 | 1 | 0.956 | 1.000 | 1 |
| q095 | scenario | hard | 1 | 1 | 0.753 | 0.840 | 2 |
| q096 | code | hard | 1 | 1 | 0.465 | 0.538 | 1 |
| q097 | code | hard | 1 | 1 | 0.707 | 0.766 | 0 |
| q098 | scenario | hard | 1 | 1 | 0.795 | 0.784 | 0 |
| q099 | classical | hard | 2 | 1 | 0.631 | 1.000 | 2 |
