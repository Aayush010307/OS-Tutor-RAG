"""Evaluate a retriever against the gold benchmark (Phase 3A baseline: the frozen Phase 2 dense retriever).

    python3 -m src.evaluation.retrieval_evaluator            # writes data/evaluation/baseline_dense_{results.json,report.md}
    python3 -m src.evaluation.retrieval_evaluator --retriever bm25 --top-k 20 --deep-k 30 \
        --benchmark data/evaluation/retrieval_queries_v1.1.json --output-dir data/evaluation/e1_bm25 --name bm25_v1.1

The evaluator only calls `search(query, top_k)` on the dense `Retriever`, the E1 `BM25Retriever` or the E2
`HybridRRFRetriever` (`--retriever hybrid`); it adds no retrieval logic. Rankings and metrics are
deterministic for a fixed index, benchmark and runtime; only `run.generated_at` changes between runs.
Error categories are automatic heuristics meant for inspection, not ground truth.
"""
import argparse
import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.retrieval.bm25 import BM25Retriever
from src.retrieval.hybrid import HybridRRFRetriever
from src.retrieval.indexer import CHUNKS, DOCUMENTS, MANIFEST, sha256_file
from src.retrieval.retriever import Retriever

from . import metrics

BENCHMARK = Path("data/evaluation/retrieval_queries.json")
OUTPUT_DIR = Path("data/evaluation")
TOP_K = 10  # results retrieved per query; the largest K any metric uses
DIFFICULTIES, TOPICS, QUERY_TYPES = ("easy", "medium", "hard"), ("Threads", "Synchronisation"), \
    ("conceptual", "mechanism", "algorithm", "classical", "code", "scenario", "comparative")
HEADLINE = ("recall@1", "recall@3", "recall@5", "recall@10", "precision@5", "mrr@5", "ndcg@5", "ndcg@10", "map@5")
IDENTIFIER = re.compile(r"\b[a-z]+_[a-z_]+\b|\b\w+\(\)|\b[A-Z]{2,}\b")  # pthread_join, park(), CAS


def validate_benchmark(bench, chunk_ids):
    """Return a list of problems (empty when the benchmark is well formed)."""
    problems = []
    for key in ("version", "corpus", "queries"):
        if key not in bench:
            problems.append(f"missing top-level field {key!r}")
    seen = set()
    for q in bench.get("queries", []):
        qid = q.get("query_id")
        if qid in seen:
            problems.append(f"duplicate query_id {qid}")
        seen.add(qid)
        for f in ("query_id", "query", "topic", "subtopic", "difficulty", "query_type", "relevant_chunks"):
            if f not in q:
                problems.append(f"{qid}: missing {f}")
        if q.get("topic") not in TOPICS or q.get("difficulty") not in DIFFICULTIES or q.get("query_type") not in QUERY_TYPES:
            problems.append(f"{qid}: invalid topic/difficulty/query_type")
        if not isinstance(q.get("query"), str) or not q.get("query", "").strip():
            problems.append(f"{qid}: empty query")
        rel = q.get("relevant_chunks", [])
        if not rel:
            problems.append(f"{qid}: no relevant chunks")
        ids = [r.get("chunk_id") for r in rel]
        if len(ids) != len(set(ids)):
            problems.append(f"{qid}: duplicate chunk in judgments")
        for r in rel:
            if r.get("chunk_id") not in chunk_ids:
                problems.append(f"{qid}: unknown chunk {r.get('chunk_id')}")
            if r.get("relevance") not in (1, 2):
                problems.append(f"{qid}: relevance must be 1 or 2, got {r.get('relevance')!r}")
        # v1.1+: pooled candidates read and judged not relevant (grade 0)
        non = [r.get("chunk_id") for r in q.get("nonrelevant_chunks", [])]
        if len(non) != len(set(non)) or set(non) & set(ids):
            problems.append(f"{qid}: duplicate chunk in judgments")
        for r in q.get("nonrelevant_chunks", []):
            if r.get("chunk_id") not in chunk_ids:
                problems.append(f"{qid}: unknown chunk {r.get('chunk_id')}")
            if r.get("relevance") != 0:
                problems.append(f"{qid}: nonrelevant relevance must be 0, got {r.get('relevance')!r}")
    return problems


def _mean(values):
    return round(statistics.mean(values), 4) if values else None


