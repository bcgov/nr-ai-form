from agent_framework import Executor, WorkflowContext, handler

class Dispatcher(Executor):
    """
    The sole purpose of this executor is to dispatch the input of the workflow to
    other executors.
    """

    @handler    
    async def handle(self, userquery: str, ctx: WorkflowContext[str]):
        if not userquery:
            raise RuntimeError("Input must not be empty.")

        await ctx.send_message(userquery)