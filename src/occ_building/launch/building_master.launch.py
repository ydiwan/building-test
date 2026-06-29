import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    building = LaunchConfiguration('building_name')
    floors = LaunchConfiguration('floors')

    return LaunchDescription([
        DeclareLaunchArgument(
            'building_name',
            default_value=os.environ.get('BUILDING_NAME', 'hospital')),
        DeclareLaunchArgument('floors', default_value='[1, 2, 3, 4]'),
        Node(
            package='occ_building',
            executable='building_master',
            name='building_master',
            parameters=[{'building_name': building, 'floors': floors}],
            output='screen',
        ),
    ])
