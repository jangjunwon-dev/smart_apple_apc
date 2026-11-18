# AGENTS.md — AI 코딩 도구 공통 지침

> 이 파일은 Codex, Claude Code, Cursor, Gemini CLI, Copilot 등 **모든 AI 도구가 먼저 읽는 프로젝트 컨텍스트**입니다.
> 팀원 3명이 각자 다른 AI를 써도 같은 규칙으로 작업하도록 하는 것이 목적입니다.
> 내용을 바꾸면 PR로 팀에 공유하세요.

## 1. 프로젝트 한 줄 요약
농촌 인력난 해소를 위한 **스마트 APC 사과 선별·물류 자동화 시스템**.
카메라 영상으로 사과 등급(특/상/보통/비상품)을 판정하고, AMR이 등급별 적재 구역으로 운반하는 과정을 **ROS 2 Lyrical + Gazebo Jetty** 시뮬레이션으로 구현하는 3인 학부 팀 프로젝트(전주대학교 인공지능학과).

## 1-1. 팀 구성
| 파트 | 담당 | 패키지 |
|---|---|---|
| 🅐 사과 이미지 분석 (Vision) | 조한서 | `apc_vision` |
| 🅑 AMR 주행·물류 | 박해원 | `apc_amr` |
| 🅒 시뮬레이션·통합 + 저장소 관리 | 장준원 | `apc_simulation`, `apc_bringup` |

## 2. 고정된 환경 (임의로 바꾸지 말 것)
- WSL2 **Ubuntu 26.04 LTS**, **ROS 2 Lyrical Luth**, **Gazebo Jetty** (`ros_gz`), Nav2, Python 3.14
- 비전 패키지는 `.venv`(`--system-site-packages`)에 설치, **numpy 2.x**(시스템 `python3-numpy`와 맞춤 — `numpy<2` 설치 금지)
- 다른 ROS 배포판(Humble, Jazzy 등)이나 Gazebo Classic(`gazebo_ros`) 코드/명령을 제안하지 말 것. Gazebo는 `gz sim`, `ros_gz_sim`, `ros_gz_bridge` 만 사용.

## 3. 저장소 구조
저장소 루트 = colcon 워크스페이스 루트(`~/apc_ws`).
```
src/apc_interfaces  공통 msg (AppleGrade, AmrStatus)    ← 3명 합의 없이 수정 금지
src/apc_vision      🅐 사과 등급 판정 노드 (ament_python)
src/apc_amr         🅑 등급→구역 배정, Nav2 운반 (ament_python)
src/apc_simulation  🅒 Gazebo 월드/launch (ament_cmake)
src/apc_bringup     🅒 전체 실행 launch (ament_cmake)
docs/               환경·Git·로드맵·아키텍처·AI 가이드
scripts/            설치·점검 스크립트
data/               sample/(커밋) raw/·processed/(공유 드라이브) — 규칙은 data/README.md
models/             가중치(공유 드라이브) — 기록은 models/README.md
```

## 4. 빌드 / 실행 / 테스트 명령
```bash
cd ~/apc_ws
source /opt/ros/lyrical/setup.bash && source .venv/bin/activate
rosdep install --from-paths src --ignore-src -y
python -m colcon build --symlink-install        # 반드시 python -m colcon (venv 패키지 인식)
source install/setup.bash
python -m colcon test --packages-select apc_vision apc_amr && colcon test-result --verbose
ros2 launch apc_bringup mock.launch.py         # Gazebo 없이 토픽 흐름 확인
ros2 launch apc_bringup apc_all.launch.py      # Gazebo 포함 전체
```
코드를 수정했다면 **최소한 빌드가 통과하는지** 확인한 뒤 완료라고 보고할 것.

## 5. 인터페이스 규약 (요약 — 상세: `docs/03_architecture.md`)
| 토픽 | 타입 | 발행 → 구독 |
|---|---|---|
| `/apc/camera/image_raw` | `sensor_msgs/Image` | Gazebo → vision |
| `/apc/apple_grade` | `apc_interfaces/AppleGrade` | vision → amr |
| `/apc/amr_status` | `apc_interfaces/AmrStatus` | amr → 모니터링 |
| `/navigate_to_pose` (action) | `nav2_msgs/NavigateToPose` | amr → Nav2 |

- 프로젝트 토픽은 `/apc/` 접두어. 등급 상수: SPECIAL=0, GOOD=1, NORMAL=2, REJECT=3.
- 모든 노드는 `mock` 파라미터를 유지해야 함 (다른 파트 없이 개발·테스트 가능하게).
- 메시지 필드/토픽 이름 변경이 필요하면 **코드를 바꾸지 말고** 변경 제안 내용을 정리해 사용자에게 알릴 것 (팀 합의 사항).

## 6. 코딩 규칙
- Python: PEP 8, 최대 줄 길이 99, 타입 힌트 권장, rclpy 노드는 클래스 기반
- 주석·로그·문서는 **한국어**, 식별자(변수·함수·토픽)는 영어 snake_case
- ROS 의존 없는 로직(예: `apc_vision/grading.py`)은 별도 모듈로 분리하고 pytest 작성
- 새 의존성은 `package.xml`(ROS) 또는 `requirements.txt`(pip)에 반드시 추가
- 하드코딩 대신 ROS 파라미터 / `config/*.yaml` 사용
- 좌표계 REP-105 (`map`, `odom`, `base_link`, `camera_link`)

## 7. Git 규칙 (상세: `docs/01_git_workflow.md`)
- `main` 직접 push 금지, 브랜치 `feat/<파트>-<내용>` → PR → 리뷰 1명 → Squash merge
- 커밋: `feat(vision): 요약` 형식 (종류: feat/fix/docs/refactor/test/chore)
- `build/ install/ log/ .venv/ data/ models/*.pt` 는 커밋 금지
- AI는 사용자가 명시적으로 요청하지 않으면 commit/push 하지 말 것

## 8. AI가 작업 전에 확인할 것
1. `docs/02_roadmap.md` — **현재 단계와 내 파트의 다음 할 일**
2. 사용자가 누구인지(조한서=🅐, 박해원=🅑, 장준원=🅒) — 모르면 먼저 물어볼 것
3. 담당 파트 밖의 패키지를 수정해야 하면 수정 전에 사용자에게 알릴 것 (해당 파트 담당자 리뷰 필요)
4. 작업을 마치면 로드맵 체크박스 갱신이 필요한지 사용자에게 제안

## 9. 답변 스타일
- 사용자는 ROS 2/Gazebo 입문 단계의 학부생 → 명령어는 복사해서 바로 실행 가능하게, 왜 필요한지 한 줄 설명
- 한국어 존댓말로 답변
