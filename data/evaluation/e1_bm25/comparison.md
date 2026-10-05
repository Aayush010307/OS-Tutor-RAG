# Retrieval comparison — Dense v1.1 (A) vs BM25 E1 (B)

Same benchmark, corpus, queries, judgments and metric definitions (checked). Differences are B − A. Measurements only; no winner is declared.

## Configuration

- **Dense v1.1**: dense (Phase 2 baseline, unchanged), top_k=20; benchmark v1.1 `bfbbd033021a…`; corpus `90d1e88ef552…`
- **BM25 E1**: bm25 (E1 lexical baseline), top_k=20; benchmark v1.1 `bfbbd033021a…`; corpus `90d1e88ef552…`

## Overall (macro-averaged over queries)

| Metric | Dense v1.1 | BM25 E1 | Difference |
| --- | --- | --- | --- |
| precision@5 | 0.598 | 0.517 | -0.081 |
| precision@10 | 0.458 | 0.378 | -0.080 |
| recall@5 | 0.436 | 0.401 | -0.036 |
| recall@10 | 0.624 | 0.543 | -0.082 |
| mrr@5 | 0.914 | 0.852 | -0.062 |
| ndcg@5 | 0.695 | 0.629 | -0.066 |
| ndcg@10 | 0.706 | 0.631 | -0.075 |
| map@5 | 0.404 | 0.361 | -0.043 |

| Queries with a relevant result in top K (of 99) | Dense v1.1 | BM25 E1 | Difference |
| --- | --- | --- | --- |
| top 1 | 87 | 79 | -8 |
| top 3 | 95 | 89 | -6 |
| top 5 | 97 | 92 | -5 |
| top 10 | 97 | 96 | -1 |
| top 20 | 99 | 99 | +0 |

## Judgment coverage

Unjudged results count as non-relevant. Benchmark v1.1 was pooled from the dense system's top 20, so unjudged results fall almost entirely on the other system and its scores are lower bounds.

| Unjudged results | Dense v1.1 | BM25 E1 |
| --- | --- | --- |
| top 5 | 0 of 495 (0.0%) | 152 of 495 (30.7%) |
| top 10 | 0 of 990 (0.0%) | 418 of 990 (42.2%) |
| top 20 | 0 of 1980 (0.0%) | 1118 of 1980 (56.5%) |

Queries where BM25 E1 has at least one unjudged result in the top 5: 68.

## By topic (Dense v1.1 / BM25 E1)

| Topic | Queries | precision@5 | precision@10 | recall@5 | recall@10 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threads | 21 | 0.543 / 0.505 | 0.414 / 0.367 | 0.437 / 0.434 | 0.634 / 0.581 | 0.905 / 0.873 | 0.665 / 0.654 | 0.702 / 0.681 | 0.417 / 0.413 |
| Synchronisation | 78 | 0.613 / 0.521 | 0.469 / 0.381 | 0.436 / 0.392 | 0.622 / 0.532 | 0.917 / 0.846 | 0.703 / 0.622 | 0.707 / 0.617 | 0.400 / 0.347 |

## By difficulty (Dense v1.1 / BM25 E1)

| Difficulty | Queries | precision@5 | precision@10 | recall@5 | recall@10 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| easy | 23 | 0.739 / 0.557 | 0.557 / 0.430 | 0.450 / 0.367 | 0.623 / 0.517 | 1.000 / 0.853 | 0.807 / 0.634 | 0.767 / 0.618 | 0.437 / 0.333 |
| medium | 48 | 0.600 / 0.521 | 0.465 / 0.388 | 0.422 / 0.384 | 0.613 / 0.530 | 0.908 / 0.823 | 0.667 / 0.601 | 0.690 / 0.613 | 0.385 / 0.350 |
| hard | 28 | 0.479 / 0.479 | 0.364 / 0.318 | 0.450 / 0.456 | 0.646 / 0.585 | 0.854 / 0.900 | 0.652 / 0.672 | 0.683 / 0.671 | 0.409 / 0.403 |

## By query type (Dense v1.1 / BM25 E1)

