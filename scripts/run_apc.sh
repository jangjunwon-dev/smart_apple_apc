#!/usr/bin/env bash
# =============================================================================
# Smart APC 전체 실행 스크립트 — 환경 설정부터 launch 까지 한 번에
#
# 사용법 (저장소 루트에서):
#   bash scripts/run_apc.sh                     # 기본 월드 + 실제 YOLO 판정 + AMR mock
#   bash scripts/run_apc.sh --preview           # 창고 배경 월드 (시연용, 더 무거움)
#   bash scripts/run_apc.sh --mock-vision       # YOLO 없이 무작위 등급 (모델 파일 없을 때)
#   bash scripts/run_apc.sh --build             # 실행 전에 colcon build 먼저
#   bash scripts/run_apc.sh --headless          # Gazebo 창 없이 (카메라는 동작)
#   bash scripts/run_apc.sh --sphere            # 사과를 단색 구로 (기본은 ycb 실제 사과 모양)
#   bash scripts/run_apc.sh --preview --build   # 옵션은 여러 개 같이 사용 가능
#   bash scripts/run_apc.sh -- spawn_apples:=false  # -- 뒤는 launch 인자로 그대로 전달
#
# 하는 일:
#   1. ROS 2 Lyrical, .venv, install/setup.bash 를 source
#   2. WSL 이면 Gazebo GPU 렌더링 환경변수 설정 (없으면 카메라 영상이 검게 나옴)
#   3. 이전 실행에서 남은 Gazebo 프로세스가 있으면 경고
#   4. 비전 모델(apple_grader.pt)이 없으면 자동으로 --mock-vision 으로 전환
#   5. ros2 launch apc_bringup apc_all.launch.py 실행
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
  sed -n '5,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

# ---------- 옵션 ----------
WORLD="apc_world.sdf"
VISION_MOCK="false"
HEADLESS="false"
APPLE_MODEL="ycb"
DO_BUILD=0
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --preview)     WORLD="apc_world_v2_preview.sdf" ;;
    --mock-vision) VISION_MOCK="true" ;;
    --headless)    HEADLESS="true" ;;
    --sphere)      APPLE_MODEL="sphere" ;;
    --build)       DO_BUILD=1 ;;
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
echo "🚀 월드=${WORLD}  비전=$([[ $VISION_MOCK == true ]] && echo mock || echo YOLO)  " \
     "AMR=mock  사과=${APPLE_MODEL}  headless=${HEADLESS}"
echo "   판정 결과: 새 터미널에서 ros2 topic echo /apc/apple_grade"
exec ros2 launch apc_bringup apc_all.launch.py \
  world:="$WORLD" headless:="$HEADLESS" apple_model:="$APPLE_MODEL" \
  vision_mock:="$VISION_MOCK" amr_mock:=true "${EXTRA_ARGS[@]}"
