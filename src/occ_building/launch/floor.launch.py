import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    building = LaunchConfiguration('building_name')
    floor = LaunchConfiguration('floor')
    params_file = LaunchConfiguration('params_file')

    return LaunchDescription([
        DeclareLaunchArgument(
            'building_name',
            default_value=os.environ.get('BUILDING_NAME', 'hospital')),
        DeclareLaunchArgument('floor', default_value='1'),
        DeclareLaunchArgument(
            'params_file',
            default_value=PathJoinSubstitution(
                [FindPackageShare('occ_building'), 'params', 'hospital.yaml'])),
        Node(
            package='occ_building',
            executable='floor_hardware',
            name='floor_hardware',
            namespace=['/', building, '/floor_', floor],
            parameters=[params_file, {'building_name': building, 'floor': floor}],
            output='screen',
        ),
    ])
