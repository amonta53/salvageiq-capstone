# =========================================================
# test_normalize_token.py
#
# Purpose:
#     Unit tests for normalize_token in normalize.py.
#
# Notes:
#     These tests verify the low-level text cleanup behavior that
#     downstream make/model/part standardization depends on.
# =========================================================

import pandas as pd

from wrangle.normalize import normalize_token


def test_normalize_token_trims_lowercases_and_collapses_spaces() -> None:
    """
    normalize_token should trim outer whitespace, lowercase text,
    and collapse repeated internal whitespace to single spaces.
    """
    value = "  Head   Lamp  Assembly  "
    result = normalize_token(value)

    assert result == "head lamp assembly"


def test_normalize_token_returns_empty_string_for_none() -> None:
    """
    normalize_token should return an empty string for None input.
    """
    result = normalize_token(None)

    assert result == ""


def test_normalize_token_returns_empty_string_for_pd_na() -> None:
    """
    normalize_token should return an empty string for pandas missing values.
    """
    result = normalize_token(pd.NA)

    assert result == ""