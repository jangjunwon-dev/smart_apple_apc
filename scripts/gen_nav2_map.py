#!/usr/bin/env python3
"""Gazebo 월드 파일로 Nav2 지도(pgm + yaml)를 만든다 — SLAM 없이 바로 Nav2 를 쓰기 위함.

사용법 (저장소 루트에서, ROS source 불필요):
  python3 scripts/gen_nav2_map.py                       # 두 월드 모두 → src/apc_simulation/maps/
  python3 scripts/gen_nav2_map.py apc_world.sdf         # 하나만
  python3 scripts/gen_nav2_map.py apc_world.sdf --res 0.05 --zmin 0.05 --zmax 0.4 --png

- 높이 zmin~zmax(기본 0.05~0.4 m, TurtleBot3 Waffle 몸체·라이다 높이 포함) 사이에 걸친
  물체만 점유로 칠함 → 바닥 구역 표시판(높이 1 cm)·천장·카메라는 빠짐.
- 지도 범위는 월드 물체 + 여백 2 m (월드 가장자리 한 칸은 점유로 막음).
- 월드 파일을 바꾸면 다시 실행해서 maps/ 를 함께 커밋할 것 (test_nav2_map 이 검사).
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM = os.path.join(ROOT, 'src', 'apc_simulation')
sys.path.insert(0, SIM)

from apc_simulation.world_map import build_grid, WorldReader, write_map  # noqa: E402

WORLDS = ['apc_world.sdf', 'apc_world_v2_preview.sdf']


def generate(world: str, args) -> None:
    path = world if os.path.isabs(world) else os.path.join(SIM, 'worlds', world)
    reader = WorldReader([os.path.join(SIM, 'models')], use_visual=not args.collision_only)
    shapes = reader.read_world(path)
    bounds = tuple(args.bounds) if args.bounds else None
    grid = build_grid(shapes, args.res, args.zmin, args.zmax, bounds, args.margin)
    stem = os.path.splitext(os.path.basename(path))[0]
    os.makedirs(args.out_dir, exist_ok=True)
    comment = (f'gen_nav2_map.py {os.path.basename(path)} res={args.res} '
               f'z=[{args.zmin},{args.zmax}] — 손으로 고치지 말고 다시 생성')
    pgm, yml = write_map(grid, os.path.join(args.out_dir, stem), comment)
    occ = grid.occ.mean() * 100
    print(f'✅ {os.path.relpath(yml, ROOT)}  {grid.width}x{grid.height} 칸 '
          f'({grid.width * args.res:.1f} x {grid.height * args.res:.1f} m), '
          f'원점 ({grid.xmin:.2f}, {grid.ymin:.2f}), 점유 {occ:.1f}%')
    for s in sorted(set(reader.shapes.skipped)):
        print(f'   ⚠ 건너뜀(지원 안 하는 메시 — 같은 모델의 충돌 박스로 대신함): {s}')
    if args.png:
        try:
            from PIL import Image
            Image.fromarray(grid.image()).save(os.path.join(args.out_dir, stem + '.png'))
        except ImportError:
            print('   (PNG 저장에는 Pillow 필요: pip install pillow)')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('worlds', nargs='*', default=WORLDS, help='worlds/ 안의 파일 이름 또는 경로')
    ap.add_argument('--res', type=float, default=0.05, help='격자 한 칸 크기 m (기본 0.05)')
    ap.add_argument('--zmin', type=float, default=0.05, help='이 높이부터 장애물 (기본 0.05 m)')
    ap.add_argument('--zmax', type=float, default=0.4, help='이 높이까지 장애물 (기본 0.4 m)')
    ap.add_argument('--margin', type=float, default=2.0, help='자동 범위 여백 m (기본 2)')
    ap.add_argument('--bounds', type=float, nargs=4, metavar=('XMIN', 'YMIN', 'XMAX', 'YMAX'))
    ap.add_argument('--collision-only', action='store_true',
                    help='보이는 모양(visual)은 빼고 충돌 모양만 사용')
    ap.add_argument('--out-dir', default=os.path.join(SIM, 'maps'))
    ap.add_argument('--png', action='store_true', help='확인용 PNG 도 저장')
    args = ap.parse_args()
    for w in args.worlds:
        generate(w, args)


if __name__ == '__main__':
    main()
