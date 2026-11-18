"""Gazebo 월드의 적재 구역 좌표와 apc_amr/config/zones.yaml 이 일치하는지 검사.

zones.yaml 은 🅑(apc_amr) 소유 파일이므로 이 테스트는 읽기만 한다.
"""
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

TOLERANCE_M = 0.01
ZONE_IDS = ('A', 'B', 'C', 'R')

PKG_DIR = Path(__file__).resolve().parents[1]           # src/apc_simulation
SRC_DIR = PKG_DIR.parent                                 # src/
ZONES_YAML = SRC_DIR / 'apc_amr' / 'config' / 'zones.yaml'
WORLD_FILES = ('apc_world.sdf', 'apc_world_v2_preview.sdf')


def load_yaml_zones(path: Path) -> dict[str, tuple[float, float]]:
    """zones.yaml 에서 zone_ZONE_<id>_xy 값을 읽어 {id: (x, y)} 로 반환."""
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    params = data['task_manager_node']['ros__parameters']
    zones = {}
    for zid in ZONE_IDS:
        key = f'zone_ZONE_{zid}_xy'
        assert key in params, f'{path.name} 에 {key} 가 없습니다'
        x, y = params[key]
        zones[zid] = (float(x), float(y))
    return zones


def load_world_zones(path: Path) -> dict[str, tuple[float, float]]:
    """SDF 월드에서 zone_<id> 모델의 pose x, y 를 읽어 {id: (x, y)} 로 반환."""
    root = ET.parse(path).getroot()
    zones = {}
    for zid in ZONE_IDS:
        name = f'zone_{zid}'
        model = root.find(f".//world/model[@name='{name}']")
        assert model is not None, f'{path.name} 에 모델 {name} 이 없습니다'
        pose = model.find('pose')
        assert pose is not None and pose.text, f'{path.name} 의 {name} 에 <pose> 가 없습니다'
        values = [float(v) for v in pose.text.split()]
        zones[zid] = (values[0], values[1])
    return zones


@pytest.fixture(scope='module')
def yaml_zones() -> dict[str, tuple[float, float]]:
    assert ZONES_YAML.is_file(), f'zones.yaml 을 찾을 수 없습니다: {ZONES_YAML}'
    return load_yaml_zones(ZONES_YAML)


@pytest.mark.parametrize('world_file', WORLD_FILES)
def test_world_zones_match_zones_yaml(world_file: str, yaml_zones) -> None:
    world_path = PKG_DIR / 'worlds' / world_file
    world_zones = load_world_zones(world_path)
    mismatches = []
    for zid in ZONE_IDS:
        wx, wy = world_zones[zid]
        yx, yy = yaml_zones[zid]
        if not (math.isclose(wx, yx, abs_tol=TOLERANCE_M)
                and math.isclose(wy, yy, abs_tol=TOLERANCE_M)):
            mismatches.append(
                f'zone_{zid}: 월드=({wx}, {wy}) / zones.yaml=({yx}, {yy})')
    assert not mismatches, (
        f'{world_file} 구역 좌표가 zones.yaml 과 다릅니다 (허용 오차 {TOLERANCE_M} m):\n  '
        + '\n  '.join(mismatches))
