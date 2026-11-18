# 00. 공통 개발 환경 구축 가이드

> **목표:** 팀원 3명이 **완전히 같은 버전**으로 개발해서 "내 컴퓨터에선 되는데?" 문제를 없앤다.
> 소요 시간: 약 40~60분 (인터넷 속도에 따라 다름)

## ✅ 팀 공통 버전 (변경 금지)

| 구성 요소 | 버전 | 비고 |
|---|---|---|
| OS (호스트) | Windows 10 22H2+ / **Windows 11 권장** | WSLg(GUI) 필요 |
| WSL | **WSL2** | `wsl --version`으로 확인 |
| 리눅스 | **Ubuntu 24.04 LTS (Noble)** | 22.04, 26.04 아님 주의 |
| ROS 2 | **Jazzy Jalisco** | 24.04용 Tier 1 LTS |
| Gazebo | **Harmonic** | `ros-jazzy-ros-gz`로 함께 설치 |
| Python | **3.12** (Ubuntu 24.04 기본) | 별도 설치 불필요 |
| 내비게이션 | Nav2 (Jazzy) | |
| 편집기 | VS Code + WSL 확장 | 권장 |

> **왜 Jazzy인가?** 2026년 5월에 나온 Lyrical(26.04용)도 LTS지만, 아직 일부 패키지·튜토리얼이 부족합니다. 한 학기 프로젝트에서는 자료가 가장 많은 **Ubuntu 24.04 + Jazzy + Harmonic** 조합이 가장 안전합니다.

---

## STEP 1. WSL2 + Ubuntu 24.04 설치 (Windows)

**PowerShell을 관리자 권한으로** 열고:

```powershell
wsl --update
wsl --install -d Ubuntu-24.04
```

- 재부팅 후 Ubuntu 창이 뜨면 **리눅스 사용자 이름/비밀번호** 설정
- 확인:

```powershell
wsl -l -v
#  NAME            STATE    VERSION
#  Ubuntu-24.04    Running  2      ← VERSION이 2여야 함
```

> 이미 다른 Ubuntu(22.04 등)가 있어도 괜찮습니다. 24.04를 **추가로** 설치하고, 이 프로젝트는 24.04에서만 작업하세요.
> 기본 배포판 지정: `wsl --set-default Ubuntu-24.04`

### (권장) WSL 메모리 설정
Gazebo는 메모리를 많이 씁니다. Windows에서 `%UserProfile%\.wslconfig` 파일을 만들고:

```ini
[wsl2]
memory=8GB        # PC RAM의 절반 정도
processors=4
swap=4GB
```

저장 후 PowerShell에서 `wsl --shutdown` → Ubuntu 다시 실행.

### (NVIDIA GPU가 있는 경우)
- **Windows 쪽**에만 최신 NVIDIA 드라이버 설치 (WSL 안에 드라이버 설치 ❌)
- Ubuntu에서 `nvidia-smi`가 나오면 성공 → YOLO 학습에 GPU 사용 가능

---

## STEP 2. 기본 도구 + Git 설정 (Ubuntu)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl build-essential

