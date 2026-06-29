import rclpy
from rclpy.node import Node
from std_msgs.msg import String  
from hamburger_interfaces.msg import OrderInfo  
import json

class OrderBridgeNode(Node):
    def __init__(self):
        super().__init__('order_bridge_node')
        
        # 1. 리액트(웹 UI)로부터 최종 결제 신호를 받아올 서브스크라이버 생성
        # 토픽명: 'react_order_trigger'로 리액트 내부 토픽 인스턴스와 완벽 매칭
        self.react_subscriber = self.create_subscription(
            String,
            'react_order_trigger',
            self.react_order_callback,
            10
        )
        
        # 2. 기존 로봇 제어 시스템으로 최종 커스텀 메시지를 던져줄 퍼블리셔
        self.order_publisher = self.create_publisher(OrderInfo, 'burger_order', 10)
 
        # 3. 주문 번호 카운터 (내부 관리용 변수)
        self.order_counter = 100       

        self.get_logger().info('🍔 햄버거 주문 해주세요~')

    def react_order_callback(self, web_msg):
        """ 리액트 웹 UI에서 결제가 완료되어 웹소켓 신호가 들어오면 호출되는 콜백 함수 """
        try:
            # 💡 웹 프론트에서 넘어온 직렬화된 JSON 데이터 역직렬화(파싱)
            web_data = json.loads(web_msg.data)
            
            # React의 상태가 변화함에 따라 전송된 최신 true/false 플래그 획득, 데이터 안넘어오면 False 처리(치즈는 True)
            has_cheese   = web_data.get('cheese', True)
            has_topping  = web_data.get('topping', False)   
            has_sauce    = web_data.get('sauce', False)     
            has_beverage = web_data.get('beverage', False)  
            has_side     = web_data.get('side', False)      

            # 주문 번호 카운트 증가
            self.order_counter += 1 
            
            # 커스텀 인터페이스 메시지 객체 생성
            msg = OrderInfo()
            msg.order_id = self.order_counter
            
            # 1. 하단 번 및 패티 필수 적재 레이어 추가
            msg.ingredients.append("BREAD_BOTTOM")
            msg.ingredients.append("PATTY")
            
            # 2. 넘어온 플래그 값(True/False)에 의거하여 순차 분기 처리
            if has_cheese:
                msg.ingredients.append("CHEESE")

            if has_sauce:
                msg.ingredients.append("SAUCE")  
                
            if has_topping:
                msg.ingredients.append("TOPPING")
                
            # 3. 상단 번 필수 적재
            msg.ingredients.append("BREAD_TOP")
            
            # 4. 사이드 디시 및 드링크 예외 로직 매핑
            if has_beverage:
                msg.beverage_item = "DRINK"
            else:
                msg.beverage_item = "NONE"
                
            if has_side:
                msg.side_item = "FRY"
            else:
                msg.side_item = "NONE"

            # 5. 매니퓰레이터 및 물류 서브시스템이 참조할 최종 토픽 발행
            self.order_publisher.publish(msg)
            
            self.get_logger().info('==================================================')
            self.get_logger().info(f'📥 [웹 주문 접수 완료]')
            self.get_logger().info(f'🔔 주문 번호: {msg.order_id}')
            self.get_logger().info(f'🍔 선택된 재료 배열: {msg.ingredients}')
            self.get_logger().info(f'🥤 음로 선택 여부: {msg.beverage_item}')
            self.get_logger().info(f'🍟 사이드 메뉴: {msg.side_item}')
            self.get_logger().info('==================================================')

        except Exception as e:
            self.get_logger().error(f'⚠️ 주문 중계 처리 중 에러 발생: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = OrderBridgeNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('주문 중계 노드가 종료되었습니다.')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()