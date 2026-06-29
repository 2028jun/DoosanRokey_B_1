# 📄 cooking_manager_node.py 전체 반영본

from math import sqrt
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
import collections
from hamburger_interfaces.msg import OrderInfo
from hamburger_interfaces.action import BurgerTask
from std_msgs.msg import String  # ★ String 메시지 타입 추가

class CookingManagerNode(Node):
    def __init__(self):
        super().__init__('cooking_manager_node')

        self.order_subscriber = self.create_subscription(
            OrderInfo, 'burger_order', self.order_callback, 10
        )

        self.robot_action_client = ActionClient(self, BurgerTask, '/burger_task')

        # ==========================================================
        # 📊 [관리자 대시보드 연동용 채널 및 변수 신설]
        # ==========================================================
        # 1. 리액트가 애타게 기다리는 마스터 채널 최종 퍼블리셔 등록
        
        
        # 2. 로봇 컨트롤러가 던져주는 하위 하드웨어 센서값 구독
        # self.sensor_subscriber = self.create_subscription(
        #     String, '/robot_raw_sensors', self.robot_sensor_callback, 10
        # )
        
        # # 로봇 하드웨어 백업 저장 버퍼 변수
        # self.rb_force = "0.0"
        # self.rb_tool = "그리퍼 단독"
        # self.rb_gripper = "RELEASE"

        # 진행률 추적용 독립 딕셔너리 정보 데이터 그룹
        self.total_predicted_tasks = {}  
        self.completed_task_counts = {}  
        self.current_progress_pct = 0    

        # 현재 모션 상태 추적 실시간 전치 변수
        # self.current_running_task = "대기 중"
        # self.current_running_ingredient = "-"
        # ==========================================================

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

    # 🛠️ [신설] 로봇이 쏴주는 가상/실제 하드웨어 스펙 수신 콜백
    # def robot_sensor_callback(self, msg):
    #     try:
    #         data = msg.data.split(',')
    #         self.rb_force = data[0]
    #         self.rb_tool = data[1]
    #         self.rb_gripper = data[2]
            
    #         # 센서 데이터가 들어올 때마다 최신 공정 상태와 진행률을 조립해 리액트로 토스
    #         self.publish_to_admin()
    #     except:
    #         pass

    # 🛠️ [신설] 조립된 5분할 마스터 규격을 리액트로 최종 Publish 하는 마스터 함수
    # def publish_to_admin(self):
    #     # 규격: "외력,도구,그리퍼,작업명,재료명,진행률"
    #     master_string = f"{self.rb_force},{self.rb_tool},{self.rb_gripper},{self.current_running_task},{self.current_running_ingredient},{self.current_progress_pct}"
    #     msg = String()
    #     msg.data = master_string
    #     self.telemetry_pub.publish(msg)

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
            self.task_queue.extend([(target_id, "튀김 조리", "튀김", "튀김기")])
            self.fry_running[target_id] = True

        self.task_queue.extend([(target_id, "패티 조리", "패티", "그릴")])

        for ingredient in msg.ingredients:
            if ingredient == "SAUCE":
                self.sauce[target_id] = True
                continue
                
            if ingredient == "PATTY":
                continue
            
            korean_name = self.map_ingredient_name(ingredient)
            self.task_queue.extend([(target_id, "재료 옮기기", korean_name, "버거 세팅지점")])

        if msg.beverage_item != "NONE":
            korean_beverage = self.map_ingredient_name(msg.beverage_item)
            self.task_queue.extend([(target_id, "음료수 옮기기", korean_beverage, "음료수_세팅지점")])

        self.task_queue.extend([(target_id, "종이 빼기", "종이", "버거 세팅")])

        # 📈 진행률 분모 예측 규칙 적용
        base_task_count = len([t for t in self.task_queue if t[0] == target_id])
        predicted_interrupt_count = 1  # 패티뒤집기
        if self.sauce[target_id]: predicted_interrupt_count += 1 # 소스뿌리기
        if msg.side_item != "NONE": predicted_interrupt_count += 2 # 튀김옮기기+튀김세팅
        predicted_interrupt_count += 1 # 최종 버거적재

        self.total_predicted_tasks[target_id] = base_task_count + predicted_interrupt_count
        self.completed_task_counts[target_id] = 0
        self.current_progress_pct = 0

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
            
            # 공정이 완전히 끝나면 화면을 대기 중으로 세팅
            # self.current_running_task = "대기 중"
            # self.current_running_ingredient = "-"
            # self.publish_to_admin()
            return

        next_order_id = self.task_queue[0][0]
        if self.task_queue[0][2] == "상단 빵" and not self.is_patty_cooked_and_placed.get(next_order_id, False):
            self.get_logger().warn(f'⚠️ [주문 {next_order_id}] 상단 빵 대기 중... 패티 조리 완수를 기다립니다.')
            self.is_waiting_lock = True 
            self.is_robot_busy = False
            return

        self.is_waiting_lock = False
        self.is_robot_busy = True

        order_id, task_type, ingredient, destination = self.task_queue.popleft()
        self.current_order_id = order_id

        self.last_order_id = order_id 
        self.last_task = task_type
        self.last_ingredient = ingredient
        self.last_destination = destination

        # ⚡ [실시간 공정 트래킹 업데이트] 로봇에게 액션을 넘기기 전에 현재 진행 공정 최신화
        # self.current_running_task = task_type
        # self.current_running_ingredient = ingredient
        # # self.publish_to_admin()

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
        status = future.result().status
        if status != 4:     
            self.get_logger().error(f'🚨 [동작 실패] 안전을 위해 스케줄러를 차단합니다.')
            self.is_robot_busy = False
            return
        
        captured_id = self.last_order_id
        
        # 📈 [진행률 분자 계산] 액션이 성공적으로 수행 완료되면 카운트 업
        # if captured_id in self.completed_task_counts:
        #     self.completed_task_counts[captured_id] += 1
        #     total = self.total_predicted_tasks.get(captured_id, 1)
        #     current = self.completed_task_counts[captured_id]
        #     self.current_progress_pct = min(int((current / total) * 100), 100)
        #     self.publish_to_admin()

        if self.last_task == "튀김 조리" and self.last_ingredient == "튀김" and self.last_destination == "튀김기":
            self.get_logger().info(f'🍟 [주문 {captured_id}] 튀김망 투입 완료! 5분 감자튀김 타이머 가동.')
            self.fry_timers[captured_id] = self.create_timer(300.0, lambda: self.fry_done_callback(captured_id))
            
        elif self.last_task == "패티 조리" and self.last_ingredient == "패티" and self.last_destination == "그릴":
            self.get_logger().info(f'🥩 [주문 {captured_id}] 패티 그릴 안착 완료! 1분 뒤집기 타이머 구동.')
            self.patty_flip_timers[captured_id] = self.create_timer(60.0, lambda: self.patty_flip_callback(captured_id)) 
            
        elif self.last_task == "패티 뒤집기" and self.last_ingredient == "패티" and self.last_destination == "그릴":
            self.get_logger().info(f'🔄 [주문 {captured_id}] 패티 뒤집기 완료 확인! 후반전 조리 타이머 가동.')
            self.patty_second_half_timers[captured_id] = self.create_timer(60.0, lambda: self.patty_done_callback(captured_id)) 

        elif self.last_task == "재료 옮기기" and self.last_ingredient == "패티" and self.last_destination == "버거 세팅지점":
            self.get_logger().info(f'✨ [락 해제] [주문 {captured_id}] 패티가 결합되었습니다. 상단 빵 조립 락을 해제합니다.')
            self.is_patty_cooked_and_placed[captured_id] = True

        self.send_next_task()

    def insert_urgent_sequence(self, sequence):
        if not sequence: return
        target_oid = sequence[0][0]
        
        # ⚡ [실시간 공정 인터럽트 트래킹] 타이머 스케줄이 터져서 새 모션이 기습 주입될 때도 화면 갱신
        # self.current_running_task = sequence[0][1]
        # self.current_running_ingredient = sequence[0][2]
        # self.publish_to_admin()

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
                    if q_task[0] == target_oid and q_task[1] == "종이  빼기":
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

        urgent_sequence = [(order_id, "패티 뒤집기", "패티", "그릴")]
        if self.sauce.get(order_id, False):      
            urgent_sequence.append((order_id, "소스 뿌리기", "소스", "버거_세팅지점"))
        self.insert_urgent_sequence(urgent_sequence)

    def fry_done_callback(self, order_id):
        self.get_logger().warn(f'⏰ [타이머] 5분 경과! {order_id}번 주문 감자튀김 조리가 끝나 수거합니다.')
        if order_id in self.fry_timers:
            self.fry_timers[order_id].destroy()
            del self.fry_timers[order_id]

        extract_sequence = [(order_id, "튀김 옮기기", "튀김", "튀김기 세팅지점"),
                            (order_id, "튀김 세팅", "튀김", "튀김 세팅지점")]
        self.insert_urgent_sequence(extract_sequence)
        self.fry_running[order_id] = False 

    def patty_done_callback(self, order_id):
        self.get_logger().warn(f'⏰ [타이머] {order_id}번 주문 패티 최종 조리가 완료되었습니다. 버거 적재를 시작합니다.')
        if order_id in self.patty_second_half_timers:
            self.patty_second_half_timers[order_id].destroy()
            del self.patty_second_half_timers[order_id]

        patty_sequence = [(order_id, "재료 옮기기", "패티", "버거 세팅지점")]
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