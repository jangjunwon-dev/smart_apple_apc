"""AMR 로봇 설정 (sim.launch.py, amr.launch.py 가 공통으로 사용).

현재 로봇: TurtleBot3 Waffle (임시 기본값 — Lyrical 에 TurtleBot4 패키지 없음, 🅑 박해원 확인 필요)
로봇을 바꿀 때는 이 파일의 상수와 config/amr_bridge.yaml 만 고치면 된다.
"""
import os

from ament_index_python.packages import get_package_share_directory

AMR_PKG = 'turtlebot3_gazebo'
AMR_SDF = os.path.join('models', 'turtlebot3_waffle', 'model.sdf')   # gz 스폰용 (플러그인 포함)
AMR_URDF = os.path.join('urdf', 'turtlebot3_waffle.urdf')            # robot_state_publisher 용
AMR_MODEL_DIR = 'models'        # SDF 안 model://turtlebot3_common 메시 검색 경로
AMR_NAME = 'amr_1'              # gz 모델 이름 = apc_amr zones.yaml 의 robot_id
SPAWN_Z = 0.01                  # 바닥에 박히지 않게 살짝 띄워서 스폰

# 시작 위치 기본값 (월드 = map 좌표, m / rad)
# (1.5, 0, 0): 컨베이어 끝(x -0.5)과 zone A/B/C 칸막이(x 3.6) 사이 중앙, zone B 를 바라봄
DEFAULT_X = '1.5'
DEFAULT_Y = '0.0'
DEFAULT_YAW = '0.0'


def amr_share() -> str:
    """로봇 패키지 share 경로."""
    return get_package_share_directory(AMR_PKG)


def amr_sdf_path() -> str:
    return os.path.join(amr_share(), AMR_SDF)


def amr_urdf_path() -> str:
    return os.path.join(amr_share(), AMR_URDF)


def amr_model_path() -> str:
    """GZ_SIM_RESOURCE_PATH 에 넣을 경로 (gz sim 시작 전에 설정해야 함)."""
    return os.path.join(amr_share(), AMR_MODEL_DIR)