def _aggregate(records, keys=None):
    keys = keys or records[0]["metrics"].keys()
    return {k: _mean([r["metrics"][k] for r in records]) for k in keys} | {"queries": len(records)}


def _duplicate_pairs(results):
    """Pairs of results in one list that carry the same content: exact duplicate chunks, or chunks from
    documents flagged as near-duplicates of each other."""
    pairs = []
    for i, a in enumerate(results):
        for b in results[i + 1:]:
            ma, mb = a["metadata"], b["metadata"]
            if ma["duplicate_of"] == b["chunk_id"] or mb["duplicate_of"] == a["chunk_id"] or \
                    (ma["duplicate_of"] and ma["duplicate_of"] == mb["duplicate_of"]):
                pairs.append((a["chunk_id"], b["chunk_id"], "exact_duplicate_chunk"))
            elif b["document_id"] in (ma["near_duplicate_documents"] or []):
                pairs.append((a["chunk_id"], b["chunk_id"], "near_duplicate_document"))
    return pairs


def _tags_for_nonrelevant(r, qrels, rel_meta, query_subtopics, image_only, dup_ids):
    """Heuristic tags for a retrieved chunk that is not judged relevant."""
    m, tags = r["metadata"], []
    section = r["section"] or ""
    if re.search(r"\bReferences\b", section):
        tags.append("reference_list")
    if re.search(r"\b(Homework|Questions)\b", section):
        tags.append("exercise_section")
    if r["chunk_id"] in dup_ids:
        tags.append("duplicate_result")
    if any(rm["document_id"] == m["document_id"] and abs(rm["chunk_index"] - m["chunk_index"]) == 1 for rm in rel_meta):
        tags.append("neighboring_chunk")
    if set(m["subtopics"]) & set(query_subtopics):
        tags.append("topically_related_unjudged")
    if (m["page_start"] or m["slide_start"]) in image_only.get(m["document_id"], ()):
        tags.append("image_only_unit")
    return tags


def evaluate(retriever, bench, chunks, documents, top_k=TOP_K, deep_k=None):
    """Run every benchmark query and return (per_query_records, aggregates). With `deep_k`, the benchmark's
    deep-pool queries (v1.1 `pooling.deep_pool`) are retrieved to that depth for inspection only: the extra
    results go to `retrieved_deep` and never enter metrics or counts."""
    chunk_meta = {c["chunk_id"]: c for c in chunks}
    image_only = {d["document_id"]: set(d.get("image_only_units") or []) for d in documents}
    deep = set(bench.get("pooling", {}).get("deep_pool", {}).get("queries", [])) if deep_k else set()
    records = []
    for q in bench["queries"]:
        qrels = {r["chunk_id"]: r["relevance"] for r in q["relevant_chunks"]}
        judged0 = {r["chunk_id"] for r in q.get("nonrelevant_chunks", [])}
        all_results = retriever.search(q["query"], top_k=max(top_k, deep_k) if q["query_id"] in deep else top_k)
        results = all_results[:top_k]
        ranked = [r["chunk_id"] for r in results]
        pairs5, pairs10 = _duplicate_pairs(results[:5]), _duplicate_pairs(results[:10])
        dup_ids5 = {c for p in pairs5 for c in p[:2]}
        rel_meta = [chunk_meta[c] for c in qrels]

        def entry(r):
            label = qrels.get(r["chunk_id"], 0 if r["chunk_id"] in judged0 else None)  # None = unjudged
            m = r["metadata"]
            return {
                "rank": r["rank"], "chunk_id": r["chunk_id"], "score": r["score"], "relevance": label,
                "document_id": r["document_id"], "filename": r["filename"], "source": m["source"],
                "document_type": m["document_type"], "page_start": r["page_start"], "page_end": r["page_end"],
                "slide_start": r["slide_start"], "slide_end": r["slide_end"], "section": r["section"],
                "duplicate_of": m["duplicate_of"],
                **({"component_ranks": r["component_ranks"]} if "component_ranks" in r else {}),  # E2 only
                "error_tags": [] if label or r["rank"] > 5 else
                _tags_for_nonrelevant(r, qrels, rel_meta, q["subtopic"], image_only, dup_ids5),
            }
        retrieved = [entry(r) for r in results]
        met = {k: round(v, 6) for k, v in metrics.all_metrics(ranked, qrels, top_k).items()}
        failure = []
        if not met["hit@5"]:
            failure.append("no_relevant_in_top5")
            idents = set(IDENTIFIER.findall(q["query"])) - {"CPU", "OS", "N", "M"}
            if idents and not any(i.lower() in chunk_meta[c]["text"].lower() for c in ranked[:5] for i in idents):
                failure.append("exact_terminology_miss")
            if any((chunk_meta[c]["page_start"] or chunk_meta[c]["slide_start"]) in image_only.get(chunk_meta[c]["document_id"], ())
                   for c in qrels):
                failure.append("relevant_near_image_only_unit")
            if len(failure) == 1:
                failure.append("semantic_mismatch")
        if not met["hit@10"]:
            failure.append("no_relevant_in_top10")
        record = {
            "query_id": q["query_id"], "query": q["query"], "topic": q["topic"], "subtopic": q["subtopic"],
            "difficulty": q["difficulty"], "query_type": q["query_type"],
            "expected": q["relevant_chunks"], "retrieved": retrieved, "metrics": met,
            "unjudged_in_top5": sum(r["relevance"] is None for r in retrieved[:5]),
            "unjudged_in_top10": sum(r["relevance"] is None for r in retrieved[:10]),
            "duplicate_pairs_top5": [list(p) for p in pairs5], "duplicate_pairs_top10": [list(p) for p in pairs10],
            "failure_categories": failure,
        }
        if top_k >= 20:
            record["unjudged_in_top20"] = sum(r["relevance"] is None for r in retrieved[:20])
        if len(all_results) > top_k:
            record["retrieved_deep"] = [entry(r) for r in all_results[top_k:]]
        records.append(record)
    return records, summarize(records)


