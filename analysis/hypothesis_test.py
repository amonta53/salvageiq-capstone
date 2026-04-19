# =========================================================
# hypothesis_test.py
# Per-vehicle paired hypothesis test
#
# Purpose:
# Compare two part categories across the same vehicles using
# metrics from the analysis summary CSV.
#
# Null hypothesis:
#   H₀: metric(part_a) ≤ metric(part_b)
#   H₁: metric(part_a) > metric(part_b)
#
# Notes:
# - Reads real pipeline output (analysis summary CSV)
# - Builds paired comparisons by vehicle key (year|make|model)
# - Non-parametric only: permutation test + Wilcoxon signed-rank
# - No normality assumption, no paired t-test
# =========================================================


# =========================================================
# Imports
# =========================================================

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from itertools import product
from scipy.stats import wilcoxon


# =========================================================
# Hypothesis test defaults
# =========================================================
HYPOTHESIS_CI_CONFIDENCE_LEVEL = 0.95
HYPOTHESIS_CI_BOOTSTRAP_ITERATIONS = 10_000
HYPOTHESIS_RANDOM_SEED = 42
HYPOTHESIS_ALPHA = 0.05
HYPOTHESIS_METRIC = "str"   
HYPOTHESIS_ALTERNATIVE = "greater"
HYPOTHESIS_PART_A = "alternator"
HYPOTHESIS_PART_B = "headlight"
HYPOTHESIS_MAKE = None
HYPOTHESIS_MODEL = None 
HYPOTHESIS_YEAR_MIN = 2012  
HYPOTHESIS_YEAR_MAX = 2020
HYPOTHESIS_PERMUTATION_EXACT_THRESHOLD = 15
HYPOTHESIS_PERMUTATION_ITERATIONS = 100_000


# =========================================================
# Result Dataclasses
# =========================================================

@dataclass
class PermutationTestResult:
    test_name: str
    alternative: str
    n_pairs: int
    observed_statistic: float
    p_value: float
    permutation_count: int
    method: str


@dataclass
class WilcoxonTestResult:
    test_name: str
    alternative: str
    n_pairs: int
    statistic: float | None
    p_value: float | None


@dataclass
class MeanDiffCIResult:
    method: str
    confidence_level: float
    n_pairs: int
    mean_diff: float
    ci_low: float
    ci_high: float
    bootstrap_iterations: int


@dataclass
class HypothesisTestResult:
    part_a: str
    part_b: str
    metric: str
    alpha: float
    alternative: str
    n_pairs: int

    mean_a: float
    mean_b: float
    mean_diff: float
    median_diff: float
    positive_rate: float

    permutation_test_name: str
    permutation_statistic: float
    permutation_p_value: float
    permutation_count: int

    wilcoxon_test_name: str
    wilcoxon_statistic: float | None
    wilcoxon_p_value: float | None

    ci_method: str
    ci_confidence_level: float
    ci_low: float
    ci_high: float
    ci_bootstrap_iterations: int

    reject_null: bool
    interpretation: str


# =========================================================
# Key Builder
# =========================================================

def build_vehicle_key(df: pd.DataFrame) -> pd.Series:
    """
    Build a stable vehicle key (year|make|model).

    Why:
    We need a consistent anchor so we compare the SAME vehicle
    across two parts. Otherwise this turns into junk stats.
    """
    return (
        df["year"].astype(str).str.strip()
        + "|"
        + df["make"].astype(str).str.strip()
        + "|"
        + df["model"].astype(str).str.strip()
    )


# =========================================================
# Loader
# =========================================================

