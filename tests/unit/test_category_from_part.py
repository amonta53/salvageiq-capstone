# =========================================================
# test_category_from_part.py
#
# Purpose:
#     Unit tests for category_from_part in normalize.py.
#
# Notes:
#     These tests verify that part labels map to the
#     expected taxonomy category where configured.
# =========================================================

from wrangle.normalize import category_from_part


def test_category_from_part_maps_known_part_to_expected_category() -> None:
    """
    category_from_part should map a known part label
    to the configured taxonomy category.
    """
    result = category_from_part("headlight")

    assert result == "Headlight Assembly"


def test_category_from_part_returns_none_for_unknown_part() -> None:
    """
    category_from_part should return None when the part does not
    map to a configured taxonomy category.
    """
    result = category_from_part("flux capacitor")

    assert result is None
