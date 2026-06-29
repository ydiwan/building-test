import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'occ_building'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'params'), glob('params/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ydiwan',
    maintainer_email='youssefdiwan08@gmail.com',
    description='',
    license='',
    entry_points={
        'console_scripts': [
            'floor_hardware = occ_building.floor_hardware:main',
            'building_master = occ_building.building_master:main',
        ],
    },
)
