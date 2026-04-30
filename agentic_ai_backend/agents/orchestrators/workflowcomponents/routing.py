from models.intentmodel import IntentModel

HIGH_CONFIDENCE_THRESHOLD = 7.0
EXECUTOR_ORDER = ("ConversationAgentA2A", "FormSupportAgentA2A")


def select_subagents(task: IntentModel, agents: list[str]) -> list[str]:
    """Select a single target when confidence is high; otherwise broadcast."""
    print("agents are ", agents)
    if task.confidence >= HIGH_CONFIDENCE_THRESHOLD and task.targetagent in agents:
        return [task.targetagent]

    return list(agents)
