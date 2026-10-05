"""Pre-test / post-test learning-gain analysis (Review 2 framework; no participant data exists yet).

    python3 -m src.assessment.learning_gain responses.json [--bank data/assessment/question_bank_draft.json]

`responses.json`: {"participants": [{"participant_id": "...", "condition": "tutor" | ..., "pre": {item_id: score},
"post": {item_id: score}}]}. Scores are raw points (0..max_score); an item missing from a response counts as 0.
Pre scores use the bank's `pre` items and post scores its `post` items. All percentages are 0-100.

- Score             = 100 * sum(points) / sum(max_score) over the form's items
- Absolute gain     = post - pre                                       (percentage points)
- Normalized gain g = (post - pre) / (100 - pre)                       (Hake 1998; None when pre = 100)
- Class gain <g>    = (mean post - mean pre) / (100 - mean pre)        (Hake's class-average gain)
- Concept-wise      = the same three numbers per learning objective, from that objective's items only
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

BANK = Path("data/assessment/question_bank_draft.json")


def _pct(scores, items):
    total = sum(i["max_score"] for i in items)
    for item_id, s in scores.items():
        item = next((i for i in items if i["item_id"] == item_id), None)
        if item and not 0 <= s <= item["max_score"]:
            raise ValueError(f"score {s} out of range for {item_id}")
    return 100 * sum(scores.get(i["item_id"], 0) for i in items) / total


def gain(pre, post):
    return {"pre": round(pre, 2), "post": round(post, 2), "absolute_gain": round(post - pre, 2),
            "normalized_gain": None if pre >= 100 else round((post - pre) / (100 - pre), 4)}


def analyze(bank, responses):
    items = bank["items"]
    forms = {f: [i for i in items if i["form"] == f] for f in ("pre", "post")}
    objectives = sorted({i["objective_id"] for i in items})
    participants = []
    for p in responses["participants"]:
        unknown = (set(p["pre"]) - {i["item_id"] for i in forms["pre"]}) | (set(p["post"]) - {i["item_id"] for i in forms["post"]})
        if unknown:
            raise ValueError(f"{p['participant_id']}: unknown item(s) {sorted(unknown)}")
        by_lo = {lo: gain(_pct(p["pre"], [i for i in forms["pre"] if i["objective_id"] == lo]),
                          _pct(p["post"], [i for i in forms["post"] if i["objective_id"] == lo])) for lo in objectives}
        participants.append({"participant_id": p["participant_id"], "condition": p.get("condition"),
                             **gain(_pct(p["pre"], forms["pre"]), _pct(p["post"], forms["post"])), "by_objective": by_lo})

    def cls(rows):
        g = gain(statistics.mean(r["pre"] for r in rows), statistics.mean(r["post"] for r in rows))
        individual = [r["normalized_gain"] for r in rows if r["normalized_gain"] is not None]
        return {"n": len(rows), **g, "mean_individual_normalized_gain": round(statistics.mean(individual), 4) if individual else None}

    conditions = sorted({p["condition"] for p in participants if p["condition"]})
    return {
        "class": cls(participants),
        "by_condition": {c: cls([p for p in participants if p["condition"] == c]) for c in conditions},
        "by_objective": {lo: cls([p["by_objective"][lo] for p in participants]) for lo in objectives},
        "participants": participants,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pre/post learning-gain analysis")
    ap.add_argument("responses", type=Path)
    ap.add_argument("--bank", type=Path, default=BANK)
    args = ap.parse_args(argv)
    bank, responses = (json.loads(p.read_text(encoding="utf-8")) for p in (args.bank, args.responses))
    print(json.dumps(analyze(bank, responses), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
