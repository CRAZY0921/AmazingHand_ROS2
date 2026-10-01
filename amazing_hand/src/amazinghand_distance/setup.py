from setuptools import find_packages, setup

package_name = 'amazinghand_distance'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='root@todo.todo',
    description='AmazingHand distance sensor publisher',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'distance_publisher = amazinghand_distance.distance_publisher:main',
            'auto_catch_node = amazinghand_distance.auto_catch_node:main',
        ],
    },
)
