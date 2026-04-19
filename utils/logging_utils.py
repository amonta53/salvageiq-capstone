# =========================================================
# logging_utils.py
#
# Purpose:
#     Simple logging helpers for pipeline execution.
#
# Notes:
#     - Writes to both console and file
#     - No log levels or rotation (intentionally simple)
# =========================================================

from __future__ import annotations

import logging 
from datetime import datetime
from pathlib import Path


# =========================================================
# Logging Helpers
# =========================================================
def setup_logging(logs_dir: Path, run_id: str) -> Path: 
    """
    Configure logging to file + console.
    Args:
        logs_dir: Directory to save log files
        run_id: Unique identifier for this run (used in log filename)
    Returns:
        Path to the log file for this run.
    Why:
    - Writes all pipeline activity to a persistent log file
    - Keeps console output readable for real-time monitoring
    - Ties logs to a specific run_id for traceability
    """

    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / f"pipeline_{run_id}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),  # still prints to console
        ],
        force=True,
    )
    return log_file


def timestamp_now() -> str:
    """Return current timestamp as YYYY-MM-DD HH:MM:SS."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_elapsed_hhmmss(elapsed_seconds: float) -> str:
    """Format elapsed seconds as HH:MM:SS."""
    total_seconds = int(elapsed_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class RunLogger:
    """Lightweight logger that writes to console and file."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, message: str) -> None:
        stamped = f"{timestamp_now()} | {message}"
        print(stamped)

        with open(self.log_path, "a", encoding="utf-8") as handle:
            handle.write(f"{stamped}\n")