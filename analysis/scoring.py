# =========================================================
# scoring.py
# Scoring helper functions for the analysis layer
#
# Purpose:
# Hold the math used to score and compare part categories.
# Keep formulas here so aggregation can stay focused on
# grouping and merging data.
#
# Keep this file focused:
# - sell-through rate
# - confidence score
# - opportunity score
# =========================================================

from __future__ import annotations

from typing import Any

# =========================================================
# Sell-through rate
# =========================================================
def calculate_str(
    sold_count: int,
    active_count: int,
) -> float:
    """
    Calculate the sell-through rate proxy.

    This compares sold count to the full observed count
    of sold plus active listings.
    """
    total_count = sold_count + active_count

    if total_count == 0:
        return 0.0

    return round(sold_count / total_count, 4)


# =========================================================
# Confidence score
# =========================================================
def calculate_confidence_score(
    sold_count: int,
    active_count: int,
    config: Any,
) -> float:
    """
    Build a simple confidence score based on how much data
    supports the result.

    More sold rows and more active rows usually mean the
    summary has better support behind it.
    """

    sold_target = config.confidence_sold_target
    active_target = config.confidence_active_target
    sold_weight = config.confidence_sold_weight
    active_weight = config.confidence_active_weight
    max_score = config.confidence_max_score

    if sold_target <= 0 or active_target <= 0:
        return 0.0

    sold_component = min(max_score, sold_count / sold_target)
    active_component = min(max_score, active_count / active_target)

    score = (sold_component * sold_weight) + (active_component * active_weight)

    return round(score, 4)


# =========================================================
# Opportunity score
# =========================================================
def calculate_opportunity_score(
    median_price: float,
    str_value: float,
    confidence_score: float,
) -> float:
    """
    Calculate the final score used to rank parts.

    This blends price, demand, and confidence into one number
    that makes comparison easier.
    """
    if median_price is None:
        return 0.0

    return round(median_price * str_value * confidence_score, 4)