import asyncio
import ast
import unittest
from typing import Any

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler
from agent_framework._workflows._message_utils import normalize_messages_input

from clientprofiles import ConversationAgentSettings, FormSupportAgentSettings
from models.intentmodel import EdgeCaseCategory, IntentListModel, IntentModel
from orchestratoragent import _select_target_executors
from workflowcomponents.aggregator import Aggregator
from workflowcomponents.conversationagentexecutor import ConversationAgentA2AExecutor
from workflowcomponents.dispatcher import Dispatcher
from workflowcomponents.formsupportagentexecutor import FormSupportAgentA2AExecutor
from workflowcomponents.routing import get_intent_for_agent, select_subagents


class StubDispatcher(Executor):
    def __init__(self, intents: list[IntentModel], category: EdgeCaseCategory | None = None):
        super().__init__(id="Dispatcher", name="Dispatcher", instructions="")
        self.intents = intents
        self.category = category

    @handler
    async def handle(self, conversation: list[Any], ctx: WorkflowContext[IntentListModel]):
        await ctx.send_message(IntentListModel(intents=self.intents, category=self.category))


class StubWorker(Executor):
    def __init__(self, exec_id: str):
        super().__init__(id=exec_id, name=exec_id, instructions="")
        self.invoked = False

    @handler
    async def handle(
        self,
        task: IntentListModel,
        ctx: WorkflowContext[dict[str, Any]],
    ):
        self.invoked = True
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


class _RecordingContext:
    """Minimal stand-in for WorkflowContext - _aggregate only calls yield_output."""

    def __init__(self):
        self.outputs: list[Any] = []

    async def yield_output(self, value):
        self.outputs.append(value)


class FakeThreadManager:
    """In-memory stand-in for redisdbutils's no-answer counter methods."""

    def __init__(self):
        self.counts: dict[str, int] = {}

    async def increment_no_answer_count(self, thread_id: str) -> int:
        self.counts[thread_id] = self.counts.get(thread_id, 0) + 1
        return self.counts[thread_id]

    async def reset_no_answer_count(self, thread_id: str) -> None:
        self.counts[thread_id] = 0


