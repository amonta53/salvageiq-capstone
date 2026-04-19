# =========================================================
# runner.py
#
# Purpose:
#     Main Playwright scrape runner for SalvageIQ raw listing collection.
#
# Responsibilities:
#     1. Execute configured eBay searches across vehicle/part combinations
#     2. Extract raw listing rows and append them to the raw CSV
#     3. Capture run-level and search-level provenance fields
#        including run_id, scrape_ts, and pass_type
#     4. Support checkpoint/resume, browser restarts, and debug HTML capture
#
# Notes:
#     - This runner favors scrape resilience over overly granular exception handling
#     - Weak first-page results can short-circuit the remaining pages for a search
#     - Static selectors live in config.extraction_rules
#     - run_id is assigned once at pipeline start and passed in through config
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
import random
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from config.extraction_rules import (
    LISTING_URL_SELECTORS,
    PRICE_SELECTORS,
    RESULT_ROW_SELECTORS,
    SUBTITLE_SELECTORS,
    TITLE_SELECTORS,
)
from config.schema import MARKET_SUMMARY_COLUMNS, RAW_COLUMNS
from config.scrape_config import ScrapeConfig
from scrape.extractors import extract_first_attr, extract_first_text, looks_like_junk_title, extract_result_count
from scrape.search_builder import build_execution_key, build_search_key, build_search_url
from utils.checkpoint_utils import append_completed_search, load_completed_searches
from utils.io_utils import append_dataframe_to_csv, ensure_csv_with_headers, ensure_directory, save_text, append_row_to_csv
from utils.logging_utils import RunLogger, format_elapsed_hhmmss


# =========================================================
# Runtime state
# =========================================================

@dataclass(slots=True)
class ScrapeStats:
    """
    Track basic runtime stats for a scrape run.

    These counters are operational only. They help monitor scrape progress,
    page volume, and row collection during the current pipeline execution.
    """
    run_start: float
    total_rows: int = 0
    total_searches_run: int = 0
    total_pages_loaded: int = 0
    next_progress_report: int = 50


# =========================================================
# Sleep and page helpers
# =========================================================

def rand_sleep(min_s: float, max_s: float) -> None:
    """Sleep for a random interval within the provided range."""
    time.sleep(random.uniform(min_s, max_s))


def save_debug_html(page: Page, filepath: Path) -> None:
    """Persist the current page HTML for scrape debugging."""
    save_text(filepath, page.content())


def create_browser_session(playwright: Playwright, config: ScrapeConfig) -> tuple[Browser, BrowserContext, Page]:
    """Create a new Playwright browser, context, and page."""
    browser = playwright.chromium.launch(headless=config.headless)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/133.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1440, "height": 900},
        locale="en-US",
    )
    page = context.new_page()
    return browser, context, page


def close_browser_session(browser: Browser | None, context: BrowserContext | None) -> None:
    """Close the active browser context and browser."""
    if context is not None:
        context.close()
    if browser is not None:
        browser.close()


# =========================================================
# Extraction
# =========================================================

def scrape_page_rows(
    page: Page,
    search_year: int,
    search_make: str,
    search_model: str,
    search_part: str,
    search_url: str,
    page_num: int,
    run_id: str,
    scrape_ts: str,
    pass_type: str,
    logger: RunLogger,
) -> list[dict[str, str | int | None]]:
    """
    Extract usable listing rows from the current search results page.

    Metadata fields added to each row:
    - run_id: identifies the full pipeline execution
    - scrape_ts: timestamp for the current search snapshot
    - pass_type: distinguishes sold vs all search passes

    scrape_ts should be generated once per search execution, not once per row,
    so all rows from the same search snapshot carry the same time marker.
    """
    rows = None
    row_count = 0

    # eBay layout shifts sometimes, so keep fallback row selectors.
    for row_selector in RESULT_ROW_SELECTORS:
        rows = page.locator(row_selector)
        row_count = rows.count()
        if row_count > 0:
            break

    logger.log(f"  Rows found on page {page_num}: {row_count}")

    extracted: list[dict[str, str | int | None]] = []

    for row_index in range(row_count):
        row = rows.nth(row_index)

        try:
            raw_text = row.inner_text()
        except Exception:
            raw_text = None

        title = extract_first_text(row, TITLE_SELECTORS)
        price_raw = extract_first_text(row, PRICE_SELECTORS)
        listing_url = extract_first_attr(row, LISTING_URL_SELECTORS, "href")
        subtitle = extract_first_text(row, SUBTITLE_SELECTORS)

        if looks_like_junk_title(title):
            continue

        if not title or not price_raw:
            continue

        extracted.append(
            {
                "run_id": run_id,
                "scrape_ts": scrape_ts,
                "pass_type": pass_type,
                "search_year": search_year,
                "search_make": search_make,
                "search_model": search_model,
                "search_part": search_part,
                "search_url": search_url,
                "search_page": page_num,
                "title": title,
                "price_raw": price_raw,
                "subtitle": subtitle,
                "listing_url": listing_url,
                "raw_text": raw_text,
            }
        )

    return extracted


