# =========================================================
# scrape_config.py
# Runtime scrape configuration for SalvageIQ.
#
# Purpose:
# - Defines the active scrape contract used by main.py and scrape/runner.py
# - Centralizes runtime flags, search scope, and file paths
#
# Notes:
# - Vehicle-level year ranges come from SUPPORTED_VEHICLES
# - Global start/end years further limit each vehicle search window
# - Keep concrete file fields named as *_path
# =========================================================

from dataclasses import dataclass, field
from pathlib import Path 
from typing import TypedDict
from uuid import uuid4 

from config.settings import (
    ALPHA,
    ANALYSIS_USE_EXISTING_SUMMARY,
    BROWSER_RESTART_INTERVAL,
    CONFIDENCE_SOLD_TARGET,
    CONFIDENCE_ACTIVE_TARGET,
    CONFIDENCE_SOLD_WEIGHT,
    CONFIDENCE_ACTIVE_WEIGHT,
    CONFIDENCE_MAX_SCORE,
    CONFIDENCE_THRESHOLD,
    ENABLE_RESUME,
    END_YEAR,
    GOTO_TIMEOUT_MS,
    HEADLESS,
    HYPOTHESIS_ALPHA,
    HYPOTHESIS_ALTERNATIVE,
    HYPOTHESIS_CI_BOOTSTRAP_ITERATIONS,
    HYPOTHESIS_CI_CONFIDENCE_LEVEL,
    HYPOTHESIS_MAKE,
    HYPOTHESIS_METRIC,
    HYPOTHESIS_MODEL,
    HYPOTHESIS_PART_A,
    HYPOTHESIS_PART_B,
    HYPOTHESIS_PERMUTATION_EXACT_THRESHOLD,
    HYPOTHESIS_PERMUTATION_ITERATIONS,
    HYPOTHESIS_RANDOM_SEED,
    HYPOTHESIS_YEAR_MAX,
    HYPOTHESIS_YEAR_MIN,
    LOW_SAMPLE_TOTAL_THRESHOLD,
    MAX_PAGES_PER_SEARCH,
    NEXT_PAGE_DELAY_MAX,
    NEXT_PAGE_DELAY_MIN,
    PAGE_DELAY_MAX,
    PAGE_DELAY_MIN,
    PROGRESS_REPORT_INTERVAL,
    RESET_OUTPUTS_ON_RUN,
    RUN_EDA,
    RUN_HYPOTHESIS_TEST,
    RUNS_DIR, 
    SAVE_DEBUG_HTML,
    SEARCH_DELAY_MAX,
    SEARCH_DELAY_MIN,
    SEARCH_REPORT_INTERVAL,
    SEARCH_SCOPE,
    STALE_SNAPSHOT_HOURS,
    START_YEAR,
    TOP_N_PARTS,
    USED_ONLY,
    VERY_LOW_SOLD_THRESHOLD,
    WEAK_RESULT_SKIP_THRESHOLD,
)
from config.taxonomy import SEARCH_PART_TERMS
from config.vehicles import SUPPORTED_VEHICLES
from config.schema import SOLD_COLUMN_MAP, ACTIVE_COLUMN_MAP, EDA_COLUMN_MAP


class VehicleConfig(TypedDict):
    year_range: tuple[int, int]
    make: str
    model: str

