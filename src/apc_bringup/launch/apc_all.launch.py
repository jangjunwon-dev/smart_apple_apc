"""전체 실행: Gazebo 월드 + 비전 + AMR.

ros2 launch apc_bringup apc_all.launch.py vision_mock:=false amr_mock:=true
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    sim_launch = os.path.join(
        get_package_share_directory('apc_simulation'), 'launch', 'sim.launch.py')
    zones = os.path.join(get_package_share_directory('apc_amr'), 'config', 'zones.yaml')

    vision_mock = ParameterValue(LaunchConfiguration('vision_mock'), value_type=bool)
    amr_mock = ParameterValue(LaunchConfiguration('amr_mock'), value_type=bool)

    return LaunchDescription([
        DeclareLaunchArgument('vision_mock', default_value='true'),
        DeclareLaunchArgument('amr_mock', default_value='true'),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(sim_launch)),
        Node(package='apc_vision', executable='grader_node', name='grader_node',
             parameters=[{'mock': vision_mock, 'use_sim_time': True}], output='screen'),
        Node(package='apc_amr', executable='task_manager_node', name='task_manager_node',
             parameters=[zones, {'mock': amr_mock, 'use_sim_time': True}], output='screen'),
    ])
