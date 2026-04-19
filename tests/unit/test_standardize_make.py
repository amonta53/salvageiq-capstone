# =========================================================
# test_standardize_make.py
#
# Purpose:
#     Unit tests for standardize_make in normalize.py.
#
# Notes:
#     These tests verify configured make alias handling and
#     fallback behavior for unknown or blank values.
# =========================================================

from wrangle.normalize import standardize_make


def test_standardize_make_maps_known_alias() -> None:
    """
    standardize_make should map a known alias to the configured canonical make.
    """
    result = standardize_make("chevy")

    assert result == "Chevrolet"


def test_standardize_make_returns_cleaned_original_for_unknown_make() -> None:
    """
    standardize_make should return the cleaned original value when
    the make is not found in the alias map.
    """
    result = standardize_make("Saturn")

    assert result == "Saturn"


def test_standardize_make_returns_none_for_blank_input() -> None:
    """
    standardize_make should return None for blank or whitespace-only input.
    """
    result = standardize_make("   ")

    assert result is None