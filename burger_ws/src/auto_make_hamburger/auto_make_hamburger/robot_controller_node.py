import time
import rclpy
import DR_init
from math import sqrt

# for single robot
ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"
VELOCITY, ACC = 80, 100

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
    
    tool_home = [[386.47, -211.39, 479.32, 89.12, -91.68, -177.64], [367.32, -319.19, 476.62, 89.23, -91.6, -177.55]]   # 옮기기 도구 잡기
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
    grill_ready = [603.91, -153.03, 162.47, 156.06, -111.68, -179.35]   # 옮기는 도구로 패티 잡을 준비
    grill_pick = [721.63, -197.13, 149.27, 153.35, -109.75, -179.05]    # 옮기는 도구로 패티 잡기(밀어 넣기)
    grill_lift = []
    flip_tool_home = [[542.58, -268.43, 379.72, 89.15, -91.45, -177.98], [544.3, -335.39, 376.47, 88.55, -91.56, -178.04]]  # 뒤집개 도구 잡기
    flip_tool_after = [624.54, 13.24, 443.65, 129.20, -94.28, -173.54]     # 뒤집개 도구 잡고 빼기
    flip_home = [641.48, -140.55, 68.04, 152.68, -101.5, -178.52]   # 뒤집을 장소로 이동

    flip_ready = [[18, 0, 0, 0, 0, 0], [0, 0, 120, 0, 0, 0]]    # 패티 도구위에 올리기
    flip_final_ready = [749.13, -200.46, 76.69, 151.77, -95.27, -178.07]   # 뒤집기 전 수평 맞추기

    plating_middle1 = [818.08, -77.04, 760.67, 170.22, -69.07, 174.2]   # 쭉 뻗어서 이동하는 지점1
    plating_middle2 = [772.88, 215.2, 789.31, 19.29, 67.67, 1.8]    # 쭉 뻗어서 이동하는 지점2
    plating_up = [572.9, 36.28, 550.34, 38.12,  72.86, -1.41]   # 트레이 위로 이동
    plating_down = [619.95, 74.53, 303.15, 38.0, 116.25, -0.29] # 트레이 아래로 내려서 재료 넣기

    patty_ready = [[18, 0, 0, 0, 0, 0], [0, 0, 120, 0, 0, 0]]


    ingredient_ready = [[0, 0, 90, 0, 0, 0], [20, 0, 0, 0, 0, 0], [0, 0, 130, 0, 0, 0], [-20, 0, 0, 0, 0, 0], [0, 0, -220, 0, 0, 0]]
    x0 = [0, 0, 90, 0, 90, 0]

    flip = 180

    #   [359.30, -77.12, 408.17, 89.17, -96.07, -178.79]  
    # [358.08, -53.99, 320.24, 91.1, -75.95, -177.09] 들어올릴 때
    
    def wait_digital_input(sig_num):
        while not get_digital_input(sig_num):
            time.sleep(0.5)
            print(f"Wait for digital input: {sig_num}")
            pass
    
    def release():  # 그리퍼놓기
        print("set for digital output 0 1 for release")
        set_digital_output(2, ON)
        set_digital_output(1, OFF)
        wait_digital_input(2)

    def grip(): # 그리퍼 잡기
        print("set for digital output 1 0 for grip")
        set_digital_output(1, ON)
        set_digital_output(2, OFF)
        wait_digital_input(1)

    set_tool("Tool Weight_2FG")
    set_tcp("2FG_TCP")

    def ingredients_setting():  # 재료를 트레이로 옮기기
        movel(plating_middle1, vel=VELOCITY, acc=ACC)
        movel(plating_middle2, vel=VELOCITY, acc=ACC)
        movel(plating_up, vel=VELOCITY, acc=ACC)
        movel(plating_down, vel=VELOCITY, acc=ACC)

    def rev_ingredients_setting():  # 재료 옮긴 후 복귀
        movel(plating_up, vel=VELOCITY, acc=ACC)
        movel(plating_middle2, vel=VELOCITY, acc=ACC)
        movel(plating_middle1, vel=VELOCITY, acc=ACC)

    
    def ingredients_grip():     # 재료를 선
        movel(ingredient_ready[0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(ingredient_ready[1], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(ingredient_ready[2], vel=VELOCITY, acc=ACC, ref=DR_TOOL)  
        movel(ingredient_ready[3], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(ingredient_ready[4], vel=VELOCITY, acc=ACC, ref=DR_TOOL)


    if rclpy.ok():
        release()

        
        print(f"Moving to joint position: {x0}")
        movej(x0, vel=VELOCITY, acc=ACC)

        movel(tool_home[0], vel=VELOCITY, acc=ACC)
        movel(tool_home[1], vel=VELOCITY, acc=ACC)
        grip()
        movel(tool_after, vel=VELOCITY, acc=ACC)

        movel(patty_home, vel=VELOCITY, acc=ACC)
        ingredients_grip()

        movel(up_gradient, vel=VELOCITY, acc=ACC)
        movel(grill_up, vel=VELOCITY, acc=ACC)
        movel(grill_down, vel=VELOCITY, acc=ACC)
        movel(grill_move, vel=VELOCITY, acc=ACC)

        movel(tool_after, vel=VELOCITY, acc=ACC)

        movel(bun_top_home, vel=VELOCITY, acc=ACC)
        ingredients_grip()

        movel(up_gradient, vel=VELOCITY, acc=ACC)
        ingredients_setting()

        time.sleep(5)

        rev_ingredients_setting()
        movel(up_gradient, vel=VELOCITY, acc=ACC)

        movel(topping1_home, vel=VELOCITY, acc=ACC)
        ingredients_grip()

        movel(up_gradient, vel=VELOCITY, acc=ACC)
        ingredients_setting()

        time.sleep(5)

        rev_ingredients_setting()
        movel(up_gradient, vel=VELOCITY, acc=ACC)

        # 뒤집기 시작
        movel(tool_after, vel=VELOCITY, acc=ACC)
        movel(tool_home[0], vel=VELOCITY, acc=ACC)
        movel(tool_home[1], vel=VELOCITY, acc=ACC)
        release()

        movel(tool_after, vel=VELOCITY, acc=ACC)
        movel(flip_tool_home[0], vel=VELOCITY, acc=ACC)
        movel(flip_tool_home[1], vel=VELOCITY, acc=ACC)
        grip()
        movel(flip_tool_after, vel=VELOCITY, acc=ACC)
        movel(flip_home, vel=VELOCITY, acc=ACC)
        movel(flip_ready[0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movel(flip_ready[1], vel=VELOCITY, acc=ACC, ref=DR_TOOL)

        movel(flip_final_ready, vel=VELOCITY, acc=ACC)

        movej([0, 0, 0, 0, 0, flip], vel = 100, acc=150, mod=DR_MV_MOD_REL)
        time.sleep(2)

        movel([30, 0, 0, 0, 0, 0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)
        movej([0, 0, 0, 0, 0, -flip], vel = 100, acc=150, mod=DR_MV_MOD_REL)
        movel(flip_tool_after, vel=VELOCITY, acc=ACC)
        movel(flip_tool_home[0], vel=VELOCITY, acc=ACC)
        movel(flip_tool_home[1], vel=VELOCITY, acc=ACC)
        release()

        movel(tool_after, vel=VELOCITY, acc=ACC)
        movel(tool_home[0], vel=VELOCITY, acc=ACC)
        movel(tool_home[1], vel=VELOCITY, acc=ACC)
        grip()
        movel(tool_after, vel=VELOCITY, acc=ACC)

        movel(topping2_home, vel=VELOCITY, acc=ACC)
        ingredients_grip()

        movel(up_gradient, vel=VELOCITY, acc=ACC)
        ingredients_setting()

        time.sleep(5)

        rev_ingredients_setting()
        movel(up_gradient, vel=VELOCITY, acc=ACC)




        # movel(bun_bottom_home, vel=VELOCITY, acc=ACC)
        # ingredients_grip()

        # movel(up_gradient, vel=VELOCITY, acc=ACC)
        # ingredients_setting()

        # time.sleep(5)

        # rev_ingredients_setting()
        # movel(up_gradient, vel=VELOCITY, acc=ACC)


        # movel(up_gradient, vel=VELOCITY, acc=ACC)
        # movel(grill_up, vel=VELOCITY, acc=ACC)
        # movel(grill_down, vel=VELOCITY, acc=ACC)

        # movel(flip_ready[0], vel=VELOCITY, acc=ACC, ref=DR_TOOL)



    rclpy.shutdown()


if __name__ == "__main__":
    main()
