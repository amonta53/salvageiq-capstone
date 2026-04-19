# =========================================================
# visuals.py
# Build final project charts from saved pipeline outputs
#
# Purpose:
# Turn analysis and hypothesis outputs into simple, readable
# visuals for the report and final review.
#
# Notes:
# - Reads saved CSV outputs instead of recomputing analysis
# - Keeps chart logic out of the pipeline controller
# - Saves charts to disk for report use
# =========================================================

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path
import numpy as np

# === Optional adjustText import ===
try:
    from adjustText import adjust_text
    _HAS_ADJUST_TEXT = True
except ImportError:
    _HAS_ADJUST_TEXT = False

# === Matplotlib Style Baseline ===
plt.rcParams.update({
    "figure.dpi": 150,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 11,
})

# === Shared Helpers ===

def save_current_figure(output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=200, bbox_inches='tight')
    plt.close()

# === STR Bar Chart ===

def build_str_bar_chart(analysis_summary_path: Path, output_path: Path) -> pd.DataFrame:
    """
    - Aggregates median STR by part
    - STR displayed as percentages on y-axis
    - IQR error bars or overlays part-level points
    - Intentional color
    - Returns aggregated DataFrame
    """
    analysis_summary_path = Path(analysis_summary_path)
    output_path = Path(output_path)

    df = pd.read_csv(analysis_summary_path)
    required_cols = {'part', 'str'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Input CSV must contain columns: {required_cols}")

    group = df.groupby('part')['str']
    median_str = group.median()
    q1 = group.quantile(0.25)
    q3 = group.quantile(0.75)
    agg = pd.DataFrame({
        'str_median': median_str,
        'str_q1': q1,
        'str_q3': q3,
    }).sort_values('str_median', ascending=False)

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(7, max(2, 0.35 * len(agg))))

    # Bar color: use a purposeful palette (e.g., muted orange)
    color = "#F89C2A"

    # Bar heights and error bars
    y = agg['str_median']
    x = np.arange(len(agg))
    yerr = np.abs(np.vstack([agg['str_median'] - agg['str_q1'],
                             agg['str_q3'] - agg['str_median']]))
    bars = ax.bar(x, y, color=color, edgecolor='gray', yerr=yerr, capsize=6, width=0.6)

    # Overlay all part-level values as scatter for spread
    for idx, part in enumerate(agg.index):
        jitter = np.random.uniform(-0.13, 0.13, size=(df[df['part']==part].shape[0],))
        ax.scatter(np.full_like(jitter, idx)+jitter,
                   df[df['part']==part]['str'],
                   color='k', alpha=0.25, s=14, marker='o', linewidths=0.4, edgecolors='none', zorder=3)

    # Axes and labels
    ax.set_xticks(x)
    ax.set_xticklabels(agg.index, rotation=30, ha='right')
    ax.set_ylabel("STR (%)")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{y*100:.0f}%"))
    ax.set_xlabel("Part")

    ax.set_title("Median STR by Part\n(Bar=Median, Error=IQR, Dots=Observations)")

    plt.tight_layout()
    save_current_figure(output_path)
    return agg.reset_index()

# === Price vs STR Scatter ===

