# =========================================================
# test_orchestrator_flags.py
# Verify pipeline routing based on config flags
#
# Purpose:
# Ensure the orchestrator runs or skips stages correctly
# based on analysis reuse and hypothesis flags.
#
# Notes:
# - This is orchestration testing only
# - All stage functions are mocked
# - Focus is on control flow, not data correctness
# =========================================================

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from pipeline.orchestrator import run_pipeline


# =========================================================
# Helpers
# =========================================================
def _minimal_config(dummy_config):
    """Ensure required flags exist for tests."""
    dummy_config.analysis_use_existing_summary = False
    dummy_config.run_hypothesis_test = False
    dummy_config.source_analysis_summary_csv_path = None
    return dummy_config


# =========================================================
# Full pipeline (no reuse)
# =========================================================
def test_full_pipeline_runs_all_core_stages(dummy_config) -> None:
    """
    Verify full pipeline runs all upstream stages when not reusing analysis.

    Why this matters:
    This is the main execution path. If any stage is skipped, the pipeline
    silently produces incomplete outputs.
    """
    config = _minimal_config(dummy_config)

    with (
        patch("pipeline.orchestrator.initialize_pipeline"),
        patch("pipeline.orchestrator.reset_pipeline_outputs"),
        patch("pipeline.orchestrator.build_stage_configs",
              return_value=(config, config)),
        patch("pipeline.orchestrator.run_sold_scrape_stage") as sold,
        patch("pipeline.orchestrator.run_active_scrape_stage") as active,
        patch("pipeline.orchestrator.run_cleansing_stage") as cleanse,
        patch("pipeline.orchestrator.run_normalization_stage",
              return_value=(pd.DataFrame(), {})) as normalize,
        patch("pipeline.orchestrator.run_analysis_stage",
              return_value={"analysis_df": pd.DataFrame([{"x": 1}])}) as analyze,
        patch("pipeline.orchestrator.log_pipeline_complete"),
    ):
        run_pipeline(config)

    sold.assert_called_once()
    active.assert_called_once()
    cleanse.assert_called_once()
    normalize.assert_called_once()
    analyze.assert_called_once()


# =========================================================
# CSV reuse path
# =========================================================
def test_reuse_analysis_skips_upstream_stages(dummy_config, tmp_path) -> None:
    """
    Verify reuse mode skips scrape, cleanse, normalize, and analysis rebuild.

    Why this matters:
    This protects long-running scrape output from being overwritten.
    """
    config = _minimal_config(dummy_config)
    config.analysis_use_existing_summary = True

    fake_csv = tmp_path / "analysis.csv"
    pd.DataFrame([{"x": 1}]).to_csv(fake_csv, index=False)
    config.source_analysis_summary_csv_path = fake_csv

    with (
        patch("pipeline.orchestrator.initialize_pipeline"),
        patch("pipeline.orchestrator.reset_pipeline_outputs"),
        patch("pipeline.orchestrator.run_sold_scrape_stage") as sold,
        patch("pipeline.orchestrator.run_active_scrape_stage") as active,
        patch("pipeline.orchestrator.run_cleansing_stage") as cleanse,
        patch("pipeline.orchestrator.run_normalization_stage") as normalize,
        patch("pipeline.orchestrator.run_analysis_stage") as analyze,
        patch("pipeline.orchestrator.log_pipeline_complete"),
    ):
        run_pipeline(config)

    sold.assert_not_called()
    active.assert_not_called()
    cleanse.assert_not_called()
    normalize.assert_not_called()
    analyze.assert_not_called()


# =========================================================
# Hypothesis + visuals
# =========================================================
def test_hypothesis_and_visuals_run_when_flag_enabled(dummy_config) -> None:
    """
    Verify hypothesis and visuals run when enabled.

    Why this matters:
    These are optional downstream stages and must not run unless requested.
    """
    config = _minimal_config(dummy_config)
    config.run_hypothesis_test = True

    with (
        patch("pipeline.orchestrator.initialize_pipeline"),
        patch("pipeline.orchestrator.reset_pipeline_outputs"),
        patch("pipeline.orchestrator.build_stage_configs",
              return_value=(config, config)),
        patch("pipeline.orchestrator.run_sold_scrape_stage"),
        patch("pipeline.orchestrator.run_active_scrape_stage"),
        patch("pipeline.orchestrator.run_cleansing_stage"),
        patch("pipeline.orchestrator.run_normalization_stage",
              return_value=(pd.DataFrame(), {})),
        patch("pipeline.orchestrator.run_analysis_stage",
              return_value={"analysis_df": pd.DataFrame([{"x": 1}])}),
        patch("pipeline.orchestrator.run_hypothesis_stage") as hypo,
        patch("pipeline.orchestrator.run_visuals_stage") as visuals,
        patch("pipeline.orchestrator.log_pipeline_complete"),
    ):
        run_pipeline(config)

    hypo.assert_called_once()
    visuals.assert_called_once()


# =========================================================
# Missing CSV error
# =========================================================
def test_reuse_missing_csv_raises_error(dummy_config, tmp_path) -> None:
    """
    Verify reuse mode fails when expected CSV does not exist.

    Why this matters:
    Silent fallback here would produce incorrect downstream results.
    """
    config = _minimal_config(dummy_config)
    config.analysis_use_existing_summary = True
    config.source_analysis_summary_csv_path = tmp_path / "missing.csv"

    with (
        patch("pipeline.orchestrator.initialize_pipeline"),
        patch("pipeline.orchestrator.reset_pipeline_outputs"),
    ):
        with pytest.raises(FileNotFoundError):
            run_pipeline(config)