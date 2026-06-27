"""Launch the building-master aggregator on the hospital-master Pi.

Subscribes to all floors' state topics and publishes CityIngest telemetry. The
floor list / building name come from args (default building from BUILDING_NAME).
"""
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
