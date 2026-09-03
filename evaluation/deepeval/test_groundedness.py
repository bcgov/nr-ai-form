"""
Groundedness / hallucination metrics for the RAG (ConversationAgent) cases —
fee, cost, eligibility, BCeID and definition questions answered from the
searchcontent/ PDF corpus.

- AnswerRelevancyMetric: response actually addresses the question.
- GEval "NoHallucination": no invented fees/rates/legal facts.

We deliberately avoid FaithfulnessMetric here because /invoke does not currently
return the retrieved chunks; wire `retrieval_context` in once the backend
surfaces citations, then add FaithfulnessMetric to this module.
"""

from __future__ import annotations

import pytest
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric, GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from dataset_loader import load_records, actual_output, is_rag_case

RECORDS = [r for r in load_records() if is_rag_case(r)]


def _ids(recs):
    return [f"{r['id']}-{r['step']}" for r in recs]


@pytest.mark.skipif(not RECORDS, reason="no RAG-style cases in current selection")
@pytest.mark.parametrize("rec", RECORDS, ids=_ids(RECORDS))
def test_no_hallucination(rec, judge):
    groundedness = GEval(
        name="NoHallucination",
        model=judge,
        threshold=0.7,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        evaluation_steps=[
            "Identify every factual claim about fees, water rates, eligibility, exemptions, or legal process.",
            "Fail if any such claim is fabricated or contradicts BC water-licensing policy "
            "(e.g. inventing a specific dollar amount or rate not established by policy).",
            "A response that correctly points to an authoritative BC source instead of guessing should score high.",
        ],
    )
    tc = LLMTestCase(input=rec["query"], actual_output=actual_output(rec))
    assert_test(tc, [groundedness])


@pytest.mark.skipif(not RECORDS, reason="no RAG-style cases in current selection")
@pytest.mark.parametrize("rec", RECORDS, ids=_ids(RECORDS))
def test_answer_relevancy(rec, judge):
    relevancy = AnswerRelevancyMetric(threshold=0.6, model=judge)
    tc = LLMTestCase(input=rec["query"], actual_output=actual_output(rec))
    assert_test(tc, [relevancy])
