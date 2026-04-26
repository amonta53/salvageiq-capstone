# SalvageIQ 

## Salvage Vehicle Part Recommendation Engine

## Project Overview

This project is the decision engine behind a larger app idea:

> Walk into a salvage yard, scan or enter a VIN, and instantly know which parts on that car are actually worth pulling.

The question that this project seeks to answer is:

> Which parts on a given vehicle will provide the best opportunity to make money?

Rather than relying on the opinions of others about which parts will provide the best returns for salvage yard workers, this project will use real marketplace data from eBay to provide a true answer to this question for any given vehicle.

## Full Dataset

The full dataset used for this project exceeds GitHub file size limits and is not stored in this repository.

For access to the complete dataset and structure details, see:

[DATASET.md](DATASET.md)

## Approach

Pull the past three months of eBay listing data and answer three things for each part:

-   How often does it sell?
-   What does it typically sell for?
-   How reliable is that data?

Answering these three questions will allow for the creation of a ranking score for each part in a salvage car, which will answer the question of which salvage parts will provide the best opportunity to make money on the marketplace.

## The Model

Because eBay does not keep sell-through metrics for their cars, this model will estimate that figure based on the available data:
```
sell_through = sold / (sold + active)
```

That gives a reasonable signal of demand vs. supply. Each part is then scored:

```
opportunity_score = median_sold_price × sell_through × confidence
```

Where the median sold price is the median price that the part is sold for on eBay, the sell through is the ratio of the number of cars that sold a part divided by the total number of cars that had that part, and the confidence in the data is a reliability score for the part on that vehicle.

The confidence score is created as a weighted sum of the sold and active values of a part on a vehicle:
```
sold_component  = min(1.0, sold_count  / confidence_sold_target)   # weight: 0.70
active_component = min(1.0, active_count / confidence_active_target) # weight: 0.30
confidence = (sold_component × 0.70) + (active_component × 0.30)
```

## Statistical Validation
The opportunity score can answer the question of which parts will sell the best, but it is important to know if the differences in opportunity score between parts are statistically significant.

The hypothesis that will be tested is the following:

> Do alternators tend to sell more reliably than headlights on eBay?

The null and alternative hypotheses will be:
-   **H₀:** STR_alternator ≤ STR_headlight
-   **H₁:** STR_alternator > STR_headlight

**Primary test — Paired Monte Carlo Permutation Test**
Uses Monte Carlo methods to sample from the distribution of the differences in each vehicle’s parts, calculating the proportion of samples where the alternator’s rate is less than the headlights’ rate to calculate a p-value. Use of permutations of the data allows for this test to be non-parametric in nature. For differences in sizes of n ≤ 15, an exact enumeration will be performed; otherwise a Monte Carlo approximation will be used. The paired nature of the samples makes this appropriate for the data despite the normality assumptions of other tests.

**Confirmatory test — Wilcoxon Signed-Rank Test**
Another non-parametric test of the same differences between the parts on each vehicle. This will corroborate the findings of the permutation test.

**Bootstrap Confidence Interval**
For a 95% confidence interval for the mean difference in sell-through between the two parts, using a percentile-based bootstrap sample for the differences.

## Quality Flags

Several quality flags will be created for the parts on each of the salvage cars.
Three quality flags will be created:
| Flag | Condition | Purpose |
|-----|-----------|---------|
| `low_sample_flag` | sold_count < 5 | Insufficient total observations |
| `very_low_sold_flag` | sold_count < 3 | Too few sold observations to trust STR |
| `stale_snapshot_flag` | time_diff > 48 hours | Active snapshot is too old relative to sold data |

Price outlier trimming is also applied at the 5th and 95th percentiles (for groups of 20+ observations) before calculating median price.

## What This Is NOT

-   This tool is not a full parts catalog or vehicle inventory
-   This tool is not a true sell-through rate metric, but instead a proxy metric for that value
-   This tool will not calculate profit - it does not account for the costs of pulling the parts or shipping the cars
-   This tool is not a predictor for the future - these values are calculated for the past 90 days only

## Project Structure