# =========================================================
# Main scrape pipeline
# =========================================================

def run_scrape(config: ScrapeConfig) -> dict[str, int]:
    """
    Run the raw scrape stage and return basic scrape totals.

    Flow:
    1. Prepare output folders and CSV headers
    2. Resume prior work if checkpointing is enabled
    3. Iterate configured vehicle/part search combinations
    4. Capture one scrape timestamp per search execution
    5. Write either market summary rows or raw listing rows
    6. Persist completed searches for resume support
    """
    ensure_directory(config.run_dir)
    if config.save_debug_html:
        ensure_directory(config.debug_dir)

    ensure_csv_with_headers(config.raw_csv_path, RAW_COLUMNS)
    ensure_csv_with_headers(config.market_summary_csv_path, MARKET_SUMMARY_COLUMNS)

    logger = RunLogger(config.scrape_log_path)
    completed_searches = load_completed_searches(config.checkpoint_path) if config.enable_resume else set()

    stats = ScrapeStats(
        run_start=time.time(),
        next_progress_report=config.progress_report_interval,
    )

    total_models = sum(len(models) for models in config.make_model_map.values())
    total_years = config.end_year - config.start_year + 1
    total_parts = len(config.parts)
    total_searches = total_models * total_years * total_parts
    search_counter = 0

    logger.log("=" * 72)
    logger.log("STARTING SCRAPE RUN")
    logger.log(f"Run ID: {config.run_id}")
    logger.log(f"Search scope: {config.search_scope}")
    logger.log(f"Raw CSV path: {config.raw_csv_path}")
    logger.log(f"Log path: {config.log_path}")
    logger.log(f"Checkpoint path: {config.checkpoint_path}")
    logger.log(f"Total potential searches: {total_searches}")
    logger.log(f"Headless mode: {config.headless}")
    logger.log("=" * 72)

    with sync_playwright() as playwright:
        browser, context, page = create_browser_session(playwright, config)

        try:
            for make, models in config.make_model_map.items():
                for model in models:
                    for year in range(config.start_year, config.end_year + 1):
                        for part in config.parts:
                            search_key = build_search_key(year, make, model, part)

                            execution_key = build_execution_key(
                                year,
                                make,
                                model,
                                part,
                                config.search_scope,
                            )

                            if config.enable_resume and execution_key in completed_searches:
                                continue

                            search_counter += 1
                            stats.total_searches_run += 1

                            elapsed_seconds = time.time() - stats.run_start
                            elapsed = format_elapsed_hhmmss(elapsed_seconds)
                            progress_pct = (search_counter / total_searches) * 100 if total_searches else 0.0

                            avg_seconds_per_search = (
                                elapsed_seconds / search_counter if search_counter else 0.0
                            )
                            remaining_searches = total_searches - search_counter
                            eta_seconds = remaining_searches * avg_seconds_per_search
                            eta = format_elapsed_hhmmss(eta_seconds)

                            logger.log(
                                f"[SEARCH {search_counter}/{total_searches} | "
                                f"{progress_pct:.1f}% | Elapsed {elapsed} | ETA {eta}] "
                                f"{config.search_scope.upper()} | {year} {make} {model} {part}"
                            )

                            if stats.total_searches_run % config.browser_restart_interval == 0:
                                logger.log(f"[BROWSER] Restarting browser session at search {stats.total_searches_run}")
                                close_browser_session(browser, context)
                                browser, context, page = create_browser_session(playwright, config)

                            # Small pre-search stagger so we do not hammer requests back-to-back.
                            rand_sleep(config.search_delay_min, config.search_delay_max)

                            # Capture one timestamp for this search execution so all rows
                            # from the same sold/all snapshot share the same scrape_ts.
                            scrape_ts = datetime.now(timezone.utc).isoformat()

                            first_page_row_count = 0

                            for page_num in range(1, config.max_pages_per_search + 1):
                                search_url = build_search_url(year, make, model, part, config, page_num)
                                logger.log(f"  Loading page {page_num}: {search_url}")

                                try:
                                    page.goto(search_url, wait_until="domcontentloaded", timeout=config.goto_timeout_ms)

                                    if config.search_scope == "all":
                                        result_count = extract_result_count(page)

                                        summary_row = {
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
                                            "search_url": search_url,
                                            "result_count": result_count,
                                            "page_count_observed": None,
                                        }

                                        append_row_to_csv(
                                            config.market_summary_csv_path,
                                            summary_row,
                                            MARKET_SUMMARY_COLUMNS,
                                        )

                                        logger.log(f"  Market summary saved. Result count: {result_count}")
                                        break

                                    stats.total_pages_loaded += 1
                                    rand_sleep(config.page_delay_min, config.page_delay_max)

                                    page_rows = scrape_page_rows(
                                        page=page,
                                        search_year=year,
                                        search_make=make,
                                        search_model=model,
                                        search_part=part,
                                        search_url=search_url,
                                        page_num=page_num,
                                        run_id=config.run_id,
                                        scrape_ts=scrape_ts,
                                        pass_type=config.search_scope,
                                        logger=logger,
                                    )

                                    if page_num == 1:
                                        first_page_row_count = len(page_rows)

                                    if page_rows:
                                        page_df = pd.DataFrame(page_rows)
                                        append_dataframe_to_csv(page_df, config.raw_csv_path)
                                        stats.total_rows += len(page_rows)
                                        logger.log(f"  Saved {len(page_rows)} rows from page {page_num}.")

                                        while stats.total_rows >= stats.next_progress_report:
                                            rows_elapsed = format_elapsed_hhmmss(time.time() - stats.run_start)
                                            logger.log(
                                                f"[ROWS] {stats.total_rows} rows collected | "
                                                f"Elapsed {rows_elapsed} | Pages loaded {stats.total_pages_loaded}"
                                            )
                                            stats.next_progress_report += config.progress_report_interval
                                    else:
                                        logger.log("  No usable rows found on this page.")
                                        if config.save_debug_html:
                                            debug_file = config.build_error_html_path(
                                                year=year,
                                                make=make,
                                                model=model,
                                                part=part,
                                                page_num=page_num,
                                            )
                                            save_debug_html(page, debug_file)
                                            logger.log(f"  Debug HTML saved: {debug_file.name}")

                                except Exception as exc:
                                    logger.log(f"  ERROR on {search_url}: {exc}")
                                    if config.save_debug_html:
                                        debug_file = config.build_error_html_path(
                                            year=year,
                                            make=make,
                                            model=model,
                                            part=part,
                                            page_num=page_num,
                                        )
                                        save_debug_html(page, debug_file)
                                        logger.log(f"  Error HTML saved: {debug_file.name}")

                                if page_num == 1 and first_page_row_count < config.weak_result_skip_threshold:
                                    logger.log(
                                        f"  Weak first page result ({first_page_row_count} rows) - "
                                        f"skipping remaining pages for this search."
                                    )
                                    break
      
                                if page_num < config.max_pages_per_search:
                                    rand_sleep(config.next_page_delay_min, config.next_page_delay_max)

                            if config.enable_resume:
                                append_completed_search(config.checkpoint_path, execution_key)
                                completed_searches.add(execution_key)

        finally:
            close_browser_session(browser, context)

    elapsed = format_elapsed_hhmmss(time.time() - stats.run_start)
    logger.log("=" * 72)
    logger.log(
        f"SCRAPE COMPLETE | Run ID={config.run_id} | Rows={stats.total_rows} | "
        f"Searches run={stats.total_searches_run} | Elapsed={elapsed}"
    )
    logger.log("=" * 72)

    return {
        "total_rows": stats.total_rows,
        "total_searches_run": stats.total_searches_run,
        "total_pages_loaded": stats.total_pages_loaded,
    }