#!/usr/bin/env python3
"""APC 미리보기 월드 생성기: apc_world.sdf → apc_world_v2_preview.sdf

사용법 (저장소 루트에서):
  python3 scripts/gen_preview_world.py
  python3 scripts/gen_preview_world.py <원본.sdf> <결과.sdf>
기본값: src/apc_simulation/worlds/apc_world.sdf
        → src/apc_simulation/worlds/apc_world_v2_preview.sdf

apc_world.sdf 의 내용(물리·플러그인·조명·바닥·컨베이어·카메라·apple_sink·zone)은 그대로 복사하고,
</world> 바로 앞에 건물·입고·세척/건조 덮개·선별 터널·저온저장고·출하 장식을 덧붙인다.
apc_world.sdf 를 바꾸거나 배치를 바꾼 뒤에는 이 스크립트를 다시 실행할 것 (결과 SDF 는 손으로 고치지 말 것).

배치 규칙
  - 카메라(-2, 0, 1.6) 시야: 벨트면 y±0.46 x±0.35 / 바닥 y±0.92 x -2.69~-1.31
    → 덮개·터널은 이 시야 밖, visual 만(collision 없음), 그림자 없음
  - zone A/B/C/R 의 1 m x 1 m 바닥과 AMR 진입 쪽은 비움, AMR 통로 폭 1.5 m 이상
  - 외부 모델은 src/apc_simulation/models/ (출처: models/ATTRIBUTION.md)
확인: SDF_PATH=src/apc_simulation/models gz sdf -k <결과.sdf>
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLDS = os.path.join(ROOT, 'src', 'apc_simulation', 'worlds')

# ---------------- 치수 상수 (m) ----------------
WALL_RGBA = (0.86, 0.88, 0.9, 1)   # 외벽 (샌드위치 패널 느낌)
WALL_H = 3.0                       # 외벽 높이 (지붕 없음)
PANEL_RGBA = (0.95, 0.96, 0.97, 1)  # 저온저장고 단열 패널
COVER_RGBA = (0.2, 0.5, 0.9, 1)    # 세척·건조 덮개 (반투명 파랑)
STEEL_RGBA = (0.55, 0.58, 0.62, 1)  # 선별 터널
NOZZLE_RGBA = (0.7, 0.7, 0.75, 1)
LAMP_RGBA = (1, 1, 0.95, 1)
PALLET_Z = 0.072                   # euro_pallet 원점 높이 (메시 z -0.072~0.072)
PALLET_TOP = 0.144                 # 팔레트 윗면
CRATE_H = 0.28                     # apc_apple_crate 높이
CRATE_GAP = 0.005                  # 상자 단 사이 틈
RACK_LEVEL1_Z = 1.511              # Pallet_Rack 1단 빔 윗면

HEADER = """<?xml version="1.0" ?>
<!--
  Smart APC 미리보기 월드 v2 (팀 공유용, 팀 합의 전)
  - apc_world.sdf 의 물리·플러그인·조명·바닥·컨베이어·카메라·apple_sink·zone_A/B/C/R 을 그대로 복사
  - 추가: 건물 외벽(지붕 없음), 입고 구역, 세척·건조 덮개, 선별 터널, 저온저장고·출하 구역
  - 덮개·터널은 visual 만 (collision 없음, 그림자 없음) → 사과 흐름·카메라 영상 영향 최소화
  - 외부 모델은 src/apc_simulation/models/ (출처: models/ATTRIBUTION.md)
  - world name 은 apc_world 그대로 → sim.launch.py 브리지·사과 스포너 재사용
  실행: ros2 launch apc_simulation sim.launch.py world:=apc_world_v2_preview.sdf
