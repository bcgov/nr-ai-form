from typing import Any
from agent_framework import Executor, WorkflowContext, handler

class Dispatcher(Executor):
    """
    The sole purpose of this executor is to dispatch the input of the workflow to
    other executors.
    """

    @handler    
    async def handle(self, conversation: list[Any], ctx: WorkflowContext[str]):
        #TODOL:ABIN, need to sanitize the PII from the user query
        if not conversation:
            raise RuntimeError("Input conversation must not be empty.")

        last_message = conversation[-1]
        
        # Determine how to get text based on message type
        userquery = ""
        if hasattr(last_message, 'text'):
            userquery = last_message.text
        elif isinstance(last_message, dict) and 'text' in last_message:
            userquery = last_message['text']
        else:
            userquery = str(last_message)

        if not userquery:
            raise RuntimeError("Input must not be empty.")

        await ctx.send_message(userquery)