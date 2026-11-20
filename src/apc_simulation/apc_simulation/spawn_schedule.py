"""사과 생성 시각 계산 — ROS 의존 없음 (pytest 대상).

rclpy 타이머를 spawn_period 주기로 직접 쓰면 use_sim_time 노드에서 문제가 생긴다.
/clock 을 받기 전(ROS 시간 0)에 만든 타이머는 다음 호출이 sim 0 기준 period 격자에 맞춰져,
첫 /clock 도착 순간(T1) 1회 실행된 뒤 두 번째 호출이 4 − (T1 mod 4) 초 뒤(0~4초 무작위)에 온다.
→ 예: T1=58.76 이면 다음 호출이 60.00 이라 사과 2개가 1.2초 차로 붙어서 생성됨.

그래서 짧은 틱 타이머에서 due(now) 를 물어보고, 간격은 이 클래스가 직접 계산한다.
- now <= 0 (아직 /clock 없음): 생성 안 함
- 첫 유효 시각에 바로 1개, 이후 직전 생성 + period 마다 1개
- 많이 밀리면(시간 점프·처리 지연) 몰아서 만들지 않고 now + period 로 다시 잡음
- 시간이 뒤로 가면(sim 리셋) now 를 기준으로 다시 시작
"""
from __future__ import annotations


class SpawnSchedule:
    """일정 주기(sim 시간 기준)로 생성 시점을 알려주는 스케줄러."""

    def __init__(self, period: float) -> None:
        self.period = 0.0
        self.next_time: float | None = None   # None = 아직 첫 생성 전
        self.set_period(period)

    def set_period(self, period: float) -> None:
        """주기 변경. 다음 생성 시각은 직전 생성 기준으로 새 주기를 적용."""
        if period <= 0:
            raise ValueError(f'period 는 0보다 커야 함 (입력: {period})')
        if self.next_time is not None:
            self.next_time += period - self.period
        self.period = float(period)

    def due(self, now: float) -> bool:
        """now(초)에 사과를 생성해야 하면 True 를 돌려주고 다음 생성 시각을 갱신."""
        if now <= 0.0:
            return False
        if self.next_time is None or now < self.next_time - self.period:
            # 첫 생성, 또는 시간이 직전 생성보다 앞으로 되돌아감(sim 리셋) → 지금 생성
            self.next_time = now + self.period
            return True
        if now < self.next_time:
            return False
        self.next_time += self.period
        if self.next_time <= now:          # 한 주기 넘게 밀림 → 몰아서 만들지 않음
            self.next_time = now + self.period
        return True
