"""Registry mapping client-profile tool set names to in-process MCP tools.

A tenant's ClientProfile selects tool sets by name via
``subAgents[formSupportAgent].config.mcpTools``. Add new tool sets here.
"""

from local_mcp.fishing_licence.inprocess_client import (
    FISHING_LICENCE_FEE_CALCULATION_TOOLS,
)
from local_mcp.livestock.inprocess_client import (
    LIVESTOCK_WATER_CONSUMPTION_TOOLS,
)

TOOL_SETS = {
    "LIVESTOCK_WATER_CONSUMPTION_TOOLS": LIVESTOCK_WATER_CONSUMPTION_TOOLS,
    "FISHING_LICENCE_FEE_CALCULATION_TOOLS": FISHING_LICENCE_FEE_CALCULATION_TOOLS,
}


def resolve_tool_sets(tool_set_names: list[str] | None) -> list:
    """Return the combined tools for the named tool sets, in order, without duplicates."""
    if isinstance(tool_set_names, str):
        raise ValueError("client_settings.config.mcpTools must be a list of tool set names.")

    unknown = [name for name in tool_set_names or [] if name not in TOOL_SETS]
    if unknown:
        raise ValueError(
            f"Unknown tool set(s) in client_settings.config.mcpTools: {', '.join(unknown)}. "
            f"Supported: {', '.join(TOOL_SETS)}."
        )

    tools = []
    for name in dict.fromkeys(tool_set_names or []):
        tools.extend(TOOL_SETS[name])
    return tools
