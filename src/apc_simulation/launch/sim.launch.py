"""Gazebo Harmonic 에서 apc_world 실행 + 카메라 토픽 브리지."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg_sim = get_package_share_directory('apc_simulation')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    world = os.path.join(pkg_sim, 'worlds', 'apc_world.sdf')

    gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': ['-r ', world]}.items(),
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='apc_gz_bridge',
        arguments=[
            '/apc/camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
        ],
        output='screen',
    )

    return LaunchDescription([
        gz,
        bridge,
    ])
