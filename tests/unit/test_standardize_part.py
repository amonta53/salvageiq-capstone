# =========================================================
# test_standardize_part.py
#
# Purpose:
#     Unit tests for standardize_part in normalize.py.
#
# Notes:
#     These tests verify configured part alias handling and
#     fallback behavior for unknown or blank values.
# =========================================================

from wrangle.normalize import standardize_part


def test_standardize_part_maps_known_alias() -> None:
    """
    standardize_part should map a known alias to the configured part term.
    """
    result = standardize_part("headlamp")

    assert result == "headlight"


def test_standardize_part_returns_normalized_input_for_unknown_part() -> None:
    """
    standardize_part should return the normalized input when
    the part is not found in the alias map.
    """
    result = standardize_part("mirror glass")

    assert result == "mirror glass"


def test_standardize_part_returns_none_for_blank_input() -> None:
    """
    standardize_part should return None for blank or whitespace-only input.
    """
    result = standardize_part("   ")

    assert result is None
