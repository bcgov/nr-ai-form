"""
Convert the human PoC test-result spreadsheet into a step-keyed golden dataset.

Input : AI PoC Testing Result & Feedback(1-35).xlsx  (35 human-labelled cases)
Output:
  - golden.jsonl         one JSON object per case (canonical dataset)
  - golden_tests.yaml    promptfoo `tests:` file generated from the dataset
  - summary.json         distribution stats (per step / severity / issue type)

The spreadsheet's "AI's Response" column is the *historical* PoC answer, not a
gold answer. We keep it as `reference_response` (useful for offline calibration
and as context for LLM-judge rubrics) and treat the human Accuracy/Clarity
scores as the ground-truth labels to calibrate automated evaluators against.

Usage:
  python build_golden.py --xlsx "<path to xlsx>" [--outdir .]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from collections import Counter

import openpyxl

# Column indices in the source spreadsheet (0-based).
COL = {
    "id": 0,
    "email": 3,
    "name": 4,
    "screen": 6,
    "query": 7,
    "ai_response": 8,
    "improvement": 9,
    "accuracy": 10,
    "clarity": 11,
    "issue_type": 12,
    "issue_severity": 13,
    "comments": 14,
}

# Canonical step IDs (match agentic_ai_backend/.../formdefinitions/*.json naming).
STEP_INTRO = "step1-Introduction"
STEP_ELIG = "step2-Eligibility"
STEP_TECH = "step3-Technical-Information"
STEP_LOC = "step4-Location"
STEP_DECL = "step9-Declarations"
STEP_BOT = "step0-Bot"
STEP_ALL = "all-steps"

# step3 sub-type detection (keyword -> subtype label used for filtering/reporting)
STEP3_SUBTYPES = [
    ("purpose", "purpose-of-water-use"),
    ("add purpose", "purpose-of-water-use"),
    ("works", "works"),
    ("diversion", "water-diversion"),
    ("dam", "dam-reservoir"),
    ("reservoir", "dam-reservoir"),
    ("source", "source-of-water"),
    ("joint works", "joint-works"),
    ("fee exemption", "fee-exemption"),
]


def _clean(v) -> str:
    return "" if v is None else str(v).strip()


def normalize_step(raw: str) -> tuple[str, str | None, float]:
    """Map messy free-text screen labels to (canonical_step, subtype, confidence)."""
    t = raw.lower()

    if not t:
        return (STEP_TECH, None, 0.2)  # blanks in this dataset are all step3 follow-ups
    if "all step" in t:
        return (STEP_ALL, None, 1.0)

    # Pre-form / BCeID code entry screen.
    if "bceid" in t or ("code" in t and "step" not in t):
        return (STEP_BOT, None, 0.7)

    if re.search(r"step\s*9|signature|declaration", t):
        return (STEP_DECL, None, 0.9)

    # Location vs Works: a "works" mention routes to the step3 technical works form
    # even when the tester mislabelled it "Step 4 - Works".
    if "works" in t and "location" not in t:
        return (STEP_TECH, "works", 0.7)
    if re.search(r"step\s*4|location|drawing|spatial|map", t):
        return (STEP_LOC, None, 0.9)

    if re.search(r"step\s*3|technical|purpose", t):
        subtype = None
        for kw, label in STEP3_SUBTYPES:
            if kw in t:
                subtype = label
                break
        return (STEP_TECH, subtype, 0.9)

    if re.search(r"step\s*2|eligibil", t):  # tolerates the "Eligibililty" typo
        return (STEP_ELIG, None, 0.95)
    if re.search(r"step\s*1|introduction|landing", t):
        return (STEP_INTRO, None, 0.95)

    # Follow-up narrative rows with no explicit step -> default to step3 (dominant).
    return (STEP_TECH, None, 0.3)


def _score(v) -> int | None:
    s = _clean(v)
    if not s:
        return None
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None


def build(xlsx_path: Path, outdir: Path) -> None:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))[1:]  # skip header

    records = []
    for r in rows:
        raw_screen = _clean(r[COL["screen"]])
        step, subtype, conf = normalize_step(raw_screen)
        query = _clean(r[COL["query"]])
        if not query:
            continue
        rec = {
            "id": f"case-{_clean(r[COL['id']]) or len(records) + 1}",
            "step": step,
            "step_subtype": subtype,
            "step_raw": raw_screen,
            "step_confidence": conf,
            "query": query,
            "reference_response": _clean(r[COL["ai_response"]]),
            "improvement_notes": _clean(r[COL["improvement"]]),
            "human_accuracy": _score(r[COL["accuracy"]]),   # 1-5, None if blank
            "human_clarity": _score(r[COL["clarity"]]),     # 1-5
            "issue_type": _clean(r[COL["issue_type"]]) or "No Issue",
            "issue_severity": _clean(r[COL["issue_severity"]]) or "None",
            "tester": _clean(r[COL["name"]]),
            "comments": _clean(r[COL["comments"]]),
        }
        records.append(rec)

    outdir.mkdir(parents=True, exist_ok=True)

    # 1) golden.jsonl
    jsonl = outdir / "golden.jsonl"
    with jsonl.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 2) promptfoo tests file
    tests = []
    for rec in records:
        rubric = (
            f"You are grading a BC Government water-permit assistant answering a "
            f"'{rec['step']}' question. The response should be factually accurate, "
            f"relevant to the question, and clearly worded for a member of the public. "
        )
        if rec["improvement_notes"]:
            rubric += (
                f"During PoC testing a reviewer noted: '{rec['improvement_notes']}'. "
                f"Penalise responses that repeat this problem. "
            )
        rubric += (
            "Fail if the response invents fees, rates, eligibility rules, or legal "
            "requirements not grounded in BC water-licensing policy."
        )
        tests.append(
            {
                "description": f"{rec['id']} [{rec['step']}]",
                "vars": {
                    "query": rec["query"],
                    "step_number": rec["step"],
                    "reference": rec["reference_response"],
                    "improvement_notes": rec["improvement_notes"],
                },
                "assert": [{"type": "llm-rubric", "value": rubric}],
                "metadata": {
                    "step": rec["step"],
                    "step_subtype": rec["step_subtype"] or "",
                    "human_accuracy": rec["human_accuracy"],
                    "human_clarity": rec["human_clarity"],
                    "issue_type": rec["issue_type"],
                    "issue_severity": rec["issue_severity"],
                },
            }
        )
    _dump_yaml(tests, outdir / "golden_tests.yaml")

    # 3) summary
    summary = {
        "total_cases": len(records),
        "by_step": dict(Counter(r["step"] for r in records)),
        "by_severity": dict(Counter(r["issue_severity"] for r in records)),
        "by_issue_type": dict(Counter(r["issue_type"] for r in records)),
        "avg_human_accuracy": _avg([r["human_accuracy"] for r in records]),
        "avg_human_clarity": _avg([r["human_clarity"] for r in records]),
        "low_step_confidence": [r["id"] for r in records if r["step_confidence"] < 0.5],
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote {len(records)} cases:")
    print(f"  {jsonl}")
    print(f"  {outdir / 'golden_tests.yaml'}")
    print(f"  {outdir / 'summary.json'}")
    print(json.dumps(summary, indent=2))


def _avg(vals):
    nums = [v for v in vals if isinstance(v, int)]
    return round(sum(nums) / len(nums), 2) if nums else None


def _dump_yaml(tests: list, path: Path) -> None:
    """Minimal YAML writer (avoids a PyYAML dependency for a fixed schema)."""

    def esc(s: str) -> str:
        return (
            '"'
            + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()
            + '"'
        )

    lines = [
        "# Auto-generated from the PoC xlsx by build_golden.py - do not edit by hand.",
        "",
    ]
    for t in tests:
        lines.append(f"- description: {esc(t['description'])}")
        lines.append("  vars:")
        for k, v in t["vars"].items():
            lines.append(f"    {k}: {esc(v)}")
        lines.append("  assert:")
        for a in t["assert"]:
            lines.append(f"    - type: {a['type']}")
            lines.append(f"      value: {esc(a['value'])}")
        lines.append("  metadata:")
        for k, v in t["metadata"].items():
            if v is None:
                lines.append(f"    {k}: null")
            elif isinstance(v, int):
                lines.append(f"    {k}: {v}")
            else:
                lines.append(f"    {k}: {esc(v)}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--xlsx",
        default=r"C:\Users\prdevar\Documents\workspace\internal\BCGov\water-permit\AI PoC Testing Result & Feedback(1-35).xlsx",
    )
    ap.add_argument("--outdir", default=str(Path(__file__).parent))
    args = ap.parse_args()
    build(Path(args.xlsx), Path(args.outdir))
