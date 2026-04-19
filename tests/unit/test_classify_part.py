# =========================================================
# test_classify_part.py
#
# Purpose:
#     Unit tests for classify_part in normalize.py.
#
# Notes:
#     These tests verify taxonomy-based text classification,
#     exclusion handling, and the special ECM/TCM overlap rule.
# =========================================================

from wrangle.normalize import classify_part


def test_classify_part_maps_known_text_to_expected_category() -> None:
    """
    classify_part should map recognizable listing text
    to the expected taxonomy category.
    """
    result = classify_part("OEM left headlight assembly for 2018 Toyota Camry")

    assert result == "Headlight Assembly"


def test_classify_part_excluded_term_blocks_false_positive() -> None:
    """
    classify_part should not classify text when an excluded term
    is present for that category.
    """
    result = classify_part("Headlight bulb for Toyota Camry")

    assert result is None


def test_classify_part_ecm_tcm_overlap_returns_engine_control_module() -> None:
    """
    classify_part should return Engine Control Module when both
    ECM and TCM terms appear in the same text.
    """
    result = classify_part("ECM TCM ECU transmission engine control module set")

    assert result == "Engine Control Module"
    