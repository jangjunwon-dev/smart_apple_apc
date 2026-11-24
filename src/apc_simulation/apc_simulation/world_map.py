"""Gazebo 월드(SDF) → Nav2 용 2D 점유 격자 지도 — ROS 의존 없음 (pytest 대상).

월드 파일에 적힌 물체 모양(박스·원기둥·구·OBJ/DAE 메시)을 로봇 높이 구간(zmin~zmax)으로
잘라 위에서 내려다본 점유 지도를 만든다. SLAM 없이 Nav2(map_server, AMCL)를 바로 쓰기 위함.

- 충돌(collision) 모양과 보이는(visual) 모양을 모두 쓴다. 라이다(gpu_lidar)는 보이는 모양을
  감지하므로, 충돌 모양이 없는 장식(세척 덮개 기둥 등)도 지도에 있어야 위치 추정이 맞는다.
- 지원 메시: OBJ(삼각형·사각형 면), DAE(꼭짓점 범위 상자로 근사). GLB 등은 건너뛰고
  같은 모델의 충돌 모양(박스)을 쓴다.
- 얇은 벽(격자 한 칸보다 얇은 것)도 빠지지 않도록 모양에 닿는 칸은 모두 점유로 칠한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import os
import re
import xml.etree.ElementTree as ET

import numpy as np

FREE, OCCUPIED = 254, 0          # PGM 값 (map_server trinary: 흰색=빈칸, 검정=점유)


# ---------------------------------------------------------------- 자세(pose) 계산
def pose_matrix(text: str | None) -> np.ndarray:
    """SDF <pose> 'x y z roll pitch yaw' → 4x4 변환 (R = Rz(yaw)·Ry(pitch)·Rx(roll))."""
    vals = [float(v) for v in (text or '').split()] + [0.0] * 6
    x, y, z, r, p, w = vals[:6]
    cr, sr, cp, sp, cw, sw = (math.cos(r), math.sin(r), math.cos(p), math.sin(p),
                              math.cos(w), math.sin(w))
    m = np.eye(4)
    m[:3, :3] = [[cw * cp, cw * sp * sr - sw * cr, cw * sp * cr + sw * sr],
                 [sw * cp, sw * sp * sr + cw * cr, sw * sp * cr - cw * sr],
                 [-sp, cp * sr, cp * cr]]
    m[:3, 3] = [x, y, z]
    return m


def _vec(text: str | None, n: int, default: float) -> list[float]:
    vals = [float(v) for v in (text or '').split()]
    return vals + [default] * (n - len(vals)) if len(vals) < n else vals[:n]


# ---------------------------------------------------------------- 모양 모으기
@dataclass
class Shapes:
    """월드 좌표 모양: 속이 찬 상자(꼭짓점 8개), 메시 표면 삼각형 (N, 3, 3), 원(수직 원기둥·구)."""
    solids: list[np.ndarray] = field(default_factory=list)       # 각 (8, 3)
    triangles: list[np.ndarray] = field(default_factory=list)
    circles: list[tuple[float, float, float, float, float]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)   # 지원하지 않아 건너뛴 메시

    def all_triangles(self) -> np.ndarray:
        return np.concatenate(self.triangles) if self.triangles else np.zeros((0, 3, 3))


_BOX_FACES = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                       [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])


def box_corners(tf: np.ndarray, size, center=(0.0, 0.0, 0.0)) -> np.ndarray:
    """상자 꼭짓점 8개의 월드 좌표 (8, 3)."""
    sx, sy, sz = size
    cx, cy, cz = center
    corners = np.array([[cx + dx * sx / 2, cy + dy * sy / 2, cz + dz * sz / 2, 1.0]
                        for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)])
    return (tf @ corners.T).T[:, :3]


def box_triangles(tf: np.ndarray, size, center=(0.0, 0.0, 0.0)) -> np.ndarray:
    return box_corners(tf, size, center)[_BOX_FACES]


def _obj_triangles(path: str) -> np.ndarray:
    verts, tris = [], []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if line.startswith('v '):
                verts.append([float(v) for v in line.split()[1:4]])
            elif line.startswith('f '):
                idx = [int(tok.split('/')[0]) for tok in line.split()[1:]]
                idx = [i - 1 if i > 0 else len(verts) + i for i in idx]
                tris += [[idx[0], idx[k], idx[k + 1]] for k in range(1, len(idx) - 1)]
    v = np.array(verts, dtype=float)
    return v[np.array(tris, dtype=int)] if tris else np.zeros((0, 3, 3))


def _dae_bbox(path: str) -> tuple[np.ndarray, np.ndarray] | None:
    """DAE 꼭짓점 범위. 장면 노드의 <matrix> (메시를 놓는 변환)를 적용한 뒤 계산."""
    text = open(path, encoding='utf-8', errors='replace').read()
    geoms = {}
    for g in re.finditer(r'<geometry[^>]*id="([^"]+)"(.*?)</geometry>', text, re.S):
        m = re.search(r'<float_array[^>]*id="[^"]*position[^"]*"[^>]*>([^<]*)<', g.group(2),
                      re.I)
        if m:
            nums = np.array(m.group(1).split(), dtype=float)
            geoms[g.group(1)] = nums[: len(nums) // 3 * 3].reshape(-1, 3)
    pts = []
    for node in re.finditer(r'<matrix[^>]*>([^<]*)</matrix>\s*<instance_geometry url="#([^"]+)"',
                            text):
        v = geoms.pop(node.group(2), None)
        if v is not None:
            mat = np.array(node.group(1).split(), dtype=float).reshape(4, 4)
            pts.append((mat @ np.c_[v, np.ones(len(v))].T).T[:, :3])
    pts += list(geoms.values())                     # 노드 변환이 없는 메시는 그대로
    if not pts:
        return None
    a = np.concatenate(pts)
    return a.min(axis=0), a.max(axis=0)


class WorldReader:
    def __init__(self, model_dirs: list[str], use_visual: bool = True,
                 exclude: str = r'^(ground_plane)$') -> None:
        self.model_dirs = model_dirs
        self.use_visual = use_visual
        self.exclude = re.compile(exclude)
        self.shapes = Shapes()

    def resolve(self, uri: str) -> str | None:
        if uri.startswith('model://'):
            rel = uri[len('model://'):]
            for d in self.model_dirs:
                p = os.path.join(d, rel)
                if os.path.exists(p):
                    return p
            return None
        return uri[len('file://'):] if uri.startswith('file://') else uri

    def read_world(self, path: str) -> Shapes:
        world = ET.parse(path).getroot().find('world')
        for model in world.findall('model'):
            self._model(model, np.eye(4))
        for inc in world.findall('include'):
            self._include(inc, np.eye(4))
        return self.shapes

    def _include(self, inc: ET.Element, parent: np.ndarray) -> None:
        d = self.resolve(inc.findtext('uri', '').strip())
        sdf = os.path.join(d, 'model.sdf') if d and os.path.isdir(d) else d
        if not sdf or not os.path.exists(sdf):
            self.shapes.skipped.append(f'include {inc.findtext("uri")} (찾을 수 없음)')
            return
        model = ET.parse(sdf).getroot().find('model')
        name = inc.findtext('name') or model.get('name', '')
        if self.exclude.search(name):
            return
        pose = inc.find('pose')
        tf = parent @ (pose_matrix(pose.text) if pose is not None
                       else pose_matrix(model.findtext('pose')))
        self._model_body(model, tf)

    def _model(self, model: ET.Element, parent: np.ndarray) -> None:
        if self.exclude.search(model.get('name', '')):
            return
        self._model_body(model, parent @ pose_matrix(model.findtext('pose')))

    def _model_body(self, model: ET.Element, tf: np.ndarray) -> None:
        for link in model.findall('link'):
            ltf = tf @ pose_matrix(link.findtext('pose'))
            for tag in ('collision', 'visual') if self.use_visual else ('collision',):
                for el in link.findall(tag):
                    self._geometry(el.find('geometry'), ltf @ pose_matrix(el.findtext('pose')))
        for sub in model.findall('model'):
            self._model(sub, tf)
        for inc in model.findall('include'):
            self._include(inc, tf)

    def _geometry(self, geom: ET.Element | None, tf: np.ndarray) -> None:
        if geom is None or len(geom) == 0:
            return
        g = geom[0]
        s = self.shapes
        if g.tag == 'box':
            s.solids.append(box_corners(tf, _vec(g.findtext('size'), 3, 0.0)))
        elif g.tag in ('cylinder', 'sphere'):
            r = float(g.findtext('radius', '0'))
            length = float(g.findtext('length', str(2 * r))) if g.tag == 'cylinder' else 2 * r
            axis = tf[:3, 2]
            if g.tag == 'sphere' or abs(axis[2]) > 0.999:     # 수직 원기둥·구 → 원
                cz = tf[2, 3]
                s.circles.append((tf[0, 3], tf[1, 3], r, cz - length / 2, cz + length / 2))
            else:                                               # 기울어진 원기둥 → 상자
                s.solids.append(box_corners(tf, (2 * r, 2 * r, length)))
        elif g.tag == 'mesh':
            uri = g.findtext('uri', '').strip()
            path = self.resolve(uri)
            scale = np.array(_vec(g.findtext('scale'), 3, 1.0))
            if path and path.lower().endswith('.obj') and os.path.exists(path):
                tri = _obj_triangles(path) * scale
                flat = np.c_[tri.reshape(-1, 3), np.ones(len(tri) * 3)]
                s.triangles.append((tf @ flat.T).T[:, :3].reshape(-1, 3, 3))
            elif path and path.lower().endswith('.dae') and os.path.exists(path):
                bb = _dae_bbox(path)
                if bb is not None:
                    lo, hi = bb[0] * scale, bb[1] * scale
                    s.solids.append(box_corners(tf, hi - lo, (lo + hi) / 2))
            else:
                s.skipped.append(uri)


# ---------------------------------------------------------------- 격자 칠하기
@dataclass
class Grid:
    xmin: float
    ymin: float
    res: float
    width: int
    height: int

    def __post_init__(self) -> None:
        self.occ = np.zeros((self.height, self.width), dtype=bool)   # [iy, ix], iy=0 이 ymin

    def centers(self, x0: float, y0: float, x1: float, y1: float):
        ix0 = max(int(math.floor((x0 - self.xmin) / self.res)) - 1, 0)
        iy0 = max(int(math.floor((y0 - self.ymin) / self.res)) - 1, 0)
        ix1 = min(int(math.ceil((x1 - self.xmin) / self.res)) + 1, self.width)
        iy1 = min(int(math.ceil((y1 - self.ymin) / self.res)) + 1, self.height)
        if ix0 >= ix1 or iy0 >= iy1:
            return None
        xs = self.xmin + (np.arange(ix0, ix1) + 0.5) * self.res
        ys = self.ymin + (np.arange(iy0, iy1) + 0.5) * self.res
        gx, gy = np.meshgrid(xs, ys)
        return (slice(iy0, iy1), slice(ix0, ix1)), gx, gy

    def fill_convex(self, pts: np.ndarray) -> None:
        """xy 점들(N,2)의 볼록 껍질에 닿는 칸(칸 중심이 껍질에서 반 칸 이내)을 점유로."""
        p = convex_hull(pts)
        c = self.centers(p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max())
        if c is None:
            return
        sl, gx, gy = c
        tol = self.res * 0.5
        n = len(p)
        inside = np.zeros(gx.shape, dtype=bool)
        if n >= 3:                                          # 반시계 볼록 다각형 안쪽
            inside = np.ones(gx.shape, dtype=bool)
            for i in range(n):
                a, b = p[i], p[(i + 1) % n]
                inside &= (b[0] - a[0]) * (gy - a[1]) - (b[1] - a[1]) * (gx - a[0]) >= 0
        near = np.zeros(gx.shape, dtype=bool)
        for i in range(n):                                  # 변까지 거리 (얇은 벽·선분 대비)
            a, b = p[i], p[(i + 1) % n]
            ab = b - a
            L2 = float(ab @ ab)
            proj = ((gx - a[0]) * ab[0] + (gy - a[1]) * ab[1]) / L2 if L2 > 1e-18 else 0.0
            t = np.clip(proj, 0, 1)
            dx, dy = gx - (a[0] + t * ab[0]), gy - (a[1] + t * ab[1])
            near |= dx * dx + dy * dy <= tol * tol
        self.occ[sl] |= inside | near

    def fill_triangle(self, p: np.ndarray) -> None:
        self.fill_convex(p)

    def fill_circle(self, x: float, y: float, r: float) -> None:
        c = self.centers(x - r, y - r, x + r, y + r)
        if c is None:
            return
        sl, gx, gy = c
        self.occ[sl] |= (gx - x) ** 2 + (gy - y) ** 2 <= (r + self.res * 0.5) ** 2

    def is_occupied(self, x: float, y: float) -> bool:
        ix = int((x - self.xmin) / self.res)
        iy = int((y - self.ymin) / self.res)
        return bool(self.occ[iy, ix])

    def image(self) -> np.ndarray:
        """PGM 이미지 (위쪽 행 = ymax)."""
        return np.where(self.occ[::-1], OCCUPIED, FREE).astype(np.uint8)


def convex_hull(pts: np.ndarray) -> np.ndarray:
    """2D 볼록 껍질 (반시계, Andrew monotone chain). 점 1~2개면 그대로."""
    u = np.unique(np.round(np.asarray(pts, dtype=float)[:, :2], 9), axis=0)
    if len(u) <= 2:
        return u

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for q in u:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
            lower.pop()
        lower.append(q)
    for q in u[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
            upper.pop()
        upper.append(q)
    return np.array(lower[:-1] + upper[:-1])


def auto_bounds(shapes: Shapes, margin: float) -> tuple[float, float, float, float]:
    tri = shapes.all_triangles()
    sol = np.concatenate(shapes.solids) if shapes.solids else np.zeros((0, 3))
    xs = list(tri[:, :, 0].ravel()) + list(sol[:, 0]) + \
        [c[0] - c[2] for c in shapes.circles] + [c[0] + c[2] for c in shapes.circles]
    ys = list(tri[:, :, 1].ravel()) + list(sol[:, 1]) + \
        [c[1] - c[2] for c in shapes.circles] + [c[1] + c[2] for c in shapes.circles]
    return min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin


def build_grid(shapes: Shapes, res: float = 0.05, zmin: float = 0.05, zmax: float = 0.4,
               bounds: tuple[float, float, float, float] | None = None, margin: float = 2.0,
               border: bool = True) -> Grid:
    x0, y0, x1, y1 = bounds or auto_bounds(shapes, margin)
    # 원점을 격자 간격에 맞춰 좌표가 깔끔하게 떨어지도록
    x0, y0 = math.floor(x0 / res) * res, math.floor(y0 / res) * res
    grid = Grid(x0, y0, res, int(math.ceil((x1 - x0) / res)), int(math.ceil((y1 - y0) / res)))
    tri = shapes.all_triangles()
    if len(tri):
        tz0, tz1 = tri[:, :, 2].min(axis=1), tri[:, :, 2].max(axis=1)
        for t in tri[(tz1 >= zmin) & (tz0 <= zmax)]:
            grid.fill_triangle(t[:, :2])
    for corners in shapes.solids:                       # 속이 찬 상자: 높이 구간에 걸치면 바닥 면적 전체
        if corners[:, 2].max() >= zmin and corners[:, 2].min() <= zmax:
            grid.fill_convex(corners[:, :2])
    for x, y, r, cz0, cz1 in shapes.circles:
        if cz1 >= zmin and cz0 <= zmax:
            grid.fill_circle(x, y, r)
    if border:
        grid.occ[0, :] = grid.occ[-1, :] = True
        grid.occ[:, 0] = grid.occ[:, -1] = True
    return grid


# ---------------------------------------------------------------- 파일 쓰기
def write_map(grid: Grid, out_base: str, comment: str = '') -> tuple[str, str]:
    """<out_base>.pgm, <out_base>.yaml 저장 (map_server 형식)."""
    img = grid.image()
    pgm, yml = out_base + '.pgm', out_base + '.yaml'
    with open(pgm, 'wb') as f:
        f.write(f'P5\n# {comment}\n{grid.width} {grid.height}\n255\n'.encode('ascii', 'replace'))
        f.write(img.tobytes())
    with open(yml, 'w', encoding='utf-8') as f:
        f.write(f'# {comment}\n' if comment else '')
        f.write(f'image: {os.path.basename(pgm)}\n'
                'mode: trinary\n'
                f'resolution: {grid.res}\n'
                f'origin: [{grid.xmin:.3f}, {grid.ymin:.3f}, 0.0]\n'
                'negate: 0\n'
                'occupied_thresh: 0.65\n'
                'free_thresh: 0.25\n')
    return pgm, yml
