# Hybrid Dense + BM25 (RRF) Retrieval — Evaluation Report

Run `hybrid_intent_v1.1` at 2026-10-08T18:56:37+00:00. Measurements only; no thresholds or quality claims.

## Configuration

- Corpus: `chunks.jsonl` SHA-256 `90d1e88ef552dfb32b5a8c2d4845cd20399eca82f6669bd184d08eaad8fcbe16` (463 chunks)
- Benchmark: `data\evaluation\retrieval_queries_v1.1.json` version 1.1, SHA-256 `bfbbd033021a154f969d284483b73416c4c7b9b3f1afc126b1609dd650bd5986`
- Retriever: hybrid + intent-aware order; rrf_k=60, 50 candidates per system, equal weights; dense `nomic-embed-text-v1.5` @ `e9b6763023c6`; BM25 k1=1.2, b=0.75; top_k=20, no filters; then intent/identifier reorder (shift {'type': 3, 'identifier': 3})
- Relevance: chunk relevant when judged grade >= 1; nDCG uses grades (2, 1) as linear gains; unjudged = 0; retrieved relevance 0 = judged not relevant, null = unjudged

## Benchmark

- Queries: 99; judgments: 757 (grade 2: 322, grade 1: 435); judged not relevant (grade 0): 1395
- Topic: {'Threads': 21, 'Synchronisation': 78}
- Difficulty: {'easy': 23, 'medium': 48, 'hard': 28}
- Query type: {'conceptual': 26, 'comparative': 11, 'mechanism': 16, 'code': 13, 'scenario': 11, 'algorithm': 12, 'classical': 10}

## Overall metrics (macro-averaged over queries)

| Metric | Value |
| --- | --- |
| recall@1 | 0.132 |
| recall@3 | 0.353 |
| recall@5 | 0.474 |
| recall@10 | 0.642 |
| hit@1 | 0.798 |
| hit@3 | 0.980 |
| hit@5 | 0.990 |
| hit@10 | 1.000 |
| hit@20 | 1.000 |
| precision@5 | 0.636 |
| precision@10 | 0.467 |
| mrr@5 | 0.883 |
| mrr@10 | 0.885 |
| ndcg@5 | 0.701 |
| ndcg@10 | 0.703 |
| map@5 | 0.415 |

Recall@K is the fraction of the judged relevant set found in the top K; queries with many background (grade 1) chunks have a low ceiling for small K (Recall@1 is at most 1/|relevant|). Hit@K is reported separately as the share of queries with at least one relevant chunk in the top K.

## By topic

| Group | Queries | recall@1 | recall@3 | recall@5 | recall@10 | precision@5 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threads | 21 | 0.142 | 0.355 | 0.458 | 0.683 | 0.581 | 0.837 | 0.681 | 0.720 | 0.418 |
| Synchronisation | 78 | 0.129 | 0.352 | 0.478 | 0.631 | 0.651 | 0.895 | 0.707 | 0.698 | 0.414 |

## By difficulty

| Group | Queries | recall@1 | recall@3 | recall@5 | recall@10 | precision@5 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| easy | 23 | 0.134 | 0.344 | 0.445 | 0.640 | 0.713 | 0.957 | 0.755 | 0.748 | 0.421 |
| medium | 48 | 0.125 | 0.336 | 0.484 | 0.642 | 0.675 | 0.885 | 0.715 | 0.706 | 0.427 |
| hard | 28 | 0.140 | 0.388 | 0.481 | 0.644 | 0.507 | 0.819 | 0.633 | 0.660 | 0.388 |

## By query type

