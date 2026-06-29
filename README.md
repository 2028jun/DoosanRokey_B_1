설치할 것

sudo apt update

sudo apt install -y nodejs npm

burger_kiosk 폴더 내부에서 실행 -> npm install roslib

sudo apt install ros-humble-rosbridge-suite

sudo apt-get install -y ros-humble-tf2-web-republisher

+ burger_kiosk/ros_models 폴더내에 dsr_descriptions2, m0609_rg2_bringup, onrobot_rg_description 링크 파일 생성하기



실행 방법

ros2 launch rosbridge_server rosbridge_websocket_launch.xml -> react와 ros2 연동

ros2 run tf2_web_republisher tf2_web_republisher_node -> rviz 화면 리액트와 연동

npm run dev -> burger_kiosk 폴더로 들어가서 실행, 주소 ctrl + 클릭 -> 사용자용 페이지 / (페이지 주소 뒤에 admin 붙이면 관리자용 페이지)

ros2 launch auto_make_hamburger burger.launch.py -> 로봇 실행 파일
