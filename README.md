설치할 것

sudo apt update

sudo apt install -y nodejs npm

burger_kiosk 폴더 내부에서 실행 -> npm install roslib 

sudo apt install ros-humble-rosbridge-suite


실행 방법

ros2 launch rosbridge_server rosbridge_websocket_launch.xml -> react와 ros2 연동

npm run dev -> burger_kiosk 폴더로 들어가서 실행, 주소 cyrl + 클릭 -> 사용자용 페이지
+ 페이지 주소 뒤에 admin 붙이면 관리자용 페이지 

ros2 run auto_make_hamburger ui_node 

ros2 run auto_make_hamburger cooking_manager_node

로봇과 연결 후

ros2 run auto_make_hamburger robot_controller_node

실행
