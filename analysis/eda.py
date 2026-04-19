# =========================================================
# eda.py
# Sanity checks for normalized listing data
#
# Purpose:
# Run quick checks on the dataset before scoring.
#
# Notes:
# - Meant for validation and debugging
# - Not a formal test suite
# =========================================================

from typing import Any

import pandas as pd


# =========================================================
# Main Runner
# =========================================================
def run_all_eda_checks(df: pd.DataFrame, config: Any) -> None:
    """Run all standard EDA checks."""
    check_nulls(df, config)
    check_price_distribution(df, config)
    check_low_sample(df, config)


# =========================================================
# Validation Helpers
# =========================================================
def validate_eda_columns(
    df: pd.DataFrame,
    config: Any,
    required_cols: list[str],
) -> None:
    """Make sure expected columns exist before running a check."""
    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        raise ValueError(f"Missing EDA columns: {missing}")


# =========================================================
# Null Checks
# =========================================================
def check_nulls(df: pd.DataFrame, config: Any) -> None:
    """Check null rates for the main analysis columns."""
    required_cols = [
        "price_clean",
        "pass_type", 
        "search_part_std", 
    ]
    validate_eda_columns(df, config, required_cols)

    print("\n[NULL CHECK]")
    print(df[required_cols].isnull().mean())


# =========================================================
# Price Checks
# =========================================================
def check_price_distribution(df: pd.DataFrame, config: Any) -> None:
    """Review basic price distribution."""
    price_col = "price_clean"
    validate_eda_columns(df, config, [price_col])

    print("\n[PRICE DISTRIBUTION]")
    print(
        df[price_col].describe(
            percentiles=[0.25, 0.5, 0.75, 0.9, 0.95]
        )
    )


# =========================================================
# STR Checks
# =========================================================
def check_str_distribution(df: pd.DataFrame, config: Any) -> None:
    """Compute sell-through rate by part category."""
    part_col = "search_part_std"
    listing_type_col = "pass_type"

    validate_eda_columns(df, config, [part_col, listing_type_col])

    working_df = df.copy()
    working_df[listing_type_col] = (
        working_df[listing_type_col]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    grouped = (
        working_df.groupby(part_col)[listing_type_col]
        .value_counts()
        .unstack(fill_value=0)
    )

    grouped["total"] = grouped.sum(axis=1)
    grouped["str"] = grouped.get("sold", 0) / grouped["total"]

    print("\n[STR DISTRIBUTION]")
    print(grouped["str"].describe())


# =========================================================
# Sample Size Checks
# =========================================================
def check_low_sample(
    df: pd.DataFrame,
    config: Any,
    threshold: int = 5,
) -> pd.Series:
    """Flag categories with low total listing volume."""
    part_col = "search_part_std"
    validate_eda_columns(df, config, [part_col])

    counts = df[part_col].value_counts(dropna=False)
    low_sample = counts[counts < threshold]

    print("\n[LOW SAMPLE CATEGORIES]")
    print(low_sample)

    return low_sample


# =========================================================
# Title Spot Checks
# =========================================================
def sample_titles(
    df: pd.DataFrame,
    config: Any,
    n: int = 5,
) -> None:
    """Print a few sample titles for each category."""
    part_col = "search_part_std"
    title_col = "title"

    validate_eda_columns(df, config, [part_col, title_col])

    print("\n[SAMPLE TITLES BY CATEGORY]")

    for category in df[part_col].dropna().unique():
        print(f"\n--- {category} ---")
        print(df[df[part_col] == category][title_col].head(n).tolist())