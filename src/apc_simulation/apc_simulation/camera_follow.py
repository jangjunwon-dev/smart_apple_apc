"""Gazebo GUI 시점(카메라)이 로봇을 따라가게 하는 gz 명령 만들기 — ROS 의존 없음 (pytest 대상).

Gazebo GUI 의 CameraTracking 플러그인이 버전에 따라 다른 이름으로 기능을 연다.
  - 예전(gz-gui 8 이하):   서비스 /gui/follow (gz.msgs.StringMsg, 빈 문자열이면 해제)
  - 새 방식(gz-gui 8.2+):  /gui/track (gz.msgs.CameraTrack) — 서비스 또는 토픽
실행 중인 GUI 가 어떤 것을 열었는지 `gz service -l` / `gz topic -l` 결과로 골라서 명령을 만든다.
GUI 가 없으면(headless) 어느 것도 없으므로 None.
"""
from __future__ import annotations

FOLLOW_SERVICE = '/gui/follow'
TRACK_NAME = '/gui/track'

# 로봇 뒤쪽 위에서 내려다보는 위치 (로봇 기준 m) / 따라가는 부드러움(0~1, 작을수록 천천히)
DEFAULT_OFFSET = (-1.5, 0.0, 1.2)
DEFAULT_PGAIN = 0.05


def _track_request(target: str, follow: bool, offset: tuple[float, float, float],
                   pgain: float) -> str:
    if not follow:
        return 'track_mode: NONE'
    x, y, z = offset
    return (f'track_mode: FOLLOW, follow_target: {{name: "{target}"}}, '
            f'follow_offset: {{x: {x}, y: {y}, z: {z}}}, follow_pgain: {pgain}')


def follow_command(services: list[str], topics: list[str], target: str, follow: bool,
                   offset: tuple[float, float, float] = DEFAULT_OFFSET,
                   pgain: float = DEFAULT_PGAIN) -> list[str] | None:
    """따라가기 켜기(follow=True)/끄기 gz 명령 인자 목록. 쓸 수 있는 방법이 없으면 None."""
    if TRACK_NAME in services:
        return ['gz', 'service', '-s', TRACK_NAME,
                '--reqtype', 'gz.msgs.CameraTrack', '--reptype', 'gz.msgs.Boolean',
                '--timeout', '2000', '--req', _track_request(target, follow, offset, pgain)]
    if TRACK_NAME in topics:
        return ['gz', 'topic', '-t', TRACK_NAME, '-m', 'gz.msgs.CameraTrack',
                '-p', _track_request(target, follow, offset, pgain)]
    if FOLLOW_SERVICE in services:
        return ['gz', 'service', '-s', FOLLOW_SERVICE,
                '--reqtype', 'gz.msgs.StringMsg', '--reptype', 'gz.msgs.Boolean',
                '--timeout', '2000', '--req', f'data: "{target if follow else ""}"']
    return None


def parse_list(output: str) -> list[str]:
    """`gz service -l` / `gz topic -l` 출력 → 이름 목록."""
    return [line.strip() for line in output.splitlines() if line.strip().startswith('/')]