def load_analysis_summary(csv_path: str | Path) -> pd.DataFrame:
    """
    Load the analysis summary CSV.

    Quick sanity checks so we fail early instead of downstream.
    """
    df = pd.read_csv(csv_path)

    required_cols = ["year", "make", "model", "part"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["vehicle_key"] = build_vehicle_key(df)

    # Normalize part labels so comparisons don't fail on casing
    df["part"] = df["part"].astype(str).str.strip().str.lower()

    return df


# =========================================================
# Filtering Layer
# =========================================================

def filter_analysis_data(
    df: pd.DataFrame,
    part_a: str,
    part_b: str,
    metric: str,
    make: str | None = None,
    model: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
) -> pd.DataFrame:
    """
    Narrow dataset to:
    - the two parts we care about
    - optional make/model/year filters

    This keeps the test focused and avoids mixing apples and trucks.
    """
    work_df = df.copy()

    if metric not in work_df.columns:
        raise ValueError(f"Metric '{metric}' not found in input data.")

    part_a = part_a.strip().lower()
    part_b = part_b.strip().lower()

    # Only keep the two parts we are comparing
    work_df = work_df[work_df["part"].isin([part_a, part_b])].copy()

    if make:
        work_df = work_df[
            work_df["make"].astype(str).str.strip().str.lower()
            == make.strip().lower()
        ]

    if model:
        work_df = work_df[
            work_df["model"].astype(str).str.strip().str.lower()
            == model.strip().lower()
        ]

    if year_min is not None:
        work_df = work_df[work_df["year"] >= year_min]

    if year_max is not None:
        work_df = work_df[work_df["year"] <= year_max]

    # Drop rows where metric is missing so we don't poison the test
    work_df = work_df.dropna(subset=[metric])

    return work_df


# =========================================================
# Paired Frame Builder
# =========================================================

def build_paired_metric_frame(
    analysis_df: pd.DataFrame,
    part_a: str,
    part_b: str,
    metric: str,
) -> pd.DataFrame:
    """
    Build a paired DataFrame with one row per vehicle and one metric
    column for each part being compared.

    Output columns:
        vehicle_key, <part_a>, <part_b>, diff

    Vehicles missing either part are dropped — no pairing, no comparison.
    """
    required_cols = ["vehicle_key", "part", metric]
    missing = [col for col in required_cols if col not in analysis_df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    part_a = part_a.strip().lower()
    part_b = part_b.strip().lower()

    subset = analysis_df[analysis_df["part"].isin([part_a, part_b])].copy()

    paired = (
        subset.pivot_table(
            index="vehicle_key",
            columns="part",
            values=metric,
            aggfunc="first",
        )
        .reset_index()
        .dropna(subset=[part_a, part_b])
    )

    missing_cols = [c for c in [part_a, part_b] if c not in paired.columns]
    if missing_cols:
        raise ValueError(
            f"Could not build paired frame. Missing part columns: {missing_cols}"
        )

    paired["diff"] = paired[part_a] - paired[part_b]

    return paired


# =========================================================
# Monte Carlo Paired Permutation Test
# =========================================================
def run_monte_carlo_paired_permutation_test(
    diffs: pd.Series | np.ndarray, 
    alternative=HYPOTHESIS_ALTERNATIVE,
    exact_threshold=HYPOTHESIS_PERMUTATION_EXACT_THRESHOLD,
    monte_carlo_iterations=HYPOTHESIS_PERMUTATION_ITERATIONS,
    random_seed=HYPOTHESIS_RANDOM_SEED,
)-> PermutationTestResult:
    """
    Monte Carlo Paired Permutation Test using sign flips on paired differences.
    - Exact sign-flip enumeration for small n
    - Monte Carlo sign-flip approximation for larger n
    """
    values = np.asarray(pd.Series(diffs).dropna(), dtype=float)

    if values.size == 0:
        raise ValueError(
            "Permutation test requires at least one non-null paired difference."
        )

    observed = float(values.mean())
    n_pairs = int(values.size)

    if n_pairs == 0:
        raise ValueError("No paired differences available for permutation test.")

    # ----------------------------------------
    # EXACT (small n)
    # ----------------------------------------
    if n_pairs <= exact_threshold:
        sign_patterns = np.array(
            list(product([-1.0, 1.0], repeat=n_pairs)),
            dtype=float,
        )
        permuted_stats = (sign_patterns * values).mean(axis=1)
        method = "exact"
        permutation_count = len(permuted_stats)

    # ----------------------------------------
    # MONTE CARLO (large n)
    # ----------------------------------------
    else:
        rng = np.random.default_rng(random_seed)

        sign_patterns = rng.choice(
            [-1.0, 1.0],
            size=(monte_carlo_iterations, n_pairs),
            replace=True,
        )

        permuted_stats = (sign_patterns * values).mean(axis=1)
        method = "monte_carlo"
        permutation_count = monte_carlo_iterations

    # ----------------------------------------
    # P-VALUE
    # ----------------------------------------
    if alternative == "greater":
        p_value = float(np.mean(permuted_stats >= observed))
    elif alternative == "less":
        p_value = float(np.mean(permuted_stats <= observed))
    elif alternative == "two-sided":
        p_value = float(np.mean(np.abs(permuted_stats) >= abs(observed)))
    else:
        raise ValueError(
            "alternative must be 'greater', 'less', or 'two-sided'."
        )

    return PermutationTestResult(
        test_name="paired_permutation",
        alternative=alternative,
        n_pairs=n_pairs,
        observed_statistic=observed,
        p_value=p_value,
        permutation_count=permutation_count,
        method=method,
    )


# =========================================================
# Wilcoxon Signed-Rank Test
# =========================================================

def run_wilcoxon_signed_rank_test(
    diffs: pd.Series | np.ndarray,
    alternative: str = "greater",
) -> WilcoxonTestResult:
    """
    Run Wilcoxon signed-rank test on paired differences.

    Purpose:
    Confirm whether the median of paired differences is greater than zero.

    Notes:
    - Nonparametric
    - Appropriate for small samples
    - Uses same directional hypothesis as permutation test
    """
    values = np.asarray(pd.Series(diffs).dropna(), dtype=float)

    if values.size == 0:
        raise ValueError("Wilcoxon test requires at least one non-null value.")

    n_pairs = int(values.size)

    # Edge case: all zeros → test is undefined
    if np.all(values == 0):
        return WilcoxonTestResult(
            test_name="wilcoxon_signed_rank",
            alternative=alternative,
            n_pairs=n_pairs,
            statistic=None,
            p_value=1.0,
        )

    try:
        stat, p_value = wilcoxon(values, alternative=alternative)
    except Exception:
        stat, p_value = None, None

    return WilcoxonTestResult(
        test_name="wilcoxon_signed_rank",
        alternative=alternative,
        n_pairs=n_pairs,
        statistic=None if stat is None else float(stat),
        p_value=None if p_value is None else float(p_value),
    )


# =========================================================
# Bootstrap Confidence Interval for Mean Paired Difference
# =========================================================

def bootstrap_mean_diff_ci(
    diffs: pd.Series | np.ndarray,
    confidence_level: float = HYPOTHESIS_CI_CONFIDENCE_LEVEL,
    n_bootstrap: int = HYPOTHESIS_CI_BOOTSTRAP_ITERATIONS,
    random_seed: int = HYPOTHESIS_RANDOM_SEED,
) -> MeanDiffCIResult:
    """
    Build a bootstrap confidence interval for the mean paired difference.

    Purpose:
    Estimate a reasonable range for the mean difference without leaning on
    normality assumptions that do not fit this project well.

    Notes:
    - Resamples paired differences with replacement
    - Returns percentile-based confidence interval
    - Mean difference is the target summary statistic
    """
    values = np.asarray(pd.Series(diffs).dropna(), dtype=float)

    if values.size == 0:
        raise ValueError(
            "Confidence interval requires at least one non-null difference."
        )

    rng = np.random.default_rng(random_seed)

    boot_means = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        sample = rng.choice(values, size=len(values), replace=True)
        boot_means[i] = sample.mean()

    alpha = 1.0 - confidence_level
    ci_low = float(np.quantile(boot_means, alpha / 2))
    ci_high = float(np.quantile(boot_means, 1.0 - alpha / 2))

    return MeanDiffCIResult(
        method="bootstrap_percentile_mean_diff",
        confidence_level=confidence_level,
        n_pairs=int(values.size),
        mean_diff=float(values.mean()),
        ci_low=ci_low,
        ci_high=ci_high,
        bootstrap_iterations=n_bootstrap,
    )


# =========================================================
# Main Entry Point
# =========================================================

def run_hypothesis_test(
    csv_path: str | Path,
    part_a: str = HYPOTHESIS_PART_A,
    part_b: str = HYPOTHESIS_PART_B,
    metric: str = HYPOTHESIS_METRIC,
    alpha: float = HYPOTHESIS_ALPHA,
    alternative: str = HYPOTHESIS_ALTERNATIVE,
    make: str | None = HYPOTHESIS_MAKE,
    model: str | None = HYPOTHESIS_MODEL,
    year_min: int | None = HYPOTHESIS_YEAR_MIN,
    year_max: int | None = HYPOTHESIS_YEAR_MAX,
    ci_confidence_level: float = HYPOTHESIS_CI_CONFIDENCE_LEVEL,
    ci_bootstrap_iterations: int = HYPOTHESIS_CI_BOOTSTRAP_ITERATIONS,
    random_seed: int = HYPOTHESIS_RANDOM_SEED,
) -> tuple[HypothesisTestResult, pd.DataFrame]:
    """
    Run a paired hypothesis test comparing two parts on a chosen metric.

    Strategy:
    1. Run Monte Carlo paired permutation test (primary ~90 pairs, assumption-free)
    2. Run Wilcoxon signed-rank test (secondary — corroborating evidence)

    The permutation test p-value drives reject_null. Both results are
    surfaced in the returned HypothesisTestResult for full transparency.

    Returns:
        (HypothesisTestResult, paired_df)
        paired_df has one row per vehicle with columns for each part and diff.
    """
    df = load_analysis_summary(csv_path)

    filtered_df = filter_analysis_data(
        df=df,
        part_a=part_a,
        part_b=part_b,
        metric=metric,
        make=make,
        model=model,
        year_min=year_min,
        year_max=year_max,
    )

    paired_df = build_paired_metric_frame(
        analysis_df=filtered_df,
        part_a=part_a,
        part_b=part_b,
        metric=metric,
    )

    if paired_df.empty:
        raise ValueError("No matched vehicle pairs found after filtering.")

    part_a_key = part_a.strip().lower()
    part_b_key = part_b.strip().lower()

    a_values = paired_df[part_a_key]
    b_values = paired_df[part_b_key]
    diffs = paired_df["diff"]

    perm_result = run_monte_carlo_paired_permutation_test(
        diffs=diffs,
        alternative=alternative,
        monte_carlo_iterations=HYPOTHESIS_PERMUTATION_ITERATIONS,
        random_seed=HYPOTHESIS_RANDOM_SEED,
    )

    wilcox_result = run_wilcoxon_signed_rank_test(
        diffs=diffs,
        alternative=alternative,
    )

    ci_result = bootstrap_mean_diff_ci(
        diffs=diffs,
        confidence_level=ci_confidence_level,
        n_bootstrap=ci_bootstrap_iterations,
        random_seed=random_seed,
    )

    mean_a = float(a_values.mean())
    mean_b = float(b_values.mean())
    mean_diff = float(diffs.mean())
    median_diff = float(diffs.median())
    positive_rate = float((diffs > 0).mean()) 

    # Permutation test is primary; Wilcoxon is corroborating
    primary_p = perm_result.p_value

    reject_null = bool(primary_p < alpha)

    if reject_null:
        if mean_diff > 0:
            interpretation = (
                f"{part_a} tends to outperform {part_b} on {metric} "
                f"(permutation p={primary_p:.4f})."
            )
        else:
            interpretation = (
                f"{part_b} tends to outperform {part_a} on {metric} "
                f"(permutation p={primary_p:.4f})."
            )
    else:
        interpretation = (
            f"No meaningful difference detected between {part_a} and {part_b} "
            f"on {metric} (permutation p={primary_p:.4f})."
        )

    result = HypothesisTestResult(
        part_a=part_a,
        part_b=part_b,
        metric=metric,
        alpha=alpha,
        alternative=alternative,
        n_pairs=int(len(paired_df)),

        mean_a=mean_a,
        mean_b=mean_b,
        mean_diff=mean_diff,
        median_diff=median_diff,
        positive_rate=positive_rate,

        permutation_test_name=perm_result.test_name,
        permutation_statistic=perm_result.observed_statistic,
        permutation_p_value=perm_result.p_value,
        permutation_count=perm_result.permutation_count,

        wilcoxon_test_name=wilcox_result.test_name,
        wilcoxon_statistic=wilcox_result.statistic,
        wilcoxon_p_value=wilcox_result.p_value,

        ci_method=ci_result.method,
        ci_confidence_level=ci_result.confidence_level,
        ci_low=ci_result.ci_low,
        ci_high=ci_result.ci_high,
        ci_bootstrap_iterations=ci_result.bootstrap_iterations,

        reject_null=reject_null,
        interpretation=interpretation,
    )

    return result, paired_df