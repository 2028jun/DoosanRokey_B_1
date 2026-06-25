# nodes/safety_manager_node.py
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
from hamburger_interfaces.srv import EmergencyStop

class SafetyManagerNode(Node):
    def __init__(self):
        super().__init__('safety_manager_node')
        
        # 1. 외력 센서 구독
        self.create_subscription(Bool, '/robot_force_sensor', self.force_callback, 10)
        
        # 2. 로봇 제어 시스템(manager_node) 서비스 클라이언트
        self.cli = self.create_client(EmergencyStop, 'emergency_stop_service')
        
        # 3. 관리자 UI 상태 알림 퍼블리셔
        self.pub_status = self.create_publisher(String, 'robot_status_topic', 10)

    def force_callback(self, msg):
        if msg.data: # 외력 감지됨
            self.get_logger().error("⚠️ 외력 감지! 비상 정지 요청 중...")
            
            # 서비스 요청 보내기
            req = EmergencyStop.Request()
            req.emergency_state = True
            req.reason = "External Force Detected"
            self.cli.call_async(req)
            
            # UI 알림 보내기
            status_msg = String()
            status_msg.data = "🚨 외력 발생: 비상 정지됨"
            self.pub_status.publish(status_msg)

def main(args=None):
    rclpy.init(args=args)
    node = SafetyManagerNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()