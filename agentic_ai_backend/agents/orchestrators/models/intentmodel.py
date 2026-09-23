from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class EdgeCaseCategory(str, Enum):
    """Fixed out-of-scope/edge-case buckets the Dispatcher can flag instead of routing.

    When set on `IntentListModel`, the Aggregator returns a fixed template for
    this category directly - no sub-agent is invoked and `intents` is ignored.
    """

    PREDICTING_OUTCOME = "predicting_outcome"
    LEGAL_ADVICE = "legal_advice"
    EXTERNAL_LOOKUP = "external_lookup"
    INTERNAL_POLICY = "internal_policy"
    OUT_OF_SCOPE_SUBJECT = "out_of_scope_subject"
    UNRELATED_TOPIC = "unrelated_topic"


class IntentModel(BaseModel):
    confidence: float = Field(
        ge=0,
        le=10,
        description="Routing confidence from 0 (lowest) to 10 (highest).",
    )
    targetagent: Literal["ConversationAgentA2A", "FormSupportAgentA2A"] = Field(
        description="The executor ID selected by the dispatcher.",
    )
    query: str = Field(
        min_length=1,
        description="The normalized user query without any step prefix.",
    )


class IntentListModel(BaseModel):
    intents: list[IntentModel] = Field(
        min_length=1,
        description="One or more routing decisions returned by the intent classifier.",
    )
    category: EdgeCaseCategory | None = Field(
        default=None,
        description=(
            "Set only when the query falls into a fixed out-of-scope/edge-case bucket "
            "(predicting an outcome, legal advice, external record lookup, internal "
            "policy, an out-of-scope subject, or an unrelated topic). When set, "
            "`intents` is ignored and no sub-agent is invoked."
        ),
    )
