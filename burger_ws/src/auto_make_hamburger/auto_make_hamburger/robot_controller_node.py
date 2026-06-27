from math import sqrt
import rclpy
from rclpy.action import ActionServer
from hamburger_interfaces.action import BurgerTask
from hamburger_interfaces.srv import EmergencyStop
from dsr_msgs2.srv import GetToolForce
import DR_init
from std_msgs.msg import Bool

# --- [로봇 기본 설정 및 전역 변수] ---
ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"
VELOCITY, ACC = 125, 150

DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL

OFF, ON = 0, 1

# --- [티칭 좌표 리스트] ---
tool_home = [[367.96, -225.74, 481.1, 89.43, -91.43, -177.67], [365.46, -314.89, 477.73, 89.26, -91.58, -177.44]]   # 옮기기 도구 잡기
tool_after = [364.46, -75.59, 503.22, 89.44, -91.65, -177.26]   # 옮기는 도구 잡은 후 뒤로 빼기
patty_home = [362.82, -90.02, 221.2, 89.18, -91.65, -178.13]     # 패티 위치 이동
bun_bottom_home = [524.54, -81.59, 319.72, 89.59, -91.20, -177.89] # 하단 빵 위치 이동
topping1_home = [527.45, -82.2, 221.2, 89.7, -91.11, -178.04]   # 토핑1 위치 이동
topping2_home = [340.34, -88.37, 411.72, 89.84, -91.29, -177.99]    # 토핑2 위치 이동
bun_top_home = [343.35, -89.25, 309.89, 89.95, -91.21, -178.17 ] # 상단 빵 위치 이동
up_gradient = [394.8, -16.99, 528.09, 94.06, -62.64, -179.2]      # 재료 잡은 후 기울여서 안쪽으로 넣기

grill_move = [365.05, 90.01, 479.81, 130.08, -89.88, -174.96]   # 그릴에 안걸리게 위치 이동 
grill_up = [467.99, -38.01, 552.64, 144.94, -56.48, -177.96]  
grill_down = [632.34, -124.60, 236.11, 148.00, -116.67, -178.75]    # 패티 떨어 뜨리기
flip_tool_home = [[542.58, -268.43, 379.72, 89.15, -91.45, -177.98], [544.3, -335.39, 376.47, 88.55, -91.56, -178.04]]  # 뒤집개 도구 잡기
flip_tool_after = [624.54, 13.24, 443.65, 129.20, -94.28, -173.54]     # 뒤집개 도구 잡고 빼기
flip_home = [639.0, -144.81, 67.07, 151.86, -101.66, -178.25]   # 뒤집을 장소로 이동

flip_ready = [[20, 0, 0, 0, 0, 0], [0, 0, 120, 0, 0, 0]]    # 패티 도구위에 올리기
flip_final_ready = [749.13, -200.46, 76.69, 151.77, -95.27, -178.07]   # 뒤집기 전 수평 맞추기

plating_up = [572.9, 36.28, 550.34, 38.12,  72.86, -1.41]   # 트레이 위로 이동
plating_middle = [584.55, 54.14, 448.74, 38.12, 73.42, -1.27]   # 트레이 중간 위치
plating_down = [601.67, 75.6, 333.91, 37.06, 113.6, 0.02]

patty_ready = [[25, 0, 0, 0, 0, 0], [0, 0, 130, 0, 0, 0], [-25, 0, 0, 0, 0, 0]] # 패티를 그릴 위에서 잡기
patty_grip_home = [577.26, -81.14, 161.72, 145.45, -90.77, -179.16] # 패티 잡기 위해 그릴로 이동

ingredient_ready = [[0, 0, 90, 0, 0, 0], [20, 0, 0, 0, 0, 0], [0, 0, 125, 0, 0, 0], [-20, 0, 0, 0, 0, 0], [0, 0, -220, 0, 0, 0]]
# 칸에서 재료 잡기