```text
salvageiq-capstone/
│
├── config/
│   ├── settings.py          # runtime defaults and tuning parameters
│   ├── vehicles.py          # supported vehicles and valid year ranges
│   ├── taxonomy.py          # part classification rules and search terms
│   ├── schema.py            # column contracts for each pipeline stage
│   ├── scrape_config.py     # ScrapeConfig dataclass and all path properties
│   └── config_builder.py    # run mode factory (full, mini, test, eda, csv)
│
├── scrape/
│   ├── runner.py            # Playwright scrape runner (sold + active passes)
│   ├── extractors.py        # field extractors for raw listing data
│   └── search_builder.py    # eBay search URL and checkpoint key builders
│
├── wrangle/
│   ├── cleanse.py           # raw listing cleanup and field extraction
│   └── normalize.py         # standardization, taxonomy mapping, deduplication
│
├── analysis/
│   ├── analyze.py           # analysis stage controller
│   ├── aggregation.py       # sold + active join, STR, flags, opportunity score
│   ├── scoring.py           # STR, confidence, and opportunity score formulas
│   ├── ranking.py           # ranked output builder
│   ├── hypothesis_test.py   # permutation test, Wilcoxon, bootstrap CI
│   ├── pricing_metrics.py   # price outlier trimming
│   └── debug_eda.py         # EDA helpers (run_eda mode only)
│
├── pipeline/
│   └── orchestrator.py      # stage sequencing and flag-driven routing
│
├── visualization/
│   └── visuals.py           # matplotlib chart builders for all four outputs
│
├── utils/
│   ├── checkpoint_utils.py  # scrape resume support (completed search tracking)
│   ├── io_utils.py          # CSV helpers, directory setup, file resets
│   └── logging_utils.py     # run-scoped logging to file + console
│
├── tests/
│   ├── smoke/
│   │   ├── test_imports.py           # module import validation
│   │   ├── test_config_build.py      # ScrapeConfig construction
│   │   ├── test_runner_smoke.py      # scrape runner execution (integration)
│   │   ├── test_wrangle_smoke.py     # cleanse → normalize flow
│   │   └── test_analyze_smoke.py     # analysis stage output
│   ├── unit/
│   │   ├── test_normalize_token.py
│   │   ├── test_standardize_make.py
│   │   ├── test_standardize_model.py
│   │   ├── test_standardize_part.py
│   │   ├── test_classify_part.py
│   │   ├── test_category_from_part.py
│   │   ├── test_deduplicate_listings.py
│   │   ├── test_run_normalization.py
│   │   ├── test_ranking.py
│   │   └── test_output_schemas.py
│   ├── test_aggregation.py           # aggregation layer unit tests
│   └── test_orchestrator_flags.py    # orchestrator routing tests (mocked stages)
│
├── data/
│   └── runs/
│       └── <run_id>/
│           ├── raw/
│           │   ├── raw_listings.csv
│           │   └── scrape_checkpoint.json
│           ├── processed/
│           │   ├── cleansed_listings.csv
│           │   ├── normalized_listings.cs
│           │   └── market_summary.csv
│           └── outputs/
│               ├── analysis/
│               │   ├── analysis_summary.csv
│               │   ├── ranked_parts_all.csv
│               │   ├── ranked_parts_top10.csv
│               │   └── eda_category_summary.csv
│               ├── hypothesis/
│               │   ├── hypothesis_test_results.csv
│               │   └── hypothesis_test_pairs.csv
│               ├── visuals/
│               │   ├── str_by_part.png
│               │   ├── price_vs_str.png
│               │   ├── opportunity_score_by_part.png
│               │   └── hypothesis_diff_distribution.png
│               ├── logs/
│               │   ├── pipeline_<run_id>.log
│               │   └── scrape_run.log
│               └── debug/
│                   └── ERROR_{year}_{make}_{model}_{part}_p{page}.html
│
├── outputs/
|   ├── hypothesis/
|   |   ├── hypothesis_test_results.csv
|   │   └── hypothesis_test_pairs.csv
│   └── visuals/
│       ├── str_by_part.png
│       ├── price_vs_str.png
│       ├── opportunity_score_by_part.png
|       └── hypothesis_diff_distribution.png
│
├── main.py                      # primary pipeline entry point
├── run_hypothesis_from_run_id.py # re-run hypothesis only from existing run
├── vis_test.py                  # rebuild visuals from existing run outputs
├── pytest.ini
├── requirements.txt
└── README.md
```

### **Project Outputs**

To provide evidence of a complete run of the pipeline, an /outputs directory has been added to the root of the repository. This directory contains the artifacts of a complete run of the pipeline.

While the raw datasets and run histories of the pipeline are not published in this repository, these outputs help to verify that the pipeline is capable of fulfilling its intended functions.

