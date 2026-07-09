"""
A2A Executors for Orchestrator Agent
These executors communicate with agents via A2A protocol instead of direct imports.
"""
import logging
from typing import Any

from agent_framework import Executor, WorkflowContext, handler

from a2aclients.conversationagentclient import ConversationAgentA2AClient
from clientprofiles import ConversationAgentSettings
from models.intentmodel import IntentListModel, IntentModel
from workflowcomponents.routing import get_intent_for_agent, get_primary_intent

logger = logging.getLogger(__name__)



class ConversationAgentA2AExecutor(Executor):
    """
    Executor that communicates with Conversation Agent via A2A protocol.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        id: str = "ConversationAgentA2A",
        name: str = "Conversation Agent (A2A)",
        instructions: str = "Handles conversation queries using A2A protocol",
        session_id: str = None,
        *,
        client_settings: ConversationAgentSettings,
        # Timeout in seconds for the HTTP A2A call to the Conversation Agent.
        timeout: int = 30
    ):
        super().__init__(id=id, name=name, instructions=instructions)
        self.client = ConversationAgentA2AClient(base_url=base_url, timeout=timeout)
        self.session_id = session_id
        # A2A requests are JSON payloads, so convert the typed settings at the boundary.
        self.client_settings = client_settings.model_dump(exclude_none=True)

    @handler
    async def handle(
        self,
        task: IntentListModel | IntentModel,
        ctx: WorkflowContext[dict[str, Any]],
    ):
        """
        Handle incoming query by forwarding to Conversation Agent via A2A.

        Args:
            task: Dispatcher output
            ctx: Workflow context for sending messages
        """
        intent = get_intent_for_agent(task, self.id)
        if intent is None:
            primary_intent = get_primary_intent(task)
            await ctx.send_message(
                {
                    "source": self.id,
                    "skipped": True,
                    "targetagent": primary_intent.targetagent,
                    "confidence": primary_intent.confidence,
                }
            )
            return

        try:
            # Invoke the remote agent via A2A, passing session_id for conversation history
            response = await self.client.invoke(
                intent.query,
                session_id=self.session_id,
                client_settings=self.client_settings,
            )
            # Send the response with source information
            # Wrap it in a dict so we can track the source
            response_with_source = {
                "source": self.id,
                "response": response,
                "confidence": intent.confidence,
            }
            await ctx.send_message(response_with_source)

        except Exception as e:
            error_msg = f"Error communicating with Conversation Agent: {str(e)}"
            print(error_msg)
            logger.exception('Conversation Agent A2A call failed')
            error_with_source = {
                "source": self.id,
                "response": error_msg,
                "confidence": intent.confidence,
            }
            await ctx.send_message(error_with_source)
