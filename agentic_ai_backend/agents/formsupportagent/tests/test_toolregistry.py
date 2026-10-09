import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from local_mcp.fishing_licence.inprocess_client import FISHING_LICENCE_FEE_CALCULATION_TOOLS
from local_mcp.livestock.inprocess_client import LIVESTOCK_WATER_CONSUMPTION_TOOLS
from local_mcp.toolregistry import resolve_tool_sets


@pytest.mark.parametrize("names", [None, []])
def test_no_tool_sets_returns_empty(names):
    assert resolve_tool_sets(names) == []


def test_single_tool_set():
    assert resolve_tool_sets(["FISHING_LICENCE_FEE_CALCULATION_TOOLS"]) == FISHING_LICENCE_FEE_CALCULATION_TOOLS


def test_multiple_tool_sets_combined_in_order_without_duplicates():
    tools = resolve_tool_sets([
        "LIVESTOCK_WATER_CONSUMPTION_TOOLS",
        "FISHING_LICENCE_FEE_CALCULATION_TOOLS",
        "LIVESTOCK_WATER_CONSUMPTION_TOOLS",
    ])
    assert tools == LIVESTOCK_WATER_CONSUMPTION_TOOLS + FISHING_LICENCE_FEE_CALCULATION_TOOLS


def test_unknown_tool_set_raises():
    with pytest.raises(ValueError, match="NOT_A_TOOL_SET"):
        resolve_tool_sets(["NOT_A_TOOL_SET"])


def test_string_instead_of_list_raises():
    with pytest.raises(ValueError, match="must be a list"):
        resolve_tool_sets("LIVESTOCK_WATER_CONSUMPTION_TOOLS")
