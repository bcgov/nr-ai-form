from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

RATES_PATH = Path(__file__).with_name("rates.json")

VALID_RESIDENCY = {"resident", "non-resident", "alien"}
VALID_DURATION = {"one-day", "eight-day", "annual"}
VALID_SURCHARGES = {"steelhead", "salmon", "rainbow-char", "sturgeon"}

# alien shares the non-resident surcharge/sturgeon/classified-waters tier
_NON_RESIDENT_TIER = {"non-resident", "alien"}


@lru_cache(maxsize=1)
def _load_rates() -> dict[str, Any]:
    with RATES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_fee_schedule() -> dict[str, Any]:
    """Return the full fee schedule for reference."""
    return _load_rates()


def _validate_inputs(
    residency: str,
    duration: str,
    surcharges: list[str],
    classified_waters_days: int | float,
) -> None:
    if residency not in VALID_RESIDENCY:
        raise ValueError(
            f"Invalid residency '{residency}'. "
            f"Must be one of: {', '.join(sorted(VALID_RESIDENCY))}."
        )
    if duration not in VALID_DURATION:
        raise ValueError(
            f"Invalid duration '{duration}'. "
            f"Must be one of: {', '.join(sorted(VALID_DURATION))}."
        )
    invalid = [s for s in surcharges if s not in VALID_SURCHARGES]
    if invalid:
        raise ValueError(
            f"Invalid surcharge(s): {', '.join(invalid)}. "
            f"Must be from: {', '.join(sorted(VALID_SURCHARGES))}."
        )
    if classified_waters_days < 1:
        raise ValueError("classified_waters_days must be at least 1.")


def calculate_fishing_licence_fee(
    residency: str,
    duration: str,
    is_senior: bool = False,
    has_disability_reduction: bool = False,
    surcharges: list[str] | None = None,
    classified_waters: bool = False,
    classified_waters_days: int | float = 1,
) -> dict[str, Any]:
    """
    Calculate the total BC recreational freshwater fishing licence fee.

    Parameters
    ----------
    residency : str
        Applicant residency: 'resident', 'non-resident', or 'alien'.
    duration : str
        Licence duration: 'one-day', 'eight-day', or 'annual'.
    is_senior : bool
        True if the applicant is 65 or older (resident annual only).
    has_disability_reduction : bool
        True if the applicant holds a Certificate of Eligibility for the fee
        reduction program (resident annual only; takes precedence over senior rate).
    surcharges : list[str]
        Conservation surcharge stamps to add. Valid values:
        'steelhead', 'salmon', 'rainbow-char', 'sturgeon'.
        'sturgeon' adds the White Sturgeon Conservation Licence (duration-sensitive).
    classified_waters : bool
        True to add a Classified Waters Licence.
    classified_waters_days : int | float
        Number of days fishing classified waters (non-residents only; default 1).

    Returns
    -------
    dict with keys: residency, duration, base_fee, surcharge_fees,
    classified_waters_fee, total, notes.
    """
    surcharges = surcharges or []
    _validate_inputs(residency, duration, surcharges, classified_waters_days)

    rates = _load_rates()
    notes: list[str] = []

    # --- Base fee ---
    base_fees = rates["base_fees"]
    if residency == "resident" and duration == "annual":
        if has_disability_reduction:
            base_fee = base_fees["resident"]["disability_annual"]
            if is_senior:
                notes.append(
                    "Senior rate not applied: disability reduction takes precedence."
                )
        elif is_senior:
            base_fee = base_fees["resident"]["senior_annual"]
        else:
            base_fee = base_fees["resident"]["annual"]
    else:
        if (is_senior or has_disability_reduction) and residency == "resident":
            notes.append(
                "Senior/disability rates apply to annual resident licences only; "
                f"standard {duration} rate used."
            )
        base_fee = base_fees[residency][duration]

    # --- Surcharge stamps and White Sturgeon licence ---
    surcharge_tier = "resident" if residency == "resident" else "non-resident"
    stamp_rates = rates["surcharges"][surcharge_tier]
    sturgeon_rates = rates["sturgeon"][surcharge_tier]

    surcharge_fees: list[dict[str, Any]] = []
    for stamp in surcharges:
        if stamp == "sturgeon":
            amount = sturgeon_rates[duration]
            surcharge_fees.append({"surcharge": "sturgeon (White Sturgeon Conservation Licence)", "amount": amount})
        else:
            amount = stamp_rates[stamp]
            surcharge_fees.append({"surcharge": stamp, "amount": amount})

    # --- Classified Waters Licence ---
    classified_waters_fee = 0.0
    if classified_waters:
        cw_rates = rates["classified_waters"]
        if residency == "resident":
            classified_waters_fee = cw_rates["resident"]["annual"]
        else:
            daily_rate = cw_rates["non-resident"]["daily"]
            classified_waters_fee = round(daily_rate * classified_waters_days, 2)
            notes.append(
                f"Non-resident classified waters: {classified_waters_days} "
                f"day(s) × ${daily_rate:.2f} = ${classified_waters_fee:.2f}."
            )

    total = round(
        base_fee
        + sum(item["amount"] for item in surcharge_fees)
        + classified_waters_fee,
        2,
    )

    return {
        "residency": residency,
        "duration": duration,
        "base_fee": base_fee,
        "surcharge_fees": surcharge_fees,
        "classified_waters_fee": classified_waters_fee,
        "total": total,
        "notes": notes,
    }
