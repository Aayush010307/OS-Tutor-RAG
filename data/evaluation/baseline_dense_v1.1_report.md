# Baseline Dense Retrieval — Evaluation Report

Run `baseline_dense_v1.1` at 2026-09-21T14:52:28+00:00. Measurements only; no thresholds or quality claims.

## Configuration

- Corpus: `chunks.jsonl` SHA-256 `90d1e88ef552dfb32b5a8c2d4845cd20399eca82f6669bd184d08eaad8fcbe16` (463 chunks)
- Benchmark: `data/evaluation/retrieval_queries_v1.1.json` version 1.1, SHA-256 `bfbbd033021a154f969d284483b73416c4c7b9b3f1afc126b1609dd650bd5986`
- Retriever: dense (Phase 2 baseline, unchanged); `nomic-embed-text-v1.5` @ `e9b6763023c6`, collection `os_tutor_chunks__nomic_embed_text_v1_5` (Cosine), vectors SHA-256 `1d65a77704cc5ecf…`, top_k=10, no filters
- Relevance: chunk relevant when judged grade >= 1; nDCG uses grades (2, 1) as linear gains; unjudged = 0; retrieved relevance 0 = judged not relevant, null = unjudged

## Benchmark

- Queries: 99; judgments: 757 (grade 2: 322, grade 1: 435); judged not relevant (grade 0): 1395
- Topic: {'Threads': 21, 'Synchronisation': 78}
- Difficulty: {'easy': 23, 'medium': 48, 'hard': 28}
- Query type: {'conceptual': 26, 'comparative': 11, 'mechanism': 16, 'code': 13, 'scenario': 11, 'algorithm': 12, 'classical': 10}

## Overall metrics (macro-averaged over queries)

| Metric | Value |
| --- | --- |
| recall@1 | 0.160 |
| recall@3 | 0.346 |
| recall@5 | 0.436 |
| recall@10 | 0.625 |
| hit@1 | 0.879 |
| hit@3 | 0.960 |
| hit@5 | 0.980 |
| hit@10 | 0.980 |
| precision@5 | 0.598 |
| mrr@5 | 0.914 |
| mrr@10 | 0.914 |
| ndcg@5 | 0.695 |
| ndcg@10 | 0.706 |
| map@5 | 0.404 |

Recall@K is the fraction of the judged relevant set found in the top K; queries with many background (grade 1) chunks have a low ceiling for small K (Recall@1 is at most 1/|relevant|). Hit@K is reported separately as the share of queries with at least one relevant chunk in the top K.

## By topic

| Group | Queries | recall@1 | recall@3 | recall@5 | recall@10 | precision@5 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threads | 21 | 0.173 | 0.367 | 0.437 | 0.634 | 0.543 | 0.905 | 0.665 | 0.702 | 0.417 |
| Synchronisation | 78 | 0.157 | 0.341 | 0.436 | 0.622 | 0.613 | 0.917 | 0.703 | 0.707 | 0.400 |

## By difficulty

| Group | Queries | recall@1 | recall@3 | recall@5 | recall@10 | precision@5 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| easy | 23 | 0.144 | 0.355 | 0.450 | 0.623 | 0.739 | 1.000 | 0.807 | 0.767 | 0.437 |
| medium | 48 | 0.137 | 0.331 | 0.422 | 0.613 | 0.600 | 0.908 | 0.667 | 0.690 | 0.385 |
| hard | 28 | 0.213 | 0.365 | 0.450 | 0.645 | 0.479 | 0.854 | 0.652 | 0.683 | 0.409 |

## By query type

| Group | Queries | recall@1 | recall@3 | recall@5 | recall@10 | precision@5 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| conceptual | 26 | 0.160 | 0.387 | 0.529 | 0.684 | 0.746 | 1.000 | 0.806 | 0.779 | 0.506 |
| mechanism | 16 | 0.092 | 0.232 | 0.298 | 0.534 | 0.575 | 0.880 | 0.587 | 0.631 | 0.268 |
| algorithm | 12 | 0.162 | 0.404 | 0.454 | 0.589 | 0.517 | 0.889 | 0.642 | 0.656 | 0.408 |
| classical | 10 | 0.174 | 0.313 | 0.421 | 0.649 | 0.740 | 0.925 | 0.763 | 0.755 | 0.403 |
| code | 13 | 0.138 | 0.303 | 0.365 | 0.574 | 0.415 | 0.821 | 0.555 | 0.611 | 0.305 |
| scenario | 11 | 0.316 | 0.466 | 0.517 | 0.731 | 0.400 | 0.909 | 0.696 | 0.748 | 0.503 |
| comparative | 11 | 0.118 | 0.314 | 0.418 | 0.585 | 0.654 | 0.894 | 0.750 | 0.725 | 0.374 |

