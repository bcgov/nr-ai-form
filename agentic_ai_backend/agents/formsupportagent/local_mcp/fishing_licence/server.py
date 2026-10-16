from __future__ import annotations

from local_mcp.fishing_licence.calculator import (
    calculate_fishing_licence_fee,
    get_fee_schedule,
)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "The 'mcp' package is required to run the fishing licence MCP server. "
        "Install it before starting this server."
    ) from exc


mcp = FastMCP("bc-fishing-licence-fee")


@mcp.tool(
    name="calculate_fishing_licence_fee",
    description=(
        "Calculate the total cost of a BC recreational freshwater fishing licence. "
        "Returns an itemized fee breakdown including base licence, conservation "
        "surcharge stamps, White Sturgeon Conservation Licence (if selected), and "
        "Classified Waters Licence (if applicable). "
        "Residency values: 'resident', 'non-resident', 'alien'. "
        "Duration values: 'one-day', 'eight-day', 'annual'. "
        "Surcharge values: 'steelhead', 'salmon', 'rainbow-char', 'sturgeon'."
    ),
)
def tool_calculate_fishing_licence_fee(
    residency: str,
    duration: str,
    is_senior: bool = False,
    has_disability_reduction: bool = False,
    surcharges: list[str] | None = None,
    classified_waters: bool = False,
    classified_waters_days: int = 1,
) -> dict:
    return calculate_fishing_licence_fee(
        residency=residency,
        duration=duration,
        is_senior=is_senior,
        has_disability_reduction=has_disability_reduction,
        surcharges=surcharges or [],
        classified_waters=classified_waters,
        classified_waters_days=classified_waters_days,
    )


@mcp.tool(
    name="get_fishing_licence_fee_schedule",
    description=(
        "Return the complete BC recreational freshwater fishing licence fee schedule, "
        "including base fees by residency and duration, conservation surcharge stamp "
        "fees, White Sturgeon Conservation Licence fees, and Classified Waters Licence "
        "fees. Useful when the user asks what fees exist or wants to compare rates."
    ),
)
def tool_get_fishing_licence_fee_schedule() -> dict:
    return get_fee_schedule()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
