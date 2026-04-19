# =========================================================
# taxonomy.py
# Part taxonomy, search terms, and normalization rules.
#
# Purpose:
# - Defines the standardized part categories used across the pipeline
# - Provides include/exclude matching rules for part classification
# - Supplies raw search terms used to build marketplace queries
#
# Design Notes:
# - Search terms are not the same thing as taxonomy categories
# - Taxonomy categories should remain stable for consistent analysis
# - Include/exclude rules are used to reduce false positives
# - Category priority resolves ambiguous multi-match listings
#
# Pipeline Role:
# - scrape: uses SEARCH_PART_TERMS to generate searches
# - cleanse: extracts rough text candidates from listings
# - normalize: maps raw text into standardized categories
# - analyze: groups and ranks listings by standardized category
# =========================================================


# =========================================================
# Standard part taxonomy
# Each category contains:
# - include: terms that support a match
# - exclude: terms that should suppress a match
# =========================================================

PART_TAXONOMY = {
    "Headlight Assembly": {
        "include": ["headlight", "head lamp", "headlamp", "lh headlight", "rh headlight"],
        "exclude": ["bulb", "bulbs"],
    },
    "Tail Light Assembly": {
        "include": ["tail light", "taillight", "rear lamp"],
        "exclude": ["bulb", "bulbs"],
    },
    "Side Mirror": {
        "include": ["mirror", "side mirror", "door mirror", "side view mirror"],
        "exclude": ["glass", "mirror glass"],
    },
    "Radio / Infotainment": {
        "include": ["radio", "stereo", "infotainment", "display screen", "console"],
        "exclude": ["wiring", "wire", "harness"],
    },
    "Instrument Cluster": {
        "include": ["cluster", "speedometer", "gauge cluster"],
        "exclude": ["individual gauge", "gauge only"],
    },
    "Alternator": {
        "include": ["alternator"],
        "exclude": ["rebuild kit", "rebuild kits"],
    },
    "Starter": {
        "include": ["starter", "starter motor"],
        "exclude": ["solenoid", "solenoids"],
    },
    "Engine Control Module": {
        "include": ["ecm", "ecu", "pcm", "engine computer"],
        "exclude": [],
    },
    "Transmission Control Module": {
        "include": ["tcm", "transmission computer"],
        "exclude": [],
    },
    "Wheel / Rim": {
        "include": ["wheel", "rim"],
        "exclude": ["tire", "tires"],
    },
    "Seat": {
        "include": ["driver seat", "passenger seat", "rear seat", "seat"],
        "exclude": ["seat cover", "seat covers"],
    },
    "Door Assembly": {
        "include": ["complete door", "door assembly", "door"],
        "exclude": ["door handle", "door handles"],
    },
    "Fender": {
        "include": ["fender"],
        "exclude": ["trim", "trim piece", "trim pieces"],
    },
    "Hood": {
        "include": ["hood"],
        "exclude": ["insulation", "insulation pad", "insulation pads"],
    },
    "Front Bumper Assembly": {
        "include": ["front bumper", "bumper cover"],
        "exclude": ["sensor", "sensors"],
    },
    "Rear Bumper Assembly": {
        "include": ["rear bumper"],
        "exclude": ["sensor", "sensors"],
    },
    "Grille": {
        "include": ["grille", "front grille"],
        "exclude": ["emblem", "emblems"],
    },
    "Window Regulator": {
        "include": ["window regulator", "power window motor", "window motor"],
        "exclude": ["switch", "switches"],
    },
    "AC Compressor": {
        "include": ["ac compressor", "air conditioning compressor"],
        "exclude": ["line", "lines", "hose", "hoses"],
    },
    "Steering Wheel": {
        "include": ["steering wheel"],
        "exclude": ["button", "buttons"],
    },
}