git config --global user.name  "본인이름"
git config --global user.email "GitHub에 등록한 이메일"
git config --global init.defaultBranch main
git config --global pull.rebase true
git config --global core.autocrlf input     # 윈도우 줄바꿈 문제 방지
```

### GitHub 로그인 (gh CLI 권장)
```bash
sudo apt install -y gh
gh auth login      # GitHub.com → HTTPS → 브라우저 로그인
```

---

## STEP 3. 저장소 클론

> ⚠️ **반드시 리눅스 홈(`~`) 안에 클론**하세요. `/mnt/c/...`(윈도우 폴더)에 두면 빌드가 10배 이상 느려지고 권한 오류가 납니다.

```bash
git clone https://github.com/jangjunwon-dev/smart_apple_apc.git ~/apc_ws
cd ~/apc_ws
```

---

## STEP 4. ROS 2 Jazzy + Gazebo Harmonic + Nav2 설치

스크립트 한 번이면 됩니다 (내용은 [scripts/setup_ros2_jazzy.sh](../scripts/setup_ros2_jazzy.sh) 참고):

```bash
bash scripts/setup_ros2_jazzy.sh
```

스크립트가 하는 일:
1. 로케일(UTF-8) 설정
2. ROS 2 apt 저장소 등록 (`ros2-apt-source` 패키지 방식, 공식 문서 기준)
3. `ros-jazzy-desktop`, `ros-dev-tools`, `ros-jazzy-ros-gz`(Gazebo Harmonic 포함), `ros-jazzy-navigation2`, `ros-jazzy-nav2-bringup`, `ros-jazzy-cv-bridge` 등 설치
4. `rosdep` 초기화
5. `~/.bashrc`에 ROS 환경 + 팀 공통 환경변수 추가

설치 후 **새 터미널**을 열고 확인:

```bash
ros2 --help              # 명령어 목록이 나오면 OK
gz sim shapes.sdf        # Gazebo 창에 도형이 뜨면 OK (WSLg)
```

### 동작 테스트 (터미널 2개)
```bash
# 터미널 1
ros2 run demo_nodes_cpp talker
# 터미널 2
ros2 run demo_nodes_py listener   # "I heard: [Hello World: N]" 출력되면 성공
```

---

## STEP 5. 팀원별 ROS_DOMAIN_ID 설정

같은 네트워크(학교 와이파이 등)에서 서로의 토픽이 섞이지 않도록 **각자 다른 번호**를 씁니다.
`setup_ros2_jazzy.sh`가 물어볼 때 입력하거나, `~/.bashrc`에서 직접 수정:

| 파트 | ROS_DOMAIN_ID |
|---|---|
| 🅐 Vision (조한서) | `11` |
| 🅑 AMR (박해원) | `12` |
| 🅒 Sim/통합 (장준원) | `13` |

```bash
export ROS_DOMAIN_ID=11
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST   # 내 PC 안에서만 통신 (Jazzy 방식)
```

> 통합 테스트할 때만 같은 번호로 맞추고 `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET`으로 바꿉니다.

---

## STEP 6. Python 가상환경 (비전 파트 필수, 나머지 권장)

Ubuntu 24.04는 시스템 Python에 `pip install`을 막습니다(PEP 668). 그래서 **ROS 패키지는 그대로 보이면서** 추가 패키지만 따로 까는 가상환경을 씁니다.

```bash
cd ~/apc_ws
bash scripts/setup_python_env.sh
```

스크립트가 하는 일:
```bash
python3 -m venv --system-site-packages .venv   # rclpy 등 ROS 패키지 접근 유지
touch .venv/COLCON_IGNORE                       # colcon이 venv를 패키지로 착각하지 않게
source .venv/bin/activate
pip install -r requirements.txt                 # ultralytics, numpy<2 등
```

> ⚠️ **numpy는 2.x 금지.** ROS Jazzy의 `cv_bridge`가 numpy 1.26 기준으로 빌드돼 있어서 numpy 2가 깔리면 이미지 변환에서 오류가 납니다. `requirements.txt`에 `numpy<2`로 고정돼 있습니다.

---

## STEP 7. 빌드 & 실행

```bash
cd ~/apc_ws
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
rosdep install --from-paths src --ignore-src -y     # 의존성 자동 설치
python -m colcon build --symlink-install            # venv 파이썬으로 빌드
source install/setup.bash

ros2 launch apc_bringup mock.launch.py              # Gazebo 없이 토픽 흐름 확인
ros2 topic echo /apc/apple_grade                    # 다른 터미널에서 확인
```

> `python -m colcon` 으로 실행해야 venv에 깔린 패키지(ultralytics 등)를 노드가 찾을 수 있습니다.

---

## STEP 8. 최종 점검

```bash
bash scripts/check_env.sh
```

모든 항목이 ✅ 이면 끝. ❌ 가 있으면 출력 그대로 팀 채팅방(또는 GitHub Issue)에 올려주세요.

---

## STEP 9. VS Code 연결 (권장)

1. Windows에 VS Code 설치 → 확장 **"WSL"**, **"Python"**, **"ROS"**(Microsoft 또는 Ranch Hand Robotics) 설치
2. Ubuntu 터미널에서:
   ```bash
   cd ~/apc_ws && code .
   ```
3. 왼쪽 아래에 `WSL: Ubuntu-24.04`가 뜨면 성공

---

## 🧯 자주 나는 문제

| 증상 | 원인/해결 |
|---|---|
| `gz sim` 창이 검은색 / 바로 꺼짐 | GPU 가속 문제. `export LIBGL_ALWAYS_SOFTWARE=1` 후 재실행 (느리지만 동작). NVIDIA라면 `export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` 시도 |
| GUI 창이 아예 안 뜸 | PowerShell에서 `wsl --update` → `wsl --shutdown` 후 재시작 (WSLg 업데이트) |
| `ros2: command not found` | 새 터미널을 안 열었음 → `source ~/.bashrc` |
| `colcon build`가 매우 느림 | 저장소가 `/mnt/c/` 아래에 있음 → `~/apc_ws`로 다시 클론 |
| `ModuleNotFoundError: ultralytics` (노드 실행 시) | venv 활성화 안 하고 빌드함 → `source .venv/bin/activate` 후 `python -m colcon build` 다시 |
| `AttributeError: _ARRAY_API not found` | numpy 2 설치됨 → `pip install "numpy<2"` |
| 남의 토픽이 보임 | ROS_DOMAIN_ID 겹침 → STEP 5 확인 |
| `rosdep update` 실패 | 학교망 차단 가능성 → 핫스팟으로 재시도 |
| Gazebo가 너무 느림 | `.wslconfig` 메모리 늘리기, 다른 프로그램 종료, `gz sim -s`(서버만) + 필요시 GUI |
