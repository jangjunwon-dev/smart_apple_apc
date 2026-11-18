"""apple_factory 단위 테스트."""
import math
import os
import random
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest

from apc_simulation.apple_factory import (
    ORANGE, RED, YCB_MESH_URI, AppleSpec, apple_sdf, names_to_remove, random_apple)

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')
YCB_DIR = os.path.join(MODELS_DIR, 'ycb_apple')


def test_random_apple_ranges():
    rng = random.Random(0)
    for _ in range(500):
        spec = random_apple(rng, 0.035, 0.048)
        assert 0.035 <= spec.radius <= 0.048
        r, g, b = spec.color
        # 빨강~주황: R 이 가장 크고, G 는 주황 이하
        assert r > g and r > b
        assert g <= ORANGE[1] + 1e-9
        assert 0.0 <= b <= max(RED[2], ORANGE[2]) + 1e-9


def test_random_apple_reproducible():
    a = random_apple(random.Random(42))
    b = random_apple(random.Random(42))
    assert a == b


def test_random_apple_invalid_range():
    with pytest.raises(ValueError):
        random_apple(random.Random(0), 0.05, 0.04)


def test_collision_bottom_matches_visual_bottom():
    spec = AppleSpec(radius=0.04, color=(0.8, 0.1, 0.05))
    bottom = spec.collision_offset_z - spec.collision_height / 2.0
    assert bottom == pytest.approx(-spec.radius)


def test_apple_sdf_parses():
    spec = AppleSpec(radius=0.04, color=(0.8, 0.1, 0.05))
    root = ET.fromstring(apple_sdf('apple_0001', spec))
    model = root.find('model')
    assert model.get('name') == 'apple_0001'
    assert float(model.find('link/visual/geometry/sphere/radius').text) == pytest.approx(0.04)
    assert model.find('link/collision/geometry/cylinder') is not None
    z = float(model.find('link/collision/pose').text.split()[2])
    assert z == pytest.approx(spec.collision_offset_z, abs=1e-5)
    assert float(model.find('link/inertial/mass').text) > 0


def test_names_to_remove():
    alive = ['apple_0001', 'apple_0002', 'apple_0003']
    # 컨베이어 등 다른 모델은 무시, 삭제 요청 중인 것과 중복은 제외
    detected = ['conveyor', 'apple_0001', 'apple_0002', 'apple_0001', 'apple_9999']
    assert names_to_remove(detected, alive, removing=['apple_0002']) == ['apple_0001']
    assert names_to_remove([], alive, removing=[]) == []


# ---------- apple_model='ycb' (YCB 013_apple 메시) ----------
SPEC = AppleSpec(radius=0.042, color=(0.8, 0.1, 0.05))


def test_sphere_is_default():
    assert apple_sdf('apple_0001', SPEC) == apple_sdf('apple_0001', SPEC, 'sphere')
    assert apple_sdf('apple_0001', SPEC) == apple_sdf('apple_0001', SPEC, 'sphere', yaw=1.0)


def test_ycb_visual_is_scaled_mesh_with_yaw():
    yaw = 1.2345
    link = ET.fromstring(apple_sdf('apple_0007', SPEC, 'ycb', yaw)).find('model/link')
    vis = link.find('visual')
    assert vis.find('geometry/mesh/uri').text == YCB_MESH_URI
    scale = [float(v) for v in vis.find('geometry/mesh/scale').text.split()]
    assert scale == pytest.approx([SPEC.radius] * 3, abs=1e-5)
    pose = [float(v) for v in vis.find('pose').text.split()]
    assert pose == pytest.approx([0, 0, 0, 0, 0, yaw], abs=1e-5)
    assert vis.find('geometry/sphere') is None
    assert vis.find('material') is None        # 스캔 텍스처를 덮어쓰지 않음


def test_ycb_keeps_collision_and_inertial():
    """외형만 바뀌고 물리(원기둥 collision·질량·관성)는 sphere 와 같아야 함."""
    sph = ET.fromstring(apple_sdf('apple_0001', SPEC, 'sphere')).find('model/link')
    ycb = ET.fromstring(apple_sdf('apple_0001', SPEC, 'ycb', math.pi)).find('model/link')
    for tag in ('collision', 'inertial'):
        assert ET.tostring(ycb.find(tag)) == ET.tostring(sph.find(tag))


def test_unknown_apple_model():
    with pytest.raises(ValueError):
        apple_sdf('apple_0001', SPEC, 'banana')


def test_ycb_model_folder():
    assert os.path.isfile(os.path.join(YCB_DIR, 'model.config'))
    assert os.path.isfile(os.path.join(YCB_DIR, 'model.sdf'))
    assert os.path.isfile(os.path.join(YCB_DIR, 'LICENSE.txt'))
    mesh = os.path.join(YCB_DIR, YCB_MESH_URI.split('model://ycb_apple/')[1])
    assert os.path.isfile(mesh)
    total = sum(os.path.getsize(os.path.join(d, f))
                for d, _, files in os.walk(YCB_DIR) for f in files)
    assert total <= 5 * 1024 * 1024


@pytest.mark.skipif(shutil.which('gz') is None, reason='gz 명령 없음')
@pytest.mark.parametrize('apple_model', ['sphere', 'ycb'])
def test_generated_sdf_passes_gz_check(tmp_path, apple_model):
    path = tmp_path / f'{apple_model}.sdf'
    path.write_text(apple_sdf('apple_0001', SPEC, apple_model, 0.5))
    env = dict(os.environ, SDF_PATH=MODELS_DIR, GZ_SIM_RESOURCE_PATH=MODELS_DIR)
    res = subprocess.run(['gz', 'sdf', '-k', str(path)], env=env,
                         capture_output=True, text=True, timeout=60)
    assert res.returncode == 0 and 'Valid' in res.stdout, res.stdout + res.stderr