# =========================================================
# Category priority
# Used when a listing matches multiple categories.
# Higher-priority categories win.
# =========================================================
CATEGORY_PRIORITY = [
    "Engine Control Module",
    "Transmission Control Module",
    "Alternator",
    "Starter",
    "Instrument Cluster",
    "Radio / Infotainment",
    "Headlight Assembly",
    "Tail Light Assembly",
    "Side Mirror",
    "Wheel / Rim",
    "Seat",
    "Door Assembly",
    "Fender",
    "Hood",
    "Front Bumper Assembly",
    "Rear Bumper Assembly",
    "Grille",
    "Window Regulator",
    "AC Compressor",
    "Steering Wheel",
]

# =========================================================
# Special module term sets
# Used for direct matching or override logic where needed.
# =========================================================
ECM_TERMS = {"ecm", "ecu", "pcm", "engine computer"}
TCM_TERMS = {"tcm", "transmission computer"}

# =========================================================
# Search part terms
# Raw query terms used to build marketplace searches.
# These are intentionally simpler than taxonomy categories.
# =========================================================
SEARCH_PART_TERMS = [
    "headlight",
    "tail light",
    "mirror",
    "radio",
    "instrument cluster",
    "alternator",
    "starter",
    "ecm",
    "tcm",
    "wheel",
    "seat",
    "door",
    "fender",
    "hood",
    "front bumper",
    "rear bumper",
    "grille",
    "window regulator",
    "ac compressor",
    "steering wheel",
]

# =========================================================
# Part aliases
# Raw term -> normalized comparison term
# =========================================================
PART_ALIASES = {
    "headlight": "headlight",
    "head lamp": "headlight",
    "headlamp": "headlight",
    "lh headlight": "headlight",
    "rh headlight": "headlight",

    "tail light": "tail light",
    "taillight": "tail light",
    "rear lamp": "tail light",

    "mirror": "mirror",
    "side mirror": "mirror",
    "door mirror": "mirror",
    "side view mirror": "mirror",

    "radio": "radio",
    "stereo": "radio",
    "infotainment": "radio",
    "display screen": "radio",
    "console": "radio",

    "cluster": "instrument cluster",
    "speedometer": "instrument cluster",
    "gauge cluster": "instrument cluster",

    "alternator": "alternator",
    "starter": "starter",
    "starter motor": "starter",

    "ecm": "ecu",
    "pcm": "ecu",
    "ecu": "ecu",
    "engine computer": "ecu",

    "tcm": "tcm",
    "transmission computer": "tcm",

    "wheel": "wheel",
    "rim": "wheel",

    "driver seat": "seat",
    "passenger seat": "seat",
    "rear seat": "seat",
    "seat": "seat",

    "complete door": "door",
    "door assembly": "door",
    "door": "door",

    "fender": "fender",
    "hood": "hood",

    "front bumper": "front bumper",
    "bumper cover": "front bumper",
    "rear bumper": "rear bumper",

    "grille": "grille",
    "front grille": "grille",

    "window regulator": "window regulator",
    "power window motor": "window regulator",
    "window motor": "window regulator",

    "ac compressor": "ac compressor",
    "a/c compressor": "ac compressor",
    "air conditioning compressor": "ac compressor",

    "steering wheel": "steering wheel",
}

# =========================================================
# Part to Category mapping
# Raw Part term -> normalized comparison term to get category 
# =========================================================
PART_CATEGORY_MAP = {
    "headlight": "Headlight Assembly",
    "tail light": "Tail Light Assembly",
    "mirror": "Side Mirror",
    "radio": "Radio / Infotainment",
    "instrument cluster": "Instrument Cluster",
    "alternator": "Alternator",
    "starter": "Starter",
    "ecu": "Engine Control Module",
    "tcm": "Transmission Control Module",
    "wheel": "Wheel / Rim",
    "seat": "Seat",
    "door": "Door Assembly",
    "fender": "Fender",
    "hood": "Hood",
    "front bumper": "Front Bumper Assembly",
    "rear bumper": "Rear Bumper Assembly",
    "grille": "Grille",
    "window regulator": "Window Regulator",
    "ac compressor": "AC Compressor",
    "steering wheel": "Steering Wheel",
}