class AggregatorGracefulDeclineTests(unittest.TestCase):
    """Covers the 'Form Assistant - Graceful Response' safety net in Aggregator._aggregate."""

    @staticmethod
    def _make_aggregator(thread_manager=None, session_id="session-1"):
        return Aggregator(
            id="Aggregator",
            name="Aggregator",
            instructions="",
            session_id=session_id,
            thread_manager=thread_manager,
        )

    def test_skip_only_returns_first_attempt_fallback(self):
        aggregator = self._make_aggregator(thread_manager=FakeThreadManager())
        ctx = _RecordingContext()

        asyncio.run(
            aggregator._aggregate(
                [
                    {"source": "ConversationAgentA2A", "skipped": True},
                    {"source": "FormSupportAgentA2A", "skipped": True},
                ],
                ctx,
            )
        )

        self.assertEqual(len(ctx.outputs), 1)
        self.assertEqual(ctx.outputs[0][0]["response"], Aggregator.FIRST_ATTEMPT_FALLBACK)

    def test_repeated_skip_only_escalates_to_second_attempt_fallback(self):
        thread_manager = FakeThreadManager()
        aggregator = self._make_aggregator(thread_manager=thread_manager)
        ctx = _RecordingContext()
        skip_results = [
            {"source": "ConversationAgentA2A", "skipped": True},
            {"source": "FormSupportAgentA2A", "skipped": True},
        ]

        asyncio.run(aggregator._aggregate(skip_results, ctx))
        asyncio.run(aggregator._aggregate(skip_results, ctx))

        self.assertEqual(ctx.outputs[0][0]["response"], Aggregator.FIRST_ATTEMPT_FALLBACK)
        self.assertEqual(ctx.outputs[1][0]["response"], Aggregator.SECOND_ATTEMPT_FALLBACK)

    def test_error_flagged_results_do_not_leak_and_trigger_decline(self):
        aggregator = self._make_aggregator(thread_manager=FakeThreadManager())
        ctx = _RecordingContext()

        asyncio.run(
            aggregator._aggregate(
                [
                    {
                        "source": "ConversationAgentA2A",
                        "response": "Error communicating with Conversation Agent: 500",
                        "error": True,
                    },
                    {
                        "source": "FormSupportAgentA2A",
                        "response": "Error communicating with Form Support Agent (step 2): timeout",
                        "error": True,
                    },
                ],
                ctx,
            )
        )

        response_text = ctx.outputs[0][0]["response"]
        self.assertEqual(response_text, Aggregator.FIRST_ATTEMPT_FALLBACK)
        self.assertNotIn("Error communicating", response_text)

    def test_conversation_only_success_resets_no_answer_count(self):
        thread_manager = FakeThreadManager()
        thread_manager.counts["session-1"] = 1
        aggregator = self._make_aggregator(thread_manager=thread_manager)
        ctx = _RecordingContext()

        asyncio.run(
            aggregator._aggregate(
                [{"source": "ConversationAgentA2A", "response": "Here is your answer."}],
                ctx,
            )
        )

        self.assertEqual(ctx.outputs[0][0]["response"], "Here is your answer.")
        self.assertEqual(thread_manager.counts["session-1"], 0)

    def test_missing_credentials_salvages_valid_content_instead_of_raw_dicts(self):
        # runtime_settings=None forces the "missing credentials" branch
        # regardless of the environment's actual Azure OpenAI env vars.
        aggregator = self._make_aggregator(thread_manager=FakeThreadManager())
        ctx = _RecordingContext()

        asyncio.run(
            aggregator._aggregate(
                [
                    {"source": "ConversationAgentA2A", "response": "Here is your answer."},
                    {
                        "source": "FormSupportAgentA2A",
                        "response": {"suggestedvalue": "yes", "type": "radio"},
                        "step_number": "step2-Eligibility",
                    },
                ],
                ctx,
            )
        )

        output = ctx.outputs[0]
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]["source"], "Aggregator")
        self.assertEqual(output[0]["response"], "Here is your answer.")

    def test_legacy_construction_without_session_still_returns_first_attempt_fallback(self):
        aggregator = Aggregator(id="Aggregator", name="Aggregator", instructions="")
        ctx = _RecordingContext()

        asyncio.run(aggregator._aggregate([], ctx))

        self.assertEqual(ctx.outputs[0][0]["response"], Aggregator.FIRST_ATTEMPT_FALLBACK)


class WorkflowGraphTests(unittest.TestCase):
    def test_select_subagents_returns_all_intents_at_or_above_threshold(self):
        # HIGH_CONFIDENCE_THRESHOLD is 7.0 and routing.select_subagents uses
        # `>=`, so a confidence exactly at the threshold is included, not
        # "excluded" - see routing.py.
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
                    query="at threshold",
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
                ("FormSupportAgentA2A", 7.0),
                ("FormSupportAgentA2A", 9.0),
            ],
        )

    def test_orchestrator_routes_executor_outputs_to_aggregator_after_fan_out_and_fan_in(self):
        conversation_executor = ConversationAgentA2AExecutor(
            base_url="http://localhost:8000", client_settings=ConversationAgentSettings()
        )
        form_support_executor = FormSupportAgentA2AExecutor(
            base_url="http://localhost:8001", client_settings=FormSupportAgentSettings()
        )
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

        # FormSupportAgentA2A is skipped (no matching intent), and the sole
        # usable result is conversation-only, so Aggregator short-circuits
        # (see Aggregator._aggregate) instead of passing the executor's raw
        # dict straight through.
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source"], "Aggregator")
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

        # Both executors ran and returned usable content, but with no Azure
        # OpenAI credentials configured the Aggregator can't call the merge
        # LLM. It must still collapse to a single coherent Aggregator
        # response (salvaging the Conversation Agent's text) rather than
        # leaking both raw executor dicts to the caller.
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source"], "Aggregator")
        self.assertEqual(result[0]["response"], "ConversationAgentA2A ok")

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

        # Same conversation-only short-circuit as the high-confidence case;
        # the routing confidence is still verifiable via original_results.
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source"], "Aggregator")
        self.assertEqual(result[0]["response"], "ConversationAgentA2A ok")
        self.assertEqual(result[0]["original_results"][0]["confidence"], 6.5)

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


