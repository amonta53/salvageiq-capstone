# =========================================================
# pricing_metrics.py
# Price-related helper functions for analysis output
#
# Purpose:
# Hold the pricing rules used when building summary results.
# This is where we decide how to measure price.
#
# =========================================================
from __future__ import annotations

import pandas as pd


# =========================================================
# 1. Price outlier handling
# =========================================================
def filter_price_outliers(
    group: pd.DataFrame,
    price_column: str = "price_clean",
    min_group_size: int = 20,
    lower_quantile: float = 0.05,
    upper_quantile: float = 0.95,
) -> pd.DataFrame:
    """
    Trim off the outlier price values for a group.

    What it does:
    - drops rows with no price
    - if the group is small, leaves it alone
    - if the group is big enough, cuts off the top and bottom ends

    Why:
    - a few bad listings can throw off pricing fast
    - this keeps the middle of the data where most real prices live

    Returns:
    - filtered copy of the group, safe to use for price stats
    """
    priced = group.dropna(subset=[price_column]).copy()

    if len(priced) < min_group_size:
        return priced

    lower_bound = priced[price_column].quantile(lower_quantile)
    upper_bound = priced[price_column].quantile(upper_quantile)

    return priced[
        (priced[price_column] >= lower_bound)
        & (priced[price_column] <= upper_bound)
    ].copy()