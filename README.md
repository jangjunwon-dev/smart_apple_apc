# 🍎 Smart APC — 사과 선별·물류 자동화 시스템

> **농촌 인력난 해소를 위한 스마트 APC(농산물산지유통센터) 사과 선별·물류 자동화 시스템**
> 카메라로 사과 등급을 판정하고, AMR(자율주행 이동로봇)이 등급별 적재 구역으로 운반하는 과정을 **ROS 2 + Gazebo** 시뮬레이션으로 구현합니다.

| 항목 | 내용 |
|---|---|
| 개발 환경 | Windows 11 + **WSL2 Ubuntu 26.04 LTS** |
| 미들웨어 | **ROS 2 Lyrical Luth** (LTS, 2031년 5월까지 지원) |
| 시뮬레이터 | **Gazebo Jetty** (Lyrical 공식 페어) |
| 비전 | Python 3.14, OpenCV, Ultralytics YOLO |
| 주행 | Nav2 |
| 협업 | GitHub (feature 브랜치 → PR → `main`) |
| 공유 드라이브 | [Google Drive `smart_apple_apc`](https://drive.google.com/drive/folders/1pAv_fzKDRd6Efjm4E63q6t5o_J5rNcx2) — `data/` `models/` `발표·보고서/` `시연영상/` |

---

## 👥 팀 구성 및 역할

| 파트 | 담당 | 주요 패키지 | 브랜치 접두어 |
|---|---|---|---|
| 🅐 사과 이미지 분석 (Vision) | **조한서** | `apc_vision` | `feat/vision-*` |
| 🅑 AMR 주행·물류 | **박해원** | `apc_amr` | `feat/amr-*` |
| 🅒 시뮬레이션·통합 | **장준원** (저장소 관리) | `apc_simulation`, `apc_bringup` | `feat/sim-*` |

> 공통 인터페이스(`apc_interfaces`)는 **3명 합의 후에만** 수정합니다. → [docs/03_architecture.md](docs/03_architecture.md)

---

## 🚀 처음 시작하는 팀원 (순서대로)

1. **환경 구축** → [docs/00_environment_setup.md](docs/00_environment_setup.md)
2. **Git 협업 규칙** 읽기 → [docs/01_git_workflow.md](docs/01_git_workflow.md)
3. **진행 계획·현황** 확인 → [docs/02_roadmap.md](docs/02_roadmap.md)
4. **시스템 구조·토픽 규약** 확인 → [docs/03_architecture.md](docs/03_architecture.md)
5. **내 AI(Claude/Codex 등)에 프로젝트 인식시키기** → [docs/04_ai_assistant_guide.md](docs/04_ai_assistant_guide.md)

```bash
# WSL Ubuntu 터미널에서
git clone https://github.com/jangjunwon-dev/smart_apple_apc.git ~/apc_ws
cd ~/apc_ws
bash scripts/setup_ros2_lyrical.sh   # ROS 2 + Gazebo + Nav2 설치 (최초 1회)
bash scripts/setup_python_env.sh     # 비전용 Python 가상환경 (최초 1회)
bash scripts/check_env.sh            # 환경 점검 — 전부 ✅ 여야 함
```

## 🔨 빌드 & 실행

```bash
cd ~/apc_ws
source /opt/ros/lyrical/setup.bash
source .venv/bin/activate
python -m colcon build --symlink-install
source install/setup.bash

# 1) 목(mock) 모드: 비전·AMR 노드만 (Gazebo 없이 토픽 흐름 확인)
ros2 launch apc_bringup mock.launch.py

# 2) 전체: Gazebo 월드 + 비전 + AMR
ros2 launch apc_bringup apc_all.launch.py
```

---

## 📁 저장소 구조

```
smart_apple_apc/              (= ~/apc_ws, colcon 워크스페이스 루트)
├── AGENTS.md                 # AI 코딩 도구 공통 컨텍스트 (Codex, Cursor 등)
├── CLAUDE.md                 # Claude Code용 (AGENTS.md를 불러옴)
├── docs/                     # 가이드·계획·설계 문서
├── scripts/                  # 설치·점검 스크립트
├── requirements.txt          # 비전 파트 Python 패키지
├── data/                     # 데이터셋 — 구조·설명서만 커밋 (data/README.md)
│   ├── sample/               #   테스트용 소량 샘플 (커밋 O)
│   ├── raw/                  #   원본 (공유 드라이브)
│   └── processed/            #   가공본 (공유 드라이브)
├── models/                   # 학습된 가중치 (공유 드라이브, models/README.md)
└── src/
    ├── apc_interfaces/       # 공통 메시지 정의 (AppleGrade, AmrStatus)
    ├── apc_vision/           # 🅐 사과 등급 판정 노드
    ├── apc_amr/              # 🅑 등급→구역 배정, 운반 작업 관리 노드
    ├── apc_simulation/       # 🅒 Gazebo 월드·실행 파일
    └── apc_bringup/          # 🅒 전체 실행 launch
```

---

## 📢 팀원 공지 — 지금 상태와 실행 방법 (2026-11-23 기준)

> 최근 바뀐 내용을 한곳에 모았습니다. 작업 시작 전에 한 번 읽어 주세요. (작성: 🅒 장준원)

### ⚡ 빠른 실행 — 터미널 2개면 끝
| 터미널 | 명령 | 하는 일 |
|---|---|---|
| 1 | `cd ~/apc_ws && bash scripts/run_apc.sh` | 시뮬 실행 + **이 터미널에서 바로 키보드로 로봇 조종** (`w a s d` / 화살표, `f` 시점 따라가기, `q` 종료) |
| 2 | `cd ~/apc_ws && source /opt/ros/lyrical/setup.bash && source install/setup.bash && ros2 run apc_simulation grade_monitor` | 사과 판정·AMR 상태를 **한국어로** 보기 |

- 코드를 새로 받은 직후에는 터미널 1에서 `bash scripts/run_apc.sh --build` (빌드 + 실행)
- 터미널 1 키보드 조종은 **그 터미널을 클릭한 상태**에서 눌러야 함. 시점 따라가기 풀기: Gazebo 창 클릭 후 `Esc`
- 터미널 2 출력 예:
  ```
  [판정] 사과 #91   특     지름  89.3 mm  신뢰도  76%  → 구역 A   (시뮬 68.8초)
  [AMR] amr_1  이동 중  사과 #91 → 구역 A  대기 작업 0개
  [누적] 총 5개: 특 1 / 상 1 / 보통 2 / 비상품 1
  ```

### 🎮 로봇(AMR) 키보드 조종 방법
`bash scripts/run_apc.sh` 를 실행하면 Gazebo 가 뜬 뒤 **그 터미널이 바로 조종기**가 됩니다.

| 키 | 동작 |
|---|---|
| `w` 또는 `↑` | 앞으로 (0.2 m/s) |
| `s` 또는 `↓` | 뒤로 |
| `a` 또는 `←` | 왼쪽으로 제자리 회전 (1.0 rad/s) |
| `d` 또는 `→` | 오른쪽으로 제자리 회전 |
| `space` 또는 `x` | 즉시 정지 |
| `f` | Gazebo 시점(카메라)이 로봇을 따라가기 |
| Gazebo 창 클릭 → `Esc` | 시점 따라가기 풀기 |
| `q` 또는 `Ctrl+C` | 조종 종료 + 시뮬까지 함께 종료 |

**사용 순서**
1. `cd ~/apc_ws && bash scripts/run_apc.sh` (코드를 새로 받았으면 `--build` 추가)
2. Gazebo 창에 컨베이어·사과·로봇(`amr_1`)이 보일 때까지 10~20초 기다리기
3. **터미널을 마우스로 한 번 클릭** — Gazebo 창이 아니라 터미널이 키를 받습니다
4. 키를 **꾹 누르고 있으면** 계속 움직이고, 떼면 약 0.6초 뒤 멈춤 (터미널 화면에 `속도: 앞뒤 +0.20 m/s ...` 표시)
5. `f` 를 누르면 시점이 로봇 뒤 위쪽에서 따라옴 → 자유 시점으로 돌아가려면 Gazebo 창 클릭 후 `Esc`, 다시 운전하려면 **터미널을 다시 클릭**

**알아 둘 것**
- 키 두 개를 동시에 못 받아서 "앞으로 가면서 회전"(대각선)은 안 됩니다. 앞 → 멈춤 → 회전 순서로 조종하세요.
- Caps Lock 이 켜져 있어도(대문자) 똑같이 동작합니다.
- 속도 바꾸기 / 시뮬을 따로 띄운 경우 조종만 실행:
  ```bash
  cd ~/apc_ws && source /opt/ros/lyrical/setup.bash && source install/setup.bash
  ros2 run apc_simulation amr_teleop --ros-args -p linear_speed:=0.15 -p angular_speed:=0.8
  ```
- 조종 없이 예전처럼 로그를 터미널에 보고 싶으면 `bash scripts/run_apc.sh --no-teleop`
- 조종 중 launch 로그는 `log/run_apc/latest.log` (다른 터미널에서 `tail -f log/run_apc/latest.log`)

**안 될 때**
| 증상 | 해결 |
|---|---|
| 키를 눌러도 로봇이 안 움직임 | 터미널을 클릭했는지 확인. 터미널에 `속도:` 줄이 안 찍히면 키가 Gazebo 창으로 가고 있는 것 |
| `속도:` 는 찍히는데 로봇이 안 움직임 | Gazebo 가 아직 뜨는 중이거나 RTF 가 0 — 몇 초 기다리기. `pgrep -fc gz-sim-main` 이 2 이상이면 Gazebo 가 여러 개 떠 있음 → 아래 정리 후 다시 실행 |
| `f` 를 눌러도 시점이 안 바뀜 | headless 실행이면 Gazebo 창이 없어서 안 됨. 아니면 Gazebo 창 Entity Tree 에서 `amr_1` 우클릭 → Follow |
| `No executable found` | 빌드 전 — `bash scripts/run_apc.sh --build` |
| 이전 실행이 남아 느림·꼬임 | `pkill -f gz-sim-main; pkill -f amr_teleop; pkill -f "ros2 launch apc"` 후 다시 실행 |

### 1. 최신 코드 받기 (매번 작업 전)
```bash
cd ~/apc_ws && git switch main && git pull
source /opt/ros/lyrical/setup.bash && source .venv/bin/activate
rosdep install --from-paths src --ignore-src -y     # 새 의존성(예: turtlebot3_gazebo) 설치
python -m colcon build --symlink-install && source install/setup.bash
```

### 2. 실행하기 — `scripts/run_apc.sh` 한 줄이면 됩니다
환경 설정(ROS·venv source, WSL GPU 렌더링), 남은 Gazebo 확인, 모델 파일 확인까지 스크립트가 알아서 합니다.
```bash
cd ~/apc_ws
bash scripts/run_apc.sh --build        # 처음 한 번 / 코드 받은 직후: 빌드 + 실행
bash scripts/run_apc.sh                # 기본 월드 + 실제 YOLO 판정 + 이 터미널에서 바로 키보드로 로봇 조종
bash scripts/run_apc.sh --no-teleop    # 조종 없이 launch 로그를 이 터미널에 출력 (예전 방식)
bash scripts/run_apc.sh --preview      # 창고 배경 월드 (시연용, 더 무거움)
bash scripts/run_apc.sh --mock-vision  # YOLO 없이 무작위 등급
bash scripts/run_apc.sh --help         # 옵션 전체 (--headless, --sphere, -- 뒤 launch 인자 전달)
```
- 비전 모델 `~/apc_ws/models/apple_grader.pt` 가 없으면 자동으로 mock 판정으로 바뀝니다 → [공유 드라이브](https://drive.google.com/drive/folders/1pAv_fzKDRd6Efjm4E63q6t5o_J5rNcx2) `models/` 에서 받아 그 위치에 두세요.
- 판정 결과는 **새 터미널**에서 **한국어로** 봅니다:
  ```bash
  cd ~/apc_ws && source /opt/ros/lyrical/setup.bash && source install/setup.bash
  ros2 run apc_simulation grade_monitor
  # [판정] 사과 #91   특   지름  89.3 mm  신뢰도  76%  → 구역 A   (시뮬 68.8초)
  # [누적] 총 5개: 특 1 / 상 1 / 보통 2 / 비상품 1
  ```
  원본 메시지 그대로 보려면 `ros2 topic echo /apc/apple_grade` (`grade` 0=특 1=상 2=보통 3=비상품)
- 종료는 `Ctrl+C`. 끝날 때 `Segmentation fault (exit 139)` 가 떠도 Gazebo 자체의 알려진 현상이라 괜찮습니다.
- 스크립트 없이 직접 실행하려면: `ros2 launch apc_bringup apc_all.launch.py vision_mock:=false amr_mock:=true`
  (WSL 에서 카메라가 검게 나오면 `export GALLIUM_DRIVER=d3d12`, NVIDIA GPU 면 `export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` 도)

### 3. `apc_all.launch.py` 실행 옵션
| 인자 | 기본값 | 설명 |
|---|---|---|
| `vision_mock` | `true` | `false` 면 YOLO(`apple_grader.pt`)로 실제 판정 |
| `amr_mock` | `true` | `false` 면 AMR 실제 동작 (🅑 구현 후) |
| `world` | `apc_world.sdf` | `apc_world_v2_preview.sdf` 로 바꾸면 창고 배경이 있는 월드 |
| `headless` | `false` | `true` 면 Gazebo 창 없이 실행 (카메라는 동작) |
| `spawn_apples` | `true` | `false` 면 사과를 만들지 않음 |
| `apple_model` | `ycb` | `sphere` 면 단색 구 (AMR·물류만 볼 때 가벼움) |

### 4. 월드 2개 — 평소엔 기본, 시연은 배경 월드
| 월드 | 모습 | 실시간 비율(RTF, YOLO 켬) | 용도 |
|---|---|---|---|
| `apc_world.sdf` (기본) | 회색 바닥 + 컨베이어 + 색 구역 | 약 90~95% | 평소 개발·테스트 |
| `apc_world_v2_preview.sdf` | 창고 건물·세척 터널·저온저장고·팔레트 | 약 70~80% | 시연 영상·발표 캡처 |

- 두 월드는 컨베이어·카메라·구역(zone) 좌표가 완전히 같습니다. 배경 월드는 `scripts/gen_preview_world.py` 가 기본 월드에서 자동으로 만듭니다 (직접 수정 금지).
- 배경 월드에는 AMR 이 부딪힐 수 있는 장애물(다리·제어반)이 있으니, Nav2 맵은 배경 월드 기준으로 만들면 두 월드 모두에서 쓸 수 있습니다.

### 5. 최근 바뀐 것
| PR | 내용 | 영향 |
|---|---|---|
| #20 | 선별 카메라 확대 (시야 0.3 rad, 30Hz) | 시뮬 사과 판정 0% → 100% |
| #22 | 비전: 지름 = 짧은 축 중앙값, 여러 프레임 신뢰도 투표 | 판정 안정화 |
| #23 | 사과 기본 외형 `ycb`(실제 사과 3D 스캔), 시작 직후 사과 2개 붙어 나오던 버그 수정 | 검출 75% → 거의 100%, 사과 간격 정확히 4초 |
| #26 | AMR 로봇 TurtleBot3 Waffle(임시) + `/cmd_vel`·`/odom`·`/scan`·`/tf` 브리지 | 로봇이 월드에 자동 등장, rosdep install 필요 |
| #28 | 키보드 조종 `amr_teleop` (WASD·화살표, `f` 시점 따라가기), `run_apc.sh` 로 켜면 바로 조종 | 로그는 `log/run_apc/latest.log` |
| #29 | 등급 = YOLO 품질 등급과 지름 크기 등급 중 낮은 쪽, `header.stamp` 판정 시각 | 등급이 특·상·보통·비상품으로 섞여 나옴 |
| #31 | 아키텍처 문서에 AMR 토픽·좌표계 추가 | `docs/03_architecture.md` 2-1·2-2절 |
| #32 | 4레인 시험 월드 재생성, 로봇 시작 위치 기본값 한곳(`amr_robot.py`)으로 | |
| #33 | (🅐) `logs/` git 추적 해제, 판정 구역 25~75%·투표 6프레임, 🅐 로드맵 체크 | `git pull` 막히던 문제 해결 |
| #34 | 판정·AMR 상태 한국어 모니터 `grade_monitor` | 위 "빠른 실행" 터미널 2 |

### 6. 1단계(인터페이스 확정, ~11/24) 남은 것
- **등급 기준값** — 구현 완료(#29). 최종 등급 = (YOLO 품질 등급, 지름 크기 등급) 중 낮은 쪽, 크기 특 ≥ 89 / 상 ≥ 83 / 보통 ≥ 76 / 비상품 < 76 mm.
  🅐 조한서 확인 완료, **🅑 박해원 확인만 남음** → 확인되면 로드맵 결정 사항 "확정"으로.
  끄려면 `grader_node` 파라미터 `size_grading:=false` (예전처럼 YOLO 클래스만).
- **인터페이스** — `AppleGrade`·`AmrStatus` 는 그대로, AMR 표준 토픽·좌표계는 #31 로 문서 반영 (Issue #30).
- **3명 환경 점검** — `bash scripts/check_env.sh` 결과를 단톡에 공유 (🅑 미확인).

### 7. AMR 로봇 — TurtleBot3 Waffle (임시) 추가됨 (#26)
- Lyrical 에는 **TurtleBot4 패키지가 없어서** **TurtleBot3 Waffle** 을 임시 기본 로봇으로 넣었습니다. 다른 로봇이 좋으면 🅑 박해원 님이 알려 주세요.
- ⚠️ **pull 후 한 번 꼭 실행** (안 하면 시뮬이 안 켜짐):
  ```bash
  cd ~/apc_ws && rosdep install --from-paths src --ignore-src -y   # turtlebot3_gazebo 설치
  ```
- **키보드로 로봇 조종**: 위 [🎮 로봇(AMR) 키보드 조종 방법](#-로봇amr-키보드-조종-방법) 참고 (`bash scripts/run_apc.sh` → 터미널 클릭 → `w a s d`)
- 실행하면 로봇이 (1.5, 0) 에 자동으로 나옵니다. 로봇 없이: `spawn_amr:=false`, 위치 변경: `amr_x:=1.0 amr_y:=-1.0 amr_yaw:=1.57`
- 토픽: `/cmd_vel`(TwistStamped) · `/odom` · `/scan` · `/tf` · `/joint_states`, 프레임 `odom → base_footprint → base_link → base_scan`
- 로봇이 있으면 배경 월드 RTF 가 약 0.7 로 떨어짐(라이다 렌더링) → **Nav2 개발은 기본 월드**에서 (RTF 약 0.92)
- 로봇 교체: `src/apc_simulation/apc_simulation/amr_robot.py` 상수 + `config/amr_bridge.yaml` 만 수정
- `slam_toolbox`, Nav2 1.5.2 는 Lyrical 에서 설치 가능

### 8. 파트별 부탁
- 🅐 조한서: 시뮬 사과는 지름 70~96 mm 인데 가끔 **100 mm 넘게** 측정됨 (예: 105.1 mm) — 크기 등급이 실제보다 높게 나올 수 있어 확인 부탁
- 🅑 박해원: 등급 기준·로봇(TurtleBot3 Waffle)·맵 방식(SLAM 또는 월드 기준 직접 작성) 확인 / `check_env.sh` 결과 공유 / Nav2 로 등급별 구역 운반 시작 (`amr_mock:=false`)
- 🅒 장준원: 🅑 Nav2 연동 지원(필요하면 월드 기준 맵 생성) → 통합 테스트 → 시연 영상
