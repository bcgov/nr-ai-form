"""
Load the golden dataset (built from the PoC xlsx) for DeepEval.

Two evaluation modes, selected by the EVAL_LIVE env var:

  EVAL_LIVE unset / "0"  -> OFFLINE CALIBRATION
        actual_output = the historical PoC response stored in the xlsx.
        Lets you grade automated metrics against the human Accuracy/Clarity
        labels with no running backend — useful to validate the judge itself.

  EVAL_LIVE = "1"        -> LIVE
        actual_output = a fresh call to the orchestrator /invoke for the case's
        step. Requires the backend + Azure creds.

Filter by step with EVAL_STEPS (comma-separated canonical step ids), e.g.
    EVAL_STEPS=step3-Technical-Information,step2-Eligibility
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # evaluation/

from shared.backend_client import invoke_text  # noqa: E402

GOLDEN = Path(__file__).resolve().parents[1] / "datasets" / "golden.jsonl"


def is_live() -> bool:
    return os.getenv("EVAL_LIVE", "0") == "1"


def _step_filter() -> set[str] | None:
    raw = os.getenv("EVAL_STEPS", "").strip()
    return {s.strip() for s in raw.split(",") if s.strip()} or None


def load_records(steps: Iterable[str] | None = None) -> list[dict[str, Any]]:
    if not GOLDEN.exists():
        raise FileNotFoundError(
            f"{GOLDEN} not found — run: python evaluation/datasets/build_golden.py"
        )
    wanted = set(steps) if steps else _step_filter()
    out: list[dict[str, Any]] = []
    with GOLDEN.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if wanted and rec["step"] not in wanted:
                continue
            out.append(rec)
    return out


def actual_output(rec: dict[str, Any]) -> str:
    """Return the response text to grade, per the active mode."""
    if is_live():
        return invoke_text(query=rec["query"], step_number=rec["step"])
    return rec.get("reference_response", "")


# --- lightweight helpers for selecting case subsets ------------------------

CALC_KEYWORDS = ("calculat", "litre", "l/s", "quantity", "m3", "m³", "acre", "irrigat", "flow rate")
RAG_KEYWORDS = ("fee", "cost", "eligib", "bceid", "definition", "licen", "exempt")


def is_calculation_case(rec: dict[str, Any]) -> bool:
    blob = (rec["query"] + " " + rec.get("reference_response", "")).lower()
    return any(k in blob for k in CALC_KEYWORDS)


def is_rag_case(rec: dict[str, Any]) -> bool:
    blob = rec["query"].lower()
    return any(k in blob for k in RAG_KEYWORDS)
