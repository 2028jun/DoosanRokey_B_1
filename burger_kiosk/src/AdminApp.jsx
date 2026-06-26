import React, { useState, useEffect } from 'react';
import * as ROSLIB from 'roslib';
import * as ROS3D from 'ros3d';

function AdminApp() {
  const [ros, setRos] = useState(null);
  const [robotStatus, setRobotStatus] = useState("연결 확인 중...");
  const [isEmergency, setIsEmergency] = useState(false);
  const [inventoryStatus, setInventoryStatus] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  
  // [추가] 경고창 상태 관리를 위한 state
  const [isAlert, setIsAlert] = useState(false);

  useEffect(() => {
    // 1. ROS 연결
    // 로봇 연결 시 localhost 부분을 ws://192.168.1.100:9090 와 같이 로봇 IP 사용
    const rosInstance = new ROSLIB.Ros({ url: 'ws://localhost:9090' });
    setRos(rosInstance);

    rosInstance.on('connection', () => setRobotStatus('ROS 2 연결됨: 상태 수신 대기'));
    rosInstance.on('error', () => setRobotStatus('ROS 2 연결 오류'));
    rosInstance.on('close', () => setRobotStatus('ROS 2 연결 종료'));

    // 2. 상태 토픽 구독
    const statusTopic = new ROSLIB.Topic({
      ros: rosInstance,
        name: '/robot_status_topic',
        messageType: 'std_msgs/msg/String'
    });

    statusTopic.subscribe(msg => {
        setRobotStatus(msg.data);
        if (msg.data.includes("외력")) {
        setIsAlert(true);
        setIsEmergency(true);
        }
    });

    // 3. 3D 뷰어 지연 로딩
    const timer = setTimeout(() => {
        const rvizDiv = document.getElementById('rviz');
        if (rvizDiv && window.ROS3D) {
        try {
            rvizDiv.innerHTML = '';
            const viewer = new window.ROS3D.Viewer({
            divID: 'rviz',
            width: 800,
            height: 400,
            antialias: true,
            background: '#000000'
            });
            new window.ROS3D.TfClient({ ros: rosInstance, fixedFrame: 'map' });
            setIsLoading(false);
        } catch (err) {
            console.log("3D 뷰어 로드 대기 중...");
        }
        }
    }, 1000);

    // 4. 정리 함수
    return () => {
        clearTimeout(timer);
        statusTopic.unsubscribe();
        rosInstance.close();
        const rvizDiv = document.getElementById('rviz');
        if (rvizDiv) rvizDiv.innerHTML = '';
    };
}, []);

  const sendCommand = (topicName, msgData, statusText) => {
    if (!ros) {
      setRobotStatus('ROS 2 연결 전: 관리자 명령을 보낼 수 없습니다.');
      return false;
    }

    // 💡 브라우저 window 객체에 등록된 전역 ROSLIB을 안전하게 가로챕니다.
    // HTML 스크립트 기반 로드와 npm 모듈 꼬임 문제를 동시에 해결하는 마법의 가교 코드입니다.
    const ROSLIB_ENV = window.ROSLIB || require('roslib'); 

    const topic = new ROSLIB_ENV.Topic({ ros, name: topicName, messageType: 'std_msgs/msg/Bool' });
    topic.publish(new ROSLIB_ENV.Message({ data: msgData })); // ⭕ 에러 완벽 해결
    
    setRobotStatus(statusText);
    return true;
  };

  // [추가] 조리 이어가기 핸들러
  const handleResume = () => {
    setIsAlert(false);
    setIsEmergency(false);
    sendCommand('/emergency_stop', false, '비상 정지 해제 요청 전송: 안전 확인 대기 중');
  };

  const handleEmergencyToggle = () => {
    const nextEmergencyState = !isEmergency;
    const statusText = nextEmergencyState
      ? '🚨 비상 정지 요청 전송: 조리 매니저 응답 대기 중'
      : '비상 정지 해제 요청 전송: 안전 확인 대기 중';

    // 화면 상태는 즉시 갱신하고, ROS 전송 실패는 상태 문구로 별도 표시합니다.
    setIsEmergency(nextEmergencyState);
    sendCommand('/emergency_stop', nextEmergencyState, statusText);
  };

  const handleInventoryToggle = () => {
    const nextInventoryState = !inventoryStatus;
    const statusText = nextInventoryState
      ? '📦 재료 부족 신호 전송: 조리 대기 전환 중'
      : '📦 재료 보충 완료 신호 전송: 조리 재개 준비 중';

    setInventoryStatus(nextInventoryState);
    sendCommand('/inventory_status', nextInventoryState, statusText);
  };

  return (
    <div style={{ padding: '20px', backgroundColor: '#14110b', color: '#fff', minHeight: '100vh', position: 'relative' }}>
      
      {/* [추가] 경고창 오버레이 (isAlert가 true일 때만 표시) */}
      {isAlert && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
          backgroundColor: 'rgba(255, 0, 0, 0.9)', zIndex: 9999,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'
        }}>
          <h1 style={{ fontSize: '60px', marginBottom: '20px' }}>⚠️ 외력 감지: 비상 정지!</h1>
          <button 
            onClick={handleResume}
            style={{ 
              padding: '20px 40px', fontSize: '24px', borderRadius: '15px', 
              border: 'none', cursor: 'pointer', backgroundColor: '#fff', color: '#ff0000', fontWeight: 'bold'
            }}
          >
            ▶️ 조리 재개
          </button>
        </div>
      )}

      <h1>🛠️ 관리자 대시보드</h1>
      
      <div style={{ background: '#2a2215', padding: '20px', borderRadius: '10px', marginBottom: '20px' }}>
        <h3>현재 상태: {robotStatus}</h3>
      </div>

      <div style={{ display: 'flex', gap: '20px' }}>
        <button 
          onClick={handleEmergencyToggle}
          style={{ padding: '20px', backgroundColor: isEmergency ? '#ff0000' : '#444', color: 'white', border: 'none', borderRadius: '10px' }}
        >
          {isEmergency ? "🚨 긴급 정지 활성화 (정지 중)" : "🚨 긴급 정지 버튼"}
        </button>

        <button 
          onClick={handleInventoryToggle}
          style={{ padding: '20px', backgroundColor: inventoryStatus ? '#e67e22' : '#2ecc71', border: 'none', borderRadius: '10px' }}
        >
          {inventoryStatus ? "재료 부족 ON (대기)" : "재료 정상 OFF (동작)"}
        </button>
      </div>

      <div style={{ marginTop: '30px', textAlign: 'center' }}>
        {isLoading && <p style={{ color: '#ffb703' }}>로봇 모델을 불러오는 중입니다...</p>}
        <div id="rviz" style={{ width: '800px', height: '400px', margin: '0 auto', background: '#000', display: isLoading ? 'none' : 'block' }}></div>
      </div>
    </div>
  );
}

export default AdminApp;