def build_price_vs_str_scatter(analysis_summary_path: Path, output_path: Path) -> pd.DataFrame:
    """
    - Aggregates median price & median STR by part
    - Annotates part names with overlap prevention if adjustText available
    - Reference lines for medians, quadrant shadings
    - Axes: $ and %
    - Returns aggregated DataFrame
    """
    analysis_summary_path = Path(analysis_summary_path)
    output_path = Path(output_path)

    df = pd.read_csv(analysis_summary_path)
    required_cols = {'part', 'median_price', 'str'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Input CSV must contain columns: {required_cols}")

    agg = df.groupby('part').agg(
        median_price=('median_price', 'median'),
        median_str=('str', 'median')
    ).sort_values('median_price', ascending=False)

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(7, 5))

    x = agg['median_price']
    y = agg['median_str']

    # Scatter: Use different color for clarity
    color = "#2A8FF8"
    ax.scatter(x, y, s=60, color=color, edgecolor='gray', zorder=3)

    # Quadrant reference lines
    xmed = x.median()
    ymed = y.median()
    ax.axhline(ymed, color='gray', ls='--', lw=1, alpha=0.6, zorder=1)
    ax.axvline(xmed, color='gray', ls='--', lw=1, alpha=0.6, zorder=1)

    # Quadrant shading
    ax.axhspan(ymed, ax.get_ylim()[1], xmed, ax.get_xlim()[1], color='#CCE2FA', alpha=0.24, zorder=0)  # Upper right
    ax.axhspan(0, ymed, 0, xmed, color='#F6DFC3', alpha=0.18, zorder=0)  # Lower left

    # Quadrant labels
    ax.text(xmed+0.02*(x.max()-x.min()), ymed+0.02*(y.max()-y.min()), "High Price, High STR",
            va='bottom', ha='left', color='k', fontsize=10, weight='bold', alpha=0.7)
    ax.text(ax.get_xlim()[0]+0.03*(x.max()-x.min()), ax.get_ylim()[0]+0.03*(y.max()-y.min()),
            "Low Price, Low STR", va='bottom', ha='left', color='k', fontsize=10, weight='bold', alpha=0.7)

    # Labels for points, avoid overlap with adjustText if available
    texts = []
    for xi, yi, label in zip(x, y, agg.index):
        if _HAS_ADJUST_TEXT:
            texts.append(ax.text(xi, yi, label, fontsize=9, va='bottom', ha='center', color='black', alpha=0.7))
        else:
            ax.annotate(label, (xi, yi), fontsize=9, textcoords='offset points',
                        xytext=(0, 4), ha='center', color='black', alpha=0.7)

    if _HAS_ADJUST_TEXT and texts:
        adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle='-', color='gray', lw=0.4, alpha=0.5))

    ax.set_xlabel("Median Price ($)")
    ax.set_ylabel("Median STR (%)")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{y*100:.0f}%"))
    ax.set_title("Median Price vs STR by Part")

    plt.tight_layout()
    save_current_figure(output_path)
    return agg.reset_index()

# === Opportunity Score Bar Chart ===

def build_opportunity_score_bar_chart(ranked_output_path: Path, output_path: Path) -> pd.DataFrame:
    """
    - Aggregates median opportunity_score by part
    - Bar: median, IQR error bars if feasible, dots for spread
    - Intentional color
    - Returns aggregated DataFrame
    """
    ranked_output_path = Path(ranked_output_path)
    output_path = Path(output_path)

    df = pd.read_csv(ranked_output_path)
    if not {'part', 'opportunity_score'}.issubset(df.columns):
        raise ValueError("Input CSV must contain 'part' and 'opportunity_score' columns.")

    group = df.groupby('part')['opportunity_score']
    median_os = group.median()
    q1 = group.quantile(0.25)
    q3 = group.quantile(0.75)
    agg = pd.DataFrame({
        'opportunity_score_median': median_os,
        'opportunity_score_q1': q1,
        'opportunity_score_q3': q3,
    }).sort_values('opportunity_score_median', ascending=False)

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(7, max(2, 0.35 * len(agg))))

    # Bar color: Use a blue/green
    color = "#36B37E"
    x = np.arange(len(agg))
    y = agg['opportunity_score_median']
    yerr = np.abs(np.vstack([
        agg['opportunity_score_median'] - agg['opportunity_score_q1'],
        agg['opportunity_score_q3'] - agg['opportunity_score_median']
    ]))
    ax.bar(x, y, color=color, edgecolor='gray', yerr=yerr, capsize=6, width=0.6)

    # Overlay all part-level values as scatter
    for idx, part in enumerate(agg.index):
        part_vals = df[df['part'] == part]['opportunity_score']
        jitter = np.random.uniform(-0.13, 0.13, size=len(part_vals))
        ax.scatter(np.full_like(jitter, idx)+jitter, part_vals,
                   color='k', alpha=0.21, s=14, marker='o', linewidths=0.3, edgecolors='none', zorder=3)

    # Formatting
    ax.set_xticks(x)
    ax.set_xticklabels(agg.index, rotation=30, ha='right')
    ax.set_xlabel("Part")
    ax.set_ylabel("Opportunity Score")
    ax.set_title("Median Opportunity Score by Part\n(Bar=Median, Error=IQR, Dots=Observations)")

    plt.tight_layout()
    save_current_figure(output_path)
    return agg.reset_index()

# === Hypothesis Difference Distribution Chart ===

