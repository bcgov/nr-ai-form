from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


CALC_DATA_PATH = Path(__file__).with_name("calc.json")
PERIOD_MULTIPLIERS = {
    "days": 1,
    "weeks": 7,
    "months": 30,
    "years": 365,
}


@lru_cache(maxsize=1)
def load_livestock_rates() -> dict[str, dict[str, Any]]:
    """Load livestock rates keyed by livestock name."""
    with CALC_DATA_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    livestock_entries = payload["livestock_water_consumption"]["data"]
    return {entry["name"]: entry for entry in livestock_entries}


def get_supported_livestock() -> list[str]:
    return sorted(load_livestock_rates())


def calculate_water_consumption(
    livestock_type: str,
    livestock_count: int | float,
    period_type: str,
    period_count: int | float,
) -> dict[str, Any]:
    """Calculate water consumption in cubic meters for the requested period."""
    normalized_livestock_type = livestock_type.strip().lower()

    if normalized_livestock_type not in load_livestock_rates():
        supported_livestock = ", ".join(get_supported_livestock())
        raise ValueError(
            f"Unsupported livestock_type '{livestock_type}'. "
            f"Supported values: {supported_livestock}."
        )

    if period_type not in PERIOD_MULTIPLIERS:
        supported_periods = ", ".join(PERIOD_MULTIPLIERS)
        raise ValueError(
            f"Unsupported period_type '{period_type}'. "
            f"Supported values: {supported_periods}."
        )

    if livestock_count <= 0:
        raise ValueError("livestock_count must be greater than 0.")

    if period_count <= 0:
        raise ValueError(f"{period_type[:-1]}_count must be greater than 0.")

    livestock = load_livestock_rates()[normalized_livestock_type]
    daily_rate = livestock["water_consumption_m3_per_day"]
    total_period_days = PERIOD_MULTIPLIERS[period_type] * period_count
    total_water_consumption = round(daily_rate * livestock_count * total_period_days, 6)

    return {
        "livestock_type": livestock["name"],
        "livestock_description": livestock["description"],
        "livestock_count": livestock_count,
        "period_type": period_type,
        "period_count": period_count,
        "daily_water_consumption_m3_per_animal": daily_rate,
        "total_period_days": total_period_days,
        "total_water_consumption_m3": total_water_consumption,
        "assumptions": {
            "month_days": PERIOD_MULTIPLIERS["months"],
            "year_days": PERIOD_MULTIPLIERS["years"],
        },
    }