| Query type | Queries | precision@5 | precision@10 | recall@5 | recall@10 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| conceptual | 26 | 0.746 / 0.500 | 0.508 / 0.346 | 0.529 / 0.386 | 0.684 / 0.506 | 1.000 / 0.863 | 0.806 / 0.622 | 0.779 / 0.608 | 0.506 / 0.362 |
| comparative | 11 | 0.655 / 0.509 | 0.500 / 0.409 | 0.418 / 0.398 | 0.585 / 0.550 | 0.894 / 0.655 | 0.750 / 0.577 | 0.725 / 0.608 | 0.374 / 0.365 |
| mechanism | 16 | 0.575 / 0.537 | 0.519 / 0.400 | 0.298 / 0.291 | 0.534 / 0.422 | 0.880 / 0.729 | 0.587 / 0.530 | 0.631 / 0.517 | 0.268 / 0.253 |
| code | 13 | 0.415 / 0.492 | 0.338 / 0.300 | 0.365 / 0.414 | 0.574 / 0.486 | 0.821 / 0.885 | 0.555 / 0.652 | 0.611 / 0.628 | 0.305 / 0.374 |
| scenario | 11 | 0.400 / 0.436 | 0.300 / 0.318 | 0.517 / 0.510 | 0.731 / 0.706 | 0.909 / 1.000 | 0.696 / 0.753 | 0.748 / 0.791 | 0.504 / 0.488 |
| algorithm | 12 | 0.517 / 0.467 | 0.367 / 0.350 | 0.454 / 0.454 | 0.589 / 0.622 | 0.889 / 0.917 | 0.642 / 0.587 | 0.656 / 0.633 | 0.408 / 0.373 |
| classical | 10 | 0.740 / 0.720 | 0.620 / 0.590 | 0.421 / 0.415 | 0.649 / 0.621 | 0.925 / 0.950 | 0.763 / 0.749 | 0.755 / 0.722 | 0.403 / 0.352 |

## Failures (no relevant chunk within the cutoff)

| Cutoff | Dense v1.1 | BM25 E1 |
| --- | --- | --- |
| top 5 | q009, q020 | q002, q008, q046, q055, q059, q060, q081 |
| top 10 | q009, q020 | q008, q046, q060 |
| top 20 | none | none |

## Overlap

- Mean shared chunks per query: top 10 4.17, top 20 8.18
- Judged-relevant chunks in the top 20 of only one system: Dense v1.1 only 176, BM25 E1 only 48, both 436
- Queries with a relevant chunk in the top 5 for BM25 E1 but not Dense v1.1: q009, q020; the reverse: q002, q008, q046, q055, q059, q060, q081

## Result categories in the top 5 / top 10

Counts of retrieved results over all queries. Top 10 split: relevant (grade ≥ 1) / judged 0 / unjudged.

| Category | Dense v1.1 top 5 | Dense v1.1 top 10 (rel / 0 / unjudged) | BM25 E1 top 5 | BM25 E1 top 10 (rel / 0 / unjudged) |
| --- | --- | --- | --- | --- |
| reference list (section 'References') | 2 | 7 (0 / 7 / 0) | 5 | 12 (0 / 3 / 9) |
| homework / questions section | 0 | 7 (0 / 7 / 0) | 34 | 73 (0 / 8 / 65) |
| practice problems (document_type) | 63 | 123 (51 / 72 / 0) | 54 | 103 (38 / 22 / 43) |
| lecture15 / Semaphore-copy chunk | 2 | 10 (9 / 1 / 0) | 5 | 16 (8 / 0 / 8) |

Queries with chunks from both lecture15 and Semaphore-copy in the top 10: Dense v1.1 q053, q059, q061, q064; BM25 E1 q053, q059, q063, q064, q066, q082, q096

## Deep-pool queries (top 30)

Grades: 2 / 1 relevant, 0 judged not relevant, — unjudged.

### q009 (hard, code): I pass &i from my for loop to pthread_create and the threads print the wrong numbers. Why?

| Judged relevant chunk | Grade | Rank Dense v1.1 | Rank BM25 E1 |
| --- | --- | --- | --- |
| ps-concurrency-381f1b77::c0019 | 2 | 19 | 2 |
| pthreads-sync-9017cfef::c0003 | 2 | >30 | 1 |
| threads-api-8ce54688::c0003 | 1 | >30 | >30 |
| threads-api-8ce54688::c0018 | 1 | >30 | 26 |