fry_home = [453.73, 327.32, 255.87, 85.81, 88.06, 1.86] # 튀김 잡기 준비
fry_grip = [456.94, 395.29, 257.77, 85.97, 87.97, 1.78] # 튀김 잡기
fry_pongdang = [[-120, 0, 0, 0, 0, 0], [0, 0, 160, 0, 0, 0], [120, 0, 0, 0, 0, 0], [0, 0, -160, 0, 0, 0]]  # 튀김망 튀김기에 넣기
flip_angle = 180    # 뒤집는 각도

x0 = [0, 0, 90, 0, 90, 0]   # 초기화 조인트 각도

fry_plating_up = [779.03, 78.83, 196.43, 24.49, 92.43, 0.11]   # 튀김망 트레이 위로 올리기
fry_back_home = [456.94, 395.29, 300.77, 85.97, 87.97, 1.78] # 튀김망 제자리로 이동

sauce_home = [795.41, -62.28, 74.72, 168.75, -96.6, 89.5] # 소스통 잡기 준비
sauce_pick = [869.76, -77.15, 66.2, 168.62, -96.43, 89.71] # 소스통 잡기
sauce_ready = [838.65, 59.5, 386.38, 3.71, 100.86, -91.01] # 소스통 잡고 올리기
sauce_final_ready = [821.36, 209.31, 203.91, 12.39, 91.77, -88.86] # 소스통 트레이 이동
sauce_turn = [0, 0, 0, 0, 0, 180] # 소스통 트레이 위에서 뒤집기
sauce_move = [[802.11, 276.99, 208.04, 17.15, 91.43, 92.42], [774.53, 266.42, 208.95, 17.04, 91.6, 92.3], [790.36, 211.68, 206.17, 16.66, 91.68, 92.15]] # 소스 뿌리기

drink_home = [223.52, -177.16, 90.54, 55.78, -96.52, -86.74] # 음료 잡기 준비
drink_pick = [201.34, -271.24, 69.21, 55.78, -96.52, -86.74] # 음료 잡기
drink_middle = [422.34, -233.62, 229.59, 86.51, -90.51, -88.66] # 음료 옮기기 중간
drink_ready = [881.73, 75.51, 127.47, 176.65, -92.08, -90.80] # 음료 내리기

paper_pick_up = [677.38, 185.46, 256.88, 14.22, 165.4, 11.45] # 종이컵 쟁반 전후
paper_pick = [754.25, 201.00, 59.27, 13.88, 167.11, 11.34]  # 종이컵 쟁반위
paper_place = [215.13, 193.69, 76.71, 35.03, 180, 2.10]# 종이컵 초기, 마지막 위치 (추후 종이들고 조정)


