# Hybrid Dense + BM25 (RRF) Retrieval — Evaluation Report

Run `rerank_v1.1` at 2026-10-08T18:56:24+00:00. Measurements only; no thresholds or quality claims.

## Configuration

- Corpus: `chunks.jsonl` SHA-256 `90d1e88ef552dfb32b5a8c2d4845cd20399eca82f6669bd184d08eaad8fcbe16` (463 chunks)
- Benchmark: `data\evaluation\retrieval_queries_v1.1.json` version 1.1, SHA-256 `bfbbd033021a154f969d284483b73416c4c7b9b3f1afc126b1609dd650bd5986`
- Retriever: hybrid + cross-encoder rerank; rrf_k=60, 50 candidates per system, equal weights; dense `nomic-embed-text-v1.5` @ `e9b6763023c6`; BM25 k1=1.2, b=0.75; top_k=20, no filters; then cross-encoder rerank of the top 20 (ms-marco-MiniLM-L-6-v2 @ 233902d25c44)
- Relevance: chunk relevant when judged grade >= 1; nDCG uses grades (2, 1) as linear gains; unjudged = 0; retrieved relevance 0 = judged not relevant, null = unjudged

## Benchmark

- Queries: 99; judgments: 757 (grade 2: 322, grade 1: 435); judged not relevant (grade 0): 1395
- Topic: {'Threads': 21, 'Synchronisation': 78}
- Difficulty: {'easy': 23, 'medium': 48, 'hard': 28}
- Query type: {'conceptual': 26, 'comparative': 11, 'mechanism': 16, 'code': 13, 'scenario': 11, 'algorithm': 12, 'classical': 10}

## Overall metrics (macro-averaged over queries)

| Metric | Value |
| --- | --- |
| recall@1 | 0.170 |
| recall@3 | 0.372 |
| recall@5 | 0.482 |
| recall@10 | 0.657 |
| hit@1 | 0.899 |
| hit@3 | 0.990 |
| hit@5 | 0.990 |
| hit@10 | 1.000 |
| hit@20 | 1.000 |
| precision@5 | 0.648 |
| precision@10 | 0.469 |
| mrr@5 | 0.938 |
| mrr@10 | 0.939 |
| ndcg@5 | 0.746 |
| ndcg@10 | 0.744 |
| map@5 | 0.449 |

Recall@K is the fraction of the judged relevant set found in the top K; queries with many background (grade 1) chunks have a low ceiling for small K (Recall@1 is at most 1/|relevant|). Hit@K is reported separately as the share of queries with at least one relevant chunk in the top K.

## By topic

| Group | Queries | recall@1 | recall@3 | recall@5 | recall@10 | precision@5 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threads | 21 | 0.195 | 0.411 | 0.512 | 0.693 | 0.629 | 1.000 | 0.773 | 0.780 | 0.487 |
| Synchronisation | 78 | 0.163 | 0.361 | 0.474 | 0.647 | 0.654 | 0.921 | 0.738 | 0.734 | 0.439 |

## By difficulty

| Group | Queries | recall@1 | recall@3 | recall@5 | recall@10 | precision@5 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| easy | 23 | 0.144 | 0.361 | 0.473 | 0.644 | 0.774 | 1.000 | 0.824 | 0.777 | 0.466 |
| medium | 48 | 0.136 | 0.339 | 0.459 | 0.657 | 0.646 | 0.882 | 0.700 | 0.718 | 0.416 |
| hard | 28 | 0.247 | 0.437 | 0.530 | 0.668 | 0.550 | 0.982 | 0.759 | 0.763 | 0.492 |

## By query type

