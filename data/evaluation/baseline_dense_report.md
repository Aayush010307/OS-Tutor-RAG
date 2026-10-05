# Baseline Dense Retrieval — Evaluation Report

Run `baseline_dense` at 2026-09-21T14:29:49+00:00. Measurements only; no thresholds or quality claims.

## Configuration

- Corpus: `chunks.jsonl` SHA-256 `90d1e88ef552dfb32b5a8c2d4845cd20399eca82f6669bd184d08eaad8fcbe16` (463 chunks)
- Benchmark: `data/evaluation/retrieval_queries.json` version 1.0, SHA-256 `370b7c3393079fe30ef9cff5402aa23a2762736b24227a6cde572e926f57abb1`
- Retriever: dense (Phase 2 baseline, unchanged); `nomic-embed-text-v1.5` @ `e9b6763023c6`, collection `os_tutor_chunks__nomic_embed_text_v1_5` (Cosine), vectors SHA-256 `1d65a77704cc5ecf…`, top_k=10, no filters
- Relevance: chunk relevant when judged grade >= 1; nDCG uses grades (2, 1) as linear gains; unjudged = 0

## Benchmark

- Queries: 99; judgments: 616 (grade 2: 322, grade 1: 294)
- Topic: {'Threads': 21, 'Synchronisation': 78}
- Difficulty: {'easy': 23, 'medium': 48, 'hard': 28}
- Query type: {'conceptual': 26, 'comparative': 11, 'mechanism': 16, 'code': 13, 'scenario': 11, 'algorithm': 12, 'classical': 10}

## Overall metrics (macro-averaged over queries)

| Metric | Value |
| --- | --- |
| recall@1 | 0.193 |
| recall@3 | 0.405 |
| recall@5 | 0.486 |
| recall@10 | 0.647 |
| hit@1 | 0.869 |
| hit@3 | 0.950 |
| hit@5 | 0.970 |
| hit@10 | 0.980 |
| precision@5 | 0.539 |
| mrr@5 | 0.904 |
| mrr@10 | 0.905 |
| ndcg@5 | 0.682 |
| ndcg@10 | 0.708 |
| map@5 | 0.451 |

Recall@K is the fraction of the judged relevant set found in the top K; queries with many background (grade 1) chunks have a low ceiling for small K (Recall@1 is at most 1/|relevant|). Hit@K is reported separately as the share of queries with at least one relevant chunk in the top K.

## By topic

| Group | Queries | recall@1 | recall@3 | recall@5 | recall@10 | precision@5 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threads | 21 | 0.223 | 0.442 | 0.497 | 0.657 | 0.486 | 0.905 | 0.662 | 0.709 | 0.476 |
| Synchronisation | 78 | 0.185 | 0.395 | 0.483 | 0.644 | 0.554 | 0.904 | 0.687 | 0.708 | 0.444 |

## By difficulty

| Group | Queries | recall@1 | recall@3 | recall@5 | recall@10 | precision@5 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| easy | 23 | 0.160 | 0.407 | 0.502 | 0.669 | 0.678 | 0.971 | 0.777 | 0.765 | 0.480 |
| medium | 48 | 0.157 | 0.368 | 0.453 | 0.626 | 0.546 | 0.901 | 0.650 | 0.686 | 0.410 |
| hard | 28 | 0.282 | 0.468 | 0.529 | 0.663 | 0.414 | 0.854 | 0.658 | 0.699 | 0.496 |

## By query type

| Group | Queries | recall@1 | recall@3 | recall@5 | recall@10 | precision@5 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| conceptual | 26 | 0.188 | 0.448 | 0.595 | 0.723 | 0.669 | 0.974 | 0.778 | 0.788 | 0.556 |
| mechanism | 16 | 0.111 | 0.286 | 0.358 | 0.549 | 0.562 | 0.880 | 0.585 | 0.622 | 0.324 |
| algorithm | 12 | 0.180 | 0.423 | 0.463 | 0.605 | 0.467 | 0.861 | 0.629 | 0.658 | 0.420 |
| classical | 10 | 0.194 | 0.354 | 0.463 | 0.685 | 0.660 | 0.925 | 0.732 | 0.733 | 0.437 |
| code | 13 | 0.186 | 0.358 | 0.381 | 0.588 | 0.339 | 0.821 | 0.543 | 0.621 | 0.335 |
| scenario | 11 | 0.400 | 0.597 | 0.623 | 0.733 | 0.364 | 0.909 | 0.733 | 0.771 | 0.615 |
| comparative | 11 | 0.137 | 0.369 | 0.448 | 0.603 | 0.582 | 0.894 | 0.723 | 0.716 | 0.406 |

