import React, { useState, useEffect } from 'react';
import * as ROSLIB from 'roslib';
import * as ROS3D from 'ros3d';

function AdminApp() {
  const [ros, setRos] = useState(null);
  const [robotStatus, setRobotStatus] = useState("연결 확인 중...");
  const [isEmergency, setIsEmergency] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  
  // 경고창 상태 관리를 위한 state
  const [isAlert, setIsAlert] = useState(false);

  useEffect(() => {
    // 1. ROS 연결
    const rosInstance = new ROSLIB.Ros({ url: 'ws://localhost:9090' });
    setRos(rosInstance);

    rosInstance.on('connection', () => setRobotStatus('ROS 2 연결됨: 상태 수신 대기'));
    rosInstance.on('error', () => setRobotStatus('❌ ROS 2 연결 오류: Bridge 서버를 확인하세요.'));
    rosInstance.on('close', () => setRobotStatus('❌ ROS 2 연결 종료'));

    // 2. 상태 토픽 구독
    const statusTopic = new ROSLIB.Topic({
      ros: rosInstance,
      name: '/robot_status_topic',
      messageType: 'std_msgs/msg/String'
    });

    statusTopic.subscribe(msg => {
      setRobotStatus(msg.data);
      // 외력 혹은 비상 정지 문자열이 감지되면 즉시 경고 모드 활성화
      if (msg.data.includes("외력") || msg.data.includes("비상 정지") || msg.data.includes("Emergency")) {
        setIsAlert(true);
        setIsEmergency(true);
      } else if (msg.data.includes("정상") || msg.data.includes("재개")) {
        setIsAlert(false);
        setIsEmergency(false);
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

    const ROSLIB_ENV = window.ROSLIB || require('roslib'); 
    const topic = new ROSLIB_ENV.Topic({ ros, name: topicName, messageType: 'std_msgs/msg/Bool' });
    topic.publish(new ROSLIB_ENV.Message({ data: msgData }));
    
    setRobotStatus(statusText);
    return true;
  };

  // 비상 정지 트리거 (오직 정지만 수행)
  const handleEmergencyStop = () => {
    setIsEmergency(true);
    setIsAlert(true); // 오버레이 경고창 띄우기
    sendCommand('/emergency_stop', true, '🚨 [위험] 관리자 수동 긴급 정지 명령 전송됨!');
  };

  // 조리 이어가기 (위험 해제 상태 전환)
  const handleResume = () => {
    setIsAlert(false);
    setIsEmergency(false);
    sendCommand('/emergency_stop', false, '🔄 시스템 복구: 안전 확인 및 조리 재개 명령 전송 완료');
  };

  return (
    <div style={{ padding: '20px', backgroundColor: '#0f0e0c', color: '#fff', minHeight: '100vh', position: 'relative' }}>
      
      {/* 1. 외력 감지 시 화면 전체를 덮는 치명적 경고 오버레이 */}
      {isAlert && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
          backgroundColor: 'rgba(217, 4, 4, 0.95)', zIndex: 9999,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          animation: 'blink 1.5s infinite alternate' // 시각적 점멸 효과 제공 가능 (CSS 추가 필요 시)
        }}>
          <h1 style={{ fontSize: '64px', marginBottom: '10px', fontWeight: '900', letterSpacing: '-1px' }}>⚠️ SYSTEM HALTED ⚠️</h1>
          <p style={{ fontSize: '24px', marginBottom: '40px' }}>외력 감지 혹은 수동 비상 정지가 발동되었습니다. 현장을 확인하십시오.</p>
          <button 
            onClick={handleResume}
            style={{ 
              padding: '25px 60px', fontSize: '28px', borderRadius: '50px', 
              border: 'none', cursor: 'pointer', backgroundColor: '#fff', color: '#d90404', fontWeight: 'bold',
              boxShadow: '0px 10px 30px rgba(0,0,0,0.5)', transition: 'transform 0.2s'
            }}
          >
            ▶️ 현장 확인 완료: 조리 재개
          </button>
        </div>
      )}

      <h1>🛠️ 로봇 제어 관리자 대시보드</h1>
      
      {/* 2. 상태창 디자인 변경 (비상 정지 시 붉은색 강렬한 경고창으로 변화) */}
      <div style={{ 
        background: isEmergency ? '#7a0909' : '#1e1a13', 
        border: isEmergency ? '3px solid #ff0000' : '1px solid #3e3524',
        padding: '25px', 
        borderRadius: '12px', 
        marginBottom: '25px',
        transition: 'all 0.4s ease'
      }}>
        <span style={{ fontSize: '14px', color: isEmergency ? '#ff9999' : '#a89a83', textTransform: 'uppercase', fontWeight: 'bold' }}>
          SYSTEM STATUS
        </span>
        <h2 style={{ margin: '5px 0 0 0', fontSize: '26px', color: isEmergency ? '#ffffff' : '#ffb703' }}>
          {robotStatus}
        </h2>
      </div>

      {/* 3. 단일 제어 영역: 비상 정지 버튼 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', maxWidth: '400px' }}>
        <button 
          onClick={handleEmergencyStop}
          disabled={isEmergency}
          style={{ 
            padding: '30px', 
            backgroundColor: isEmergency ? '#331111' : '#d90404', 
            color: isEmergency ? '#888' : 'white', 
            border: 'none', 
            borderRadius: '12px',
            fontSize: '22px',
            fontWeight: 'bold',
            cursor: isEmergency ? 'not-allowed' : 'pointer',
            boxShadow: isEmergency ? 'none' : '0 8px 24px rgba(217, 4, 4, 0.4)',
            transition: 'all 0.2s'
          }}
        >
          {isEmergency ? "🚨 비상 정지 시스템 가동 중" : "🚨 긴급 정지 (EMERGENCY STOP)"}
        </button>
        
        {isEmergency && (
          <button 
            onClick={handleResume}
            style={{
              padding: '12px',
              backgroundColor: '#2ecc71',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            🔓 대시보드에서 안전 해제 유도
          </button>
        )}
      </div>

      {/* 4. 3D 모니터링 영역 */}
      <div style={{ marginTop: '40px', textAlign: 'center' }}>
        {isLoading && <p style={{ color: '#ffb703' }}>로봇 디지털 트윈 3D 모델을 불러오는 중...</p>}
        <div id="rviz" style={{ width: '800px', height: '400px', margin: '0 auto', background: '#000', borderRadius: '8px', display: isLoading ? 'none' : 'block' }}></div>
      </div>
    </div>
  );
}

export default AdminApp;