from typing import Literal

from pydantic import BaseModel, Field


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
