import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_share = get_package_share_directory('paxini_tactile')
    urdf_file = os.path.join(pkg_share, 'urdf', 'amazing_hand.urdf')

    # 讀取 URDF 模型內容
    with open(urdf_file, 'r') as infp:
        robot_desc = infp.read()

    return LaunchDescription([
        # 1. 機器人狀態發布器 (解析 URDF + 發布 TF)
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_desc}]
        ),

        # 2. Amazing Hand 馬達驅動節點
        Node(
            package='paxini_tactile',
            executable='amazing_hand_node',
            name='amazing_hand_node',
            output='screen',
            parameters=[{'port': '/dev/ttyACM0', 'baudrate': 1000000}]
        ),

        # 3. Paxini 觸覺感測器節點
        Node(
            package='paxini_tactile',
            executable='paxini_node',
            name='paxini_node',
            output='screen',
            parameters=[{'port': '/dev/ttyACM1', 'baudrate': 921600}]
        ),

        # 4. 抓握控制器節點
        Node(
            package='paxini_tactile',
            executable='grasp_controller_node',
            name='grasp_controller_node',
            output='screen',
            parameters=[{'contact_threshold': 1.5}]
        ),

        # 5. RViz2 視覺化
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen'
        )
    ])
