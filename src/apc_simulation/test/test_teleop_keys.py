"""teleop_keys 테스트 (ROS 없이 실행)."""
import pytest

from apc_simulation.teleop_keys import TeleopState, parse_keys


@pytest.mark.parametrize('data, keys', [
    (b'w', ['w']),
    (b'WASD', ['w', 'a', 's', 'd']),
    (b'\x1b[A\x1b[B\x1b[C\x1b[D', ['up', 'down', 'right', 'left']),
    (b'\x1bOA', ['up']),                     # 일부 터미널의 화살표 형식
    (b' x', ['space', 'x']),
    (b'\x03', ['ctrl-c']),
    (b'ww\x1b[Aw', ['w', 'w', 'up', 'w']),    # 꾹 누를 때 반복 입력
    (b'\x1b', []),                           # ESC 혼자 → 무시
    (b'\x1b[Z', []),                         # 모르는 ESC 시퀀스 → 무시
])
def test_parse_keys(data, keys):
    assert parse_keys(data) == keys


@pytest.mark.parametrize('key, expected', [
    ('w', (0.2, 0.0)), ('up', (0.2, 0.0)),
    ('s', (-0.2, 0.0)), ('down', (-0.2, 0.0)),
    ('a', (0.0, 1.0)), ('left', (0.0, 1.0)),
    ('d', (0.0, -1.0)), ('right', (0.0, -1.0)),
])
def test_wasd_and_arrows_same_direction(key, expected):
    st = TeleopState(0.2, 1.0, hold_timeout=0.6)
    st.press(key, now=10.0)
    assert st.velocity(10.1) == pytest.approx(expected)


def test_stops_when_key_released():
    st = TeleopState(0.2, 1.0, hold_timeout=0.6)
    st.press('w', 10.0)
    assert st.velocity(10.5) == (0.2, 0.0)       # 반복 입력 시작 전 → 계속 움직임
    assert st.velocity(10.61) == (0.0, 0.0)      # 입력 끊김 → 정지


def test_holding_key_keeps_moving():
    st = TeleopState(0.2, 1.0, hold_timeout=0.6)
    t = 10.0
    st.press('w', t)
    for _ in range(50):                          # 0.03 s 간격 반복 입력 1.5 초
        t += 0.03
        st.press('w', t)
        assert st.velocity(t) == (0.2, 0.0)


def test_last_key_wins():
    st = TeleopState(0.2, 1.0)
    st.press('w', 1.0)
    st.press('d', 1.1)
    assert st.velocity(1.2) == (0.0, -1.0)


@pytest.mark.parametrize('stop_key', ['space', 'x'])
def test_stop_keys(stop_key):
    st = TeleopState(0.2, 1.0)
    st.press('w', 1.0)
    st.press(stop_key, 1.1)
    assert st.velocity(1.2) == (0.0, 0.0)


def test_unknown_key_ignored():
    st = TeleopState(0.2, 1.0)
    st.press('w', 1.0)
    st.press('z', 1.1)
    assert st.velocity(1.2) == (0.2, 0.0)


def test_nothing_pressed():
    assert TeleopState(0.2, 1.0).velocity(0.0) == (0.0, 0.0)