-->
"""


def _material(rgba: tuple, emissive: str | None = None) -> str:
    r, g, b, a = rgba
    em = f'<emissive>{emissive}</emissive>' if emissive else ''
    return (f'<material><ambient>{r} {g} {b} {a}</ambient>'
            f'<diffuse>{r} {g} {b} {a}</diffuse>{em}</material>')


class WorldBuilder:
    """장식 SDF 조각을 줄 단위로 모은다."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.crate_count = 0

    def comment(self, text: str) -> None:
        self.lines.append(text)

    def box_model(self, name: str, xyz: str, size: str, rgba: tuple) -> None:
        """collision 있는 정적 박스 (벽·칸막이)."""
        self.lines.append(f'    <model name="{name}"><static>true</static>'
                          f'<pose>{xyz} 0 0 0</pose>')
        self.lines.append(
            f'      <link name="l"><collision name="c"><geometry><box><size>{size}</size>'
            f'</box></geometry></collision><visual name="v">'
            f'<geometry><box><size>{size}</size></box></geometry>{_material(rgba)}'
            f'</visual></link></model>')

    def visual_model(self, name: str, xyz: str, visuals: list[str]) -> None:
        """visual 만 있는 정적 모델 (덮개·터널)."""
        self.lines.append(f'    <model name="{name}"><static>true</static>'
                          f'<pose>{xyz} 0 0 0</pose>')
        self.lines.append('      <link name="l">')
        self.lines.extend(visuals)
        self.lines.append('      </link></model>')

    def include(self, name: str, uri: str, x: float, y: float,
                z: float = 0.0, yaw: float = 0.0) -> None:
        self.lines.append(
            f'    <include><name>{name}</name><uri>model://{uri}</uri><static>true</static>'
            f'<pose>{x:.3f} {y:.3f} {z:.3f} 0 0 {yaw:.4f}</pose></include>')

    def pallet_load(self, name: str, x: float, y: float, base_z: float,
                    long_axis_x: bool, layers: int) -> None:
        """팔레트(1.2 x 0.8) 1개 + 노란 상자 2 x 2 x layers 단."""
        yaw = math.pi / 2 if long_axis_x else 0.0   # euro_pallet 원본은 긴 변이 y
        self.include(f'{name}_pallet', 'euro_pallet', x, y, base_z + PALLET_Z, yaw)
        for k in range(layers):
            z = base_z + PALLET_TOP + CRATE_H / 2 + k * (CRATE_H + CRATE_GAP)
            for i, sx in enumerate((-1, 1)):
                for j, sy in enumerate((-1, 1)):
                    if long_axis_x:
                        cx, cy, cyaw = x + sx * 0.295, y + sy * 0.195, 0.0
                    else:
                        cx, cy, cyaw = x + sx * 0.195, y + sy * 0.295, math.pi / 2
                    self.include(f'{name}_crate_{k}{i}{j}', 'apc_apple_crate',
                                 cx, cy, z, cyaw)
                    self.crate_count += 1


def shadeless_visual(name: str, pose: str, geom: str, rgba: tuple,
                     transparency: float = 0.0, emissive: str | None = None) -> str:
    """그림자를 만들지 않는 visual (카메라 영상 밝기 유지용)."""
    tr = f'<transparency>{transparency}</transparency>' if transparency else ''
    return (f'        <visual name="{name}"><pose>{pose}</pose>'
            f'<cast_shadows>false</cast_shadows>{tr}'
            f'<geometry>{geom}</geometry>{_material(rgba, emissive)}</visual>')


def add_building(b: WorldBuilder) -> None:
    b.comment('    <!-- ===================== 미리보기 장식 (v2 preview) ===================== -->')
    b.comment('    <!-- 건물 외벽: 중심 (1.0, -0.5), 20 x 12 m → x -9~11, y -6.5~5.5, '
              '높이 3 m, 지붕 없음 -->')
    b.comment('    <!-- 서쪽 출입구(입고) y -1.5~1.5 / 동쪽 출입구(출하) y -2.25~1.25 -->')
    h = WALL_H
    b.box_model('wall_north', f'1.0 5.5 {h / 2}', f'20.2 0.2 {h}', WALL_RGBA)
    b.box_model('wall_south', f'1.0 -6.5 {h / 2}', f'20.2 0.2 {h}', WALL_RGBA)
    b.box_model('wall_west_s', f'-9.0 -4.0 {h / 2}', f'0.2 5.0 {h}', WALL_RGBA)
    b.box_model('wall_west_n', f'-9.0 3.5 {h / 2}', f'0.2 4.0 {h}', WALL_RGBA)
    b.box_model('wall_east_s', f'11.0 -4.375 {h / 2}', f'0.2 4.25 {h}', WALL_RGBA)
    b.box_model('wall_east_n', f'11.0 3.375 {h / 2}', f'0.2 4.25 {h}', WALL_RGBA)


