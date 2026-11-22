from apc_vision.grading import (
    GRADE_GOOD, GRADE_NORMAL, GRADE_REJECT, GRADE_SPECIAL, grade_from_features,
)


def test_reject_when_defect_large():
    assert grade_from_features(90.0, 0.3) == GRADE_REJECT


def test_special_big_clean_apple():
    assert grade_from_features(88.0, 0.0) == GRADE_SPECIAL


def test_good_medium_clean_apple():
    assert grade_from_features(78.0, 0.02) == GRADE_GOOD


def test_normal_small_or_slight_defect():
    assert grade_from_features(65.0, 0.0) == GRADE_NORMAL
    assert grade_from_features(90.0, 0.1) == GRADE_NORMAL


# ---------- 크기 등급 / 품질·크기 결합 (2026-11-22 초안) ----------
import pytest  # noqa: E402

from apc_vision.grading import combine_grade, size_grade  # noqa: E402


@pytest.mark.parametrize('diameter, expected', [
    (96.0, GRADE_SPECIAL), (89.0, GRADE_SPECIAL),
    (88.9, GRADE_GOOD), (83.0, GRADE_GOOD),
    (82.9, GRADE_NORMAL), (76.0, GRADE_NORMAL),
    (75.9, GRADE_REJECT), (70.0, GRADE_REJECT),
])
def test_size_grade_boundaries(diameter, expected):
    assert size_grade(diameter) == expected


def test_combine_takes_lower_grade():
    # 품질 특 + 크기 보통 → 보통
    assert combine_grade(GRADE_SPECIAL, 80.0) == GRADE_NORMAL
    # 품질 보통 + 크기 특 → 보통 (크기가 커도 품질을 올리지 않음)
    assert combine_grade(GRADE_NORMAL, 95.0) == GRADE_NORMAL
    # 품질 비상품이면 크기와 상관없이 비상품
    assert combine_grade(GRADE_REJECT, 95.0) == GRADE_REJECT
    # 둘 다 특 → 특
    assert combine_grade(GRADE_SPECIAL, 90.0) == GRADE_SPECIAL


def test_combine_custom_thresholds():
    assert combine_grade(GRADE_SPECIAL, 86.0, special_mm=85.0) == GRADE_SPECIAL


def test_combine_keeps_unknown_quality():
    assert combine_grade(7, 70.0) == 7
