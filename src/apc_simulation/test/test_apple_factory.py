"""apple_factory 단위 테스트."""
import random
import xml.etree.ElementTree as ET

import pytest

from apc_simulation.apple_factory import (
    ORANGE, RED, AppleSpec, apple_sdf, names_to_remove, random_apple)


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
