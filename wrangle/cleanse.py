# =========================================================
# cleanse.py
#
# Purpose:
#     Transform raw scraped listing data into a cleaner, more structured
#     dataset that is ready for downstream validation, classification,
#     and analysis.
#
# High-level responsibilities:
#     1. Load the raw extract CSV
#     2. Normalize text-heavy fields
#     3. Build a combined text field for extractor logic
#     4. Derive cleansed / guessed attributes
#     5. Write the cleansed dataset to disk
#
# Notes:
#     - This step does not try to fully validate business rules.
#       It focuses on cleanup and lightweight validation.
#     - Extracted values are intentionally labeled as "guess" where
#       pproximation parsing is being used.
# =========================================================
from __future__ import annotations

import pandas as pd

from config.schema import CLEANSED_COLUMNS
from scrape.extractors import (
    clean_price,
    clean_text,
    extract_condition,
    extract_part_guess,
    extract_part_number,
    extract_shipping_text,
    extract_sold_date_guess,
    extract_vehicle_guess,
    extract_year_range,
    extract_years,
)
from utils.io_utils import ensure_csv_with_headers


# =========================================================
# DATA CLEANSING
# =========================================================


def run_cleansing(raw_csv_path, cleansed_csv_path) -> pd.DataFrame:
    """
    Run the cleansing step for raw scraped listing data.

    Parameters
    ----------
    raw_csv_path : str | Path
        File path to the raw extracted CSV.
    cleansed_csv_path : str | Path
        File path where the cleansed CSV should be written.

    Returns
    -------
    pd.DataFrame
        The cleansed DataFrame written to disk.

    Processing overview
    -------------------
    1. Ensure the cleansed output file exists with the expected header schema.
    2. Read the raw CSV into a DataFrame.
    3. Normalize key text columns used in parsing.
    4. Build a combined text blob from title, subtitle, and raw_text.
    5. Apply extractor functions to derive structured fields such as:
       - cleaned price
       - condition guess
       - sold date guess
       - shipping text
       - vehicle guess
       - part guess
       - part number guess
       - year range guess
       - explicit years found
    6. Save the transformed result to the cleansed CSV path.
    """

    # =========================================================
    #  --- Create output file with headers if it doesn't exist 
    # =========================================================
    ensure_csv_with_headers(cleansed_csv_path, CLEANSED_COLUMNS)

    df = pd.read_csv(raw_csv_path)

    ## Handle empty case by writing out an empty cleansed file with headers
    if df.empty: 
        df.to_csv(cleansed_csv_path, index=False)
        return df

    required_text_columns = ["title", "subtitle", "listing_url", "raw_text", "price_raw"]
    for column_name in required_text_columns: 
        if column_name in df.columns:
            df[column_name] = df[column_name].map(clean_text)

    ## Build a combined text field for use in extractors that look across multiple fields
    combined_series = (
        df[["title", "subtitle", "raw_text"]]
        .fillna("")
        .agg(" | ".join, axis=1)
        .str.strip(" |")
    )

    # =========================================================
    #  --- Normalize and extract fields using the combined text and raw price 
    # =========================================================
    df["price_clean"] = df["price_raw"].map(clean_price)
    df["condition_guess"] = combined_series.map(extract_condition)
    df["sold_date_guess"] = df["raw_text"].map(extract_sold_date_guess)
    df["shipping_text"] = df["raw_text"].map(extract_shipping_text)
    df["vehicle_guess"] = combined_series.map(extract_vehicle_guess)
    df["part_guess"] = combined_series.map(extract_part_guess)
    df["part_number_guess"] = combined_series.map(extract_part_number)
    df["year_range_guess"] = combined_series.map(extract_year_range)
    df["years_found"] = combined_series.map(extract_years)

    df.to_csv(cleansed_csv_path, index=False)
    return df
