import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('influx_url', default_value=os.environ.get('INFLUXDB_URL', 'http://localhost:8086')),
        DeclareLaunchArgument('influx_token', default_value=os.environ.get('INFLUXDB_TOKEN', '')),
        DeclareLaunchArgument('influx_org', default_value=os.environ.get('INFLUXDB_ORG', 'occ')),
        DeclareLaunchArgument('influx_bucket', default_value=os.environ.get('INFLUXDB_BUCKET', 'occ')),
        Node(
            package='occ_central_hub',
            executable='city_sink',
            name='city_sink',
            output='screen',
            parameters=[{
                'influx_url': LaunchConfiguration('influx_url'),
                'influx_token': LaunchConfiguration('influx_token'),
                'influx_org': LaunchConfiguration('influx_org'),
                'influx_bucket': LaunchConfiguration('influx_bucket'),
            }],
        ),
    ])
