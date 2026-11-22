#!/usr/bin/env bash
# =============================================================================
# Smart APC 전체 실행 스크립트 — 환경 설정부터 launch 까지 한 번에
#
# 사용법 (저장소 루트에서):
#   bash scripts/run_apc.sh                     # 기본 월드 + 실제 YOLO 판정 + 바로 키보드로 로봇 조종
#   bash scripts/run_apc.sh --no-teleop         # 키보드 조종 없이 launch 로그를 이 터미널에 출력
#   bash scripts/run_apc.sh --preview           # 창고 배경 월드 (시연용, 더 무거움)
#   bash scripts/run_apc.sh --mock-vision       # YOLO 없이 무작위 등급 (모델 파일 없을 때)
#   bash scripts/run_apc.sh --build             # 실행 전에 colcon build 먼저
#   bash scripts/run_apc.sh --headless          # Gazebo 창 없이 (카메라는 동작)
#   bash scripts/run_apc.sh --sphere            # 사과를 단색 구로 (기본은 ycb 실제 사과 모양)
#   bash scripts/run_apc.sh --preview --build   # 옵션은 여러 개 같이 사용 가능
#   bash scripts/run_apc.sh -- spawn_apples:=false  # -- 뒤는 launch 인자로 그대로 전달
#
# 키보드 조종 (기본): 시뮬이 켜지면 이 터미널에서 바로 로봇을 움직일 수 있음
#   w/↑ 앞  s/↓ 뒤  a/← 왼쪽  d/→ 오른쪽  (누르고 있는 동안만)  space 정지  f 시점 따라가기(풀기: Gazebo 창에서 Esc)
#   q 또는 Ctrl+C → 조종과 시뮬 모두 종료.  launch 로그는 log/run_apc/ 에 저장
#
# 하는 일:
#   1. ROS 2 Lyrical, .venv, install/setup.bash 를 source
#   2. WSL 이면 Gazebo GPU 렌더링 환경변수 설정 (없으면 카메라 영상이 검게 나옴)
#   3. 이전 실행에서 남은 Gazebo 프로세스가 있으면 경고
#   4. 비전 모델(apple_grader.pt)이 없으면 자동으로 --mock-vision 으로 전환
#   5. ros2 launch apc_bringup apc_all.launch.py 실행
#      (기본: 백그라운드로 띄우고 이 터미널은 키보드 조종 / --no-teleop: 이 터미널에서 실행)
#
# 판정 결과 보기 (새 터미널):
#   source /opt/ros/lyrical/setup.bash && source ~/apc_ws/install/setup.bash
#   ros2 topic echo /apc/apple_grade
# 종료: Ctrl+C  (끝날 때 'Segmentation fault (exit 139)' 는 Gazebo 자체 현상이라 무시)
# =============================================================================
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_PATH="${HOME}/apc_ws/models/apple_grader.pt"   # grader_node 의 model_path 기본값과 같음

usage() {
  sed -n '5,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

# ---------- 옵션 ----------
WORLD="apc_world.sdf"
VISION_MOCK="false"
HEADLESS="false"
APPLE_MODEL="ycb"
DO_BUILD=0
TELEOP=1
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --preview)     WORLD="apc_world_v2_preview.sdf" ;;
    --mock-vision) VISION_MOCK="true" ;;
    --headless)    HEADLESS="true" ;;
    --sphere)      APPLE_MODEL="sphere" ;;
    --build)       DO_BUILD=1 ;;
    --no-teleop)   TELEOP=0 ;;
    -h|--help)     usage 0 ;;
    --)            shift; EXTRA_ARGS=("$@"); break ;;
    *) echo "❌ 모르는 옵션: $1" >&2; usage 1 ;;
  esac
  shift
done

cd "$ROOT"

# ---------- ROS 2 / venv ----------
if [[ ! -f /opt/ros/lyrical/setup.bash ]]; then
  echo "❌ ROS 2 Lyrical 이 없습니다 → bash scripts/setup_ros2_lyrical.sh" >&2
  exit 1
fi
set +u
# shellcheck disable=SC1091
source /opt/ros/lyrical/setup.bash
if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  echo "⚠️  .venv 없음 → 실제 비전에는 bash scripts/setup_python_env.sh 필요" >&2
fi

if [[ "$DO_BUILD" -eq 1 ]]; then
  echo "🔨 빌드 중 (python -m colcon build --symlink-install)..."
  python -m colcon build --symlink-install
fi
if [[ ! -f install/setup.bash ]]; then
  echo "❌ install/setup.bash 없음 → --build 를 붙여 다시 실행하세요" >&2
  exit 1
