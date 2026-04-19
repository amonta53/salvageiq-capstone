# =========================================================
# main.py
# Entry point for the SalvageIQ pipeline
#
# Purpose:
# Keep startup simple:
# - choose mode
# - build config
# - hand control to the orchestrator
# =========================================================

from __future__ import annotations

import logging
import sys

from config.config_builder import build_scrape_config
from pipeline.orchestrator import run_pipeline


if __name__ == "__main__":
    selected_mode = sys.argv[1] if len(sys.argv) > 1 else "full"
    input_run_id = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        config = build_scrape_config(mode=selected_mode, input_run_id=input_run_id)
        run_pipeline(config)
    except Exception:
        logging.exception("Pipeline failed")
        raise