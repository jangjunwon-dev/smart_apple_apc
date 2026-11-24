#!/usr/bin/env python3
"""APC 미리보기 월드 생성기: apc_world.sdf → apc_world_v2_preview.sdf

사용법 (저장소 루트에서):
  python3 scripts/gen_preview_world.py
  python3 scripts/gen_preview_world.py <원본.sdf> <결과.sdf>
기본값: src/apc_simulation/worlds/apc_world.sdf
        → src/apc_simulation/worlds/apc_world_v2_preview.sdf

apc_world.sdf 의 내용(물리·플러그인·조명·바닥·컨베이어·카메라·apple_sink·zone)은 그대로 복사하고,
</world> 바로 앞에 건물·입고·세척/건조 덮개·선별 터널·선별 라인 부속·저온저장고·출하 장식을 덧붙인다.
텍스처를 반복해서 입히는 바닥·벽·철골은 OBJ 메시로 함께 생성한다
(src/apc_simulation/models/apc_preview_assets/meshes/, 텍스처는 같은 폴더 materials/textures/).
apc_world.sdf 를 바꾸거나 배치를 바꾼 뒤에는 이 스크립트를 다시 실행할 것 (결과 SDF·OBJ 는 손으로 고치지 말 것).

배치 규칙
  - 카메라(-2, 0, 1.6, hfov 0.3) 시야: 벨트면 y±0.12 x±0.09 / 바닥 y±0.24 x -2.18~-1.82
    → 새 부속은 x -2.24~-1.76 (y ±0.27, 바닥까지) 에 두지 않음
    (기존 부속은 예전 넓은 시야(hfov 1.047) 기준 x -2.75~-1.25 밖에 배치되어 있음)
    → 바닥 구멍 x -3.0~-1.0, y -1.2~1.2 는 에폭시를 깔지 않고 기존 ground_plane 색 유지
  - 장식 visual 은 모두 그림자 없음(cast_shadows false), 조명 추가 없음
  - 선별 라인 부속은 visual 만. AMR 이 부딪힐 수 있는 다리·제어반만 바닥~0.5 m collision
    (z 0.6 이상, 컨베이어 몸체 |y| < 0.3 안쪽은 collision 금지)
  - zone A/B/C/R 의 1 m x 1 m 바닥과 AMR 진입 쪽은 비움, AMR 통로 폭 1.5 m 이상 (실행 시 확인 출력)
  - 외부 모델·텍스처는 src/apc_simulation/models/ (출처: models/ATTRIBUTION.md)
확인: SDF_PATH=src/apc_simulation/models gz sdf -k <결과.sdf>
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLDS = os.path.join(ROOT, 'src', 'apc_simulation', 'worlds')
ASSETS = os.path.join(ROOT, 'src', 'apc_simulation', 'models', 'apc_preview_assets')
ASSET_URI = 'model://apc_preview_assets'
TEX_URI = f'{ASSET_URI}/materials/textures'

# ---------------- 색 ----------------
PANEL_RGBA = (0.95, 0.96, 0.97, 1)  # 칸막이 (단열 패널)
COVER_RGBA = (0.2, 0.5, 0.9, 1)    # 세척·건조 덮개 (반투명 파랑)
STEEL_RGBA = (0.55, 0.58, 0.62, 1)  # 선별 터널
NOZZLE_RGBA = (0.7, 0.7, 0.75, 1)
LAMP_RGBA = (1, 1, 0.95, 1)
FRAME_RGBA = (0.52, 0.57, 0.63, 1)  # 지붕 철골 (회청색 도장)
SS_RGBA = (0.78, 0.8, 0.82, 1)     # 스테인리스 (선별 라인 다리·프레임)
ROLLER_RGBA = (0.62, 0.64, 0.66, 1)
SAFETY_RGBA = (0.95, 0.78, 0.05, 1)  # 노란 안전선
SEAM_RGBA = (0.62, 0.64, 0.66, 1)  # 단열 패널 이음줄
DOOR_RGBA = (0.9, 0.92, 0.93, 1)   # 저장고 문
DOOR_TRIM_RGBA = (0.45, 0.48, 0.52, 1)
SHUTTER_RGBA = (0.7, 0.72, 0.74, 1)
CABINET_RGBA = (0.85, 0.85, 0.8, 1)
SCREEN_RGBA = (0.05, 0.1, 0.2, 1)
GRADE_RGBA = {   # zone 색과 맞춤 (apc_world.sdf zone_A/B/C/R)
    'special': (0.1, 0.6, 0.1, 1),
    'good': (0.1, 0.3, 0.8, 1),
    'normal': (0.9, 0.7, 0.1, 1),
    'reject': (0.7, 0.1, 0.1, 1),
}

# ---------------- 치수 상수 (m) ----------------
WALL_H = 5.0                       # 외벽 높이 (지붕판 없음, 위에 철골 트러스)
DOOR_H = 3.5                       # 출입구 높이 (위는 상인방 패널)
PALLET_Z = 0.072                   # euro_pallet 원점 높이 (메시 z -0.072~0.072)
PALLET_TOP = 0.144                 # 팔레트 윗면
CRATE_H = 0.28                     # apc_apple_crate 높이
CRATE_GAP = 0.005                  # 상자 단 사이 틈
RACK_LEVEL1_Z = 1.511              # Pallet_Rack 1단 빔 윗면
FLOOR_TOP = 0.004                  # 에폭시 윗면 (zone 윗면 0.01 보다 낮게)
FLOOR_HOLE = (-3.0, -1.0, -1.2, 1.2)   # 기존 바닥색 유지 구역 x0, x1, y0, y1
SAFETY_W = 0.1                     # 안전선 폭
CAM_KEEP_OUT = (-2.24, -1.76, -0.27, 0.27)  # 카메라 시야(바닥까지 + 여유): 새 부속 금지 구역
LEG_COLL_H = 0.5                   # 다리·제어반 collision 높이 (바닥~0.5 m)
AISLE_MIN = 1.5

# 건물 외벽: 중심 (1.0, -0.5), 20 x 12 m → x -9~11, y -6.5~5.5
# 서쪽 출입구 y -1.5~1.5 / 동쪽 출입구 y -2.25~1.25
WALLS = [   # (이름, 중심 x, 중심 y, 크기 x, 크기 y)
    ('wall_north', 1.0, 5.5, 20.2, 0.2),
    ('wall_south', 1.0, -6.5, 20.2, 0.2),
    ('wall_west_s', -9.0, -4.0, 0.2, 5.0),
    ('wall_west_n', -9.0, 3.5, 0.2, 4.0),
    ('wall_east_s', 11.0, -4.375, 0.2, 4.25),
    ('wall_east_n', 11.0, 3.375, 0.2, 4.25),
]
DOORS = [   # (벽 x, y0, y1, 안쪽 방향 부호)
    (-9.0, -1.5, 1.5, 1),
    (11.0, -2.25, 1.25, -1),
]

# 저온저장고 방: x 6.25~9.0, y -3~3, 높이 4, 동쪽 면에 큰 문(y -1.5~1.0, 높이 3)
COLD_X0, COLD_X1, COLD_Y0, COLD_Y1 = 6.25, 9.0, -3.0, 3.0
COLD_H, COLD_T = 4.0, 0.15
COLD_DOOR_Y0, COLD_DOOR_Y1, COLD_DOOR_H = -1.5, 1.0, 3.0

# 지붕 트러스 (x 위치), 경간 y -6.5~5.5, 용마루 y -0.5
TRUSS_X = (-8.85, -5.0, -1.0, 3.0, 7.0, 10.85)
TRUSS_Y0, TRUSS_Y1, RIDGE_Y = -6.5, 5.5, -0.5
TRUSS_PANEL = 1.5
EAVE_Z, RIDGE_Z = 5.1, 6.2
COLUMN_Y = (5.3, -6.3)             # 벽 안쪽면에 붙인 기둥

# 선별 라인 부속
LINE_LEG_X = (-3.4, -2.95, -1.05, -0.6)
LINE_LEG_Y = 0.29
LINE_SEGMENTS = ((-3.5, -2.75), (-1.25, -0.5))   # 카메라 시야 밖 컨베이어 구간
ROLLER_X0, ROLLER_X1, ROLLER_HALF_W = -4.7, -3.5, 0.36
CHUTE_W = 0.3
CHUTES = [   # (중심 x, 방향 y 부호, 등급)
    (-1.05, 1, 'special'), (-0.7, 1, 'good'),
    (-1.05, -1, 'normal'), (-0.7, -1, 'reject'),
]
CHUTE_IN = (0.29, 0.76)            # 컨베이어 옆 (|y|, z)
CHUTE_OUT = (0.85, 0.45)           # 바깥 끝 (|y|, z)
CABINET = (-4.3, -0.6, 0.6, 0.3, 1.6)   # 제어반 중심 x, y, 크기 x, y, z (입고 롤러 남쪽에 붙임)

# 통로 확인용 장애물 (x0, x1, y0, y1)
INTAKE_PALLETS = {'intake_1': (-6.5, 2.8), 'intake_2': (-6.5, -2.8), 'intake_3': (-5.0, 3.8)}

HEADER = """<?xml version="1.0" ?>
<!--
  Smart APC 미리보기 월드 v2 (팀 공유용, 팀 합의 전) — scripts/gen_preview_world.py 로 생성
  - apc_world.sdf 의 물리·플러그인·조명·바닥·컨베이어·카메라·apple_sink·zone_A/B/C/R 을 그대로 복사
  - 추가: 초록 에폭시 바닥(카메라 아래 x -3~-1, y ±1.2 는 기존 바닥색 + 노란 안전선),
    흰 샌드위치 패널 외벽(5 m), 철골 트러스(지붕판 없음), 입고 구역, 세척·건조 덮개, 선별 터널,
    선별 라인 부속(다리·롤러·가이드·등급별 배출 슈트·제어반), 단열 패널 저온저장고, 출하 구역
  - 장식은 그림자 없음, 조명 추가 없음. 선별 라인 부속은 visual 만(다리·제어반만 바닥~0.5 m collision)
  - 외부 모델·텍스처는 src/apc_simulation/models/ (출처: models/ATTRIBUTION.md)
  - world name 은 apc_world 그대로 → sim.launch.py 브리지·사과 스포너 재사용
  실행: ros2 launch apc_simulation sim.launch.py world:=apc_world_v2_preview.sdf
