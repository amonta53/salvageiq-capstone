# =========================================================
# test_ranking.py
# Unit tests for ranked resale opportunity outputs
#
# Purpose:
# Verify that ranking.py correctly sorts parts by
# opportunity score within each vehicle, assigns ranks,
# applies top-N filtering, and fails cleanly when
# required input columns are missing.
#
# Notes:
# - These are unit tests for ranking logic only
# - They do not test controller flow or file writing
# - Test data is intentionally small and deterministic
# =========================================================

from __future__ import annotations

import pandas as pd
import pytest

from analysis.ranking import build_ranked_outputs


# =========================================================
# Test helpers
# =========================================================
def make_analysis_input_df() -> pd.DataFrame:
    """
    Build a small, controlled analysis dataset for ranking tests.

    Returns
    -------
    pd.DataFrame
        One row per vehicle-part combination with the fields
        required by build_ranked_outputs().
    """
    return pd.DataFrame(
        [
            # -------------------------------------------------
            # Vehicle 1: 2018 Toyota Camry
            # -------------------------------------------------
            {
                "search_year": 2018,
                "search_make": "Toyota",
                "search_model": "Camry",
                "part_name": "alternator",
                "median_price": 120.0,
                "sell_through_rate": 0.60,
                "listing_count": 20,
                "sold_count": 12,
                "active_count": 8,
                "confidence_factor": 0.90,
                "opportunity_score": 64.80,
            },
            {
                "search_year": 2018,
                "search_make": "Toyota",
                "search_model": "Camry",
                "part_name": "radio",
                "median_price": 100.0,
                "sell_through_rate": 0.40,
                "listing_count": 15,
                "sold_count": 6,
                "active_count": 9,
                "confidence_factor": 0.80,
                "opportunity_score": 32.00,
            },
            {
                "search_year": 2018,
                "search_make": "Toyota",
                "search_model": "Camry",
                "part_name": "headlight",
                "median_price": 90.0,
                "sell_through_rate": 0.50,
                "listing_count": 18,
                "sold_count": 9,
                "active_count": 9,
                "confidence_factor": 0.85,
                "opportunity_score": 38.25,
            },
            # -------------------------------------------------
            # Vehicle 2: 2017 Honda Accord
            # -------------------------------------------------
            {
                "search_year": 2017,
                "search_make": "Honda",
                "search_model": "Accord",
                "part_name": "starter",
                "median_price": 110.0,
                "sell_through_rate": 0.55,
                "listing_count": 14,
                "sold_count": 8,
                "active_count": 6,
                "confidence_factor": 0.88,
                "opportunity_score": 53.24,
            },
            {
                "search_year": 2017,
                "search_make": "Honda",
                "search_model": "Accord",
                "part_name": "mirror",
                "median_price": 75.0,
                "sell_through_rate": 0.45,
                "listing_count": 11,
                "sold_count": 5,
                "active_count": 6,
                "confidence_factor": 0.82,
                "opportunity_score": 27.68,
            },
        ]
    )


# =========================================================
# Happy path
# =========================================================
def test_build_ranked_outputs_smoke() -> None:
    """
    Verify that ranked outputs are built successfully from a
    valid analysis dataframe and include expected columns.
    """
    analysis_df = make_analysis_input_df()

    full_ranked_df, top_ranked_df = build_ranked_outputs(
        analysis_df=analysis_df,
        top_n=10,
    )

    assert not full_ranked_df.empty
    assert not top_ranked_df.empty

    assert "vehicle_key" in full_ranked_df.columns
    assert "vehicle_rank" in full_ranked_df.columns
    assert "opportunity_score" in full_ranked_df.columns


# =========================================================
# Ranking order by vehicle
# =========================================================
def test_build_ranked_outputs_sorts_within_vehicle() -> None:
    """
    Verify that parts are ranked in descending opportunity
    score order within each vehicle.
    """
    analysis_df = make_analysis_input_df()

    full_ranked_df, _ = build_ranked_outputs(
        analysis_df=analysis_df,
        top_n=10,
    )

    camry_df = full_ranked_df[
        full_ranked_df["vehicle_key"] == "2018 Toyota Camry"
    ].sort_values("vehicle_rank")

    assert list(camry_df["part_name"]) == [
        "alternator",
        "headlight",
        "radio",
    ]
    assert list(camry_df["vehicle_rank"]) == [1, 2, 3]


