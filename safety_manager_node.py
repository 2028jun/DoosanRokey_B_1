# nodes/safety_manager_node.py
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
from hamburger_interfaces.srv import EmergencyStop
from dsr_msgs2.srv import MoveStop

class SafetyManagerNode(Node):
    def __init__(self):
        super().__init__('safety_manager_node')
        
        # 1. 외력 센서 구독
        self.create_subscription(Bool, '/robot_force_sensor', self.force_callback, 10)
        
        # 2. 로봇 제어 시스템(manager_node) 서비스 클라이언트
        self.cli_controller = self.create_client(EmergencyStop, '/emergency_stop_robot_controller')
        self.move_stop_clients = [
            ('/motion/move_stop', self.create_client(MoveStop, '/motion/move_stop')),
            ('/dsr01/motion/move_stop', self.create_client(MoveStop, '/dsr01/motion/move_stop')),
        ]
        
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

        if state:
            self.request_motion_stop()
        
        # 로봇 컨트롤러 노드로 비상정지 서비스 요청 전송
        req = EmergencyStop.Request()
        req.emergency_state = state
        req.reason = reason  
        
        if self.cli_controller.wait_for_service(timeout_sec=1.0):           
            self.cli_controller.call_async(req)
        else:
            self.get_logger().error("❌ 비상정지 서비스 서버가 응답하지 않습니다!")

        status_msg = String()
        if state:  
            if "외력" in reason:
                status_msg.data = f"로봇 충돌이 감지되었습니다! 현장 위험 요소를 제거하고 시스템을 재가동하십시오."
            else:
                status_msg.data = f"관리자가 비상정지 버튼을 눌렀습니다. 현장 확인 후 시스템을 재가동하십시오."
        else:
            status_msg.data = "정상 가동 준비: 비상 정지 락 해제됨. (시스템 재시작 필요)"
            
        self.pub_status.publish(status_msg)

    def request_motion_stop(self):
        for service_name, client in self.move_stop_clients:
            if client.service_is_ready():
                req = MoveStop.Request()
                req.stop_mode = 0
                client.call_async(req)
                self.get_logger().error(f"🚨 {service_name} 즉시 정지 요청을 전송했습니다.")
                return

        self.get_logger().error("❌ move_stop 서비스가 준비되지 않아 즉시 정지 요청을 보내지 못했습니다. (/motion, /dsr01/motion 모두 실패)")

    def hmi_emergency_callback(self, msg):
        if msg.data == True:
            self.get_logger().warn("🚨 관리자가 수동으로 긴급 정지 버튼을 눌렀습니다!")
            self.trigger_all_nodes(True, "관리자 수동 정지 발동")
        else:
            self.get_logger().info("🔓 관리자가 안전을 확인하고 비상 정지 버튼을 해제했습니다.")
            self.trigger_all_nodes(False, "관리자 버튼 해제")

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
