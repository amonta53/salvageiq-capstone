# =========================================================
# checkpoint_utils.py
#
# Purpose:
#     Simple checkpoint tracking for scrape resume support.
#
# Notes:
#     - One search key per line
#     - Flat file by design (fast, simple, easy to inspect)
#     - No dedup or locking — caller owns correctness
# =========================================================
from __future__ import annotations

from pathlib import Path


# =========================================================
# Checkpoint helpers
# =========================================================


def load_completed_searches(checkpoint_path: Path) -> set[str]:
    """
    Load completed search keys from checkpoint file.

    Returns empty set if file doesn't exist.
    """
    if not checkpoint_path.exists():
        return set()

    with open(checkpoint_path, "r", encoding="utf-8") as handle:
        return {line.strip() for line in handle if line.strip()}



def append_completed_search(checkpoint_path: Path, search_key: str) -> None:
    """ Append a completed search key to the checkpoint file. """

    # Make sure directory exists before writing
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    with open(checkpoint_path, "a", encoding="utf-8") as handle:
        handle.write(f"{search_key}\n")