# =========================================================
# Rank reset by vehicle
# =========================================================
def test_build_ranked_outputs_resets_rank_per_vehicle() -> None:
    """
    Verify that rank numbering restarts at 1 for each vehicle.
    """
    analysis_df = make_analysis_input_df()

    full_ranked_df, _ = build_ranked_outputs(
        analysis_df=analysis_df,
        top_n=10,
    )

    accord_df = full_ranked_df[
        full_ranked_df["vehicle_key"] == "2017 Honda Accord"
    ].sort_values("vehicle_rank")

    assert list(accord_df["vehicle_rank"]) == [1, 2]
    assert accord_df.iloc[0]["part_name"] == "starter"
    assert accord_df.iloc[0]["vehicle_rank"] == 1


# =========================================================
# Top-N filtering
# =========================================================
def test_build_ranked_outputs_applies_top_n_per_vehicle() -> None:
    """
    Verify that top_n keeps only the highest-ranked rows
    for each vehicle.
    """
    analysis_df = make_analysis_input_df()

    full_ranked_df, top_ranked_df = build_ranked_outputs(
        analysis_df=analysis_df,
        top_n=1,
    )

    assert len(full_ranked_df) == 5
    assert len(top_ranked_df) == 2

    assert set(top_ranked_df["vehicle_rank"]) == {1}
    assert set(top_ranked_df["part_name"]) == {"alternator", "starter"}


# =========================================================
# Tie-break behavior
# =========================================================
def test_build_ranked_outputs_uses_tie_break_rules() -> None:
    """
    Verify that ties on opportunity_score are broken by:
    1. higher listing_count
    2. higher median_price
    3. part_name ascending
    """
    analysis_df = pd.DataFrame(
        [
            {
                "search_year": 2019,
                "search_make": "Ford",
                "search_model": "Fusion",
                "part_name": "b_part",
                "median_price": 100.0,
                "sell_through_rate": 0.50,
                "listing_count": 10,
                "sold_count": 5,
                "active_count": 5,
                "confidence_factor": 0.80,
                "opportunity_score": 40.0,
            },
            {
                "search_year": 2019,
                "search_make": "Ford",
                "search_model": "Fusion",
                "part_name": "a_part",
                "median_price": 100.0,
                "sell_through_rate": 0.50,
                "listing_count": 10,
                "sold_count": 5,
                "active_count": 5,
                "confidence_factor": 0.80,
                "opportunity_score": 40.0,
            },
            {
                "search_year": 2019,
                "search_make": "Ford",
                "search_model": "Fusion",
                "part_name": "c_part",
                "median_price": 110.0,
                "sell_through_rate": 0.50,
                "listing_count": 10,
                "sold_count": 5,
                "active_count": 5,
                "confidence_factor": 0.80,
                "opportunity_score": 40.0,
            },
            {
                "search_year": 2019,
                "search_make": "Ford",
                "search_model": "Fusion",
                "part_name": "d_part",
                "median_price": 90.0,
                "sell_through_rate": 0.50,
                "listing_count": 12,
                "sold_count": 6,
                "active_count": 6,
                "confidence_factor": 0.80,
                "opportunity_score": 40.0,
            },
        ]
    )

    full_ranked_df, _ = build_ranked_outputs(
        analysis_df=analysis_df,
        top_n=10,
    )

    fusion_df = full_ranked_df.sort_values("vehicle_rank")

    assert list(fusion_df["part_name"]) == [
        "d_part",  # highest listing_count
        "c_part",  # same listing_count, higher median_price
        "a_part",  # same listing_count + price, alphabetical
        "b_part",
    ]
    assert list(fusion_df["vehicle_rank"]) == [1, 2, 3, 4]


# =========================================================
# Missing input columns
# =========================================================
def test_build_ranked_outputs_raises_on_missing_required_columns() -> None:
    """
    Verify that the function fails cleanly when required
    input columns are missing.
    """
    analysis_df = make_analysis_input_df().drop(columns=["opportunity_score"])

    with pytest.raises(ValueError) as exc_info:
        build_ranked_outputs(
            analysis_df=analysis_df,
            top_n=10,
        )

    assert "missing required input columns" in str(exc_info.value).lower()
    assert "opportunity_score" in str(exc_info.value)


# =========================================================
# Top-N greater than available rows
#  -- It should not crash and should return all rows without filtering
# =========================================================
def test_top_n_greater_than_rows() -> None:
    df = make_analysis_input_df()

    _, top_df = build_ranked_outputs(df, top_n=10)

    # should not crash or drop rows incorrectly
    assert len(top_df) == len(df)