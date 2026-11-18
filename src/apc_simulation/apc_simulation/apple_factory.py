"""사과 모델(SDF) 생성 로직 — ROS 의존 없음 (pytest 대상).

사과는 크기(반지름)와 색(빨강~주황)을 무작위로 만들어 비전 파트가 등급 차이를 볼 수 있게 한다.
- visual: 구(sphere) — 카메라에는 둥근 사과로 보임
- collision: 납작한 원기둥 — 구는 벨트 위에서 굴러 속도가 줄고 옆으로 흐르므로
  바닥이 평평한 원기둥으로 벨트 속도 그대로 미끄러짐 없이 이동시킴
"""
from __future__ import annotations

import math
import random
from collections.abc import Iterable
from dataclasses import dataclass

# 빨강 → 주황 색 범위 (RGB, 0~1)
RED = (0.80, 0.05, 0.04)
ORANGE = (0.85, 0.40, 0.05)

APPLE_DENSITY = 850.0           # kg/m^3 (사과 평균 밀도 근사)
COLLISION_HEIGHT_RATIO = 1.6    # 원기둥 높이 = 반지름 × 비율


@dataclass(frozen=True)
class AppleSpec:
    """사과 1개의 물리·외형 속성."""

    radius: float                       # m
    color: tuple[float, float, float]   # RGB 0~1

    @property
    def mass(self) -> float:
        return APPLE_DENSITY * 4.0 / 3.0 * math.pi * self.radius ** 3

    @property
    def collision_height(self) -> float:
        return COLLISION_HEIGHT_RATIO * self.radius

    @property
    def collision_offset_z(self) -> float:
        """원기둥 바닥이 구의 바닥(중심 -r)과 같도록 원기둥 중심을 내리는 양."""
        return -self.radius + self.collision_height / 2.0


def random_apple(rng: random.Random, r_min: float = 0.035, r_max: float = 0.048) -> AppleSpec:
    """반지름·색을 무작위로 정한 사과 사양을 만든다."""
    if r_min <= 0 or r_max < r_min:
        raise ValueError(f'잘못된 반지름 범위: {r_min} ~ {r_max}')
    radius = rng.uniform(r_min, r_max)
    t = rng.random()                    # 0=빨강, 1=주황
    shade = rng.uniform(0.85, 1.0)      # 약간의 밝기 차이
    color = tuple(
        min(1.0, (RED[i] + (ORANGE[i] - RED[i]) * t) * shade) for i in range(3))
    return AppleSpec(radius=radius, color=color)  # type: ignore[arg-type]


def apple_sdf(name: str, spec: AppleSpec) -> str:
    """Gazebo /world/<w>/create 에 넘길 사과 모델 SDF 문자열."""
    r = spec.radius
    m = spec.mass
    i = 0.4 * m * r * r                 # 구의 관성 모멘트
    rgb = ' '.join(f'{c:.3f}' for c in spec.color)
    return f"""<?xml version="1.0" ?>
<sdf version="1.9">
  <model name="{name}">
    <link name="link">
      <inertial>
        <mass>{m:.5f}</mass>
        <inertia>
          <ixx>{i:.8f}</ixx><ixy>0</ixy><ixz>0</ixz>
          <iyy>{i:.8f}</iyy><iyz>0</iyz><izz>{i:.8f}</izz>
        </inertia>
      </inertial>
      <collision name="collision">
        <pose>0 0 {spec.collision_offset_z:.5f} 0 0 0</pose>
        <geometry>
          <cylinder><radius>{r:.5f}</radius><length>{spec.collision_height:.5f}</length></cylinder>
        </geometry>
      </collision>
      <visual name="visual">
        <geometry><sphere><radius>{r:.5f}</radius></sphere></geometry>
        <material><ambient>{rgb} 1</ambient><diffuse>{rgb} 1</diffuse></material>
      </visual>
    </link>
  </model>
</sdf>
"""


def names_to_remove(detected: Iterable[str], alive: Iterable[str],
                    removing: Iterable[str]) -> list[str]:
    """수거 지점 센서에 잡힌 모델 중 내가 생성했고 아직 삭제 요청 전인 사과 이름."""
    alive_set = set(alive)
    removing_set = set(removing)
    result: list[str] = []
    for name in detected:
        if name in alive_set and name not in removing_set and name not in result:
            result.append(name)
    return result
