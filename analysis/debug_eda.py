# =========================================================
# debug_eda.py
# Quick runner for sanity-checking normalized data
#
# Purpose:
# Run EDA checks and export a category summary without
# rerunning the full pipeline.
# While running in eda mode, trying to answer the big questions early:
# - Do we have enough sold and active records to compare?
# - Do the prices make sense, or are outliers driving the story?
# - Are part categories populated cleanly enough to trust?
# - Does the exported summary contain enough signal to review
#   what actually appears to sell?
#
# Usage:
# python -m analysis.debug_eda
#
# Notes:
# - Uses config for all paths
# - Assumes normalized data already exists
# =========================================================

from pathlib import Path
from typing import Any

import pandas as pd

from analysis.eda import run_all_eda_checks
from config.config_builder import build_scrape_config


# =========================================================
# Data Loading
# =========================================================
def load_normalized_data(config: Any) -> pd.DataFrame:
    """Load normalized dataset from config path."""
    input_path = Path(config.normalized_csv_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Missing normalized data: {input_path}")

    print(f"\nLoading normalized data from: {input_path}")
    return pd.read_csv(input_path)


# =========================================================
# Summary Export
# =========================================================
def export_grouped_summary(df: pd.DataFrame, config: Any) -> None:
    """
    Build and export part-level summary:
    sold/active counts, STR, price stats, and flags.
    """
    output_path = Path(config.eda_summary_csv_path)

    working_df = df.copy()
    working_df["pass_type"] = (
        working_df["pass_type"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    sold_df = working_df[working_df["pass_type"] == "sold"]
    active_df = working_df[working_df["pass_type"] == "active"]

    sold_counts = sold_df.groupby("search_part_std").size().rename("sold_count")
    active_counts = active_df.groupby("search_part_std").size().rename("active_count")

    sold_price_stats = sold_df.groupby("search_part_std")["price_clean"].agg(
        median_sold_price="median",
        mean_sold_price="mean",
        min_sold_price="min",
        max_sold_price="max",
    )

    summary = pd.concat(
        [sold_counts, active_counts, sold_price_stats],
        axis=1,
    ).fillna(0)

    summary["sold_count"] = summary["sold_count"].astype(int)
    summary["active_count"] = summary["active_count"].astype(int)
    summary["total_count"] = summary["sold_count"] + summary["active_count"]

    summary["sell_through_rate"] = (
        summary["sold_count"] / summary["total_count"]
    ).fillna(0)

    summary["low_sample_flag"] = summary["total_count"] < 5
    summary["very_low_sold_flag"] = summary["sold_count"] < 3

    summary = summary.sort_values(
        by=["sell_through_rate", "sold_count", "median_sold_price"],
        ascending=[False, False, False],
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_path, index=True)

    print(f"\nExported EDA summary to: {output_path}")


# =========================================================
# Main Runner
# =========================================================
def main() -> None:
    """Run EDA checks and export summary for eda mode."""
    config = build_scrape_config(mode="eda")

    df = load_normalized_data(config)

    # Early sanity check before running full EDA 
    print("\nLoaded columns:")
    print(df.columns.tolist()) 

    print("\n=== RUNNING EDA CHECKS ===")
    run_all_eda_checks(df, config)

    print("\n=== EXPORTING SUMMARY ===")
    export_grouped_summary(df, config)

    print("\n=== DONE ===")


if __name__ == "__main__":
    main()