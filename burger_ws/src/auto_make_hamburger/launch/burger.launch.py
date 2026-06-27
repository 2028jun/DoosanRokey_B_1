import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, LogInfo
from launch_ros.actions import Node

def generate_launch_description():
    # 💡 질문자님의 리액트 프로젝트 최상위 폴더 경로 (package.json이 있는 폴더)
    # 실제 본인의 우분투 PC 경로에 맞게 수정하세요. (예: '/home/junhyeok/react-kiosk-app')

    return LaunchDescription([
        LogInfo(msg="🍔 [Auto Make Hamburger] 시스템 일괄 기동을 시작합니다..."),

        # 3. 패키지 내부의 핵심 ROS2 백엔드 노드들 동시 실행
        # (제공해주하신 setup.py의 console_scripts 이름을 기준으로 등록했습니다)
        
        # 요리 매니저 노드
        Node(
            package='auto_make_hamburger',       
            executable='cooking_manager_node', 
            name='cooking_manager',
            output='screen'
        ),

        # 로봇 컨트롤러 노드
        Node(
            package='auto_make_hamburger',       
            executable='robot_controller_node', 
            name='robot_controller',
            output='screen'
        ),

        # 안전 관리 노드 (비상정지 등)
        Node(
            package='auto_make_hamburger',       
            executable='safety_manager_node', 
            name='safety_manager',
            output='screen'
        ),

        Node(
            package='auto_make_hamburger',       
            executable='ui_node', 
            name='ui',
            output='screen'
        ),
        
        # 💡 만약 dummy_robot_node나 ui_node도 상시로 같이 켜져야 한다면 
        # 아래에 Node() 형식으로 똑같이 추가해주시면 됩니다.
    ])