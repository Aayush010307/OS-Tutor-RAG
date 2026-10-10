"""Tutor quality evaluation (Phase 4): run the scripted student dialogues through the real tutor and score them.

    /usr/local/bin/python3 -m src.evaluation.tutor_eval run --model qwen3:8b       # writes <out>/<model>_transcripts.json
    /usr/local/bin/python3 -m src.evaluation.tutor_eval report qwen3:8b            # one model -> <out>/report_qwen3_8b.md
    /usr/local/bin/python3 -m src.evaluation.tutor_eval report qwen3:8b llama3.1:8b
                                                         # comparison -> <out>/report_qwen3_8b_vs_llama3.1_8b.md

Only the models named on the command line are evaluated; nothing else is read or run. Each model set gets its own
report file, so a routine single-model report never overwrites a comparison. (`report.md` in tutor_eval/ and
tutor_eval_v2/ was written by the earlier naming scheme and is never rewritten.)

`run` plays every scenario of data/evaluation/tutor_scenarios_v1.json (8 questions x 3 student profiles) through
TutorController with the E2 hybrid retriever and a local Ollama model, recording every model call and its latency.
`report` computes the automatic checks below for each model, plus the manual rubric grades in
<out>/manual_grades_<model>.json when that file exists.

Automatic checks (per tutor turn unless stated):
- analysis agreement: the analysed level vs the scripted label (exact where the script fixes a level; solid / not
  solid for every reply) and valid JSON from the analysis call
- flow: the stage sequence equals the profile's expected path
- format: DIAGNOSE and CHECK ask exactly one question; EXPLAIN ends with a question; WRAP_UP asks none; at most 120 words
- citations: EXPLAIN, WRAP_UP and ANSWER cite at least one source; every [Sn] cited exists
- leak: the text mentions "the context", "instructions" or "the conversation"
- retrieval: a grade-2 benchmark chunk is among the 5 chunks the tutor was given
- latency: seconds per model call
Manual rubric (0/1/2 each, one annotator): correct (OS facts right), grounded (supported by the given sources),
pedagogy (DIAGNOSE probes without giving the answer; EXPLAIN targets the student's gap with an example; CHECK tests the
idea; WRAP_UP / ANSWER confirm or answer clearly).
"""
import argparse
import json
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from src.retrieval.indexer import sha256_file
from src.tutor.controller import LEVELS, TutorController
from src.tutor.llm import DEFAULT_MODEL, OllamaLLM

SCENARIOS = Path("data/evaluation/tutor_scenarios_v1.json")
BENCHMARK = Path("data/evaluation/retrieval_queries_v1.1.json")
OUT = Path("data/evaluation/tutor_eval")
EVAL_TIMEOUT = 600  # seconds per model call; the slowest measured call was 88 s (llama3.1:8b, Phase 4.1)
EXPECTED = {  # per profile: (label of each scripted reply, stage after each reply); None = any level except solid
    "solid": (["solid", "solid"], ["CHECK", "DONE"]),
    "misconception": (["misconception", "solid"], ["EXPLAIN", "DONE"]),
    "unsure": (["unclear", None, "unclear"], ["EXPLAIN", "EXPLAIN", "DONE"]),
}
CITE = re.compile(r"\[S(\d+)\]")
LEAK = re.compile(r"\b(the (course )?context|instructions|the conversation)\b", re.I)


class Recording:
    """Wraps the LLM and keeps every call: kind (analysis / tutor), output, seconds."""
    def __init__(self, llm):
        self.llm, self.calls = llm, []

    def __call__(self, prompt, json_mode=False, on_token=None):
        t0 = time.perf_counter()
        out = self.llm(prompt, json_mode=json_mode)
        self.calls.append({"kind": "analysis" if json_mode else "tutor", "output": out,
                           "seconds": round(time.perf_counter() - t0, 2), "prompt_chars": len(prompt)})
        return out


