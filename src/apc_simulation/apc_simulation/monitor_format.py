"""판정·AMR 상태를 한국어 한 줄로 만드는 함수 — ROS 의존 없음 (pytest 대상).

등급·상태 번호는 apc_interfaces 의 AppleGrade / AmrStatus 상수와 같다.
"""
from __future__ import annotations

GRADE_NAMES = {0: '특', 1: '상', 2: '보통', 3: '비상품'}
GRADE_ZONES = {0: 'A', 1: 'B', 2: 'C', 3: 'R'}          # 기본 매핑 (docs/03_architecture.md 4절)
AMR_STATES = {0: '대기', 1: '싣는 중', 2: '이동 중', 3: '내리는 중', 4: '오류'}


def grade_name(grade: int) -> str:
    return GRADE_NAMES.get(grade, f'알 수 없음({grade})')


def format_grade(apple_id: int, grade: int, diameter_mm: float, confidence: float,
                 defect_ratio: float, zone_id: str, stamp_sec: float) -> str:
    """예) [판정] 사과 #91  특      지름 89.3 mm  신뢰도 76%  → 구역 A   (시뮬 68.8초)"""
    zone = zone_id or GRADE_ZONES.get(grade, '?')
    zone = zone.removeprefix('ZONE_')
    parts = [f'[판정] 사과 #{apple_id:<4d} {grade_name(grade):<4s}',
             f'지름 {diameter_mm:5.1f} mm' if diameter_mm > 0 else '지름  모름',
             f'신뢰도 {confidence * 100:3.0f}%']
    if defect_ratio > 0:
        parts.append(f'결함 {defect_ratio * 100:.0f}%')
    parts.append(f'→ 구역 {zone}')
    line = '  '.join(parts)
    if stamp_sec > 0:
        line += f'   (시뮬 {stamp_sec:.1f}초)'
    return line


def format_amr(robot_id: str, state: int, current_apple_id: int, target_zone: str,
               queue_length: int) -> str:
    """예) [AMR] amr_1  이동 중  사과 #91 → 구역 A  대기 작업 2개"""
    name = AMR_STATES.get(state, f'알 수 없음({state})')
    line = f'[AMR] {robot_id or "?"}  {name}'
    if current_apple_id:
        line += f'  사과 #{current_apple_id}'
    if target_zone:
        line += f' → 구역 {target_zone.removeprefix("ZONE_")}'
    line += f'  대기 작업 {queue_length}개'
    return line


class GradeTally:
    """등급별 개수 누적 → 요약 한 줄."""

    def __init__(self) -> None:
        self.counts = dict.fromkeys(GRADE_NAMES, 0)

    def add(self, grade: int) -> None:
        if grade in self.counts:
            self.counts[grade] += 1

    def summary(self) -> str:
        total = sum(self.counts.values())
        body = ' / '.join(f'{GRADE_NAMES[g]} {n}' for g, n in self.counts.items())
        return f'[누적] 총 {total}개: {body}'
