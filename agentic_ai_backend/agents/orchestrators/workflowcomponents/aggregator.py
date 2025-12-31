from agent_framework import Executor, WorkflowContext, handler
from typing import Any

class Aggregator(Executor):
    """Aggregate the results from the different tasks and yield the final output."""

    @handler
    async def handle(self, results: list[Any], ctx: WorkflowContext):
        """Receive the results from the source executors.

        The framework will automatically collect messages from the source executors
        and deliver them as a list.

        Args:
            results (list[Any]): execution results from upstream executors.
                The type annotation must be a list of union types that the upstream
                executors will produce.
            ctx (WorkflowContext[Never, list[Any]]): A workflow context that can yield the final output.
        """
        await ctx.yield_output(results)