# Nav2 지도 (월드에서 자동 생성)

| 파일 | 월드 | 크기 | 용도 |
|---|---|---|---|
| `apc_world.yaml` / `.pgm` | `apc_world.sdf` (기본) | 12.0 × 10.0 m | 평소 개발·Nav2 시험 |
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
ros2 launch nav2_bringup bringup_launch.py map:=$MAP use_sim_time:=true
# RViz 의 "2D Pose Estimate" 로 (1.5, 0) 을 찍거나, AMCL 파라미터 initial_pose 를 x 1.5 / y 0.0 / yaw 0.0 으로
```
SLAM(`slam_toolbox`)으로 직접 만든 지도와 비교하거나 예비용으로 써도 됩니다.

## 다시 만들기 (월드를 바꿨을 때, ROS source 불필요)
```bash
cd ~/apc_ws && python3 scripts/gen_nav2_map.py          # 두 월드 모두
python3 scripts/gen_nav2_map.py apc_world.sdf --png     # 확인용 PNG 도 (Pillow 필요)
python3 scripts/gen_nav2_map.py --help                  # 해상도·높이 구간·범위 옵션
```
`.pgm`/`.yaml` 은 손으로 고치지 말고 다시 생성해서 커밋하세요.
