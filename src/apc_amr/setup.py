from glob import glob

from setuptools import find_packages, setup

package_name = 'apc_amr'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='smart_apple_apc team',
    maintainer_email='team@example.com',
    description='Smart APC AMR task manager node',
    license='MIT',
    extras_require={'test': ['pytest']},
    entry_points={
        'console_scripts': [
            'task_manager_node = apc_amr.task_manager_node:main',
        ],
    },
)
