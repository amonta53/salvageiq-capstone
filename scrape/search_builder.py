# =========================================================
# search_builder.py
# Search key and eBay search URL builders for scrape runs.
#
# Purpose:
# - Builds consistent search URLs from vehicle and part inputs
# - Builds stable search keys for checkpoint/resume tracking
#
# Notes:
# - URL options are driven by ScrapeConfig flags
# - Search keys should remain stable once checkpoint files exist
# =========================================================
from __future__ import annotations

from urllib.parse import quote_plus

from config.extraction_rules import EBAY_BASE_SEARCH_URL, SEARCH_KEY_DELIMITER
from config.scrape_config import ScrapeConfig


# =========================================================
# Search URL helpers
# =========================================================


def build_search_url(
    year: int,
    make: str,
    model: str,
    part: str,
    config: ScrapeConfig,
    page_num: int = 1,
) -> str:
    """Build an eBay search URL for a specific year/make/model/part query."""
    query = f"{year} {make} {model} {part}"
    url = f"{EBAY_BASE_SEARCH_URL}?_nkw={quote_plus(query)}"

    if config.search_scope == "sold":
        url += "&LH_Sold=1&LH_Complete=1"

    if config.used_only:
        url += "&LH_ItemCondition=3000"

    if page_num > 1:
        url += f"&_pgn={page_num}"

    return url



def build_search_key(year: int, make: str, model: str, part: str) -> str:
    """Build a stable checkpoint key for a single search unit."""
    return SEARCH_KEY_DELIMITER.join([str(year), make, model, part])



def build_execution_key(
    year: int,
    make: str,
    model: str,
    part: str,
    search_scope: str,
) -> str:
    """Build a scope-aware execution key for checkpoint tracking."""
    return SEARCH_KEY_DELIMITER.join(
        [str(year), make, model, part, search_scope]
    )