```text
outputs/  
├── hypothesis/  
│   ├── hypothesis_test_results.csv  
│   └── hypothesis_test_pairs.csv  
└── visuals/  
 ├── str_by_part.png  
 ├── price_vs_str.png  
 ├── opportunity_score_by_part.png  
 └── hypothesis_diff_distribution.png
```
The outputs of the pipeline indicate the results of each phase of the SalvageIQ pipeline, from the analytical data to the insights and visualizations of those results.

## Data Flow

Each pipeline run is fully isolated under a unique `run_id` (UUID). The orchestrator sequences stages and routes data through the folder structure above.

```
eBay (sold pass)    ──► raw_listings.csv
eBay (active pass)  ──► market_summary.csv
                            │
                      cleanse.py
                            │
                      cleansed_listings.csv
                            │
                      normalize.py
                            │
                      normalized_listings.csv
                            │
                      aggregation.py  ◄── market_summary.csv
                            │
                      analysis_summary.csv
                      ranked_parts_all.csv
                      ranked_parts_top10.csv
                            │
                      hypothesis_test.py (if enabled)
                            │
                      hypothesis_test_results.csv
                      hypothesis_test_pairs.csv
                            │
                      visuals.py (if hypothesis ran)
                            │
                      str_by_part.png
                      price_vs_str.png
                      opportunity_score_by_part.png
                      hypothesis_diff_distribution.png
```

**Sold and active are scraped as separate passes.** The sold pass writes to `raw_listings.csv` and feeds the full cleanse → normalize → analysis path. The active pass writes a compact market summary (`market_summary.csv`) that is joined to sold data during aggregation to compute sell-through rates.

## Key Design Decisions

### 1. Run-Isolated Directory Structure
Each run of the data analysis scripts will be performed within its own isolated directory. The unique `run_id` will allow for the isolation of each run’s results. This isolation will allow for the easy reference to a specific run of the application, and will prevent any run from overwriting the results of any other run.

### 2. Config-Driven Architecture
Most of the data within the project is contained within the config files. For example, the make, model, and year of each of the vehicles that will be analyzed is contained within the vehicles.py file. Additionally, the paths to each file is contained within the config files (such as in the ScrapeConfig dataclass). Thus, this structure allows for an easy modification of the application; no variables are defined outside of the application that would prevent a developer from being able to modify those variables.

### 3. Vehicle Year Authority
The application uses a dictionary to define the years in which each of the makes and models of vehicles is produced. The years that are used by the application to determine which years of each make and model will be analyzed are based on the intersection of the years that the makes and models are produced and the years that are defined in the application’s config file.

### 4. Taxonomy-Based Classification
The classification system that determines which parts on a vehicle are which part is based on a list of searchable terms for each part. For example, the alternator part includes the terms “alternator” as searchable terms, but excludes terms like “alternator rebuild kit.” These lists allow for flexibility in the search terms on eBay, as well as provide a method of easily modifying the classification of the vehicles’ parts.

### 5. Analysis Reuse Pattern
An important feature of the application is the ability to rerun the hypothesis and visualization modules of the application, while using the results of the previous runs of the application. This ability is made possible through the implementation of an `analysis_use_existing_summary` flag on the `analyze.py` script, and the ability of the hypothesis and visualization scripts to take an `input_run_id` and perform their analyses on that specific run of the application.

### 6. Resilience for Long-Running Jobs

The full scrape (10 vehicles × 9 years × 20 parts = 1,800 searches) takes approximately 10 hours. The pipeline is built to survive network interruptions:
-   Checkpoint/Resume support: The script will save the searches that have been completed during its run, so that if it is manually stopped, it can be started again to complete the searches that it had previously completed.
-   Browser Restart: The script will restart the browser at a set interval; running for too long may result in that browser session to time out on eBay, or to develop errors in the browser.
-   Randomized Page and Search Delays: To avoid detection by eBay of the automation of the browser for the purpose of data scraping, the script will randomly delay the actions of its automation scripts.
-   Debug HTML capture saves the raw page response on extraction failures for post-run inspection

## Run Modes

Defined in `config/config_builder.py`. All modes use the same main.py file with different scopes and flags.

### Full Run

All 10 vehicles, all 20 parts, all years (2012–2020). Approximately 1,800 sold searches + 1,800 active searches. **Expect ~10 hours to complete.**
```bash
python main.py
# or explicitly:
python main.py full
```

