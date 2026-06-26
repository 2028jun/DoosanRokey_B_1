import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
import collections
from hamburger_interfaces.msg import OrderInfo
from hamburger_interfaces.action import BurgerTask
from hamburger_interfaces.srv import EmergencyStop 

class CookingManagerNode(Node):
    def __init__(self):
        super().__init__('cooking_manager_node')

        self.order_subscriber = self.create_subscription(
            OrderInfo, 'burger_order', self.order_callback, 10
        )

        self.robot_action_client = ActionClient(self, BurgerTask, '/burger_task')

        # 상태 및 스케줄링 관리 변수
        self.task_queue = collections.deque()  # FIFO 큐
        self.is_robot_busy = False             
        self.current_order_id = 0              

        # 타이머 변수
        self.fry_timer = None
        self.patty_flip_timer = None          
        self.patty_second_half_timer = None   

        # 의존성 제어 플래그
        self.is_fry_cooked_and_placed = False
        self.is_patty_cooked_and_placed = False
        self.is_waiting_lock = False           

        # 다중 메뉴 상태 플래그
        self.sauce = False
        self.fry_running = False  # 현재 튀김기가 작동 중인지 여부

        # 직전 작업 정보 기록용 변수
        self.last_task = ""
        self.last_ingredient = ""
        self.last_destination = ""

        self.get_logger().info('🍳 [Cooking Manager] 규칙 기반 완전 무결성 스케줄러 가동.')

    def order_callback(self, msg):      # 작업을 큐에 추가
        if self.is_robot_busy or len(self.task_queue) > 0:
            self.get_logger().warn(f'⏳ [주문 대기] 주문 번호 {msg.order_id}번은 대기열에 추가되었습니다.')
        else:
            self.current_order_id = msg.order_id
            self.get_logger().info(f'📥 [주문 접수] 번호: {msg.order_id}번 조리를 즉시 시작합니다.')

        self.is_patty_cooked_and_placed = False
        self.is_fry_cooked_and_placed = False   
        self.is_waiting_lock = False
        self.sauce = False
        self.fry_running = False

        # 감자튀김 조리 시작
        if msg.side_item != "NONE":
            self.task_queue.extend([(msg.order_id, "튀김조리", "튀김", "튀김기")])
            self.fry_running = True

        # 패티 조리 시작
        self.task_queue.extend([(msg.order_id, "패티조리", "패티", "그릴")])

        # 버거 기본 재료 쌓기
        for ingredient in msg.ingredients:
            if ingredient == "SAUCE":
                self.sauce = True
                continue
                
            if ingredient == "PATTY":
                continue
            
            korean_name = self.map_ingredient_name(ingredient)
            self.task_queue.extend([(msg.order_id, "재료 옮기기", korean_name, "버거 세팅지점")])

        # 음료수 추가
        if msg.beverage_item != "NONE":
            korean_beverage = self.map_ingredient_name(msg.beverage_item)
            self.task_queue.extend([(msg.order_id, "음료수 옮기기", korean_beverage, "음료수_세팅지점")])

        # 일을 완수하면 다음 동작 수행
        if not self.is_robot_busy:
            self.send_next_task()

    def send_next_task(self):   # 큐에서 작업 정보를 꺼내서 작업 수행
        
        if not self.task_queue:     # 모든 작업을 완료했을 때
            if self.fry_running:    # 튀김기가 아직 조리중이면 대기
                self.get_logger().warn('⏳ 튀김 완료 타이머를 대기합니다.', throttle_duration_sec=4.0)
                self.is_waiting_lock = True
                self.is_robot_busy = False
                return
                
            self.get_logger().info('✅ 모든 주문 요리 완료! 로봇 대기 상태 전환.')
            self.is_robot_busy = False
            self.is_waiting_lock = False
            self.current_order_id = 0
            return

        self.is_robot_busy = True
        
        # 패티 결합 전에는 상단 빵 작업 금지
        if self.task_queue[0][2] == "상단 빵" and not self.is_patty_cooked_and_placed:
            self.get_logger().warn('⚠️ 상단 빵 대기 중... 패티 조리 완수를 기다립니다.')
            self.is_waiting_lock = True 
            self.is_robot_busy = False
            return

        self.is_waiting_lock = False

        # 필터를 통과한 정상 작업 최종 pop
        order_id, task_type, ingredient, destination = self.task_queue.popleft()
        self.current_order_id = order_id

        self.last_task = task_type
        self.last_ingredient = ingredient
        self.last_destination = destination

        if not self.robot_action_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('❌ /burger_task 액션 서버가 응답하지 않습니다.')
            self.is_robot_busy = False
            self.task_queue.appendleft((order_id, task_type, ingredient, destination))
            return

        goal_msg = BurgerTask.Goal()
        goal_msg.order_id = order_id
        goal_msg.task_type = task_type
        goal_msg.ingredient = ingredient
        goal_msg.destination = destination

        self.get_logger().info(f'🤖 [명령 전송] 행동:{task_type} | 대상:{ingredient} | 목적지:{destination}')

        send_goal_future = self.robot_action_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('❌ [명령 거부됨] 대기열 복구 후 재시도합니다.')
            self.task_queue.appendleft((self.current_order_id, self.last_task, self.last_ingredient, self.last_destination))
            self.is_robot_busy = False
            return
            
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        """ 액션 완수 시 타이머 가동 및 플래그 트리거 """
        status = future.result().status
        
        if status != 4:     #
            self.get_logger().error(f'🚨 [동작 실패] 안전을 위해 스케줄러를 차단합니다.')
            self.is_robot_busy = False
            return
        
        # 타이머 가동 조건
        if self.last_task == "튀김조리" and self.last_ingredient == "튀김" and self.last_destination == "튀김기":
            self.get_logger().info('🍟 튀김망 투입 완료! 5분 감자튀김 튀기기 타이머 가동.')
            self.fry_timer = self.create_timer(300.0, self.fry_done_callback)
            
        elif self.last_task == "패티조리" and self.last_ingredient == "패티" and self.last_destination == "그릴":
            self.get_logger().info('🥩 패티 그릴 안착 완료! 1분 뒤집기 타이머 구동.')
            self.patty_flip_timer = self.create_timer(60.0, self.patty_flip_callback) 
            
        elif self.last_task == "패티뒤집기" and self.last_ingredient == "패티" and self.last_destination == "그릴":
            self.get_logger().info('🔄 패티 뒤집기 완료 확인! 후반전 조리 타이머 가동.')
            self.patty_second_half_timer = self.create_timer(60.0, self.patty_done_callback) 

        # 조리 완료된 패티를 작업 완료 시
        elif self.last_task == "재료 옮기기" and self.last_ingredient == "패티" and self.last_destination == "버거 세팅지점":
            self.get_logger().info('✨ [락 해제] 패티가 결합되었습니다. 상단 빵 조립 락을 해제합니다.')
            self.is_patty_cooked_and_placed = True

        # 안전하게 단 한 번만 다음 태스크 루프를 호출
        self.send_next_task()

    def insert_urgent_sequence(self, sequence):
        insert_idx = 0
        for i, task in enumerate(self.task_queue):  # 패티뒤집기와 튀김옮기기 타이머가 겹치면 순서대로 처리
            if task[1] in ["패티뒤집기", "튀김옮기기"]:
                insert_idx = i + 1
            else:           # 나머지 작업은 뒤로 밀리며 패티뒤집기 혹은 튀김옮기기 먼저 처리
                break

        for task in reversed(sequence):
            self.task_queue.insert(insert_idx, task)

        if self.is_waiting_lock:
            self.is_waiting_lock = False
            self.send_next_task()

    def patty_flip_callback(self):      
        self.get_logger().warn('⏰ [타이머] 패티를 뒤집습니다.')
        if self.patty_flip_timer:
            self.patty_flip_timer.destroy()
            self.patty_flip_timer = None

        urgent_sequence = [(self.current_order_id, "패티뒤집기", "패티", "그릴")]
        if self.sauce:      # 소스를 주문 받았을 때 패티 뒤집은 후 소스 작업 시행
            urgent_sequence.append((self.current_order_id, "소스뿌리기", "소스", "버거_세팅지점"))
        self.insert_urgent_sequence(urgent_sequence)

    def fry_done_callback(self):
        self.get_logger().warn('⏰ [타이머] 5분 경과! 감자튀김 조리가 끝나 수거합니다.')
        if self.fry_timer:
            self.fry_timer.destroy()
            self.fry_timer = None

        extract_sequence = [(self.current_order_id, "튀김옮기기", "튀김", "튀김기 세팅지점")]
        self.insert_urgent_sequence(extract_sequence)

        self.task_queue.append((self.current_order_id, "튀김세팅", "튀김", "튀김 세팅지점"))
        self.fry_running = False 

    def patty_done_callback(self):
        self.get_logger().warn('⏰ [타이머] 패티 최종 조리가 완료되었습니다. 버거 적재를 시작합니다.')
        if self.patty_second_half_timer:
            self.patty_second_half_timer.destroy()
            self.patty_second_half_timer = None

        patty_sequence = [(self.current_order_id, "재료 옮기기", "패티", "버거 세팅지점")]
        self.insert_urgent_sequence(patty_sequence)

    def map_ingredient_name(self, eng_name):
        mapping = {
            "BREAD_BOTTOM": "하단 빵", "BREAD_TOP": "상단 빵",
            "PATTY": "패티", "CHEESE": "치즈",
            "TOPPING": "토핑", "DRINK": "음료수", "FRY": "감자튀김"
        }
        return mapping.get(eng_name, eng_name)

def main(args=None):
    rclpy.init(args=args)
    node = CookingManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()