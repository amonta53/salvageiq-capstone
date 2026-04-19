# =========================================================
# orchestrator.py
# Pipeline flow control for SalvageIQ
#
# Purpose:
# Run pipeline stages in the correct order based on config.
#
# Notes:
# - This is the traffic cop
# - Stage logic stays in the stage modules
# - Keep this file focused on flow, not transformation rules
# =========================================================

from __future__ import annotations

import logging
import pandas as pd
from dataclasses import replace

from analysis.analyze import run_analysis
from config.scrape_config import ScrapeConfig
from scrape.runner import run_scrape
from utils.io_utils import reset_output_file
from utils.logging_utils import setup_logging
from visualization.visuals import run_visuals
from wrangle.cleanse import run_cleansing
from wrangle.normalize import run_normalization


# =========================================================
# Setup helpers
# =========================================================

def initialize_pipeline(config: ScrapeConfig) -> logging.Logger:
    """
    Start logging and write the pipeline header.

    Keep this separate so run_pipeline stays readable.
    """
    setup_logging(config.logs_dir, config.run_id)
    logger = logging.getLogger(__name__)

    if not logger.handlers and not logging.getLogger().handlers:
        raise RuntimeError("Logging setup failed. No handlers were attached.")

    logger.info("=" * 70)
    logger.info("Pipeline started | run_id=%s | mode=%s| input_run_id=%s", 
                config.run_id, config.mode, config.input_run_id)
    logger.info("=" * 70)

    return logger


def reset_pipeline_outputs(config: ScrapeConfig, logger: logging.Logger) -> None:
    """
    Clear prior run outputs when reset flag is enabled.
    """
    if not config.reset_outputs_on_run:
        # For hypothesis testing, we want to keep most files, but still reset the hypothesis outputs.
        if config.run_hypothesis_test:
            reset_output_file(config.hypothesis_output_csv_path)
            reset_output_file(config.hypothesis_pairs_csv_path)
        return

    logger.info("Reset flag is on. Clearing old output files.")

    paths_to_reset = [
        config.raw_csv_path,
        config.market_summary_csv_path,
        config.cleansed_csv_path,
        config.normalized_csv_path,
        config.eda_summary_csv_path,
        config.checkpoint_path,
        config.analysis_summary_csv_path,
        config.full_ranked_output_csv_path,
        config.top_10_output_csv_path,
        config.hypothesis_output_csv_path,
        config.hypothesis_pairs_csv_path,
    ]

    for path in paths_to_reset:
        reset_output_file(path)


def build_stage_configs(config: ScrapeConfig) -> tuple[ScrapeConfig, ScrapeConfig]:
    """
    Build config variants for sold and active scrape passes.
    """
    sold_config = replace(config, search_scope="sold")
    all_config = replace(config, search_scope="all")
    return sold_config, all_config


# =========================================================
# Stage wrappers
# =========================================================

def run_sold_scrape_stage(config: ScrapeConfig, logger: logging.Logger) -> dict:
    """
    Run sold listings scrape.
    """
    logger.info("Stage start | sold scrape")
    result = run_scrape(config)
    logger.info(
        "Stage complete | sold scrape | rows_collected=%s",
        result.get("total_rows", 0),
    )
    return result


def run_active_scrape_stage(config: ScrapeConfig, logger: logging.Logger) -> dict:
    """
    Run active listings / market snapshot scrape.
    """
    logger.info("Stage start | active scrape")
    result = run_scrape(config)
    logger.info(
        "Stage complete | active scrape | rows_collected=%s",
        result.get("total_rows", 0),
    )
    return result


def run_cleansing_stage(config: ScrapeConfig, logger: logging.Logger):
    """
    Clean raw sold listing data.
    """
    logger.info("Stage start | cleansing")
    cleansed_df = run_cleansing(
        config.raw_csv_path,
        config.cleansed_csv_path,
    )
    logger.info(
        "Stage complete | cleansing | rows_out=%s",
        len(cleansed_df),
    )
    return cleansed_df


def run_normalization_stage(config: ScrapeConfig, logger: logging.Logger):
    """
    Normalize cleansed sold listing data and remove duplicates.
    """
    logger.info("Stage start | normalization")
    normalized_df, dedup_stats = run_normalization(
        config.cleansed_csv_path,
        config.normalized_csv_path,
    )
    logger.info(
        "Stage complete | normalization | rows_out=%s | duplicates_removed=%s",
        len(normalized_df),
        dedup_stats.get("removed_count", 0),
    )
    return normalized_df, dedup_stats


def run_analysis_stage(config: ScrapeConfig, logger: logging.Logger):
    """
    Build analysis summary from normalized sold data and market snapshot.
    """
    logger.info("Stage start | analysis summary")

    analysis_result = run_analysis(
        sold_csv_path=config.normalized_csv_path,
        active_csv_path=config.market_summary_csv_path,
        output_csv_path=config.analysis_summary_csv_path,
        config=config,
    )

    analysis_df = analysis_result["analysis_df"]

    logger.info(
        "Stage complete | analysis summary | rows_out=%s",
        len(analysis_df),
    )

    return analysis_result

