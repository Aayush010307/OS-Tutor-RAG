"""Side-by-side comparison of two evaluator runs on the same benchmark (Phase 3B experiments).

    python3 -m src.evaluation.compare data/evaluation/e1_bm25/dense_v1.1_top20_results.json \\
        data/evaluation/e1_bm25/bm25_v1.1_results.json --output data/evaluation/e1_bm25/comparison.md

Refuses runs that differ in benchmark, corpus, query set, depth or metric definitions. Reports numbers and the
retrieved chunks with their judgments; it declares no winner. Differences are B - A.
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path
import json

from . import metrics

METRICS = ("precision@5", "precision@10", "recall@5", "recall@10", "mrr@5", "ndcg@5", "ndcg@10", "map@5")
HITS = (1, 3, 5, 10, 20)
GROUPS = (("topic", "Topic"), ("difficulty", "Difficulty"), ("query_type", "Query type"))
DEEP = ("q009", "q020", "q091")
NEAR_DUP_DOCS = ("lecture15-918b182c", "semaphore-ppt-copy-0dcb4a42")
CATEGORIES = {  # same section rules as the evaluator's error tags, plus practice problems and the near-duplicate pair
    "reference list (section 'References')": lambda x: bool(re.search(r"\bReferences\b", x["section"] or "")),
    "homework / questions section": lambda x: bool(re.search(r"\b(Homework|Questions)\b", x["section"] or "")),
    "practice problems (document_type)": lambda x: x["document_type"] == "practice_problems",
    "lecture15 / Semaphore-copy chunk": lambda x: x["document_id"] in NEAR_DUP_DOCS,
}


def check_comparable(a, b):
    ca, cb = a["configuration"], b["configuration"]
    problems = [f"{what} differs" for what, x, y in (
        ("benchmark", ca["benchmark"]["sha256"], cb["benchmark"]["sha256"]),
        ("corpus", ca["corpus"]["chunks_sha256"], cb["corpus"]["chunks_sha256"]),
        ("metric definitions", ca["metric_definitions"], cb["metric_definitions"]),
        ("top_k", ca["retriever"]["top_k"], cb["retriever"]["top_k"]),
        ("query set", [r["query_id"] for r in a["per_query"]], [r["query_id"] for r in b["per_query"]])) if x != y]
    if problems:
        raise ValueError("runs are not comparable: " + ", ".join(problems))


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _grade(x):
    return "—" if x["relevance"] is None else str(x["relevance"])


def _label(cid):
    doc, idx = cid.split("::")
    return f"{doc[:18]}…{doc[-8:]}::{idx}" if len(doc) > 30 else cid  # the hash suffix tells the VIT decks apart


def _first_rank(r, depth=None):
    items = r["retrieved"] + r.get("retrieved_deep", [])
    return next((x["rank"] for x in items[:depth] if x["relevance"]), None)


def condensed(r):
    """Judged-only ("condensed list", Sakai 2007) metrics for one query: unjudged results are removed from the
    retrieved list before scoring with the unchanged metric functions. A supplementary view that does not reward or
    punish a system for results the benchmark never judged; it is not a replacement for the main metrics."""
    ranked = [x["chunk_id"] for x in r["retrieved"] if x["relevance"] is not None]  # top_k only, same for every query
    qrels = {e["chunk_id"]: e["relevance"] for e in r["expected"]}
    return {"precision@5": metrics.precision_at_k(ranked, qrels, 5), "ndcg@10": metrics.ndcg_at_k(ranked, qrels, 10),
            "map@5": metrics.average_precision_at_k(ranked, qrels, 5)}


def build(a, b, name_a, name_b):
    check_comparable(a, b)
    qa, qb = a["per_query"], b["per_query"]
    n = len(qa)
    f = lambda v: f"{v:.3f}"
    d = lambda v: f"{v:+.3f}"
    L = [f"# Retrieval comparison — {name_a} (A) vs {name_b} (B)", "",
         "Same benchmark, corpus, queries, judgments and metric definitions (checked). Differences are B − A. "
         "Measurements only; no winner is declared.", "",
         "## Configuration", ""]
    for nm, run in ((name_a, a), (name_b, b)):
        c = run["configuration"]
        L.append(f"- **{nm}**: {c['retriever']['type']}, top_k={c['retriever']['top_k']}; benchmark "
                 f"v{c['benchmark']['version']} `{c['benchmark']['sha256'][:12]}…`; corpus `{c['corpus']['chunks_sha256'][:12]}…`")
    L += ["", "## Overall (macro-averaged over queries)", "", f"| Metric | {name_a} | {name_b} | Difference |", "| --- | --- | --- | --- |"]
    for m in METRICS:
        va, vb = _mean([r["metrics"][m] for r in qa]), _mean([r["metrics"][m] for r in qb])
        L.append(f"| {m} | {f(va)} | {f(vb)} | {d(vb - va)} |")
    L += ["", f"| Queries with a relevant result in top K (of {n}) | {name_a} | {name_b} | Difference |", "| --- | --- | --- | --- |"]
    for k in HITS:
        ha, hb = sum(r["metrics"][f"hit@{k}"] for r in qa), sum(r["metrics"][f"hit@{k}"] for r in qb)
        L.append(f"| top {k} | {ha:.0f} | {hb:.0f} | {hb - ha:+.0f} |")

    L += ["", "## Judgment coverage", "",
          "Unjudged results count as non-relevant. Benchmark v1.1 was pooled from the dense system's top 20, so "
          "unjudged results fall almost entirely on the other system and its scores are lower bounds.", "",
          f"| Unjudged results | {name_a} | {name_b} |", "| --- | --- | --- |"]
    for k in (5, 10, 20):
        ua, ub = (sum(r[f"unjudged_in_top{k}"] for r in qs) for qs in (qa, qb))
        L.append(f"| top {k} | {ua} of {n * k} ({ua / (n * k):.1%}) | {ub} of {n * k} ({ub / (n * k):.1%}) |")
    unj5 = [r["query_id"] for r in qb if r["unjudged_in_top5"]]
    L.append(f"\nQueries where {name_b} has at least one unjudged result in the top 5: {len(unj5)}.")
    L += ["", "### Judged-only (condensed-list) metrics, supplementary", "",
          "Unjudged results are dropped from each top-20 list before scoring with the same metric functions. This "
          "removes the pooling penalty but also lets a system skip past chunks nobody judged, so it favours the system "
          "with more unjudged results. Read it together with the main table, not instead of it.", "",
          f"| Metric (judged only) | {name_a} | {name_b} | Difference |", "| --- | --- | --- | --- |"]
    for m in ("precision@5", "ndcg@10", "map@5"):
        va, vb = _mean([condensed(r)[m] for r in qa]), _mean([condensed(r)[m] for r in qb])
        L.append(f"| {m} | {f(va)} | {f(vb)} | {d(vb - va)} |")

    for key, title in GROUPS:
        L += ["", f"## By {title.lower()} ({name_a} / {name_b})", "",
              f"| {title} | Queries | " + " | ".join(METRICS) + " |", "| --- | --- | " + " | ".join("---" for _ in METRICS) + " |"]
        for g in sorted({r[key] for r in qa}, key=lambda g: [r[key] for r in qa].index(g)):
            ra, rb = [r for r in qa if r[key] == g], [r for r in qb if r[key] == g]
            cells = [f"{f(_mean([r['metrics'][m] for r in ra]))} / {f(_mean([r['metrics'][m] for r in rb]))}" for m in METRICS]
            L.append(f"| {g} | {len(ra)} | " + " | ".join(cells) + " |")

    fail = lambda qs, k: {r["query_id"] for r in qs if not r["metrics"][f"hit@{k}"]}
    L += ["", "## Failures (no relevant chunk within the cutoff)", "", f"| Cutoff | {name_a} | {name_b} |", "| --- | --- | --- |"]
    for k in (5, 10, 20):
        L.append(f"| top {k} | {', '.join(sorted(fail(qa, k))) or 'none'} | {', '.join(sorted(fail(qb, k))) or 'none'} |")

    top = lambda r, k: {x["chunk_id"] for x in r["retrieved"][:k]}
    rel = lambda r, k: {x["chunk_id"] for x in r["retrieved"][:k] if x["relevance"]}
    L += ["", "## Overlap", "",
          f"- Mean shared chunks per query: top 10 {_mean([len(top(x, 10) & top(y, 10)) for x, y in zip(qa, qb)]):.2f}, "
          f"top 20 {_mean([len(top(x, 20) & top(y, 20)) for x, y in zip(qa, qb)]):.2f}",
          f"- Judged-relevant chunks in the top 20 of only one system: {name_a} only "
          f"{sum(len(rel(x, 20) - rel(y, 20)) for x, y in zip(qa, qb))}, {name_b} only "
          f"{sum(len(rel(y, 20) - rel(x, 20)) for x, y in zip(qa, qb))}, both {sum(len(rel(x, 20) & rel(y, 20)) for x, y in zip(qa, qb))}",
          f"- Queries with a relevant chunk in the top 5 for {name_b} but not {name_a}: "
          f"{', '.join(r['query_id'] for r, s in zip(qb, qa) if r['metrics']['hit@5'] and not s['metrics']['hit@5']) or 'none'}; "
          f"the reverse: {', '.join(r['query_id'] for r, s in zip(qa, qb) if r['metrics']['hit@5'] and not s['metrics']['hit@5']) or 'none'}"]

    L += ["", "## Result categories in the top 5 / top 10", "",
          "Counts of retrieved results over all queries. Top 10 split: relevant (grade ≥ 1) / judged 0 / unjudged.", "",
          f"| Category | {name_a} top 5 | {name_a} top 10 (rel / 0 / unjudged) | {name_b} top 5 | {name_b} top 10 (rel / 0 / unjudged) |",
          "| --- | --- | --- | --- | --- |"]
    for cat, test in CATEGORIES.items():
        row = []
        for qs in (qa, qb):
            t5 = sum(test(x) for r in qs for x in r["retrieved"][:5])
            t10 = [x for r in qs for x in r["retrieved"][:10] if test(x)]
            split = Counter("rel" if x["relevance"] else "unj" if x["relevance"] is None else "zero" for x in t10)
            row += [str(t5), f"{len(t10)} ({split['rel']} / {split['zero']} / {split['unj']})"]
        L.append(f"| {cat} | " + " | ".join(row) + " |")
    both = lambda r: {x["document_id"] for x in r["retrieved"][:10]} >= set(NEAR_DUP_DOCS)
    L.append(f"\nQueries with chunks from both lecture15 and Semaphore-copy in the top 10: {name_a} "
             f"{', '.join(r['query_id'] for r in qa if both(r)) or 'none'}; {name_b} {', '.join(r['query_id'] for r in qb if both(r)) or 'none'}")

    L += ["", "## Deep-pool queries (top 30)", "",
          "Grades: 2 / 1 relevant, 0 judged not relevant, — unjudged.", ""]
    for qid in DEEP:
        ra, rb = next(r for r in qa if r["query_id"] == qid), next(r for r in qb if r["query_id"] == qid)
        items = lambda r: r["retrieved"] + r.get("retrieved_deep", [])
        L += [f"### {qid} ({ra['difficulty']}, {ra['query_type']}): {ra['query']}", ""]
        pos = lambda r, c: next((x["rank"] for x in items(r) if x["chunk_id"] == c), None)
        L += ["| Judged relevant chunk | Grade | Rank " + name_a + " | Rank " + name_b + " |", "| --- | --- | --- | --- |"]
        for e in ra["expected"]:
            L.append(f"| {_label(e['chunk_id'])} | {e['relevance']} | {pos(ra, e['chunk_id']) or '>' + str(len(items(ra)))} | "
                     f"{pos(rb, e['chunk_id']) or '>' + str(len(items(rb)))} |")
        L += ["", f"| Rank | {name_a} chunk | Grade | {name_b} chunk | Grade | {name_b} section |", "| --- | --- | --- | --- | --- | --- |"]
        for x, y in zip(items(ra), items(rb)):
            L.append(f"| {x['rank']} | {_label(x['chunk_id'])} | {_grade(x)} | {_label(y['chunk_id'])} | {_grade(y)} | "
                     f"{str(y['section'])[:60].replace('|', '/')} |")
        L.append("")

    L += ["## Per query", "", f"| Query | Type | Difficulty | First relevant rank {name_a} | First relevant rank {name_b} | "
          f"nDCG@10 {name_a} | nDCG@10 {name_b} | Unjudged@10 {name_b} |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for x, y in zip(qa, qb):
        L.append(f"| {x['query_id']} | {x['query_type']} | {x['difficulty']} | {_first_rank(x, 20) or '>20'} | "
                 f"{_first_rank(y, 20) or '>20'} | {f(x['metrics']['ndcg@10'])} | {f(y['metrics']['ndcg@10'])} | {y['unjudged_in_top10']} |")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compare two evaluator result files on the same benchmark")
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--names", nargs=2, default=("Dense v1.1", "BM25 E1"))
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        a, b = (json.loads(p.read_text(encoding="utf-8")) for p in (args.a, args.b))
        args.output.write_text(build(a, b, *args.names), encoding="utf-8")
    except (ValueError, FileNotFoundError, KeyError) as e:
        sys.exit(f"error: {e}")
    print(f"comparison: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
