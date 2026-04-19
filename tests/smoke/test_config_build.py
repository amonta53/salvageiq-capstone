# =========================================================
# test_config_build.py
# Smoke tests for SalvageIQ config builder.
# Purpose:
#   Verify that build_scrape_config() returns valid ScrapeConfig
#   objects for supported runtime modes.
# =========================================================

from config.scrape_config import ScrapeConfig
from config.config_builder import build_scrape_config


def test_config_build_full_smoke() -> None:
    print("Starting full config build smoke test...")

    config = build_scrape_config(mode="full")

    assert isinstance(config, ScrapeConfig), "Expected ScrapeConfig from full mode"
    assert hasattr(config, "mode"), "Config must have a mode attribute"

    print("Full config build smoke test passed.")


def test_config_build_test_mode_smoke() -> None:
    print("Starting test-mode config smoke test...")

    config = build_scrape_config(mode="test")

    assert isinstance(config, ScrapeConfig), "Expected ScrapeConfig from test mode"
    assert config.mode == "test", "Expected config.mode to be 'test'"
    assert config.start_year == 2019, "Expected test mode start_year == 2019"
    assert config.end_year == 2019, "Expected test mode end_year == 2019"
    assert config.parts == ["alternator"], "Expected test mode to use only alternator"
    assert config.max_pages_per_search == 1, "Expected test mode max_pages_per_search == 1"

    assert len(config.supported_vehicles) == 1, "Expected exactly one test vehicle"

    vehicle = config.supported_vehicles[0]
    assert vehicle["make"] == "Toyota", "Expected Toyota test vehicle"
    assert vehicle["model"] == "Camry", "Expected Camry test vehicle"
    assert vehicle["year_range"] == (2012, 2020), "Expected Toyota Camry year range of 2012-2020"

    print("Test-mode config smoke test passed.")


if __name__ == "__main__":
    test_config_build_full_smoke()
    test_config_build_test_mode_smoke()