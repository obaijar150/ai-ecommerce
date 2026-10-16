"""
Constraint extraction for natural-language product search.

Pulls hard filters (budget, category, availability, intended use) out of a
free-text query without inventing data — every field is either derived from
explicit user wording or left ``None``.
"""

from __future__ import annotations

import re
from typing import Any

from apps.ai_engine.text.normalizer import normalize, tokens


_BUDGET_MAX_PATTERNS = (
    r"(?:under|below|less than|cheaper than|lower than|up to|max(?:imum)?)\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
    r"\$([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:max|or less|or under)",
)
_BUDGET_MIN_PATTERNS = (
    r"(?:over|above|more than|greater than|min(?:imum)?|at least)\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
)
_BUDGET_RANGE_PATTERN = re.compile(
    r"between\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:and|to|-)\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)"
)

_AVAILABILITY_WORDS = {"available", "in stock", "in-stock", "ready", "instock"}
_CATEGORY_HINTS = {
    "laptop": "laptops",
    "notebook": "laptops",
    "phone": "smartphones",
    "smartphone": "smartphones",
    "headphone": "headphones",
    "headphones": "headphones",
    "earbud": "headphones",
    "earbuds": "headphones",
    "cookware": "cookware",
    "espresso": "coffee",
    "coffee": "coffee",
    "shoe": "shoes",
    "shoes": "shoes",
    "watch": "watches",
}
_USE_HINTS = {
    "programming": ["laptop", "notebook"],
    "coding": ["laptop", "notebook"],
    "development": ["laptop", "notebook"],
    "gaming": ["laptop", "gaming"],
    "travel": ["laptop", "lightweight"],
    "photography": ["camera", "lens"],
}


def _money(value: str) -> float:
    return float(value.replace(",", ""))


def extract_constraints(text: str) -> dict[str, Any]:
    """Extract hard filters and intent from a natural-language query.

    Returns a dictionary with keys: ``budget_min``, ``budget_max``,
    ``category``, ``intended_use``, ``availability_required``.
    """
    raw = text or ""
    lowered = normalize(raw)
    constraints: dict[str, Any] = {
        "budget_min": None,
        "budget_max": None,
        "category": None,
        "intended_use": None,
        "availability_required": False,
    }

    # Range first (between X and Y).
    range_match = _BUDGET_RANGE_PATTERN.search(lowered)
    if range_match:
        low, high = _money(range_match.group(1)), _money(range_match.group(2))
        constraints["budget_min"] = min(low, high)
        constraints["budget_max"] = max(low, high)
    else:
        for pattern in _BUDGET_MAX_PATTERNS:
            match = re.search(pattern, lowered)
            if match:
                constraints["budget_max"] = _money(match.group(1))
                break
        for pattern in _BUDGET_MIN_PATTERNS:
            match = re.search(pattern, lowered)
            if match:
                constraints["budget_min"] = _money(match.group(1))
                break

    token_list = tokens(lowered)
    for token in token_list:
        if token in _CATEGORY_HINTS:
            constraints["category"] = _CATEGORY_HINTS[token]
            break

    for use, hints in _USE_HINTS.items():
        if use in token_list:
            constraints["intended_use"] = use
            if constraints["category"] is None and hints:
                constraints["category"] = hints[0]
            break

    if any(word in lowered for word in ("in stock", "available", "ready")):
        constraints["availability_required"] = True

    return constraints
