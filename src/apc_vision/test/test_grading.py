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
