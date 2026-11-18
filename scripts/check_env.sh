#!/usr/bin/env bash
# =============================================================================
# Smart APC — 개발 환경 점검
# 사용법: bash scripts/check_env.sh   → 결과를 그대로 복사해 팀 채팅/Issue에 공유
# =============================================================================
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0; FAIL=0

check() {  # check "설명" "명령"
  local desc="$1"; shift
  local out
  if out=$(eval "$@" 2>/dev/null) && [[ -n "$out" ]]; then
    printf "✅ %-26s %s\n" "$desc" "$(echo "$out" | head -1)"; PASS=$((PASS+1))
  else
    printf "❌ %-26s %s\n" "$desc" "(확인 필요)"; FAIL=$((FAIL+1))
  fi
}

echo "================ Smart APC 환경 점검 ================"
check "WSL2"                 "uname -r | grep -i microsoft"
check "Ubuntu 26.04"         ". /etc/os-release && [[ \$VERSION_ID == 26.04 ]] && echo \$PRETTY_NAME"
check "ROS_DISTRO=lyrical"   "[[ \${ROS_DISTRO:-} == lyrical ]] && echo lyrical"
check "ros2 CLI"             "command -v ros2"
check "Gazebo Jetty"         "gz sim --versions 2>/dev/null | grep -E '^10\\.'"
check "ros_gz_sim"           "ros2 pkg prefix ros_gz_sim"
check "Nav2 bringup"         "ros2 pkg prefix nav2_bringup"
check "cv_bridge"            "ros2 pkg prefix cv_bridge"
check "colcon"               "command -v colcon"
check "rosdep"               "command -v rosdep"
check "Python 3.14"          "python3 --version | grep '3.14'"
check "ROS_DOMAIN_ID"        "[[ -n \${ROS_DOMAIN_ID:-} ]] && echo \$ROS_DOMAIN_ID"
check "저장소 위치(~ 아래)"   "[[ '$REPO_ROOT' != /mnt/* ]] && echo '$REPO_ROOT'"
check "git user.name"        "git config user.name"
check "git user.email"       "git config user.email"
check ".venv 존재"           "[[ -f '$REPO_ROOT/.venv/bin/activate' ]] && echo '.venv OK'"
check "numpy 2.x (venv)"     "'$REPO_ROOT/.venv/bin/python' -c 'import numpy as n; assert int(n.__version__.split(\".\")[0])>=2; print(n.__version__)'"
check "ultralytics (venv)"   "'$REPO_ROOT/.venv/bin/python' -c 'import ultralytics as u; print(u.__version__)'"
check "WSLg 디스플레이"       "[[ -n \${DISPLAY:-}\${WAYLAND_DISPLAY:-} ]] && echo \${DISPLAY:-\$WAYLAND_DISPLAY}"
check "GPU 렌더링(llvmpipe 아님)" "glxinfo -B 2>/dev/null | grep -i 'renderer string' | grep -vi llvmpipe | sed 's/.*: //'"

if command -v nvidia-smi >/dev/null 2>&1; then
  printf "ℹ️  %-26s %s\n" "GPU" "$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
else
  printf "ℹ️  %-26s %s\n" "GPU" "없음 (CPU로 진행, 학습은 Colab 권장)"
fi
echo "-----------------------------------------------------"
echo "결과: ✅ ${PASS}  /  ❌ ${FAIL}"
[[ $FAIL -eq 0 ]] && echo "🎉 환경 구축 완료!" || echo "❌ 항목은 docs/00_environment_setup.md '자주 나는 문제' 참고"
