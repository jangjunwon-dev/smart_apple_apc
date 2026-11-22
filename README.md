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

## 📢 팀원 공지 — 지금 상태와 실행 방법 (2026-11-22 기준)

> 최근 바뀐 내용을 한곳에 모았습니다. 작업 시작 전에 한 번 읽어 주세요. (작성: 🅒 장준원)

### 1. 최신 코드 받기 (매번 작업 전)
```bash
cd ~/apc_ws && git switch main && git pull
source /opt/ros/lyrical/setup.bash && source .venv/bin/activate
python -m colcon build --symlink-install && source install/setup.bash
```

### 2. 실행하기 — `scripts/run_apc.sh` 한 줄이면 됩니다
환경 설정(ROS·venv source, WSL GPU 렌더링), 남은 Gazebo 확인, 모델 파일 확인까지 스크립트가 알아서 합니다.
```bash
cd ~/apc_ws
bash scripts/run_apc.sh --build        # 처음 한 번 / 코드 받은 직후: 빌드 + 실행
bash scripts/run_apc.sh                # 기본 월드 + 실제 YOLO 판정 + AMR mock
bash scripts/run_apc.sh --preview      # 창고 배경 월드 (시연용, 더 무거움)
bash scripts/run_apc.sh --mock-vision  # YOLO 없이 무작위 등급
bash scripts/run_apc.sh --help         # 옵션 전체 (--headless, --sphere, -- 뒤 launch 인자 전달)
```
- 비전 모델 `~/apc_ws/models/apple_grader.pt` 가 없으면 자동으로 mock 판정으로 바뀝니다 → [공유 드라이브](https://drive.google.com/drive/folders/1pAv_fzKDRd6Efjm4E63q6t5o_J5rNcx2) `models/` 에서 받아 그 위치에 두세요.
- 판정 결과는 **새 터미널**에서 봅니다 (사과 1개당 1번 찍힘, `grade` 0=특 1=상 2=보통 3=비상품):
  ```bash
  cd ~/apc_ws && source /opt/ros/lyrical/setup.bash && source install/setup.bash
  ros2 topic echo /apc/apple_grade
  ```
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

### 6. 지금 정해야 할 것 (1단계 마감 11/24)
- **등급 기준값** — 초안: 최종 등급 = (YOLO 품질 등급, 지름 크기 등급) 중 더 낮은 쪽.
  지름은 표준규격 무게 구분을 사과를 구로 보고 근사 환산 → 특 ≥ 89mm / 상 83~89mm / 보통 76~83mm / 비상품 < 76mm.
  지금 코드는 YOLO 클래스만 쓰고 `grading.py` 는 쓰이지 않음. 확정되면 `docs/02_roadmap.md` 결정 사항에 기록.
- **인터페이스 최종 합의** — `AppleGrade`, `AmrStatus` 를 3명이 확인.
- **3명 환경 점검** — `bash scripts/check_env.sh` 결과를 단톡에 공유.

### 7. AMR 로봇 (진행 중)
- Lyrical 에는 **TurtleBot4 패키지가 없음**. **TurtleBot3**(`ros-lyrical-turtlebot3-gazebo`), **slam_toolbox**, **Nav2 1.5.2** 는 설치 가능 확인.
- 그래서 🅒 가 **TurtleBot3 Waffle 을 임시 기본 로봇**으로 월드에 넣는 작업을 시작합니다 (`/cmd_vel`, `/odom`, `/scan` 브리지, 시작 위치는 launch 인자).
  다른 로봇을 원하면 🅑 박해원 님이 알려 주세요.
- 로봇이 들어가면 미리 설치해 두기: `sudo apt install -y ros-lyrical-turtlebot3-gazebo`

### 8. 파트별 부탁
- 🅐 조한서: 로드맵 🅐 체크박스 중 끝난 것 체크 / `/apc/apple_grade` 의 `header.stamp` 가 0 이라 판정 시각 넣기
- 🅑 박해원: GitHub 저장소 초대 수락 확인 / `check_env.sh` 결과 공유 / 로봇 종류·시작 위치·맵 방식(SLAM 또는 월드 기준 직접 작성) 의견
- 🅒 장준원: TurtleBot3 월드 추가 → Nav2 용 브리지 확인 → 시연 영상
