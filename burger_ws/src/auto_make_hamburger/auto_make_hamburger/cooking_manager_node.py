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

        # 상태 및 스케줄링 관리 변수
        self.task_queue = collections.deque()  # FIFO 큐
        self.is_robot_busy = False             
        self.current_order_id = 0              

        # 타이머 변수
        self.fry_timer = None
        self.patty_flip_timer = None          # 1번째 15초 (뒤집기용)
        self.patty_second_half_timer = None   # 2번째 15초 (뒤집은 후 완료용)

        # 의존성 제어 플래그
        self.is_fry_cooked_and_placed = False
        self.is_patty_cooked_and_placed = False
        self.is_waiting_lock = False           

        # 현재 로봇의 손 상태 추적 ("NONE", "도구", "소스통", "튀김망")
        self.robot_holding_item = "NONE"

        # 직전 작업 정보 기록용 변수
        self.last_task = ""
        self.last_ingredient = ""
        self.last_destination = ""

        self.get_logger().info('🍳 [Cooking Manager] 규칙 기반 완전 무결성 스케줄러 가동.')

    def order_callback(self, msg):
        """ 주문이 들어왔을 때 표준 명칭 규칙에 맞춰 기본 시퀀스를 조립하는 곳 """
        if self.is_robot_busy or len(self.task_queue) > 0:
            self.get_logger().warn(f'⏳ [주문 대기] 주문 번호 {msg.order_id}번은 대기열에 추가되었습니다.')
        else:
            self.current_order_id = msg.order_id
            self.get_logger().info(f'📥 [주문 접수] 번호: {msg.order_id}번 조리를 즉시 시작합니다.')

        self.is_patty_cooked_and_placed = False
        self.is_fry_cooked_and_placed = False   
        self.is_waiting_lock = False

        # 1️⃣ 감자튀김 조리 시작 (튀김망 제어)
        if msg.side_item != "NONE":
            self.task_queue.extend([(msg.order_id, "튀김조리", "튀김", "튀김기")])

        # 2️⃣ 패티 조리 시작
        self.task_queue.extend([(msg.order_id, "패티조리", "패티", "그릴")])

        # 3️⃣ 버거 기본 재료 쌓기 시퀀스
        for ingredient in msg.ingredients:
            if ingredient == "PATTY":
                continue 
            
            korean_name = self.map_ingredient_name(ingredient)
            
            if ingredient == "SAUCE":
                # 소스 뿌리기 시퀀스 (손 교체 흐름)
                self.task_queue.extend([(msg.order_id, "소스뿌리기", "소스", "버거_세팅지점")])
                
            else:
                self.task_queue.extend([(msg.order_id, "재료 옮기기", korean_name, "버거 세팅지점")])

        # 4️⃣ 음료수 처리
        if msg.beverage_item != "NONE":
            korean_beverage = self.map_ingredient_name(msg.beverage_item)
            self.task_queue.extend([(msg.order_id, "음료수 옮기기", korean_beverage, "음료수_세팅지점")])

        if not self.is_robot_busy:
            self.send_next_task()

    def send_next_task(self):
        """ 큐에서 작업을 하나씩 꺼내 전송 전 스마트 패스(중복 제거)를 수행하는 핵심 함수 """
        if not self.task_queue:
            self.get_logger().info('✅ 모든 주문 요리 완료! 로봇 대기 상태 전환.')
            self.is_robot_busy = False
            self.is_waiting_lock = False
            self.current_order_id = 0
            return

        self.is_robot_busy = True
        
        # [의존성 제어] 패티 결합 전에는 상단 빵 적재 금지 락(Lock)
        if self.task_queue[0][2] == "상단 빵" and not self.is_patty_cooked_and_placed:
            self.get_logger().warn('⚠️ [의존성 대기] 상단 빵 대기 중... 패티 조리 완수를 기다립니다.')
            self.is_waiting_lock = True 
            return

        self.is_waiting_lock = False

        # 필터를 통과한 정상 작업 최종 pop
        order_id, task_type, ingredient, destination = self.task_queue.popleft()
        self.current_order_id = order_id

        self.last_task = task_type
        self.last_ingredient = ingredient
        self.last_destination = destination

        if not self.robot_action_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error('❌ 로봇 컨트롤러가 응답하지 않습니다.')
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
            self.get_logger().error('❌ [명령 거부됨] 로봇이 명령 접수를 거부했습니다. 대기열 복구 후 재시도합니다.')
            # 💡 [보완 완료] 거부된 명령을 다시 대기열 맨 앞에 우겨넣고 바쁨을 풀어줍니다.
            self.task_queue.appendleft((self.current_order_id, self.last_task, self.last_ingredient, self.last_destination))
            if self.last_task == "잡기":
                self.robot_holding_item = "NONE" # 집기 시도 실패했으니 손상태 원복
            self.is_robot_busy = False
            return
            
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        """ 미니 액션이 완수되는 순간을 캐치하여 정밀 타이머를 키는 공간 """
        status = future.result().status
        
        # 💡 [보완 완료] 하드웨어 이상으로 액션이 실패(status != 4)했을 때 후속 명령 송출을 강제 정지시킵니다.
        if status != 4:
            self.get_logger().error(f'🚨 [동작 실패] 로봇 팔 제어 중 비정상 종료가 감지되었습니다. (Status Code: {status}) 안전을 위해 스케줄러를 차단합니다.')
            self.is_robot_busy = False
            return
        
        # 타이머 가동 조건
        if self.last_task == "튀김조리" and self.last_ingredient == "튀김" and self.last_destination == "튀김기":
            self.get_logger().info('🍟 튀김망 투입 완료! 30초 감자튀김 튀기기 타이머 가동.')
            self.fry_timer = self.create_timer(30.0, self.fry_done_callback)
            
        elif self.last_task == "패티조리" and self.last_ingredient == "패티" and self.last_destination == "그릴":
            self.get_logger().info('🥩 패티 그릴 안착 완료! 15초 뒤집기 타이머 구동.')
            self.patty_flip_timer = self.create_timer(15.0, self.patty_flip_callback)
            
        elif self.last_task == "패티뒤집기" and self.last_ingredient == "패티" and self.last_destination == "그릴":
            self.get_logger().info('🔄 패티 뒤집기 완료 확인! 추가 15초 조리 타이머 가동.')
            self.patty_second_half_timer = self.create_timer(15.0, self.patty_done_callback)
            
        elif self.last_task == "재료 옮기기" and self.last_ingredient == "패티" and self.last_destination == "버거 세팅지점":
            self.get_logger().info('✨ [락 해제] 패티가 결합되었습니다. 상단 빵 조립 락을 해제합니다.')
            self.is_patty_cooked_and_placed = True

        # 안전하게 단 한 번만 다음 태스크 루프를 호출
        self.send_next_task()

    def insert_urgent_sequence(self, sequence):

        insert_idx = 0
        
        # '동작 세트'가 큐 앞부분에 남아있다면, 그 세트가 끝날 때까지 새치기 인덱스를 뒤로 밀어냅니다.
        for i, task in enumerate(self.task_queue):
            if (task[1] == "패티뒤집기" or task[1] == "튀김옮기기"):
                insert_idx = i + 1
            else:
                # 일반 재료(치즈, 양배추 등)를 만나는 순간에야 비로소 그 앞에 새치기를 합니다.
                break

        for task in reversed(sequence):
            self.task_queue.insert(insert_idx, task)

        if self.is_waiting_lock:
            self.is_waiting_lock = False
            self.send_next_task()

    def patty_flip_callback(self):
        """ ⏰ 15초 경과: 패티 뒤집기 알람 루틴 """
        self.get_logger().warn('⏰ [타이머] 15초 경과! 패티를 뒤집습니다.')
        if self.patty_flip_timer:
            self.patty_flip_timer.destroy()
            self.patty_flip_timer = None

        flip_sequence = []
            
        flip_sequence.append((self.current_order_id, "패티뒤집기", "패티", "그릴")) 
        
        self.insert_urgent_sequence(flip_sequence)

    def fry_done_callback(self):
        """ ⏰ 30초 경과: 감자튀김 완료 알람 루틴 """
        self.get_logger().warn('⏰ [타이머] 30초 경과! 감자튀김 조리가 끝나 수거합니다.')
        if self.fry_timer:
            self.fry_timer.destroy()
            self.fry_timer = None

        extract_sequence = []
            
        extract_sequence.append((self.current_order_id, "튀김옮기기", "튀김", "튀김기 세팅지점"))
        self.insert_urgent_sequence(extract_sequence)

        self.task_queue.append((self.current_order_id, "튀김세팅", "튀김", "튀김 세팅지점"))

    def patty_done_callback(self):
        """ ⏰ 뒤집은 후 추가 15초 경과: 패티 수거 및 버거 결합 알람 루틴 """
        self.get_logger().warn('⏰ [타이머] 패티 최종 조리가 완료되었습니다. 버거 적재를 시작합니다.')
        if self.patty_second_half_timer:
            self.patty_second_half_timer.destroy()
            self.patty_second_half_timer = None

        patty_sequence = []

        patty_sequence.append((self.current_order_id, "재료 옮기기", "패티", "버거 세팅지점"))
        
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