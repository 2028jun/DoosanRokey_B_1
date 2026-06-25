import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
import time

# 매니저와 동일한 액션 인터페이스 임포트
from hamburger_interfaces.action import BurgerTask

class DummyRobotNode(Node):
    def __init__(self):
        super().__init__('dummy_robot_node')
        
        # 매니저가 바라보는 'robot_task' 액션 서버를 엽니다.
        self._action_server = ActionServer(
            self,
            BurgerTask,
            'burger_task',
            self.execute_callback
        )
        self.get_logger().info('🤖 [가짜 로봇] 테스트용 액션 서버가 가동되었습니다. 명령을 기다립니다.')

    def execute_callback(self, goal_handle):
        # 매니저가 보낸 메시지 확인
        order_id = goal_handle.request.order_id
        task = goal_handle.request.task_type
        item = goal_handle.request.ingredient
        dest = goal_handle.request.destination

        self.get_logger().info(f'📥 [명령 수신] 주문:{order_id} | 행동:{task} | 대상:{item} | 목적지:{dest}')
        
        # 로봇이 물리적으로 움직이는 척 1초간 대기 (딜레이 테스트용)
        time.sleep(2.0)

        # 💡 매니저에게 "성공(SUCCEEDED)" 결과 콜백을 강제로 쏩니다!
        goal_handle.succeed()
        
        # Result 메시지 실체 채워서 리턴
        result = BurgerTask.Result()
        result.success = True
        
        self.get_logger().info(f'📤 [결과 전송] {task} ({item}) 완료 신호 발송!')
        return result

def main(args=None):
    rclpy.init(args=args)
    node = DummyRobotNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()