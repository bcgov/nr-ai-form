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


def find_step_interceptor(query: str) -> dict[str, Any] | None:
    """
    Check if a user query matches any interceptor rule.
    
    Compares the query against configured match terms and returns the first
    matching rule or None if no match is found.
    
    Args:
        query: User query text to check for trigger terms
        
    Returns:
        Rule dict if a match is found, None otherwise.
    """
    if not query:
        return None

    # Normalize query for case-insensitive comparison
    normalized_query = query.lower()

    # Load rules and check for matches
    for rule in _load_step_interceptor_rules():
        # Check if any match term appears in the query
        terms = rule.get("match_terms", [])
        if any(term and term.lower() in normalized_query for term in terms):
            return rule

    return None
