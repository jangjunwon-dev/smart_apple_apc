"""전체 실행: Gazebo 월드 + 비전 + AMR.

ros2 launch apc_bringup apc_all.launch.py vision_mock:=false amr_mock:=true
ros2 launch apc_bringup apc_all.launch.py world:=apc_world_v2_preview.sdf headless:=true
ros2 launch apc_bringup apc_all.launch.py apple_model:=sphere   # 단색 구 외형 (기본은 ycb)
ros2 launch apc_bringup apc_all.launch.py amr_x:=1.0 amr_y:=-1.0   # AMR 시작 위치 변경
  - world, headless, spawn_apples, apple_model, spawn_amr, amr_x/amr_y/amr_yaw 는
    apc_simulation/sim.launch.py 로 그대로 넘김
    (기본값도 sim.launch.py 와 같음 → 인자 없이 실행하면 sim.launch.py 단독 실행과 같은 월드·외형)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

from apc_simulation import amr_robot   # AMR 시작 위치 기본값은 여기 한곳에서 관리

# sim.launch.py 로 넘기는 인자: (이름, 기본값, 설명) — 기본값은 sim.launch.py 와 같게 유지
SIM_ARGS = [
    ('world', 'apc_world.sdf', 'worlds/ 안의 월드 파일 이름 또는 절대 경로'),
    ('headless', 'false', 'true 면 GUI 없이 gz sim 서버만 실행'),
    ('spawn_apples', 'true', '사과 주기적 생성/삭제 노드 실행 여부'),
    ('apple_model', 'ycb', '사과 외형: ycb(YCB 3D 스캔 메시) | sphere(단색 구)'),
    ('spawn_amr', 'true', 'AMR 로봇(TurtleBot3 Waffle, 임시) 스폰 + 브리지 실행 여부'),
    ('amr_x', amr_robot.DEFAULT_X, 'AMR 시작 x [m] (월드 좌표)'),
    ('amr_y', amr_robot.DEFAULT_Y, 'AMR 시작 y [m] (월드 좌표)'),
    ('amr_yaw', amr_robot.DEFAULT_YAW, 'AMR 시작 방향 [rad] (0 = +x, zone B 쪽)'),
]


def generate_launch_description():
    sim_launch = os.path.join(
        get_package_share_directory('apc_simulation'), 'launch', 'sim.launch.py')
    zones = os.path.join(get_package_share_directory('apc_amr'), 'config', 'zones.yaml')

    vision_mock = ParameterValue(LaunchConfiguration('vision_mock'), value_type=bool)
    amr_mock = ParameterValue(LaunchConfiguration('amr_mock'), value_type=bool)

    sim_arg_decls = [DeclareLaunchArgument(name, default_value=default, description=desc)
                     for name, default, desc in SIM_ARGS]
    sim_launch_args = {name: LaunchConfiguration(name) for name, _, _ in SIM_ARGS}

    return LaunchDescription([
        DeclareLaunchArgument('vision_mock', default_value='true'),
        DeclareLaunchArgument('amr_mock', default_value='true'),
        *sim_arg_decls,
        IncludeLaunchDescription(PythonLaunchDescriptionSource(sim_launch),
                                 launch_arguments=sim_launch_args.items()),
        Node(package='apc_vision', executable='grader_node', name='grader_node',
             parameters=[{'mock': vision_mock, 'use_sim_time': True}], output='screen'),
        Node(package='apc_amr', executable='task_manager_node', name='task_manager_node',
             parameters=[zones, {'mock': amr_mock, 'use_sim_time': True}], output='screen'),
    ])
