#!/usr/bin/env python3
"""4레인 성능 측정용 시험 월드 생성기: apc_world.sdf → apc_world_4lane_test.sdf

사용법 (저장소 루트에서):
  python3 scripts/make_4lane.py
  python3 scripts/make_4lane.py <원본.sdf> <결과.sdf>
기본값: src/apc_simulation/worlds/apc_world.sdf → src/apc_simulation/worlds/apc_world_4lane_test.sdf

apc_world.sdf 를 바꾼 뒤에는 이 스크립트를 다시 실행해 시험 월드를 맞춰 주세요.
레인 위치·색(LANES), 왕복 주기(HALF_PERIOD_MS), 위상차(PHASE_MS), 밀기 거리(STROKE)는 아래 상수로 조정.
※ 성능 측정용이라 밀대는 사과 판정과 동기화하지 않고 주기적으로 왕복함.
   실제 레인 구현 시에는 판정 결과(/apc/apple_grade)에 맞춰 해당 레인 밀대만 동작시켜야 함.
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLDS = os.path.join(ROOT, 'src', 'apc_simulation', 'worlds')
if len(sys.argv) == 3:
    src, dst = sys.argv[1], sys.argv[2]
elif len(sys.argv) == 1:
    src = os.path.join(WORLDS, 'apc_world.sdf')
    dst = os.path.join(WORLDS, 'apc_world_4lane_test.sdf')
else:
    sys.exit('사용법: python3 scripts/make_4lane.py [<원본.sdf> <결과.sdf>]')
with open(src) as f:
    s = f.read()

CONV_X = -2.0                      # 컨베이어 모델 중심 x
LANES = [                          # (이름, 레인 중심 x(world), 색)
    ('special', -1.40, '0.1 0.6 0.1'),
    ('good', -1.15, '0.1 0.3 0.8'),
    ('normal', -0.90, '0.9 0.7 0.1'),
    ('reject', -0.65, '0.7 0.1 0.1'),
]
GAP = 0.2                          # 레일 틈 폭 (m)
PHASE_MS = 500                     # 레인 간 위상차
HALF_PERIOD_MS = 1000              # 밀기/복귀 각각 1초 → 2초 주기
STROKE = 0.6                       # 밀어내기 거리 (m)
TP_OPEN = ('      <plugin filename="gz-sim-triggered-publisher-system"'
           ' name="gz::sim::systems::TriggeredPublisher">')


def box(name, pose, size, color='0.6 0.6 0.6', collide=True, mu=None):
    out = ''
    if collide:
        surface = ''
        if mu is not None:
            surface = (f'<surface><friction><ode><mu>{mu}</mu><mu2>{mu}</mu2></ode></friction>'
                       '</surface>')
        out += (f'        <collision name="{name}_collision"><pose>{pose}</pose>'
                f'<geometry><box><size>{size}</size></box></geometry>{surface}</collision>\n')
    out += (f'        <visual name="{name}_visual"><pose>{pose}</pose>'
            f'<geometry><box><size>{size}</size></box></geometry>'
            f'<material><ambient>{color} 1</ambient><diffuse>{color} 1</diffuse></material>'
            '</visual>\n')
    return out


# ---- 1) 가이드 레일을 레인 입구마다 틈이 생기도록 구간 분할 (모델 좌표 x: -1.5~1.5) ----
gaps = sorted((lx - CONV_X - GAP / 2, lx - CONV_X + GAP / 2) for _, lx, _ in LANES)
segs, start = [], -1.5
for g0, g1 in gaps:
    segs.append((start, g0))
    start = g1
segs.append((start, 1.5))
rails = '      <!-- 가이드 레일: 벨트와 다른 링크여야 TrackController 영향을 받지 않음\n' \
        '           [4레인 시험] 레인 입구마다 0.2m 틈 (밀어내기 판·사과가 지나가도록) -->\n' \
        '      <link name="guides">\n'
for side, y in (('left', 0.26), ('right', -0.26)):
    for i, (a, b) in enumerate(segs):
        rails += box(f'{side}_{i}', f'{(a + b) / 2:.3f} {y} 0.43 0 0 0', f'{b - a:.3f} 0.02 0.06')
rails += '      </link>\n'
a = s.index('      <!-- 가이드 레일')
b = s.index('      <plugin filename="gz-sim-track-controller-system"')
s = s[:a] + rails + s[b:]

# ---- 2) 레인 + 밀어내기 장치 + 왕복 타이머 ----
dy, dz = 0.73, 0.43                     # 슈트: y -0.27 → -1.00, z 0.78 → 0.35
tilt = math.atan2(dz, dy)
length = math.hypot(dy, dz)
cy, cz = -0.27 - dy / 2, 0.78 - dz / 2

extra = '''
    <!-- ================= [4레인 시험] 성능 측정용 추가 요소 =================
         등급별 배출 레인 4개(특/상/보통/비상품) + 밀어내기 장치 4개(prismatic + JointPositionController)
         왕복: /apc/bench/tick(Int32) 1 ↔ 2 를 TriggeredPublisher 가 1초 지연으로 서로 발행해 스스로 진동
               (bench_sim.sh 가 시작할 때 data:1 을 한 번 보내 순환 시작)
         레인 끝 logical_camera 는 apc/sim/apple_sink 로 발행 → 배출된 사과도 스포너가 삭제 -->
    <model name="bench_ticker">
      <static>true</static>
      <link name="l"/>
%(tp)s
        <input type="gz.msgs.Int32" topic="/apc/bench/tick"><match field="data">1</match></input>
        <output type="gz.msgs.Int32" topic="/apc/bench/tick">data: 2</output>
        <delay_ms>%(half)d</delay_ms>
      </plugin>
%(tp)s
        <input type="gz.msgs.Int32" topic="/apc/bench/tick"><match field="data">2</match></input>
        <output type="gz.msgs.Int32" topic="/apc/bench/tick">data: 1</output>
        <delay_ms>%(half)d</delay_ms>
      </plugin>
    </model>
''' % {'tp': TP_OPEN, 'half': HALF_PERIOD_MS}

for i, (g, lx, color) in enumerate(LANES):
    cmd = f'/apc/bench/pusher_{g}/cmd'
    delay = i * PHASE_MS
    chute_boxes = ''.join([
        box('slide', f'0 {cy:.3f} {cz:.3f} {tilt:.4f} 0 0', f'0.2 {length:.3f} 0.02', color,
            mu=0.1),
        box('wall_l', f'-0.11 {cy:.3f} {cz + 0.04:.3f} {tilt:.4f} 0 0',
            f'0.02 {length:.3f} 0.08', mu=0.1),
        box('wall_r', f'0.11 {cy:.3f} {cz + 0.04:.3f} {tilt:.4f} 0 0',
            f'0.02 {length:.3f} 0.08', mu=0.1),
        box('bin', '0 -1.25 0.005 0 0 0', '0.24 0.5 0.01', color, collide=False),
        box('bin_l', '-0.12 -1.25 0.05 0 0 0', '0.02 0.5 0.1'),
        box('bin_r', '0.12 -1.25 0.05 0 0 0', '0.02 0.5 0.1'),
        box('bin_end', '0 -1.5 0.05 0 0 0', '0.26 0.02 0.1'),
    ])
    extra += f'''
    <!-- 배출 레인: {g} -->
    <model name="lane_{g}">
      <static>true</static>
      <pose>{lx} 0 0 0 0 0</pose>
      <link name="chute">
{chute_boxes}        <sensor name="lane_{g}_sink" type="logical_camera">
          <pose>0 -1.1 0.9 0 1.5707 0</pose>
          <update_rate>10</update_rate>
          <logical_camera><near>0.05</near><far>1.0</far>
            <horizontal_fov>1.2</horizontal_fov><aspect_ratio>1.0</aspect_ratio></logical_camera>
          <always_on>1</always_on>
          <topic>apc/sim/apple_sink</topic>
        </sensor>
      </link>
    </model>

    <!-- 밀어내기 장치: {g} (+y 쪽에서 -y 로 밀어 레인으로 배출) -->
    <model name="pusher_{g}">
      <pose>{lx} 0.36 0.85 0 0 0</pose>
      <link name="base">
        <inertial><mass>2.0</mass></inertial>
{box('base', '0 0.03 0 0 0 0', '0.12 0.04 0.10', '0.3 0.3 0.3', collide=False)}      </link>
      <joint name="fix" type="fixed"><parent>world</parent><child>base</child></joint>
      <link name="paddle">
        <pose>0 -0.03 0 0 0 0</pose>
        <inertial>
          <mass>0.3</mass>
          <inertia><ixx>0.0002</ixx><iyy>0.0004</iyy><izz>0.0004</izz>
            <ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia>
        </inertial>
{box('paddle', '0 0 0 0 0 0', '0.12 0.02 0.08', color, mu=0.0)}      </link>
      <joint name="slide" type="prismatic">
        <parent>base</parent><child>paddle</child>
        <axis><xyz>0 -1 0</xyz>
          <limit><lower>0</lower><upper>{STROKE}</upper><effort>200</effort><velocity>2.0</velocity></limit>
        </axis>
      </joint>
      <plugin filename="gz-sim-joint-position-controller-system"
              name="gz::sim::systems::JointPositionController">
        <joint_name>slide</joint_name>
        <topic>{cmd}</topic>
        <use_velocity_commands>true</use_velocity_commands>
        <p_gain>6</p_gain>
        <cmd_max>1.5</cmd_max>
        <cmd_min>-1.5</cmd_min>
      </plugin>
      <!-- 왕복: tick=1 → 밀기, tick=2 → 복귀 (레인마다 {PHASE_MS}ms 위상차) -->
{TP_OPEN}
        <input type="gz.msgs.Int32" topic="/apc/bench/tick"><match field="data">1</match></input>
        <output type="gz.msgs.Double" topic="{cmd}">data: {STROKE}</output>
        <delay_ms>{delay}</delay_ms>
      </plugin>
{TP_OPEN}
        <input type="gz.msgs.Int32" topic="/apc/bench/tick"><match field="data">2</match></input>
        <output type="gz.msgs.Double" topic="{cmd}">data: 0.0</output>
        <delay_ms>{delay}</delay_ms>
      </plugin>
    </model>
'''

# ---- 3) +y 쪽 막이 벽 + 바닥 수거 카메라 ----
# 판은 사과 도착과 동기화하지 않고 2초 주기로 왕복(부하 시험용)하므로, 판이 뻗어 있을 때 들어온 사과를
# 복귀 행정의 판 뒷면이 +y 로 쳐낼 수 있음 → 벽으로 막고 바닥에 떨어진 사과도 수거해 사과 수 유지
xs = [lx for _, lx, _ in LANES]
wall_x0, wall_x1 = min(xs) - 0.3, max(xs) + 0.3
wall_box = box('wall', f'{(wall_x0 + wall_x1) / 2:.3f} 0.52 0.5 0 0 0',
               f'{wall_x1 - wall_x0:.3f} 0.02 1.0')
extra += f"""
    <!-- [4레인 시험] +y 막이 벽 + 바닥 수거 카메라 (복귀 행정에 튕겨난 사과 수거) -->
    <model name="bench_overflow">
      <static>true</static>
      <link name="l">
{wall_box}"""
for i, cx in enumerate((min(xs) + 0.1, max(xs) - 0.1)):
    extra += f"""        <sensor name="overflow_sink_{i}" type="logical_camera">
          <pose>{cx:.3f} 0.38 0.6 0 1.5707 0</pose>
          <update_rate>10</update_rate>
          <logical_camera><near>0.05</near><far>0.65</far>
            <horizontal_fov>1.2</horizontal_fov><aspect_ratio>1.0</aspect_ratio></logical_camera>
          <always_on>1</always_on>
          <topic>apc/sim/apple_sink</topic>
        </sensor>
"""
extra += """      </link>
    </model>
"""

s = s.replace('  </world>', extra + '  </world>')
s = s.replace('  Smart APC 기본 월드 (Gazebo Jetty)',
              '  Smart APC 4레인 성능 측정용 시험 월드 (Gazebo Jetty) — apc_world.sdf 복사본\n'
              '  ※ 성능 측정(scripts/bench_sim.sh) 전용. 기본 launch 는 apc_world.sdf 를 사용\n'
              '  ※ world 이름은 apc_world 그대로 (기존 브리지·스포너 재사용)\n'
              '  ※ 레인 4개·밀어내기 장치 4개는 파일 끝 [4레인 시험] 블록')
with open(dst, 'w') as f:
    f.write(s)
print(f'생성 완료: {dst}')
