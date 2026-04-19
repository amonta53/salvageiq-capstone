# =========================================================
# test_standardize_model.py
#
# Purpose:
#     Unit tests for standardize_model in normalize.py.
#
# Notes:
#     These tests verify configured model alias handling and
#     fallback behavior for unknown or blank values.
# =========================================================

from wrangle.normalize import standardize_model


def test_standardize_model_maps_known_alias() -> None:
    """
    standardize_model should map a known alias to the configured canonical model.
    """
    result = standardize_model("f150")

    assert result == "F-150"


def test_standardize_model_returns_cleaned_original_for_unknown_model() -> None:
    """
    standardize_model should return the cleaned original value when
    the model is not found in the alias map.
    """
    result = standardize_model("Camry")

    assert result == "Camry"


def test_standardize_model_returns_none_for_blank_input() -> None:
    """
    standardize_model should return None for blank or whitespace-only input.
    """
    result = standardize_model("   ")

    assert result is None