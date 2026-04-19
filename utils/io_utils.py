# =========================================================
# io_utils.py
#
# Purpose:
#     Small file and CSV helpers used across the pipeline.
#
# Notes:
#     - Keeps common file setup logic in one place
#     - CSV helpers assume pandas DataFrame input/output
# =========================================================

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import logging

import pandas as pd


# =========================================================
# File and directory helpers
# =========================================================


def ensure_directory(path: Path) -> None:
    """Create a directory tree if it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)


def ensure_csv_with_headers(filepath: Path, columns: Iterable[str]) -> None:
    """
    Create a CSV with headers if it does not already exist.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if not filepath.exists():
        pd.DataFrame(columns=list(columns)).to_csv(filepath, index=False)


def append_dataframe_to_csv(df: pd.DataFrame, filepath: Path) -> None:
    """
    Append a DataFrame to a CSV, writing headers only when needed.
    """
    filepath = Path(filepath)
    header = not filepath.exists() or filepath.stat().st_size == 0
    df.to_csv(filepath, mode="a", header=header, index=False)


def append_row_to_csv(
    filepath: Path,
    row: dict,
    columns: Iterable[str],
) -> None:
    """
    Append a single row to a CSV using the provided column order.
    """
    df = pd.DataFrame([row], columns=list(columns))
    append_dataframe_to_csv(df, filepath)


def save_text(filepath: Path, content: str) -> None:
    """Write text content to a file, creating parent folders if needed."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")


def reset_output_file(filepath: Path) -> None:
    """Delete an output file if it exists."""
    filepath = Path(filepath)

    if not filepath.exists():
        return

    try:
        filepath.unlink()
        logger = logging.getLogger(__name__) 
        logger.info(f"Deleted existing file: {filepath}")

    except PermissionError as e:
        msg = (
            f"\n\n Cannot delete file: {filepath}\n"
            f"Reason: File is likely open in Excel or another program.\n\n"
            f"Action:\n"
            f"- Close the file\n"
            f"- Or switch to a different output mode/path\n\n"
            f"- I know you've been running a lot of analysis\n"
            f"- and have these open constantly, but bro, you should be \n"
            f"- used to this by now. Close the files before you run the pipeline."
        )

        logger.error(msg)
        raise PermissionError(msg) from e