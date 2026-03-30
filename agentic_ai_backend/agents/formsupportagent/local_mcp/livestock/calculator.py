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


def _get_application_fee(livestock: dict[str, Any]) -> int:
    """Return the flat application fee as an integer."""
    return int(livestock.get("application_fees", 0))


def _validate_livestock_type(livestock_type: str) -> str:
    normalized_livestock_type = livestock_type.strip().lower()
    if normalized_livestock_type not in load_livestock_rates():
        supported_livestock = ", ".join(get_supported_livestock())
        raise ValueError(
            f"Unsupported livestock_type '{livestock_type}'. "
            f"Supported values: {supported_livestock}."
        )
    return normalized_livestock_type


def _validate_period_type(period_type: str) -> None:
    if period_type not in PERIOD_MULTIPLIERS:
        supported_periods = ", ".join(PERIOD_MULTIPLIERS)
        raise ValueError(
            f"Unsupported period_type '{period_type}'. "
            f"Supported values: {supported_periods}."
        )


def calculate_water_consumption(
    livestock_type: str,
    livestock_count: int | float,
    period_type: str,
    period_count: int | float,
) -> dict[str, Any]:
    """Calculate water consumption in cubic meters for the requested period."""
    normalized_livestock_type = _validate_livestock_type(livestock_type)
    _validate_period_type(period_type)

    if livestock_count <= 0:
        raise ValueError("livestock_count must be greater than 0.")

    if period_count <= 0:
        raise ValueError(f"{period_type[:-1]}_count must be greater than 0.")

    livestock = load_livestock_rates()[normalized_livestock_type]
    daily_rate = livestock["water_consumption_m3_per_day"]
    application_fee = _get_application_fee(livestock)
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
        "application_fee": application_fee,
        "assumptions": {
            "month_days": PERIOD_MULTIPLIERS["months"],
            "year_days": PERIOD_MULTIPLIERS["years"],
        },
    }


def calculate_multiple_water_consumption(
    livestock_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate combined water consumption for multiple livestock entries."""
    if not livestock_entries:
        raise ValueError("livestock_entries must contain at least one item.")

    calculations = []
    combined_total_m3 = 0.0

    for index, entry in enumerate(livestock_entries, start=1):
        try:
            livestock_type = entry["livestock_type"]
            livestock_count = entry["livestock_count"]
            period_type = entry["period_type"]
            period_count = entry["period_count"]
        except KeyError as exc:
            raise ValueError(
                "Each livestock entry must include livestock_type, livestock_count, "
                "period_type, and period_count."
            ) from exc

        result = calculate_water_consumption(
            livestock_type=livestock_type,
            livestock_count=livestock_count,
            period_type=period_type,
            period_count=period_count,
        )
        result["entry_index"] = index
        calculations.append(result)
        combined_total_m3 += result["total_water_consumption_m3"]

    return {
        "entry_count": len(calculations),
        "calculations": calculations,
        "combined_total_water_consumption_m3": round(combined_total_m3, 6),
        "application_fee": calculations[0]["application_fee"],
        "assumptions": {
            "month_days": PERIOD_MULTIPLIERS["months"],
            "year_days": PERIOD_MULTIPLIERS["years"],
        },
    }
