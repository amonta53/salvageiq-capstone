# =========================================================
# test_deduplicate_listings.py
#
# Purpose:
#     Unit tests for deduplicate_listings in normalize.py.
#
# Notes:
#     These tests verify URL-based deduplication, fallback behavior
#     for missing URLs, and defensive validation of required columns.
# =========================================================

import pandas as pd
import pytest

from wrangle.normalize import deduplicate_listings


def test_deduplicate_listings_collapses_same_listing_url() -> None:
    """
    deduplicate_listings should collapse rows that share the same listing_url.
    """
    df = pd.DataFrame(
        [
            {
                "listing_url": "https://example.com/item1",
                "title": "OEM alternator",
                "price": 100.00,
                "search_make_std": "Toyota",
                "search_model_std": "Camry",
                "search_part_std": "alternator",
            },
            {
                "listing_url": "https://example.com/item1",
                "title": "OEM alternator duplicate",
                "price": 100.00,
                "search_make_std": "Toyota",
                "search_model_std": "Camry",
                "search_part_std": "alternator",
            },
            {
                "listing_url": "https://example.com/item2",
                "title": "OEM headlight",
                "price": 150.00,
                "search_make_std": "Toyota",
                "search_model_std": "Camry",
                "search_part_std": "headlight",
            },
        ]
    )

    deduped_df, dedup_stats = deduplicate_listings(df)

    assert len(deduped_df) == 2
    assert dedup_stats["before_count"] == 3
    assert dedup_stats["after_count"] == 2
    assert dedup_stats["removed_count"] == 1


def test_deduplicate_listings_keeps_different_urls() -> None:
    """
    deduplicate_listings should preserve rows with different listing URLs.
    """
    df = pd.DataFrame(
        [
            {
                "listing_url": "https://example.com/item1",
                "title": "OEM alternator",
                "price": 100.00,
                "search_make_std": "Toyota",
                "search_model_std": "Camry",
                "search_part_std": "alternator",
            },
            {
                "listing_url": "https://example.com/item2",
                "title": "OEM alternator",
                "price": 100.00,
                "search_make_std": "Toyota",
                "search_model_std": "Camry",
                "search_part_std": "alternator",
            },
        ]
    )

    deduped_df, dedup_stats = deduplicate_listings(df)

    assert len(deduped_df) == 2
    assert dedup_stats["removed_count"] == 0


def test_deduplicate_listings_uses_fallback_when_url_is_blank() -> None:
    """
    deduplicate_listings should use the fallback key when listing_url is blank.
    """
    df = pd.DataFrame(
        [
            {
                "listing_url": "",
                "title": "OEM alternator",
                "price": 100.00,
                "search_make_std": "Toyota",
                "search_model_std": "Camry",
                "search_part_std": "alternator",
            },
            {
                "listing_url": "",
                "title": "OEM alternator",
                "price": 100.00,
                "search_make_std": "Toyota",
                "search_model_std": "Camry",
                "search_part_std": "alternator",
            },
            {
                "listing_url": "",
                "title": "OEM alternator",
                "price": 110.00,
                "search_make_std": "Toyota",
                "search_model_std": "Camry",
                "search_part_std": "alternator",
            },
        ]
    )

    deduped_df, dedup_stats = deduplicate_listings(df)

    assert len(deduped_df) == 2
    assert dedup_stats["removed_count"] == 1


def test_deduplicate_listings_raises_when_listing_url_missing() -> None:
    """
    deduplicate_listings should raise an error when listing_url is missing.
    """
    df = pd.DataFrame(
        [
            {
                "title": "OEM alternator",
                "price": 100.00,
            }
        ]
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        deduplicate_listings(df)