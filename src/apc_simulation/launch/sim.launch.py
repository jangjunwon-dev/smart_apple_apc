"""Gazebo Jetty 에서 apc_world 실행 + 브리지 + 사과 스포너.

ros2 launch apc_simulation sim.launch.py               # 사과 스폰 포함
ros2 launch apc_simulation sim.launch.py spawn_apples:=false
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

WORLD_NAME = 'apc_world'


def generate_launch_description():
    pkg_sim = get_package_share_directory('apc_simulation')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    world = os.path.join(pkg_sim, 'worlds', 'apc_world.sdf')
    spawner_params = os.path.join(pkg_sim, 'config', 'apple_spawner.yaml')

    gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': ['-r ', world]}.items(),
    )

    belt_gz_topic = '/model/conveyor/link/belt/track_cmd_vel'

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
        gz,
        bridge,
        spawner,
    ])