| Group | Queries | recall@1 | recall@3 | recall@5 | recall@10 | precision@5 | mrr@5 | ndcg@5 | ndcg@10 | map@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| conceptual | 26 | 0.150 | 0.382 | 0.495 | 0.640 | 0.685 | 0.955 | 0.771 | 0.745 | 0.475 |
| mechanism | 16 | 0.092 | 0.268 | 0.390 | 0.582 | 0.725 | 0.865 | 0.672 | 0.677 | 0.363 |
| algorithm | 12 | 0.162 | 0.379 | 0.537 | 0.695 | 0.617 | 0.903 | 0.712 | 0.712 | 0.460 |
| classical | 10 | 0.187 | 0.314 | 0.448 | 0.659 | 0.800 | 1.000 | 0.828 | 0.799 | 0.433 |
| code | 13 | 0.186 | 0.405 | 0.473 | 0.587 | 0.508 | 0.962 | 0.690 | 0.696 | 0.425 |
| scenario | 11 | 0.334 | 0.520 | 0.572 | 0.787 | 0.473 | 1.000 | 0.815 | 0.845 | 0.556 |
| comparative | 11 | 0.138 | 0.356 | 0.479 | 0.713 | 0.691 | 0.894 | 0.751 | 0.780 | 0.439 |

## Retrieval failures

- Queries with no relevant chunk in the top 5: 1 (q051)
- Queries with no relevant chunk in the top 10: 0 (none)
- Heuristic failure categories (top-5 failures): {'semantic_mismatch': 1}

## Non-relevant results in the top 5 (heuristic tags)

- Non-relevant (unjudged or grade 0) results in the top 5 across all queries: 174
- Tag counts (a result can carry several tags): exercise_section 4, image_only_unit 8, neighboring_chunk 25, reference_list 2, topically_related_unjudged 133
- `topically_related_unjudged` means the chunk shares a subtopic label with the query; such chunks may be relevant material that the incomplete judgments do not list.

## Judgment coverage

- Mean unjudged results per query: top 5 0.3333, top 10 1.6061 (share of all top-10 results unjudged: 0.1606); top 20 6.7374 (share 0.3369)
- Unjudged results count as non-relevant, so metrics are a lower bound with respect to judgment completeness.

## Duplicates

- Queries with duplicate content in the top 5: 4; in the top 10: 7
- Duplicate pairs in top-10 lists by kind: {'near_duplicate_document': 5, 'exact_duplicate_chunk': 2}

## Notable error cases

Queries where no relevant chunk was retrieved in the top 5 (expected = grade-2 judgments; retrieved = top 3):

- **q051** (medium, mechanism) When should pthread_cond_broadcast be used instead of pthread_cond_signal?
  - categories: semantic_mismatch; first relevant rank within top 10: 10
  - expected: threads-cv-3156a56b::c0021, threads-cv-3156a56b::c0022
  - #1 0.032 threads-api-8ce54688::c0015 (p.8-9) 27 Interlude: Thread API > 27.4 Condition Variables [topically_related_unjudged]
  - #2 0.029 threads-api-8ce54688::c0013 (p.7-8) 27 Interlude: Thread API > 27.4 Condition Variables [topically_related_unjudged]
  - #3 0.024 threads-cv-3156a56b::c0018 (p.12-14) 30 Condition Variables > The Single Buffer Producer/Consumer Solution [topically_related_unjudged]

## Per-query results

