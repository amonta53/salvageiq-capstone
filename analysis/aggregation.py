# =========================================================
# aggregation.py
# Build analysis-ready summary from sold listings and market data
#
# Purpose:
# Combine sold listing history with active market summary so we
# can calculate snapshot-based STR and prepare for scoring.
#
# Notes:
# - Sold data comes from normalized listings
# - Active data comes from ebay_market_summary
# - STR is approximate, not true turnover
# =========================================================

from typing import Any

import pandas as pd

from analysis.pricing_metrics import filter_price_outliers
from analysis.scoring import (
    calculate_confidence_score,
    calculate_opportunity_score,
    calculate_str,
)


# =========================================================
# Validation Helpers
# =========================================================
def validate_columns(
    df: pd.DataFrame,
    required_cols: list[str],
    df_name: str,
) -> None:
    """Make sure expected columns exist."""
    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        raise ValueError(
            f"Missing required columns in {df_name}: {missing}"
        )


# =========================================================
# Sold Listing Aggregation
# =========================================================
def summarize_sold_group(
    group: pd.DataFrame,
    price_column: str,
    timestamp_column: str,
) -> pd.Series:
    """
    Build one sold-summary row for a single year / make / model / part group.

    Count, min, max, and timestamp come from the full priced group.
    Median and mean come from the trimmed price group so a few odd
    listings do not throw off the main price numbers.
    """
    priced = group.dropna(subset=[price_column]).copy()
    trimmed_priced = filter_price_outliers(
        priced,
        price_column=price_column,
    )

    return pd.Series(
        {
            "sold_count": priced[price_column].count(),
            "median_sold_price": trimmed_priced[price_column].median(),
            "mean_sold_price": trimmed_priced[price_column].mean(),
            "min_sold_price": priced[price_column].min(),
            "max_sold_price": priced[price_column].max(),
            "sold_timestamp": priced[timestamp_column].max(),
        }
    )

def build_sold_summary(
    sold_df: pd.DataFrame,
    config: Any,
) -> pd.DataFrame:
    """Summarize sold listings by year, make, model, and part."""
    sold_cols = config.sold_column_map

    sold_group_cols = [
        sold_cols["year"],
        sold_cols["make"],
        sold_cols["model"],
        sold_cols["part"],
    ]

    validate_columns(
        sold_df,
        sold_group_cols + [sold_cols["price"], sold_cols["timestamp"]],
        "sold_df",
    )

    # To keep row level data, but trim price outliers for the median and mean
    # Use the summarize_sold_group function to build the summary stats for each group.
    sold_summary = (
        sold_df.groupby(sold_group_cols, dropna=False)
        .apply(
            lambda group: summarize_sold_group(
                group,
                price_column=sold_cols["price"],
                timestamp_column=sold_cols["timestamp"],
            )
        )
        .reset_index()
        .rename(
            columns={
                sold_cols["year"]: "year",
                sold_cols["make"]: "make",
                sold_cols["model"]: "model",
                sold_cols["part"]: "part",
            }
        )
    )

    return sold_summary


# =========================================================
# Market Summary Prep
# =========================================================
def build_active_summary(
    active_df: pd.DataFrame,
    config: Any,
) -> pd.DataFrame:
    """Prepare active market summary for join."""
    active_cols = config.active_column_map

    active_required_cols = [
        active_cols["year"],
        active_cols["make"],
        active_cols["model"],
        active_cols["part"],
        active_cols["active_count"],
        active_cols["timestamp"],
    ]

    validate_columns(active_df, active_required_cols, "active_df")

    active_summary = (
        active_df[active_required_cols]
        .copy()
        .rename(
            columns={
                active_cols["year"]: "year",
                active_cols["make"]: "make",
                active_cols["model"]: "model",
                active_cols["part"]: "part",
                active_cols["active_count"]: "active_count",
                active_cols["timestamp"]: "timestamp",
            }
        )
    )

    return active_summary


# =========================================================
# Combined Analysis Summary
# =========================================================
def build_analysis_summary(
    sold_df: pd.DataFrame,
    active_df: pd.DataFrame,
    config: Any,
) -> pd.DataFrame:
    """
    Build one combined summary from sold and active listing data.

    What this does:
    1. Builds the sold-side summary
    2. Builds the active-side summary
    3. Joins them together by year / make / model / part
    4. Adds pricing, STR, confidence, and quality flags

    Notes:
    - sold-side price stats come from build_sold_summary()
    - active-side counts come from build_active_summary()
    - settings are used for thresholds where possible
    """
   
    join_cols = ["year", "make", "model", "part"]

    # =========================================================
    # Build sold and active summary tables
    # =========================================================
    sold_summary = build_sold_summary(sold_df, config)
    active_summary = build_active_summary(active_df, config)

    # =========================================================
    # Join sold and active results
    # =========================================================
    analysis_df = sold_summary.merge(
        active_summary,
        on=join_cols,
        how="left",
    )

    # =========================================================
    # Fill core count fields
    # =========================================================
    analysis_df["sold_count"] = analysis_df["sold_count"].fillna(0).astype(int)
    analysis_df["active_count"] = analysis_df["active_count"].fillna(0).astype(int)

    analysis_df["total_count"] = (
        analysis_df["sold_count"] + analysis_df["active_count"]
    )

    # =========================================================
    # Build STR and confidence metrics
    # =========================================================
    analysis_df["str"] = analysis_df.apply(
        lambda row: calculate_str(
            sold_count=int(row["sold_count"]),
            active_count=int(row["active_count"]),
        ),
        axis=1,
    )

    analysis_df["confidence_score"] = analysis_df.apply(
        lambda row: calculate_confidence_score(
            sold_count=int(row["sold_count"]),
            active_count=int(row["active_count"]),
            config=config,
        ),
        axis=1,
    )

    analysis_df["opportunity_score"] = analysis_df.apply(
        lambda row: calculate_opportunity_score(
            median_price=float(row["median_sold_price"])
            if pd.notna(row["median_sold_price"])
            else 0.0,
            str_value=float(row["str"]),
            confidence_score=float(row["confidence_score"]),
        ),
        axis=1,
    ) 

    # =========================================================
    # Clean timestamp fields
    # =========================================================
    analysis_df["sold_timestamp"] = pd.to_datetime(
        analysis_df["sold_timestamp"],
        errors="coerce",
    )

    analysis_df["active_timestamp"] = pd.to_datetime(
        analysis_df["timestamp"],
        errors="coerce",
    )

    analysis_df["time_diff_hours"] = (
        (
            analysis_df["sold_timestamp"] - analysis_df["active_timestamp"]
        ).abs().dt.total_seconds() / 3600
    )

    # =========================================================
    # Add quality flags
    # =========================================================
    analysis_df["stale_snapshot_flag"] = (
        analysis_df["time_diff_hours"] > config.stale_snapshot_hours
    )

    analysis_df["low_sample_flag"] = (
        analysis_df["sold_count"] < config.low_sample_total_threshold
    )

    analysis_df["very_low_sold_flag"] = (
        analysis_df["sold_count"] < config.very_low_sold_threshold
    )

    return analysis_df