def add_intake(b: WorldBuilder) -> None:
    b.comment('    <!-- 입고 구역 (x -8~-4.5): 팔레트 + 노란 사과 상자. '
              '서쪽 출입구 앞 통로 y -1.5~1.5 는 비움 -->')
    b.pallet_load('intake_1', -6.5, 2.8, 0.0, True, 3)
    b.pallet_load('intake_2', -6.5, -2.8, 0.0, True, 3)
    b.pallet_load('intake_3', -5.0, 3.8, 0.0, True, 2)
    b.include('pallet_jack', 'Pallet_Jack', -8.0, -4.5)


def add_wash_dry_cover(b: WorldBuilder) -> None:
    b.comment('    <!-- 세척·건조 덮개: x -3.45~-2.9, visual 만(collision 없음), '
              '그림자 없음 → 사과 흐름·카메라 밝기 영향 없음 -->')
    nozzle = '<cylinder><radius>0.015</radius><length>0.86</length></cylinder>'
    b.visual_model('wash_dry_cover', '-3.175 0 0', [
        shadeless_visual('roof', '0 0 1.35 0 0 0',
                         '<box><size>0.55 0.9 0.02</size></box>', COVER_RGBA, 0.6),
        shadeless_visual('side_l', '0 0.45 1.1 0 0 0',
                         '<box><size>0.55 0.02 0.5</size></box>', COVER_RGBA, 0.6),
        shadeless_visual('side_r', '0 -0.45 1.1 0 0 0',
                         '<box><size>0.55 0.02 0.5</size></box>', COVER_RGBA, 0.6),
        shadeless_visual('nozzle_1', '-0.15 0 1.25 1.5708 0 0', nozzle, NOZZLE_RGBA),
        shadeless_visual('nozzle_2', '0.12 0 1.25 1.5708 0 0', nozzle, NOZZLE_RGBA),
    ])


def add_grading_tunnel(b: WorldBuilder) -> None:
    b.comment('    <!-- 카메라 선별 터널: x -2.85~-1.15, visual 만, 그림자 없음.')
    b.comment('         카메라(z=1.6) 시야: 벨트면 y±0.46 x±0.35 / 바닥 y±0.92 x -2.69~-1.31')
    b.comment('         → 지붕 z 1.75 이상, 옆판 |y|=0.55 · z≥0.85, '
              '기둥 x -2.85/-1.15 (시야 밖) -->')
    visuals = [
        shadeless_visual('roof', '0 0 1.775 0 0 0',
                         '<box><size>1.7 1.14 0.05</size></box>', STEEL_RGBA),
        shadeless_visual('side_l', '0 0.55 1.3 0 0 0',
                         '<box><size>1.7 0.02 0.9</size></box>', STEEL_RGBA),
        shadeless_visual('side_r', '0 -0.55 1.3 0 0 0',
                         '<box><size>1.7 0.02 0.9</size></box>', STEEL_RGBA),
        shadeless_visual('lamp', '0 0 1.745 0 0 0',
                         '<box><size>1.2 0.06 0.01</size></box>', LAMP_RGBA,
                         emissive='1 1 0.95 1'),
    ]
    posts = [(-0.85, 0.55), (-0.85, -0.55), (0.85, 0.55), (0.85, -0.55)]
    for i, (px, py) in enumerate(posts):   # 기둥 단면 4 cm
        visuals.append(shadeless_visual(f'post_{i}', f'{px} {py} 0.875 0 0 0',
                                        '<box><size>0.04 0.04 1.75</size></box>',
                                        STEEL_RGBA))
    b.visual_model('grading_tunnel', '-2.0 0 0', visuals)


