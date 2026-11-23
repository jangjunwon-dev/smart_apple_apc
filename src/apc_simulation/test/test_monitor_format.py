"""monitor_format 테스트 (ROS 없이 실행)."""
from apc_simulation.monitor_format import format_amr, format_grade, grade_name, GradeTally


def test_grade_names():
    assert [grade_name(g) for g in range(4)] == ['특', '상', '보통', '비상품']
    assert grade_name(9) == '알 수 없음(9)'


def test_format_grade_default_zone():
    line = format_grade(91, 0, 89.33, 0.759, 0.0, '', 68.759)
    assert line.startswith('[판정] 사과 #91')
    assert '특' in line and '지름  89.3 mm' in line and '신뢰도  76%' in line
    assert '→ 구역 A' in line and '(시뮬 68.8초)' in line
    assert '결함' not in line


def test_format_grade_zone_from_msg_and_defect():
    line = format_grade(5, 3, 72.0, 0.5, 0.12, 'ZONE_R', 0.0)
    assert '비상품' in line and '결함 12%' in line and '→ 구역 R' in line
    assert '시뮬' not in line                      # stamp 0 이면 시각 생략


def test_format_grade_unknown_diameter():
    assert '지름  모름' in format_grade(1, 1, 0.0, 0.9, 0.0, '', 1.0)


def test_format_amr():
    assert format_amr('amr_1', 2, 91, 'ZONE_A', 0) == \
        '[AMR] amr_1  이동 중  사과 #91 → 구역 A  대기 작업 0개'
    assert format_amr('amr_1', 0, 0, '', 2) == '[AMR] amr_1  대기  대기 작업 2개'


def test_tally():
    t = GradeTally()
    for g in [0, 0, 1, 2, 3, 3, 7]:
        t.add(g)
    assert t.summary() == '[누적] 총 6개: 특 2 / 상 1 / 보통 1 / 비상품 2'
