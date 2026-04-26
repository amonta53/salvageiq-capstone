# =========================================================
# salvage_service.py
# Application service layer for SalvageIQ
#
# Purpose:
# Tie vehicle identity to the existing scrape/analyze/rank pipeline.
# This is the boundary between the web app and the capstone pipeline.
#
# Notes:
# - Keeps FastAPI endpoints thin
# - Keeps pipeline-specific code out of the UI
# - Uses one vehicle, one model year, full configured part list
# =========================================================

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from config.config_builder import build_scrape_config
from config.taxonomy import SEARCH_PART_TERMS
from pipeline.orchestrator import run_pipeline

from app.vehicle_lookup import VehicleIdentity, normalize_vehicle_input


@dataclass(slots=True)
class SalvageIQRequest:
    """User-facing lookup request."""

    year: int | None = None
    make: str | None = None
    model: str | None = None
    vin: str | None = None
    top_n: int = 10
    max_pages_per_search: int = 2


@dataclass(slots=True)
class SalvageIQResult:
    """Response returned to the web/API layer."""

    run_id: str
    vehicle: dict[str, Any]
    ranked_parts: list[dict[str, Any]]
    ranked_output_path: str
    caveats: list[str]


def run_vehicle_lookup(request: SalvageIQRequest) -> SalvageIQResult:
    """
    Run a one-vehicle SalvageIQ lookup and return ranked part opportunities.

    This creates a focused ScrapeConfig:
    - one vehicle
    - one model year
    - softcoded SEARCH_PART_TERMS list
    - sold pass plus active market snapshot
    - ranked top-N output
    """
    vehicle = normalize_vehicle_input(
        year=request.year,
        make=request.make,
        model=request.model,
        vin=request.vin,
    )

    config = build_scrape_config(mode="full")
    config.start_year = vehicle.year
    config.end_year = vehicle.year
    config.supported_vehicles = [
        {
            "year_range": (vehicle.year, vehicle.year),
            "make": vehicle.make,
            "model": vehicle.model,
        }
    ]
    config.parts = SEARCH_PART_TERMS.copy()
    config.max_pages_per_search = request.max_pages_per_search
    config.top_n_parts = request.top_n
    config.run_hypothesis_test = False
    config.reset_outputs_on_run = True
    config.enable_resume = False

    # ScrapeConfig builds make_model_map in __post_init__, but we mutate
    # supported_vehicles after creation. Rebuild the map explicitly.
    config.make_model_map = {vehicle.make: [vehicle.model]}

    run_pipeline(config)

    top_path = config.top_10_output_csv_path
    ranked_parts = _load_ranked_parts(top_path)

    return SalvageIQResult(
        run_id=config.run_id,
        vehicle=vehicle.to_dict(),
        ranked_parts=ranked_parts,
        ranked_output_path=str(top_path),
        caveats=[
            "Sell-through rate is an approximation based on sold listing count versus active listing count.",
            "eBay sold listings are treated as a recent market window; verify exact listing dates before using this for high-dollar buying decisions.",
            "Softcoded part terms are broad, so fitment and trim-specific compatibility still need a human sanity check.",
        ],
    )


def _load_ranked_parts(path: Path) -> list[dict[str, Any]]:
    """Load ranked parts CSV and convert NaN values to JSON-friendly nulls."""
    if not path.exists():
        raise FileNotFoundError(f"Ranked output was not created: {path}")

    df = pd.read_csv(path)
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient="records")
