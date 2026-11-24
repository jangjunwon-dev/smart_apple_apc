"""world_map(월드 → Nav2 지도) 테스트 (ROS 없이 실행)."""
import os
import tempfile

import numpy as np
import pytest

from apc_simulation.world_map import (
    build_grid, convex_hull, Grid, pose_matrix, Shapes, WorldReader, write_map,
)

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLDS = os.path.join(PKG, 'worlds')
MODELS = os.path.join(PKG, 'models')
MAPS = os.path.join(PKG, 'maps')

# 로봇 시작 위치(amr_robot.py)와 구역 중심(apc_amr/config/zones.yaml)은 비어 있어야 함
START = (1.5, 0.0)
ZONES = [(4.0, 2.0), (4.0, 0.0), (4.0, -2.0), (0.0, -3.0)]


def test_pose_matrix_yaw():
    m = pose_matrix('1 2 3 0 0 1.5707963')
    np.testing.assert_allclose(m @ [1, 0, 0, 1], [1, 3, 3, 1], atol=1e-6)


def test_convex_hull_square_ccw():
    h = convex_hull(np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0.5, 0.5]]))
    assert len(h) == 4


def test_thin_wall_is_not_missed():
    """격자(5 cm)보다 얇은 2 cm 벽도 점유로 칠해짐."""
    from apc_simulation.world_map import box_corners
    s = Shapes(solids=[box_corners(pose_matrix('0 0 0.5 0 0 0'), (2.0, 0.02, 1.0))])
    g = build_grid(s, res=0.05, bounds=(-2, -1, 2, 1), border=False)
    assert g.is_occupied(0.0, 0.0) and g.is_occupied(0.9, 0.0)
    assert not g.is_occupied(0.0, 0.2)


def test_height_band_excludes_floor_plate_and_ceiling():
    from apc_simulation.world_map import box_corners
    s = Shapes(solids=[box_corners(pose_matrix('0 0 0.005 0 0 0'), (1, 1, 0.01)),   # 바닥 표시판
                       box_corners(pose_matrix('1 0 2.0 0 0 0'), (0.5, 0.5, 0.1))])   # 천장
    g = build_grid(s, res=0.05, bounds=(-1, -1, 2, 1), border=False)
    assert not g.occ.any()


@pytest.fixture(scope='module', params=['apc_world.sdf', 'apc_world_v2_preview.sdf'])
def world_grid(request):
    shapes = WorldReader([MODELS]).read_world(os.path.join(WORLDS, request.param))
    return request.param, build_grid(shapes)


def test_start_and_zones_are_free(world_grid):
    name, g = world_grid
    for x, y in [START, *ZONES]:
        assert not g.is_occupied(x, y), f'{name}: ({x}, {y}) 가 막혀 있음'
    # 로봇(반경 약 0.22 m)이 시작 위치에서 들어갈 자리
    for dx in (-0.25, 0.25):
        for dy in (-0.25, 0.25):
            assert not g.is_occupied(START[0] + dx, START[1] + dy)


def test_conveyor_is_obstacle(world_grid):
    name, g = world_grid
    assert g.is_occupied(-2.0, 0.0), f'{name}: 컨베이어가 지도에 없음'


def test_committed_maps_are_up_to_date(world_grid):
    """월드를 바꾸고 지도를 다시 만들지 않은 경우를 잡음 → python3 scripts/gen_nav2_map.py"""
    name, g = world_grid
    stem = os.path.splitext(name)[0]
    with tempfile.TemporaryDirectory() as d:
        write_map(g, os.path.join(d, stem))
        new = open(os.path.join(d, stem + '.pgm'), 'rb').read().split(b'\n', 3)[3]
    old = open(os.path.join(MAPS, stem + '.pgm'), 'rb').read().split(b'\n', 3)[3]
    assert new == old, f'maps/{stem}.pgm 이 월드와 다름 — python3 scripts/gen_nav2_map.py 실행 후 커밋'


def test_yaml_origin_matches_grid(world_grid):
    name, g = world_grid
    text = open(os.path.join(MAPS, os.path.splitext(name)[0] + '.yaml'), encoding='utf-8').read()
    assert f'origin: [{g.xmin:.3f}, {g.ymin:.3f}, 0.0]' in text
    assert 'resolution: 0.05' in text and 'mode: trinary' in text


def test_grid_image_top_row_is_ymax():
    g = Grid(0.0, 0.0, 1.0, 2, 2)
    g.occ[1, 0] = True                     # y 가 큰 쪽(위) 왼쪽 칸
    assert g.image()[0, 0] == 0 and g.image()[1, 0] == 254
