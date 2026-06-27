# nodes/safety_manager_node.py
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
from hamburger_interfaces.srv import EmergencyStop

class SafetyManagerNode(Node):
    def __init__(self):
        super().__init__('safety_manager_node')
        
        # 1. 외력 센서 구독
        self.create_subscription(Bool, 'robot_force_sensor', self.force_callback, 10)
        
        # 2. 로봇 제어 시스템(manager_node) 서비스 클라이언트
        self.cli_controller = self.create_client(EmergencyStop, '/emergency_stop_robot_controller')
        
        # 3. 관리자 UI 상태 알림 퍼블리셔
        self.pub_status = self.create_publisher(String, 'robot_status_topic', 10)

        self.emergency_subscriber = self.create_subscription(
            Bool,
            '/emergency_stop',
            self.hmi_emergency_callback,
            10
        )

        self.get_logger().info('안전 관리 매니저 노드 실행')

        self.is_emergency = False

    def trigger_all_nodes(self, state, reason):

        if self.is_emergency == state:
            return
        
        self.is_emergency = state
        
        str =''
        req = EmergencyStop.Request()
        req.emergency_state = state
        req.reason = reason  
        
        if self.cli_controller.wait_for_service(timeout_sec=1.0):           
            self.cli_controller.call_async(req)
        else:
        # 💡 서비스 서버가 안 켜져 있으면 이 경고가 뜹니다.
            self.get_logger().error("❌ 비상정지 서비스 서버가 응답하지 않습니다! (컨트롤러 노드가 켜져있나요?)")

        # 리액트 관리자 UI 화면 문구 업데이트용 토픽 발행
        status_msg = String()
        if reason == "외력 감지!! 비상 정지 시스템을 가동합니다.":
            status_msg.data = f"🚨 비상 정지 시스템 가동: {reason}--------- 로봇을 확인해주세요."
            self.pub_status.publish(status_msg)

    def hmi_emergency_callback(self, msg):
        if msg.data == True:
            self.get_logger().warn("🚨 관리자가 수동으로 긴급 정지 버튼을 눌렀습니다!")
            self.trigger_all_nodes(True, "Manual Emergency Stop by Admin UI Button")
        else:
            self.get_logger().info("🔓 관리자가 안전을 확인하고 조리 재개 버튼을 눌렀습니다.")
            self.trigger_all_nodes(False, "Emergency Situation Cleared by Admin")

    def force_callback(self, msg):
        if self.is_emergency or msg.data == False:
            return
    
        if msg.data == True:
            self.get_logger().error("💥 로봇 외력 감지! 비상 정지 시스템을 가동합니다.")
            self.trigger_all_nodes(True, "외력 감지!! 비상 정지 시스템을 가동합니다.")

def main(args=None):
    rclpy.init(args=args)
    node = SafetyManagerNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()