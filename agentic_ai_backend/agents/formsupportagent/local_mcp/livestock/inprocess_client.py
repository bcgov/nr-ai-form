

import json

from agent_framework import ai_function

from .calculator import (
    calculate_multiple_water_consumption,
    calculate_water_consumption,
    get_supported_livestock,
)


@ai_function(
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
) -> str:
    return json.dumps(
        calculate_water_consumption(livestock_type, livestock_count, "days", days)
    )


@ai_function(
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
) -> str:
    return json.dumps(
        calculate_water_consumption(livestock_type, livestock_count, "weeks", weeks)
    )


@ai_function(
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
) -> str:
    return json.dumps(
        calculate_water_consumption(livestock_type, livestock_count, "months", months)
    )


@ai_function(
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
) -> str:
    return json.dumps(
        calculate_water_consumption(livestock_type, livestock_count, "years", years)
    )


@ai_function(
    name="list_supported_livestock_types",
    description="List supported livestock types for water-consumption calculations.",
)
def list_supported_livestock_types() -> str:
    return json.dumps(get_supported_livestock())


@ai_function(
    name="calculate_multiple_livestock_water_consumption",
    description=(
        "Calculate combined livestock water consumption in cubic meters (m3) for "
        "multiple livestock entries. Input must be a JSON array string where each "
        "item contains livestock_type, livestock_count, period_type, and "
        "period_count. Example: "
        '[{"livestock_type":"beef","livestock_count":10,"period_type":"years","period_count":1},'
        '{"livestock_type":"poultry_broiler","livestock_count":20,"period_type":"months","period_count":10}]'
    ),
)
def calculate_multiple_livestock_water_consumption(livestock_entries_json: str) -> str:
    livestock_entries = json.loads(livestock_entries_json)
    return json.dumps(calculate_multiple_water_consumption(livestock_entries))


LIVESTOCK_WATER_CONSUMPTION_TOOLS = [
    calculate_livestock_water_consumption_days,
    calculate_livestock_water_consumption_weeks,
    calculate_livestock_water_consumption_months,
    calculate_livestock_water_consumption_years,
    calculate_multiple_livestock_water_consumption,
    list_supported_livestock_types,
]
