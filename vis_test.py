# =========================================================
# run_visuals_from_existing_csv.py
# Rebuild visualization outputs from an existing pipeline run
#
# Purpose:
# Use already-generated CSV outputs from a prior run_id
# so visuals can be rebuilt without re-running scrape,
# normalization, analysis, or ranking.
#
# Notes:
# - This is a safe rebuild pattern
# - Replace the placeholder run_id before running
# - Assumes the source CSV files already exist for that run
# =========================================================

from pathlib import Path

from config.config_builder import build_scrape_config
from visualization.visuals import run_visuals


# =========================================================
# Configuration setup
# =========================================================
# Build config in CSV mode so the script points at existing
# pipeline outputs instead of trying to scrape fresh data.
config = build_scrape_config(mode="csv")

# Set the existing run_id you want to use as the source.
# This should match a run folder that already contains
# the analysis, ranking, and hypothesis CSV outputs.
config.input_run_id = "PUT_EXISTING_RUN_ID_HERE"


# =========================================================
# Optional validation
# =========================================================
# Light guardrail so you do not accidentally run this with
# the placeholder still in place.
if config.input_run_id == "PUT_EXISTING_RUN_ID_HERE":
    raise ValueError(
        "Replace 'PUT_EXISTING_RUN_ID_HERE' with a real existing run_id "
        "before running this script."
    )


# =========================================================
# Rebuild visuals from existing CSV outputs
# =========================================================
# This only regenerates charts from stored CSV data.
# It does not re-run the full pipeline.
run_visuals(
    analysis_summary_path=config.source_analysis_summary_csv_path,
    ranked_output_path=config.source_full_ranked_output_csv_path,
    hypothesis_pairs_path=config.source_hypothesis_pairs_csv_path,
    str_chart_path=config.str_by_part_png_path,
    price_vs_str_path=config.price_vs_str_png_path,
    opportunity_chart_path=config.opportunity_score_by_part_png_path,
    diff_chart_path=config.hypothesis_diff_distribution_png_path,
)