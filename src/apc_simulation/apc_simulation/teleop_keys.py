"""키보드 조종 로직 — ROS 의존 없음 (pytest 대상).

키 → 속도 방향:
  w / ↑ : 앞으로      s / ↓ : 뒤로
  a / ← : 왼쪽 회전   d / → : 오른쪽 회전
  space / x : 즉시 정지

터미널은 '키를 뗐다' 는 신호가 없고, 키를 누르고 있으면 같은 글자가 반복 입력된다.
그래서 마지막 입력 후 hold_timeout 초 동안 새 입력이 없으면 멈춘 것으로 본다
(→ 누르고 있는 동안만 움직임). 반복 입력 시작 지연(보통 0.25~0.5 초)보다 길어야
처음 누를 때 끊기지 않는다.
"""
from __future__ import annotations

# 키 이름 → (앞뒤 방향, 회전 방향). +회전 = 왼쪽(반시계, REP-103)
KEY_DIRECTIONS: dict[str, tuple[int, int]] = {
    'w': (1, 0), 'up': (1, 0),
    's': (-1, 0), 'down': (-1, 0),
    'a': (0, 1), 'left': (0, 1),
    'd': (0, -1), 'right': (0, -1),
}
STOP_KEYS = {'space', 'x'}
QUIT_KEYS = {'q', 'ctrl-c'}

_ARROWS = {'A': 'up', 'B': 'down', 'C': 'right', 'D': 'left'}


def parse_keys(data: bytes) -> list[str]:
    """터미널에서 읽은 바이트를 키 이름 목록으로 바꾼다.

    화살표 키는 ESC [ A~D (또는 ESC O A~D) 세 바이트로 온다. 영문자는 대소문자 구분 없음.
    모르는 바이트는 버린다.
    """
    keys: list[str] = []
    i = 0
    while i < len(data):
        b = data[i]
        if b == 0x1b:  # ESC
            if i + 2 < len(data) and data[i + 1] in (0x5b, 0x4f):  # '[' 또는 'O'
                name = _ARROWS.get(chr(data[i + 2]))
                if name:
                    keys.append(name)
                i += 3
                continue
            i += 1
            continue
        if b == 0x03:
            keys.append('ctrl-c')
        elif b == 0x20:
            keys.append('space')
        elif 0x21 <= b <= 0x7e:
            keys.append(chr(b).lower())
        i += 1
    return keys


class TeleopState:
    """마지막으로 누른 방향키를 기억하고, 시간이 지나면 멈춘다."""

    def __init__(self, linear_speed: float, angular_speed: float,
                 hold_timeout: float = 0.6) -> None:
        self.linear_speed = linear_speed
        self.angular_speed = angular_speed
        self.hold_timeout = hold_timeout
        self.direction = (0, 0)
        self.last_press: float | None = None

    def press(self, key: str, now: float) -> None:
        if key in KEY_DIRECTIONS:
            self.direction = KEY_DIRECTIONS[key]
            self.last_press = now
        elif key in STOP_KEYS:
            self.stop()

    def stop(self) -> None:
        self.direction = (0, 0)
        self.last_press = None

    def velocity(self, now: float) -> tuple[float, float]:
        """(선속도 m/s, 각속도 rad/s). 입력이 끊긴 지 hold_timeout 이 지나면 0."""
        if self.last_press is None or now - self.last_press > self.hold_timeout:
            self.direction = (0, 0)
            return 0.0, 0.0
        lin, ang = self.direction
        return lin * self.linear_speed, ang * self.angular_speed
