"""
A2A Executors for Orchestrator Agent
These executors communicate with agents via A2A protocol instead of direct imports.
"""
from agent_framework import Executor, WorkflowContext, handler
from typing import Any
from a2aclients.conversationagentclient import ConversationAgentA2AClient



class ConversationAgentA2AExecutor(Executor):
    """
    Executor that communicates with Conversation Agent via A2A protocol.
    """
    
    def __init__(
        self, 
        base_url: str = "http://localhost:8000",
        id: str = "ConversationAgentA2A",
        name: str = "Conversation Agent (A2A)",
        instructions: str = "Handles conversation queries using A2A protocol"
    ):
        super().__init__(id=id, name=name, instructions=instructions)
        self.client = ConversationAgentA2AClient(base_url=base_url)
        
    @handler
    async def handle(self, query: str, ctx: WorkflowContext[str]):
        """
        Handle incoming query by forwarding to Conversation Agent via A2A.
        
        Args:
            query: User query string
            ctx: Workflow context for sending messages
        """
        try:
            # Invoke the remote agent via A2A
            response = await self.client.invoke(query)
            
            # Send the response with source information
            # Wrap it in a dict so we can track the source
            response_with_source = {
                "source": self.id,
                "response": response
            }
            await ctx.send_message(response_with_source)
            
        except Exception as e:
            error_msg = f"Error communicating with Conversation Agent: {str(e)}"
            print(error_msg)
            error_with_source = {
                "source": self.id,
                "response": error_msg
            }
            await ctx.send_message(error_with_source)