-->
"""


# =====================================================================
# SDF 조각
# =====================================================================
def _material(rgba: tuple, emissive: str | None = None) -> str:
    r, g, b, a = rgba
    em = f'<emissive>{emissive}</emissive>' if emissive else ''
    return (f'<material><ambient>{r} {g} {b} {a}</ambient>'
            f'<diffuse>{r} {g} {b} {a}</diffuse>{em}</material>')


def _pbr_material(rgba: tuple, albedo: str | None, normal: str | None,
                  roughness_map: str | None, roughness: float, metalness: float) -> str:
    """텍스처 PBR 재질. diffuse 색이 albedo 텍스처에 곱해진다."""
    r, g, b, a = rgba
    maps = ''
    if albedo:
        maps += f'<albedo_map>{TEX_URI}/{albedo}</albedo_map>'
    if normal:
        maps += f'<normal_map>{TEX_URI}/{normal}</normal_map>'
    if roughness_map:
        maps += f'<roughness_map>{TEX_URI}/{roughness_map}</roughness_map>'
    return (f'<material><ambient>{r} {g} {b} {a}</ambient><diffuse>{r} {g} {b} {a}</diffuse>'
            f'<specular>0.2 0.2 0.2 1</specular>'
            f'<pbr><metal>{maps}<roughness>{roughness}</roughness>'
            f'<metalness>{metalness}</metalness></metal></pbr></material>')


EPOXY_MAT = _pbr_material((0.3, 0.7, 0.42, 1), 'Concrete034_1K-JPG_Color.jpg',
                          'Concrete034_1K-JPG_NormalGL.jpg',
                          'Concrete034_1K-JPG_Roughness.jpg', 0.45, 0.0)
SANDWICH_MAT = _pbr_material((1, 1, 1, 1), 'CorrugatedSteel007A_1K-JPG_Color_white.jpg',
                             'CorrugatedSteel007A_1K-JPG_NormalGL.jpg',
                             'CorrugatedSteel007A_1K-JPG_Roughness.jpg', 0.8, 0.2)
INSULATED_MAT = _pbr_material((0.95, 0.96, 0.97, 1), None, 'Plastic010_1K-JPG_NormalGL.jpg',
                              'Plastic010_1K-JPG_Roughness.jpg', 0.7, 0.0)


def _box(size: tuple) -> str:
    return f'<box><size>{size[0]:.4g} {size[1]:.4g} {size[2]:.4g}</size></box>'


def _pose(x: float, y: float, z: float, roll: float = 0.0, pitch: float = 0.0,
          yaw: float = 0.0) -> str:
    return f'{x:.4f} {y:.4f} {z:.4f} {roll:.4f} {pitch:.4f} {yaw:.4f}'


def shadeless_visual(name: str, pose: str, geom: str, rgba: tuple,
                     transparency: float = 0.0, emissive: str | None = None) -> str:
    """그림자를 만들지 않는 visual (카메라 영상 밝기 유지용)."""
    tr = f'<transparency>{transparency}</transparency>' if transparency else ''
    return (f'        <visual name="{name}"><pose>{pose}</pose>'
            f'<cast_shadows>false</cast_shadows>{tr}'
            f'<geometry>{geom}</geometry>{_material(rgba, emissive)}</visual>')


def mesh_visual(name: str, mesh: str, material: str) -> str:
    return (f'        <visual name="{name}"><cast_shadows>false</cast_shadows>'
            f'<geometry><mesh><uri>{ASSET_URI}/meshes/{mesh}</uri></mesh></geometry>'
            f'{material}</visual>')


def collision(name: str, pose: str, size: tuple) -> str:
    return (f'        <collision name="{name}"><pose>{pose}</pose>'
            f'<geometry>{_box(size)}</geometry></collision>')


class WorldBuilder:
    """장식 SDF 조각을 줄 단위로 모은다."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.crate_count = 0

    def comment(self, text: str) -> None:
        self.lines.append(text)

    def box_model(self, name: str, xyz: str, size: str, rgba: tuple) -> None:
        """collision 있는 정적 박스 (칸막이)."""
        self.lines.append(f'    <model name="{name}"><static>true</static>'
                          f'<pose>{xyz} 0 0 0</pose>')
        self.lines.append(
            f'      <link name="l"><collision name="c"><geometry><box><size>{size}</size>'
            f'</box></geometry></collision><visual name="v">'
            f'<geometry><box><size>{size}</size></box></geometry>{_material(rgba)}'
            f'</visual></link></model>')

    def visual_model(self, name: str, xyz: str, visuals: list[str]) -> None:
        """visual(+ 필요한 collision) 정적 모델. 줄 목록을 그대로 link 안에 넣는다."""
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