### Mini Run
Only 2 years and one vehicle (Toyota Camry) with the alternator and headlight parts selected for study. Hypothesis test enabled.

```bash
python main.py mini
```

### Test Run
One year, one vehicle (Toyota Camry), alternator part only, and one page max of search results.

```bash
python main.py test
```

### 1FullHypo Run
One year (2020), one vehicle (Ram 1500), and all 20 parts available for study. This mode is good for testing the heavier hypotheses or the full analysis output.

```bash
python main.py 1fullhypo
```

### EDA Run
One year, one vehicle (Toyota Camry), all parts, and the EDA output will be produced along with the standard analysis. The EDA output will be a `eda_category_summary.csv` file.

```bash
python main.py eda
```

### CSV Mode
Skip the scrape, cleanse, and normalize stages and load an existing `analysis_summary.csv` file from the analysis by entering the `run_id`. The `reset_outputs_on_run` option is disabled in this mode to preserve existing outputs.

```bash
python main.py csv <existing_run_id>
```

## Standalone Helper Scripts

### Re-run Hypothesis from Existing Run
This script will load the `analysis_summary.csv` file from the provided `run_id` and execute only the hypothesis test. The parts (A and B), the metric, and the alpha level are set at the top of the script.

```bash
python run_hypothesis_from_run_id.py
```
Edit the `RUN_ID` and hypothesis parameters at the top of the script prior to running.

### Rebuild Visuals from Existing Run
Rebuild all four charts based on the output from an existing run of the script without performing the main script stages again.

```bash
python vis_test.py
```
Replace the example `PUT_EXISTING_RUN_ID_HERE` with an actual run ID prior to running the script. If the placeholder is not replaced, a ValueError will be raised when attempting to run the script.

## Testing

### Overview
The test suite is for testing the entire project from start to orchestration. To run all tests:

```bash
pytest
```

To test without the integration tests (browser/ebay):

```bash
pytest -m "not integration"
```

### Test Structure
Each test script is contained in the following structure:
```text
tests/
├── smoke/
│   ├── test_imports.py            # all core modules import without error
│   ├── test_config_build.py       # ScrapeConfig builds correctly for each mode
│   ├── test_runner_smoke.py       # scrape runner executes and returns expected shape [integration]
│   ├── test_wrangle_smoke.py      # cleanse → normalize produces correct output
│   └── test_analyze_smoke.py      # analysis stage reads inputs and writes expected CSV
├── unit/
│   ├── test_normalize_token.py    # token normalization
│   ├── test_standardize_make.py   # make name standardization
│   ├── test_standardize_model.py  # model name standardization
│   ├── test_standardize_part.py   # part name standardization
│   ├── test_classify_part.py      # taxonomy classification
│   ├── test_category_from_part.py # category resolution
│   ├── test_deduplicate_listings.py # URL canonicalization and deduplication
│   ├── test_run_normalization.py  # full normalization pipeline
│   ├── test_ranking.py            # ranking and vehicle scoring
│   └── test_output_schemas.py     # output column contract validation
├── test_aggregation.py            # sold + active aggregation, STR, flags, scoring
└── test_orchestrator_flags.py     # orchestrator stage routing with mocked stages
```
Integration tests include tests for browsing and Ebay API calls. All other tests are independent of other scripts.

## Assumptions
 - That the sell-through is only an estimate of the true sell-through rate
 - That the active listings are only a snapshot of the active listings at one time
 - That the sold listings are representative of the past 90 days of eBay sales
 - That the data on eBay can be imprecise - the titles of the vehicles may differ, the price may vary, and the vehicles may be listed on multiple search result pages

The main goal of the project is to provide consistency and comparisons between the different parts listed on eBay

## Future Improvements
 - Expand the part taxonomy to include additional categories or to exclude additional subcategories within existing categories
 - Increase the number of makes and models of vehicles included in the project
 - Provide the trim levels of the models of vehicles
 - Perform analyses of the trend of certain parts over time by comparing different analysis runs
 - Determine the profit for each part by including time and cost estimates for each part
 - Provide an interface to lookup recommendations for vehicles based on their VIN

## Bottom Line
The project transforms the statement:

> "I think this part might sell"

into:

> "Based on real market data, these parts give you the best chance for success."

## Author

Andrew Montalbano  
Student ID: 012821411  
D502 — Capstone — WGU
