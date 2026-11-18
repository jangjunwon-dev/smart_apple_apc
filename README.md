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
