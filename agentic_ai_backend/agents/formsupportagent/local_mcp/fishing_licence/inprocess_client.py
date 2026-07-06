from __future__ import annotations

import json

from agent_framework import tool

from .calculator import (
    calculate_fishing_licence_fee,
    get_fee_schedule,
)


@tool(
    name="calculate_fishing_licence_fee",
    description=(
        "Calculate the total cost of a BC recreational freshwater fishing licence. "
        "Returns an itemized fee breakdown including base licence, conservation "
        "surcharge stamps, White Sturgeon Conservation Licence (if selected), and "
        "Classified Waters Licence (if applicable). "
        "residency: 'resident', 'non-resident', or 'alien'. "
        "duration: 'one-day', 'eight-day', or 'annual'. "
        "surcharges: list of zero or more values from "
        "'steelhead', 'salmon', 'rainbow-char', 'sturgeon'. "
        "is_senior: true if applicant is 65+ (applies to resident annual only). "
        "has_disability_reduction: true if applicant holds a Certificate of Eligibility "
        "(resident annual only; takes precedence over senior rate). "
        "classified_waters: true to add a Classified Waters Licence. "
        "classified_waters_days: number of days for non-resident classified waters (default 1)."
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
) -> str:
    return json.dumps(
        calculate_fishing_licence_fee(
            residency=residency,
            duration=duration,
            is_senior=is_senior,
            has_disability_reduction=has_disability_reduction,
            surcharges=surcharges or [],
            classified_waters=classified_waters,
            classified_waters_days=classified_waters_days,
        )
    )


@tool(
    name="get_fishing_licence_fee_schedule",
    description=(
        "Return the complete BC recreational freshwater fishing licence fee schedule, "
        "including base fees by residency and duration, conservation surcharge stamp "
        "fees, White Sturgeon Conservation Licence fees, and Classified Waters Licence "
        "fees. Useful when the user asks what fees exist or wants to compare rates."
    ),
)
def tool_get_fishing_licence_fee_schedule() -> str:
    return json.dumps(get_fee_schedule())


FISHING_LICENCE_TOOLS = [
    tool_calculate_fishing_licence_fee,
    tool_get_fishing_licence_fee_schedule,
]