def summarize(records):
    by = lambda field, values: {v: _aggregate([r for r in records if r[field] == v], HEADLINE)
                                for v in values if any(r[field] == v for r in records)}
    tags = Counter(t for r in records for x in r["retrieved"] for t in x["error_tags"])
    nonrel5 = sum(not x["relevance"] for r in records for x in r["retrieved"][:5])
    return {
        "overall": _aggregate(records),
        "by_topic": by("topic", TOPICS), "by_difficulty": by("difficulty", DIFFICULTIES),
        "by_query_type": by("query_type", QUERY_TYPES),
        "failures": {
            "no_relevant_in_top5": [r["query_id"] for r in records if "no_relevant_in_top5" in r["failure_categories"]],
            "no_relevant_in_top10": [r["query_id"] for r in records if "no_relevant_in_top10" in r["failure_categories"]],
            "categories": dict(Counter(c for r in records for c in r["failure_categories"]
                                       if c not in ("no_relevant_in_top5", "no_relevant_in_top10"))),
        },
        "nonrelevant_top5_tags": {"nonrelevant_results_in_top5": nonrel5, "tag_counts": dict(sorted(tags.items()))},
        "judgment_coverage": {
            "mean_unjudged_in_top5": _mean([r["unjudged_in_top5"] for r in records]),
            "mean_unjudged_in_top10": _mean([r["unjudged_in_top10"] for r in records]),
            "share_of_top10_unjudged": round(sum(r["unjudged_in_top10"] for r in records) /
                                             max(1, sum(len(r["retrieved"][:10]) for r in records)), 4),
        } | ({
            "mean_unjudged_in_top20": _mean([r["unjudged_in_top20"] for r in records]),
            "share_of_top20_unjudged": round(sum(r["unjudged_in_top20"] for r in records) /
                                             max(1, sum(len(r["retrieved"][:20]) for r in records)), 4),
        } if all("unjudged_in_top20" in r for r in records) else {}),
        "duplicates": {
            "queries_with_duplicate_content_in_top5": sum(bool(r["duplicate_pairs_top5"]) for r in records),
            "queries_with_duplicate_content_in_top10": sum(bool(r["duplicate_pairs_top10"]) for r in records),
            "duplicate_pairs_in_top10": dict(Counter(p[2] for r in records for p in r["duplicate_pairs_top10"])),
        },
    }