| Group | Queries | recall@1 | recall@3 | recall@5 | recall@10 | precision@5 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| conceptual | 26 | 0.143 | 0.377 | 0.494 | 0.644 | 0.685 | 0.942 | 0.731 | 0.726 | 0.468 |
| mechanism | 16 | 0.085 | 0.272 | 0.370 | 0.571 | 0.688 | 0.865 | 0.645 | 0.644 | 0.334 |
| algorithm | 12 | 0.162 | 0.400 | 0.554 | 0.648 | 0.600 | 0.903 | 0.714 | 0.686 | 0.477 |
| classical | 10 | 0.074 | 0.321 | 0.446 | 0.716 | 0.780 | 0.883 | 0.740 | 0.768 | 0.348 |
| code | 13 | 0.134 | 0.336 | 0.434 | 0.557 | 0.508 | 0.795 | 0.612 | 0.616 | 0.363 |
| scenario | 11 | 0.172 | 0.437 | 0.575 | 0.775 | 0.455 | 0.795 | 0.664 | 0.720 | 0.443 |
| comparative | 11 | 0.148 | 0.326 | 0.463 | 0.634 | 0.691 | 0.939 | 0.805 | 0.778 | 0.434 |

## Retrieval failures

- Queries with no relevant chunk in the top 5: 1 (q008)
- Queries with no relevant chunk in the top 10: 0 (none)
- Heuristic failure categories (top-5 failures): {'semantic_mismatch': 1}

## Non-relevant results in the top 5 (heuristic tags)

- Non-relevant (unjudged or grade 0) results in the top 5 across all queries: 180
- Tag counts (a result can carry several tags): exercise_section 6, image_only_unit 9, neighboring_chunk 32, reference_list 2, topically_related_unjudged 130
- `topically_related_unjudged` means the chunk shares a subtopic label with the query; such chunks may be relevant material that the incomplete judgments do not list.

## Judgment coverage

- Mean unjudged results per query: top 5 0.1212, top 10 1.1212 (share of all top-10 results unjudged: 0.1121); top 20 6.7374 (share 0.3369)
- Unjudged results count as non-relevant, so metrics are a lower bound with respect to judgment completeness.

## Duplicates

- Queries with duplicate content in the top 5: 2; in the top 10: 4
- Duplicate pairs in top-10 lists by kind: {'near_duplicate_document': 1, 'exact_duplicate_chunk': 3}

## Notable error cases

Queries where no relevant chunk was retrieved in the top 5 (expected = grade-2 judgments; retrieved = top 3):

- **q008** (hard, code) How can a thread hand a result back to the thread that joins it, and what bug should be avoided when returning it?
  - categories: semantic_mismatch; first relevant rank within top 10: 6
  - expected: threads-api-8ce54688::c0006, threads-api-8ce54688::c0007
  - #1 0.030 threads-intro-c1df7202::c0009 (p.6) 26 Concurrency: An Introduction > 26.3 Why It Gets Worse: Shared Data [topically_related_unjudged]
  - #2 0.029 threads-locks-cb67d3bd::c0028 (p.18) 28 Locks > 28.14 Using Queues: Sleeping Instead Of Spinning
  - #3 0.028 threads-intro-c1df7202::c0017 (p.10) 26 Concurrency: An Introduction > 26.4 The Heart Of The Problem: Uncon

## Per-query results

