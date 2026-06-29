# 📄 cooking_manager_node.py 전체 반영본

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
import collections
from hamburger_interfaces.msg import OrderInfo
from hamburger_interfaces.action import BurgerTask

class CookingManagerNode(Node):
    def __init__(self):
        super().__init__('cooking_manager_node')

        self.order_subscriber = self.create_subscription(
            OrderInfo, 'burger_order', self.order_callback, 10
        )

        self.robot_action_client = ActionClient(self, BurgerTask, '/burger_task')

        # 상태 및 С케줄링 관리 변수 (기존 변수 유지)
        self.task_queue = collections.deque()  
        self.is_robot_busy = False             
        self.current_order_id = 0              

        # 타이머 변수
        self.fry_timers = {}
        self.patty_flip_timers = {}          
        self.patty_second_half_timers = {}   

        # 의존성 제어 플래그
        self.is_fry_cooked_and_placed = {}
        self.is_patty_cooked_and_placed = {}
        self.is_waiting_lock = False           

        # 다중 메뉴 상태 플래그
        self.sauce = {}
        self.fry_running = {}  

        # 직전 작업 정보 기록용 변수
        self.last_order_id = 0  
        self.last_task = ""
        self.last_ingredient = ""
        self.last_destination = ""

        self.get_logger().info('🍳 [Cooking Manager] 햄버거 조리 작업 스케줄러 가동.')

    def order_callback(self, msg):      
        target_id = msg.order_id
        
        if self.is_robot_busy or len(self.task_queue) > 0:
            self.get_logger().warn(f'⏳ [주문 대기] 주문 번호 {target_id}번은 대기열에 추가되었습니다.')
        else:
            self.current_order_id = target_id
            self.get_logger().info(f'📥 [주문 접수] 번호: {target_id}번 조리를 즉시 시작합니다.')

        self.is_patty_cooked_and_placed[target_id] = False
        self.is_fry_cooked_and_placed[target_id] = False   
        self.is_waiting_lock = False
        self.sauce[target_id] = False
        self.fry_running[target_id] = False

        if msg.side_item != "NONE":
            self.task_queue.extend([(target_id, "튀김 조리", "튀김")])
            self.fry_running[target_id] = True

        self.task_queue.extend([(target_id, "패티 조리", "패티")])

        for ingredient in msg.ingredients:
            if ingredient == "SAUCE":
                self.sauce[target_id] = True
                continue
                
            if ingredient == "PATTY":
                continue
            
            korean_name = self.map_ingredient_name(ingredient)
            self.task_queue.extend([(target_id, "재료 옮기기", korean_name)])

        if msg.beverage_item != "NONE":
            korean_beverage = self.map_ingredient_name(msg.beverage_item)
            self.task_queue.extend([(target_id, "음료수 옮기기", korean_beverage)])

        self.task_queue.extend([(target_id, "종이 빼기", "종이")])

        if not self.is_robot_busy:
            self.send_next_task()

    def send_next_task(self):   
        if not self.task_queue:     
            active_fries = [oid for oid, running in self.fry_running.items() if running]
            if active_fries:
                self.get_logger().warn(f'⏳ 튀김 완료 타이머를 대기합니다.', throttle_duration_sec=4.0)
                self.is_waiting_lock = True
                self.is_robot_busy = False
                return
                
            self.get_logger().info('✅ 모든 주문 요리 완료! 로봇 대기 상태 전환.')
            self.is_robot_busy = False
            self.is_waiting_lock = False
            self.current_order_id = 0

            return

        next_order_id = self.task_queue[0][0]
        if self.task_queue[0][2] == "상단 빵" and not self.is_patty_cooked_and_placed.get(next_order_id, False):
            self.get_logger().warn(f'⚠️ [주문 {next_order_id}] 상단 빵 대기 중... 패티 조리 완수를 기다립니다.')
            self.is_waiting_lock = True 
            self.is_robot_busy = False
            return

        self.is_waiting_lock = False
        self.is_robot_busy = True

        order_id, task_type, ingredient = self.task_queue.popleft()
        self.current_order_id = order_id

        self.last_order_id = order_id 
        self.last_task = task_type
        self.last_ingredient = ingredient

        if not self.robot_action_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('❌ /burger_task 액션 서버가 응답하지 않습니다.')
            self.is_robot_busy = False
            self.task_queue.appendleft((order_id, task_type, ingredient))
            return

        goal_msg = BurgerTask.Goal()
        goal_msg.order_id = order_id
        goal_msg.task_type = task_type
        goal_msg.ingredient = ingredient

        self.get_logger().info(f'🤖 [명령 전송] 주문번호: {order_id} | 행동:{task_type} | 대상:{ingredient}')

        send_goal_future = self.robot_action_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('❌ [명령 거부됨] 대기열 복구 후 재시도합니다.')
            self.task_queue.appendleft((self.current_order_id, self.last_task, self.last_ingredient))
            self.is_robot_busy = False
            return
            
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        status = future.result().status
        if status != 4:     
            self.get_logger().error(f'🚨 [동작 실패] 안전을 위해 스케줄러를 차단합니다.')
            self.is_robot_busy = False
            return
        
        captured_id = self.last_order_id

        if self.last_task == "튀김 조리" and self.last_ingredient == "튀김":
            self.get_logger().info(f'🍟 [주문 {captured_id}] 튀김망 투입 완료! 5분 감자튀김 타이머 가동.')
            self.fry_timers[captured_id] = self.create_timer(300.0, lambda: self.fry_done_callback(captured_id))
            
        elif self.last_task == "패티 조리" and self.last_ingredient == "패티":
            self.get_logger().info(f'🥩 [주문 {captured_id}] 패티 그릴 안착 완료! 1분 뒤집기 타이머 구동.')
            self.patty_flip_timers[captured_id] = self.create_timer(60.0, lambda: self.patty_flip_callback(captured_id)) 
            
        elif self.last_task == "패티 뒤집기" and self.last_ingredient == "패티":
            self.get_logger().info(f'🔄 [주문 {captured_id}] 패티 뒤집기 완료 확인! 후반전 조리 타이머 가동.')
            self.patty_second_half_timers[captured_id] = self.create_timer(60.0, lambda: self.patty_done_callback(captured_id)) 

        elif self.last_task == "재료 옮기기" and self.last_ingredient == "패티":
            self.get_logger().info(f'✨ [락 해제] [주문 {captured_id}] 패티가 결합되었습니다. 상단 빵 조립 락을 해제합니다.')
            self.is_patty_cooked_and_placed[captured_id] = True

        self.send_next_task()

    def insert_urgent_sequence(self, sequence):
        if not sequence: return
        target_oid = sequence[0][0]

        fry_setting_tasks = [t for t in sequence if t[1] == "튀김 세팅"]
        other_urgent_tasks = [t for t in sequence if t[1] != "튀김 세팅"]

        for task in reversed(other_urgent_tasks):
            insert_idx = 0
            for i, q_task in enumerate(self.task_queue):
                if q_task[1] in ["패티 뒤집기", "튀김 옮기기"]:
                    insert_idx = i + 1
                else:
                    break
            self.task_queue.insert(insert_idx, task)

        if fry_setting_tasks:
            has_beverage = any(q_task[0] == target_oid and q_task[1] == "음료수 옮기기" for q_task in self.task_queue)
            if has_beverage:
                new_queue = collections.deque()
                for q_task in self.task_queue:
                    if q_task[0] == target_oid and q_task[1] == "음료수 옮기기":
                        new_queue.extend(fry_setting_tasks)
                    new_queue.append(q_task)
                self.task_queue = new_queue
            else:
                new_queue = collections.deque()
                inserted = False
                for q_task in self.task_queue:
                    if q_task[0] == target_oid and q_task[1] == "종이 빼기":
                        new_queue.extend(fry_setting_tasks)
                        inserted = True
                    new_queue.append(q_task)
                if inserted: self.task_queue = new_queue
                else: self.task_queue.extend(fry_setting_tasks)

        if (self.is_waiting_lock or not self.is_robot_busy):
            self.is_waiting_lock = False
            self.send_next_task()

    def patty_flip_callback(self, order_id):      
        self.get_logger().warn(f'⏰ [타이머] {order_id}번 주문 패티를 뒤집습니다.')
        if order_id in self.patty_flip_timers:
            self.patty_flip_timers[order_id].destroy()
            del self.patty_flip_timers[order_id]

        urgent_sequence = [(order_id, "패티 뒤집기", "패티")]
        if self.sauce.get(order_id, False):      
            urgent_sequence.append((order_id, "소스 뿌리기", "소스"))
        self.insert_urgent_sequence(urgent_sequence)

    def fry_done_callback(self, order_id):
        self.get_logger().warn(f'⏰ [타이머] 5분 경과! {order_id}번 주문 감자튀김 조리가 끝나 수거합니다.')
        if order_id in self.fry_timers:
            self.fry_timers[order_id].destroy()
            del self.fry_timers[order_id]

        extract_sequence = [(order_id, "튀김 꺼내기", "튀김"),
                            (order_id, "튀김 세팅", "튀김")]
        self.insert_urgent_sequence(extract_sequence)
        self.fry_running[order_id] = False 

    def patty_done_callback(self, order_id):
        self.get_logger().warn(f'⏰ [타이머] {order_id}번 주문 패티 최종 조리가 완료되었습니다. 버거 적재를 시작합니다.')
        if order_id in self.patty_second_half_timers:
            self.patty_second_half_timers[order_id].destroy()
            del self.patty_second_half_timers[order_id]

        patty_sequence = [(order_id, "재료 옮기기", "패티")]
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