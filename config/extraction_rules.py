# =========================================================
# extraction_rules.py
# Shared scrape extraction rules and static constants for SalvageIQ.
#
# Purpose:
# - Centralizes scrape-stage selectors, regex patterns, and static URL constants
# - Keeps runner, search builder, and extractors clean and focused on execution logic
#
# Notes:
# - These rules support scrape-stage extraction and heuristics
# - Runtime variables like delays, retries, and paths are in ScrapeConfig
# - Don’t mix taxonomy with scrape guess logic. Keep that stuff separate.
# =========================================================

from __future__ import annotations


# =========================================================
# Search and URL constants
# =========================================================

EBAY_BASE_SEARCH_URL = "https://www.ebay.com/sch/i.html"
SEARCH_KEY_DELIMITER = "|"


# =========================================================
# Result row and field selectors
# =========================================================

RESULT_ROW_SELECTORS = [
    ".srp-results li",
    ".srp-river-results li",
]

TITLE_SELECTORS = [
    '[role="heading"]',
    ".s-item__title",
    "a span",
    "a",
    'div[role="heading"]',
]

PRICE_SELECTORS = [
    ".s-item__price",
    'span:has-text("$")',
    'div:has-text("$")',
]

SUBTITLE_SELECTORS = [
    ".s-item__subtitle",
    ".SECONDARY_INFO",
    ".s-item__dynamic",
    ".s-item__details",
    ".s-item__caption-section",
]

LISTING_URL_SELECTORS = ["a"]


# =========================================================
# Extraction patterns and heuristics
# =========================================================

CONDITION_PATTERNS = [
    ("used", r"\bused\b"),
    ("new", r"\bnew\b"),
    ("remanufactured", r"\breman(?:ufactured)?\b"),
    ("for parts or not working", r"\bfor parts\b|\bnot working\b"),
    ("open box", r"\bopen box\b"),
    ("seller refurbished", r"\brefurbished\b"),
]

PART_NUMBER_PATTERNS = [
    r"\b\d{5}-\d{5}\b",
    r"\b[a-zA-Z]{1,4}\d{5,10}[a-zA-Z]{0,3}\b",
    r"\b[a-zA-Z0-9]{3,6}-[a-zA-Z0-9]{3,8}\b",
]

VEHICLE_GUESS_MAKES = [
    "toyota", "honda", "ford", "chevrolet", "chevy", "gmc", "nissan",
    "hyundai", "kia", "mazda", "subaru", "lexus", "acura", "jeep",
    "dodge", "chrysler", "bmw", "audi", "mercedes", "volkswagen", "vw",
]

VEHICLE_GUESS_MODELS = [
    "camry", "corolla", "rav4", "highlander", "tacoma", "tundra",
    "accord", "civic", "cr-v", "crv", "pilot", "f-150", "f150",
    "escape", "fusion", "silverado", "malibu", "equinox",
    "altima", "sentra", "rogue", "sonata", "elantra", "santa fe",
    "optima", "sorento", "soul", "mazda3", "cx-5", "cx5",
    "outback", "forester", "legacy", "wrangler", "grand cherokee",
]

PART_GUESS_PATTERNS = {
    "alternator": [r"\balternator\b", r"\balt\b"],
    "starter": [r"\bstarter\b"],
    "headlight": [r"\bheadlight\b", r"\bheadlamp\b"],
    "tail light": [r"\btaillight\b", r"\btail light\b", r"\btail lamp\b"],
    "side mirror": [r"\bside mirror\b", r"\bdoor mirror\b", r"\bmirror\b"],
    "radiator": [r"\bradiator\b"],
    "ac compressor": [r"\ba/c compressor\b", r"\bac compressor\b"],
    "ecu": [r"\becu\b", r"\becm\b", r"\bpcm\b", r"\bengine control module\b"],
}

JUNK_TITLE_MARKERS = [
    "shop on ebay",
    "results matching fewer words",
    "shop with confidence",
    "sponsored",
    "see all",
]