fi
# shellcheck disable=SC1091
source install/setup.bash

# ---------- WSL GPU 렌더링 (이미 설정돼 있으면 그 값 유지) ----------
if grep -qi microsoft /proc/version 2>/dev/null; then
  export GALLIUM_DRIVER="${GALLIUM_DRIVER:-d3d12}"
  if command -v nvidia-smi >/dev/null 2>&1; then
    export MESA_D3D12_DEFAULT_ADAPTER_NAME="${MESA_D3D12_DEFAULT_ADAPTER_NAME:-NVIDIA}"
  fi
  export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
fi

# ---------- 이전 실행 잔여 프로세스 ----------
if pgrep -f "gz sim|gz-sim-main" >/dev/null 2>&1; then
  echo "⚠️  이전에 실행한 Gazebo 가 아직 살아 있습니다 (속도 저하·토픽 꼬임 원인)." >&2
  echo "    정리하려면: pkill -f gz-sim-main; pkill -f 'gz sim'" >&2
fi

# ---------- 비전 모델 ----------
if [[ "$VISION_MOCK" == "false" && ! -f "$MODEL_PATH" ]]; then
  echo "⚠️  비전 모델이 없습니다: $MODEL_PATH" >&2
  echo "    공유 드라이브 models/apple_grader.pt 를 받아 위 위치에 두세요. 이번엔 --mock-vision 으로 실행합니다." >&2
  VISION_MOCK="true"
fi

# ---------- 실행 ----------
LAUNCH_ARGS=(world:="$WORLD" headless:="$HEADLESS" apple_model:="$APPLE_MODEL"
             vision_mock:="$VISION_MOCK" amr_mock:=true "${EXTRA_ARGS[@]}")
# 로봇을 안 띄우면 조종할 것이 없음
for a in "${EXTRA_ARGS[@]}"; do
  [[ "$a" == "spawn_amr:=false" ]] && TELEOP=0
done
# 키보드 입력을 받을 수 없는 환경(파이프·원격 실행 등)이면 조종 끔
[[ -t 0 ]] || TELEOP=0

echo "🚀 월드=${WORLD}  비전=$([[ $VISION_MOCK == true ]] && echo mock || echo YOLO)  " \
     "AMR=mock  사과=${APPLE_MODEL}  headless=${HEADLESS}"
echo "   판정 결과: 새 터미널에서 ros2 topic echo /apc/apple_grade"

if [[ "$TELEOP" -eq 0 ]]; then
  exec ros2 launch apc_bringup apc_all.launch.py "${LAUNCH_ARGS[@]}"
fi

# ---------- 시뮬은 백그라운드, 이 터미널은 키보드 조종 ----------
LOG_DIR="$ROOT/log/run_apc"          # log/ 는 커밋 제외 폴더
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date +%Y%m%d_%H%M%S).log"
ln -sfn "$LOG_FILE" "$LOG_DIR/latest.log"

# setsid: 새 세션으로 띄워서 이 터미널의 Ctrl+C 가 직접 가지 않게 하고, 종료는 아래 cleanup 이 담당
setsid ros2 launch apc_bringup apc_all.launch.py "${LAUNCH_ARGS[@]}" >"$LOG_FILE" 2>&1 &
LAUNCH_PID=$!

cleanup() {
  trap - EXIT INT TERM
  if kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "⏹  시뮬 종료 중..."
    # 스크립트의 백그라운드 프로세스는 SIGINT 를 무시하므로 SIGTERM 으로 launch 에 종료 요청
    # (ros2 launch 는 SIGTERM 도 Ctrl+C 와 같이 하위 노드·Gazebo 를 차례로 정리함)
    kill -TERM "$LAUNCH_PID" 2>/dev/null || true
    for _ in $(seq 1 30); do                 # 최대 15초 대기
      kill -0 "$LAUNCH_PID" 2>/dev/null || break
      sleep 0.5
    done
    kill -KILL -- "-$LAUNCH_PID" 2>/dev/null || true   # 남은 것 강제 정리
  fi
  echo "   launch 로그: $LOG_FILE"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

echo "   launch 로그: $LOG_FILE  (다른 터미널에서 보기: tail -f $LOG_DIR/latest.log)"
echo "⏳ 시뮬 시작 중... (Gazebo 창이 뜨면 이 터미널을 클릭하고 키를 누르세요)"
sleep 3
if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
  echo "❌ 시뮬이 바로 종료됐습니다. 로그 마지막 부분:" >&2
  tail -n 30 "$LOG_FILE" >&2
  exit 1
fi

set +e
ros2 run apc_simulation amr_teleop
set -e
