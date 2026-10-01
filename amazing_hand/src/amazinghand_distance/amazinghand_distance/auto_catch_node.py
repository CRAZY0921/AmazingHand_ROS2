#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Int32MultiArray
import numpy as np

class AutoCatchNode(Node):
    def __init__(self):
        super().__init__('auto_catch_node')

        self.state = 'IDLE'
        self.trigger_threshold_mm = 80  # 80 mm (8 cm)

        # 接收外部啟動命令
        self.task_sub = self.create_subscription(
            String,
            '/hand/auto_cmd',
            self.task_callback,
            10
        )

        # 訂閱距離感測器數據（修正為 Int32MultiArray）
        self.dist_sub = self.create_subscription(
            Int32MultiArray,
            '/hand/distance_matrix',
            self.distance_callback,
            10
        )

        # 轉發指令給原廠靈巧手控制器 grasp_controller_node
        self.cmd_pub = self.create_publisher(
            String,
            '/hand/task_cmd',
            10
        )

        self.get_logger().info('Auto Catch Node ready. Waiting for /hand/auto_cmd ("start" / "stop")...')

    def task_callback(self, msg: String):
        command = msg.data.strip().lower()
        if command in ['start', 'catch', 'arm']:
            self.state = 'ARMED'
            self.get_logger().info('>>> [STATE: ARMED] Proximity trigger activated! Waiting for object...')
        elif command in ['stop', 'open', 'reset']:
            self.state = 'IDLE'
            open_msg = String()
            open_msg.data = 'open'
            self.cmd_pub.publish(open_msg)
            self.get_logger().info('>>> [STATE: IDLE] Stopped. Sent "open" to hand.')

    def distance_callback(self, msg: Int32MultiArray):
        if self.state != 'ARMED' or len(msg.data) == 0:
            return

        # 轉為 8x8 矩陣並取中心區域
        matrix = np.array(msg.data, dtype=np.int32).reshape((-1, 8))
        if matrix.shape[0] >= 8:
            center_region = matrix[2:6, 2:6]
        else:
            center_region = matrix

        valid = center_region[(center_region > 20) & (center_region < 2000)]
        if valid.size == 0:
            return

        min_dist = np.min(valid)

        if min_dist <= self.trigger_threshold_mm:
            self.get_logger().warn(f'>>> [TRIGGER] Object detected at {min_dist} mm! Sending "grasp" to hand!')
            
            # 向 grasp_controller_node 發布 "grasp"
            grasp_msg = String()
            grasp_msg.data = 'grasp'
            self.cmd_pub.publish(grasp_msg)
            
            self.state = 'IDLE'

def main(args=None):
    rclpy.init(args=args)
    node = AutoCatchNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
