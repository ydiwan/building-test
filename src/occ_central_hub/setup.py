import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'occ_central_hub'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ydiwan',
    maintainer_email='youssefdiwan08@gmail.com',
    description='',
    license='',
    entry_points={
        'console_scripts': [
            'city_sink = occ_central_hub.city_sink:main',
        ],
    },
)
