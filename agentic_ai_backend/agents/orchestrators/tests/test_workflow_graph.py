import asyncio
import ast
import unittest
from typing import Any

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler
from agent_framework._workflows._message_utils import normalize_messages_input

from models.intentmodel import IntentListModel, IntentModel
from workflowcomponents.aggregator import Aggregator
from workflowcomponents.conversationagentexecutor import ConversationAgentA2AExecutor
from workflowcomponents.dispatcher import Dispatcher
from workflowcomponents.formsupportagentexecutor import FormSupportAgentA2AExecutor
from workflowcomponents.routing import get_intent_for_agent, select_subagents


class StubDispatcher(Executor):
    def __init__(self, intents: list[IntentModel]):
        super().__init__(id="Dispatcher", name="Dispatcher", instructions="")
        self.intents = intents

    @handler
    async def handle(self, conversation: list[Any], ctx: WorkflowContext[IntentListModel]):
        await ctx.send_message(IntentListModel(intents=self.intents))


class StubWorker(Executor):
    def __init__(self, exec_id: str):
        super().__init__(id=exec_id, name=exec_id, instructions="")

    @handler
    async def handle(
        self,
        task: IntentListModel,
        ctx: WorkflowContext[dict[str, Any]],
    ):
        intent = get_intent_for_agent(task, self.id)
        if intent is None:
            await ctx.send_message(
                {
                    "source": self.id,
                    "skipped": True,
                }
            )
            return

        await ctx.send_message(
            {
                "source": self.id,
                "response": f"{self.id} ok",
                "confidence": intent.confidence,
            }
        )


class WorkflowGraphTests(unittest.TestCase):
    def test_select_subagents_returns_all_intents_above_threshold(self):
        task = IntentListModel(
            intents=[
                IntentModel(
                    confidence=8.5,
                    targetagent="ConversationAgentA2A",
                    query="conversation",
                ),
                IntentModel(
                    confidence=7.0,
                    targetagent="FormSupportAgentA2A",
                    query="excluded",
                ),
                IntentModel(
                    confidence=9.0,
                    targetagent="FormSupportAgentA2A",
                    query="form",
                ),
            ]
        )

        selected = select_subagents(task)

        self.assertEqual(
            [(intent.targetagent, intent.confidence) for intent in selected],
            [
                ("ConversationAgentA2A", 8.5),
                ("FormSupportAgentA2A", 9.0),
            ],
        )

    def test_orchestrator_routes_executor_outputs_to_aggregator_after_fan_out_and_fan_in(self):
        conversation_executor = ConversationAgentA2AExecutor(base_url="http://localhost:8000")
        form_support_executor = FormSupportAgentA2AExecutor(base_url="http://localhost:8001")
        executors = [conversation_executor, form_support_executor]
        dispatcher = Dispatcher(id="Dispatcher", name="Dispatcher", instructions="Dispatch intents.")
        aggregator = Aggregator(id="Aggregator", name="Aggregator", instructions="Aggregate executor results.")

        workflow = (
            WorkflowBuilder(start_executor=dispatcher)
            .add_fan_out_edges(dispatcher, executors)
            .add_fan_in_edges(executors, aggregator)
            .build()
        )

        fan_out_group = next(
            edge_group for edge_group in workflow.edge_groups if type(edge_group).__name__ == "FanOutEdgeGroup"
        )
        fan_in_group = next(
            edge_group for edge_group in workflow.edge_groups if type(edge_group).__name__ == "FanInEdgeGroup"
        )

        self.assertEqual(
            {edge.target_id for edge in fan_out_group.edges},
            {"ConversationAgentA2A", "FormSupportAgentA2A"},
        )
        self.assertEqual(
            {(edge.source_id, edge.target_id) for edge in fan_in_group.edges},
            {
                ("ConversationAgentA2A", "Aggregator"),
                ("FormSupportAgentA2A", "Aggregator"),
            },
        )

    def test_high_confidence_route_completes_with_single_selected_executor(self):
        result = asyncio.run(
            self._run_stub_workflow(
                intents=[
                    IntentModel(
                        confidence=7.5,
                        targetagent="ConversationAgentA2A",
                        query="test",
                    )
                ]
            )
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source"], "ConversationAgentA2A")
        self.assertEqual(result[0]["response"], "ConversationAgentA2A ok")

    def test_dual_high_confidence_route_completes_with_both_selected_executors(self):
        result = asyncio.run(
            self._run_stub_workflow(
                intents=[
                    IntentModel(
                        confidence=8.0,
                        targetagent="ConversationAgentA2A",
                        query="conversation",
                    ),
                    IntentModel(
                        confidence=8.5,
                        targetagent="FormSupportAgentA2A",
                        query="form",
                    ),
                ]
            )
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(
            {item["source"] for item in result},
            {"ConversationAgentA2A", "FormSupportAgentA2A"},
        )

    def test_low_confidence_route_falls_back_to_best_matching_executor(self):
        result = asyncio.run(
            self._run_stub_workflow(
                intents=[
                    IntentModel(
                        confidence=6.5,
                        targetagent="ConversationAgentA2A",
                        query="test",
                    )
                ]
            )
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source"], "ConversationAgentA2A")
        self.assertEqual(result[0]["confidence"], 6.5)

    async def _run_stub_workflow(self, intents: list[IntentModel]) -> list[dict[str, Any]]:
        dispatcher = StubDispatcher(intents=intents)
        conversation_executor = StubWorker("ConversationAgentA2A")
        form_support_executor = StubWorker("FormSupportAgentA2A")
        aggregator = Aggregator(id="Aggregator", name="Aggregator", instructions="")

        workflow = (
            WorkflowBuilder(start_executor=dispatcher)
            .add_fan_out_edges(dispatcher, [conversation_executor, form_support_executor])
            .add_fan_in_edges([conversation_executor, form_support_executor], aggregator)
            .build()
        )

        result = await workflow.as_agent("test").run(normalize_messages_input("hello"))
        return self._parse_workflow_result_text(result.text)

    def _parse_workflow_result_text(self, result_text: str) -> list[dict[str, Any]]:
        try:
            parsed = ast.literal_eval(result_text)
            if isinstance(parsed, list):
                return parsed
            return [parsed]
        except (SyntaxError, ValueError):
            return [
                ast.literal_eval(literal_text)
                for literal_text in self._split_top_level_literals(result_text)
            ]

    def _split_top_level_literals(self, result_text: str) -> list[str]:
        literals: list[str] = []
        start_index: int | None = None
        depth = 0
        in_string = False
        quote_char = ""
        escape_next = False

        for index, char in enumerate(result_text):
            if start_index is None:
                if char.isspace():
                    continue
                start_index = index

            if in_string:
                if escape_next:
                    escape_next = False
                elif char == "\\":
                    escape_next = True
                elif char == quote_char:
                    in_string = False
                continue

            if char in {"'", '"'}:
                in_string = True
                quote_char = char
                continue

            if char in "{[(":
                depth += 1
                continue

            if char in "}])":
                depth -= 1
                if depth == 0 and start_index is not None:
                    literals.append(result_text[start_index : index + 1].strip())
                    start_index = None

        return literals


if __name__ == "__main__":
    unittest.main()
