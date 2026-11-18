#!/usr/bin/env bash
# =============================================================================
# Smart APC — ROS 2 Jazzy + Gazebo Harmonic + Nav2 설치 스크립트
# 대상: WSL2 Ubuntu 24.04 (Noble)
# 사용법: bash scripts/setup_ros2_jazzy.sh
# =============================================================================
set -euo pipefail

ROS_DISTRO_TARGET="jazzy"
BASHRC="$HOME/.bashrc"
MARK_BEGIN="# >>> smart_apple_apc >>>"
MARK_END="# <<< smart_apple_apc <<<"

info() { echo -e "\033[1;34m[INFO]\033[0m $*"; }
ok()   { echo -e "\033[1;32m[ OK ]\033[0m $*"; }
err()  { echo -e "\033[1;31m[ERR ]\033[0m $*" >&2; }

# ---------------------------------------------------------------------------
# 0. OS 확인
# ---------------------------------------------------------------------------
. /etc/os-release
if [[ "${VERSION_ID:-}" != "24.04" ]]; then
  err "Ubuntu 24.04가 아닙니다 (현재: ${PRETTY_NAME:-unknown}). 팀 공통 환경은 Ubuntu 24.04입니다."
  err "PowerShell에서: wsl --install -d Ubuntu-24.04"
  exit 1
fi
ok "Ubuntu ${VERSION_ID} 확인"

# ---------------------------------------------------------------------------
# 1. 로케일
# ---------------------------------------------------------------------------
info "로케일(UTF-8) 설정"
sudo apt update
sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# ---------------------------------------------------------------------------
# 2. ROS 2 apt 저장소 등록 (공식 ros2-apt-source 방식)
# ---------------------------------------------------------------------------
if ! dpkg -s ros2-apt-source >/dev/null 2>&1; then
  info "ROS 2 apt 저장소 등록"
  sudo apt install -y software-properties-common curl
  sudo add-apt-repository -y universe
  ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
    | grep -F "tag_name" | awk -F'"' '{print $4}')
  if [[ -z "$ROS_APT_SOURCE_VERSION" ]]; then
    err "ros-apt-source 최신 버전을 가져오지 못했습니다. 네트워크(학교망 차단 등)를 확인하세요."
    exit 1
  fi
  curl -L -o /tmp/ros2-apt-source.deb \
    "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${UBUNTU_CODENAME:-${VERSION_CODENAME}}_all.deb"
  sudo dpkg -i /tmp/ros2-apt-source.deb
else
  ok "ROS 2 apt 저장소 이미 등록됨"
fi

# ---------------------------------------------------------------------------
# 3. 패키지 설치
# ---------------------------------------------------------------------------
info "ROS 2 ${ROS_DISTRO_TARGET} + Gazebo Harmonic + Nav2 설치 (시간이 꽤 걸립니다)"
sudo apt update
sudo apt upgrade -y
sudo apt install -y \
  ros-${ROS_DISTRO_TARGET}-desktop \
  ros-dev-tools \
  ros-${ROS_DISTRO_TARGET}-ros-gz \
  ros-${ROS_DISTRO_TARGET}-navigation2 \
  ros-${ROS_DISTRO_TARGET}-nav2-bringup \
  ros-${ROS_DISTRO_TARGET}-cv-bridge \
  ros-${ROS_DISTRO_TARGET}-vision-opencv \
  ros-${ROS_DISTRO_TARGET}-rqt-image-view \
  ros-${ROS_DISTRO_TARGET}-teleop-twist-keyboard \
  python3-colcon-common-extensions \
  python3-venv \
  python3-pip
ok "패키지 설치 완료"

# ---------------------------------------------------------------------------
# 4. rosdep
# ---------------------------------------------------------------------------
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  info "rosdep 초기화"
  sudo rosdep init
fi
rosdep update

# ---------------------------------------------------------------------------
# 5. ~/.bashrc 설정 (중복 방지: 기존 블록 교체)
# ---------------------------------------------------------------------------
echo
echo "팀 파트를 선택하세요 (ROS_DOMAIN_ID 결정):"
echo "  1) 🅐 Vision     → 11"
echo "  2) 🅑 AMR        → 12"
echo "  3) 🅒 Sim/통합   → 13"
read -r -p "번호 입력 [1-3] (기본 3): " PART
case "${PART:-3}" in
  1) DOMAIN_ID=11 ;;
  2) DOMAIN_ID=12 ;;
  *) DOMAIN_ID=13 ;;
esac

if grep -qF "$MARK_BEGIN" "$BASHRC"; then
  sed -i "/$MARK_BEGIN/,/$MARK_END/d" "$BASHRC"
fi

cat >> "$BASHRC" <<EOF
$MARK_BEGIN
source /opt/ros/${ROS_DISTRO_TARGET}/setup.bash
export ROS_DOMAIN_ID=${DOMAIN_ID}
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export RCUTILS_COLORIZED_OUTPUT=1
# colcon 자동완성
[ -f /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash ] && \\
  source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash
# 워크스페이스 단축 명령
alias apc='cd ~/apc_ws && source /opt/ros/${ROS_DISTRO_TARGET}/setup.bash && [ -f .venv/bin/activate ] && source .venv/bin/activate; [ -f install/setup.bash ] && source install/setup.bash'
alias apcb='cd ~/apc_ws && python -m colcon build --symlink-install && source install/setup.bash'
# Gazebo 화면이 검게 나오면 아래 주석 해제
# export LIBGL_ALWAYS_SOFTWARE=1
$MARK_END
EOF

ok "~/.bashrc 설정 완료 (ROS_DOMAIN_ID=${DOMAIN_ID})"
echo
ok "설치 끝! 새 터미널을 열거나 'source ~/.bashrc' 실행 후 아래로 확인하세요:"
echo "    ros2 run demo_nodes_cpp talker"
echo "    gz sim shapes.sdf"