def run_hypothesis_stage(config: ScrapeConfig, logger: logging.Logger):
    """
    Run hypothesis testing from the saved analysis summary CSV.
    """
    logger.info("Stage start | hypothesis")

    from analysis.analyze import run_hypothesis_from_summary

    result, paired_df = run_hypothesis_from_summary(config)

    logger.info(
        "Stage complete | hypothesis | n_pairs=%s | reject_null=%s",
        getattr(result, "n_pairs", "unknown"),
        getattr(result, "reject_null", "unknown"),
    )

    return result, paired_df

def run_visuals_stage(config: ScrapeConfig, logger: logging.Logger) -> dict:
    """
    Run the visuals stage using saved analysis, ranking, and hypothesis outputs.

    Notes:
    - This stage is downstream of hypothesis in the current pipeline flow
    - A chart depends on hypothesis pair output
    """
    logger.info("Stage start | visuals")

    result = run_visuals(
        analysis_summary_path=config.source_analysis_summary_csv_path,
        ranked_output_path=config.source_full_ranked_output_csv_path,
        hypothesis_pairs_path=config.source_hypothesis_pairs_csv_path,
        str_chart_path=config.str_by_part_png_path,
        price_vs_str_path=config.price_vs_str_png_path,
        opportunity_chart_path=config.opportunity_score_by_part_png_path,
        diff_chart_path=config.hypothesis_diff_distribution_png_path,
    )

    logger.info("Stage complete | visuals | output_dir=%s", config.visuals_dir)
    return result

# =========================================================
# Wrap-up
# =========================================================

def log_pipeline_complete(
    config: ScrapeConfig,
    logger: logging.Logger,
    normalized_rows: int,
    summary_rows: int,
) -> None:
    """
    Write final pipeline summary logs.
    """
    logger.info("=" * 70)
    logger.info(
        "Pipeline complete | run_id=%s | normalized_rows=%s | summary_rows=%s | mode=%s | status=success",
        config.run_id,
        normalized_rows,
        summary_rows,
        config.mode,
    )
    logger.info("=" * 70)


# =========================================================
# Main orchestrator
# =========================================================

def run_pipeline(config: ScrapeConfig) -> None:
    """
    Run the end-to-end SalvageIQ pipeline for one configured execution.

    Purpose:
    Coordinate pipeline setup, stage execution order, flag-driven routing,
    and final completion logging for a single run.

    High-level flow:
    1. Initialize pipeline logging and run-level setup
    2. Reset outputs only where configured to do so
    3. Either:
       - reuse an existing analysis summary CSV, or
       - execute the full scrape -> cleanse -> normalize -> analysis flow
    4. Optionally run hypothesis testing
    5. Optionally generate visuals from saved analytical outputs
    6. Log final pipeline completion summary

    Flag-driven behavior:
    - config.analysis_use_existing_summary:
        Skips scrape, cleansing, normalization, and analysis rebuild.
        Instead, reads the existing analysis summary CSV from disk and
        uses it as the source dataset for downstream stages.

    - config.run_hypothesis_test:
        Runs the hypothesis stage after analysis data is available.
        Visual generation is also gated behind this flag because at least
        one visual depends on hypothesis output data.

    Notes:
    - This function is orchestration only. It does not perform the stage
      logic itself. Each stage is delegated to a dedicated helper.
    - Analysis summary availability is the key branch point. Once that
      dataset exists, downstream hypothesis testing and visuals can run
      without rebuilding the upstream scrape pipeline.
    - normalized_rows is reported as 0 when existing analysis output is
      reused, because normalization did not run in the current execution.
    - summary_rows always reflects the row count of the analysis summary
      DataFrame used for the current run.

    Raises:
        FileNotFoundError:
            If config.analysis_use_existing_summary is True but the
            expected analysis summary CSV does not exist.
    """
    logger = initialize_pipeline(config)
    reset_pipeline_outputs(config, logger)

    if config.analysis_use_existing_summary:
        source_path = config.source_analysis_summary_csv_path

        logger.info(
            "Analysis summary rebuild skipped | using existing CSV | path=%s",
            source_path,
        )
        if not source_path.exists():
            raise FileNotFoundError(
                f"Expected analysis summary CSV not found: {source_path}"
            )
        else:
            analysis_df = pd.read_csv(source_path)
            normalized_rows = 0
    else:
        sold_config, all_config = build_stage_configs(config)

        run_sold_scrape_stage(sold_config, logger)
        run_active_scrape_stage(all_config, logger)

        run_cleansing_stage(sold_config, logger)
        normalized_df, _ = run_normalization_stage(config, logger)
        analysis_result = run_analysis_stage(config, logger)

        analysis_df = analysis_result["analysis_df"]
        normalized_rows = len(normalized_df)

    if config.run_hypothesis_test:
        run_hypothesis_stage(config, logger)
        run_visuals_stage(config, logger)

    log_pipeline_complete(
        config=config,
        logger=logger,
        normalized_rows=normalized_rows,
        summary_rows=len(analysis_df),
    )
    