class RobotControllerNode:
    def __init__(self, node):
        self.node = node

        # 두산 로봇 API 지연 임포트 및 바인딩
        self.init_robot_api(node)

        self.force_sensor_pub = self.node.create_publisher(Bool, 'robot_force_sensor', 10)   # 외력 퍼블리시
        self.tool_force_client = self.node.create_client(GetToolForce, 'aux_control/get_tool_force')
        self.pending_tool_force_future = None

        self.force_monitor_timer = self.node.create_timer(0.1, self.publish_realtime_force)    # 외력을 계속 계산
        self.FORCE_THRESHOLD = 35.0 # 외력 35이상 발생 시 비상정지
        self.is_emergency = False

        self.current_goal_handle = None

        self.move_fry_done = False
        self.fry_setting = False

        self.srv = self.node.create_service(
            EmergencyStop, 
            '/emergency_stop_robot_controller', 
            self.emergency_stop_callback  
        )

        # 액션 서버 가동
        self._action_server = ActionServer(
            self.node,
            BurgerTask,
            '/burger_task',
            self.execute_callback
        )
        self.get_logger().info('🤖 두산 로봇 실구동 제어 액션 서버가 가동되었습니다.')

        self.current_tool = None
        
        # 시작 시 로봇 홈 위치로 초기화 이동
        self.get_logger().info(f"초기 조인트 위치 이동중...: {x0}")
        self.movej(x0, vel=50, acc=100)
        self.release()

    def paper_grip(self):
        self.movel(paper_pick_up, vel=VELOCITY, acc=ACC)
        self.movel(paper_pick, vel=VELOCITY, acc=ACC)
        self.grip()
        self.movel(paper_pick_up, vel=VELOCITY, acc=ACC)
        self.movel(paper_place, vel=VELOCITY, acc=ACC)
        self.release()

    def shake_oil(self):
        self.move_periodic(amp =[10,0,0,0,0,0], period=0.5, atime=0.2, repeat=3, ref=self.DR_TOOL)

    def shake_sauce(self):
        self.movel(sauce_move[0], vel=VELOCITY, acc=ACC)
        self.movel(sauce_move[1], vel=VELOCITY, acc=ACC)
        self.movel(sauce_move[2], vel=VELOCITY, acc=ACC)

    def emergency_stop_callback(self, request, response):
        self.is_emergency = request.emergency_state
        reason = request.reason

        if self.is_emergency is True:
            self.get_logger().error(f"🛑 비상정지 시스템 가동: {reason}")
            self.get_logger().error("⚠️ 로봇이 잠금 상태로 전환됩니다. 모든 모션 진입이 강제 차단됩니다.")
            self.drl_script_pause()

            if self.current_goal_handle and self.current_goal_handle.is_active:
                self.get_logger().warn("💥 [컨트롤러 방어] 현재 수행 중인 액션 목표를 중단(Abort) 처리합니다.")
                self.current_goal_handle.abort()

            response.success = True
            response.message = "비상 정지 시스템 가동"
            return response

        else:
            self.get_logger().warn(f"🔓 비상정지 시스템 해제: {reason}")
            self.get_logger().info("🔄 비상 상황이 종료되어 로봇 구동을 재개할 준비가 완료되었습니다.")
            self.drl_script_resume()
            response.success = True
            response.message = "비상 정지 시스템 해제"
            return response

    def publish_realtime_force(self):
        if not self.tool_force_client.service_is_ready():
            return

        request = GetToolForce.Request()
        request.ref = self.DR_BASE
        self.pending_tool_force_future = self.tool_force_client.call_async(request)
        self.pending_tool_force_future.add_done_callback(self.handle_tool_force_response)

    def handle_tool_force_response(self, future):
        try:
            result = future.result()
        except Exception as e:
            self.get_logger().warn(f"get_tool_force service call failed: {e}")
            return

        if result is None or not result.success:
            return

        fx, fy, fz = result.tool_force[0], result.tool_force[1], result.tool_force[2]
        force_magnitude = sqrt(fx**2 + fy**2 + fz**2)

        msg_sensor = Bool()
        msg_sensor.data = force_magnitude >= self.FORCE_THRESHOLD
        if msg_sensor.data:
            self.get_logger().error(f"🚨 [하드웨어 알람] 실시간 임계값 초과 힘 감지! 계측값: {force_magnitude:.2f} N")
        self.force_sensor_pub.publish(msg_sensor)

    def get_logger(self):
        return self.node.get_logger()

    def get_clock(self):
        return self.node.get_clock()

    def init_robot_api(self, dsr_node):
        """두산 API를 노드 내부 스코프로 안전하게 바인딩"""
        setattr(DR_init, "__dsr__id", ROBOT_ID)
        setattr(DR_init, "__dsr__model", ROBOT_MODEL)
        setattr(DR_init, "__dsr__node", dsr_node)

        try:
            import DSR_ROBOT2 as dsr
            
            # 외부 제어 함수 매핑
            self.set_digital_output = dsr.set_digital_output
            self.get_digital_input = dsr.get_digital_input
            self.movej = dsr.movej
            self.movel = dsr.movel
            self.move_periodic = dsr.move_periodic
            self.set_tool = dsr.set_tool
            self.set_tcp = dsr.set_tcp
            
            self.DR_TOOL = dsr.DR_TOOL
            self.DR_BASE = dsr.DR_BASE
            self.DR_MV_MOD_REL = dsr.DR_MV_MOD_REL
            self.get_tool_force = dsr.get_tool_force
            self.drl_script_pause = dsr.drl_script_pause
            self.drl_script_resume = dsr.drl_script_resume
            
            # 그리퍼 초기 설정
            self.set_tool("Tool Weight_2FG")
            self.set_tcp("2FG_TCP")

            
        except ImportError as e:
            self.get_logger().error(f"Error importing DSR_ROBOT2 : {e}")
            raise
        
    def node_sleep(self, seconds: float):
        """ROS 2 스레드를 방해하지 않는 안전한 대기 함수"""
        self.get_clock().sleep_for(rclpy.duration.Duration(seconds=seconds))

    def wait_digital_input(self, sig_num):
        while not self.get_digital_input(sig_num):
            self.node_sleep(0.1)
            self.get_logger().info(f"Wait for digital input: {sig_num}", throttle_duration_sec=2.0)

    def release(self):  # 그리퍼놓기
        print("set for digital output 0 1 0 for release")
        self.set_digital_output(2, ON)
        self.set_digital_output(1, OFF)
        self.set_digital_output(3, OFF)
        self.node_sleep(1)

    def grip(self): # 그리퍼 잡기
        print("set for digital output 1 0 0 for grip")
        self.set_digital_output(1, ON)
        self.set_digital_output(2, OFF)
        self.set_digital_output(3, OFF)
        self.node_sleep(1)

    def source_grip(self): # 소스통 잡기
        print("set for digital output 0 0 1 for grip")
        self.set_digital_output(3, ON)
        self.set_digital_output(1, OFF)
        self.set_digital_output(2, OFF)
        self.node_sleep(1)

    def grip_soft(self): # 소스통 누르기, 음료 잡기
        print("set for digital output 1 0 1 for grip")
        self.set_digital_output(3, ON)
        self.set_digital_output(1, ON)
        self.set_digital_output(2, OFF)
        self.node_sleep(1)

    def release_wait(self):  # 소스, 음료용 그리퍼놓기
        print("set for digital output 0 1 0 for release")
        self.set_digital_output(2, ON)
        self.set_digital_output(1, OFF)
        self.set_digital_output(3, OFF)
        self.node_sleep(1)

    def shake(self):
        self.move_periodic(amp=[0,0,-10,0,0,0], period=0.5, atime=0.2, repeat=3, ref=self.DR_TOOL)

    # --- [도구 장착 제어] ---
    def grip_tool(self):    # 옮기기 도구 잡기
        self.movel(tool_after, vel=VELOCITY, acc=ACC)
        self.movel(tool_home[0], vel=VELOCITY, acc=ACC)
        self.movel(tool_home[1], vel=VELOCITY, acc=ACC)
        self.grip()
        self.movel(tool_after, vel=VELOCITY, acc=ACC)
        self.current_tool = "tool"

    def release_tool(self): # 옮기기 도구 놓기
        self.movel(tool_after, vel=VELOCITY, acc=ACC)
        self.movel([-30, 0, 0, 0, 0, 0], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel([0, 0, 230, 0, 0, 0], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(tool_home[1], vel=VELOCITY, acc=ACC)
        self.release()
        self.movel(tool_after, vel=VELOCITY, acc=ACC)
        self.current_tool = None

    def grip_flip_tool(self):    # 뒤집기 도구 잡기
        self.movel(tool_after, vel=VELOCITY, acc=ACC)
        self.movel(flip_tool_home[0], vel=VELOCITY, acc=ACC)
        self.movel(flip_tool_home[1], vel=VELOCITY, acc=ACC)
        self.grip()
        self.movel(flip_tool_after, vel=VELOCITY, acc=ACC)
        self.current_tool = "flip_tool"

    def release_flip_tool(self):    # 뒤집기 도구 놓기
        self.movel(flip_tool_after, vel=VELOCITY, acc=ACC)
        self.movel(flip_tool_home[0], vel=VELOCITY, acc=ACC)
        self.movel(flip_tool_home[1], vel=VELOCITY, acc=ACC)
        self.release()
        self.movel(flip_tool_after, vel=VELOCITY, acc=ACC)
        self.current_tool = None

    # --- [재료 공급 및 가공 모션 시퀀스] ---
    def ingredients_grip(self):
        self.movel(ingredient_ready[0], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(ingredient_ready[1], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(ingredient_ready[2], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)  
        self.movel(ingredient_ready[3], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(ingredient_ready[4], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)

    def ingredients_setting(self):
        self.movel(plating_up, vel=20, acc=30)
        self.movel(plating_middle, vel=VELOCITY, acc=ACC)
        self.movel(plating_down, vel=VELOCITY, acc=ACC)
        self.shake()

    def rev_ingredients_setting(self):
        self.movel(plating_up, vel=VELOCITY, acc=ACC)

    def ingredients_to_burger(self):
        self.movel(up_gradient, vel=VELOCITY, acc=ACC)
        self.shake()
        self.ingredients_setting()
        self.node_sleep(1)
        self.rev_ingredients_setting()
        self.movel(up_gradient, vel=20, acc=30)

    def patty_to_grill(self):
        self.movel(up_gradient, vel=VELOCITY, acc=ACC)
        self.shake()
        self.movel(grill_up, vel=VELOCITY, acc=ACC)
        self.movel(grill_down, vel=VELOCITY, acc=ACC)
        self.shake()
        self.movel(grill_move, vel=VELOCITY, acc=ACC)
        self.movel(tool_after, vel=VELOCITY, acc=ACC)

    def flip_patty(self):
        self.movel(flip_home, vel=VELOCITY, acc=ACC)
        self.movel(flip_ready[0], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(flip_ready[1], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(flip_final_ready, vel=VELOCITY, acc=ACC)
        self.movel([0, 25, 0, 0, 0, 0], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movej([0, 0, 0, 0, 0, flip_angle], vel=100, acc=150, mod=self.DR_MV_MOD_REL)
        self.node_sleep(2)
        self.movel([30, 0, 0, 0, 0, 0], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)

    def pick_patty(self):
        self.movel(grill_up, vel=VELOCITY, acc=ACC)
        self.movel(patty_grip_home, vel=VELOCITY, acc=ACC)
        self.movel(patty_ready[0], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(patty_ready[1], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(patty_ready[2], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(grill_up, vel=VELOCITY, acc=ACC)
        self.shake()
        self.ingredients_setting()
        self.node_sleep(1)
        self.rev_ingredients_setting()
        self.movel(up_gradient, vel=20, acc=30)

    def fry_in(self):
        self.movel(fry_home, vel=VELOCITY, acc=ACC)
        self.movel(fry_grip, vel=VELOCITY, acc=ACC)
        self.grip()
        self.movel(fry_pongdang[0], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(fry_pongdang[1], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(fry_pongdang[2], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.release()
        self.movel(fry_home, vel=VELOCITY, acc=ACC)

    def fry_out(self):
        self.movej(x0, vel=50, acc=100)
        self.movel(fry_grip, vel=VELOCITY, acc=ACC)
        self.movel(fry_pongdang[1], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.grip()
        self.movel(fry_pongdang[0], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.shake_oil()
        self.movel(fry_pongdang[3], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(fry_grip, vel=VELOCITY, acc=ACC)
        self.release()
        self.movel(fry_home, vel=VELOCITY, acc=ACC)

    def fry_ingredients_setting(self):
        self.movel(fry_pongdang[0], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(fry_pongdang[3], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(fry_plating_up, vel=VELOCITY, acc=ACC)
        self.movej([0, 0, 0, 0, 0, -140], vel = 100, acc=150, mod=self.DR_MV_MOD_REL) # 튀김 트레이에 붓기
        self.movel(fry_plating_up, vel=VELOCITY, acc=ACC)
        self.movel([-200, 0, 0, 0, 0, 0], vel=VELOCITY, acc=ACC, ref=self.DR_TOOL)
        self.movel(fry_back_home, vel=VELOCITY, acc=ACC)
        self.movel(fry_grip, vel=VELOCITY, acc=ACC)
        self.release()
        self.movel(fry_home, vel=VELOCITY, acc=ACC)
    
    def sauce_setting(self):
        self.movel(sauce_home, vel=VELOCITY, acc=ACC)
        self.movel(sauce_pick, vel=VELOCITY, acc=ACC)
        self.source_grip()
        self.movel(sauce_ready, vel=VELOCITY, acc=ACC)
        self.movel(sauce_final_ready, vel=VELOCITY, acc=ACC)
        self.movej(sauce_turn, vel=VELOCITY, acc=ACC, mod=self.DR_MV_MOD_REL)
        self.grip_soft()
        self.shake_sauce()
        self.source_grip()
        self.movel(flip_tool_after, vel=50, acc=100)
        self.movel(sauce_pick, vel=VELOCITY, acc=ACC)
        self.release_wait()
        self.movel(sauce_home, vel=VELOCITY, acc=ACC)
        self.movej(x0, vel=50, acc=100)

    def drink_setting(self):
        self.movel(drink_home, vel=VELOCITY, acc=ACC)
        self.movel(drink_pick, vel=VELOCITY, acc=ACC)
        self.grip_soft()
        self.movel(drink_middle, vel=VELOCITY, acc=ACC)
        self.movel(drink_ready, vel=VELOCITY, acc=ACC)
        self.movel([0, -50, 0, 0, 0, 0], vel=VELOCITY, acc=ACC ,ref=self.DR_TOOL)
        self.release_wait()
        self.movel([0, 0, -50, 0, 0, 0], vel=VELOCITY, acc=ACC ,ref=self.DR_TOOL)
        self.movel(drink_middle, vel=VELOCITY, acc=ACC)

    # --- [상위 매니저 명령 수신 및 조율부] ---
    def execute_callback(self, goal_handle):
        self.current_goal_handle = goal_handle

        order_id = goal_handle.request.order_id
        task = goal_handle.request.task_type        # 예: "PICK", "FLIP", "FRY" 등
        item = goal_handle.request.ingredient       # 예: "patty", "bun_top", "topping1" 등
        dest = goal_handle.request.destination

        self.get_logger().info(f'📥 [명령 접수] 주문:{order_id} | Task:{task} | 대상:{item}')

        if self.is_emergency:
            self.get_logger().error("❌ 현재 비상 정지 상태이므로 명령을 수행할 수 없습니다.")
            goal_handle.abort()
            result = BurgerTask.Result()
            result.success = False
            return result

        try:
            if task == "튀김조리":
                if self.current_tool is not None:
                    if self.current_tool == "tool":
                        self.release_tool()
                    elif self.current_tool == "flip_tool":
                        self.release_flip_tool() 
                self.fry_in()
                self.movej(x0, vel=50, acc=100)
                print(f"위치 초기화: {x0}") 

            # 1. 재료 조리 및 운반 태스크 매핑
            elif task == "재료 옮기기":
                if self.current_tool != "tool":
                    if self.current_tool is None:
                        self.grip_tool()
                    elif self.current_tool == "flip_tool":
                        self.release_flip_tool() 
                        self.grip_tool()
                # 대상 아이템 홈 위치 찾기
                if item == "패티":  # 그릴 위 패티를 트레이로 옮기기
                    self.pick_patty()
                elif item == "상단 빵":
                    self.movel(bun_top_home, vel=VELOCITY, acc=ACC)
                    self.ingredients_grip()
                    self.ingredients_to_burger()
                    self.release_tool()
                    self.movej(x0, vel=50, acc=100)
                    if self.move_fry_done is True:
                        self.fry_setting = False
                    else: 
                        self.fry_setting = True
                elif item == "토핑":
                    self.movel(topping1_home, vel=VELOCITY, acc=ACC)
                    self.ingredients_grip()
                    self.ingredients_to_burger()
                elif item == "치즈":
                    self.movel(topping2_home, vel=VELOCITY, acc=ACC)
                    self.ingredients_grip()
                    self.ingredients_to_burger()
                elif item == "하단 빵":
                    self.movel(bun_bottom_home, vel=VELOCITY, acc=ACC)
                    self.ingredients_grip()
                    self.ingredients_to_burger()
                else:
                    self.get_logger().warn(f"미정의된 재료입니다: {item}")

            # 2. 패티 뒤집기 태스크 매핑
            elif task == "패티뒤집기":
                if self.current_tool != "flip_tool":
                    if self.current_tool is None:
                        self.grip_flip_tool()
                    elif self.current_tool == "tool":
                        self.release_tool() 
                        self.grip_flip_tool()
                self.flip_patty()
                self.release_flip_tool() 

            elif task == "패티조리":
                if self.current_tool != "tool":
                    if self.current_tool is None:
                        self.grip_tool()
                    elif self.current_tool == "flip_tool":
                        self.release_flip_tool() 
                        self.grip_tool()
                self.movel(patty_home, vel=VELOCITY, acc=ACC)
                self.ingredients_grip()
                self.patty_to_grill()

            elif task == "튀김옮기기":
                if self.current_tool is not None:
                    if self.current_tool == "tool":
                        self.release_tool()
                    elif self.current_tool == "flip_tool":
                        self.release_flip_tool() 
                self.fry_out()
                self.movej(x0, vel=50, acc=100)
                self.move_fry_done = True

                if self.fry_setting is True:
                    self.movel(fry_grip, vel=VELOCITY, acc=ACC)
                    self.grip()
                    self.fry_ingredients_setting()
                    self.movej(x0, vel=50, acc=100)
            
            elif (task == "튀김세팅" and self.fry_setting == False):
                if self.current_tool is not None:
                    if self.current_tool == "tool":
                        self.release_tool()
                    elif self.current_tool == "flip_tool":
                        self.release_flip_tool() 

                self.movel(fry_home, vel=VELOCITY, acc=ACC)
                self.movel(fry_grip, vel=VELOCITY, acc=ACC)
                self.grip()
                self.fry_ingredients_setting()
                self.get_logger().info(f"초기 조인트 위치 이동중...: {x0}")
                self.movej(x0, vel=50, acc=100)
            
            elif task == "소스뿌리기":
                if self.current_tool is not None:
                    if self.current_tool == "tool":
                        self.release_tool()
                    elif self.current_tool == "flip_tool":
                        self.release_flip_tool() 
                self.sauce_setting()
            
            elif task == "음료수 옮기기":
                if self.current_tool is not None:
                    if self.current_tool == "tool":
                        self.release_tool()
                    elif self.current_tool == "flip_tool":
                        self.release_flip_tool() 
                self.drink_setting()
            
            elif task == "종이빼기":
                if self.current_tool is not None:
                    if self.current_tool == "tool":
                        self.release_tool()
                    elif self.current_tool == "flip_tool":
                        self.release_flip_tool() 
                self.paper_grip()
                self.movej(x0, vel=50, acc=100)
            
            else:
                self.get_logger().error(f"알 수 없는 Task 요청입니다: {task}")
                goal_handle.abort()
                result = BurgerTask.Result()
                result.success = False
                return result
            
            if self.is_emergency or not goal_handle.is_active:
                self.get_logger().warn("🛑 작업 수행 중 비상정지가 인지되어 결과를 성공으로 전송하지 않습니다.")
                result = BurgerTask.Result()
                result.success = False
                return result

            # 구동 성공 후 상위 매니저 노드로 결과 리턴
            goal_handle.succeed()
            result = BurgerTask.Result()
            result.success = True
            self.get_logger().info(f'📤 [완료 통보] 주문 {order_id}의 {task} 작업 성공!')
            
            # 사용이 끝난 핸들 초기화
            self.current_goal_handle = None
            return result

        except Exception as e:
            # 🛑 비상 정지(abort)로 인해 주행 중 예외가 터지면 이곳으로 들어와 스레드가 안전하게 종료됩니다.
            self.get_logger().error(f"로봇 구동 중 중단 또는 예외 발생: {e}")
            if goal_handle.is_active:
                goal_handle.abort()
            self.current_goal_handle = None
            result = BurgerTask.Result()
            result.success = False
            return result

def main(args=None):
    rclpy.init(args=args)

    node = rclpy.create_node('robot_controller_node', namespace=ROBOT_ID)
    controller = RobotControllerNode(node)
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()