def run(benchmark_path=BENCHMARK, output_dir=OUTPUT_DIR, name="baseline_dense", store_dir=None, manifest_path=MANIFEST,
        chunks_path=CHUNKS, documents_path=DOCUMENTS, top_k=TOP_K, retriever="dense", deep_k=None):
    bench = json.loads(Path(benchmark_path).read_text(encoding="utf-8"))
    chunks = [json.loads(l) for l in Path(chunks_path).read_text(encoding="utf-8").splitlines()]
    problems = validate_benchmark(bench, {c["chunk_id"] for c in chunks})
    if problems:
        raise ValueError("invalid benchmark:\n  " + "\n  ".join(problems))
    corpus_sha = sha256_file(chunks_path)
    if bench["corpus"]["chunks_sha256"] != corpus_sha:
        raise RuntimeError("benchmark was written for a different chunks.jsonl (corpus hash mismatch)")
    documents = json.loads(Path(documents_path).read_text(encoding="utf-8"))
    if retriever == "bm25":
        opened = BM25Retriever.open(chunks_path, documents_path)
        retriever_config = opened.config()
    elif retriever in ("dense", "hybrid"):
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        kwargs = {"manifest_path": manifest_path, "chunks_path": chunks_path} | ({"store_dir": store_dir} if store_dir else {})
        opened = Retriever.open(**kwargs)
        retriever_config = {"type": "dense (Phase 2 baseline, unchanged)", "embedding_model": manifest["embedding"]["model"],
                            "model_revision": manifest["embedding"]["revision"], "collection": manifest["vector_store"]["collection"],
                            "distance": manifest["vector_store"]["distance"], "vectors_sha256": manifest["digests"]["vectors_sha256"]}
        if retriever == "hybrid":
            opened = HybridRRFRetriever(opened, BM25Retriever.open(chunks_path, documents_path))
            retriever_config = opened.config() | {"dense": retriever_config}
    else:
        raise ValueError(f"unknown retriever {retriever!r}")
    retriever_config |= {"filters": None, "top_k": top_k} | ({"deep_k": deep_k} if deep_k else {})
    with opened:
        records, summary = evaluate(opened, bench, chunks, documents, top_k, deep_k)
    out = {
        "run": {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "name": name},
        "configuration": {
            "benchmark": {"path": str(benchmark_path), "version": bench["version"], "sha256": sha256_file(benchmark_path),
                          "queries": len(bench["queries"])},
            "corpus": {"chunks_sha256": corpus_sha, "chunks": len(chunks)},
            "retriever": retriever_config,
            "relevance": "chunk relevant when judged grade >= 1; nDCG uses grades (2, 1) as linear gains; unjudged = 0"
                         + ("; retrieved relevance 0 = judged not relevant, null = unjudged"
                            if any(q.get("nonrelevant_chunks") for q in bench["queries"]) else ""),
            "metric_definitions": metrics.__doc__.strip(),
        },
        "summary": summary,
        "per_query": records,
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{name}_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / f"{name}_report.md").write_text(build_report(out, bench), encoding="utf-8")
    return out


def _fmt(v):
    return "-" if v is None else f"{v:.3f}"


def _table(rows, cols):
    lines = ["| Group | Queries | " + " | ".join(cols) + " |", "| --- | --- | " + " | ".join("---" for _ in cols) + " |"]
    lines += [f"| {g} | {m['queries']} | " + " | ".join(_fmt(m[c]) for c in cols) + " |" for g, m in rows.items()]
    return lines


def _loc(x):
    if x["page_start"] is not None:
        return f"p.{x['page_start']}" + (f"-{x['page_end']}" if x["page_end"] != x["page_start"] else "")
    return f"s.{x['slide_start']}" + (f"-{x['slide_end']}" if x["slide_end"] != x["slide_start"] else "")


