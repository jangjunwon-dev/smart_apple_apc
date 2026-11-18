"""등급 판정 규칙 (ROS 의존성 없음 → pytest 로 단독 테스트 가능).

⚠️ 아래 경계값은 임시값입니다. 기획서/공공 기준 확정 후 🅐 가 수정하고
   docs/02_roadmap.md '결정 사항'에 기록하세요.
"""

GRADE_SPECIAL = 0
GRADE_GOOD = 1
GRADE_NORMAL = 2
GRADE_REJECT = 3

GRADE_NAMES = {
    GRADE_SPECIAL: '특',
    GRADE_GOOD: '상',
    GRADE_NORMAL: '보통',
    GRADE_REJECT: '비상품',
}

# 임시 기준값 (TODO: 확정 필요)
DEFECT_REJECT = 0.20      # 결함 면적 20% 이상 → 비상품
DEFECT_GOOD_MAX = 0.05    # 결함 5% 이하여야 특/상
DIAMETER_SPECIAL = 85.0   # mm 이상 → 특 후보
DIAMETER_GOOD = 75.0      # mm 이상 → 상 후보


def grade_from_features(diameter_mm: float, defect_ratio: float) -> int:
    """지름과 결함 비율로 등급 상수를 반환한다."""
    if defect_ratio >= DEFECT_REJECT:
        return GRADE_REJECT
    if defect_ratio <= DEFECT_GOOD_MAX:
        if diameter_mm >= DIAMETER_SPECIAL:
            return GRADE_SPECIAL
        if diameter_mm >= DIAMETER_GOOD:
            return GRADE_GOOD
    return GRADE_NORMAL
