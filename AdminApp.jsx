import React, { useState, useEffect } from 'react';
import * as ROSLIB2 from 'roslib';

const ROSBRIDGE_URL = 'ws://localhost:9090';
const ROBOT_FIXED_FRAME = 'base_link';
const ROBOT_DESCRIPTION_SERVICES = [
  {
    name: '/robot_state_publisher/get_parameters',
    serviceType: 'rcl_interfaces/srv/GetParameters',
    request: { names: ['robot_description'] },
    pickValue: response => response?.values?.[0]?.string_value
  },
  {
    name: '/robot_state_publisher/get_parameters',
    serviceType: 'rcl_interfaces/GetParameters',
    request: { names: ['robot_description'] },
    pickValue: response => response?.values?.[0]?.string_value
  },
  {
    name: '/rosapi/get_param',
    serviceType: 'rosapi/GetParam',
    request: { name: 'robot_description' },
    pickValue: response => response?.value
  }
];
const ROBOT_MESH_BASE_PATH = '/ros_models/';

function AdminApp() {
  const [ros, setRos] = useState(null);
  const [robotStatus, setRobotStatus] = useState("연결 확인 중...");
  const [isEmergency, setIsEmergency] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  
  // 경고창 상태 관리를 위한 state
  const [isAlert, setIsAlert] = useState(false);

  useEffect(() => {
    const ROSLIB = window.ROSLIB;
    let isDisposed = false;
    let viewerStarted = false;
    let rosInstance = null;
    let ros2TfInstance = null;
    let statusTopic = null;
    let reconnectTimer = null;

    if (!ROSLIB) {
      setRobotStatus('ROSLIB 로드 실패: index.html의 roslib 스크립트를 확인하세요.');
      setIsLoading(false);
      return;
    }

    const parseParamValue = (value) => {
      if (!value) return '';
      try {
        const parsed = JSON.parse(value);
        return typeof parsed === 'string' ? parsed : value;
      } catch {
        return value;
      }
    };

    const callServiceWithTimeout = (service, request, onSuccess, onFailure) => {
      let completed = false;
      const timeout = setTimeout(() => {
        if (completed) return;
        completed = true;
        onFailure();
      }, 3000);

      service.callService(
        new ROSLIB.ServiceRequest(request),
        (response) => {
          if (completed) return;
          completed = true;
          clearTimeout(timeout);
          onSuccess(response);
        },
        () => {
          if (completed) return;
          completed = true;
          clearTimeout(timeout);
          onFailure();
        }
      );
    };

    const getRobotDescription = (rosInstance, index, onSuccess, onFailure) => {
      if (index >= ROBOT_DESCRIPTION_SERVICES.length) {
        onFailure();
        return;
      }

      const source = ROBOT_DESCRIPTION_SERVICES[index];
      const getParamService = new ROSLIB.Service({
        ros: rosInstance,
        name: source.name,
        serviceType: source.serviceType
      });

      callServiceWithTimeout(
        getParamService,
        source.request,
        (response) => {
          const description = parseParamValue(source.pickValue(response));
          if (description && description.includes('<robot')) {
            onSuccess(description, source.name);
            return;
          }
          getRobotDescription(rosInstance, index + 1, onSuccess, onFailure);
        },
        () => getRobotDescription(rosInstance, index + 1, onSuccess, onFailure)
      );
    };

    const start3DViewer = (rosInstance) => {
      if (viewerStarted || isDisposed) return;
      viewerStarted = true;

      const rvizDiv = document.getElementById('rviz');
      const ROS3D = window.ROS3D;

      if (rvizDiv && ROS3D) {
        try {
          const testCanvas = document.createElement('canvas');
          const webglContext = testCanvas.getContext('webgl') || testCanvas.getContext('experimental-webgl');

          if (!webglContext) {
            setIsLoading(false);
            setRobotStatus('3D 표시 실패: Chrome에서 WebGL을 사용할 수 없습니다. GPU/브라우저 설정을 확인하세요.');
            return;
          }

          rvizDiv.innerHTML = '';
          const viewer = new ROS3D.Viewer({
            divID: 'rviz',
            width: 800,
            height: 400,
            antialias: true,
            background: '#000000'
          });

          viewer.addObject(new ROS3D.Grid({
            color: '#334155',
            cellSize: 0.25,
            num_cells: 20
          }));

          const TFClient = ROSLIB2.ROS2TFClient || ROSLIB.TFClient;
          ros2TfInstance = ROSLIB2.ROS2TFClient ? new ROSLIB2.Ros({ url: ROSBRIDGE_URL }) : rosInstance;
          const tfClient = new TFClient({
            ros: ros2TfInstance,
            fixedFrame: ROBOT_FIXED_FRAME,
            angularThres: 0.01,
            transThres: 0.01,
            rate: 10.0
          });

          getRobotDescription(rosInstance, 0, (robotDescription, paramName) => {
            const urdfModel = new ROSLIB.UrdfModel({ string: robotDescription });
            const urdf = new ROS3D.Urdf({
              urdfModel,
              tfClient,
              path: ROBOT_MESH_BASE_PATH
            });
            viewer.scene.add(urdf);

            if (!isDisposed) {
              setRobotStatus(`ROS 2 연결됨: 3D 모델 로드 완료 (${paramName})`);
            }
          }, () => {
            if (!isDisposed) {
              setRobotStatus('3D 모델 로드 실패: robot_description 파라미터를 읽지 못했습니다.');
            }
          });

          setIsLoading(false);
        } catch (err) {
          console.error("3D 뷰어 로드 실패:", err);
          setRobotStatus('3D 모델 로드 실패: robot_description, /tf, /joint_states를 확인하세요.');
        }
      } else {
        setIsLoading(false);
        setRobotStatus('ROS3D 로드 실패: index.html의 ros3d 스크립트를 확인하세요.');
      }
    };

    const subscribeStatusTopic = (instance) => {
      statusTopic = new ROSLIB.Topic({
        ros: instance,
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
    };

    const scheduleReconnect = () => {
      if (isDisposed || reconnectTimer) return;
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectRos();
      }, 2000);
    };

    const connectRos = () => {
      if (isDisposed) return;

      rosInstance = new ROSLIB.Ros({ url: ROSBRIDGE_URL });
      setRos(rosInstance);

      rosInstance.on('connection', () => {
        if (isDisposed) return;
        setRobotStatus('ROS 2 연결됨: 3D 모델 로드 대기');
        subscribeStatusTopic(rosInstance);
        start3DViewer(rosInstance);
      });
      rosInstance.on('error', () => {
        if (!isDisposed) setRobotStatus('ROS 2 연결 재시도 중: rosbridge 서버를 확인하세요.');
      });
      rosInstance.on('close', () => {
        if (isDisposed) return;
        setRobotStatus('ROS 2 연결 대기 중: 2초 후 재시도합니다.');
        scheduleReconnect();
      });
    };

    // 1. ROS 연결
    connectRos();

    return () => {
      isDisposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (statusTopic) statusTopic.unsubscribe();
      if (ros2TfInstance && ros2TfInstance !== rosInstance) ros2TfInstance.close();
      if (rosInstance) rosInstance.close();
      const rvizDiv = document.getElementById('rviz');
      if (rvizDiv) rvizDiv.innerHTML = '';
    };
  }, []);

  const sendCommand = (topicName, msgData, statusText) => {
    if (!ros) {
      setRobotStatus('ROS 2 연결 전: 관리자 명령을 보낼 수 없습니다.');
      return false;
    }

    const ROSLIB = window.ROSLIB;
    if (!ROSLIB) {
      setRobotStatus('ROSLIB 로드 실패: 관리자 명령을 보낼 수 없습니다.');
      return false;
    }

    const topic = new ROSLIB.Topic({ ros, name: topicName, messageType: 'std_msgs/msg/Bool' });
    topic.publish(new ROSLIB.Message({ data: msgData }));
    
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
          <h1 style={{ fontSize: '42px', marginBottom: '10px', fontWeight: '900', letterSpacing: '0' }}>⚠️ SYSTEM HALTED ⚠️</h1>
          <p style={{ fontSize: '18px', marginBottom: '32px' }}>외력 감지 혹은 수동 비상 정지가 발동되었습니다. 현장을 확인하십시오.</p>
          <button 
            onClick={handleResume}
            style={{ 
              padding: '18px 36px', fontSize: '20px', borderRadius: '32px', 
              border: 'none', cursor: 'pointer', backgroundColor: '#fff', color: '#d90404', fontWeight: 'bold',
              boxShadow: '0px 10px 30px rgba(0,0,0,0.5)', transition: 'transform 0.2s'
            }}
          >
            ▶️ 현장 확인 완료: 조리 재개
          </button>
        </div>
      )}

      <h1 style={{ fontSize: '32px', margin: '28px 0 24px' }}>🛠️ 로봇 제어 관리자 대시보드</h1>
      
      {/* 2. 상태창 디자인 변경 (비상 정지 시 붉은색 강렬한 경고창으로 변화) */}
      <div style={{ 
        background: isEmergency ? '#7a0909' : '#1e1a13', 
        border: isEmergency ? '3px solid #ff0000' : '1px solid #3e3524',
        padding: '18px 24px', 
        borderRadius: '10px', 
        marginBottom: '22px',
        transition: 'all 0.4s ease'
      }}>
        <span style={{ fontSize: '12px', color: isEmergency ? '#ff9999' : '#a89a83', textTransform: 'uppercase', fontWeight: 'bold' }}>
          SYSTEM STATUS
        </span>
        <h2 style={{ margin: '5px 0 0 0', fontSize: '22px', color: isEmergency ? '#ffffff' : '#ffb703' }}>
          {robotStatus}
        </h2>
      </div>

      {/* 3. 단일 제어 영역: 비상 정지 버튼 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', maxWidth: '400px' }}>
        <button 
          onClick={handleEmergencyStop}
          disabled={isEmergency}
          style={{ 
            padding: '20px 24px', 
            backgroundColor: isEmergency ? '#331111' : '#d90404', 
            color: isEmergency ? '#888' : 'white', 
            border: 'none', 
            borderRadius: '10px',
            fontSize: '18px',
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
