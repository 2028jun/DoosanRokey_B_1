import React, { useState, useEffect } from 'react';
import * as ROSLIB2 from 'roslib';

const ROSBRIDGE_URL = 'ws://localhost:9090';
const ROBOT_FIXED_FRAME = 'base_link';

const ROBOT_DESCRIPTION_SERVICES = [
  {
    name: '/dsr01/robot_state_publisher/get_parameters',
    serviceType: 'rcl_interfaces/srv/GetParameters',
    request: { names: ['robot_description'] },
    pickValue: response => response?.values?.[0]?.string_value
  },
  {
    name: '/robot_state_publisher/get_parameters',
    serviceType: 'rcl_interfaces/srv/GetParameters',
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
  const [robotStatus, setRobotStatus] = useState("정상 가동 준비");
  const [isEmergency, setIsEmergency] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const [currentForce, setCurrentForce] = useState(0.0);
  const [currentTool, setCurrentTool] = useState("그리퍼 단독");
  const [gripperStatus, setGripperStatus] = useState("RELEASE");

  const [currentTaskDisplay, setCurrentTaskDisplay] = useState("대기 중");

  useEffect(() => {
    const styleId = "emergency-blink-style";
    if (!document.getElementById(styleId)) {
      const style = document.createElement("style");
      style.id = styleId;
      style.innerText = `
        @keyframes emergencyBlink {
          0% { background-color: #7a0909; border-color: #ff0000; }
          50% { background-color: #b31414; border-color: #ff6666; }
          100% { background-color: #7a0909; border-color: #ff0000; }
        }
        .emergency-active {
          animation: emergencyBlink 1.2s infinite ease-in-out;
        }
      `;
      document.head.appendChild(style);
    }

    const ROSLIB = window.ROSLIB;
    let isDisposed = false;
    let viewerStarted = false;
    let rosInstance = null;
    let ros2TfInstance = null;
    let statusTopic = null;
    let telemetryTopic = null;
    let completeTopic = null;
    let reconnectTimer = null;
    let resizeObserver = null;

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
          rvizDiv.innerHTML = '';
          const initWidth = rvizDiv.parentElement.clientWidth - 40;

          const viewer = new ROS3D.Viewer({
            divID: 'rviz',
            width: initWidth > 0 ? initWidth : 1200,
            height: 400,
            antialias: true,
            background: '#141311',
            cameraPose: { x: 2.2, y: -2.2, z: 1.5 }
          });

          viewer.camera.lookAt(0, 0, 0.4);

          viewer.addObject(new ROS3D.Grid({
            color: '#334155',
            cellSize: 0.25,
            num_cells: 24
          }));

          const TFClient = ROSLIB2.ROS2TFClient || ROSLIB.TFClient;
          ros2TfInstance = ROSLIB2.ROS2TFClient ? new ROSLIB2.Ros({ url: ROSBRIDGE_URL }) : rosInstance;

          const tfClient = new TFClient({
            ros: ros2TfInstance,
            fixedFrame: ROBOT_FIXED_FRAME,
            angularThres: 0.01,
            transThres: 0.01,
            rate: 15.0,
            serverName: '/tf2_web_republisher'
          });

          getRobotDescription(rosInstance, 0, (robotDescription) => {
            const urdfModel = new ROSLIB.UrdfModel({ string: robotDescription });
            const urdf = new ROS3D.Urdf({
              urdfModel,
              tfClient,
              path: ROBOT_MESH_BASE_PATH
            });
            viewer.scene.add(urdf);

            resizeObserver = new ResizeObserver(entries => {
              for (let entry of entries) {
                const { width } = entry.contentRect;
                if (width > 0 && viewer) {
                  viewer.resize(width, 400);
                  viewer.camera.lookAt(0, 0, 0.4);
                }
              }
            });
            resizeObserver.observe(rvizDiv);
          }, () => {
            console.log('robot_description 로드 대기 중...');
          });

          setIsLoading(false);
        } catch (err) {
          console.error("3D 뷰어 로드 실패:", err);
        }
      }
    };

    const subscribeTopics = (instance) => {
      statusTopic = new ROSLIB.Topic({
        ros: instance,
        name: '/robot_status_topic',
        messageType: 'std_msgs/msg/String'
      });
      statusTopic.subscribe(msg => {
        if (isDisposed) return;
        setRobotStatus(msg.data);
        if (msg.data.includes("충돌") || msg.data.includes("비상정지")) {
          setIsEmergency(true);
        } else {
          setIsEmergency(false);
        }
      });

      telemetryTopic = new ROSLIB.Topic({
        ros: instance,
        name: '/robot_telemetry_topic',
        messageType: 'std_msgs/msg/String'
      });
      telemetryTopic.subscribe(msg => {
        if (isDisposed) return;
        try {
          const dataArray = msg.data.split(',');
          setCurrentForce(parseFloat(dataArray[0]) || 0.0);
          setCurrentTool(dataArray[1] || "그리퍼 단독");
          setGripperStatus(dataArray[2] || "RELEASE");

          const rawTask = dataArray[3] || "대기 중";
          const rawIngredient = dataArray[4] || "";

          if (rawTask === "대기 중" || rawTask === "완료") {
            setCurrentTaskDisplay("대기 중");
          } else if (rawTask === "재료 옮기기" && rawIngredient && rawIngredient !== "-") {
            const cleanTask = rawTask.replace("재료 ", "");
            setCurrentTaskDisplay(`${rawIngredient} ${cleanTask}`);
          } else {
            setCurrentTaskDisplay(rawTask);
          }

          if (isEmergency) {
            setCurrentTaskDisplay("❌ 구동 중단됨 (이머전시 락)");
          }
        } catch (err) {
          console.error(err);
        }
      });
    };

    const connectRos = () => {
      if (isDisposed) return;
      rosInstance = new ROSLIB.Ros({ url: ROSBRIDGE_URL });
      setRos(rosInstance);

      rosInstance.on('connection', () => {
        if (isDisposed) return;
        subscribeTopics(rosInstance);
        start3DViewer(rosInstance);
      });
      rosInstance.on('close', () => {
        if (isDisposed) return;
        reconnectTimer = setTimeout(connectRos, 2000);
      });
    };

    connectRos();

    return () => {
      isDisposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (statusTopic) statusTopic.unsubscribe();
      if (telemetryTopic) telemetryTopic.unsubscribe();
      if (ros2TfInstance && ros2TfInstance !== rosInstance) ros2TfInstance.close();
      if (rosInstance) rosInstance.close();
      if (resizeObserver) resizeObserver.disconnect();
    };
  }, [isEmergency]);

  const sendCommand = (topicName, msgData, statusText) => {
    if (!ros) return false;
    const ROSLIB = window.ROSLIB;
    const topic = new ROSLIB.Topic({ ros, name: topicName, messageType: 'std_msgs/msg/Bool' });
    topic.publish({ data: msgData });
    setRobotStatus(statusText);
    return true;
  };

  const handleEmergencyStop = () => {
    setIsEmergency(true);
    setRobotStatus("[수동 정지 상황] 관리자가 비상 버튼을 눌렀습니다. 현장 확인 후 시스템을 재가동하십시오.");
    sendCommand('/emergency_stop', true, '[수동 정지 상황] 관리자가 비상 버튼을 눌렀습니다. 현장 확인 후 시스템을 재가동하십시오.');
  };

  const handleResume = () => {
    setIsEmergency(false);
    setRobotStatus("정상 가동 준비: 비상 정지 락 해제됨. (시스템 재시작 필요)");
    sendCommand('/emergency_stop', false, '정상 가동 준비: 비상 정지 락 해제됨. (시스템 재시작 필요)');
  };

  return (
    <div style={{ padding: '24px', backgroundColor: '#0f0e0c', color: '#fff', minHeight: '100vh', fontFamily: 'sans-serif' }}>

      <h1 style={{ fontSize: '26px', margin: '0 0 20px 0', fontWeight: '800' }}>🛠️ 로봇 제어 관리자 대시보드</h1>

      {/* SYSTEM STATUS 알림창 */}
      <div
        className={isEmergency ? "emergency-active" : ""}
        style={{
          background: isEmergency ? '#7a0909' : '#1e1a13',
          border: isEmergency ? '2px solid #ff0000' : '1px solid #3e3524',
          padding: '16px 20px',
          borderRadius: '6px',
          marginBottom: '15px',
          transition: 'background-color 0.3s ease'
        }}
      >
        <span style={{ fontSize: '11px', color: isEmergency ? '#ffcccc' : '#a89a83', textTransform: 'uppercase', fontWeight: 'bold', letterSpacing: '1px' }}>
          SYSTEM STATUS
        </span>
        <h2 style={{ margin: '6px 0 0 0', fontSize: '16px', color: '#ffffff', fontWeight: '600' }}>
          {isEmergency ? "🚨 " : "🔄 "} {robotStatus}
        </h2>
      </div>

      {/* SYSTEM HALTED 경고창 + 복구 버튼 */}
      {isEmergency && (
        <div className="emergency-active" style={{
          border: '1px solid #ff0000', padding: '14px 20px', borderRadius: '6px', marginBottom: '20px',
          display: 'flex', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'
        }}>
          <div>
            <h3 style={{ margin: 0, color: '#ff4d4d', fontSize: '16px', fontWeight: 'bold' }}>⚠️ SYSTEM HALTED</h3>
            <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#ffcccc' }}>로봇 안전 잠금 상태입니다. 현장 위험을 제거하고 락을 해제하십시오.</p>
          </div>
          <button
            onClick={handleResume}
            style={{
              padding: '8px 16px',
              backgroundColor: '#ffffff',
              color: '#b31414',
              border: 'none',
              borderRadius: '20px',
              fontSize: '12px',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
            }}
          >
            ▶️ 대시보드 락 해제
          </button>
        </div>
      )}

      {/* 데이터 전광판 메인 그리드 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>

        {/* 좌측 카드: 실시간 하드웨어 모니터링 */}
        <div style={{ background: '#141311', padding: '20px', borderRadius: '8px', border: '1px solid #29241c' }}>
          <h3 style={{ marginTop: 0, color: '#ffb703', fontSize: '15px', marginBottom: '15px' }}>⚡ 실시간 하드웨어 모니터링</h3>
          <p style={{ fontSize: '14px', margin: '8px 0', color: '#a89a83' }}>
            실시간 측정 외력: <strong style={{ color: '#2ecc71', fontSize: '18px' }}>{currentForce.toFixed(1)} N</strong> / 15.0 N
          </p>
          <p style={{ fontSize: '14px', margin: '8px 0', color: '#a89a83' }}>장착된 도구: <strong style={{ color: '#fff' }}>{currentTool}</strong></p>
          <p style={{ fontSize: '14px', margin: '8px 0', color: '#a89a83' }}>
            그리퍼 상태: <span style={{ padding: '3px 8px', borderRadius: '4px', background: gripperStatus === "GRIP" ? '#2ecc71' : '#e67e22', fontWeight: 'bold', fontSize: '11px', color: '#fff' }}>
              {gripperStatus === "GRIP" ? "잡기 (GRIP)" : "열림 (RELEASE)"}
            </span>
          </p>
        </div>

        {/* 우측 카드: 현재 작업 공정 */}
        <div style={{ background: '#141311', padding: '20px', borderRadius: '8px', border: '1px solid #29241c', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <h3 style={{ marginTop: 0, color: '#ffb703', fontSize: '15px', marginBottom: '5px' }}>⚙️ 현재 작업 공정</h3>
          <span style={{ fontSize: '11px', color: '#a89a83', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Current Task Running
          </span>
          <h2 style={{ margin: '12px 0 0 0', fontSize: '32px', color: isEmergency ? '#ff4d4d' : '#2ecc71', fontWeight: '700' }}>
            {currentTaskDisplay}
          </h2>
        </div>

      </div>

      {/* 3D 로봇 뷰어 영역 */}
      <div style={{
        background: '#141311', borderRadius: '8px', border: '1px solid #29241c', padding: '20px', marginBottom: '25px',
        width: '100%', boxSizing: 'border-box'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: isLoading ? '#ffb703' : '#2ecc71' }}></span>
          <span style={{ fontSize: '13px', color: '#a89a83', fontWeight: 'bold', letterSpacing: '0.5px' }}>🤖 DIGITAL TWIN 3D VIEW (RVIZ)</span>
        </div>
        <div id="rviz" style={{ width: '100%', height: '400px', borderRadius: '6px', overflow: 'hidden', display: isLoading ? 'none' : 'block' }}></div>
      </div>

      {/* 하단 비상정지 버튼 */}
      <div style={{ display: 'flex', justifyContent: 'center', width: '100%' }}>
        <button
          onClick={handleEmergencyStop}
          disabled={isEmergency}
          style={{
            width: '100%', maxWidth: '450px', padding: '16px 0',
            backgroundColor: isEmergency ? '#2b1111' : '#d90404',
            color: isEmergency ? '#a89a83' : 'white',
            border: isEmergency ? '1px solid #552222' : 'none',
            borderRadius: '6px', fontSize: '16px', fontWeight: 'bold',
            cursor: isEmergency ? 'not-allowed' : 'pointer',
            boxShadow: isEmergency ? 'none' : '0 4px 15px rgba(217, 4, 4, 0.4)',
            transition: 'all 0.2s'
          }}
        >
          {isEmergency ? "🚨 비상 정지 시스템 가동 중" : "🚨 긴급 정지 (EMERGENCY STOP)"}
        </button>
      </div>

    </div>
  );
}

export default AdminApp;