| Rank | Dense v1.1 chunk | Grade | BM25 E1 chunk | Grade | BM25 E1 section |
| --- | --- | --- | --- | --- | --- |
| 1 | lecture12-4288650c::c0005 | 0 | pthreads-sync-9017cfef::c0003 | 2 | Lab: Pthreads Synchronization > Warm-up exercises > 2. Write |
| 2 | threads-4d568260::c0004 | 0 | ps-concurrency-381f1b77::c0019 | 2 | Practice Problems: Concurrency > 20. Describe the output of  |
| 3 | threads-api-8ce54688::c0001 | 0 | pthreads-sync-9017cfef::c0008 | — | Lab: Pthreads Synchronization > Part B: Master-Worker Thread |
| 4 | threads-api-8ce54688::c0008 | 0 | pthreads-sync-9017cfef::c0004 | 0 | Lab: Pthreads Synchronization > Warm-up exercises > 3. You a |
| 5 | threads-api-8ce54688::c0004 | 0 | threads-intro-c1df7202::c0009 | 0 | 26 Concurrency: An Introduction > 26.3 Why It Gets Worse: Sh |
| 6 | threads-api-8ce54688::c0005 | 0 | threads-intro-c1df7202::c0010 | 0 | 26 Concurrency: An Introduction > 26.3 Why It Gets Worse: Sh |
| 7 | threads-intro-c1df7202::c0010 | 0 | pthreads-sync-9017cfef::c0005 | — | Lab: Pthreads Synchronization > Part A: Speeding up computat |
| 8 | threads-intro-c1df7202::c0005 | 0 | thread-synchroniza…e871e8ad::c0008 | — | 9. Traffic Intersection Synchronization |
| 9 | threads-api-8ce54688::c0017 | 0 | threads-intro-c1df7202::c0027 | — | 26 Concurrency: An Introduction > Questions |
| 10 | pthreads-sync-9017cfef::c0001 | 0 | threads-cv-3156a56b::c0009 | — | 30 Condition Variables > 30.2 The Producer/Consumer (Bounded |
| 11 | threads-intro-c1df7202::c0009 | 0 | threads-intro-c1df7202::c0026 | — | 26 Concurrency: An Introduction > Questions |
| 12 | threads-4d568260::c0005 | 0 | threads-locks-cb67d3bd::c0028 | — | 28 Locks > 28.14 Using Queues: Sleeping Instead Of Spinning |
| 13 | threads-api-8ce54688::c0015 | 0 | threads-sema-d8fb1c00::c0015 | — | 31 Semaphores > A Solution: Adding Mutual Exclusion |
| 14 | threads-intro-c1df7202::c0004 | 0 | sumsem2025-26-vl-b…02c11114::c0021 | — | We now prove that this solution is correct. We need to show  |
| 15 | fallsem2025-26-vl-…170d2f74::c0009 | 0 | threads-api-8ce54688::c0002 | 0 | 27 Interlude: Thread API > 27.1 Thread Creation |
| 16 | pthreads-sync-9017cfef::c0009 | 0 | threads-intro-c1df7202::c0003 | — | 26 Concurrency: An Introduction > 26.1 Why Use Threads? |
| 17 | ps-concurrency-381f1b77::c0005 | 0 | threads-cv-3156a56b::c0018 | — | 30 Condition Variables > The Single Buffer Producer/Consumer |
| 18 | pthreads-sync-9017cfef::c0014 | 0 | fallsem2025-26-vl-…170d2f74::c0009 | 0 | Why Pthreads |
| 19 | ps-concurrency-381f1b77::c0019 | 2 | fallsem2025-26-vl-…fd173a9e::c0006 | — | 3. Dining Philosophers problem using Semaphores > Semaphore  |
| 20 | pthreads-sync-9017cfef::c0000 | 0 | lecture12-4288650c::c0003 | — | Why threads? |
| 21 | threads-api-8ce54688::c0007 | 0 | threads-api-8ce54688::c0005 | 0 | 27 Interlude: Thread API > 27.2 Thread Completion |
| 22 | threads-api-8ce54688::c0013 | 0 | lecture14-a8135675::c0002 | — | Why check condition in while loop? |
| 23 | threads-api-8ce54688::c0016 | 0 | thread-synchroniza…e871e8ad::c0009 | 0 | 10. Shared Resource Pool |
| 24 | threads-api-8ce54688::c0006 | 0 | threads-api-8ce54688::c0001 | 0 | 27 Interlude: Thread API > 27.1 Thread Creation |
| 25 | threads-api-8ce54688::c0002 | 0 | ps-concurrency-381f1b77::c0048 | — | Practice Problems: Concurrency > 49. Consider the barrier sy |
| 26 | threads-cv-3156a56b::c0014 | 0 | threads-api-8ce54688::c0018 | 1 | 27 Interlude: Thread API > 27.6 Summary |
| 27 | pthreads-sync-9017cfef::c0004 | 0 | threads-cv-3156a56b::c0010 | — | 30 Condition Variables > A Broken Solution |
| 28 | thread-synchroniza…e871e8ad::c0009 | 0 | threads-api-8ce54688::c0007 | 0 | 27 Interlude: Thread API > 27.2 Thread Completion |
| 29 | threads-cv-3156a56b::c0002 | 0 | threads-api-8ce54688::c0004 | 0 | 27 Interlude: Thread API > 27.2 Thread Completion |
| 30 | threads-api-8ce54688::c0019 | 0 | ps-concurrency-381f1b77::c0047 | — | Practice Problems: Concurrency > 48. Consider the classic “b |

### q020 (hard, scenario): How would you speed up a CPU-heavy loop by splitting it across 10 threads, and do the threads need locks if each writes a different part of the array?

| Judged relevant chunk | Grade | Rank Dense v1.1 | Rank BM25 E1 |
| --- | --- | --- | --- |
| pthreads-sync-9017cfef::c0006 | 2 | 21 | 1 |
| pthreads-sync-9017cfef::c0005 | 1 | 24 | 8 |
| pthreads-sync-9017cfef::c0007 | 1 | >30 | >30 |
| threads-4d568260::c0003 | 1 | >30 | >30 |
| threads-intro-c1df7202::c0003 | 1 | 16 | 4 |

| Rank | Dense v1.1 chunk | Grade | BM25 E1 chunk | Grade | BM25 E1 section |
| --- | --- | --- | --- | --- | --- |
| 1 | threads-locks-cb67d3bd::c0022 | 0 | pthreads-sync-9017cfef::c0006 | 2 | Lab: Pthreads Synchronization > Part A: Speeding up computat |
| 2 | threads-locks-cb67d3bd::c0016 | 0 | threads-locks-cb67d3bd::c0039 | 0 | 28 Locks > Questions |
| 3 | threads-locks-cb67d3bd::c0023 | 0 | pthreads-sync-9017cfef::c0002 | — | Lab: Pthreads Synchronization > Warm-up exercises > 1. Write |
| 4 | threads-locks-cb67d3bd::c0024 | 0 | threads-intro-c1df7202::c0003 | 1 | 26 Concurrency: An Introduction > 26.1 Why Use Threads? |
| 5 | pthreads-sync-9017cfef::c0004 | 0 | threads-cv-3156a56b::c0026 | — | 30 Condition Variables > Questions |
| 6 | ps-concurrency-381f1b77::c0022 | 0 | threads-locks-cb67d3bd::c0016 | 0 | 28 Locks > 28.8 Evaluating Spin Locks |
| 7 | threads-locks-cb67d3bd::c0009 | 0 | ps-concurrency-381f1b77::c0022 | 0 | Practice Problems: Concurrency > 23. Consider a multithreade |
| 8 | ps-concurrency-381f1b77::c0018 | 0 | pthreads-sync-9017cfef::c0005 | 1 | Lab: Pthreads Synchronization > Part A: Speeding up computat |
| 9 | threads-locks-cb67d3bd::c0008 | 0 | threads-4d568260::c0001 | — | What are threads? |
| 10 | threads-locks-cb67d3bd::c0000 | 0 | threads-locks-cb67d3bd::c0023 | 0 | 28 Locks > 28.13 A Simple Approach: Just Yield, Baby |
| 11 | pthreads-sync-9017cfef::c0011 | 0 | threads-intro-c1df7202::c0009 | — | 26 Concurrency: An Introduction > 26.3 Why It Gets Worse: Sh |
| 12 | threads-api-8ce54688::c0009 | 0 | threads-locks-cb67d3bd::c0038 | 0 | 28 Locks > Questions |
| 13 | threads-locks-cb67d3bd::c0039 | 0 | threads-bugs-e5dff53b::c0026 | — | 32 Common Concurrency Problems > Questions |
| 14 | threads-locks-cb67d3bd::c0004 | 0 | threads-bugs-e5dff53b::c0018 | — | 32 Common Concurrency Problems > Deadlock Avoidance via Sche |
| 15 | threads-locks-cb67d3bd::c0015 | 0 | ps-concurrency-381f1b77::c0048 | — | Practice Problems: Concurrency > 49. Consider the barrier sy |
| 16 | threads-intro-c1df7202::c0003 | 1 | threads-intro-c1df7202::c0028 | — | 26 Concurrency: An Introduction > Questions |
| 17 | threads-sema-d8fb1c00::c0025 | 0 | pthreads-sync-9017cfef::c0008 | — | Lab: Pthreads Synchronization > Part B: Master-Worker Thread |
| 18 | threads-api-8ce54688::c0017 | 0 | ps-concurrency-381f1b77::c0053 | — | Practice Problems: Concurrency > 54. Consider a database ser |
| 19 | threads-locks-cb67d3bd::c0001 | 0 | threads-api-8ce54688::c0017 | 0 | 27 Interlude: Thread API > 27.6 Summary |
| 20 | threads-locks-cb67d3bd::c0014 | 0 | ps-concurrency-381f1b77::c0037 | — | Practice Problems: Concurrency > 38. Consider a process with |
| 21 | pthreads-sync-9017cfef::c0006 | 2 | threads-locks-cb67d3bd::c0004 | 0 | 28 Locks > 28.4 Evaluating Locks |
| 22 | threads-locks-cb67d3bd::c0038 | 0 | threads-api-8ce54688::c0015 | — | 27 Interlude: Thread API > 27.4 Condition Variables |
| 23 | threads-bugs-e5dff53b::c0017 | 0 | threads-sema-d8fb1c00::c0002 | — | 31 Semaphores > 31.1 Semaphores: A Definition |
| 24 | pthreads-sync-9017cfef::c0005 | 1 | ps-concurrency-381f1b77::c0049 | — | Practice Problems: Concurrency > 50. Consider a web server t |
| 25 | ps-concurrency-381f1b77::c0023 | 0 | threads-intro-c1df7202::c0002 | — | 26 Concurrency: An Introduction |
| 26 | threads-sema-d8fb1c00::c0021 | 0 | threads-intro-c1df7202::c0017 | — | 26 Concurrency: An Introduction > 26.4 The Heart Of The Prob |
| 27 | threads-cv-3156a56b::c0000 | 0 | threads-locks-cb67d3bd::c0006 | — | 28 Locks > 28.5 Controlling Interrupts |
| 28 | threads-locks-cb67d3bd::c0026 | 0 | threads-sema-d8fb1c00::c0025 | 0 | 31 Semaphores > 31.7 Thread Throttling |
| 29 | threads-bugs-e5dff53b::c0015 | 0 | pthreads-sync-9017cfef::c0004 | 0 | Lab: Pthreads Synchronization > Warm-up exercises > 3. You a |
| 30 | threads-intro-c1df7202::c0026 | 0 | pthreads-sync-9017cfef::c0013 | — | Lab: Pthreads Synchronization > Part C: Reader-Writer Locks |

### q091 (medium, algorithm): How can the atomic swap instruction be used to implement mutual exclusion?

| Judged relevant chunk | Grade | Rank Dense v1.1 | Rank BM25 E1 |
| --- | --- | --- | --- |
| fallsem2025-26-vl-…3f6ce962::c0019 | 2 | 15 | >30 |
| fallsem2025-26-vl-…975bc607::c0017 | 2 | 11 | >30 |
| ps-concurrency-381f1b77::c0023 | 2 | 9 | 5 |
| fallsem2025-26-vl-…3f6ce962::c0015 | 1 | >30 | >30 |
| fallsem2025-26-vl-…3f6ce962::c0018 | 1 | 13 | 21 |
| fallsem2025-26-vl-…975bc607::c0013 | 1 | 27 | 18 |
| fallsem2025-26-vl-…975bc607::c0016 | 1 | 14 | 22 |
| sumsem2025-26-vl-b…02c11114::c0024 | 1 | 3 | 1 |
| threads-locks-cb67d3bd::c0010 | 1 | 18 | >30 |

| Rank | Dense v1.1 chunk | Grade | BM25 E1 chunk | Grade | BM25 E1 section |
| --- | --- | --- | --- | --- | --- |
| 1 | threads-bugs-e5dff53b::c0014 | 0 | sumsem2025-26-vl-b…02c11114::c0024 | 1 | Test and Set |
| 2 | sumsem2025-26-vl-b…02c11114::c0025 | 0 | threads-bugs-e5dff53b::c0014 | 0 | 32 Common Concurrency Problems > Prevention > Mutual Exclusi |
| 3 | sumsem2025-26-vl-b…02c11114::c0024 | 1 | sumsem2025-26-vl-b…02c11114::c0025 | 0 | compare and swap() instruction (CAS) |
| 4 | threads-locks-cb67d3bd::c0005 | 0 | fallsem2025-26-vl-…975bc607::c0001 | — | Objectives |
| 5 | ps-concurrency-381f1b77::c0020 | 0 | ps-concurrency-381f1b77::c0023 | 2 | Practice Problems: Concurrency > 24. Consider the atomic har |
| 6 | threads-sema-d8fb1c00::c0015 | 0 | threads-locks-cb67d3bd::c0005 | 0 | 28 Locks > 28.5 Controlling Interrupts |
| 7 | fallsem2025-26-vl-…975bc607::c0008 | 0 | fallsem2025-26-vl-…3f6ce962::c0021 | — | Semaphore as General Synchronization Tool |
| 8 | threads-locks-cb67d3bd::c0009 | 0 | lecture12-4288650c::c0006 | — | Race conditions and synchronization |
| 9 | ps-concurrency-381f1b77::c0023 | 2 | lecture13-0af66874::c0006 | 0 | Alternative to spinning |
| 10 | concurrency-bugs-e8a8fced::c0001 | 0 | threads-locks-cb67d3bd::c0003 | — | 28 Locks > 28.3 Building A Lock |
| 11 | fallsem2025-26-vl-…975bc607::c0017 | 2 | ps-concurrency-381f1b77::c0020 | 0 | Practice Problems: Concurrency > 21. Recall that the atomic  |
| 12 | threads-intro-c1df7202::c0022 | 0 | threads-locks-cb67d3bd::c0017 | 0 | 28 Locks > 28.9 Compare-And-Swap |
| 13 | fallsem2025-26-vl-…3f6ce962::c0018 | 1 | fallsem2025-26-vl-…fd173a9e::c0008 | — | 4. Readers and Writers problem using Semaphores |
| 14 | fallsem2025-26-vl-…975bc607::c0016 | 1 | threads-4d568260::c0008 | — | Race conditions, critical sections |
| 15 | fallsem2025-26-vl-…3f6ce962::c0019 | 2 | lecture13-0af66874::c0002 | — | Is disabling interrupts enough? |
| 16 | threads-intro-c1df7202::c0019 | 0 | sumsem2025-26-vl-b…02c11114::c0036 | — | Dining-Philosophers Problem Algorithm |
| 17 | lecture13-0af66874::c0004 | 0 | threads-locks-cb67d3bd::c0039 | — | 28 Locks > Questions |
| 18 | threads-locks-cb67d3bd::c0010 | 1 | fallsem2025-26-vl-…975bc607::c0013 | 1 | Hardware Instructions |
| 19 | threads-intro-c1df7202::c0017 | 0 | threads-intro-c1df7202::c0019 | 0 | 26 Concurrency: An Introduction > 26.5 The Wish For Atomicit |
| 20 | threads-locks-cb67d3bd::c0017 | 0 | fallsem2025-26-vl-…975bc607::c0018 | — | Mutex Locks |
| 21 | lecture13-0af66874::c0006 | 0 | fallsem2025-26-vl-…3f6ce962::c0018 | 1 | Swap Instruction |
| 22 | concurrency-bugs-e8a8fced::c0003 | 0 | fallsem2025-26-vl-…975bc607::c0016 | 1 | Swap Instruction |
| 23 | threads-locks-cb67d3bd::c0014 | 0 | lecture13-0af66874::c0004 | 0 | Solution: Hardware atomic instructions |
| 24 | threads-locks-cb67d3bd::c0000 | 0 | threads-intro-c1df7202::c0022 | 0 | 26 Concurrency: An Introduction > References |
| 25 | concurrency-bugs-e8a8fced::c0002 | 0 | threads-sema-d8fb1c00::c0021 | — | 31 Semaphores > 31.5 Reader-Writer Locks |
| 26 | threads-bugs-e5dff53b::c0003 | 0 | threads-locks-cb67d3bd::c0002 | — | 28 Locks > 28.2 Pthread Locks |
| 27 | fallsem2025-26-vl-…975bc607::c0013 | 1 | threads-locks-cb67d3bd::c0014 | 0 | 28 Locks > 28.7 Building Working Spin Locks with Test-And-Se |
| 28 | threads-intro-c1df7202::c0020 | 0 | sumsem2025-26-vl-b…02c11114::c0001 | — | Objectives |
| 29 | threads-api-8ce54688::c0009 | 0 | threads-locks-cb67d3bd::c0009 | 0 | 28 Locks > 28.6 A Failed Attempt: Just Using Loads/Stores >  |
| 30 | sumsem2025-26-vl-b…02c11114::c0021 | 0 | ps-concurrency-381f1b77::c0030 | — | Practice Problems: Concurrency > 31. Consider the classic re |

## Per query

| Query | Type | Difficulty | First relevant rank Dense v1.1 | First relevant rank BM25 E1 | nDCG@10 Dense v1.1 | nDCG@10 BM25 E1 | Unjudged@10 BM25 E1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| q001 | conceptual | easy | 1 | 1 | 0.660 | 0.353 | 7 |
| q002 | comparative | medium | 1 | 6 | 0.932 | 0.252 | 6 |
| q003 | conceptual | easy | 1 | 1 | 0.477 | 0.435 | 7 |
| q004 | comparative | easy | 1 | 1 | 0.908 | 0.908 | 4 |
| q005 | mechanism | medium | 1 | 1 | 0.702 | 0.776 | 2 |
| q006 | mechanism | easy | 1 | 1 | 0.433 | 0.557 | 5 |
| q007 | mechanism | easy | 1 | 3 | 0.636 | 0.537 | 4 |
| q008 | code | hard | 1 | 14 | 0.714 | 0.000 | 7 |
| q009 | code | hard | 19 | 1 | 0.000 | 0.778 | 5 |
| q010 | conceptual | medium | 1 | 1 | 0.886 | 0.928 | 3 |
| q011 | mechanism | medium | 1 | 1 | 0.849 | 0.839 | 5 |
| q012 | comparative | easy | 1 | 1 | 0.931 | 0.888 | 0 |
| q013 | scenario | medium | 1 | 1 | 0.824 | 0.735 | 0 |
| q014 | conceptual | easy | 1 | 1 | 0.871 | 0.739 | 7 |
| q015 | scenario | medium | 1 | 1 | 0.692 | 0.532 | 7 |
| q016 | conceptual | medium | 1 | 1 | 0.900 | 0.930 | 1 |
| q017 | conceptual | medium | 1 | 1 | 0.731 | 0.666 | 6 |
| q018 | conceptual | easy | 1 | 1 | 1.000 | 1.000 | 4 |
| q019 | mechanism | easy | 1 | 1 | 0.719 | 0.894 | 5 |
| q020 | scenario | hard | 16 | 1 | 0.000 | 0.695 | 3 |
| q021 | scenario | hard | 1 | 1 | 0.880 | 0.870 | 2 |
| q022 | conceptual | easy | 1 | 1 | 0.765 | 0.649 | 5 |
| q023 | mechanism | medium | 1 | 1 | 0.594 | 0.616 | 2 |
| q024 | conceptual | easy | 1 | 1 | 0.631 | 0.494 | 2 |
| q025 | conceptual | easy | 1 | 1 | 0.748 | 0.646 | 3 |
| q026 | conceptual | medium | 1 | 1 | 0.690 | 0.589 | 6 |
| q027 | mechanism | easy | 1 | 3 | 0.737 | 0.117 | 5 |
| q028 | code | medium | 1 | 1 | 0.793 | 0.722 | 4 |
| q029 | comparative | medium | 1 | 1 | 0.532 | 1.000 | 6 |
| q030 | conceptual | medium | 1 | 1 | 0.753 | 0.536 | 7 |
| q031 | algorithm | medium | 1 | 1 | 0.715 | 0.710 | 4 |
| q032 | algorithm | easy | 1 | 2 | 0.948 | 0.491 | 2 |
| q033 | algorithm | medium | 1 | 2 | 0.725 | 0.361 | 3 |
| q034 | algorithm | medium | 1 | 1 | 0.701 | 0.699 | 4 |
| q035 | algorithm | hard | 1 | 1 | 0.596 | 0.569 | 5 |
| q036 | algorithm | medium | 1 | 1 | 1.000 | 1.000 | 5 |
| q037 | algorithm | hard | 1 | 1 | 0.695 | 0.791 | 4 |
| q038 | conceptual | medium | 1 | 1 | 0.845 | 0.632 | 5 |
| q039 | comparative | medium | 1 | 1 | 0.789 | 0.591 | 7 |
| q040 | conceptual | hard | 1 | 1 | 0.858 | 0.584 | 5 |
| q041 | mechanism | hard | 1 | 1 | 0.877 | 0.880 | 3 |
| q042 | conceptual | medium | 1 | 1 | 0.695 | 0.979 | 4 |
| q043 | conceptual | medium | 1 | 1 | 0.580 | 0.733 | 4 |
| q044 | conceptual | easy | 1 | 4 | 0.597 | 0.126 | 8 |
| q045 | mechanism | easy | 1 | 1 | 0.555 | 0.497 | 5 |
| q046 | mechanism | medium | 1 | 14 | 0.581 | 0.000 | 9 |
| q047 | code | medium | 1 | 1 | 0.755 | 0.655 | 3 |
| q048 | conceptual | hard | 1 | 1 | 0.849 | 0.647 | 5 |
| q049 | comparative | medium | 1 | 2 | 0.800 | 0.564 | 3 |
| q050 | code | hard | 1 | 1 | 0.759 | 0.826 | 3 |
| q051 | mechanism | medium | 4 | 2 | 0.282 | 0.226 | 6 |
| q052 | mechanism | easy | 1 | 1 | 0.873 | 0.365 | 6 |
| q053 | comparative | easy | 1 | 1 | 0.686 | 0.982 | 0 |
| q054 | mechanism | medium | 1 | 1 | 0.584 | 0.532 | 5 |
| q055 | mechanism | medium | 3 | 7 | 0.314 | 0.108 | 7 |
| q056 | mechanism | medium | 1 | 1 | 0.889 | 0.918 | 0 |
| q057 | code | hard | 3 | 1 | 0.307 | 0.613 | 7 |
| q058 | scenario | medium | 1 | 1 | 1.000 | 0.760 | 6 |
| q059 | conceptual | medium | 1 | 6 | 0.867 | 0.127 | 5 |
| q060 | comparative | medium | 3 | 12 | 0.404 | 0.000 | 9 |
| q061 | comparative | hard | 1 | 5 | 0.821 | 0.233 | 7 |
| q062 | classical | easy | 1 | 1 | 0.796 | 0.878 | 0 |
| q063 | classical | medium | 1 | 1 | 0.862 | 0.931 | 1 |
| q064 | code | hard | 1 | 1 | 0.634 | 0.769 | 2 |
| q065 | classical | hard | 4 | 1 | 0.197 | 0.402 | 3 |
| q066 | classical | medium | 1 | 1 | 0.808 | 0.729 | 2 |
| q067 | classical | easy | 1 | 1 | 0.853 | 0.768 | 2 |
| q068 | classical | medium | 1 | 1 | 0.635 | 0.632 | 1 |
| q069 | classical | hard | 1 | 1 | 0.764 | 0.778 | 1 |
| q070 | code | hard | 1 | 2 | 0.847 | 0.539 | 5 |
| q071 | classical | easy | 1 | 1 | 0.915 | 0.780 | 2 |
| q072 | classical | medium | 1 | 1 | 0.723 | 0.694 | 2 |
| q073 | code | hard | 3 | 1 | 0.431 | 0.823 | 0 |
| q074 | conceptual | easy | 1 | 1 | 1.000 | 1.000 | 3 |
| q075 | mechanism | medium | 2 | 2 | 0.469 | 0.417 | 1 |
| q076 | scenario | medium | 1 | 1 | 0.547 | 0.822 | 3 |
| q077 | conceptual | hard | 1 | 1 | 0.834 | 0.605 | 4 |
| q078 | comparative | medium | 2 | 2 | 0.403 | 0.403 | 8 |
| q079 | comparative | medium | 1 | 1 | 0.771 | 0.871 | 3 |
| q080 | code | hard | 1 | 1 | 0.620 | 0.621 | 6 |
| q081 | conceptual | medium | 1 | 9 | 0.470 | 0.185 | 8 |
| q082 | scenario | hard | 1 | 1 | 1.000 | 1.000 | 8 |
| q083 | conceptual | medium | 1 | 1 | 0.855 | 0.786 | 0 |
| q084 | conceptual | medium | 1 | 1 | 0.850 | 0.615 | 4 |
| q085 | conceptual | medium | 1 | 1 | 0.927 | 0.706 | 3 |
| q086 | code | hard | 1 | 1 | 0.849 | 0.639 | 7 |
| q087 | algorithm | medium | 1 | 1 | 0.432 | 0.508 | 4 |
| q088 | algorithm | hard | 1 | 1 | 0.701 | 0.817 | 2 |
| q089 | algorithm | medium | 3 | 1 | 0.235 | 0.617 | 4 |
| q090 | algorithm | medium | 1 | 1 | 0.954 | 0.754 | 4 |
| q091 | algorithm | medium | 3 | 1 | 0.173 | 0.278 | 4 |
| q092 | conceptual | easy | 1 | 5 | 0.905 | 0.111 | 7 |
| q093 | scenario | medium | 1 | 1 | 0.621 | 0.778 | 4 |
| q094 | scenario | hard | 1 | 1 | 0.866 | 0.956 | 5 |
| q095 | scenario | hard | 1 | 1 | 0.954 | 0.753 | 7 |
| q096 | code | hard | 1 | 1 | 0.611 | 0.465 | 6 |
| q097 | code | hard | 1 | 1 | 0.620 | 0.707 | 4 |
| q098 | scenario | hard | 1 | 1 | 0.849 | 0.795 | 1 |
| q099 | classical | hard | 1 | 2 | 1.000 | 0.631 | 8 |