@dataclass(slots=True)
class ScrapeConfig:
    # =====================================================
    # --- Run mode ---
    # "full" -- Scrape all 10 vehicles and all parts for the full year range (2012-2020)
    # "mini" -- Scrape a small subset of vehicles/parts/years for quick testing and debugging
    # "pre_collected" -- Skip scraping and just load from raw CSV (useful for testing downstream processing and analysis)
    # =====================================================
    mode: str = "full"   

    # =========================================================
    # Allow an optional input run_id to support reusing existing outputs and logs for a given run.  
    # =========================================================
    input_run_id: str | None = None
    
    # =========================================================
    # Core run settings
    # =========================================================
    run_id: str = field(default_factory=lambda: str(uuid4()))

    # =========================================================
    # Key output paths
    # =========================================================
    runs_dir: Path = RUNS_DIR

    # =====================================================
    # --- Browser / scraping behavior ---
    # =====================================================
    headless: bool = HEADLESS
    search_scope: str = SEARCH_SCOPE
    used_only: bool = USED_ONLY
    enable_resume: bool = ENABLE_RESUME
    save_debug_html: bool = SAVE_DEBUG_HTML
    run_eda: bool = RUN_EDA 
    reset_outputs_on_run: bool = RESET_OUTPUTS_ON_RUN

    browser_restart_interval: int = BROWSER_RESTART_INTERVAL
    progress_report_interval: int = PROGRESS_REPORT_INTERVAL
    search_report_interval: int = SEARCH_REPORT_INTERVAL
    max_pages_per_search: int = MAX_PAGES_PER_SEARCH
    goto_timeout_ms: int = GOTO_TIMEOUT_MS
    weak_result_skip_threshold: int = WEAK_RESULT_SKIP_THRESHOLD

    page_delay_min: float = PAGE_DELAY_MIN
    page_delay_max: float = PAGE_DELAY_MAX
    next_page_delay_min: float = NEXT_PAGE_DELAY_MIN
    next_page_delay_max: float = NEXT_PAGE_DELAY_MAX
    search_delay_min: float = SEARCH_DELAY_MIN
    search_delay_max: float = SEARCH_DELAY_MAX

    # =====================================================
    # --- Search Scope ---
    # =====================================================
    start_year: int = START_YEAR
    end_year: int = END_YEAR
    parts: list[str] = field(default_factory=lambda: SEARCH_PART_TERMS.copy())
    supported_vehicles: list[VehicleConfig] = field(
        default_factory=lambda: [v.copy() for v in SUPPORTED_VEHICLES]
    )

    # =====================================================
    # --- Confidence Scoring ---
    # =====================================================
    confidence_sold_target: int = CONFIDENCE_SOLD_TARGET
    confidence_active_target: int = CONFIDENCE_ACTIVE_TARGET
    confidence_sold_weight: float = CONFIDENCE_SOLD_WEIGHT
    confidence_active_weight: float = CONFIDENCE_ACTIVE_WEIGHT
    confidence_max_score: float = CONFIDENCE_MAX_SCORE

    # =========================================================
    # --- Quality flags ---
    # =========================================================
    low_sample_total_threshold: int = LOW_SAMPLE_TOTAL_THRESHOLD
    very_low_sold_threshold: int = VERY_LOW_SOLD_THRESHOLD
    stale_snapshot_hours: int = STALE_SNAPSHOT_HOURS

    # =========================================================
    # --- Output Criteria ---
    # =========================================================
    confidence_threshold: int = CONFIDENCE_THRESHOLD
    alpha: float = ALPHA
    top_n_parts: int = TOP_N_PARTS

    # =========================================================
    # --- Hypothesis test parameters ---
    # =========================================================
    analysis_use_existing_summary: bool = ANALYSIS_USE_EXISTING_SUMMARY
    run_hypothesis_test: bool = RUN_HYPOTHESIS_TEST

    hypothesis_part_a: str = HYPOTHESIS_PART_A
    hypothesis_part_b: str = HYPOTHESIS_PART_B
    hypothesis_metric: str = HYPOTHESIS_METRIC
    hypothesis_alpha: float = HYPOTHESIS_ALPHA
    hypothesis_alternative: str = HYPOTHESIS_ALTERNATIVE

    hypothesis_ci_confidence_level: float = HYPOTHESIS_CI_CONFIDENCE_LEVEL
    hypothesis_ci_bootstrap_iterations: int = HYPOTHESIS_CI_BOOTSTRAP_ITERATIONS
    hypothesis_random_seed: int = HYPOTHESIS_RANDOM_SEED

    hypothesis_permutation_exact_threshold: int = HYPOTHESIS_PERMUTATION_EXACT_THRESHOLD
    hypothesis_permutation_iterations: int = HYPOTHESIS_PERMUTATION_ITERATIONS

    hypothesis_make: str | None = HYPOTHESIS_MAKE
    hypothesis_model: str | None = HYPOTHESIS_MODEL
    hypothesis_year_min: int | None = HYPOTHESIS_YEAR_MIN
    hypothesis_year_max: int | None = HYPOTHESIS_YEAR_MAX

    # =====================================================
    # --- Column Maps---
    # =====================================================
    sold_column_map: dict = field(default_factory=lambda: SOLD_COLUMN_MAP.copy())
    active_column_map: dict = field(default_factory=lambda: ACTIVE_COLUMN_MAP.copy())
    eda_column_map: dict = field(default_factory=lambda: EDA_COLUMN_MAP.copy())
    

    # =========================================================
    # Run-scoped directory structure
    # =========================================================
    @property
    def run_dir(self) -> Path:
        return self.runs_dir / self.run_id

    @property
    def raw_dir(self) -> Path:
        return self.run_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.run_dir / "processed"

    @property
    def outputs_dir(self) -> Path:
        return self.run_dir / "outputs"

    @property
    def logs_dir(self) -> Path:
        return self.outputs_dir / "logs"

    @property
    def visuals_dir(self) -> Path:
        return self.outputs_dir / "visuals"
    
    @property
    def analysis_dir(self) -> Path:
        return self.outputs_dir / "analysis"
    
    @property
    def hypothesis_dir(self) -> Path:
        return self.outputs_dir / "hypothesis"

    @property
    def debug_dir(self) -> Path:
        return self.outputs_dir / "debug"
    
    # =========================================================
    # --- CSV output paths ---
    # These are the concrete paths used by the processing and analysis stages. 
    # They point to the run-specific directories.
    # =========================================================

    @property
    def raw_csv_path(self) -> Path:
        return self.raw_dir / "raw_listings.csv"

    @property
    def checkpoint_path(self) -> Path:
        return self.raw_dir / "scrape_checkpoint.json"

    @property
    def cleansed_csv_path(self) -> Path:
        return self.processed_dir / "cleansed_listings.csv"

    @property
    def normalized_csv_path(self) -> Path:
        return self.processed_dir / "normalized_listings.csv"

    @property
    def market_summary_csv_path(self) -> Path:
        return self.processed_dir / "market_summary.csv"

    @property
    def analysis_summary_csv_path(self) -> Path:
        return self.analysis_dir / "analysis_summary.csv"

    @property
    def full_ranked_output_csv_path(self) -> Path:
        return self.analysis_dir / "ranked_parts_all.csv"

    @property
    def top_10_output_csv_path(self) -> Path:
        return self.analysis_dir / "ranked_parts_top10.csv"

    @property
    def eda_summary_csv_path(self) -> Path:
        return self.analysis_dir / "eda_category_summary.csv"

    @property
    def hypothesis_output_csv_path(self) -> Path:
        return self.hypothesis_dir / "hypothesis_test_results.csv"

    @property
    def hypothesis_pairs_csv_path(self) -> Path:
        return self.hypothesis_dir / "hypothesis_test_pairs.csv"

    @property
    def log_path(self) -> Path:
        return self.logs_dir / f"pipeline_{self.run_id}.log"
    
    @property
    def manifest_path(self) -> Path:
        return self.outputs_dir / "run_manifest.json"
    
    @property
    def scrape_log_path(self) -> Path:
        return self.logs_dir / "scrape_run.log"
    
    @property
    def pipeline_log_path(self) -> Path:
        return self.logs_dir / f"pipeline_{self.run_id}.log"
    
    @property
    def hypothesis_diff_distribution_png_path(self) -> Path:
        return self.visuals_dir / "hypothesis_diff_distribution.png"

    @property
    def opportunity_score_by_part_png_path(self) -> Path:
        return self.visuals_dir / "opportunity_score_by_part.png"

    @property
    def price_vs_str_png_path(self) -> Path:
        return self.visuals_dir / "price_vs_str.png"

    @property
    def str_by_part_png_path(self) -> Path:
        return self.visuals_dir / "str_by_part.png"
    
    # =========================================================
    # --- Input run directory (optional) ---
    # If input_run_id is provided, this property resolves to the run_dir of that run, 
    # allowing downstream stages to read from existing outputs and logs.
    # =========================================================
    @property
    def input_run_dir(self) -> Path | None:
        if not self.input_run_id:
            return None
        return self.runs_dir / self.input_run_id
    
    @property
    def source_analysis_summary_csv_path(self) -> Path:
        if self.analysis_use_existing_summary and self.input_run_id:
            return self.input_run_dir / self.analysis_summary_csv_path.relative_to(self.run_dir)
        return self.analysis_summary_csv_path
    
    @property
    def source_full_ranked_output_csv_path(self) -> Path:
        if self.input_run_id:
            return self.input_run_dir / self.full_ranked_output_csv_path.relative_to(self.run_dir)
        return self.full_ranked_output_csv_path

    @property
    def source_hypothesis_pairs_csv_path(self) -> Path:
        if self.input_run_id:
            return self.input_run_dir / self.hypothesis_pairs_csv_path.relative_to(self.run_dir)
        return self.hypothesis_pairs_csv_path

    @property
    def source_hypothesis_output_csv_path(self) -> Path:
        if self.input_run_id:
            return self.input_run_dir / self.hypothesis_output_csv_path.relative_to(self.run_dir)
        return self.hypothesis_output_csv_path

    # =========================================================
    # --- Debug HTML path builder ---
    # Builds a consistent path for saving debug HTML files based on the search parameters.
    # ========================================================== 
    def build_error_html_path(
        self,
        year: int,
        make: str,
        model: str,
        part: str,
        page_num: int,
    ) -> Path:
        safe_make = str(make).replace(" ", "_")
        safe_model = str(model).replace(" ", "_")
        safe_part = str(part).replace(" ", "_")

        filename = (
            f"ERROR_{year}_{safe_make}_{safe_model}_{safe_part}_p{page_num}.html"
        )
        return self.debug_dir / filename

    # =====================================================
    # --- Make-Model Map ---
    # =====================================================
    make_model_map: dict[str, list[str]] = field(init=False)

    def __post_init__(self) -> None:
        result: dict[str, list[str]] = {}
        for vehicle in self.supported_vehicles:
            make = vehicle["make"]
            model = vehicle["model"]
            result.setdefault(make, [])
            if model not in result[make]:
                result[make].append(model)
        self.make_model_map = result