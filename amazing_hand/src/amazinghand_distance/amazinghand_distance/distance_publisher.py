import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32MultiArray
import serial
import time

class DistancePublisher(Node):
    def __init__(self):
        super().__init__('distance_publisher_node')
        self.publisher_ = self.create_publisher(Int32MultiArray, '/hand/distance_matrix', 10)
        
        # 連接 Serial 埠
        port = '/dev/ttyUSB0'
        baudrate = 115200
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.get_logger().info(f'Successfully opened serial port: {port}')
        except Exception as e:
            self.get_logger().error(f'Failed to open serial port {port}: {e}')
            self.ser = None

        self.timer = self.create_timer(0.05, self.read_and_publish)  # 20 Hz

    def read_and_publish(self):
        if not self.ser or not self.ser.is_open:
            return
        
        try:
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                return

            # 支援逗號或空格分隔的距離數據
            sep = ',' if ',' in line else None
            values = [int(v) for v in line.split(sep) if v.isdigit() or (v.startswith('-') and v[1:].isdigit())]

            if values:
                msg = Int32MultiArray()
                msg.data = values
                self.publisher_.publish(msg)
        except Exception as e:
            self.get_logger().warn(f'Parse error: {e}')

    def destroy_node(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = DistancePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
