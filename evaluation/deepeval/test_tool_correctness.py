"""
Tool / calculation correctness for the FormSupportAgent's livestock-watering
MCP calculator (agents/formsupportagent/local_mcp/livestock).

The PoC data shows the assistant's biggest recurring failure is water-quantity
guidance — recommending the wrong calculator (provincial vs BC Ag Calculator)
or producing unjustified numbers. This module targets exactly those cases.

Two layers:
  1. GEval "CalculationGuidance" (works now, offline or live): grades whether
     water-quantity answers use the correct BC methodology and don't emit
     numbers without a stated, sound basis.
  2. ToolCorrectnessMetric (activates in live mode once /invoke returns tool
     traces): compares the tools actually called against expected tools.

Populate real `tools_called` by having the orchestrator echo tool invocations
in the /invoke response, then set EVAL_TOOL_TRACES=1.
"""

from __future__ import annotations

import os

import pytest
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams, ToolCall

from dataset_loader import load_records, actual_output, is_calculation_case

RECORDS = [r for r in load_records() if is_calculation_case(r)]
TOOL_TRACES = os.getenv("EVAL_TOOL_TRACES", "0") == "1"


def _ids(recs):
    return [f"{r['id']}-{r['step']}" for r in recs]


@pytest.mark.skipif(not RECORDS, reason="no calculation cases in current selection")
@pytest.mark.parametrize("rec", RECORDS, ids=_ids(RECORDS))
def test_calculation_guidance(rec, judge):
    calc = GEval(
        name="CalculationGuidance",
        model=judge,
        threshold=0.6,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        evaluation_steps=[
            "Determine whether the question involves estimating a water quantity, rate, or volume.",
            "For agricultural/irrigation demand, the correct tool is the BC Agriculture Water Calculator; "
            "penalise recommending the generic provincial calculator, which ignores climate and crop type.",
            "Fail if the response states a specific numeric quantity/rate without a stated, sound basis "
            "(input assumptions, units, or the calculator used).",
            "Reward responses that guide the user to the correct calculator and show unit-consistent reasoning.",
        ],
    )
    tc = LLMTestCase(input=rec["query"], actual_output=actual_output(rec))
    assert_test(tc, [calc])


@pytest.mark.skipif(
    not (RECORDS and TOOL_TRACES),
    reason="tool traces unavailable — set EVAL_TOOL_TRACES=1 once /invoke returns tool calls",
)
@pytest.mark.parametrize("rec", RECORDS, ids=_ids(RECORDS))
def test_tool_correctness(rec):
    from deepeval.metrics import ToolCorrectnessMetric

    # TODO: parse real tools from the /invoke response once the backend emits them.
    tools_called: list[ToolCall] = []
    expected_tools = [ToolCall(name="livestock_water_calculator")]

    tc = LLMTestCase(
        input=rec["query"],
        actual_output=actual_output(rec),
        tools_called=tools_called,
        expected_tools=expected_tools,
    )
    assert_test(tc, [ToolCorrectnessMetric(threshold=1.0)])