class EdgeCaseCategoryTests(unittest.TestCase):
    """Covers Phase 2: fixed-template edge-case categories (see EdgeCaseCategory)."""

    def test_select_target_executors_returns_empty_when_category_set(self):
        intent_list = IntentListModel(
            intents=[
                IntentModel(confidence=9.0, targetagent="ConversationAgentA2A", query="what's the weather"),
            ],
            category=EdgeCaseCategory.UNRELATED_TOPIC,
        )

        selected = _select_target_executors(intent_list, ["ConversationAgentA2A", "FormSupportAgentA2A"])

        self.assertEqual(selected, [])

    def test_select_target_executors_unaffected_when_category_unset(self):
        intent_list = IntentListModel(
            intents=[IntentModel(confidence=9.0, targetagent="ConversationAgentA2A", query="test")],
        )

        selected = _select_target_executors(intent_list, ["ConversationAgentA2A", "FormSupportAgentA2A"])

        self.assertEqual(selected, ["ConversationAgentA2A"])

    def test_handle_intent_yields_generic_fallback_for_each_category_without_tenant_templates(self):
        """No tenant content lives in code - without an edge_case_templates
        override, every category falls back to the plain first-attempt copy,
        never a per-category message."""
        for category in EdgeCaseCategory:
            with self.subTest(category=category):
                aggregator = Aggregator(id="Aggregator", name="Aggregator", instructions="")
                ctx = _RecordingContext()
                task = IntentListModel(
                    intents=[IntentModel(confidence=1.0, targetagent="ConversationAgentA2A", query="test")],
                    category=category,
                )

                asyncio.run(aggregator.handle_intent(task, ctx))

                self.assertEqual(len(ctx.outputs), 1)
                output = ctx.outputs[0][0]
                self.assertEqual(output["source"], "Aggregator")
                self.assertEqual(output["response"], Aggregator.FIRST_ATTEMPT_FALLBACK)
                self.assertEqual(output["category"], category.value)

    def test_full_workflow_skips_both_executors_for_edge_case_category(self):
        dispatcher = StubDispatcher(
            intents=[IntentModel(confidence=1.0, targetagent="ConversationAgentA2A", query="what's the weather")],
            category=EdgeCaseCategory.UNRELATED_TOPIC,
        )
        conversation_executor = StubWorker("ConversationAgentA2A")
        form_support_executor = StubWorker("FormSupportAgentA2A")
        aggregator = Aggregator(id="Aggregator", name="Aggregator", instructions="")

        workflow = (
            WorkflowBuilder(start_executor=dispatcher)
            .add_edge(dispatcher, aggregator)
            .add_multi_selection_edge_group(
                dispatcher, [conversation_executor, form_support_executor], _select_target_executors
            )
            .build()
        )

        result = asyncio.run(workflow.as_agent("test").run(normalize_messages_input("hello")))
        parsed = ast.literal_eval(result.text)
        # A single-item yield_output serializes as a bare dict rather than a
        # one-element list - mirrors the normalization in
        # orchestratoragent._parse_workflow_result_text.
        if isinstance(parsed, dict):
            parsed = [parsed]

        self.assertFalse(conversation_executor.invoked)
        self.assertFalse(form_support_executor.invoked)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["response"], Aggregator.FIRST_ATTEMPT_FALLBACK)


if __name__ == "__main__":
    unittest.main()
