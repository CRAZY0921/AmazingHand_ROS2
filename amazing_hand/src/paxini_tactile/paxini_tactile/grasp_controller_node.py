import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray, String
import numpy as np

class GraspControllerNode(Node):
    def __init__(self):
        super().__init__('grasp_controller_node')

        self.declare_parameter('force_threshold', 1.2)
        self.declare_parameter('step_angle_deg', 2.0)
        self.declare_parameter('control_rate_hz', 25.0)

        self.threshold = self.get_parameter('force_threshold').get_parameter_value().double_value
        self.step_angle = self.get_parameter('step_angle_deg').get_parameter_value().double_value
        rate_hz = self.get_parameter('control_rate_hz').get_parameter_value().double_value

        self.middle_pos = np.array([3, 0, -5, -8, -2, 5, -12, 0], dtype=float)
        # [thumb, index, middle, ring]
        self.finger_angles = np.array([-35.0, -35.0, -35.0, -35.0], dtype=float)
        self.current_forces = np.array([0.0, 0.0, 0.0, 0.0])
        self.braked_flags = [False, False, False, False]
        self.state = 'IDLE'

        self.fz_sub = self.create_subscription(Float32MultiArray, '/tactile/fz', self.fz_callback, 10)
        self.task_sub = self.create_subscription(String, '/hand/task_cmd', self.task_callback, 10)
        self.cmd_pub = self.create_publisher(Float32MultiArray, '/hand/cmd_positions', 10)
        self.timer = self.create_timer(1.0 / rate_hz, self.control_loop)

        self.get_logger().info(f'Grasp Controller 啟動！當前接觸煞車閾值: {self.threshold} N')

    def fz_callback(self, msg: Float32MultiArray):
        if len(msg.data) >= 4:
            self.current_forces = np.array(msg.data[:4])

    def task_callback(self, msg: String):
        cmd = msg.data.strip().lower()
        if cmd == 'grasp':
            self.state = 'GRASPING'
            self.braked_flags = [False, False, False, False]
            self.get_logger().info('收到指令：開始自適應包覆抓取...')
        elif cmd == 'open':
            self.state = 'OPENING'
            self.braked_flags = [False, False, False, False]
            self.get_logger().info('收到指令：開始張開...')
        elif cmd == 'stop':
            self.state = 'HOLDING'
            self.get_logger().info('收到指令：保持當前姿態。')

    def control_loop(self):
        if self.state == 'GRASPING':
            all_braked = True
            for i in range(4):
                # 如果已經煞車，則維持鎖定
                if self.braked_flags[i]:
                    continue

                # 判定受力是否達標
                if self.current_forces[i] >= self.threshold:
                    self.braked_flags[i] = True
                    self.get_logger().info(f'手指 [{i}] 碰觸物體 (力={self.current_forces[i]:.2f}N)，立即煞車鎖定！')
                elif self.finger_angles[i] < 90.0:
                    # 尚未受力且未到極限，繼續前進一步
                    self.finger_angles[i] = min(90.0, self.finger_angles[i] + self.step_angle)
                    all_braked = False
                else:
                    self.braked_flags[i] = True

            self.get_logger().info(
                f"[GRASP] 力:[T:{self.current_forces[0]:.2f}, I:{self.current_forces[1]:.2f}, M:{self.current_forces[2]:.2f}, R:{self.current_forces[3]:.2f}] | "
                f"角:{np.round(self.finger_angles, 1)}",
                throttle_duration_sec=0.2
            )

            self.publish_angles()

            if all_braked:
                self.state = 'HOLDING'
                self.get_logger().info('所有手指已完成自適應抓握並鎖定！')

        elif self.state == 'OPENING':
            all_opened = True
            open_step = self.step_angle * 4.0
            for i in range(4):
                if self.finger_angles[i] > -35.0:
                    self.finger_angles[i] = max(-35.0, self.finger_angles[i] - open_step)
                    all_opened = False

            self.publish_angles()

            if all_opened:
                self.state = 'IDLE'
                self.get_logger().info('手掌已張開完成。')

    def publish_angles(self):
        thumb_ang  = self.finger_angles[0]
        index_ang  = self.finger_angles[1]
        mid_ang    = self.finger_angles[2]
        ring_ang   = self.finger_angles[3]

        servo_deg = np.array([
            index_ang, -index_ang,
            mid_ang,   -mid_ang,
            ring_ang,  -ring_ang,
            thumb_ang, -thumb_ang
        ])

        target_rad = np.deg2rad(self.middle_pos + servo_deg)
        msg = Float32MultiArray()
        msg.data = target_rad.tolist()
        self.cmd_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = GraspControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
