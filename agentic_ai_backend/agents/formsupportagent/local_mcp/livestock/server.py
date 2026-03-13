from __future__ import annotations

from local_mcp.livestock.calculator import (
    calculate_multiple_water_consumption,
    calculate_water_consumption,
    get_supported_livestock,
)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "The 'mcp' package is required to run the livestock water consumption MCP "
        "server. Install it before starting this server."
    ) from exc


mcp = FastMCP("livestock-water-consumption")


@mcp.tool(
    name="calculate_livestock_water_consumption_days",
    description=(
        "Calculate livestock water consumption in cubic meters (m3) for a number "
        "of days."
    ),
)
def calculate_livestock_water_consumption_days(
    livestock_type: str,
    livestock_count: int | float,
    days: int | float,
) -> dict:
    return calculate_water_consumption(
        livestock_type=livestock_type,
        livestock_count=livestock_count,
        period_type="days",
        period_count=days,
    )


@mcp.tool(
    name="calculate_livestock_water_consumption_weeks",
    description=(
        "Calculate livestock water consumption in cubic meters (m3) for a number "
        "of weeks."
    ),
)
def calculate_livestock_water_consumption_weeks(
    livestock_type: str,
    livestock_count: int | float,
    weeks: int | float,
) -> dict:
    return calculate_water_consumption(
        livestock_type=livestock_type,
        livestock_count=livestock_count,
        period_type="weeks",
        period_count=weeks,
    )


@mcp.tool(
    name="calculate_livestock_water_consumption_months",
    description=(
        "Calculate livestock water consumption in cubic meters (m3) for a number "
        "of months. Assumes 30 days per month."
    ),
)
def calculate_livestock_water_consumption_months(
    livestock_type: str,
    livestock_count: int | float,
    months: int | float,
) -> dict:
    return calculate_water_consumption(
        livestock_type=livestock_type,
        livestock_count=livestock_count,
        period_type="months",
        period_count=months,
    )


@mcp.tool(
    name="calculate_livestock_water_consumption_years",
    description=(
        "Calculate livestock water consumption in cubic meters (m3) for a number "
        "of years. Assumes 365 days per year."
    ),
)
def calculate_livestock_water_consumption_years(
    livestock_type: str,
    livestock_count: int | float,
    years: int | float,
) -> dict:
    return calculate_water_consumption(
        livestock_type=livestock_type,
        livestock_count=livestock_count,
        period_type="years",
        period_count=years,
    )


@mcp.tool(
    name="list_supported_livestock_types",
    description="List supported livestock types for water-consumption calculations.",
)
def list_supported_livestock_types() -> list[str]:
    return get_supported_livestock()


@mcp.tool(
    name="calculate_multiple_livestock_water_consumption",
    description=(
        "Calculate combined livestock water consumption in cubic meters (m3) for "
        "multiple livestock entries. Each item must include livestock_type, "
        "livestock_count, period_type, and period_count."
    ),
)
def calculate_multiple_livestock_water_consumption(
    livestock_entries: list[dict],
) -> dict:
    return calculate_multiple_water_consumption(livestock_entries)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
