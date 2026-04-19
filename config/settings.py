# =========================================================
# settings.py
# Central project paths and runtime defaults.
#
# Purpose:
# - Defines file system locations used across the pipeline
# - Stores shared runtime defaults that are not vehicle- or taxonomy-specific
#
# Notes:
# - PROJECT_ROOT should resolve to the repository root
# - Use *_PATH names for concrete file paths
# - Vehicle support scope belongs in vehicles.py, not here
# =========================================================

from pathlib import Path

# =========================================================
# --- Project paths ---
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RUNS_DIR = DATA_DIR / "runs"

# =========================================================
# --- Time scope ---
# Vehicle-level production ranges may narrow this further.
# =========================================================
START_YEAR = 2012
END_YEAR = 2020
OBSERVATION_WINDOW_DAYS = 90

# =========================================================
# Confidence score tuning
# =========================================================
CONFIDENCE_SOLD_TARGET = 10
CONFIDENCE_ACTIVE_TARGET = 10
CONFIDENCE_SOLD_WEIGHT = 0.7
CONFIDENCE_ACTIVE_WEIGHT = 0.3
CONFIDENCE_MAX_SCORE = 1.0

# =========================================================
# Quality flags
# =========================================================
LOW_SAMPLE_TOTAL_THRESHOLD = 5
VERY_LOW_SOLD_THRESHOLD = 3
STALE_SNAPSHOT_HOURS = 48

# =========================================================
# Analysis parameters
# =========================================================
CONFIDENCE_THRESHOLD = 10
ALPHA = 0.05
TOP_N_PARTS = 10

# =========================================================
# Hypothesis test parameters
# =========================================================
ANALYSIS_USE_EXISTING_SUMMARY = False
RUN_HYPOTHESIS_TEST = False

HYPOTHESIS_PART_A = "alternator"
HYPOTHESIS_PART_B = "headlight"
HYPOTHESIS_METRIC = "str"
HYPOTHESIS_ALPHA = 0.05
HYPOTHESIS_ALTERNATIVE = "greater"

HYPOTHESIS_CI_CONFIDENCE_LEVEL = 0.95
HYPOTHESIS_CI_BOOTSTRAP_ITERATIONS = 10_000
HYPOTHESIS_RANDOM_SEED = 42

HYPOTHESIS_PERMUTATION_EXACT_THRESHOLD = 15
HYPOTHESIS_PERMUTATION_ITERATIONS = 100_000

HYPOTHESIS_MAKE = None
HYPOTHESIS_MODEL = None 
HYPOTHESIS_YEAR_MIN = 2012  
HYPOTHESIS_YEAR_MAX = 2020

# =========================================================
# --- Scrape / processing behavior ---
# =========================================================
HEADLESS = True
ENABLE_RESUME = True
SAVE_DEBUG_HTML = False
RUN_EDA = False 
SEARCH_SCOPE = "sold" # "sold" or "all" 
USED_ONLY = True
RESET_OUTPUTS_ON_RUN = True 

# --- Browser Scraping settings ---
PAGE_DELAY_MIN = 0.6
PAGE_DELAY_MAX = 1.5
NEXT_PAGE_DELAY_MIN = 0.5
NEXT_PAGE_DELAY_MAX = 1.0
SEARCH_DELAY_MIN = 0.5
SEARCH_DELAY_MAX = 1.2 
GOTO_TIMEOUT_MS = 15000
SAVE_INTERMEDIATE_FILES = True
MAX_RETRIES = 3
MAX_PAGES_PER_SEARCH = 2 
BROWSER_RESTART_INTERVAL = 50
PROGRESS_REPORT_INTERVAL = 50
SEARCH_REPORT_INTERVAL = 10
WEAK_RESULT_SKIP_THRESHOLD = 3
