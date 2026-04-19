# =========================================================
# ranking.py
# Generate ranked resale opportunity outputs by vehicle
#
# Purpose:
# Turn analyzed vehicle-part metrics into usable ranked outputs.
# Produces a full ranked dataset and a top-N dataset per vehicle.
#
# Notes:
# - Ranking is done within each vehicle only
# - Higher opportunity score ranks better
# - Secondary sort helps keep results stable on ties
# =========================================================

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.schema import RANKED_OUTPUT_COLUMNS, RANKED_DERIVED_COLUMNS


def build_ranked_outputs(
    analysis_df: pd.DataFrame,
    top_n: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build ranked opportunity outputs by vehicle.

    Parameters
    ----------
    analysis_df : pd.DataFrame
        Final analysis dataset with one row per vehicle-part combination.
    top_n : int, default=10
        Number of top ranked parts to keep per vehicle.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        full_ranked_df:
            All rows ranked within each vehicle.
        top_ranked_df:
            Top N rows per vehicle only.
    """
    df = analysis_df.copy()

    missing_input_cols = [
        col for col in RANKED_OUTPUT_COLUMNS
        if col not in RANKED_DERIVED_COLUMNS and col not in df.columns
    ]
    if missing_input_cols:
        raise ValueError(
            f"build_ranked_outputs missing required input columns: {missing_input_cols}"
        )

    df["vehicle_key"] = (
        df["year"].astype(str).str.strip()
        + " "
        + df["make"].astype(str).str.strip()
        + " "
        + df["model"].astype(str).str.strip()
    )

    df = df.sort_values(
        by=[
            "vehicle_key",
            "opportunity_score",
            "active_count",
            "median_sold_price",
            "part",
        ],
        ascending=[True, False, False, False, True],
    ).reset_index(drop=True)

    df["vehicle_rank"] = df.groupby("vehicle_key").cumcount() + 1

    missing_output_cols = [col for col in RANKED_OUTPUT_COLUMNS if col not in df.columns]
    if missing_output_cols:
        raise ValueError(
            f"build_ranked_outputs missing output columns: {missing_output_cols}"
        )

    full_ranked_df = df[RANKED_OUTPUT_COLUMNS].copy()
    top_ranked_df = full_ranked_df[full_ranked_df["vehicle_rank"] <= top_n].copy()

    return full_ranked_df, top_ranked_df


def save_ranked_outputs(
    full_ranked_df: pd.DataFrame,
    top_ranked_df: pd.DataFrame,
    full_output_path: Path,
    top_output_path: Path,
) -> None:
    """
    Save ranked output datasets to CSV.

    Parameters
    ----------
    full_ranked_df : pd.DataFrame
        Full ranked output for all vehicle-part rows.
    top_ranked_df : pd.DataFrame
        Top-N ranked output per vehicle.
    full_output_path : Path
        Output path for full ranked CSV.
    top_output_path : Path
        Output path for top-N ranked CSV.
    """
    full_output_path.parent.mkdir(parents=True, exist_ok=True)
    top_output_path.parent.mkdir(parents=True, exist_ok=True)

    full_ranked_df.to_csv(full_output_path, index=False)
    top_ranked_df.to_csv(top_output_path, index=False)