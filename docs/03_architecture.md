# 03. 시스템 구조 & 인터페이스 규약

> 이 문서는 **팀 간 계약서**입니다. 토픽 이름·메시지 필드는 3명이 합의한 뒤에만 바꿉니다.
> 바꿀 때는 `interface-change` 라벨을 붙인 Issue → 합의 → PR 순서로 진행합니다.

## 1. 전체 흐름

```
 ┌────────────┐   /apc/camera/image_raw   ┌──────────────────┐
 │  Gazebo    │ ────────────────────────▶ │  🅐 apc_vision    │
 │  (컨베이어  │      sensor_msgs/Image    │  grader_node     │
 │   + 카메라) │                           │  (YOLO 등급 판정) │
 └────────────┘                           └────────┬─────────┘
       ▲                                           │ /apc/apple_grade
       │ /cmd_vel, /navigate_to_pose               │ apc_interfaces/AppleGrade
       │                                           ▼
 ┌─────┴──────────┐   /apc/amr_status    ┌──────────────────────┐
 │  Nav2 (AMR)    │ ◀─────────────────── │  🅑 apc_amr           │
 │  TurtleBot4 등 │   AmrStatus          │  task_manager_node   │
 └────────────────┘ ──────────────────▶  │  (등급→구역 배정·운반) │
                                          └──────────────────────┘
               🅒 apc_simulation / apc_bringup : 월드·launch·통합
```

## 2. 토픽 규약

| 토픽 | 타입 | 발행 | 구독 | 주기 |
|---|---|---|---|---|
| `/apc/camera/image_raw` | `sensor_msgs/Image` | Gazebo 카메라 (🅒) | 🅐 | 10~30 Hz |
| `/apc/apple_grade` | `apc_interfaces/AppleGrade` | 🅐 | 🅑 | 사과 1개당 1회 |
| `/apc/amr_status` | `apc_interfaces/AmrStatus` | 🅑 | 🅒(모니터링) | 1 Hz + 상태 변화 시 |
| `/navigate_to_pose` (action) | `nav2_msgs/NavigateToPose` | 🅑 | Nav2 | 작업당 1회 |

- 모든 프로젝트 토픽은 **`/apc/` 접두어**를 씁니다.
- 좌표계: `map` (전역), `base_link` (로봇) — REP-105 준수.

## 3. 메시지 정의 (`src/apc_interfaces/msg/`)

### AppleGrade.msg
```
std_msgs/Header header
uint32  apple_id          # 컨베이어 진입 순서 번호
uint8   grade             # 아래 상수 중 하나
float32 confidence        # 0.0 ~ 1.0
float32 diameter_mm       # 추정 지름 (mm), 모르면 0
float32 defect_ratio      # 결함 면적 비율 0.0 ~ 1.0
string  zone_id           # 적재 구역 ID (apc_amr이 채워도 됨, 비전은 빈 문자열 허용)

uint8 GRADE_SPECIAL = 0   # 특
uint8 GRADE_GOOD    = 1   # 상
uint8 GRADE_NORMAL  = 2   # 보통
uint8 GRADE_REJECT  = 3   # 비상품(불량)
```

> 등급 기준(지름·결함 비율 경계값)은 기획서 기준을 따르며 [`02_roadmap.md`](02_roadmap.md)의 "결정 사항"에 기록합니다.

### AmrStatus.msg
```
std_msgs/Header header
string  robot_id
uint8   state             # 아래 상수
uint32  current_apple_id  # 운반 중인 사과 (없으면 0)
string  target_zone
uint32  queue_length      # 대기 중인 운반 작업 수

uint8 STATE_IDLE      = 0
uint8 STATE_LOADING   = 1
uint8 STATE_MOVING    = 2
uint8 STATE_UNLOADING = 3
uint8 STATE_ERROR     = 4
```

## 4. 등급 → 적재 구역 매핑

`src/apc_amr/config/zones.yaml` 에서 관리 (좌표는 🅒가 월드 완성 후 갱신)

| 등급 | zone_id | 비고 |
|---|---|---|
| 특 | `ZONE_A` | |
| 상 | `ZONE_B` | |
| 보통 | `ZONE_C` | |
| 비상품 | `ZONE_R` | 가공용/폐기 |

## 5. 병렬 개발을 위한 Mock 모드

각 파트가 다른 파트를 기다리지 않도록 **모든 노드에 `mock` 파라미터**가 있습니다.

| 노드 | `mock:=true` 일 때 |
|---|---|
| `apc_vision/grader_node` | 카메라 없이 2초마다 무작위 `AppleGrade` 발행 |
| `apc_amr/task_manager_node` | Nav2 없이 이동 시간을 흉내 내며 `AmrStatus` 발행 |

```bash
ros2 launch apc_bringup mock.launch.py         # 둘 다 mock
ros2 run apc_vision grader_node --ros-args -p mock:=false   # 비전만 실제
```

## 6. 패키지 소유권

| 패키지 | 담당 | 다른 사람이 수정할 때 |
|---|---|---|
| `apc_interfaces` | 3명 공동 | Issue 합의 필수 |
| `apc_vision` | 🅐 | PR 리뷰에 🅐 필수 |
| `apc_amr` | 🅑 | PR 리뷰에 🅑 필수 |
| `apc_simulation`, `apc_bringup` | 🅒 | PR 리뷰에 🅒 필수 |
| `docs/`, `scripts/`, `AGENTS.md` | 3명 공동 | 리뷰 1명 |
