# =========================================================
# analyze.py
# Controller for the analysis stage
#
# Purpose:
# Load prepared data, run the analysis layer, write outputs,
# and hand results back to the main pipeline.
# =========================================================
from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from analysis.aggregation import build_analysis_summary
from analysis.hypothesis_test import run_hypothesis_test
from analysis.ranking import build_ranked_outputs, save_ranked_outputs
from config.schema import ANALYSIS_EXPORT_RENAME_MAP, ANALYSIS_OUTPUT_COLUMNS


# =========================================================
# Hypothesis execution
# =========================================================
def run_hypothesis_from_summary(config):
    """
    Run hypothesis testing from an existing analysis summary CSV.

    Purpose:
    Reuse the saved analysis summary output instead of rebuilding the
    full scrape/cleanse/normalize path every time we want to test a
    part-vs-part comparison.

    Outputs:
    - hypothesis result CSV (single-row summary)
    - paired comparison CSV (one row per matched vehicle)
    """
    logger = logging.getLogger(__name__)

    source_path = config.source_analysis_summary_csv_path 

    if not source_path.exists():
        raise FileNotFoundError(
            f"Analysis summary CSV not found: {source_path}"
        )

    result, paired_df = run_hypothesis_test(
        csv_path=source_path,
        part_a=config.hypothesis_part_a,
        part_b=config.hypothesis_part_b,
        metric=config.hypothesis_metric,
        alpha=config.hypothesis_alpha,
        alternative=config.hypothesis_alternative,
        make=config.hypothesis_make,
        model=config.hypothesis_model,
        year_min=config.hypothesis_year_min,
        year_max=config.hypothesis_year_max,
        ci_confidence_level=config.hypothesis_ci_confidence_level,
        ci_bootstrap_iterations=config.hypothesis_ci_bootstrap_iterations,
        random_seed=config.hypothesis_random_seed,
    )

    config.hypothesis_output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    config.hypothesis_pairs_csv_path.parent.mkdir(parents=True, exist_ok=True)

    pd.DataFrame([asdict(result)]).to_csv(
        config.hypothesis_output_csv_path,
        index=False,
    )

    paired_df.to_csv(
        config.hypothesis_pairs_csv_path,
        index=False,
    )

    logger.info(
        "Hypothesis outputs written | result_path=%s | pairs_path=%s | n_pairs=%s",
        config.hypothesis_output_csv_path,
        config.hypothesis_pairs_csv_path,
        result.n_pairs,
    )

    return result, paired_df

# =========================================================
# Run analysis stage
# =========================================================
def run_analysis(
    sold_csv_path: Path,
    active_csv_path: Path,
    output_csv_path: Path,
    config: Any,
) -> dict[str, Any]:
    """
    Run the analysis stage from prepared sold and active CSV files.

    High-level flow:
    1. Load input datasets (sold + active)
    2. Build combined analysis summary (metrics + scoring)
    3. Generate ranked outputs (top parts per vehicle)
    4. Format and export analysis summary
    5. Return results for downstream use
    """
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("Analysis stage start")
    logger.info("=" * 70)

    # ---------------------------------------------------------
    # 1. Load input data
    # ---------------------------------------------------------
    logger.info("Reading input CSVs")
    logger.info("sold_csv=%s", sold_csv_path)
    logger.info("active_csv=%s", active_csv_path)

    sold_df = pd.read_csv(sold_csv_path)
    active_df = pd.read_csv(active_csv_path)

    logger.info(
        "Input loaded | sold_rows=%s | active_rows=%s",
        len(sold_df),
        len(active_df),
    )

    # ---------------------------------------------------------
    # 2. Build analysis summary (core metrics + scoring)
    # ---------------------------------------------------------
    logger.info("Building analysis summary")

    analysis_df = build_analysis_summary(
        sold_df=sold_df,
        active_df=active_df,
        config=config,
    )

    logger.info(
        "Analysis summary built | rows=%s",
        len(analysis_df),
    )

    # ---------------------------------------------------------
    # 3. Format analysis summary for export
    # ---------------------------------------------------------
    logger.info("Formatting analysis summary for export")

    analysis_export_df = analysis_df.rename(columns=ANALYSIS_EXPORT_RENAME_MAP)
    analysis_export_df = analysis_export_df.reindex(columns=ANALYSIS_OUTPUT_COLUMNS)

    # ---------------------------------------------------------
    # 4. Write analysis summary output
    # ---------------------------------------------------------
    logger.info("Writing analysis summary CSV")

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_export_df.to_csv(output_csv_path, index=False)

    logger.info(
        "Analysis summary CSV written | rows=%s | path=%s",
        len(analysis_export_df),
        output_csv_path,
    )

    # ---------------------------------------------------------
    # 5. Generate ranked outputs (final product layer)
    # ---------------------------------------------------------
    logger.info(
        "Generating ranked outputs | top_n=%s",
        config.top_n_parts,
    )

    logger.info("Ranking input columns: %s", sorted(analysis_df.columns.tolist()))
    logger.info("Ranking input preview:\n%s", analysis_df.head())

    full_ranked_df, top_ranked_df = build_ranked_outputs(
        analysis_df=analysis_df,
        top_n=config.top_n_parts,
    )

    save_ranked_outputs(
        full_ranked_df=full_ranked_df,
        top_ranked_df=top_ranked_df,
        full_output_path=config.full_ranked_output_csv_path,
        top_output_path=config.top_10_output_csv_path,
    )

    logger.info(
        "Ranked outputs written | full=%s | top=%s",
        config.full_ranked_output_csv_path,
        config.top_10_output_csv_path,
    )

    # ---------------------------------------------------------
    # 6. Return results for pipeline continuity
    # ---------------------------------------------------------
    return {
        "analysis_df": analysis_export_df,
        "analysis_output_path": output_csv_path,
    }