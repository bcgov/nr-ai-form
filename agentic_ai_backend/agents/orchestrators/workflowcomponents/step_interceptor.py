"""
Step Interceptor Module

Provides configuration-driven query interception before sub-agent execution.
"""

import json
import os
from typing import Any


def _load_step_interceptor_rules() -> list[dict[str, Any]]:
    """Load step interceptor rules from JSON configuration file."""
    rules_path = os.path.join(os.path.dirname(__file__), "step_interceptor_rules.json")
    try:
        with open(rules_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def find_step_interceptor(step_number: Any, query: str) -> dict[str, Any] | None:
    """
    Check if a user query matches any interceptor rule for the given form step.

    Matching logic:
    - If a rule declares `step_ids`, the step_number must exactly match one
      of those ids (case-insensitive, trimmed) for the rule to be considered.
    - If a rule does not declare `step_ids`, it is considered global and
      can match regardless of the step_number.
    - A match occurs when any of the rule's `match_terms` appears as a
      case-insensitive substring in the query.

    Args:
        step_number: Form step identifier, e.g. "step7-Contact-Information"
        query: User query text to check for trigger terms

    Returns:
        Rule dict if a match is found, None otherwise.
    """
    if not query:
        return None

    normalized_step = str(step_number).strip().lower() if step_number is not None else ""
    normalized_query = query.lower()

    for rule in _load_step_interceptor_rules():
        step_ids = rule.get("step_ids")
        # If step_ids are provided, only consider the rule when the step matches exactly
        if step_ids:
            if isinstance(step_ids, str):
                step_ids = [step_ids]
            if not any(normalized_step == str(s).strip().lower() for s in step_ids):
                continue

        terms = rule.get("match_terms", [])
        if any(term and term.lower() in normalized_query for term in terms):
            return rule

    return None