| Query | Topic | Difficulty | Type | R@5 | R@10 | P@5 | MRR@5 | nDCG@10 | Unjudged@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q001 | Threads | easy | conceptual | 0.182 | 0.273 | 0.400 | 1.000 | 0.501 | 1 |
| q002 | Threads | medium | comparative | 0.385 | 0.462 | 1.000 | 1.000 | 0.804 | 0 |
| q003 | Threads | easy | conceptual | 0.250 | 0.625 | 0.400 | 0.500 | 0.552 | 1 |
| q004 | Threads | easy | comparative | 0.750 | 0.750 | 0.600 | 1.000 | 0.860 | 0 |
| q005 | Threads | medium | mechanism | 0.417 | 0.667 | 1.000 | 1.000 | 0.782 | 0 |
| q006 | Threads | easy | mechanism | 0.429 | 0.714 | 0.600 | 1.000 | 0.653 | 0 |
| q007 | Threads | easy | mechanism | 0.500 | 0.900 | 1.000 | 1.000 | 0.942 | 0 |
| q008 | Threads | hard | code | 0.000 | 0.400 | 0.000 | 0.000 | 0.147 | 0 |
| q009 | Threads | hard | code | 0.250 | 0.250 | 0.200 | 0.333 | 0.239 | 0 |
| q010 | Threads | medium | conceptual | 0.833 | 0.833 | 1.000 | 1.000 | 0.928 | 0 |
| q011 | Threads | medium | mechanism | 0.600 | 0.800 | 0.600 | 1.000 | 0.909 | 0 |
| q012 | Threads | easy | comparative | 0.455 | 0.909 | 1.000 | 1.000 | 0.975 | 0 |
| q013 | Threads | medium | scenario | 0.500 | 1.000 | 0.800 | 1.000 | 0.893 | 0 |
| q014 | Threads | easy | conceptual | 0.429 | 0.571 | 0.600 | 1.000 | 0.789 | 2 |
| q015 | Threads | medium | scenario | 0.333 | 0.667 | 0.200 | 0.500 | 0.513 | 1 |
| q016 | Threads | medium | conceptual | 0.714 | 0.857 | 1.000 | 1.000 | 0.908 | 0 |
| q017 | Threads | medium | conceptual | 0.400 | 0.600 | 0.400 | 1.000 | 0.746 | 0 |
| q018 | Threads | easy | conceptual | 1.000 | 1.000 | 0.400 | 1.000 | 1.000 | 0 |
| q019 | Threads | easy | mechanism | 0.500 | 0.667 | 0.600 | 1.000 | 0.794 | 0 |
| q020 | Threads | hard | scenario | 0.200 | 0.400 | 0.200 | 0.250 | 0.290 | 0 |
| q021 | Threads | hard | scenario | 0.500 | 1.000 | 0.200 | 1.000 | 0.887 | 0 |
| q022 | Synchronisation | easy | conceptual | 0.385 | 0.615 | 1.000 | 1.000 | 0.910 | 0 |
| q023 | Synchronisation | medium | mechanism | 0.294 | 0.471 | 1.000 | 1.000 | 0.625 | 0 |
| q024 | Synchronisation | easy | conceptual | 0.455 | 0.727 | 1.000 | 1.000 | 0.712 | 0 |
| q025 | Synchronisation | easy | conceptual | 0.375 | 0.375 | 0.600 | 1.000 | 0.700 | 0 |
| q026 | Synchronisation | medium | conceptual | 0.625 | 0.875 | 1.000 | 1.000 | 0.898 | 0 |
| q027 | Synchronisation | easy | mechanism | 0.300 | 0.500 | 0.600 | 0.500 | 0.459 | 0 |
| q028 | Synchronisation | medium | code | 0.800 | 0.800 | 0.800 | 1.000 | 0.847 | 0 |
| q029 | Synchronisation | medium | comparative | 0.667 | 0.667 | 0.400 | 1.000 | 0.867 | 0 |
| q030 | Synchronisation | medium | conceptual | 0.375 | 0.500 | 0.600 | 1.000 | 0.655 | 0 |
| q031 | Synchronisation | medium | algorithm | 0.750 | 0.750 | 0.600 | 1.000 | 0.722 | 0 |
| q032 | Synchronisation | easy | algorithm | 0.250 | 0.583 | 0.600 | 1.000 | 0.787 | 0 |
| q033 | Synchronisation | medium | algorithm | 0.273 | 0.455 | 0.600 | 1.000 | 0.622 | 0 |
| q034 | Synchronisation | medium | algorithm | 0.556 | 0.778 | 1.000 | 1.000 | 0.893 | 0 |
| q035 | Synchronisation | hard | algorithm | 0.500 | 0.500 | 0.400 | 1.000 | 0.628 | 0 |
| q036 | Synchronisation | medium | algorithm | 1.000 | 1.000 | 0.600 | 1.000 | 1.000 | 0 |
| q037 | Synchronisation | hard | algorithm | 0.500 | 0.500 | 0.400 | 1.000 | 0.610 | 0 |
| q038 | Synchronisation | medium | conceptual | 0.571 | 0.714 | 0.800 | 1.000 | 0.836 | 0 |
| q039 | Synchronisation | medium | comparative | 0.375 | 0.375 | 0.600 | 1.000 | 0.607 | 0 |
| q040 | Synchronisation | hard | conceptual | 0.444 | 0.667 | 0.800 | 1.000 | 0.789 | 0 |
| q041 | Synchronisation | hard | mechanism | 0.714 | 0.857 | 1.000 | 1.000 | 0.943 | 0 |
| q042 | Synchronisation | medium | conceptual | 0.500 | 0.500 | 0.400 | 1.000 | 0.695 | 0 |
| q043 | Synchronisation | medium | conceptual | 0.333 | 0.500 | 0.400 | 0.500 | 0.494 | 0 |
| q044 | Synchronisation | easy | conceptual | 0.500 | 0.625 | 0.800 | 1.000 | 0.583 | 0 |
| q045 | Synchronisation | easy | mechanism | 0.333 | 0.500 | 0.800 | 1.000 | 0.572 | 0 |
| q046 | Synchronisation | medium | mechanism | 0.286 | 0.286 | 0.400 | 1.000 | 0.304 | 0 |
| q047 | Synchronisation | medium | code | 0.556 | 0.667 | 1.000 | 1.000 | 0.777 | 0 |
| q048 | Synchronisation | hard | conceptual | 0.500 | 0.750 | 0.800 | 1.000 | 0.774 | 0 |
| q049 | Synchronisation | medium | comparative | 0.444 | 0.667 | 0.800 | 1.000 | 0.826 | 0 |
| q050 | Synchronisation | hard | code | 0.429 | 0.857 | 0.600 | 1.000 | 0.874 | 0 |
| q051 | Synchronisation | medium | mechanism | 0.125 | 0.250 | 0.200 | 0.333 | 0.307 | 1 |
| q052 | Synchronisation | easy | mechanism | 0.222 | 0.278 | 0.800 | 1.000 | 0.608 | 0 |
| q053 | Synchronisation | easy | comparative | 0.556 | 0.889 | 1.000 | 1.000 | 0.924 | 0 |
| q054 | Synchronisation | medium | mechanism | 0.273 | 0.636 | 0.600 | 1.000 | 0.689 | 0 |
| q055 | Synchronisation | medium | mechanism | 0.091 | 0.364 | 0.200 | 0.500 | 0.367 | 1 |
| q056 | Synchronisation | medium | mechanism | 0.500 | 0.800 | 1.000 | 1.000 | 0.915 | 0 |
| q057 | Synchronisation | hard | code | 0.500 | 0.500 | 0.200 | 1.000 | 0.613 | 0 |
| q058 | Synchronisation | medium | scenario | 1.000 | 1.000 | 0.400 | 1.000 | 0.907 | 0 |
| q059 | Synchronisation | medium | conceptual | 0.500 | 0.500 | 0.600 | 0.500 | 0.371 | 0 |
| q060 | Synchronisation | medium | comparative | 0.286 | 0.286 | 0.400 | 0.333 | 0.258 | 0 |
| q061 | Synchronisation | hard | comparative | 0.214 | 0.429 | 0.600 | 1.000 | 0.754 | 1 |
| q062 | Synchronisation | easy | classical | 0.333 | 0.533 | 1.000 | 1.000 | 0.869 | 0 |
| q063 | Synchronisation | medium | classical | 0.333 | 0.667 | 1.000 | 1.000 | 0.967 | 0 |
| q064 | Synchronisation | hard | code | 0.400 | 0.500 | 0.800 | 1.000 | 0.749 | 0 |
| q065 | Synchronisation | hard | classical | 0.375 | 0.625 | 0.600 | 0.500 | 0.493 | 0 |
| q066 | Synchronisation | medium | classical | 0.500 | 0.833 | 0.600 | 1.000 | 0.811 | 0 |
| q067 | Synchronisation | easy | classical | 0.385 | 0.615 | 1.000 | 1.000 | 0.858 | 0 |
| q068 | Synchronisation | medium | classical | 0.308 | 0.615 | 0.800 | 1.000 | 0.696 | 0 |
| q069 | Synchronisation | hard | classical | 0.400 | 0.800 | 0.800 | 1.000 | 0.771 | 0 |
| q070 | Synchronisation | hard | code | 0.500 | 0.500 | 0.400 | 1.000 | 0.716 | 0 |
| q071 | Synchronisation | easy | classical | 0.444 | 0.778 | 0.800 | 1.000 | 0.861 | 0 |
| q072 | Synchronisation | medium | classical | 0.385 | 0.692 | 1.000 | 1.000 | 0.852 | 0 |
| q073 | Synchronisation | hard | code | 0.375 | 0.625 | 0.600 | 1.000 | 0.710 | 0 |
| q074 | Synchronisation | easy | conceptual | 1.000 | 1.000 | 0.400 | 1.000 | 1.000 | 0 |
| q075 | Synchronisation | medium | mechanism | 0.333 | 0.444 | 0.600 | 0.500 | 0.438 | 0 |
| q076 | Synchronisation | medium | scenario | 0.444 | 0.667 | 0.800 | 1.000 | 0.826 | 0 |
| q077 | Synchronisation | hard | conceptual | 0.571 | 0.714 | 0.800 | 1.000 | 0.732 | 0 |
| q078 | Synchronisation | medium | comparative | 0.333 | 0.667 | 0.200 | 1.000 | 0.745 | 2 |
| q079 | Synchronisation | medium | comparative | 0.625 | 0.875 | 1.000 | 1.000 | 0.933 | 0 |
| q080 | Synchronisation | hard | code | 0.429 | 0.429 | 0.600 | 0.500 | 0.473 | 0 |
| q081 | Synchronisation | medium | conceptual | 0.222 | 0.333 | 0.400 | 1.000 | 0.610 | 1 |
| q082 | Synchronisation | hard | scenario | 1.000 | 1.000 | 0.200 | 0.500 | 0.631 | 1 |
| q083 | Synchronisation | medium | conceptual | 0.625 | 0.750 | 1.000 | 1.000 | 0.776 | 0 |
| q084 | Synchronisation | medium | conceptual | 0.400 | 0.800 | 0.800 | 1.000 | 0.782 | 0 |
| q085 | Synchronisation | medium | conceptual | 0.455 | 0.727 | 1.000 | 1.000 | 0.859 | 0 |
| q086 | Synchronisation | hard | code | 0.667 | 0.667 | 0.400 | 0.500 | 0.563 | 0 |
| q087 | Synchronisation | medium | algorithm | 0.500 | 0.500 | 1.000 | 1.000 | 0.551 | 0 |
| q088 | Synchronisation | hard | algorithm | 0.429 | 0.714 | 0.600 | 1.000 | 0.819 | 0 |
| q089 | Synchronisation | medium | algorithm | 0.667 | 0.667 | 0.400 | 0.500 | 0.478 | 0 |
| q090 | Synchronisation | medium | algorithm | 1.000 | 1.000 | 0.600 | 1.000 | 0.860 | 0 |
| q091 | Synchronisation | medium | algorithm | 0.222 | 0.333 | 0.400 | 0.333 | 0.258 | 0 |
| q092 | Synchronisation | easy | conceptual | 0.200 | 0.300 | 0.400 | 1.000 | 0.288 | 0 |
| q093 | Synchronisation | medium | scenario | 0.500 | 0.500 | 0.400 | 0.500 | 0.486 | 0 |
| q094 | Synchronisation | hard | scenario | 0.800 | 1.000 | 0.800 | 1.000 | 0.864 | 0 |
| q095 | Synchronisation | hard | scenario | 0.667 | 0.667 | 0.400 | 1.000 | 0.840 | 0 |
| q096 | Synchronisation | hard | code | 0.167 | 0.333 | 0.200 | 1.000 | 0.535 | 0 |
| q097 | Synchronisation | hard | code | 0.571 | 0.714 | 0.800 | 1.000 | 0.771 | 0 |
| q098 | Synchronisation | hard | scenario | 0.375 | 0.625 | 0.600 | 1.000 | 0.779 | 0 |
| q099 | Synchronisation | hard | classical | 1.000 | 1.000 | 0.200 | 0.333 | 0.500 | 0 |