def build_report(out, bench):
    c, s, recs = out["configuration"], out["summary"], out["per_query"]
    qs = bench["queries"]
    grade = Counter(r["relevance"] for q in qs for r in q["relevant_chunks"])
    r_cfg = c["retriever"]
    if r_cfg["type"].startswith("hybrid"):
        d, b = r_cfg["dense"], r_cfg["bm25"]
        title = "# Hybrid Dense + BM25 (RRF) Retrieval — Evaluation Report"
        retriever_line = (f"- Retriever: {r_cfg['type']}; rrf_k={r_cfg['rrf_k']}, {r_cfg['candidate_k_per_system']} candidates "
                          f"per system, equal weights; dense `{d['embedding_model']}` @ `{d['model_revision'][:12]}`; "
                          f"BM25 k1={b['k1']}, b={b['b']}; top_k={r_cfg['top_k']}, no filters")
    elif r_cfg["type"].startswith("bm25"):
        title = "# BM25 Lexical Retrieval — Evaluation Report"
        retriever_line = (f"- Retriever: {r_cfg['type']}; k1={r_cfg['k1']}, b={r_cfg['b']}, idf {r_cfg['idf']}; tokenizer: "
                          f"{r_cfg['tokenizer']}; {r_cfg['documents']} chunks, vocabulary {r_cfg['vocabulary']}, "
                          f"avgdl {r_cfg['avgdl']}; top_k={r_cfg['top_k']}, no filters")
    else:
        title = "# Baseline Dense Retrieval — Evaluation Report"
        retriever_line = (f"- Retriever: {r_cfg['type']}; `{r_cfg['embedding_model']}` @ `{r_cfg['model_revision'][:12]}`, "
                          f"collection `{r_cfg['collection']}` ({r_cfg['distance']}), vectors SHA-256 `{r_cfg['vectors_sha256'][:16]}…`, "
                          f"top_k={r_cfg['top_k']}, no filters")
    if r_cfg.get("deep_k"):
        retriever_line += f"; deep-pool queries retrieved to {r_cfg['deep_k']} for inspection (not in metrics)"
    L = [title, "",
         f"Run `{out['run']['name']}` at {out['run']['generated_at']}. Measurements only; no thresholds or quality claims.", "",
         "## Configuration", "",
         f"- Corpus: `chunks.jsonl` SHA-256 `{c['corpus']['chunks_sha256']}` ({c['corpus']['chunks']} chunks)",
         f"- Benchmark: `{c['benchmark']['path']}` version {c['benchmark']['version']}, SHA-256 `{c['benchmark']['sha256']}`",
         retriever_line,
         f"- Relevance: {c['relevance']}", "",
         "## Benchmark", "",
         f"- Queries: {len(qs)}; judgments: {sum(grade.values())} (grade 2: {grade[2]}, grade 1: {grade[1]})"
         + (f"; judged not relevant (grade 0): {n0}" if (n0 := sum(len(q.get('nonrelevant_chunks', [])) for q in qs)) else ""),
         f"- Topic: {dict(Counter(q['topic'] for q in qs))}",
         f"- Difficulty: {dict(Counter(q['difficulty'] for q in qs))}",
         f"- Query type: {dict(Counter(q['query_type'] for q in qs))}", "",
         "## Overall metrics (macro-averaged over queries)", "",
         "| Metric | Value |", "| --- | --- |"]
    L += [f"| {k} | {_fmt(v)} |" for k, v in s["overall"].items() if k != "queries"]
    L += ["", "Recall@K is the fraction of the judged relevant set found in the top K; queries with many background "
          "(grade 1) chunks have a low ceiling for small K (Recall@1 is at most 1/|relevant|). Hit@K is reported "
          "separately as the share of queries with at least one relevant chunk in the top K.", ""]
    for title, key in (("By topic", "by_topic"), ("By difficulty", "by_difficulty"), ("By query type", "by_query_type")):
        L += [f"## {title}", ""] + _table(s[key], HEADLINE) + [""]
    f = s["failures"]
    L += ["## Retrieval failures", "",
          f"- Queries with no relevant chunk in the top 5: {len(f['no_relevant_in_top5'])} ({', '.join(f['no_relevant_in_top5']) or 'none'})",
          f"- Queries with no relevant chunk in the top 10: {len(f['no_relevant_in_top10'])} ({', '.join(f['no_relevant_in_top10']) or 'none'})",
          f"- Heuristic failure categories (top-5 failures): {f['categories'] or 'none'}", "",
          "## Non-relevant results in the top 5 (heuristic tags)", "",
          f"- Non-relevant (unjudged or grade 0) results in the top 5 across all queries: {s['nonrelevant_top5_tags']['nonrelevant_results_in_top5']}",
          "- Tag counts (a result can carry several tags): " + (", ".join(f"{k} {v}" for k, v in s['nonrelevant_top5_tags']['tag_counts'].items()) or "none"),
          "- `topically_related_unjudged` means the chunk shares a subtopic label with the query; such chunks may be "
          "relevant material that the incomplete judgments do not list.", "",
          "## Judgment coverage", "",
          f"- Mean unjudged results per query: top 5 {s['judgment_coverage']['mean_unjudged_in_top5']}, top 10 "
          f"{s['judgment_coverage']['mean_unjudged_in_top10']} (share of all top-10 results unjudged: "
          f"{s['judgment_coverage']['share_of_top10_unjudged']})"
          + (f"; top 20 {s['judgment_coverage']['mean_unjudged_in_top20']} (share "
             f"{s['judgment_coverage']['share_of_top20_unjudged']})" if "mean_unjudged_in_top20" in s["judgment_coverage"] else ""),
          "- Unjudged results count as non-relevant, so metrics are a lower bound with respect to judgment completeness.", "",
          "## Duplicates", "",
          f"- Queries with duplicate content in the top 5: {s['duplicates']['queries_with_duplicate_content_in_top5']}; "
          f"in the top 10: {s['duplicates']['queries_with_duplicate_content_in_top10']}",
          f"- Duplicate pairs in top-10 lists by kind: {s['duplicates']['duplicate_pairs_in_top10'] or 'none'}", "",
          "## Notable error cases", "",
          "Queries where no relevant chunk was retrieved in the top 5 (expected = grade-2 judgments; retrieved = top 3):", ""]
    chunk_label = lambda cid: cid.split("::")[0][:32] + "::" + cid.split("::")[1]
    for r in recs:
        if "no_relevant_in_top5" not in r["failure_categories"]:
            continue
        exp = [chunk_label(e["chunk_id"]) for e in r["expected"] if e["relevance"] == 2][:4]
        L.append(f"- **{r['query_id']}** ({r['difficulty']}, {r['query_type']}) {r['query']}")
        L.append(f"  - categories: {', '.join(c for c in r['failure_categories'] if not c.startswith('no_relevant'))}; "
                 f"first relevant rank within top 10: {next((x['rank'] for x in r['retrieved'] if x['relevance']), 'none')}")
        L.append(f"  - expected: {', '.join(exp)}")
        for x in r["retrieved"][:3]:
            L.append(f"  - #{x['rank']} {x['score']:.3f} {chunk_label(x['chunk_id'])} ({_loc(x)}) {str(x['section'])[:70]}"
                     + (f" [{', '.join(x['error_tags'])}]" if x["error_tags"] else ""))
    L += ["", "## Per-query results", "", "| Query | Topic | Difficulty | Type | R@5 | R@10 | P@5 | MRR@5 | nDCG@10 | Unjudged@5 |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in recs:
        m = r["metrics"]
        L.append(f"| {r['query_id']} | {r['topic']} | {r['difficulty']} | {r['query_type']} | {_fmt(m['recall@5'])} | "
                 f"{_fmt(m['recall@10'])} | {_fmt(m['precision@5'])} | {_fmt(m['mrr@5'])} | {_fmt(m['ndcg@10'])} | {r['unjudged_in_top5']} |")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Evaluate a retriever (dense, BM25 or hybrid RRF) against the gold retrieval benchmark")
    ap.add_argument("--benchmark", default=BENCHMARK, type=Path)
    ap.add_argument("--output-dir", default=OUTPUT_DIR, type=Path)
    ap.add_argument("--name", default="baseline_dense")
    ap.add_argument("--retriever", default="dense", choices=("dense", "bm25", "hybrid"))
    ap.add_argument("--top-k", default=TOP_K, type=int, help="results scored per query (metrics use cutoffs up to 20)")
    ap.add_argument("--deep-k", type=int, help="also retrieve the benchmark's deep-pool queries to this depth (inspection only)")
    args = ap.parse_args(argv)
    try:
        out = run(args.benchmark, args.output_dir, args.name, top_k=args.top_k, retriever=args.retriever, deep_k=args.deep_k)
    except (ValueError, RuntimeError, FileNotFoundError) as e:
        sys.exit(f"error: {e}")
    o = out["summary"]["overall"]
    print(" ".join(f"{k}={o[k]:.3f}" for k in HEADLINE))
    print(f"results: {args.output_dir / (args.name + '_results.json')}\nreport:  {args.output_dir / (args.name + '_report.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
