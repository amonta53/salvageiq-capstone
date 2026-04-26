# =========================================================
# api.py
# FastAPI entry point for SalvageIQ
#
# Purpose:
# Provide a small web/API layer around the existing pipeline.
# =========================================================

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.salvage_service import SalvageIQRequest, run_vehicle_lookup


class LookupRequest(BaseModel):
    """Incoming lookup payload from UI or API clients."""

    vin: str | None = Field(default=None, max_length=17)
    year: int | None = Field(default=None, ge=1975, le=2035)
    make: str | None = None
    model: str | None = None
    top_n: int = Field(default=10, ge=1, le=25)
    max_pages_per_search: int = Field(default=2, ge=1, le=5)


app = FastAPI(title="SalvageIQ", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/lookup")
def lookup_parts(payload: LookupRequest) -> dict:
    """Run a vehicle lookup and return ranked part opportunities."""
    try:
        result = run_vehicle_lookup(
            SalvageIQRequest(
                vin=payload.vin,
                year=payload.year,
                make=payload.make,
                model=payload.model,
                top_n=payload.top_n,
                max_pages_per_search=payload.max_pages_per_search,
            )
        )
        return {
            "run_id": result.run_id,
            "vehicle": result.vehicle,
            "ranked_parts": result.ranked_parts,
            "ranked_output_path": result.ranked_output_path,
            "caveats": result.caveats,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
