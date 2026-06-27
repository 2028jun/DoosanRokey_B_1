import time
import rclpy
import DR_init
from math import sqrt

# for single robot
ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"
VELOCITY, ACC = 125, 150

DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL

OFF, ON = 0, 1

def main(args=None):
    rclpy.init(args=args)
    node = rclpy.create_node("rokey_force_control", namespace=ROBOT_ID)

    DR_init.__dsr__node = node

    try:
        from DSR_ROBOT2 import (
            set_digital_output,
            get_digital_input,
            release_compliance_ctrl,
            release_force,
            get_current_posx,
            task_compliance_ctrl,
            set_desired_force,
            set_tool,
            set_tcp,
            movej,
            amovel,
            movel,
            get_tool_force,
            move_periodic,
            DR_MV_MOD_REL,
            DR_FC_MOD_ABS,
            DR_BASE,
            DR_TOOL
        )

        from DR_common2 import posx, posj

    except ImportError as e:
        print(f"Error importing DSR_ROBOT2 : {e}")
        return
    
    tool_home = [[367.96, -225.74, 481.1, 89.43, -91.43, -177.67], [365.46, -314.89, 477.73, 89.26, -91.58, -177.44]]   # 옮기기 도구 잡기
    tool_after = [364.46, -75.59, 503.22, 89.44, -91.65, -177.26]   # 옮기는 도구 잡은 후 뒤로 빼기
    patty_home = [362.82, -90.02, 221.2, 89.18, -91.65, -178.13]     # 패티 위치 이동
    bun_top_home = [524.54, -81.59, 319.72, 89.59, -91.20, -177.89] # 상단 빵 위치 이동
    topping1_home = [527.45, -82.2, 221.2, 89.7, -91.11, -178.04]   # 토핑1 위치 이동
    topping2_home = [340.34, -88.37, 411.72, 89.84, -91.29, -177.99]    # 토핑2 위치 이동
    bun_bottom_home = [343.35, -89.25, 309.89, 89.95, -91.21, -178.17 ] # 하단 빵 위치 이동
    up_gradient = [394.8, -16.99, 528.09, 94.06, -62.64, -179.2]      # 재료 잡은 후 기울여서 안쪽으로 넣기

    grill_move = [365.05, 90.01, 479.81, 130.08, -89.88, -174.96]   # 그릴에 안걸리게 위치 이동 
    grill_up = [528.39, -44.42, 460.39, 146.52, -77.65, 177.82]         # 그릴 위로 이동
    grill_down = [632.34, -124.60, 236.11, 148.00, -116.67, -178.75]    # 패티 떨어 뜨리기
    flip_tool_home = [[542.58, -268.43, 379.72, 89.15, -91.45, -177.98], [544.3, -335.39, 376.47, 88.55, -91.56, -178.04]]  # 뒤집개 도구 잡기
    flip_tool_after = [624.54, 13.24, 443.65, 129.20, -94.28, -173.54]     # 뒤집개 도구 잡고 빼기
    flip_home = [639.0, -144.81, 67.07, 151.86, -101.66, -178.25]   # 뒤집을 장소로 이동

    flip_ready = [[18, 0, 0, 0, 0, 0], [0, 0, 120, 0, 0, 0]]    # 패티 도구위에 올리기
    flip_final_ready = [749.13, -200.46, 76.69, 151.77, -95.27, -178.07]   # 뒤집기 전 수평 맞추기

    plating_up = [572.9, 36.28, 550.34, 38.12,  72.86, -1.41]   # 트레이 위로 이동
    plating_middle = [584.55, 54.14, 448.74, 38.12, 73.42, -1.27]   # 트레이 중간 위치
    plating_down = [591.95, 51.27, 266.46, 36.98, 103.66, 0.43] # 트레이 아래로 내려서 재료 넣기

    patty_ready = [[25, 0, 0, 0, 0, 0], [0, 0, 130, 0, 0, 0], [-25, 0, 0, 0, 0, 0]] # 패티를 그릴 위에서 잡기
    patty_grip_home = [577.26, -81.14, 161.72, 145.45, -90.77, -179.16] # 패티 잡기 위해 그릴로 이동

    ingredient_ready = [[0, 0, 90, 0, 0, 0], [20, 0, 0, 0, 0, 0], [0, 0, 125, 0, 0, 0], [-20, 0, 0, 0, 0, 0], [0, 0, -220, 0, 0, 0]]
    # 칸에서 재료 잡기
  
    fry_home = [453.73, 327.32, 255.87, 85.81, 88.06, 1.86] # 튀김 잡기 준비
    fry_grip = [456.94, 395.29, 257.77, 85.97, 87.97, 1.78] # 튀김 잡기
    fry_pongdang = [[-120, 0, 0, 0, 0, 0], [0, 0, 160, 0, 0, 0], [120, 0, 0, 0, 0, 0]]  # 튀김망 튀김기에 넣기
    fry_out_move = [0, 0, -160, 0, 0, 0]   # 튀김망에서 튀김기 뒤로 뺴기
    flip_angle = 180    # 뒤집는 각도

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
    paper_pick = [742.57, 184.77, 49.09, 11.76, 170.47, -20.14] # 종이컵 쟁반위
    paper_place = [215.13, 193.69, 76.71, 35.03, 180, 2.10]# 종이컵 초기, 마지막 위치 (추후 종이들고 조정)
    x0 = [0, 0, 90, 0, 90, 0]   # 초기화 조인트 각도

    

    def shake():
        move_periodic(amp =[0,0,-10,0,0,0], period=0.5, atime=0.2, repeat=2, ref=DR_TOOL)

    def shake_oil():
        move_periodic(amp =[10,0,0,0,0,0], period=0.5, atime=0.2, repeat=3, ref=DR_TOOL)
    
    def paper_grip():
        movel(paper_pick_up, vel=VELOCITY, acc=ACC)
        movel(paper_pick, vel=VELOCITY, acc=ACC)
        grip()
        movej([1.5, 0, 0, 0, 0, 0], vel=100, acc=150, mod=DR_MV_MOD_REL)
        movej([-1.5, 0, 0, 0, 0, 0], vel=100, acc=150, mod=DR_MV_MOD_REL)
        movej([1.5, 0, 0, 0, 0, 0], vel=100, acc=150, mod=DR_MV_MOD_REL)
        movej([-1.5, 0, 0, 0, 0, 0], vel=100, acc=150, mod=DR_MV_MOD_REL)
        movel(paper_pick_up, vel=VELOCITY, acc=ACC)
        movel(paper_place, vel=VELOCITY, acc=ACC)
        release()

    def shake_sauce():
        movel(sauce_move[0], vel=VELOCITY, acc=ACC)
        movel(sauce_move[1], vel=VELOCITY, acc=ACC)
        movel(sauce_move[2], vel=VELOCITY, acc=ACC)

    
    def wait_digital_input(sig_num):
        while not get_digital_input(sig_num):
            time.sleep(0.5)
            print(f"Wait for digital input: {sig_num}")
            pass
    
    def release():  # 그리퍼놓기
        print("set for digital output 0 1 0 for release")
        set_digital_output(2, ON)
        set_digital_output(1, OFF)
        set_digital_output(3, OFF)
        wait_digital_input(2)

    def grip(): # 그리퍼 잡기
        print("set for digital output 1 0 0 for grip")
        set_digital_output(1, ON)
        set_digital_output(2, OFF)
        set_digital_output(3, OFF)
        wait_digital_input(1)

    def source_grip(): # 소스통 잡기
        print("set for digital output 0 0 1 for grip")
        set_digital_output(3, ON)
        set_digital_output(1, OFF)
        set_digital_output(2, OFF)
        time.sleep(1)

    def grip_soft(): # 소스통 누르기, 음료 잡기
        print("set for digital output 1 0 1 for grip")
        set_digital_output(3, ON)
        set_digital_output(1, ON)
        set_digital_output(2, OFF)
        time.sleep(1)

    def release_wait():  # 소스, 음료용 그리퍼놓기
        print("set for digital output 0 1 0 for release")
        set_digital_output(2, ON)
        set_digital_output(1, OFF)
        set_digital_output(3, OFF)
        time.sleep(1)

    set_tool("Tool Weight_2FG")
    set_tcp("2FG_TCP")

    def grip_tool():    # 옮기기 도구 잡기
        # movel(tool_after, vel=VELOCITY, acc=ACC)
        movel(tool_home[0], vel=VELOCITY, acc=ACC)
        movel(tool_home[1], vel=VELOCITY, acc=ACC)
        grip()
        movel(tool_after, vel=VELOCITY, acc=ACC)

    def release_tool(): # 옮기기 도구 놓기
        movel(tool_after, vel=VELOCITY, acc=ACC)
        movel([-30, 0, 0, 0, 0, 0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel([0, 0, 230, 0, 0, 0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        # movel(tool_home[0], vel=VELOCITY, acc=ACC)
        movel(tool_home[1], vel=VELOCITY, acc=ACC)
        release()
        movel(tool_after, vel=VELOCITY, acc=ACC)



    def grip_flip_tool():   # 뒤집기 도구 잡기
        movel(tool_after, vel=VELOCITY, acc=ACC)
        movel(flip_tool_home[0], vel=VELOCITY, acc=ACC)
        movel(flip_tool_home[1], vel=VELOCITY, acc=ACC)
        grip()
        movel(flip_tool_after, vel=VELOCITY, acc=ACC)

    
    def release_flip_tool():    # 뒤집기 도구 놓기
        movel(flip_tool_after, vel=VELOCITY, acc=ACC)
        movel(flip_tool_home[0], vel=VELOCITY, acc=ACC)
        movel(flip_tool_home[1], vel=VELOCITY, acc=ACC)
        release()
        movel(flip_tool_after, vel=VELOCITY, acc=ACC)

    def flip():    # 패티 뒤집기
        movel(flip_home, vel=VELOCITY, acc=ACC)
        movel(flip_ready[0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(flip_ready[1], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(flip_final_ready, vel=VELOCITY, acc=ACC)
        movej([0, 0, 0, 0, 0, flip_angle], vel = 100, acc=150, mod=DR_MV_MOD_REL)
        time.sleep(2)
        movel([30, 0, 0, 0, 0, 0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)


    def ingredients_setting():  # 재료를 트레이로 옮기기
        movel(plating_up, vel=20, acc=30)
        movel(plating_middle, vel=VELOCITY, acc=ACC)
        movel(plating_down, vel=VELOCITY, acc=ACC)
        shake()

    def rev_ingredients_setting():  # 재료 옮긴 후 복귀
        movel(plating_up, vel=VELOCITY, acc=ACC)

    
    def ingredients_grip():     # 재료를 잡고 위로 올리기
        movel(ingredient_ready[0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(ingredient_ready[1], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(ingredient_ready[2], vel=VELOCITY, acc=ACC, ref=DR_TOOL)  
        movel(ingredient_ready[3], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(ingredient_ready[4], vel=VELOCITY, acc=ACC, ref=DR_TOOL)

    def ingredients_to_burger():    # 재료를 쌓고 복귀
        movel(up_gradient, vel=VELOCITY, acc=ACC)
        shake()
        ingredients_setting()
        time.sleep(1)
        rev_ingredients_setting()
        movel(up_gradient, vel=20, acc=30)
    
    def pattty_to_grill():  # 패티를 그릴 위로 이동
        movel(up_gradient, vel=VELOCITY, acc=ACC)
        shake()
        movel(grill_up, vel=VELOCITY, acc=ACC)
        movel(grill_down, vel=VELOCITY, acc=ACC)
        shake()
        movel(grill_move, vel=VELOCITY, acc=ACC)
        movel(tool_after, vel=VELOCITY, acc=ACC)

    def pick_patty():   # 그릴 위에서 패티 잡거 트레이까지 옮기기
        movel(grill_up, vel=VELOCITY, acc=ACC)
        movel(patty_grip_home, vel=VELOCITY, acc=ACC)
        movel(patty_ready[0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(patty_ready[1], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(patty_ready[2], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(grill_up, vel=VELOCITY, acc=ACC)

        ingredients_setting()
        time.sleep(3)
        rev_ingredients_setting()
        movel(up_gradient, vel=20, acc=30)
    
    def fry_in():
        movel(fry_home, vel=VELOCITY, acc=ACC)
        movel(fry_grip, vel=VELOCITY, acc=ACC)
        grip()
        movel(fry_pongdang[0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(fry_pongdang[1], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(fry_pongdang[2], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        release()
        movel(fry_home, vel=VELOCITY, acc=ACC)

    def fry_out():
        movej(x0, vel=VELOCITY, acc=ACC)
        movel(fry_grip, vel=VELOCITY, acc=ACC)
        movel(fry_pongdang[1], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        grip()
        movel(fry_pongdang[0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        shake_oil()
        movel(fry_out_move, vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        

    def fry_ingredients_setting():
        movel([0, 0, -100, 0, 0, 0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(fry_plating_up, vel=VELOCITY, acc=ACC)
        movej([0, 0, 0, 0, 0, -140], vel = 100, acc=150, mod=DR_MV_MOD_REL)
        movel(fry_plating_up, vel=VELOCITY, acc=ACC)
        movel([-300, 0, 0, 0, 0, 0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(fry_back_home, vel=VELOCITY, acc=ACC)
        movel(fry_grip, vel=VELOCITY, acc=ACC)
        release()
        movel(fry_home, vel=VELOCITY, acc=ACC)

    def sauce_setting():
        movel(sauce_home, vel=VELOCITY, acc=ACC)
        movel(sauce_pick, vel=VELOCITY, acc=ACC)
        source_grip()
        movel(sauce_ready, vel=VELOCITY, acc=ACC)
        movel(sauce_final_ready, vel=VELOCITY, acc=ACC)
        movej(sauce_turn, vel=VELOCITY, acc=ACC, mod=DR_MV_MOD_REL)
        grip_soft()
        shake_sauce()
        source_grip()
        # movel(sauce_ready, vel=VELOCITY, acc=ACC)
        movel(flip_tool_after, vel=50, acc=100)
        movel(sauce_pick, vel=VELOCITY, acc=ACC)
        release_wait()
        movel(sauce_home, vel=VELOCITY, acc=ACC)
        movej(x0, vel=50, acc=100)

    def drink_setting():
        movel(drink_home, vel=VELOCITY, acc=ACC)
        movel(drink_pick, vel=VELOCITY, acc=ACC)
        grip_soft()
        movel(drink_middle, vel=VELOCITY, acc=ACC)
        movel(drink_ready, vel=VELOCITY, acc=ACC)
        movel([0, -50, 0, 0, 0, 0], vel=VELOCITY, acc=ACC ,ref=DR_TOOL)
        release_wait()
        movel([0, 0, -50, 0, 0, 0], vel=VELOCITY, acc=ACC ,ref=DR_TOOL)
        movel(drink_middle, vel=VELOCITY, acc=ACC)
        


    if rclpy.ok():
        # release()

        # # 위치 초기화
        # print(f"Moving to joint position: {x0}")
        

        # fry_in()
        release()
        movej(x0, vel=50, acc=100)
        paper_grip()
        # movej(x0, vel=50, acc=100)
        # print(f"Moving to joint position: {x0}")
        
        # # 도구 잡기
        # grip_tool()

        # # 패티를 그릴 위로 옮기기
        # movel(patty_home, vel=VELOCITY, acc=ACC)
        # ingredients_grip()
        # pattty_to_grill()

        # # 상단 빵 옮기기
        # movel(bun_top_home, vel=VELOCITY, acc=ACC)
        # ingredients_grip()
        # ingredients_to_burger()
        
        # # 토핑1 옮기
        # movel(topping1_home, vel=VELOCITY, acc=ACC)
        # ingredients_grip()
        # ingredients_to_burger()

        # # 패티 뒤집기 
        # release_tool()
        # grip_flip_tool()
        # flip()
        # # release_flip_tool()
        # movel(tool_after, vel=VELOCITY, acc=ACC)
        # # # # 소스통 잡고 뿌리기
        # movel(sauce_ready, vel=VELOCITY, acc=ACC)
        # movel(sauce_final_ready, vel=VELOCITY, acc=ACC)
        # sauce_setting()
        

        # # 도구1 잡기
        # grip_tool()

        # # 토핑2 옮기기
        # movel(topping2_home, vel=VELOCITY, acc=ACC)
        # ingredients_grip()
        # ingredients_to_burger()

        # # 구운 패티 트레이로 옮기기
        # pick_patty()

        # movel(bun_bottom_home, vel=VELOCITY, acc=ACC)
        # ingredients_grip()
        # ingredients_to_burger()

        # release_tool()

        # fry_out()
        # fry_ingredients_setting()

        # movej(x0, vel=VELOCITY, acc=ACC)
        
        # drink_setting()

        # movej(x0, vel=VELOCITY, acc=ACC)

    rclpy.shutdown()

if __name__ == "__main__":
    main()