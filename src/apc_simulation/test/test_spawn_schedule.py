"""spawn_schedule.SpawnSchedule 테스트 (ROS 없이 실행)."""
import pytest

from apc_simulation.spawn_schedule import SpawnSchedule

TICK = 0.05


def spawn_times(sched: SpawnSchedule, start: float, end: float, tick: float = TICK):
    """start~end 를 tick 간격으로 돌며 생성된 시각 목록."""
    out = []
    n = 0
    while True:
        t = round(start + n * tick, 6)
        if t > end:
            return out
        if sched.due(t):
            out.append(t)
        n += 1


def test_no_spawn_before_clock():
    s = SpawnSchedule(4.0)
    assert not s.due(0.0)
    assert not s.due(0.0)
    assert s.next_time is None


@pytest.mark.parametrize('t1', [4.0, 16.083, 28.787, 44.743, 58.758, 23.8])
def test_second_apple_is_one_period_after_first(t1):
    """회귀: 첫 /clock 이 4초 격자 직전(예 58.758)이어도 두 번째는 정확히 4초 뒤."""
    s = SpawnSchedule(4.0)
    times = spawn_times(s, t1, t1 + 12.5)
    assert times[0] == pytest.approx(t1)
    gaps = [b - a for a, b in zip(times, times[1:])]
    assert len(gaps) == 3
    assert all(g == pytest.approx(4.0, abs=TICK + 1e-9) for g in gaps)


def test_no_drift_over_many_periods():
    s = SpawnSchedule(4.0)
    times = spawn_times(s, 10.02, 10.02 + 402.0, tick=0.03)
    assert len(times) == 101
    # 틱 지연이 쌓이지 않음: n 번째 생성은 10.02 + 4n 에서 한 틱 안
    for n, t in enumerate(times):
        assert 0.0 <= t - (10.02 + 4.0 * n) < 0.03 + 1e-9


def test_big_jump_does_not_burst():
    s = SpawnSchedule(4.0)
    assert s.due(10.0)
    assert s.due(50.0)          # 40초 점프 → 1개만
    assert not s.due(50.05)
    assert not s.due(53.9)
    assert s.due(54.0)


def test_time_going_backwards_restarts():
    s = SpawnSchedule(4.0)
    assert s.due(100.0)
    assert s.due(104.0)
    assert s.due(1.0)           # sim 리셋 → 바로 1개, 이후 1.0 기준
    assert not s.due(4.9)
    assert s.due(5.0)


def test_set_period():
    s = SpawnSchedule(4.0)
    assert s.due(10.0)
    s.set_period(2.0)           # 직전 생성(10.0) + 2.0
    assert not s.due(11.9)
    assert s.due(12.0)
    s.set_period(6.0)           # 직전 생성(12.0) + 6.0
    assert not s.due(17.9)
    assert s.due(18.0)


def test_set_period_before_first_spawn():
    s = SpawnSchedule(4.0)
    s.set_period(1.0)
    assert s.due(3.0)
    assert s.due(4.0)


@pytest.mark.parametrize('bad', [0.0, -1.0])
def test_invalid_period(bad):
    with pytest.raises(ValueError):
        SpawnSchedule(bad)
    with pytest.raises(ValueError):
        SpawnSchedule(4.0).set_period(bad)
