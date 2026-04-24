"""
A2A Executors for Orchestrator Agent
These executors communicate with agents via A2A protocol instead of direct imports.
"""
from typing import Any

from agent_framework import Executor, WorkflowContext, handler

from a2aclients.conversationagentclient import ConversationAgentA2AClient
from models.intentmodel import IntentModel



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
        session_id: str = None
    ):
        super().__init__(id=id, name=name, instructions=instructions)
        self.client = ConversationAgentA2AClient(base_url=base_url)
        self.session_id = session_id
        
    @handler
    async def handle(self, intent: IntentModel, ctx: WorkflowContext[dict[str, Any]]):
        """
        Handle incoming query by forwarding to Conversation Agent via A2A.
        
        Args:
            intent: Dispatcher output
            ctx: Workflow context for sending messages
        """
        if intent.targetagent != self.id:
            await ctx.send_message(
                {
                    "source": self.id,
                    "skipped": True,
                    "targetagent": intent.targetagent,
                    "confidence": intent.confidence,
                }
            )
            return

        try:
            # Invoke the remote agent via A2A, passing session_id for conversation history
            response = await self.client.invoke(intent.query, session_id=self.session_id)
            
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
            error_with_source = {
                "source": self.id,
                "response": error_msg,
                "confidence": intent.confidence,
            }
            await ctx.send_message(error_with_source)

