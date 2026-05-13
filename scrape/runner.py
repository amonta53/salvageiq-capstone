# =========================================================
# runner.py
#
# Purpose:
#     Playwright-based scrape runner for SalvageIQ raw listing collection.
#     Uses a headless Chromium browser to handle eBay's DataDome JS challenge
#     interstitial, which blocks pure HTTP clients (httpx, requests, curl).
#
# Responsibilities:
#     1. Execute configured eBay searches across vehicle/part combinations
#        concurrently using asyncio.gather + a Semaphore
#     2. Extract raw listing rows from the captured HTML
#     3. Capture run-level and search-level provenance fields
#     4. Support checkpoint/resume
#
# Notes:
#     - eBay serves a DataDome "Pardon Our Interruption" JS challenge to
#       non-browser HTTP clients.  Playwright (headless Chromium) executes
#       the challenge JS naturally, obtains the datadome cookie, and gets
#       redirected to the real search results.
#     - HTML parsing stays with BeautifulSoup — Playwright just captures the
#       final rendered HTML after all redirects complete.
#     - All searches for a given pass (sold/all) run concurrently up to
#       _MAX_CONCURRENCY simultaneous browser pages.
#     - run_scrape() is the sync entry point; it bridges to asyncio internally.
# =========================================================

from __future__ import annotations

import asyncio
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import Browser, BrowserContext, async_playwright

from config.extraction_rules import RESULT_ROW_SELECTORS
from config.schema import MARKET_SUMMARY_COLUMNS, RAW_COLUMNS
from config.scrape_config import ScrapeConfig
from scrape.extractors import clean_text, looks_like_junk_title
from scrape.search_builder import build_execution_key, build_search_key, build_search_url
from utils.checkpoint_utils import append_completed_search, load_completed_searches
from utils.io_utils import ensure_directory
from utils.logging_utils import RunLogger, format_elapsed_hhmmss


# =========================================================
# Constants
# =========================================================

# Concurrent page cap.
# Two pages share a single browser context (same session cookies), which means
# the DataDome cookie obtained on the warm-up is reused by all searches.
# More than 2-3 simultaneous pages starts to look like bot traffic.
_MAX_CONCURRENCY = 2

# Markers that indicate eBay served a bot-detection page instead of results.
_BOT_BLOCK_MARKERS = [
    "<title>Access Denied</title>",
    "<h1>Access Denied</h1>",
    "Pardon Our Interruption",   # DataDome JS challenge interstitial
    "verify you are a human",
    "verify you're not a robot",
    "Please complete the security check",
    "robot check",
    "g-recaptcha",
    "errors.edgesuite.net",
]

_EBAY_HOME_URL = "https://www.ebay.com"

