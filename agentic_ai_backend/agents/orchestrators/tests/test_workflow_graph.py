import asyncio
import ast
import unittest
from typing import Any

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler
from agent_framework._workflows._message_utils import normalize_messages_input

from models.intentmodel import IntentModel
from workflowcomponents.aggregator import Aggregator
from workflowcomponents.conversationagentexecutor import ConversationAgentA2AExecutor
from workflowcomponents.dispatcher import Dispatcher
from workflowcomponents.formsupportagentexecutor import FormSupportAgentA2AExecutor
from workflowcomponents.routing import select_subagents


class StubDispatcher(Executor):
    def __init__(self, confidence: float, targetagent: str):
        super().__init__(id="Dispatcher", name="Dispatcher", instructions="")
        self.confidence = confidence
        self.targetagent = targetagent

    @handler
    async def handle(self, conversation: list[Any], ctx: WorkflowContext[IntentModel]):
        await ctx.send_message(
            IntentModel(
                confidence=self.confidence,
                targetagent=self.targetagent,
                query="test",
            )
        )


class StubWorker(Executor):
    def __init__(self, exec_id: str):
        super().__init__(id=exec_id, name=exec_id, instructions="")

    @handler
    async def handle(self, intent: IntentModel, ctx: WorkflowContext[dict[str, Any]]):
        await ctx.send_message(
            {
                "source": self.id,
                "response": f"{self.id} ok",
                "confidence": intent.confidence,
            }
        )


class WorkflowGraphTests(unittest.TestCase):
    def test_select_subagents_targets_one_executor_when_confidence_is_high(self):
        intent = IntentModel(
            confidence=7.5,
            targetagent="ConversationAgentA2A",
            query="test",
        )

        selected = select_subagents(intent, ["ConversationAgentA2A", "FormSupportAgentA2A"])

        self.assertEqual(selected, ["ConversationAgentA2A"])

    def test_select_subagents_broadcasts_when_confidence_is_low(self):
        intent = IntentModel(
            confidence=6.5,
            targetagent="ConversationAgentA2A",
            query="test",
        )

        selected = select_subagents(intent, ["ConversationAgentA2A", "FormSupportAgentA2A"])

        self.assertEqual(selected, ["ConversationAgentA2A", "FormSupportAgentA2A"])

    def test_orchestrator_routes_executor_outputs_to_aggregator_after_conditional_fan_out(self):
        conversation_executor = ConversationAgentA2AExecutor(base_url="http://localhost:8000")
        form_support_executor = FormSupportAgentA2AExecutor(base_url="http://localhost:8001")
        executors = [conversation_executor, form_support_executor]
        dispatcher = Dispatcher(id="Dispatcher", name="Dispatcher", instructions="Dispatch intents.")
        aggregator = Aggregator(id="Aggregator", name="Aggregator", instructions="Aggregate executor results.")

        workflow = (
            WorkflowBuilder(start_executor=dispatcher)
            .add_multi_selection_edge_group(dispatcher, executors, selection_func=select_subagents)
            .add_edge(conversation_executor, aggregator)
            .add_edge(form_support_executor, aggregator)
            .build()
        )

        fan_out_group = next(
            edge_group for edge_group in workflow.edge_groups if type(edge_group).__name__ == "FanOutEdgeGroup"
        )
        aggregator_edges = [
            edge_group
            for edge_group in workflow.edge_groups
            if type(edge_group).__name__ == "SingleEdgeGroup"
        ]

        self.assertEqual(
            {edge.target_id for edge in fan_out_group.edges},
            {"ConversationAgentA2A", "FormSupportAgentA2A"},
        )
        self.assertEqual(
            {
                (edge_group.edges[0].source_id, edge_group.edges[0].target_id)
                for edge_group in aggregator_edges
            },
            {
                ("ConversationAgentA2A", "Aggregator"),
                ("FormSupportAgentA2A", "Aggregator"),
            },
        )

    def test_high_confidence_route_completes_with_single_selected_executor(self):
        result = asyncio.run(self._run_stub_workflow(confidence=7.5))

        self.assertEqual(result["source"], "ConversationAgentA2A")
        self.assertEqual(result["response"], "ConversationAgentA2A ok")

    def test_low_confidence_route_completes_after_broadcast_path(self):
        result = asyncio.run(self._run_stub_workflow(confidence=6.5))

        self.assertEqual(len(result), 2)
        self.assertEqual(
            {item["source"] for item in result},
            {"ConversationAgentA2A", "FormSupportAgentA2A"},
        )
        self.assertTrue(all("skipped" not in item for item in result))

    async def _run_stub_workflow(self, confidence: float) -> dict[str, Any] | list[dict[str, Any]]:
        dispatcher = StubDispatcher(confidence=confidence, targetagent="ConversationAgentA2A")
        conversation_executor = StubWorker("ConversationAgentA2A")
        form_support_executor = StubWorker("FormSupportAgentA2A")
        aggregator = Aggregator(id="Aggregator", name="Aggregator", instructions="")

        workflow = (
            WorkflowBuilder(start_executor=dispatcher)
            .add_multi_selection_edge_group(
                dispatcher,
                [conversation_executor, form_support_executor],
                selection_func=select_subagents,
            )
            .add_edge(conversation_executor, aggregator)
            .add_edge(form_support_executor, aggregator)
            .build()
        )

        result = await workflow.as_agent("test").run(normalize_messages_input("hello"))
        return ast.literal_eval(result.text)


if __name__ == "__main__":
    unittest.main()
