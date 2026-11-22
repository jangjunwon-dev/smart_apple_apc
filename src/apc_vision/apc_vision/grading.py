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


# ---------------------------------------------------------------------------
# 크기 등급 (2026-11-22 초안 — 팀 확정 전, docs/02_roadmap.md '결정 사항' 참고)
# 농산물 표준규격 사과 크기 구분(1과 무게)을 지름으로 근사 환산한 값.
# 사과를 밀도 0.82 g/cm³ 구로 보고 d = (6m / (π·ρ))^(1/3):
#   약 300 g(2L) → 89 mm,  약 250 g(L) → 83 mm,  약 188 g(S/2S 경계) → 76 mm
# 최종 등급 = YOLO 품질 등급(착색·결함)과 크기 등급 중 더 낮은 쪽(숫자가 큰 쪽).
# ---------------------------------------------------------------------------
SIZE_SPECIAL_MM = 89.0    # 이상 → 특
SIZE_GOOD_MM = 83.0       # 이상 → 상
SIZE_NORMAL_MM = 76.0     # 이상 → 보통, 미만 → 비상품


def size_grade(diameter_mm: float,
               special_mm: float = SIZE_SPECIAL_MM,
               good_mm: float = SIZE_GOOD_MM,
               normal_mm: float = SIZE_NORMAL_MM) -> int:
    """지름만으로 정한 크기 등급."""
    if diameter_mm >= special_mm:
        return GRADE_SPECIAL
    if diameter_mm >= good_mm:
        return GRADE_GOOD
    if diameter_mm >= normal_mm:
        return GRADE_NORMAL
    return GRADE_REJECT


def combine_grade(quality_grade: int, diameter_mm: float, **size_thresholds: float) -> int:
    """품질 등급과 크기 등급 중 더 낮은 등급(숫자가 큰 쪽)을 반환한다.

    quality_grade 가 0~3 밖이면 그대로 둔다 (판단 근거가 없으므로 크기로 덮어쓰지 않음).
    """
    if not GRADE_SPECIAL <= quality_grade <= GRADE_REJECT:
        return quality_grade
    return max(quality_grade, size_grade(diameter_mm, **size_thresholds))