def build_diff_distribution_chart(hypothesis_pairs_path: Path, output_path: Path) -> pd.DataFrame:
    """
    - Plots histogram of diff, with vertical lines at 0, mean, median
    - Optional stats: p_value, wilcoxon_p_value, ci_low, ci_high, n_pairs
    - Shaded CI region when available
    - Returns the DataFrame as loaded
    """
    hypothesis_pairs_path = Path(hypothesis_pairs_path)
    output_path = Path(output_path)

    df = pd.read_csv(hypothesis_pairs_path)
    if 'diff' not in df.columns:
        raise ValueError("Input CSV must contain 'diff' column.")

    diffs = df['diff'].dropna()
    n = len(diffs)
    if n == 0:
        raise ValueError("No valid 'diff' values found in input.")

    mean_diff = diffs.mean()
    median_diff = diffs.median()
    ci_low = df['ci_low'].iloc[0] if 'ci_low' in df.columns and not df['ci_low'].isna().all() else None
    ci_high = df['ci_high'].iloc[0] if 'ci_high' in df.columns and not df['ci_high'].isna().all() else None
    n_pairs = int(df['n_pairs'].iloc[0]) if 'n_pairs' in df.columns and not df['n_pairs'].isna().all() else n
    p_value = df['p_value'].iloc[0] if 'p_value' in df.columns and not df['p_value'].isna().all() else None
    wilcoxon_p = df['wilcoxon_p_value'].iloc[0] if 'wilcoxon_p_value' in df.columns and not df['wilcoxon_p_value'].isna().all() else None

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(7, 4))
    bins = min(30, max(6, n//6))
    color = "#355C7D"

    # Histogram
    ax.hist(diffs, bins=bins, color=color, alpha=0.88, edgecolor='white', zorder=2)

    # Vertical reference lines
    ax.axvline(0, color='k', linestyle=':', linewidth=1.1, label='Null (0)', zorder=3)
    ax.axvline(mean_diff, color='#EF8636', linestyle='--', linewidth=1.5, label='Mean', zorder=3)
    ax.axvline(median_diff, color='#229378', linestyle='-.', linewidth=1.2, label='Median', zorder=3)

    # CI shading
    if ci_low is not None and ci_high is not None and np.isfinite(ci_low) and np.isfinite(ci_high):
        ax.axvspan(ci_low, ci_high, color='#FAF067', alpha=0.25, zorder=1)
        ci_text = f"Boot. 95% CI: [{ci_low:.3f}, {ci_high:.3f}]"
    else:
        ci_text = None

    # Stats annotation
    summary_lines = [f"n pairs: {n_pairs}",
                     f"Mean diff: {mean_diff:.3f}",
                     f"Median diff: {median_diff:.3f}"]
    if p_value is not None and np.isfinite(p_value):
        summary_lines.append(f"Perm. p: {p_value:.3g}")
    if wilcoxon_p is not None and np.isfinite(wilcoxon_p):
        summary_lines.append(f"Wilcoxon p: {wilcoxon_p:.3g}")
    if ci_text:
        summary_lines.append(ci_text)
    summary = "\n".join(summary_lines)

    # Annotation box (upper right)
    props = dict(boxstyle='round', facecolor='white', alpha=0.8, lw=0.8)
    ax.text(0.98, 0.98, summary, ha='right', va='top', fontsize=10, color='black',
            transform=ax.transAxes, bbox=props)

    ax.set_xlabel("Difference")
    ax.set_ylabel("Count")
    ax.set_title("Distribution of Hypothesis Test Differences")
    ax.legend(loc='upper left', frameon=False)

    plt.tight_layout()
    save_current_figure(output_path)
    return df

# === Orchestration ===

def run_visuals(
    analysis_summary_path: Path,
    ranked_output_path: Path,
    hypothesis_pairs_path: Path,
    str_chart_path: Path,
    price_vs_str_path: Path,
    opportunity_chart_path: Path,
    diff_chart_path: Path,
) -> dict:
    """
    - Calls all chart builders and saves charts to specified output directory
    - Returns dict with DataFrames and chart paths
    """
    str_chart_df = build_str_bar_chart(analysis_summary_path, str_chart_path)
    price_vs_str_df = build_price_vs_str_scatter(analysis_summary_path, price_vs_str_path)
    opportunity_chart_df = build_opportunity_score_bar_chart(ranked_output_path, opportunity_chart_path)
    diff_chart_df = build_diff_distribution_chart(hypothesis_pairs_path, diff_chart_path)

    return {
        'str_chart_df': str_chart_df,
        'price_vs_str_df': price_vs_str_df,
        'opportunity_chart_df': opportunity_chart_df,
        'diff_chart_df': diff_chart_df,
        'str_chart_path': str_chart_path,
        'price_vs_str_path': price_vs_str_path,
        'opportunity_chart_path': opportunity_chart_path,
        'diff_chart_path': diff_chart_path,
    }
