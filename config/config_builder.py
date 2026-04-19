# =========================================================
# config_builder.py
# Build runtime ScrapeConfig objects by named mode
#
# Purpose:
# Keep run-mode overrides out of main.py so startup stays clean.
# This file should only decide which knobs change by mode.
#
# Notes:
# - Full mode uses ScrapeConfig defaults unless overridden
# - Mode overrides should stay obvious and boring
# - Do not bury business logic in this file
# =========================================================

from __future__ import annotations

from config.scrape_config import ScrapeConfig


# =========================================================
# Build scrape config by mode
# =========================================================
def build_scrape_config(mode: str = "full", input_run_id: str | None = None) -> ScrapeConfig:
    """
    Build a runtime ScrapeConfig for the requested mode.

    Why:
    Different run modes are useful for different jobs:
    - full: everything *** Takes 10 hours to run ***
    - 1fullhypo: one vehicle, full part list, one year 
    - mini/test: quick pipeline checks
    - eda: quick runs with EDA enabled
    - csv: skip scrape/cleanse/normalize and reuse saved analysis summary CSV

    Notes:
    - The mode string is normalized before comparison
    - Any field not overridden here falls back to ScrapeConfig defaults
    """
    mode = mode.lower().strip()

    # -----------------------------------------------------
    # Tiny smoke test mode
    # One year, one part, one vehicle, one page
    # Good for fast validation when the pipeline acts dumb
    # -----------------------------------------------------
    if mode == "test":
        return ScrapeConfig(
            mode="test",
            start_year=2019,
            end_year=2019,
            parts=["alternator"],
            supported_vehicles=[
                {
                    "year_range": (2012, 2020),
                    "make": "Toyota",
                    "model": "Camry",
                }
            ],
            max_pages_per_search=1,
        )

    # -----------------------------------------------------
    # One vehicle, full part list, one year
    # Good for heavier hypothesis or full-output validation
    # without setting the whole world on fire
    # -- 1 year, 1 vehicle, all parts, full output
    # -----------------------------------------------------
    if mode == "1fullhypo":
        return ScrapeConfig(
            mode="1fullhypo",
            start_year=2020,
            end_year=2020,
            supported_vehicles=[
                {
                    "year_range": (2012, 2020),
                    "make": "Ram",
                    "model": "1500",
                }
            ],
            max_pages_per_search=2,
        )

    # -----------------------------------------------------
    # Small pipeline run
    # Good for checking scrape -> cleanse -> normalize ->
    # analysis -> ranking without waiting forever
    # -- 2 years, 1 vehicle, 2 (hypothesis) parts, full output
    # -----------------------------------------------------
    if mode == "mini":
        return ScrapeConfig(
            mode="mini",
            start_year=2018,
            end_year=2019,
            parts=["alternator", "headlight"],
            supported_vehicles=[
                {
                    "year_range": (2012, 2020),
                    "make": "Toyota",
                    "model": "Camry",
                }
            ],
            max_pages_per_search=2,
            run_hypothesis_test=True,
        )

    # -----------------------------------------------------
    # EDA mode
    # Same idea as a small focused run, but with EDA enabled
    # -- 1 year, 1 vehicle, all parts, EDA enabled
    # -----------------------------------------------------
    if mode == "eda":
        return ScrapeConfig(
            mode="eda",
            start_year=2019,
            end_year=2019,
            run_eda=True,
            supported_vehicles=[
                {
                    "year_range": (2012, 2020),
                    "make": "Toyota",
                    "model": "Camry",
                }
            ],
            max_pages_per_search=2,
        )

    # -----------------------------------------------------
    # CSV reuse mode
    # Skip rebuild work and use saved analysis summary output
    # This is useful when scrape time is the enemy
    # -- full analysis summary reuse, with hypothesis testing enabled
    # -- All years, All Vehicles, all parts, but reuse existing analysis summary CSV
    # -----------------------------------------------------
    if mode == "csv":
        return ScrapeConfig(
            mode="csv",
            input_run_id=input_run_id,
            analysis_use_existing_summary=True,
            run_hypothesis_test=True,
            reset_outputs_on_run=False,
        )

    # -----------------------------------------------------
    # Default to full run
    # -----------------------------------------------------
    return ScrapeConfig(
        mode="full",
        input_run_id=input_run_id,
    )
