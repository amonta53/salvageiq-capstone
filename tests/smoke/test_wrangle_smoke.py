# =========================================================
# test_wrangle_smoke.py
# Smoke test for raw-to-normalized wrangle flow
#
# Purpose:
# Verify the wrangle pipeline can read a tiny raw CSV,
# normalize listing fields, deduplicate rows, and write
# the expected normalized output.
# =========================================================

from pathlib import Path

import pandas as pd

from wrangle.normalize import run_normalization


def test_wrangle_smoke(tmp_path: Path) -> None:
    """
    Verify the normalization flow can process a tiny raw input file
    without relying on artifacts created by other tests.

    Why this matters:
    A smoke test should prove the wrangle layer still works end to end.
    It should not depend on test order, shared files, or prior runs.
    """
    raw_csv_path = tmp_path / "raw_test.csv"
    normalized_csv_path = tmp_path / "normalized_test.csv"

    raw_df = pd.DataFrame(
        [
            {
                "title": "2018 Toyota Camry Alternator OEM",
                "price": "$125.00",
                "item_url": "https://www.ebay.com/itm/12345?_trkparms=abc",
                "search_year": 2018,
                "search_make": "Toyota",
                "search_model": "Camry",
                "search_part": "alternator",
                "listing_status": "sold",
                "scrape_ts": "2026-04-10 10:00:00",
            },
            {
                "title": "2018 Toyota Camry Alternator OEM",
                "price": "$125.00",
                "item_url": "https://www.ebay.com/itm/12345?_trkparms=xyz",
                "search_year": 2018,
                "search_make": "TOYOTA",
                "search_model": "camry",
                "search_part": "alt",
                "listing_status": "sold",
                "scrape_ts": "2026-04-10 10:00:00",
            },
            {
                "title": "2018 Toyota Camry Headlight Assembly",
                "price": "$210.00",
                "item_url": "https://www.ebay.com/itm/99999",
                "search_year": 2018,
                "search_make": "Toyota",
                "search_model": "Camry",
                "search_part": "head light",
                "listing_status": "active",
                "scrape_ts": "2026-04-10 10:00:00",
            },
        ]
    )

    raw_df.to_csv(raw_csv_path, index=False)

    normalized_df = run_normalization(
        input_csv_path=raw_csv_path,
        output_csv_path=normalized_csv_path,
    )

    assert normalized_csv_path.exists()
    assert not normalized_df.empty

    # Duplicate URLs should collapse after canonicalization
    assert len(normalized_df) == 2

    alternator_row = normalized_df.loc[
        normalized_df["item_url"].str.contains("/itm/12345", na=False)
    ].iloc[0]

    assert alternator_row["search_make_std"] == "toyota"
    assert alternator_row["search_model_std"] == "camry"
    assert alternator_row["search_part_std"] == "alternator"

    headlight_row = normalized_df.loc[
        normalized_df["item_url"].str.contains("/itm/99999", na=False)
    ].iloc[0]

    assert headlight_row["search_part_std"] == "headlight"