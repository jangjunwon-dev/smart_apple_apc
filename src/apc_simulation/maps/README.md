# Nav2 지도 (월드에서 자동 생성)

| 파일 | 월드 | 크기 | 용도 |
|---|---|---|---|
| `apc_world.yaml` / `.pgm` | `apc_world.sdf` (기본) | 13.6 × 11.2 m | 평소 개발·Nav2 시험 (AMCL 기준물 기둥 6개·벽 2개 포함) |
| `apc_world_v2_preview.yaml` / `.pgm` | `apc_world_v2_preview.sdf` (배경) | 24.2 × 16.2 m | 시연 |

- 격자 5 cm, 높이 0.05~0.4 m 에 걸친 물체(컨베이어, 벽, 랙, 팔레트, 상자, 장식 기둥 등)를 점유로 칠함.
  바닥 구역 표시판·천장·카메라는 빠짐.
- **지도 좌표 = Gazebo 월드 좌표**입니다 (`origin` 이 월드 기준). 그래서
  - AMCL 초기 위치 = 로봇 스폰 위치 그대로 **(1.5, 0.0, yaw 0)** (`apc_simulation/amr_robot.py`)
  - `apc_amr/config/zones.yaml` 의 구역 좌표를 Nav2 목표로 그대로 쓸 수 있음
- 테스트(`test/test_nav2_map.py`)가 로봇 시작 위치·구역 중심이 비어 있는지, 지도가 월드와 같은지 검사합니다.

## Nav2 에서 쓰기 (🅑)
```bash
source /opt/ros/lyrical/setup.bash && source ~/apc_ws/install/setup.bash
MAP=$(ros2 pkg prefix apc_simulation)/share/apc_simulation/maps/apc_world.yaml
ros2 launch nav2_bringup localization_launch.py map:=$MAP use_sim_time:=true
# ⚠ Lyrical 의 localization_launch.py 에는 lifecycle_manager 가 없어 map_server·amcl 이 비활성으로 남음 → 따로 실행
ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args -r __node:=lifecycle_manager_localization \
  -p use_sim_time:=true -p autostart:=true -p "node_names:=['map_server','amcl']"
# 초기 위치: RViz "2D Pose Estimate" 로 (1.5, 0) 을 찍거나 /initialpose 발행 (x 1.5, y 0.0, yaw 0.0)
```
SLAM(`slam_toolbox`)으로 직접 만든 지도와 비교하거나 예비용으로 써도 됩니다.

## 검증 결과 (2026-11-24, WSL · Gazebo Jetty · nav2_bringup localization)
- `/map` 크기·해상도·원점이 yaml 과 **정확히 일치**, 시작 위치 반경 0.3 m 안 장애물 없음
- 실제 로봇 위치에서 라이다 스캔과 지도 레이캐스트 비교: 거리차 중앙값 **0.9~2.3 cm**, 지도를 옮겨 봐도 (0, 0) 이 가장 잘 맞음 → **원점·축 어긋남 없음**
- AMCL 위치 오차(전진 1 m → 90° 회전 → 전진 1 m, map→base_footprint TF 기준)

  | AMCL 설정 | 기본 월드 | 배경 월드 |
  |---|---|---|
  | nav2_bringup 기본값 | 최대 25.7 cm / 3.4° | 최대 39.3 cm / 2.3° |
  | 아래 조정값 | 최대 24.4 cm / 2.1° | 최대 14.6 cm / 0.8° |

- 오차 원인은 지도가 아니라
  - **기본 월드는 라이다(사거리 3.5 m) 안에 볼 구조물이 거의 없음** (360빔 중 약 10빔만 맞음) → x 방향을 잡을 근거 부족
    → 이후 기본 월드에 기준물(기둥·벽, `nav_*`)을 추가함. 지도 기준 맞는 빔 수: 시작 16→39, zone 앞 0→66~108
  - nav2 기본 AMCL 은 스캔을 덜 믿고 오도메트리 잡음을 크게 잡음
  - Gazebo TB3 제자리 회전 시 바퀴 미끄러짐 (/odom 90° 인데 실제 약 86°)
- 참고 조정값 (스크래치에서 시험, 🅑 Nav2 params 에 반영할지 판단): `alpha1~4 0.05`, `z_hit 0.9`, `z_rand 0.1`, `sigma_hit 0.05`,
  `max_beams 180`, `laser_max_range 3.5`, `update_min_d 0.1`, `update_min_a 0.1`
- 작은 차이 (영향 작음): 4~5 cm 다리·기둥은 지도에서 10 cm 로 보임, 랙 위 상자 바닥(0.144 m)이 라이다 높이(약 0.142 m)와 거의 같아 라이다는 상자 아래 팔레트에 맞음

## 다시 만들기 (월드를 바꿨을 때, ROS source 불필요)
```bash
cd ~/apc_ws && python3 scripts/gen_nav2_map.py          # 두 월드 모두
python3 scripts/gen_nav2_map.py apc_world.sdf --png     # 확인용 PNG 도 (Pillow 필요)
python3 scripts/gen_nav2_map.py --help                  # 해상도·높이 구간·범위 옵션
```
`.pgm`/`.yaml` 은 손으로 고치지 말고 다시 생성해서 커밋하세요.
