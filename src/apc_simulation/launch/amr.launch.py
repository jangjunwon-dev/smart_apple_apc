"""AMR 로봇 스폰 + 브리지 + robot_state_publisher (sim.launch.py 가 spawn_amr:=true 일 때 include).

로봇 종류·모델 파일·이름은 apc_simulation/amr_robot.py, 토픽 브리지는 config/amr_bridge.yaml 에 있음.
단독 실행(sim.launch.py spawn_amr:=false 로 월드가 이미 떠 있을 때):
  ros2 launch apc_simulation amr.launch.py amr_x:=1.5 amr_y:=0.0 amr_yaw:=0.0
  - amr_x, amr_y [m], amr_yaw [rad]: 월드(map) 좌표계 시작 위치
  ※ 메시 경로(GZ_SIM_RESOURCE_PATH)는 gz sim 시작 전에 필요 → sim.launch.py 가 미리 추가함
토픽: /cmd_vel(TwistStamped) → 로봇, /odom, /scan, /tf(odom→base_footprint), /joint_states
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from apc_simulation import amr_robot

WORLD_NAME = 'apc_world'


def generate_launch_description():
    pkg_sim = get_package_share_directory('apc_simulation')

    with open(amr_robot.amr_urdf_path(), encoding='utf-8') as f:
        robot_description = f.read()

    pose_args = [
        DeclareLaunchArgument('amr_x', default_value=amr_robot.DEFAULT_X,
                              description='AMR 시작 x [m] (월드 좌표)'),
        DeclareLaunchArgument('amr_y', default_value=amr_robot.DEFAULT_Y,
                              description='AMR 시작 y [m] (월드 좌표)'),
        DeclareLaunchArgument('amr_yaw', default_value=amr_robot.DEFAULT_YAW,
                              description='AMR 시작 방향 [rad] (0 = +x, zone B 쪽)'),
    ]

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        name='amr_spawner',
        arguments=[
            '-world', WORLD_NAME,
            '-name', amr_robot.AMR_NAME,
            '-file', amr_robot.amr_sdf_path(),
            '-x', LaunchConfiguration('amr_x'),
            '-y', LaunchConfiguration('amr_y'),
            '-z', str(amr_robot.SPAWN_Z),
            '-Y', LaunchConfiguration('amr_yaw'),
        ],
        output='screen',
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='amr_gz_bridge',
        parameters=[{'config_file': os.path.join(pkg_sim, 'config', 'amr_bridge.yaml'),
                     'use_sim_time': True}],
        output='screen',
    )

    # base_footprint → base_link → 센서 프레임 (고정 관절은 /tf_static, 바퀴는 /joint_states 로 /tf)
    state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
        output='screen',
    )

    return LaunchDescription([*pose_args, spawn, bridge, state_publisher])
