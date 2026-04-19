# =========================================================
# test_imports.py
# Smoke test for SalvageIQ package imports.
# Purpose:
#   Verify that key config modules and objects import cleanly
#   and pass a few basic sanity checks.
# =========================================================

def test_import_smoke() -> None:
    print("Starting import smoke test...")

    from config.settings import (
        PROJECT_ROOT,
        DATA_DIR,
        RAW_DIR,
        PROCESSED_DIR,
        OUTPUT_DIR,
        START_YEAR,
        END_YEAR,
        OBSERVATION_WINDOW_DAYS,
        CONFIDENCE_THRESHOLD,
        ALPHA,
        TOP_N_PARTS,
    )

    from config.taxonomy import (
        PART_TAXONOMY,
        CATEGORY_PRIORITY,
        ECM_TERMS,
        TCM_TERMS,
    )

    from config.vehicles import (
        SUPPORTED_VEHICLES,
        MAKE_ALIASES,
        MODEL_ALIASES,
        HEAVY_DUTY_EXCLUSIONS,
    )

    from config.scrape_config import ScrapeConfig
    from config.config_builder import build_scrape_config

    print("All imports passed.")

    assert START_YEAR <= END_YEAR, "START_YEAR must be <= END_YEAR"
    assert isinstance(PART_TAXONOMY, dict), "PART_TAXONOMY must be a dict"
    assert isinstance(CATEGORY_PRIORITY, list), "CATEGORY_PRIORITY must be a list"
    assert isinstance(SUPPORTED_VEHICLES, list), "SUPPORTED_VEHICLES must be a list"
    assert ScrapeConfig is not None, "ScrapeConfig import failed"
    assert callable(build_scrape_config), "build_scrape_config must be callable"

    print("Basic validation passed.")
    print("Import smoke test completed successfully.")


if __name__ == "__main__":
    test_import_smoke()