"""Standard retrieval metrics for one ranked list against graded judgments.

`ranked` is the list of retrieved chunk ids (rank 1 first). `qrels` maps chunk id -> grade (2 directly
relevant, 1 background); unjudged chunks count as grade 0. A chunk is "relevant" when its grade is >= 1.
Per-query values are macro-averaged over queries by the evaluator.

- Recall@K     = |relevant in top K| / |relevant|            (how much of the known relevant set is found)
- Hit@K        = 1 if any relevant chunk is in the top K     (success@K; not the same thing as recall)
- Precision@K  = |relevant in top K| / K                     (K is the denominator even if fewer are returned)
- MRR@K        = 1 / rank of the first relevant chunk within the top K, else 0
- nDCG@K       = DCG@K / IDCG@K, DCG = sum(grade_i / log2(i + 1)) over ranks i <= K, IDCG from the judged
                 grades sorted descending (linear gain, as in trec_eval / BEIR)
- MAP@K (AP@K) = (sum of Precision@i over ranks i <= K holding a relevant chunk) / |relevant|
                 (trec_eval map_cut convention: the denominator is the full relevant set)
"""
import math


def _relevant(qrels):
    return {c for c, g in qrels.items() if g > 0}


def recall_at_k(ranked, qrels, k):
    rel = _relevant(qrels)
    return len(set(ranked[:k]) & rel) / len(rel) if rel else 0.0


def hit_at_k(ranked, qrels, k):
    return float(any(qrels.get(c, 0) > 0 for c in ranked[:k]))


def precision_at_k(ranked, qrels, k):
    return sum(qrels.get(c, 0) > 0 for c in ranked[:k]) / k


def mrr_at_k(ranked, qrels, k):
    return next((1 / i for i, c in enumerate(ranked[:k], 1) if qrels.get(c, 0) > 0), 0.0)


def _dcg(gains):
    return sum(g / math.log2(i + 1) for i, g in enumerate(gains, 1))


def ndcg_at_k(ranked, qrels, k):
    ideal = _dcg(sorted(qrels.values(), reverse=True)[:k])
    return _dcg([qrels.get(c, 0) for c in ranked[:k]]) / ideal if ideal else 0.0


def average_precision_at_k(ranked, qrels, k):
    rel = _relevant(qrels)
    if not rel:
        return 0.0
    hits, total = 0, 0.0
    for i, c in enumerate(ranked[:k], 1):
        if c in rel:
            hits += 1
            total += hits / i
    return total / len(rel)


def all_metrics(ranked, qrels, depth=10):
    """The metric set reported for every query. Runs retrieving >= 20 results also get Precision@10 and Hit@20
    (added for E1); depth-10 runs keep the Phase 3A set, so the frozen v1.0/v1.1 outputs stay reproducible."""
    deep = depth >= 20
    m = {f"recall@{k}": recall_at_k(ranked, qrels, k) for k in (1, 3, 5, 10)}
    m.update({f"hit@{k}": hit_at_k(ranked, qrels, k) for k in (1, 3, 5, 10) + ((20,) if deep else ())})
    m["precision@5"] = precision_at_k(ranked, qrels, 5)
    if deep:
        m["precision@10"] = precision_at_k(ranked, qrels, 10)
    m.update({"mrr@5": mrr_at_k(ranked, qrels, 5), "mrr@10": mrr_at_k(ranked, qrels, 10),
              "ndcg@5": ndcg_at_k(ranked, qrels, 5), "ndcg@10": ndcg_at_k(ranked, qrels, 10),
              "map@5": average_precision_at_k(ranked, qrels, 5)})
    return m
