# =========================================================
# test_output_schemas.py
# Verify output schema contracts for major pipeline stages
#
# Purpose:
# Catch column drift before it breaks downstream logic,
# exports, visuals, or hypothesis testing.
# =========================================================

from __future__ import annotations

import pandas as pd

from analysis.aggregation import build_analysis_summary
from analysis.ranking import build_ranked_outputs


# =========================================================
# Analysis Output Schema
# =========================================================
def test_analysis_output_schema_matches_expected(dummy_config) -> None:
    """
    Verify analysis summary output matches the expected schema contract.
    """
    sold_df = pd.DataFrame(
        [
            {
                "search_year": 2018,
                "search_make_std": "toyota",
                "search_model_std": "camry",
                "search_part_std": "alternator",
                "price_clean": 100.0,
                "scrape_ts": "2026-04-10 10:00:00",
            },
            {
                "search_year": 2018,
                "search_make_std": "toyota",
                "search_model_std": "camry",
                "search_part_std": "alternator",
                "price_clean": 120.0,
                "scrape_ts": "2026-04-11 10:00:00",
            },
        ]
    )

    active_df = pd.DataFrame(
        [
            {
                "search_year": 2018,
                "search_make_std": "toyota",
                "search_model_std": "camry",
                "search_part_std": "alternator",
                "active_listing_count": 4,
                "scrape_ts": "2026-04-11 12:00:00",
            }
        ]
    )

    result = build_analysis_summary(sold_df, active_df, dummy_config)

    expected_columns = [
        "year",
        "make",
        "model",
        "part",
        "sold_count",
        "median_sold_price",
        "mean_sold_price",
        "min_sold_price",
        "max_sold_price",
        "sold_timestamp",
        "active_count",
        "timestamp",
        "total_count",
        "str",
        "confidence_score",
        "opportunity_score",
        "active_timestamp",
        "time_diff_hours",
        "stale_snapshot_flag",
        "low_sample_flag",
        "very_low_sold_flag",
    ]

    assert list(result.columns) == expected_columns


# =========================================================
# Ranking Output Schema
# =========================================================
def test_ranked_output_schema_matches_expected() -> None:
    """
    Verify ranked outputs match the expected schema contract.
    """
    analysis_df = pd.DataFrame(
        [
            {
                "search_year": 2018,
                "search_make": "Toyota",
                "search_model": "Camry",
                "part_name": "alternator",
                "median_price": 120.0,
                "sell_through_rate": 0.60,
                "confidence_factor": 0.80,
                "opportunity_score": 57.6,
            },
            {
                "search_year": 2018,
                "search_make": "Toyota",
                "search_model": "Camry",
                "part_name": "headlight",
                "median_price": 150.0,
                "sell_through_rate": 0.40,
                "confidence_factor": 0.75,
                "opportunity_score": 45.0,
            },
        ]
    )

    full_df, top_df = build_ranked_outputs(analysis_df, top_n=1)

    assert "vehicle_key" in full_df.columns
    assert "rank_within_vehicle" in full_df.columns
    assert "opportunity_score" in full_df.columns
    assert list(full_df.columns) == list(top_df.columns)