## Retrieval failures

- Queries with no relevant chunk in the top 5: 3 (q009, q020, q091)
- Queries with no relevant chunk in the top 10: 2 (q009, q020)
- Heuristic failure categories (top-5 failures): {'semantic_mismatch': 3}

## Non-relevant results in the top 5 (heuristic tags)

- Unjudged results in the top 5 across all queries: 228
- Tag counts (a result can carry several tags): image_only_unit 10, neighboring_chunk 34, reference_list 2, topically_related_unjudged 178
- `topically_related_unjudged` means the chunk shares a subtopic label with the query; such chunks may be relevant material that the incomplete judgments do not list.

## Judgment coverage

- Mean unjudged results per query: top 5 2.303, top 10 6.1717 (share of all top-10 results unjudged: 0.6172)
- Unjudged results count as non-relevant, so metrics are a lower bound with respect to judgment completeness.

## Duplicates

- Queries with duplicate content in the top 5: 0; in the top 10: 4
- Duplicate pairs in top-10 lists by kind: {'near_duplicate_document': 2, 'exact_duplicate_chunk': 2}

## Notable error cases

Queries where no relevant chunk was retrieved in the top 5 (expected = grade-2 judgments; retrieved = top 3):

- **q009** (hard, code) I pass &i from my for loop to pthread_create and the threads print the wrong numbers. Why?
  - categories: semantic_mismatch; first relevant rank within top 10: none
  - expected: ps-concurrency-381f1b77::c0019, pthreads-sync-9017cfef::c0003
  - #1 0.781 lecture12-4288650c::c0005 (p.7-9) Threads with shared data: what happens? [topically_related_unjudged, image_only_unit]
  - #2 0.756 threads-4d568260::c0004 (p.6) POSIX threads [topically_related_unjudged]
  - #3 0.750 threads-api-8ce54688::c0001 (p.1) 27 Interlude: Thread API > 27.1 Thread Creation [topically_related_unjudged]
- **q020** (hard, scenario) How would you speed up a CPU-heavy loop by splitting it across 10 threads, and do the threads need locks if each writes a different part of the array?
  - categories: semantic_mismatch; first relevant rank within top 10: none
  - expected: pthreads-sync-9017cfef::c0006
  - #1 0.764 threads-locks-cb67d3bd::c0022 (p.13-14) 28 Locks > 28.12 Too Much Spinning: What Now?
  - #2 0.753 threads-locks-cb67d3bd::c0016 (p.9-10) 28 Locks > 28.8 Evaluating Spin Locks
  - #3 0.743 threads-locks-cb67d3bd::c0023 (p.14-15) 28 Locks > 28.13 A Simple Approach: Just Yield, Baby
- **q091** (medium, algorithm) How can the atomic swap instruction be used to implement mutual exclusion?
  - categories: semantic_mismatch; first relevant rank within top 10: 9
  - expected: fallsem2025-26-vl-bcse303l-00100::c0019, fallsem2025-26-vl-bcse303l-00100::c0017, ps-concurrency-381f1b77::c0023
  - #1 0.777 threads-bugs-e5dff53b::c0014 (p.10) 32 Common Concurrency Problems > Prevention > Mutual Exclusion [topically_related_unjudged]
  - #2 0.716 sumsem2025-26-vl-bcse303l-00100-::c0025 (s.40-43) compare and swap() instruction (CAS) [topically_related_unjudged, image_only_unit]
  - #3 0.698 sumsem2025-26-vl-bcse303l-00100-::c0024 (s.37-39) Test and Set [topically_related_unjudged]

## Per-query results

