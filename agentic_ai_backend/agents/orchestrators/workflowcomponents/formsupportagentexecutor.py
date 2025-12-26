
from agent_framework import Executor, WorkflowContext, handler
from typing import Any, Optional
from a2aclients.formsupportagentclient import FormSupportAgentA2AClient

class FormSupportAgentA2AExecutor(Executor):
    """
    Executor that communicates with Form Support Agent via A2A protocol.
    Supports dynamic form step selection.
    """
    
    def __init__(
        self, 
        base_url: str = "http://localhost:8001",
        step_number: Optional[int] = 2,
        id: str = "FormSupportAgentA2A",
        name: str = "Form Support Agent (A2A)",
        instructions: str = "Handles form support queries using A2A protocol"
    ):
        super().__init__(id=id, name=name, instructions=instructions)
        self.client = FormSupportAgentA2AClient(base_url=base_url)
        self.step_number = step_number
        
    @handler
    async def handle(self, query: str, ctx: WorkflowContext[str]):
        """
        Handle incoming query by forwarding to Form Support Agent via A2A.
        
        Args:
            query: User query string
            ctx: Workflow context for sending messages
        """
        try:
            # Invoke the remote agent via A2A with step number
            response = await self.client.invoke(query, step_number=self.step_number)
            
            # Send the response with source information
            # Wrap it in a dict so we can track the source
            response_with_source = {
                "source": self.id,
                "response": response,
                "step_number": self.step_number
            }
            await ctx.send_message(response_with_source)
            
        except Exception as e:
            error_msg = f"Error communicating with Form Support Agent (step {self.step_number}): {str(e)}"
            print(error_msg)
            error_with_source = {
                "source": self.id,
                "response": error_msg,
                "step_number": self.step_number
            }
            await ctx.send_message(error_with_source)