## Retrieval failures

- Queries with no relevant chunk in the top 5: 2 (q009, q020)
- Queries with no relevant chunk in the top 10: 2 (q009, q020)
- Heuristic failure categories (top-5 failures): {'semantic_mismatch': 2}

## Non-relevant results in the top 5 (heuristic tags)

- Non-relevant (unjudged or grade 0) results in the top 5 across all queries: 199
- Tag counts (a result can carry several tags): image_only_unit 9, neighboring_chunk 34, reference_list 2, topically_related_unjudged 151
- `topically_related_unjudged` means the chunk shares a subtopic label with the query; such chunks may be relevant material that the incomplete judgments do not list.

## Judgment coverage

- Mean unjudged results per query: top 5 0, top 10 0 (share of all top-10 results unjudged: 0.0)
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

## Per-query results

| Query | Topic | Difficulty | Type | R@5 | R@10 | P@5 | MRR@5 | nDCG@10 | Unjudged@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q001 | Threads | easy | conceptual | 0.273 | 0.545 | 0.600 | 1.000 | 0.660 | 0 |
| q002 | Threads | medium | comparative | 0.308 | 0.692 | 0.800 | 1.000 | 0.932 | 0 |
| q003 | Threads | easy | conceptual | 0.250 | 0.375 | 0.400 | 1.000 | 0.477 | 0 |
| q004 | Threads | easy | comparative | 0.750 | 0.750 | 0.600 | 1.000 | 0.908 | 0 |
| q005 | Threads | medium | mechanism | 0.250 | 0.500 | 0.600 | 1.000 | 0.702 | 0 |
| q006 | Threads | easy | mechanism | 0.286 | 0.286 | 0.400 | 1.000 | 0.433 | 0 |
| q007 | Threads | easy | mechanism | 0.400 | 0.500 | 0.800 | 1.000 | 0.636 | 0 |
| q008 | Threads | hard | code | 0.600 | 0.800 | 0.600 | 1.000 | 0.714 | 0 |
| q009 | Threads | hard | code | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| q010 | Threads | medium | conceptual | 0.667 | 0.833 | 0.800 | 1.000 | 0.886 | 0 |
| q011 | Threads | medium | mechanism | 0.400 | 1.000 | 0.400 | 1.000 | 0.849 | 0 |
| q012 | Threads | easy | comparative | 0.455 | 0.818 | 1.000 | 1.000 | 0.931 | 0 |
| q013 | Threads | medium | scenario | 0.625 | 0.875 | 1.000 | 1.000 | 0.824 | 0 |
| q014 | Threads | easy | conceptual | 0.571 | 0.714 | 0.800 | 1.000 | 0.871 | 0 |
| q015 | Threads | medium | scenario | 0.333 | 0.667 | 0.200 | 1.000 | 0.692 | 0 |
| q016 | Threads | medium | conceptual | 0.571 | 0.857 | 0.800 | 1.000 | 0.900 | 0 |
| q017 | Threads | medium | conceptual | 0.600 | 0.600 | 0.600 | 1.000 | 0.731 | 0 |
| q018 | Threads | easy | conceptual | 1.000 | 1.000 | 0.400 | 1.000 | 1.000 | 0 |
| q019 | Threads | easy | mechanism | 0.333 | 0.500 | 0.400 | 1.000 | 0.719 | 0 |
| q020 | Threads | hard | scenario | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| q021 | Threads | hard | scenario | 0.500 | 1.000 | 0.200 | 1.000 | 0.880 | 0 |
| q022 | Synchronisation | easy | conceptual | 0.385 | 0.538 | 1.000 | 1.000 | 0.765 | 0 |
| q023 | Synchronisation | medium | mechanism | 0.235 | 0.471 | 0.800 | 1.000 | 0.594 | 0 |
| q024 | Synchronisation | easy | conceptual | 0.455 | 0.545 | 1.000 | 1.000 | 0.631 | 0 |
| q025 | Synchronisation | easy | conceptual | 0.375 | 0.500 | 0.600 | 1.000 | 0.748 | 0 |
| q026 | Synchronisation | medium | conceptual | 0.500 | 0.750 | 0.800 | 1.000 | 0.690 | 0 |
| q027 | Synchronisation | easy | mechanism | 0.300 | 0.600 | 0.600 | 1.000 | 0.737 | 0 |
| q028 | Synchronisation | medium | code | 0.600 | 0.600 | 0.600 | 1.000 | 0.793 | 0 |
| q029 | Synchronisation | medium | comparative | 0.333 | 0.333 | 0.200 | 1.000 | 0.532 | 0 |
| q030 | Synchronisation | medium | conceptual | 0.625 | 0.625 | 1.000 | 1.000 | 0.753 | 0 |
| q031 | Synchronisation | medium | algorithm | 0.500 | 0.750 | 0.400 | 1.000 | 0.715 | 0 |
| q032 | Synchronisation | easy | algorithm | 0.417 | 0.750 | 1.000 | 1.000 | 0.948 | 0 |
| q033 | Synchronisation | medium | algorithm | 0.455 | 0.636 | 1.000 | 1.000 | 0.725 | 0 |
| q034 | Synchronisation | medium | algorithm | 0.333 | 0.444 | 0.600 | 1.000 | 0.701 | 0 |
| q035 | Synchronisation | hard | algorithm | 0.500 | 0.500 | 0.400 | 1.000 | 0.596 | 0 |
| q036 | Synchronisation | medium | algorithm | 1.000 | 1.000 | 0.600 | 1.000 | 1.000 | 0 |
| q037 | Synchronisation | hard | algorithm | 0.500 | 0.500 | 0.400 | 1.000 | 0.695 | 0 |
| q038 | Synchronisation | medium | conceptual | 0.571 | 0.714 | 0.800 | 1.000 | 0.845 | 0 |
| q039 | Synchronisation | medium | comparative | 0.500 | 0.625 | 0.800 | 1.000 | 0.789 | 0 |
| q040 | Synchronisation | hard | conceptual | 0.556 | 0.778 | 1.000 | 1.000 | 0.858 | 0 |
| q041 | Synchronisation | hard | mechanism | 0.571 | 0.714 | 0.800 | 1.000 | 0.877 | 0 |
| q042 | Synchronisation | medium | conceptual | 0.500 | 0.500 | 0.400 | 1.000 | 0.695 | 0 |
| q043 | Synchronisation | medium | conceptual | 0.333 | 0.333 | 0.400 | 1.000 | 0.580 | 0 |
| q044 | Synchronisation | easy | conceptual | 0.500 | 0.500 | 0.800 | 1.000 | 0.597 | 0 |
| q045 | Synchronisation | easy | mechanism | 0.333 | 0.417 | 0.800 | 1.000 | 0.555 | 0 |
| q046 | Synchronisation | medium | mechanism | 0.286 | 0.571 | 0.400 | 1.000 | 0.581 | 0 |
| q047 | Synchronisation | medium | code | 0.333 | 0.667 | 0.600 | 1.000 | 0.755 | 0 |
| q048 | Synchronisation | hard | conceptual | 0.500 | 0.875 | 0.800 | 1.000 | 0.849 | 0 |
| q049 | Synchronisation | medium | comparative | 0.444 | 0.667 | 0.800 | 1.000 | 0.800 | 0 |
| q050 | Synchronisation | hard | code | 0.429 | 0.714 | 0.600 | 1.000 | 0.759 | 0 |
| q051 | Synchronisation | medium | mechanism | 0.125 | 0.250 | 0.200 | 0.250 | 0.282 | 0 |
| q052 | Synchronisation | easy | mechanism | 0.278 | 0.556 | 1.000 | 1.000 | 0.873 | 0 |
| q053 | Synchronisation | easy | comparative | 0.333 | 0.667 | 0.600 | 1.000 | 0.686 | 0 |
| q054 | Synchronisation | medium | mechanism | 0.364 | 0.455 | 0.800 | 1.000 | 0.584 | 0 |
| q055 | Synchronisation | medium | mechanism | 0.091 | 0.364 | 0.200 | 0.333 | 0.314 | 0 |
| q056 | Synchronisation | medium | mechanism | 0.400 | 0.800 | 0.800 | 1.000 | 0.889 | 0 |
| q057 | Synchronisation | hard | code | 0.500 | 0.500 | 0.200 | 0.333 | 0.307 | 0 |
| q058 | Synchronisation | medium | scenario | 1.000 | 1.000 | 0.400 | 1.000 | 1.000 | 0 |
| q059 | Synchronisation | medium | conceptual | 0.500 | 0.833 | 0.600 | 1.000 | 0.867 | 0 |
| q060 | Synchronisation | medium | comparative | 0.286 | 0.429 | 0.400 | 0.333 | 0.404 | 0 |
| q061 | Synchronisation | hard | comparative | 0.357 | 0.500 | 1.000 | 1.000 | 0.821 | 0 |
| q062 | Synchronisation | easy | classical | 0.333 | 0.467 | 1.000 | 1.000 | 0.796 | 0 |
| q063 | Synchronisation | medium | classical | 0.333 | 0.600 | 1.000 | 1.000 | 0.862 | 0 |
| q064 | Synchronisation | hard | code | 0.300 | 0.600 | 0.600 | 1.000 | 0.634 | 0 |
| q065 | Synchronisation | hard | classical | 0.125 | 0.375 | 0.200 | 0.250 | 0.197 | 0 |
| q066 | Synchronisation | medium | classical | 0.500 | 0.667 | 0.600 | 1.000 | 0.808 | 0 |
| q067 | Synchronisation | easy | classical | 0.385 | 0.615 | 1.000 | 1.000 | 0.853 | 0 |
| q068 | Synchronisation | medium | classical | 0.308 | 0.538 | 0.800 | 1.000 | 0.635 | 0 |
| q069 | Synchronisation | hard | classical | 0.400 | 0.800 | 0.800 | 1.000 | 0.764 | 0 |
| q070 | Synchronisation | hard | code | 0.500 | 0.750 | 0.400 | 1.000 | 0.847 | 0 |
| q071 | Synchronisation | easy | classical | 0.444 | 0.889 | 0.800 | 1.000 | 0.915 | 0 |
| q072 | Synchronisation | medium | classical | 0.385 | 0.538 | 1.000 | 1.000 | 0.723 | 0 |
| q073 | Synchronisation | hard | code | 0.250 | 0.500 | 0.400 | 0.333 | 0.431 | 0 |
| q074 | Synchronisation | easy | conceptual | 1.000 | 1.000 | 0.400 | 1.000 | 1.000 | 0 |
| q075 | Synchronisation | medium | mechanism | 0.111 | 0.556 | 0.200 | 0.500 | 0.469 | 0 |
| q076 | Synchronisation | medium | scenario | 0.333 | 0.444 | 0.600 | 1.000 | 0.547 | 0 |
| q077 | Synchronisation | hard | conceptual | 0.714 | 0.857 | 1.000 | 1.000 | 0.834 | 0 |
| q078 | Synchronisation | medium | comparative | 0.333 | 0.333 | 0.200 | 0.500 | 0.403 | 0 |
| q079 | Synchronisation | medium | comparative | 0.500 | 0.625 | 0.800 | 1.000 | 0.771 | 0 |
| q080 | Synchronisation | hard | code | 0.286 | 0.571 | 0.400 | 1.000 | 0.620 | 0 |
| q081 | Synchronisation | medium | conceptual | 0.222 | 0.222 | 0.400 | 1.000 | 0.470 | 0 |
| q082 | Synchronisation | hard | scenario | 1.000 | 1.000 | 0.200 | 1.000 | 1.000 | 0 |
| q083 | Synchronisation | medium | conceptual | 0.625 | 0.875 | 1.000 | 1.000 | 0.855 | 0 |
| q084 | Synchronisation | medium | conceptual | 0.500 | 0.800 | 1.000 | 1.000 | 0.850 | 0 |
| q085 | Synchronisation | medium | conceptual | 0.455 | 0.818 | 1.000 | 1.000 | 0.927 | 0 |
| q086 | Synchronisation | hard | code | 0.333 | 1.000 | 0.200 | 1.000 | 0.849 | 0 |
| q087 | Synchronisation | medium | algorithm | 0.200 | 0.500 | 0.400 | 1.000 | 0.432 | 0 |
| q088 | Synchronisation | hard | algorithm | 0.429 | 0.429 | 0.600 | 1.000 | 0.701 | 0 |
| q089 | Synchronisation | medium | algorithm | 0.333 | 0.333 | 0.200 | 0.333 | 0.235 | 0 |
| q090 | Synchronisation | medium | algorithm | 0.667 | 1.000 | 0.400 | 1.000 | 0.954 | 0 |
| q091 | Synchronisation | medium | algorithm | 0.111 | 0.222 | 0.200 | 0.333 | 0.173 | 0 |
| q092 | Synchronisation | easy | conceptual | 0.500 | 0.800 | 1.000 | 1.000 | 0.905 | 0 |
| q093 | Synchronisation | medium | scenario | 0.250 | 0.500 | 0.200 | 1.000 | 0.621 | 0 |
| q094 | Synchronisation | hard | scenario | 0.600 | 0.800 | 0.600 | 1.000 | 0.866 | 0 |
| q095 | Synchronisation | hard | scenario | 0.667 | 1.000 | 0.400 | 1.000 | 0.954 | 0 |
| q096 | Synchronisation | hard | code | 0.333 | 0.333 | 0.400 | 1.000 | 0.611 | 0 |
| q097 | Synchronisation | hard | code | 0.286 | 0.429 | 0.400 | 1.000 | 0.620 | 0 |
| q098 | Synchronisation | hard | scenario | 0.375 | 0.750 | 0.600 | 1.000 | 0.849 | 0 |
| q099 | Synchronisation | hard | classical | 1.000 | 1.000 | 0.200 | 1.000 | 1.000 | 0 |
