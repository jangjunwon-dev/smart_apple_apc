"""camera_follow 테스트 (ROS·Gazebo 없이 실행)."""
from apc_simulation.camera_follow import follow_command, parse_list


def test_parse_list():
    out = '/gui/track\n/world/apc_world/create\n\nsome text\n'
    assert parse_list(out) == ['/gui/track', '/world/apc_world/create']


def test_track_service_preferred():
    cmd = follow_command(['/gui/track', '/gui/follow'], [], 'amr_1', True)
    assert cmd[:4] == ['gz', 'service', '-s', '/gui/track']
    req = cmd[cmd.index('--req') + 1]
    assert 'track_mode: FOLLOW' in req and 'name: "amr_1"' in req


def test_track_off():
    cmd = follow_command(['/gui/track'], [], 'amr_1', False)
    assert cmd[cmd.index('--req') + 1] == 'track_mode: NONE'


def test_track_topic():
    cmd = follow_command([], ['/gui/track'], 'amr_1', True)
    assert cmd[:4] == ['gz', 'topic', '-t', '/gui/track']


def test_old_follow_service():
    on = follow_command(['/gui/follow'], [], 'amr_1', True)
    off = follow_command(['/gui/follow'], [], 'amr_1', False)
    assert on[on.index('--req') + 1] == 'data: "amr_1"'
    assert off[off.index('--req') + 1] == 'data: ""'


def test_no_gui():
    assert follow_command(['/world/apc_world/create'], ['/clock'], 'amr_1', True) is None


SAMPLE_POSE = """header {
  stamp {
    sec: 12
  }
}
position {
  x: -1.5
  y: 2
  z: 1.2
}
orientation {
  z: 0.38
  w: 0.92
}
"""


def test_parse_pose_with_omitted_zeros():
    from apc_simulation.camera_follow import parse_pose
    assert parse_pose(SAMPLE_POSE) == ((-1.5, 2.0, 1.2), (0.0, 0.0, 0.38, 0.92))


def test_parse_pose_bad():
    from apc_simulation.camera_follow import parse_pose
    assert parse_pose('') is None
    assert parse_pose('position {\n  x: 1\n}\n') is None        # orientation 없음


def test_move_to_pose_command():
    from apc_simulation.camera_follow import move_to_pose_command
    cmd = move_to_pose_command(((1.0, 2.0, 3.0), (0.0, 0.0, 0.0, 1.0)))
    assert cmd[:4] == ['gz', 'service', '-s', '/gui/move_to/pose']
    req = cmd[cmd.index('--req') + 1]
    assert 'position: {x: 1.0, y: 2.0, z: 3.0}' in req and 'w: 1.0' in req