# =====================================================================
# OBJ 메시 (텍스처 반복용 UV 포함)
# =====================================================================
Vec = tuple[float, float, float]


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _scale(a: Vec, s: float) -> Vec:
    return (a[0] * s, a[1] * s, a[2] * s)


def _unit(a: Vec) -> Vec:
    n = math.sqrt(_dot(a, a))
    return _scale(a, 1.0 / n)


class ObjMesh:
    """직육면체를 모아 OBJ 하나로 쓴다 (draw call 1개).

    UV 는 월드 좌표를 면에 투영해 타일 크기로 나눈 값 → 인접한 면끼리 텍스처가 이어진다.
    """

    def __init__(self, tile_u: float = 1.0, tile_v: float = 1.0) -> None:
        self.tile_u, self.tile_v = tile_u, tile_v
        self.v: list[str] = []
        self.vt: list[str] = []
        self.vn: list[str] = []
        self.f: list[str] = []

    def box(self, x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> None:
        """축 정렬 박스 (최소·최대 좌표)."""
        c = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        self.cuboid(c, ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                    ((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2))

    def beam(self, p0: Vec, p1: Vec, w: float, h: float, side: Vec = (1, 0, 0)) -> None:
        """p0→p1 방향 각재 (폭 w 는 side 방향, 높이 h 는 그 수직)."""
        d = _sub(p1, p0)
        length = math.sqrt(_dot(d, d))
        ax = _unit(d)
        s = _unit(side)
        t = _unit(_cross(ax, s))
        c = _scale((p0[0] + p1[0], p0[1] + p1[1], p0[2] + p1[2]), 0.5)
        self.cuboid(c, (ax, s, t), (length / 2, w / 2, h / 2))

    def cuboid(self, c: Vec, axes: tuple, half: tuple) -> None:
        for i in range(3):
            j, k = (i + 1) % 3, (i + 2) % 3     # j x k = i (오른손 좌표)
            for sgn in (1, -1):
                n = _scale(axes[i], sgn)
                fc = tuple(c[m] + n[m] * half[i] for m in range(3))
                a, b = _scale(axes[j], half[j]), _scale(axes[k], half[k])
                quad = [tuple(fc[m] + sa * a[m] + sb * b[m] for m in range(3))
                        for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
                if sgn < 0:
                    quad.reverse()               # 바깥에서 볼 때 반시계
                self._face(quad, n)

    def _face(self, quad: list, n: Vec) -> None:
        # UV 축: 수직면은 v=z, 수평면은 v=y. u = v_axis x n (텍스처 뒤집힘 방지)
        v_axis = (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (0.0, 1.0, 0.0)
        u_axis = _cross(v_axis, n)
        if _dot(u_axis, u_axis) < 1e-9:
            u_axis = (1.0, 0.0, 0.0)
        u_axis = _unit(u_axis)
        self.vn.append(f'vn {n[0]:.4f} {n[1]:.4f} {n[2]:.4f}')
        ni = len(self.vn)
        idx = []
        for p in quad:
            self.v.append(f'v {p[0]:.4f} {p[1]:.4f} {p[2]:.4f}')
            self.vt.append(f'vt {_dot(p, u_axis) / self.tile_u:.4f} '
                           f'{_dot(p, v_axis) / self.tile_v:.4f}')
            idx.append(len(self.v))
        self.f.append('f ' + ' '.join(f'{i}/{i}/{ni}' for i in idx))

    def write(self, path: str, title: str) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'# {title} — scripts/gen_preview_world.py 로 생성 (손으로 고치지 말 것)\n')
            f.write('o mesh\n')
            f.write('\n'.join(self.v + self.vt + self.vn + self.f) + '\n')


# =====================================================================
# 장식 요소
# =====================================================================
def add_floor(b: WorldBuilder, meshes: dict) -> None:
    hx0, hx1, hy0, hy1 = FLOOR_HOLE
    b.comment('    <!-- ===================== 미리보기 장식 (v2 preview) ===================== -->')
    b.comment(f'    <!-- 초록 에폭시 바닥(visual 만, 윗면 z {FLOOR_TOP}). 카메라 아래 '
              f'x {hx0}~{hx1}, y {hy0}~{hy1} 는 비워 기존 바닥색 유지 + 둘레 노란 안전선 -->')
    floor = ObjMesh(2.0, 1.0)    # Concrete034 는 2:1 텍스처 → 2 m x 1 m 반복
    bx0, bx1, by0, by1 = -9.0, 11.0, -6.5, 5.5
    floor.box(bx0, hx0, by0, by1, 0, FLOOR_TOP)
    floor.box(hx1, bx1, by0, by1, 0, FLOOR_TOP)
    floor.box(hx0, hx1, hy1, by1, 0, FLOOR_TOP)
    floor.box(hx0, hx1, by0, hy0, 0, FLOOR_TOP)
    meshes['epoxy_floor.obj'] = (floor, '초록 에폭시 바닥')
    w = SAFETY_W
    z, t = FLOOR_TOP + 0.001, 0.002
    lines = [   # 구멍 바깥 둘레 (에폭시 쪽)
        ('north', (hx0 + hx1) / 2, hy1 + w / 2, hx1 - hx0 + 2 * w, w),
        ('south', (hx0 + hx1) / 2, hy0 - w / 2, hx1 - hx0 + 2 * w, w),
        ('west', hx0 - w / 2, (hy0 + hy1) / 2, w, hy1 - hy0),
        ('east', hx1 + w / 2, (hy0 + hy1) / 2, w, hy1 - hy0),
    ]
    visuals = [mesh_visual('epoxy', 'epoxy_floor.obj', EPOXY_MAT)]
    for name, cx, cy, sx, sy in lines:
        visuals.append(shadeless_visual(f'safety_{name}', _pose(cx, cy, z),
                                        _box((sx, sy, t)), SAFETY_RGBA))
    b.visual_model('epoxy_floor', '0 0 0', visuals)


def add_building(b: WorldBuilder, meshes: dict) -> None:
    b.comment('    <!-- 건물 외벽(흰 샌드위치 패널): x -9~11, y -6.5~5.5, 높이 5 m, 지붕판 없음.')
    b.comment('         서쪽 출입구(입고) y -1.5~1.5 / 동쪽 출입구(출하) y -2.25~1.25, '
              '출입구 위 z 3.5~5 상인방 + 셔터 박스 -->')
    walls = ObjMesh(2.0, 2.0)    # 골 8개 / 2 m → 골 간격 0.25 m
    items = []
    for name, cx, cy, sx, sy in WALLS:
        walls.box(cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, 0, WALL_H)
        items.append(collision(name, _pose(cx, cy, WALL_H / 2), (sx, sy, WALL_H)))
    shutter = []
    for i, (wx, y0, y1, inward) in enumerate(DOORS):
        walls.box(wx - 0.1, wx + 0.1, y0, y1, DOOR_H, WALL_H)        # 상인방
        cx, cy = wx + inward * 0.25, (y0 + y1) / 2
        shutter.append(shadeless_visual(f'shutter_box_{i}', _pose(cx, cy, DOOR_H + 0.2),
                                        _box((0.3, y1 - y0 + 0.2, 0.4)), SHUTTER_RGBA))
        shutter.append(shadeless_visual(f'shutter_slat_{i}', _pose(cx - inward * 0.1, cy,
                                                                   DOOR_H - 0.15),
                                        _box((0.03, y1 - y0, 0.3)), SHUTTER_RGBA))
        for j, ry in enumerate((y0 - 0.05, y1 + 0.05)):            # 셔터 가이드 레일
            shutter.append(shadeless_visual(f'shutter_rail_{i}{j}',
                                            _pose(wx + inward * 0.13, ry, DOOR_H / 2),
                                            _box((0.06, 0.1, DOOR_H)), SHUTTER_RGBA))
    meshes['sandwich_walls.obj'] = (walls, '흰 샌드위치 패널 외벽')
    b.visual_model('building_walls', '0 0 0',
                   items + [mesh_visual('panels', 'sandwich_walls.obj', SANDWICH_MAT)] + shutter)


def _truss_top_z(y: float) -> float:
    half = max(RIDGE_Y - TRUSS_Y0, TRUSS_Y1 - RIDGE_Y)
    return EAVE_Z + (RIDGE_Z - EAVE_Z) * (1 - abs(y - RIDGE_Y) / half)


def add_steel_frame(b: WorldBuilder, meshes: dict) -> None:
    b.comment('    <!-- 철골 (visual 만, 그림자 없음, 지붕판 없음): 트러스 6개 x '
              f'{TRUSS_X}, 하현재 z {EAVE_Z - 0.05}, 용마루 y {RIDGE_Y} z {RIDGE_Z},')
    b.comment('         중도리 1.5 m 간격, H형 기둥(벽 안쪽 y 5.3 / -6.3) -->')
    m = ObjMesh()
    n = round((TRUSS_Y1 - TRUSS_Y0) / TRUSS_PANEL)
    ys = [TRUSS_Y0 + k * TRUSS_PANEL for k in range(n + 1)]
    ridge_k = round((RIDGE_Y - TRUSS_Y0) / TRUSS_PANEL)
    zb = EAVE_Z - 0.05                                    # 하현재 중심
    for tx in TRUSS_X:
        m.beam((tx, TRUSS_Y0, zb), (tx, TRUSS_Y1, zb), 0.1, 0.1)                 # 하현재
        for ya, yb in ((ys[0], ys[ridge_k]), (ys[ridge_k], ys[-1])):             # 상현재
            m.beam((tx, ya, _truss_top_z(ya)), (tx, yb, _truss_top_z(yb)), 0.1, 0.12)
        for k in range(1, n):                                                    # 수직재
            m.beam((tx, ys[k], zb), (tx, ys[k], _truss_top_z(ys[k])), 0.06, 0.06)
        for k in range(n):                                                       # 사재 (워렌)
            if k < ridge_k:
                p0, p1 = (tx, ys[k], zb), (tx, ys[k + 1], _truss_top_z(ys[k + 1]))
            else:
                p0, p1 = (tx, ys[k], _truss_top_z(ys[k])), (tx, ys[k + 1], zb)
            m.beam(p0, p1, 0.06, 0.06)
        for cy in COLUMN_Y:                                                      # H형 기둥
            m.box(tx - 0.1, tx + 0.1, cy - 0.1, cy - 0.085, 0, zb)
            m.box(tx - 0.1, tx + 0.1, cy + 0.085, cy + 0.1, 0, zb)
            m.box(tx - 0.0075, tx + 0.0075, cy - 0.085, cy + 0.085, 0, zb)
    x0, x1 = TRUSS_X[0] - 0.1, TRUSS_X[-1] + 0.1
    for y in ys:                                                                 # 중도리
        z = _truss_top_z(y) + 0.1
        m.beam((x0, y, z), (x1, y, z), 0.08, 0.08, side=(0, 1, 0))
    meshes['steel_frame.obj'] = (m, '지붕 철골 트러스·기둥·중도리')
    b.visual_model('steel_frame', '0 0 0',
                   [mesh_visual('frame', 'steel_frame.obj', _material(FRAME_RGBA))])


def add_intake(b: WorldBuilder) -> None:
    b.comment('    <!-- 입고 구역 (x -8~-4.5): 팔레트 + 노란 사과 상자. '
              '서쪽 출입구 앞 통로 y -1.5~1.5 는 비움 -->')
    b.pallet_load('intake_1', *INTAKE_PALLETS['intake_1'], 0.0, True, 3)
    b.pallet_load('intake_2', *INTAKE_PALLETS['intake_2'], 0.0, True, 3)
    b.pallet_load('intake_3', *INTAKE_PALLETS['intake_3'], 0.0, True, 2)
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
    b.comment('         카메라(z=1.6, hfov 0.3) 시야: 벨트면 y±0.12 x±0.09 / 바닥 y±0.24 x -2.18~-1.82')
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


class LineParts:
    """선별 라인 부속 visual/collision 모음 + 카메라 금지 구역 검사."""

    def __init__(self) -> None:
        self.items: list[str] = []
        self.n = 0

    def _check(self, name: str, x0: float, x1: float, y0: float, y1: float) -> None:
        kx0, kx1, ky0, ky1 = CAM_KEEP_OUT
        if x1 > kx0 and x0 < kx1 and y1 > ky0 and y0 < ky1:
            sys.exit(f'❌ {name} 이(가) 카메라 시야 금지 구역 {CAM_KEEP_OUT} 과 겹침')

    def box(self, name: str, c: Vec, size: Vec, rgba: tuple, rpy: Vec = (0, 0, 0),
            check_half: tuple | None = None) -> None:
        hx, hy = check_half or (size[0] / 2, size[1] / 2)
        self._check(name, c[0] - hx, c[0] + hx, c[1] - hy, c[1] + hy)
        self.items.append(shadeless_visual(name, _pose(*c, *rpy), _box(size), rgba))

    def cylinder(self, name: str, c: Vec, r: float, length: float, rpy: Vec,
                 rgba: tuple, half: tuple) -> None:
        self._check(name, c[0] - half[0], c[0] + half[0], c[1] - half[1], c[1] + half[1])
        geom = f'<cylinder><radius>{r}</radius><length>{length}</length></cylinder>'
        self.items.append(shadeless_visual(name, _pose(*c, *rpy), geom, rgba))

    def coll(self, name: str, x: float, y: float, sx: float, sy: float) -> None:
        """바닥~LEG_COLL_H collision. 컨베이어 몸체 |y|<0.3 안쪽 금지."""
        if abs(y) - sy / 2 < 0.3 - 1e-9 and -3.5 < x < -0.5:
            sys.exit(f'❌ {name} collision 이 컨베이어 몸체 |y|<0.3 안쪽')
        self.items.append(collision(name, _pose(x, y, LEG_COLL_H / 2), (sx, sy, LEG_COLL_H)))


def add_sorting_line(b: WorldBuilder) -> tuple:
    b.comment('    <!-- 선별 라인 부속 (conveyor 모델은 그대로): 다리·프레임·가이드바·입고 롤러·'
              '등급별 배출 슈트·제어반.')
    b.comment(f'         카메라 시야 x {CAM_KEEP_OUT[0]}~{CAM_KEEP_OUT[1]} '
              f'(y ±{CAM_KEEP_OUT[3]}, 바닥까지) '
              '에는 아무것도 없음. visual 만, 그림자 없음.')
    b.comment(f'         AMR 용 collision: 롤러 다리·슈트 받침다리·제어반만 바닥~{LEG_COLL_H} m -->')
    p = LineParts()
    # 컨베이어 다리 + 바닥 받침 (|y| 0.29 → collision 없음)
    for i, lx in enumerate(LINE_LEG_X):
        for j, s in enumerate((1, -1)):
            y = s * LINE_LEG_Y
            p.box(f'leg_{i}{j}', (lx, y, 0.38), (0.05, 0.05, 0.76), SS_RGBA)
            p.box(f'foot_{i}{j}', (lx, y, 0.005), (0.1, 0.1, 0.01), SS_RGBA)
    # 측면 프레임 (카메라 시야 밖 구간만), 상류 구간 원형 가이드바
    for i, (x0, x1) in enumerate(LINE_SEGMENTS):
        cx, length = (x0 + x1) / 2, x1 - x0
        for j, s in enumerate((1, -1)):
            p.box(f'side_frame_{i}{j}', (cx, s * 0.27, 0.74), (length, 0.03, 0.08), SS_RGBA)
            if i == 0:
                p.cylinder(f'guide_bar_{j}', (cx, s * 0.28, 0.9), 0.012, length,
                           (0, math.pi / 2, 0), SS_RGBA, (length / 2, 0.012))
                for k, px in enumerate((x0 + 0.05, x1 - 0.05)):
                    p.box(f'guide_post_{j}{k}', (px, s * 0.28, 0.875), (0.015, 0.015, 0.05),
                          SS_RGBA)
    # 입고 롤러 컨베이어 (상류 연장): 롤러 12개, 프레임, 다리 4개
    rx0, rx1, hw = ROLLER_X0, ROLLER_X1, ROLLER_HALF_W
    rcx, rlen = (rx0 + rx1) / 2, rx1 - rx0
    for j, s in enumerate((1, -1)):
        p.box(f'roller_frame_{j}', (rcx, s * (hw - 0.03), 0.75), (rlen, 0.04, 0.08), SS_RGBA)
    for k in range(12):
        x = rx0 + 0.05 + 0.1 * k
        p.cylinder(f'roller_{k}', (x, 0, 0.76), 0.03, 2 * (hw - 0.05), (math.pi / 2, 0, 0),
                   ROLLER_RGBA, (0.03, hw - 0.05))
    for i, lx in enumerate((rx0 + 0.1, rx1 - 0.1)):
        for j, s in enumerate((1, -1)):
            y = s * (hw - 0.03)
            p.box(f'roller_leg_{i}{j}', (lx, y, 0.36), (0.05, 0.05, 0.72), SS_RGBA)
            p.coll(f'roller_leg_c_{i}{j}', lx, y, 0.06, 0.06)
    # 등급별 배출 슈트: 컨베이어 옆에서 바깥으로 경사, 옆 턱은 등급 색, 위에 배출 액추에이터
    (yi, zi), (yo, zo) = CHUTE_IN, CHUTE_OUT
    length = math.hypot(yo - yi, zi - zo)
    tilt = math.atan2(zi - zo, yo - yi)
    for xc, s, grade in CHUTES:
        rgba = GRADE_RGBA[grade]
        ym, zm = s * (yi + yo) / 2, (zi + zo) / 2
        half = (CHUTE_W / 2, length / 2)
        rpy = (-s * tilt, 0, 0)
        p.box(f'chute_{grade}', (xc, ym, zm), (CHUTE_W, length, 0.01), SS_RGBA, rpy, half)
        for k, dx in enumerate((-CHUTE_W / 2, CHUTE_W / 2)):
            p.box(f'chute_{grade}_lip_{k}', (xc + dx, ym, zm + 0.03), (0.01, length, 0.06),
                  rgba, rpy, (0.005, length / 2))
        p.box(f'chute_{grade}_sign', (xc, s * (yo + 0.01), zo + 0.02), (CHUTE_W, 0.01, 0.1),
              rgba)
        leg_y = s * (yo - 0.03)
        p.box(f'chute_{grade}_leg', (xc, leg_y, zo / 2), (0.05, 0.05, zo), SS_RGBA)
        p.coll(f'chute_{grade}_leg_c', xc, leg_y, 0.05, 0.05)
        p.box(f'chute_{grade}_actuator', (xc, s * 0.32, 0.95), (0.1, 0.08, 0.1), rgba)
        p.box(f'chute_{grade}_post', (xc, s * 0.32, 0.85), (0.03, 0.03, 0.1), SS_RGBA)
    # 제어반 (입고 롤러 남쪽에 붙임) + HMI 화면
    cx, cy, sx, sy, sz = CABINET
    p.box('cabinet', (cx, cy, sz / 2), (sx, sy, sz), CABINET_RGBA)
    p.box('cabinet_hmi', (cx, cy - sy / 2 - 0.005, 1.25), (0.32, 0.01, 0.22), SCREEN_RGBA)
    p.coll('cabinet_c', cx, cy, sx, sy)
    b.visual_model('sorting_line_frame', '0 0 0', p.items)
    xs = [c[0] for c in CHUTES]
    return (min(xs) - CHUTE_W / 2, max(xs) + CHUTE_W / 2)


def add_cold_storage(b: WorldBuilder, meshes: dict) -> None:
    b.comment('    <!-- 예냉 대기 구역 (zone A/B/C 뒤 x 4.6~6.0): 팔레트 랙 2개 + 칸막이(구역 사이).')
    b.comment('         구역 바닥(x 3.5~4.5)과 AMR 진입 쪽(x<3.5)은 비움 -->')
    for i, ry in enumerate((1.3, -1.3)):
        b.include(f'cold_rack_{i}', 'Pallet_Rack', 5.3, ry, 0.0, math.pi / 2)
        for j, s in enumerate((-1, 1)):
            py = ry + s * 0.62
            b.pallet_load(f'cold_rack_{i}_floor_{j}', 5.3, py, 0.0, True, 1)
            b.pallet_load(f'cold_rack_{i}_lv1_{j}', 5.3, py, RACK_LEVEL1_Z, True, 2)
    b.box_model('partition_AB', '4.1 1.0 1.0', '1.0 0.08 2.0', PANEL_RGBA)
    b.box_model('partition_BC', '4.1 -1.0 1.0', '1.0 0.08 2.0', PANEL_RGBA)

    b.comment(f'    <!-- 저온저장고 (단열 패널): x {COLD_X0}~{COLD_X1}, y {COLD_Y0}~{COLD_Y1}, '
              f'높이 {COLD_H}, 천장판 없음. 벽 collision 있음.')
    b.comment(f'         동쪽 면 큰 슬라이딩 문(visual) y {COLD_DOOR_Y0}~{COLD_DOOR_Y1}, '
              f'높이 {COLD_DOOR_H} → 동쪽 출하 출입구를 향함 -->')
    t, h = COLD_T, COLD_H
    x0, x1, y0, y1 = COLD_X0, COLD_X1, COLD_Y0, COLD_Y1
    walls = [   # (이름, x0, x1, y0, y1) — 벽 중심선 기준 두께 t
        ('west', x0 - t / 2, x0 + t / 2, y0 - t / 2, y1 + t / 2),
        ('south', x0 + t / 2, x1 + t / 2, y0 - t / 2, y0 + t / 2),
        ('north', x0 + t / 2, x1 + t / 2, y1 - t / 2, y1 + t / 2),
        ('east_s', x1 - t / 2, x1 + t / 2, y0 + t / 2, COLD_DOOR_Y0),
        ('east_n', x1 - t / 2, x1 + t / 2, COLD_DOOR_Y1, y1 - t / 2),
    ]
    panel = ObjMesh(1.1, 1.1)
    seams = ObjMesh()
    items = []
    for name, wx0, wx1, wy0, wy1 in walls:
        panel.box(wx0, wx1, wy0, wy1, 0, h)
        items.append(collision(f'cold_{name}', _pose((wx0 + wx1) / 2, (wy0 + wy1) / 2, h / 2),
                               (wx1 - wx0, wy1 - wy0, h)))
        along_x = (wx1 - wx0) > (wy1 - wy0)
        a0, a1 = (wx0, wx1) if along_x else (wy0, wy1)
        k = math.ceil((a0 + 1e-6) / 1.1)
        while k * 1.1 < a1 - 0.05:                       # 1.1 m 간격 패널 이음줄 (양면)
            a = k * 1.1
            if along_x:
                seams.box(a - 0.01, a + 0.01, wy0 - 0.004, wy1 + 0.004, 0, h)
            else:
                seams.box(wx0 - 0.004, wx1 + 0.004, a - 0.01, a + 0.01, 0, h)
            k += 1
    panel.box(x1 - t / 2, x1 + t / 2, COLD_DOOR_Y0, COLD_DOOR_Y1, COLD_DOOR_H, h)  # 문 위 패널
    for name, wx0, wx1, wy0, wy1 in walls:               # 벽 위 마감 (회색 캡)
        seams.box(wx0 - 0.01, wx1 + 0.01, wy0 - 0.01, wy1 + 0.01, h - 0.04, h + 0.02)
    meshes['cold_room_panels.obj'] = (panel, '저온저장고 단열 패널 벽')
    meshes['cold_room_seams.obj'] = (seams, '저온저장고 패널 이음줄·상부 마감')
    # 큰 슬라이딩 문 (visual): 벽 바깥면에 붙임, 상부 레일은 북쪽(열리는 방향)으로 방 끝까지
    dx = x1 + t / 2 + 0.04
    dy0, dy1 = COLD_DOOR_Y0 - 0.1, COLD_DOOR_Y1 + 0.1
    dcy, dw = (dy0 + dy1) / 2, dy1 - dy0
    door = [
        shadeless_visual('door', _pose(dx, dcy, COLD_DOOR_H / 2 + 0.02),
                         _box((0.08, dw, COLD_DOOR_H + 0.04)), DOOR_RGBA),
        shadeless_visual('door_trim_top', _pose(dx + 0.045, dcy, COLD_DOOR_H),
                         _box((0.01, dw, 0.06)), DOOR_TRIM_RGBA),
        shadeless_visual('door_trim_bottom', _pose(dx + 0.045, dcy, 0.1),
                         _box((0.01, dw, 0.2)), DOOR_TRIM_RGBA),
        shadeless_visual('door_handle', _pose(dx + 0.06, dy1 - 0.25, 1.1),
                         _box((0.04, 0.04, 0.5)), DOOR_TRIM_RGBA),
        shadeless_visual('door_rail', _pose(dx, (dy0 + y1) / 2, COLD_DOOR_H + 0.12),
                         _box((0.1, y1 - dy0, 0.1)), DOOR_TRIM_RGBA),
    ]
    b.visual_model('cold_room', '0 0 0',
                   items + [mesh_visual('panels', 'cold_room_panels.obj', INSULATED_MAT),
                            mesh_visual('seams', 'cold_room_seams.obj', _material(SEAM_RGBA))]
                   + door)
    b.pallet_load('cold_room_1', 7.4, 1.9, 0.0, True, 3)
    b.pallet_load('cold_room_2', 7.4, -1.9, 0.0, True, 3)


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


# =====================================================================
# 통로 폭 확인
# =====================================================================
def _gap(a: tuple, b: tuple) -> float:
    """두 사각형 (x0, x1, y0, y1) 사이 최소 거리."""
    dx = max(a[0] - b[1], b[0] - a[1], 0.0)
    dy = max(a[2] - b[3], b[2] - a[3], 0.0)
    return math.hypot(dx, dy)


def _pallet_rect(x: float, y: float) -> tuple:   # 긴 변 x 방향 팔레트
    return (x - 0.6, x + 0.6, y - 0.4, y + 0.4)


def check_aisles(chute_x: tuple) -> list[str]:
    cx, cy, sx, sy, _ = CABINET
    cabinet = (cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2)
    roller = (ROLLER_X0, ROLLER_X1, -ROLLER_HALF_W, ROLLER_HALF_W)
    chutes_s = (chute_x[0], chute_x[1], -CHUTE_OUT[0], -CHUTE_IN[0])
    zone_r = (-0.5, 0.5, -3.5, -2.5)
    door_outer = COLD_X1 + COLD_T / 2 + 0.08 + 0.05    # 문 + 레일 바깥면
    cold_east = (COLD_X1 - COLD_T / 2, door_outer, COLD_Y0, COLD_Y1)
    east_wall = (10.9, 11.1, -6.5, 5.5)
    pal = {k: _pallet_rect(*v) for k, v in INTAKE_PALLETS.items()}
    checks = [
        ('저장고 문 바깥면 ↔ 건물 동쪽 벽', cold_east, east_wall),
        ('비상품 쪽 배출 슈트 ↔ zone R', chutes_s, zone_r),
        ('입고 롤러 ↔ intake_1 팔레트', roller, pal['intake_1']),
        ('입고 롤러 ↔ intake_2 팔레트', roller, pal['intake_2']),
        ('입고 롤러 ↔ intake_3 팔레트', roller, pal['intake_3']),
        ('제어반 ↔ intake_2 팔레트', cabinet, pal['intake_2']),
        ('제어반 ↔ intake_3 팔레트', cabinet, pal['intake_3']),
    ]
    out = []
    for name, a, b in checks:
        g = _gap(a, b)
        mark = '✓' if g >= AISLE_MIN else '⚠ 1.5 m 미만'
        out.append(f'  {name}: {g:.2f} m {mark}')
    return out


# =====================================================================
def build(base: str) -> tuple[str, int, dict, list[str]]:
    """원본 월드 문자열 → (미리보기 월드 문자열, 상자 개수, OBJ 메시들, 통로 확인 결과)."""
    b = WorldBuilder()
    meshes: dict = {}
    add_floor(b, meshes)
    add_building(b, meshes)
    add_steel_frame(b, meshes)
    add_intake(b)
    add_wash_dry_cover(b)
    add_grading_tunnel(b)
    chute_x = add_sorting_line(b)
    add_cold_storage(b, meshes)
    add_reject(b)
    add_shipping(b)
    body = '\n'.join(b.lines)

    result = HEADER + base[base.index('<sdf'):]   # 원본 헤더 주석만 교체
    idx = result.rindex('  </world>')
    return (result[:idx] + '\n' + body + '\n' + result[idx:], b.crate_count, meshes,
            check_aisles(chute_x))


def write_assets(meshes: dict) -> None:
    mesh_dir = os.path.join(ASSETS, 'meshes')
    os.makedirs(mesh_dir, exist_ok=True)
    for fname, (mesh, title) in meshes.items():
        mesh.write(os.path.join(mesh_dir, fname), title)
    with open(os.path.join(ASSETS, 'model.config'), 'w', encoding='utf-8') as f:
        f.write("""<?xml version="1.0"?>
<!-- scripts/gen_preview_world.py 로 생성 -->
<model>
  <name>apc_preview_assets</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>Smart APC 팀</name></author>
  <description>
    apc_world_v2_preview.sdf 용 메시(OBJ, 생성기 출력)와 CC0 텍스처 모음.
    model.sdf 는 에폭시 바닥 재질 견본 1 m x 1 m. 텍스처 출처는 models/ATTRIBUTION.md.
  </description>
</model>
""")
    with open(os.path.join(ASSETS, 'model.sdf'), 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0"?>\n<!-- scripts/gen_preview_world.py 로 생성: '
                '에폭시 바닥 재질 견본 -->\n<sdf version="1.9">\n'
                '  <model name="apc_preview_assets"><static>true</static>\n'
                '    <link name="l"><visual name="epoxy_sample"><pose>0 0 0.002 0 0 0</pose>'
                f'<geometry>{_box((1, 1, 0.004))}</geometry>{EPOXY_MAT}</visual></link>\n'
                '  </model>\n</sdf>\n')


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
    # 기본 월드의 AMCL 기준물(기둥·벽)은 빼고 생성 — 배경 월드는 자체 벽·랙·저장고가 있음
    if '<!-- NAV_LANDMARKS_BEGIN' in base:
        i = base.index('    <!-- NAV_LANDMARKS_BEGIN')
        j = base.index('<!-- NAV_LANDMARKS_END -->') + len('<!-- NAV_LANDMARKS_END -->\n')
        base = base[:i] + base[j:]
    world, crates, meshes, aisles = build(base)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(world)
    write_assets(meshes)
    print(f'생성: {dst} (사과 상자 {crates}개)')
    print(f'메시: {", ".join(meshes)} → {os.path.join(ASSETS, "meshes")}')
    print('AMR 통로 폭 확인 (기준 1.5 m):')
    print('\n'.join(aisles))


if __name__ == '__main__':
    main()
