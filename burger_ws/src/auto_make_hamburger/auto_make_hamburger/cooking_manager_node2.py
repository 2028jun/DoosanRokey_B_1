import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
import collections

# 커스텀 인터페이스 임포트 (BurgerTask.action)
from hamburger_interfaces.msg import OrderInfo
from hamburger_interfaces.action import BurgerTask

class CookingManagerNode(Node):
    def __init__(self):
        super().__init__('cooking_manager_node')

        self.order_subscriber = self.create_subscription(
            OrderInfo, 'burger_order', self.order_callback, 10
        )
        self.robot_action_client = ActionClient(self, BurgerTask, 'robot_task')