def add_cold_storage(b: WorldBuilder) -> None:
    b.comment('    <!-- 저온저장고 (zone A/B/C 뒤 x 4.6~6.0): 팔레트 랙 2개 + 칸막이(구역 사이) '
              '+ 뒤 단열벽.')
    b.comment('         구역 바닥(x 3.5~4.5)과 AMR 진입 쪽(x<3.5)은 비움 -->')
    for i, ry in enumerate((1.3, -1.3)):
        b.include(f'cold_rack_{i}', 'Pallet_Rack', 5.3, ry, 0.0, math.pi / 2)
        for j, s in enumerate((-1, 1)):
            py = ry + s * 0.62
            b.pallet_load(f'cold_rack_{i}_floor_{j}', 5.3, py, 0.0, True, 1)
            b.pallet_load(f'cold_rack_{i}_lv1_{j}', 5.3, py, RACK_LEVEL1_Z, True, 2)
    b.box_model('partition_AB', '4.1 1.0 1.0', '1.0 0.08 2.0', PANEL_RGBA)
    b.box_model('partition_BC', '4.1 -1.0 1.0', '1.0 0.08 2.0', PANEL_RGBA)
    b.box_model('cold_wall', '6.25 0 1.5', '0.1 6.0 3.0', PANEL_RGBA)


def add_reject(b: WorldBuilder) -> None:
    b.comment('    <!-- 비상품 R 뒤 (y -4.99~-3.61): 팔레트 랙 1개. '
              '구역 바닥(y -3.5~-2.5)과 진입 쪽(+y)은 비움 -->')
    b.include('reject_rack', 'Pallet_Rack', 0.0, -4.3)
    for j, s in enumerate((-1, 1)):
        b.pallet_load(f'reject_rack_floor_{j}', s * 0.62, -4.3, 0.0, False, 1)


def add_shipping(b: WorldBuilder) -> None:
    b.comment('    <!-- 출하 구역 (x 7~10.5): 출하 대기 팔레트(동쪽 출입구 남쪽) '
              '+ 지게차(출입구 북쪽 외벽에 붙임, collision 유지) -->')
    b.pallet_load('ship_1', 8.5, -4.0, 0.0, True, 2)
    b.pallet_load('ship_2', 8.5, -5.3, 0.0, True, 2)
    # Forklift collision bbox: x ±0.57, y -0.87~2.29
    # → 원점 (10.2, 2.75) 이면 x 9.63~10.77, y 1.88~5.04 (출입구 북쪽 끝 y=1.25 침범 안 함)
    b.include('forklift', 'Forklift', 10.2, 2.75)


def build(base: str) -> tuple[str, int]:
    """원본 월드 문자열 → (미리보기 월드 문자열, 상자 개수)."""
    b = WorldBuilder()
    add_building(b)
    add_intake(b)
    add_wash_dry_cover(b)
    add_grading_tunnel(b)
    add_cold_storage(b)
    add_reject(b)
    add_shipping(b)
    body = '\n'.join(b.lines)

    result = HEADER + base[base.index('<sdf'):]   # 원본 헤더 주석만 교체
    idx = result.rindex('  </world>')
    return result[:idx] + '\n' + body + '\n' + result[idx:], b.crate_count


def main() -> None:
    if len(sys.argv) == 3:
        src, dst = sys.argv[1], sys.argv[2]
    elif len(sys.argv) == 1:
        src = os.path.join(WORLDS, 'apc_world.sdf')
        dst = os.path.join(WORLDS, 'apc_world_v2_preview.sdf')
    else:
        sys.exit('사용법: python3 scripts/gen_preview_world.py [<원본.sdf> <결과.sdf>]')
    with open(src, encoding='utf-8') as f:
        base = f.read()
    world, crates = build(base)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(world)
    print(f'생성: {dst} (사과 상자 {crates}개)')


if __name__ == '__main__':
    main()
