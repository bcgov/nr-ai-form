"""
Task-completion / correctness metrics per form step.

Mirrors the human PoC labels (Accuracy, Clarity) with two GEval metrics judged
by GPT-4.1. This is the primary per-step quality gate: run the whole golden set,
or scope to a step with EVAL_STEPS.

    # offline calibration against historical PoC answers
    pytest evaluation/deepeval/test_task_completion.py

    # live, only step 3
    EVAL_LIVE=1 EVAL_STEPS=step3-Technical-Information \
        pytest evaluation/deepeval/test_task_completion.py
"""

from __future__ import annotations

import pytest
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from dataset_loader import load_records, actual_output

RECORDS = load_records()


def _ids(recs):
    return [f"{r['id']}-{r['step']}" for r in recs]


@pytest.mark.parametrize("rec", RECORDS, ids=_ids(RECORDS))
def test_accuracy(rec, judge):
    correctness = GEval(
        name="WaterPermitAccuracy",
        model=judge,
        threshold=0.6,  # ~ human avg accuracy 3.46/5
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        evaluation_steps=[
            "Check whether the response correctly and completely answers the applicant's water-permit question.",
            "Heavily penalise fabricated fees, water rates, eligibility rules, or legal requirements.",
            "Penalise incomplete answers that omit information the applicant needs to proceed on this step.",
            "Reward answers that correctly defer to authoritative BC sources when uncertain.",
        ],
    )
    tc = LLMTestCase(input=rec["query"], actual_output=actual_output(rec))
    assert_test(tc, [correctness])


@pytest.mark.parametrize("rec", RECORDS, ids=_ids(RECORDS))
def test_clarity(rec, judge):
    clarity = GEval(
        name="Clarity",
        model=judge,
        threshold=0.6,  # ~ human avg clarity 3.57/5
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        evaluation_steps=[
            "Judge whether a member of the public with no water-licensing expertise could act on the response.",
            "Penalise jargon left unexplained, disorganised structure, or ambiguous next steps.",
            "Reward concise, well-structured, plain-language guidance.",
        ],
    )
    tc = LLMTestCase(input=rec["query"], actual_output=actual_output(rec))
    assert_test(tc, [clarity])