# Stealth init script — patches the most common headless-Chrome fingerprinting
# signals before any page JS runs.  DataDome checks navigator.webdriver and
# a handful of other properties; removing them greatly reduces challenge rate.
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
window.chrome = { runtime: {} };
"""


# =========================================================
# Runtime stats
# =========================================================

@dataclass(slots=True)
class ScrapeStats:
    """Track basic runtime totals for a scrape run."""
    run_start: float
    total_rows: int = 0
    total_searches_run: int = 0
    total_pages_loaded: int = 0


# =========================================================
# BeautifulSoup extraction helpers
# =========================================================

def _bs_first_text(tag: Any, selectors: list[str]) -> str | None:
    """
    Return the first non-empty text match from a list of CSS selectors.

    Handles Playwright-style :has-text() pseudo-selectors by converting them
    to a manual find_all scan, since BS4 does not support that pseudo-class.
    """
    for sel in selectors:
        if ":has-text(" in sel:
            # e.g. 'span:has-text("$")' — find any matching tag whose text contains the value
            m = re.match(r'^(\w+)?:has-text\("([^"]+)"\)$', sel)
            if m:
                tag_name = m.group(1) or True
                search_text = m.group(2)
                for el in tag.find_all(tag_name):
                    t = clean_text(el.get_text())
                    if t and search_text in t:
                        return t
            continue

        try:
            el = tag.select_one(sel)
            if el:
                t = clean_text(el.get_text())
                if t:
                    return t
        except Exception:
            continue

    return None


def _bs_first_attr(tag: Any, selectors: list[str], attr: str) -> str | None:
    """Return the first non-empty attribute value from a list of CSS selectors."""
    for sel in selectors:
        if ":has-text(" in sel:
            continue  # attribute extraction on :has-text is unsupported
        try:
            el = tag.select_one(sel)
            if el and el.has_attr(attr):
                val = clean_text(el[attr])
                if val:
                    return val
        except Exception:
            continue
    return None


def _is_bot_block_page(html: str) -> bool:
    """Return True if the HTML looks like a bot-detection or access-denied page."""
    return any(marker in html for marker in _BOT_BLOCK_MARKERS)


def _extract_result_count_bs(soup: BeautifulSoup) -> int | None:
    """Extract total active-listing result count from an eBay search results page."""
    try:
        el = soup.select_one("h1.srp-controls__count-heading")
        if el:
            m = re.search(r"([\d,]+)", el.get_text())
            if m:
                return int(m.group(1).replace(",", ""))
    except Exception:
        pass
    return None


def _extract_rows_from_page(
    soup: BeautifulSoup,
    year: int,
    make: str,
    model: str,
    part: str,
    search_url: str,
    page_num: int,
    run_id: str,
    scrape_ts: str,
    pass_type: str,
) -> list[dict[str, Any]]:
    """
    Extract usable listing rows from a parsed eBay search results page.

    Returns a list of row dicts whose keys match RAW_COLUMNS.
    """
    # Try each row container selector in priority order
    item_tags: list = []
    for sel in RESULT_ROW_SELECTORS:
        item_tags = soup.select(sel)
        if item_tags:
            break

    extracted: list[dict[str, Any]] = []

    for row in item_tags:
        # --- Title ---
        title = _bs_first_text(row, [
            '[role="heading"]',
            ".s-item__title",
            "a span",
            "a",
            'div[role="heading"]',
        ])

        if looks_like_junk_title(title):
            continue

        # --- Price ---
        price_raw = _bs_first_text(row, [".s-item__price"])
        if not price_raw:
            # Fallback: any short span/div containing "$"
            for el in row.find_all(["span", "div"]):
                t = clean_text(el.get_text())
                if t and "$" in t and len(t) < 40:
                    price_raw = t
                    break

        if not title or not price_raw:
            continue

        # --- Subtitle ---
        subtitle = _bs_first_text(row, [
            ".s-item__subtitle",
            ".SECONDARY_INFO",
            ".s-item__dynamic",
            ".s-item__details",
            ".s-item__caption-section",
        ])

        # --- Listing URL ---
        listing_url = _bs_first_attr(row, ["a"], "href")

        # --- Raw text for downstream guess heuristics ---
        raw_text = clean_text(row.get_text(separator=" "))

        extracted.append({
            "run_id": run_id,
            "scrape_ts": scrape_ts,
            "pass_type": pass_type,
            "search_year": year,
            "search_make": make,
            "search_model": model,
            "search_part": part,
            "search_url": search_url,
            "search_page": page_num,
            "title": title,
            "price_raw": price_raw,
            "subtitle": subtitle,
            "listing_url": listing_url,
            "raw_text": raw_text,
        })

    return extracted


# =========================================================
# Playwright page fetch
# =========================================================

async def _fetch_page(
    context: BrowserContext,
    url: str,
    logger: RunLogger,
    retries: int = 3,
) -> str | None:
    """
    Navigate to a URL using a new Playwright page and return the final HTML.

    Each call creates and closes its own page so pages don't accumulate.
    The shared BrowserContext passes session cookies (including the DataDome
    cookie obtained during warm-up) to every request automatically.

    Returns None if the page can't be fetched or bot-block persists after retries.
    """
    for attempt in range(1, retries + 2):
        page = await context.new_page()
        try:
            await page.add_init_script(_STEALTH_SCRIPT)
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            # Give DataDome's JS puzzle time to run and redirect if needed.
            await asyncio.sleep(random.uniform(1.5, 3.0))

            html = await page.content()

            if _is_bot_block_page(html):
                wait = random.uniform(3.0, 6.0) * attempt
                logger.log(
                    f"  Bot-block page detected (attempt {attempt}) — "
                    f"retrying in {wait:.1f}s"
                )
                await page.close()
                if attempt <= retries:
                    await asyncio.sleep(wait)
                    continue
                logger.log(f"  Bot-block persisted after {retries + 1} attempts: {url}")
                return None

            return html

        except Exception as exc:
            await page.close()
            if attempt <= retries:
                wait = random.uniform(2.0, 5.0) * attempt
                logger.log(
                    f"  Fetch error (attempt {attempt}): {exc} — retrying in {wait:.1f}s"
                )
                await asyncio.sleep(wait)
            else:
                logger.log(f"  Fetch failed after {retries + 1} attempts: {url} — {exc}")
        else:
            await page.close()

    return None


# =========================================================
# Single search coroutine
# =========================================================

async def _scrape_one_search(
    sem: asyncio.Semaphore,
    context: BrowserContext,
    year: int,
    make: str,
    model: str,
    part: str,
    config: ScrapeConfig,
    logger: RunLogger,
) -> tuple[list[dict], dict | None, int]:
    """
    Scrape all pages for a single year/make/model/part search.

    Returns (rows, summary_row, pages_loaded) where:
    - rows is populated for 'sold' pass and empty for 'all' pass
    - summary_row is populated for 'all' pass and None for 'sold' pass
    - pages_loaded is the number of pages successfully fetched
    """
    async with sem:
        scrape_ts = datetime.now(timezone.utc).isoformat()
        rows: list[dict] = []
        summary: dict | None = None
        pages_loaded = 0

        search_key = build_search_key(year, make, model, part)
        execution_key = build_execution_key(year, make, model, part, config.search_scope)

        logger.log(f"  [{config.search_scope.upper()}] {year} {make} {model} | {part}")

        for page_num in range(1, config.max_pages_per_search + 1):
            url = build_search_url(year, make, model, part, config, page_num)

            # Random jitter between pages to avoid looking like rapid-fire bot traffic
            await asyncio.sleep(random.uniform(0.5, 1.5))

            html = await _fetch_page(context, url, logger)
            if not html:
                break

            pages_loaded += 1
            soup = BeautifulSoup(html, "lxml")

            # ---- 'all' pass: grab result count and stop ----
            if config.search_scope == "all":
                result_count = _extract_result_count_bs(soup)
                summary = {
                    "run_id": config.run_id,
                    "scrape_ts": scrape_ts,
                    "pass_type": config.search_scope,
                    "search_key": search_key,
                    "execution_key": execution_key,
                    "search_scope": config.search_scope,
                    "search_year": year,
                    "search_make": make,
                    "search_model": model,
                    "search_part": part,
                    "search_url": url,
                    "result_count": result_count,
                    "page_count_observed": None,
                }
                logger.log(f"    Market summary: result_count={result_count}")
                break

            # ---- 'sold' pass: extract listing rows ----
            page_rows = _extract_rows_from_page(
                soup=soup,
                year=year,
                make=make,
                model=model,
                part=part,
                search_url=url,
                page_num=page_num,
                run_id=config.run_id,
                scrape_ts=scrape_ts,
                pass_type=config.search_scope,
            )

            logger.log(f"    Page {page_num}: {len(page_rows)} rows")
            rows.extend(page_rows)

            # Weak first-page guard: skip further pages when results are sparse.
            # Log an HTML snippet so we can diagnose selector mismatches vs real empties.
            if page_num == 1 and len(page_rows) < config.weak_result_skip_threshold:
                html_preview = html[:500].replace("\n", " ").strip()
                logger.log(
                    f"    Weak first page ({len(page_rows)} rows) — skipping remaining pages."
                )
                logger.log(f"    HTML preview: {html_preview}")
                break

        return rows, summary, pages_loaded


# =========================================================
# Async orchestration
# =========================================================

async def _run_scrape_async(
    config: ScrapeConfig,
    logger: RunLogger,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """
    Core async implementation: build all search tasks, run them concurrently,
    collect results, and return DataFrames in memory.

    Uses a single shared BrowserContext so the DataDome cookie obtained during
    warm-up is reused by all search pages within the same run.
    """
    completed_searches = (
        load_completed_searches(config.checkpoint_path) if config.enable_resume else set()
    )

    # Build the full list of (year, make, model, part) tuples to search
    tasks: list[tuple[int, str, str, str]] = []
    for make, models in config.make_model_map.items():
        for model in models:
            for year in range(config.start_year, config.end_year + 1):
                for part in config.parts:
                    execution_key = build_execution_key(
                        year, make, model, part, config.search_scope
                    )
                    if config.enable_resume and execution_key in completed_searches:
                        continue
                    tasks.append((year, make, model, part))

    logger.log(f"Search tasks: {len(tasks)} (scope={config.search_scope})")

    sem = asyncio.Semaphore(_MAX_CONCURRENCY)

    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context: BrowserContext = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/133.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
            viewport={"width": 1366, "height": 768},
            java_script_enabled=True,
        )

        # ---- Session warm-up ----
        # Visit eBay's homepage so DataDome can fingerprint the browser and
        # issue its session cookie before any search requests start.
        # Subsequent pages from the same context carry that cookie automatically.
        logger.log("Warming session via eBay homepage …")
        warmup_page = await context.new_page()
        await warmup_page.add_init_script(_STEALTH_SCRIPT)
        try:
            await warmup_page.goto(_EBAY_HOME_URL, wait_until="domcontentloaded", timeout=30_000)
            await asyncio.sleep(random.uniform(2.0, 4.0))
            logger.log(f"  Warm-up complete: {warmup_page.url}")
        except Exception as exc:
            logger.log(f"  Warm-up failed (continuing anyway): {exc}")
        finally:
            await warmup_page.close()

        coroutines = [
            _scrape_one_search(sem, context, year, make, model, part, config, logger)
            for year, make, model, part in tasks
        ]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        await context.close()
        await browser.close()

    # Collect results from all completed tasks
    all_rows: list[dict] = []
    all_summaries: list[dict] = []
    total_pages = 0

    for i, result in enumerate(results):
        year, make, model, part = tasks[i]

        if isinstance(result, Exception):
            logger.log(f"  Exception for {year} {make} {model} | {part}: {result}")
            continue

        rows, summary, pages = result
        all_rows.extend(rows)
        total_pages += pages

        if summary:
            all_summaries.append(summary)

        # Checkpoint each completed search
        if config.enable_resume:
            execution_key = build_execution_key(
                year, make, model, part, config.search_scope
            )
            append_completed_search(config.checkpoint_path, execution_key)

    raw_df = (
        pd.DataFrame(all_rows).reindex(columns=RAW_COLUMNS)
        if all_rows
        else pd.DataFrame(columns=RAW_COLUMNS)
    )
    market_df = (
        pd.DataFrame(all_summaries).reindex(columns=MARKET_SUMMARY_COLUMNS)
        if all_summaries
        else pd.DataFrame(columns=MARKET_SUMMARY_COLUMNS)
    )
    stats = {
        "total_rows": len(all_rows),
        "total_searches_run": len(tasks),
        "total_pages_loaded": total_pages,
    }
    return raw_df, market_df, stats


# =========================================================
# Public entry point (sync, for orchestrator compatibility)
# =========================================================

def run_scrape(config: ScrapeConfig) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """
    Run the raw scrape stage and return results in memory.

    This is the sync entry point called by the pipeline orchestrator.
    It bridges to the async implementation via asyncio.run().

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, dict]
        raw_df:    Sold listing rows (RAW_COLUMNS schema)
        market_df: Active market snapshot rows (MARKET_SUMMARY_COLUMNS schema)
        stats:     {"total_rows", "total_searches_run", "total_pages_loaded"}

    Flow:
    1. Create logs directory and open run logger
    2. Resume prior checkpoint if enabled
    3. Warm browser session via eBay homepage (DataDome cookie acquisition)
    4. Run all part searches concurrently with bounded parallelism
    5. Return collected DataFrames and stats (no CSV I/O)
    """
    run_start = time.time()

    # Only the logs directory needs to exist — all data stays in memory
    ensure_directory(config.logs_dir)

    logger = RunLogger(config.scrape_log_path)

    logger.log("=" * 72)
    logger.log("STARTING SCRAPE RUN  [Playwright / Chromium]")
    logger.log(f"Run ID:  {config.run_id}")
    logger.log(f"Scope:   {config.search_scope}")
    logger.log(f"Log:     {config.scrape_log_path}")
    logger.log("=" * 72)

    raw_df, market_df, totals = asyncio.run(_run_scrape_async(config, logger))

    elapsed = format_elapsed_hhmmss(time.time() - run_start)
    logger.log("=" * 72)
    logger.log(
        f"SCRAPE COMPLETE | Run ID={config.run_id} | "
        f"Rows={totals['total_rows']} | "
        f"Searches={totals['total_searches_run']} | "
        f"Pages={totals['total_pages_loaded']} | "
        f"Elapsed={elapsed}"
    )
    logger.log("=" * 72)

    return raw_df, market_df, totals
