
from typing import Any, Optional, Union

from agent_framework import Executor, WorkflowContext, handler

from a2aclients.formsupportagentclient import FormSupportAgentA2AClient
from models.intentmodel import IntentListModel, IntentModel
from workflowcomponents.routing import get_intent_for_agent, get_primary_intent

class FormSupportAgentA2AExecutor(Executor):
    """
    Executor that communicates with Form Support Agent via A2A protocol.
    Supports dynamic form step selection.
    """
    
    def __init__(
        self, 
        base_url: str = "http://localhost:8001",
        step_number: Optional[Union[int, str]] = "step2-Eligibility",
        id: str = "FormSupportAgentA2A",
        name: str = "Form Support Agent (A2A)",
        instructions: str = "Handles form support queries using A2A protocol",
        session_id: str = None
    ):
        super().__init__(id=id, name=name, instructions=instructions)
        self.client = FormSupportAgentA2AClient(base_url=base_url)
        self.step_number = step_number
        self.session_id = session_id
        
    @handler
    async def handle(
        self,
        task: IntentListModel | IntentModel,
        ctx: WorkflowContext[dict[str, Any]],
    ):
        """
        Handle incoming query by forwarding to Form Support Agent via A2A.
        
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
                    "step_number": self.step_number,
                }
            )
            return

        try:
            # Invoke the remote agent via A2A with step number and session_id for history
            response = await self.client.invoke(
                intent.query,
                session_id=self.session_id,
                step_number=self.step_number,
            )
            
            # Send the response with source information
            # Wrap it in a dict so we can track the source
            response_with_source = {
                "source": self.id,
                "response": response,
                "step_number": self.step_number,
                "confidence": intent.confidence,
            }
            await ctx.send_message(response_with_source)
            
        except Exception as e:
            error_msg = f"Error communicating with Form Support Agent (step {self.step_number}): {str(e)}"
            print(error_msg)
            error_with_source = {
                "source": self.id,
                "response": error_msg,
                "step_number": self.step_number,
                "confidence": intent.confidence,
            }
            await ctx.send_message(error_with_source)
