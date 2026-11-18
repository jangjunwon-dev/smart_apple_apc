"""Gazebo Jetty 에서 apc_world 실행 + 브리지 + 사과 스포너.

ros2 launch apc_simulation sim.launch.py               # 사과 스폰 포함
ros2 launch apc_simulation sim.launch.py spawn_apples:=false
ros2 launch apc_simulation sim.launch.py world:=apc_world_4lane_test.sdf headless:=true
ros2 launch apc_simulation sim.launch.py world:=apc_world_v2_preview.sdf   # 미리보기 월드
  - world: worlds/ 안의 파일 이름 또는 절대 경로 (기본 apc_world.sdf)
  - headless: true 면 GUI 없이 서버만 실행 (센서 렌더링은 유지)
  - models/ 폴더를 GZ_SIM_RESOURCE_PATH 에 추가 → 월드에서 model://<모델이름> 사용 (오프라인 가능)
  ※ 브리지·스포너는 world 이름 'apc_world' 기준 → 다른 월드도 <world name="apc_world"> 유지
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument,
                            IncludeLaunchDescription, OpaqueFunction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

WORLD_NAME = 'apc_world'


def _gz_sim(context):
    """world/headless 인자로 gz sim 실행 인자를 만든다."""
    pkg_sim = get_package_share_directory('apc_simulation')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    world = LaunchConfiguration('world').perform(context)
    if not os.path.isabs(world):
        world = os.path.join(pkg_sim, 'worlds', world)
    headless = LaunchConfiguration('headless').perform(context).lower() in ('true', '1')
    gz_args = '-r ' + ('-s --headless-rendering ' if headless else '') + world
    return [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': gz_args}.items(),
    )]


def generate_launch_description():
    pkg_sim = get_package_share_directory('apc_simulation')
    spawner_params = os.path.join(pkg_sim, 'config', 'apple_spawner.yaml')

    belt_gz_topic = '/model/conveyor/link/belt/track_cmd_vel'

    # 로컬 모델(model://...) 검색 경로. gz sim 실행(OpaqueFunction)보다 먼저 와야 함
    model_path = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(pkg_sim, 'models'))

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='apc_gz_bridge',
        arguments=[
            '/apc/camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            # 컨베이어 벨트 속도 (ROS → Gazebo TrackController)
            f'{belt_gz_topic}@std_msgs/msg/Float64]gz.msgs.Double',
            # 컨베이어 끝 논리 카메라 (Gazebo → ROS): 떨어진 사과 이름 → 삭제 판정
            # (dynamic_pose/info 는 TFMessage 변환 시 모델 이름이 빠져서 사용 불가)
            '/apc/sim/apple_sink@ros_gz_interfaces/msg/LogicalCameraImage'
            '[gz.msgs.LogicalCameraImage',
            # 엔티티 생성/삭제 서비스 (UserCommands 시스템 제공)
            f'/world/{WORLD_NAME}/create@ros_gz_interfaces/srv/SpawnEntity',
            f'/world/{WORLD_NAME}/remove@ros_gz_interfaces/srv/DeleteEntity',
        ],
        remappings=[
            (belt_gz_topic, '/apc/conveyor/cmd_vel'),
        ],
        output='screen',
    )

    spawner = Node(
        package='apc_simulation',
        executable='apple_spawner_node',
        name='apple_spawner',
        parameters=[spawner_params, {'use_sim_time': True, 'world_name': WORLD_NAME}],
        condition=IfCondition(LaunchConfiguration('spawn_apples')),
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('spawn_apples', default_value='true',
                              description='사과 주기적 생성/삭제 노드 실행 여부'),
        DeclareLaunchArgument('world', default_value='apc_world.sdf',
                              description='worlds/ 안의 월드 파일 이름 또는 절대 경로'),
        DeclareLaunchArgument('headless', default_value='false',
                              description='true 면 GUI 없이 gz sim 서버만 실행'),
        model_path,
        OpaqueFunction(function=_gz_sim),
        bridge,
        spawner,
    ])