| Query | Topic | Difficulty | Type | R@5 | R@10 | P@5 | MRR@5 | nDCG@10 | Unjudged@5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q001 | Threads | easy | conceptual | 0.364 | 0.455 | 0.800 | 1.000 | 0.654 | 0 |
| q002 | Threads | medium | comparative | 0.385 | 0.538 | 1.000 | 1.000 | 0.854 | 0 |
| q003 | Threads | easy | conceptual | 0.250 | 0.375 | 0.400 | 1.000 | 0.506 | 2 |
| q004 | Threads | easy | comparative | 0.750 | 0.750 | 0.600 | 1.000 | 0.908 | 0 |
| q005 | Threads | medium | mechanism | 0.417 | 0.583 | 1.000 | 1.000 | 0.802 | 0 |
| q006 | Threads | easy | mechanism | 0.286 | 0.714 | 0.400 | 1.000 | 0.652 | 0 |
| q007 | Threads | easy | mechanism | 0.400 | 0.700 | 0.800 | 1.000 | 0.760 | 1 |
| q008 | Threads | hard | code | 0.600 | 0.600 | 0.600 | 1.000 | 0.412 | 0 |
| q009 | Threads | hard | code | 0.250 | 0.250 | 0.200 | 1.000 | 0.477 | 0 |
| q010 | Threads | medium | conceptual | 0.667 | 0.833 | 0.800 | 1.000 | 0.899 | 0 |
| q011 | Threads | medium | mechanism | 0.800 | 0.800 | 0.800 | 1.000 | 0.915 | 0 |
| q012 | Threads | easy | comparative | 0.455 | 0.818 | 1.000 | 1.000 | 0.923 | 0 |
| q013 | Threads | medium | scenario | 0.500 | 0.875 | 0.800 | 1.000 | 0.788 | 0 |
| q014 | Threads | easy | conceptual | 0.429 | 0.571 | 0.600 | 1.000 | 0.791 | 0 |
| q015 | Threads | medium | scenario | 0.667 | 1.000 | 0.400 | 1.000 | 0.947 | 2 |
| q016 | Threads | medium | conceptual | 0.571 | 0.857 | 0.800 | 1.000 | 0.923 | 0 |
| q017 | Threads | medium | conceptual | 0.400 | 0.600 | 0.400 | 1.000 | 0.757 | 1 |
| q018 | Threads | easy | conceptual | 1.000 | 1.000 | 0.400 | 1.000 | 1.000 | 0 |
| q019 | Threads | easy | mechanism | 0.667 | 0.833 | 0.800 | 1.000 | 0.902 | 1 |
| q020 | Threads | hard | scenario | 0.400 | 0.400 | 0.400 | 1.000 | 0.633 | 1 |
| q021 | Threads | hard | scenario | 0.500 | 1.000 | 0.200 | 1.000 | 0.887 | 0 |
| q022 | Synchronisation | easy | conceptual | 0.385 | 0.538 | 1.000 | 1.000 | 0.777 | 0 |
| q023 | Synchronisation | medium | mechanism | 0.294 | 0.529 | 1.000 | 1.000 | 0.652 | 0 |
| q024 | Synchronisation | easy | conceptual | 0.364 | 0.636 | 0.800 | 1.000 | 0.747 | 0 |
| q025 | Synchronisation | easy | conceptual | 0.375 | 0.500 | 0.600 | 1.000 | 0.752 | 0 |
| q026 | Synchronisation | medium | conceptual | 0.375 | 0.750 | 0.600 | 1.000 | 0.780 | 1 |
| q027 | Synchronisation | easy | mechanism | 0.400 | 0.700 | 0.800 | 1.000 | 0.758 | 0 |
| q028 | Synchronisation | medium | code | 0.600 | 0.600 | 0.600 | 1.000 | 0.763 | 0 |
| q029 | Synchronisation | medium | comparative | 0.667 | 1.000 | 0.400 | 1.000 | 0.962 | 0 |
| q030 | Synchronisation | medium | conceptual | 0.500 | 0.500 | 0.800 | 1.000 | 0.670 | 0 |
| q031 | Synchronisation | medium | algorithm | 0.500 | 1.000 | 0.400 | 1.000 | 0.801 | 0 |
| q032 | Synchronisation | easy | algorithm | 0.417 | 0.667 | 1.000 | 1.000 | 0.866 | 0 |
| q033 | Synchronisation | medium | algorithm | 0.455 | 0.545 | 1.000 | 1.000 | 0.660 | 0 |
| q034 | Synchronisation | medium | algorithm | 0.444 | 0.667 | 0.800 | 1.000 | 0.840 | 0 |
| q035 | Synchronisation | hard | algorithm | 0.500 | 0.750 | 0.400 | 1.000 | 0.723 | 1 |
| q036 | Synchronisation | medium | algorithm | 1.000 | 1.000 | 0.600 | 1.000 | 1.000 | 0 |
| q037 | Synchronisation | hard | algorithm | 0.750 | 0.750 | 0.600 | 1.000 | 0.860 | 0 |
| q038 | Synchronisation | medium | conceptual | 0.429 | 0.571 | 0.600 | 1.000 | 0.740 | 0 |
| q039 | Synchronisation | medium | comparative | 0.375 | 0.375 | 0.600 | 1.000 | 0.618 | 1 |
| q040 | Synchronisation | hard | conceptual | 0.444 | 0.556 | 0.800 | 1.000 | 0.710 | 0 |
| q041 | Synchronisation | hard | mechanism | 0.571 | 0.714 | 0.800 | 1.000 | 0.875 | 0 |
| q042 | Synchronisation | medium | conceptual | 1.000 | 1.000 | 0.800 | 1.000 | 0.991 | 0 |
| q043 | Synchronisation | medium | conceptual | 0.333 | 0.333 | 0.400 | 1.000 | 0.661 | 0 |
| q044 | Synchronisation | easy | conceptual | 0.625 | 0.625 | 1.000 | 1.000 | 0.734 | 0 |
| q045 | Synchronisation | easy | mechanism | 0.417 | 0.500 | 1.000 | 1.000 | 0.675 | 0 |
| q046 | Synchronisation | medium | mechanism | 0.429 | 0.429 | 0.600 | 1.000 | 0.510 | 0 |
| q047 | Synchronisation | medium | code | 0.444 | 0.556 | 0.800 | 1.000 | 0.666 | 0 |
| q048 | Synchronisation | hard | conceptual | 0.625 | 0.875 | 1.000 | 1.000 | 0.855 | 0 |
| q049 | Synchronisation | medium | comparative | 0.222 | 0.667 | 0.400 | 0.500 | 0.556 | 0 |
| q050 | Synchronisation | hard | code | 0.429 | 0.857 | 0.600 | 1.000 | 0.874 | 0 |
| q051 | Synchronisation | medium | mechanism | 0.000 | 0.125 | 0.000 | 0.000 | 0.104 | 2 |
| q052 | Synchronisation | easy | mechanism | 0.278 | 0.333 | 1.000 | 1.000 | 0.719 | 0 |
| q053 | Synchronisation | easy | comparative | 0.556 | 0.889 | 1.000 | 1.000 | 0.886 | 0 |
| q054 | Synchronisation | medium | mechanism | 0.364 | 0.636 | 0.800 | 1.000 | 0.749 | 0 |
| q055 | Synchronisation | medium | mechanism | 0.091 | 0.364 | 0.200 | 0.333 | 0.322 | 1 |
| q056 | Synchronisation | medium | mechanism | 0.500 | 0.800 | 1.000 | 1.000 | 0.901 | 0 |
| q057 | Synchronisation | hard | code | 1.000 | 1.000 | 0.400 | 1.000 | 1.000 | 1 |
| q058 | Synchronisation | medium | scenario | 0.500 | 1.000 | 0.200 | 1.000 | 0.875 | 1 |
| q059 | Synchronisation | medium | conceptual | 0.167 | 0.500 | 0.200 | 0.333 | 0.426 | 2 |
| q060 | Synchronisation | medium | comparative | 0.286 | 0.571 | 0.400 | 0.333 | 0.402 | 0 |
| q061 | Synchronisation | hard | comparative | 0.286 | 0.571 | 0.800 | 1.000 | 0.891 | 1 |
| q062 | Synchronisation | easy | classical | 0.333 | 0.533 | 1.000 | 1.000 | 0.873 | 0 |
| q063 | Synchronisation | medium | classical | 0.333 | 0.667 | 1.000 | 1.000 | 1.000 | 0 |
| q064 | Synchronisation | hard | code | 0.400 | 0.500 | 0.800 | 1.000 | 0.743 | 0 |
| q065 | Synchronisation | hard | classical | 0.375 | 0.500 | 0.600 | 1.000 | 0.482 | 1 |
| q066 | Synchronisation | medium | classical | 0.333 | 0.667 | 0.400 | 1.000 | 0.617 | 0 |
| q067 | Synchronisation | easy | classical | 0.385 | 0.692 | 1.000 | 1.000 | 0.871 | 0 |
| q068 | Synchronisation | medium | classical | 0.385 | 0.615 | 1.000 | 1.000 | 0.838 | 0 |
| q069 | Synchronisation | hard | classical | 0.400 | 0.600 | 0.800 | 1.000 | 0.727 | 0 |
| q070 | Synchronisation | hard | code | 0.500 | 0.500 | 0.400 | 0.500 | 0.539 | 0 |
| q071 | Synchronisation | easy | classical | 0.556 | 0.778 | 1.000 | 1.000 | 0.865 | 0 |
| q072 | Synchronisation | medium | classical | 0.385 | 0.538 | 1.000 | 1.000 | 0.717 | 0 |
| q073 | Synchronisation | hard | code | 0.375 | 0.625 | 0.600 | 1.000 | 0.726 | 0 |
| q074 | Synchronisation | easy | conceptual | 1.000 | 1.000 | 0.400 | 1.000 | 1.000 | 0 |
| q075 | Synchronisation | medium | mechanism | 0.333 | 0.556 | 0.600 | 0.500 | 0.541 | 0 |
| q076 | Synchronisation | medium | scenario | 0.333 | 0.667 | 0.600 | 1.000 | 0.801 | 1 |
| q077 | Synchronisation | hard | conceptual | 0.571 | 0.714 | 0.800 | 1.000 | 0.752 | 0 |
| q078 | Synchronisation | medium | comparative | 0.667 | 0.667 | 0.400 | 1.000 | 0.595 | 0 |
| q079 | Synchronisation | medium | comparative | 0.625 | 1.000 | 1.000 | 1.000 | 0.985 | 0 |
| q080 | Synchronisation | hard | code | 0.286 | 0.429 | 0.400 | 1.000 | 0.674 | 0 |
| q081 | Synchronisation | medium | conceptual | 0.222 | 0.333 | 0.400 | 0.500 | 0.466 | 3 |
| q082 | Synchronisation | hard | scenario | 1.000 | 1.000 | 0.200 | 1.000 | 1.000 | 1 |
| q083 | Synchronisation | medium | conceptual | 0.625 | 0.875 | 1.000 | 1.000 | 0.925 | 0 |
| q084 | Synchronisation | medium | conceptual | 0.500 | 0.800 | 1.000 | 1.000 | 0.837 | 0 |
| q085 | Synchronisation | medium | conceptual | 0.455 | 0.636 | 1.000 | 1.000 | 0.784 | 0 |
| q086 | Synchronisation | hard | code | 0.667 | 0.667 | 0.400 | 1.000 | 0.798 | 0 |
| q087 | Synchronisation | medium | algorithm | 0.400 | 0.500 | 0.800 | 1.000 | 0.548 | 0 |
| q088 | Synchronisation | hard | algorithm | 0.429 | 0.571 | 0.600 | 1.000 | 0.760 | 0 |
| q089 | Synchronisation | medium | algorithm | 0.333 | 0.667 | 0.200 | 1.000 | 0.626 | 0 |
| q090 | Synchronisation | medium | algorithm | 1.000 | 1.000 | 0.600 | 0.500 | 0.658 | 1 |
| q091 | Synchronisation | medium | algorithm | 0.222 | 0.222 | 0.400 | 0.333 | 0.199 | 0 |
| q092 | Synchronisation | easy | conceptual | 0.200 | 0.200 | 0.400 | 1.000 | 0.244 | 1 |
| q093 | Synchronisation | medium | scenario | 0.500 | 0.500 | 0.400 | 1.000 | 0.778 | 0 |
| q094 | Synchronisation | hard | scenario | 0.600 | 0.800 | 0.600 | 1.000 | 0.866 | 1 |
| q095 | Synchronisation | hard | scenario | 0.667 | 0.667 | 0.400 | 1.000 | 0.840 | 1 |
| q096 | Synchronisation | hard | code | 0.167 | 0.333 | 0.200 | 1.000 | 0.542 | 2 |
| q097 | Synchronisation | hard | code | 0.429 | 0.714 | 0.600 | 1.000 | 0.830 | 0 |
| q098 | Synchronisation | hard | scenario | 0.625 | 0.750 | 1.000 | 1.000 | 0.877 | 0 |
| q099 | Synchronisation | hard | classical | 1.000 | 1.000 | 0.200 | 1.000 | 1.000 | 2 |
