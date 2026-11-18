"""Gazebo 없이 비전·AMR 노드를 mock 모드로 실행 (토픽 흐름 확인용)."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    zones = os.path.join(get_package_share_directory('apc_amr'), 'config', 'zones.yaml')
    return LaunchDescription([
        Node(package='apc_vision', executable='grader_node', name='grader_node',
             parameters=[{'mock': True}], output='screen'),
        Node(package='apc_amr', executable='task_manager_node', name='task_manager_node',
             parameters=[zones, {'mock': True}], output='screen'),
    ])