| Query | Topic | Difficulty | Type | R@5 | R@10 | P@5 | MRR@5 | nDCG@10 | Unjudged@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q001 | Threads | easy | conceptual | 0.250 | 0.500 | 0.400 | 1.000 | 0.589 | 3 |
| q002 | Threads | medium | comparative | 0.364 | 0.727 | 0.800 | 1.000 | 0.888 | 1 |
| q003 | Threads | easy | conceptual | 0.286 | 0.286 | 0.400 | 1.000 | 0.455 | 3 |
| q004 | Threads | easy | comparative | 0.750 | 0.750 | 0.600 | 1.000 | 0.908 | 2 |
| q005 | Threads | medium | mechanism | 0.300 | 0.500 | 0.600 | 1.000 | 0.660 | 2 |
| q006 | Threads | easy | mechanism | 0.333 | 0.333 | 0.400 | 1.000 | 0.460 | 3 |
| q007 | Threads | easy | mechanism | 0.500 | 0.625 | 0.800 | 1.000 | 0.698 | 1 |
| q008 | Threads | hard | code | 0.500 | 0.750 | 0.400 | 1.000 | 0.677 | 3 |
| q009 | Threads | hard | code | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 5 |
| q010 | Threads | medium | conceptual | 0.800 | 1.000 | 0.800 | 1.000 | 0.955 | 1 |
| q011 | Threads | medium | mechanism | 0.500 | 1.000 | 0.400 | 1.000 | 0.843 | 3 |
| q012 | Threads | easy | comparative | 0.571 | 1.000 | 0.800 | 1.000 | 0.950 | 1 |
| q013 | Threads | medium | scenario | 0.571 | 0.857 | 0.800 | 1.000 | 0.803 | 1 |
| q014 | Threads | easy | conceptual | 0.800 | 0.800 | 0.800 | 1.000 | 0.924 | 1 |
| q015 | Threads | medium | scenario | 0.333 | 0.667 | 0.200 | 1.000 | 0.692 | 4 |
| q016 | Threads | medium | conceptual | 0.500 | 0.750 | 0.400 | 1.000 | 0.847 | 3 |
| q017 | Threads | medium | conceptual | 0.750 | 0.750 | 0.600 | 1.000 | 0.811 | 2 |
| q018 | Threads | easy | conceptual | 1.000 | 1.000 | 0.400 | 1.000 | 1.000 | 3 |
| q019 | Threads | easy | mechanism | 0.333 | 0.500 | 0.400 | 1.000 | 0.719 | 3 |
| q020 | Threads | hard | scenario | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 5 |
| q021 | Threads | hard | scenario | 1.000 | 1.000 | 0.200 | 1.000 | 1.000 | 4 |
| q022 | Synchronisation | easy | conceptual | 0.385 | 0.538 | 1.000 | 1.000 | 0.765 | 0 |
| q023 | Synchronisation | medium | mechanism | 0.250 | 0.438 | 0.800 | 1.000 | 0.557 | 1 |
| q024 | Synchronisation | easy | conceptual | 0.455 | 0.545 | 1.000 | 1.000 | 0.631 | 0 |
| q025 | Synchronisation | easy | conceptual | 0.375 | 0.500 | 0.600 | 1.000 | 0.748 | 2 |
| q026 | Synchronisation | medium | conceptual | 0.429 | 0.714 | 0.600 | 1.000 | 0.660 | 2 |
| q027 | Synchronisation | easy | mechanism | 0.286 | 0.571 | 0.400 | 1.000 | 0.727 | 3 |
| q028 | Synchronisation | medium | code | 0.600 | 0.600 | 0.600 | 1.000 | 0.793 | 2 |
| q029 | Synchronisation | medium | comparative | 0.333 | 0.333 | 0.200 | 1.000 | 0.532 | 4 |
| q030 | Synchronisation | medium | conceptual | 0.625 | 0.625 | 1.000 | 1.000 | 0.753 | 0 |
| q031 | Synchronisation | medium | algorithm | 0.500 | 0.750 | 0.400 | 1.000 | 0.715 | 3 |
| q032 | Synchronisation | easy | algorithm | 0.417 | 0.750 | 1.000 | 1.000 | 0.948 | 0 |
| q033 | Synchronisation | medium | algorithm | 0.444 | 0.667 | 0.800 | 1.000 | 0.670 | 1 |
| q034 | Synchronisation | medium | algorithm | 0.333 | 0.444 | 0.600 | 1.000 | 0.701 | 2 |
| q035 | Synchronisation | hard | algorithm | 0.500 | 0.500 | 0.400 | 1.000 | 0.596 | 3 |
| q036 | Synchronisation | medium | algorithm | 1.000 | 1.000 | 0.600 | 1.000 | 1.000 | 2 |
| q037 | Synchronisation | hard | algorithm | 0.667 | 0.667 | 0.400 | 1.000 | 0.765 | 3 |
| q038 | Synchronisation | medium | conceptual | 0.600 | 0.800 | 0.600 | 1.000 | 0.866 | 2 |
| q039 | Synchronisation | medium | comparative | 0.429 | 0.571 | 0.600 | 1.000 | 0.765 | 2 |
| q040 | Synchronisation | hard | conceptual | 0.625 | 0.875 | 1.000 | 1.000 | 0.897 | 0 |
| q041 | Synchronisation | hard | mechanism | 0.800 | 0.800 | 0.800 | 1.000 | 0.930 | 1 |
| q042 | Synchronisation | medium | conceptual | 0.500 | 0.500 | 0.400 | 1.000 | 0.695 | 3 |
| q043 | Synchronisation | medium | conceptual | 0.500 | 0.500 | 0.400 | 1.000 | 0.682 | 3 |
| q044 | Synchronisation | easy | conceptual | 0.600 | 0.600 | 0.600 | 0.333 | 0.519 | 2 |
| q045 | Synchronisation | easy | mechanism | 0.444 | 0.556 | 0.800 | 1.000 | 0.580 | 1 |
| q046 | Synchronisation | medium | mechanism | 0.333 | 0.500 | 0.400 | 1.000 | 0.558 | 3 |
| q047 | Synchronisation | medium | code | 0.375 | 0.750 | 0.600 | 1.000 | 0.788 | 2 |
| q048 | Synchronisation | hard | conceptual | 0.600 | 0.800 | 0.600 | 1.000 | 0.804 | 2 |
| q049 | Synchronisation | medium | comparative | 0.571 | 0.571 | 0.800 | 1.000 | 0.771 | 1 |
| q050 | Synchronisation | hard | code | 0.250 | 0.750 | 0.200 | 1.000 | 0.727 | 4 |
| q051 | Synchronisation | medium | mechanism | 0.125 | 0.250 | 0.200 | 0.250 | 0.282 | 4 |
| q052 | Synchronisation | easy | mechanism | 0.417 | 0.583 | 1.000 | 1.000 | 0.765 | 0 |
| q053 | Synchronisation | easy | comparative | 0.286 | 0.714 | 0.400 | 1.000 | 0.692 | 3 |
| q054 | Synchronisation | medium | mechanism | 0.400 | 0.400 | 0.800 | 1.000 | 0.536 | 1 |
| q055 | Synchronisation | medium | mechanism | 0.111 | 0.333 | 0.200 | 0.333 | 0.273 | 4 |
| q056 | Synchronisation | medium | mechanism | 0.400 | 0.800 | 0.800 | 1.000 | 0.889 | 1 |
| q057 | Synchronisation | hard | code | 0.500 | 0.500 | 0.200 | 0.333 | 0.307 | 4 |
| q058 | Synchronisation | medium | scenario | 1.000 | 1.000 | 0.400 | 1.000 | 1.000 | 3 |
| q059 | Synchronisation | medium | conceptual | 0.750 | 0.750 | 0.600 | 1.000 | 0.879 | 2 |
| q060 | Synchronisation | medium | comparative | 0.333 | 0.333 | 0.400 | 0.333 | 0.359 | 3 |
| q061 | Synchronisation | hard | comparative | 0.455 | 0.636 | 1.000 | 1.000 | 0.821 | 0 |
| q062 | Synchronisation | easy | classical | 0.417 | 0.500 | 1.000 | 1.000 | 0.759 | 0 |
| q063 | Synchronisation | medium | classical | 0.357 | 0.571 | 1.000 | 1.000 | 0.823 | 0 |
| q064 | Synchronisation | hard | code | 0.286 | 0.571 | 0.400 | 1.000 | 0.611 | 3 |
| q065 | Synchronisation | hard | classical | 0.167 | 0.333 | 0.200 | 0.250 | 0.159 | 4 |
| q066 | Synchronisation | medium | classical | 0.600 | 0.800 | 0.600 | 1.000 | 0.865 | 2 |
| q067 | Synchronisation | easy | classical | 0.556 | 0.889 | 1.000 | 1.000 | 0.885 | 0 |
| q068 | Synchronisation | medium | classical | 0.273 | 0.545 | 0.600 | 1.000 | 0.588 | 2 |
| q069 | Synchronisation | hard | classical | 0.429 | 0.857 | 0.600 | 1.000 | 0.748 | 2 |
| q070 | Synchronisation | hard | code | 0.500 | 0.750 | 0.400 | 1.000 | 0.847 | 3 |
| q071 | Synchronisation | easy | classical | 0.429 | 0.857 | 0.600 | 1.000 | 0.883 | 2 |
| q072 | Synchronisation | medium | classical | 0.400 | 0.500 | 0.800 | 1.000 | 0.619 | 1 |
| q073 | Synchronisation | hard | code | 0.286 | 0.571 | 0.400 | 0.333 | 0.451 | 3 |
| q074 | Synchronisation | easy | conceptual | 1.000 | 1.000 | 0.400 | 1.000 | 1.000 | 3 |
| q075 | Synchronisation | medium | mechanism | 0.200 | 0.600 | 0.200 | 0.500 | 0.473 | 4 |
| q076 | Synchronisation | medium | scenario | 0.429 | 0.571 | 0.600 | 1.000 | 0.611 | 2 |
| q077 | Synchronisation | hard | conceptual | 0.833 | 0.833 | 1.000 | 1.000 | 0.830 | 0 |
| q078 | Synchronisation | medium | comparative | 0.333 | 0.333 | 0.200 | 0.500 | 0.403 | 4 |
| q079 | Synchronisation | medium | comparative | 0.500 | 0.667 | 0.600 | 1.000 | 0.783 | 2 |
| q080 | Synchronisation | hard | code | 0.250 | 0.500 | 0.200 | 1.000 | 0.615 | 4 |
| q081 | Synchronisation | medium | conceptual | 0.250 | 0.250 | 0.400 | 1.000 | 0.493 | 3 |
| q082 | Synchronisation | hard | scenario | 1.000 | 1.000 | 0.200 | 1.000 | 1.000 | 4 |
| q083 | Synchronisation | medium | conceptual | 0.714 | 1.000 | 1.000 | 1.000 | 0.901 | 0 |
| q084 | Synchronisation | medium | conceptual | 0.500 | 0.875 | 0.800 | 1.000 | 0.867 | 1 |
| q085 | Synchronisation | medium | conceptual | 0.667 | 1.000 | 0.800 | 1.000 | 0.941 | 1 |
| q086 | Synchronisation | hard | code | 0.500 | 1.000 | 0.200 | 1.000 | 0.875 | 4 |
| q087 | Synchronisation | medium | algorithm | 0.200 | 0.500 | 0.400 | 1.000 | 0.432 | 3 |
| q088 | Synchronisation | hard | algorithm | 0.500 | 0.500 | 0.400 | 1.000 | 0.778 | 3 |
| q089 | Synchronisation | medium | algorithm | 0.333 | 0.333 | 0.200 | 0.333 | 0.235 | 4 |
| q090 | Synchronisation | medium | algorithm | 0.667 | 1.000 | 0.400 | 1.000 | 0.954 | 3 |
| q091 | Synchronisation | medium | algorithm | 0.000 | 0.143 | 0.000 | 0.000 | 0.104 | 5 |
| q092 | Synchronisation | easy | conceptual | 0.667 | 1.000 | 0.800 | 1.000 | 0.979 | 1 |
| q093 | Synchronisation | medium | scenario | 0.250 | 0.500 | 0.200 | 1.000 | 0.621 | 4 |
| q094 | Synchronisation | hard | scenario | 0.667 | 0.667 | 0.400 | 1.000 | 0.867 | 3 |
| q095 | Synchronisation | hard | scenario | 1.000 | 1.000 | 0.400 | 1.000 | 1.000 | 3 |
| q096 | Synchronisation | hard | code | 0.500 | 0.500 | 0.400 | 1.000 | 0.739 | 3 |
| q097 | Synchronisation | hard | code | 0.400 | 0.400 | 0.400 | 1.000 | 0.642 | 3 |
| q098 | Synchronisation | hard | scenario | 0.600 | 0.800 | 0.600 | 1.000 | 0.885 | 2 |
| q099 | Synchronisation | hard | classical | 1.000 | 1.000 | 0.200 | 1.000 | 1.000 | 4 |
