from models.intentmodel import IntentListModel, IntentModel

HIGH_CONFIDENCE_THRESHOLD = 7.0
EXECUTOR_ORDER = ("ConversationAgentA2A", "FormSupportAgentA2A")


def _coerce_intents(task: IntentListModel | IntentModel) -> list[IntentModel]:
    if isinstance(task, IntentListModel):
        return task.intents
    return [task]


def select_subagents(task: IntentListModel | IntentModel) -> list[IntentModel]:
    """Return every intent whose confidence is greater than 7."""
    return [
        intent
        for intent in _coerce_intents(task)
        if intent.confidence >= HIGH_CONFIDENCE_THRESHOLD
    ]


def get_intent_for_agent(task: IntentListModel | IntentModel, agent_id: str) -> IntentModel | None:
    """Pick the best matching intent for a given executor."""
    candidate_intents = select_subagents(task) or _coerce_intents(task)
    matching_intents = [
        intent
        for intent in candidate_intents
        if intent.targetagent == agent_id
    ]
    if not matching_intents:
        return None

    return max(matching_intents, key=lambda intent: intent.confidence)


def get_primary_intent(task: IntentListModel | IntentModel) -> IntentModel:
    """Return the highest-confidence intent from the task payload."""
    return max(_coerce_intents(task), key=lambda intent: intent.confidence)
