설치할 것

sudo apt update

sudo apt install -y nodejs npm

burger_kiosk 폴더 내부에서 실행 -> npm install roslib 

sudo apt install ros-humble-rosbridge-suite

ros2 launch rosbridge_server rosbridge_websocket_launch.xml -> react와 ros2 연동

npm run dev -> burger_kiosk 폴더로 들어가서 실행

ros2 run burger_kiosk ui_node