def run(model, scenarios_path=SCENARIOS, out_dir=OUT, retriever=None):
    from src.retrieval.hybrid import HybridRRFRetriever
    spec = json.loads(Path(scenarios_path).read_text(encoding="utf-8"))
    own = retriever is None
    retriever = retriever or HybridRRFRetriever.open()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{model.replace(':', '_')}_transcripts.json"
    write = lambda ds: path.write_text(json.dumps(header(model, scenarios_path) | {"dialogues": ds},
                                                  ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dialogues = []
    try:
        for sc in spec["scenarios"]:
            for profile, replies in sc["replies"].items():
                # evaluation keeps the generous Phase 4 reply timeout; the app's 120 s default is for students waiting
                rec = Recording(OllamaLLM(model, timeout=EVAL_TIMEOUT))
                tutor = TutorController(retriever, rec)
                session, turn = tutor.start(sc["question"])
                turns = [{"stage": turn.stage, "message": turn.message, "student": None, "analysis": None}]
                for reply in replies:
                    if session.stage == "DONE":
                        break
                    turn = tutor.respond(session, reply)
                    turns.append({"stage": turn.stage, "message": turn.message, "student": reply, "analysis": turn.analysis})
                dialogues.append({"id": f"{sc['query_id']}-{profile}", "objective": sc["objective"], "query_id": sc["query_id"],
                                  "profile": profile, "question": sc["question"],
                                  "context": [r["chunk_id"] for r in session.context], "turns": turns,
                                  "analysis_raw": [c["output"] for c in rec.calls if c["kind"] == "analysis"],
                                  "calls": [{k: c[k] for k in ("kind", "seconds", "prompt_chars")} for c in rec.calls]})
                print(f"{dialogues[-1]['id']}: {' -> '.join(t['stage'] for t in turns)}", flush=True)
                write(dialogues)  # partial results survive an Ollama failure mid-run
    finally:
        if own:
            retriever.close()
    write(dialogues)
    return path


def header(model, scenarios_path):
    return {"run": {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": model,
                    "llm_options": OllamaLLM(model).options, "scenarios": str(scenarios_path),
                    "scenarios_sha256": sha256_file(scenarios_path), "retriever": "hybrid RRF (E2), top 5"}}


def _valid_json(raw):
    try:
        return json.loads(raw).get("level") in LEVELS
    except (json.JSONDecodeError, AttributeError):
        return False


def turn_checks(turn, n_sources):
    text, stage = turn["message"], turn["stage"]
    cites = [int(n) for n in CITE.findall(text)]
    last = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s][-1:] or [""]
    kind = turn.get("kind", stage)
    c = {"words": len(text.split()), "within_120_words": len(text.split()) <= 120, "leak": bool(LEAK.search(text)),
         "citations_valid": all(1 <= n <= n_sources for n in cites)}
    if kind in ("DIAGNOSE", "CHECK"):
        c["one_question"] = text.count("?") == 1
    if kind == "EXPLAIN":
        c["ends_with_question"] = "?" in last[0]
    if kind == "WRAP_UP":
        c["no_question"] = "?" not in text
    if kind in ("EXPLAIN", "WRAP_UP", "ANSWER"):
        c["cites_source"] = bool(cites)
    return c


def turn_kind(dialogue, i):
    """The prompt that produced turn i: DONE turns are WRAP_UP (after a solid check) or ANSWER (after the last round)."""
    t = dialogue["turns"][i]
    if t["stage"] != "DONE":
        return t["stage"]
    return "WRAP_UP" if t["analysis"] and t["analysis"]["level"] == "solid" else "ANSWER"


def score(transcripts, grade2):
    d_rows, t_rows = [], []
    for d in transcripts["dialogues"]:
        labels, path = EXPECTED[d["profile"]]
        got = [t["analysis"]["level"] for t in d["turns"][1:]]
        stages = [t["stage"] for t in d["turns"][1:]]
        exact = [g == e for g, e in zip(got, labels) if e is not None]
        binary = [(g == "solid") == (e == "solid") for g, e in zip(got, labels)]
        d_rows.append({"id": d["id"], "profile": d["profile"], "flow_ok": stages == path, "exact": exact, "binary": binary,
                       "json_ok": [_valid_json(r) for r in d["analysis_raw"]],
                       "grade2_in_context": bool(set(d["context"]) & grade2[d["query_id"]])})
        for i, t in enumerate(d["turns"]):
            kind = turn_kind(d, i)
            t_rows.append({"id": d["id"], "turn": i, "kind": kind,
                           **turn_checks(t | {"kind": kind}, len(d["context"]))})
    lat = {k: [c["seconds"] for d in transcripts["dialogues"] for c in d["calls"] if c["kind"] == k] for k in ("tutor", "analysis")}
    return d_rows, t_rows, lat


def _share(xs):
    xs = list(xs)
    return (sum(xs), len(xs))


def _fmt(pair):
    k, n = pair
    return f"{k}/{n} ({k / n:.0%})" if n else "-"


def _slug(model):
    return model.replace(":", "_")


def canonical(models):
    """One order per model set, whatever order they were typed in: the primary model first, the rest alphabetical."""
    return sorted(dict.fromkeys(models), key=lambda m: (m != DEFAULT_MODEL, m))


def report_path(models, out_dir=OUT):
    """One file per model set: report_qwen3_8b.md, report_qwen3_8b_vs_llama3.1_8b.md (for either typing order)."""
    return Path(out_dir) / f"report_{'_vs_'.join(_slug(m) for m in canonical(models))}.md"


def report(models, out_dir=OUT, benchmark=BENCHMARK):
    """Score exactly the given models from their transcripts in out_dir; no other model is read."""
    models = canonical(models)  # same model set -> same file and same column order
    if not models:
        raise ValueError("name at least one model")
    out_dir = Path(out_dir)
    missing = [m for m in models if not (out_dir / f"{_slug(m)}_transcripts.json").exists()]
    if missing:
        raise FileNotFoundError("no transcripts for " + ", ".join(missing) + f" in {out_dir}; run "
                                + "; ".join(f"`tutor_eval run --model {m} --output-dir {out_dir}`" for m in missing))
    bench = json.loads(Path(benchmark).read_text(encoding="utf-8"))
    grade2 = {q["query_id"]: {r["chunk_id"] for r in q["relevant_chunks"] if r["relevance"] == 2} for q in bench["queries"]}
    names = ", ".join(f"`{m}`" for m in models)
    L = [f"# Tutor Quality Evaluation — {' vs '.join(models)}", "",
         (f"Model evaluated: {names} (single-model report; no other model was run or scored)." if len(models) == 1 else
          f"Models evaluated (comparison requested explicitly): {names}."), "",
         "Scripted student dialogues (data/evaluation/tutor_scenarios_v1.json: 8 questions x 3 profiles) run through the "
         "tutor with the E2 hybrid retriever and a local Ollama model. Measurements only.", ""]
    summary, options = {}, {}
    for model in models:
        tr = json.loads((out_dir / f"{_slug(model)}_transcripts.json").read_text(encoding="utf-8"))
        d_rows, t_rows, lat = score(tr, grade2)
        kinds = lambda k: [t for t in t_rows if t["kind"] == k]
        s = {
            "Dialogues following the expected path": _share(r["flow_ok"] for r in d_rows),
            "Analysis: exact level agreement": _share(x for r in d_rows for x in r["exact"]),
            "Analysis: solid / not-solid agreement": _share(x for r in d_rows for x in r["binary"]),
            "Analysis: valid JSON": _share(x for r in d_rows for x in r["json_ok"]),
            "DIAGNOSE asks exactly one question": _share(t["one_question"] for t in kinds("DIAGNOSE")),
            "CHECK asks exactly one question": _share(t["one_question"] for t in kinds("CHECK")),
            "EXPLAIN ends with a check question": _share(t["ends_with_question"] for t in kinds("EXPLAIN")),
            "WRAP_UP asks no question": _share(t["no_question"] for t in kinds("WRAP_UP")),
            "EXPLAIN / WRAP_UP / ANSWER cite a source": _share(t["cites_source"] for t in t_rows if "cites_source" in t),
            "All citations point to a given source": _share(t["citations_valid"] for t in t_rows),
            "Turns within 120 words": _share(t["within_120_words"] for t in t_rows),
            "Turns mentioning context / instructions": _share(t["leak"] for t in t_rows),
            "Grade-2 chunk among the 5 retrieved (per dialogue)": _share(r["grade2_in_context"] for r in d_rows),
        }
        by_profile = {p: _share(r["flow_ok"] for r in d_rows if r["profile"] == p) for p in EXPECTED}
        manual = out_dir / f"manual_grades_{model.replace(':', '_')}.json"
        grades = json.loads(manual.read_text(encoding="utf-8"))["grades"] if manual.exists() else None
        summary[model] = (s, by_profile, lat, len(t_rows), grades, t_rows)
        options[model] = tr["run"].get("llm_options")
    L += ["Generation settings: " + "; ".join(f"{m} {o}" for m, o in options.items()), ""]
    L += ["## Automatic checks", "", "| Check | " + " | ".join(models) + " |", "| --- | " + " | ".join("---" for _ in models) + " |"]
    for key in next(iter(summary.values()))[0]:
        L.append(f"| {key} | " + " | ".join(_fmt(summary[m][0][key]) for m in models) + " |")
    L += ["", "| Expected path followed, by student profile | " + " | ".join(models) + " |", "| --- | " + " | ".join("---" for _ in models) + " |"]
    for p in EXPECTED:
        L.append(f"| {p} | " + " | ".join(_fmt(summary[m][1][p]) for m in models) + " |")
    L += ["", "| Latency per model call (s) | " + " | ".join(models) + " |", "| --- | " + " | ".join("---" for _ in models) + " |"]
    for k in ("tutor", "analysis"):
        L.append(f"| {k}: median / max | " + " | ".join(
            f"{statistics.median(summary[m][2][k]):.1f} / {max(summary[m][2][k]):.1f}" for m in models) + " |")
    L += ["", "Tutor turns scored: " + ", ".join(f"{m} {summary[m][3]}" for m in models) + ".", ""]
    if any(summary[m][4] for m in models):
        L += ["## Manual rubric (0-2 per turn, single annotator)", "",
              "| Criterion | " + " | ".join(models) + " |", "| --- | " + " | ".join("---" for _ in models) + " |"]
        for crit in ("correct", "grounded", "pedagogy"):
            cells = []
            for m in models:
                g = summary[m][4]
                if not g:
                    cells.append("-")
                    continue
                vals = [x[crit] for x in g]
                cells.append(f"mean {statistics.mean(vals):.2f}; 2: {vals.count(2)}, 1: {vals.count(1)}, 0: {vals.count(0)}")
            L.append(f"| {crit} | " + " | ".join(cells) + " |")
        L += ["", "| Mean pedagogy by turn type | " + " | ".join(models) + " |", "| --- | " + " | ".join("---" for _ in models) + " |"]
        for kind in ("DIAGNOSE", "EXPLAIN", "CHECK", "WRAP_UP", "ANSWER"):
            cells = []
            for m in models:
                g = summary[m][4] or []
                vals = [x["pedagogy"] for x in g if x["kind"] == kind]
                cells.append(f"{statistics.mean(vals):.2f} (n={len(vals)})" if vals else "-")
            L.append(f"| {kind} | " + " | ".join(cells) + " |")
        L.append("")
    path = report_path(models, out_dir)
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Tutor quality evaluation")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--model", required=True)
    r.add_argument("--scenarios", default=SCENARIOS, type=Path)
    r.add_argument("--output-dir", default=OUT, type=Path)
    p = sub.add_parser("report", help="score only the models named here (one model, or several for a comparison)")
    p.add_argument("models", nargs="+", metavar="MODEL")
    p.add_argument("--output-dir", default=OUT, type=Path)
    args = ap.parse_args(argv)
    try:
        path = run(args.model, args.scenarios, args.output_dir) if args.cmd == "run" else report(args.models, args.output_dir)
    except FileNotFoundError as e:
        sys.exit(f"error: {e}")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
