# =========================================================
# run_hypothesis_from_run_id.py
# Run only hypothesis testing from an existing pipeline run
#
# Purpose:
# Reuse a previously generated analysis summary CSV by run_id
# and avoid rerunning scrape / analysis / ranking.
# =========================================================

from __future__ import annotations

from pathlib import Path

from analysis.hypothesis_test import run_hypothesis_test
from config.config_builder import build_scrape_config


# =========================================================
# User inputs
# =========================================================
RUN_ID = "di3ei3d9-e6a8-491b-96ee-e66206bcddf4"

PART_A = "alternator"
PART_B = "headlight"
METRIC = "str"
ALPHA = 0.05


# =========================================================
# Main
# =========================================================
def main() -> None:
    """
    Load the existing analysis summary CSV for a prior run and
    execute only the paired hypothesis test.
    """
    config = build_scrape_config(mode="csv", input_run_id=RUN_ID)
    csv_path = Path(config.source_analysis_summary_csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Analysis CSV not found: {csv_path}")

    result, paired_df = run_hypothesis_test(
        csv_path=csv_path,
        part_a=PART_A,
        part_b=PART_B,
        metric=METRIC,
        alpha=ALPHA,
    )

    print("\n" + "=" * 60)
    print("HYPOTHESIS TEST RESULT")
    print("=" * 60)
    print(result)

    print("\n" + "=" * 60)
    print("PAIRED DATA PREVIEW")
    print("=" * 60)
    print(paired_df.head(10))

    output_dir = csv_path.parent
    paired_output_path = output_dir / f"hypothesis_pairs_{PART_A}_vs_{PART_B}.csv"
    summary_output_path = output_dir / f"hypothesis_result_{PART_A}_vs_{PART_B}.txt"

    paired_df.to_csv(paired_output_path, index=False)

    with open(summary_output_path, "w", encoding="utf-8") as f:
        f.write(str(result))
        f.write("\n")

    print(f"\nPaired output saved to: {paired_output_path}")
    print(f"Summary output saved to: {summary_output_path}")


if __name__ == "__main__":
    main()