#!/usr/bin/env bash
# =============================================================================
# Smart APC — Python 가상환경 생성 (ROS 패키지 접근 유지)
# 사용법: cd ~/apc_ws && bash scripts/setup_python_env.sh
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -d .venv ]]; then
  echo "[INFO] .venv 생성 (--system-site-packages: rclpy, cv_bridge 사용 가능)"
  python3 -m venv --system-site-packages .venv
fi
touch .venv/COLCON_IGNORE

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip wheel
pip install -r requirements.txt

echo
python - <<'PY'
import numpy, cv2
print(f"[ OK ] numpy {numpy.__version__}  /  opencv {cv2.__version__}")
assert int(numpy.__version__.split('.')[0]) >= 2, "Lyrical cv_bridge 는 numpy 2.x 기준입니다 (numpy<2 설치 금지)"
try:
    import ultralytics
    print(f"[ OK ] ultralytics {ultralytics.__version__}")
except ImportError:
    print("[WARN] ultralytics 미설치")
try:
    import torch
    print(f"[ OK ] torch {torch.__version__}  CUDA 사용 가능: {torch.cuda.is_available()}")
except ImportError:
    pass
PY
echo "[ OK ] 완료. 앞으로 작업 전: source ~/apc_ws/.venv/bin/activate  (또는 'apc' 단축 명령)"
