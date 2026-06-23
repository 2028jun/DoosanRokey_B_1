import { useState, useEffect } from 'react';
import './index.css';

// 1. 키오스크 메뉴 데이터 정의
const MENU_DATA = {
  bun: [
    { id: 'b1', name: '브리오슈 번', desc: '버터 풍미 가득한 부드러운 번', price: 500, color: '#ffb703' },
    { id: 'b2', name: '세서미 번', desc: '고소한 참깨를 올린 클래식 번', price: 300, color: '#e0e0e0' },
    { id: 'b3', name: '프레츨 번', desc: '바삭하고 짭조름한 독일식 번', price: 700, color: '#b57c59' },
    { id: 'b4', name: '양상추 랩', desc: '저칼로리 글루텐프리 옵션', price: 200, color: '#70b652' },
  ],
  patty: [
    { id: 'p1', name: '클래식 비프', desc: '180g 한우 갈빗살 패티', price: 3500, color: '#a23c3c', icon: '🥩' },
    { id: 'p2', name: '더블 비프', desc: '180gx2 더블 스택', price: 5500, color: '#7a2828', icon: '🍖' },
    { id: 'p3', name: '치킨 패티', desc: '바삭한 통가슴살 프라이드', price: 2800, color: '#d08c43', icon: '🍗' },
    { id: 'p4', name: '식물성 패티', desc: '100% 식물성 단백질 패티', price: 3200, color: '#567d46', icon: '🌿' },
    { id: 'p5', name: '피시 패티', desc: '대구살 튀김 패티', price: 2600, color: '#4a8cb6', icon: '🐟' },
  ],
  topping: [
    { id: 't1', name: '양상추', desc: '신선한 아이스버그 레터스', price: 200, icon: '🥬'}, 
    { id: 't2', name: '토마토', desc: '완숙 슬라이스 토마토', price: 300, icon: '🍅'},  
    { id: 't3', name: '양파', desc: '생양파 또는 캐러멜라이즈', price: 200, icon: '🧅'},   
    { id: 't4', name: '피클', desc: '딜 향 오이 피클', price: 200, icon: '🥒'},       
    { id: 't5', name: '베이컨', desc: '크리스피 스모크 베이컨 2줄', price: 1200, icon: '🥓'}, 
    { id: 't6', name: '아보카도', desc: '신선한 아보카도 슬라이스', price: 1500, icon: '🥑'}, 
    { id: 't_no_cheese', name: '치즈 빼기', desc: '기본으로 들어가는 체다 치즈를 제외합니다', price: 0, icon: '🧀❌' },
  ],
  sauce: [
    { id: 's1', name: '케찹', desc: '하인즈 클래식 케찹', price: 0, color: '#e74c3c' },
    { id: 's2', name: '마요네즈', desc: '일본식 크리미 마요', price: 0, color: '#f39c12' },
    { id: 's3', name: 'BBQ 소스', desc: '스모키 하우스 BBQ', price: 300, color: '#7e5233' },
    { id: 's4', name: '머스타드', desc: '디종 홀그레인 머스타드', price: 0, color: '#f1c40f' },
  ],
  beverage: [
    { id: 'd1', name: '콜라', desc: '시원하고 청량한 톡 쏘는 탄산음료', price: 1800, icon: '🥤' },
    { id: 'd2', name: '사이다', desc: '맑고 깨끗한 라임 향 탄산음료', price: 1800, icon: '🥤' },
    { id: 'd3', name: '제로 콜라', desc: '칼로리 걱정 없는 깔끔한 콜라', price: 1800, icon: '🥤' },
    { id: 'd4', name: '제로 사이다', desc: '부담 없이 즐기는 제로 칼로리 사이다', price: 1800, icon: '🥤' },
  ],
  side: [
    { id: 'sd1', name: '감자튀김', desc: '겉바속촉 고소한 황금빛 감자튀김', price: 1500, icon: '🍟' },
    { id: 'sd2', name: '어니언링', desc: '달콤한 양파를 바삭하게 튀긴 링', price: 1500, icon: '🧅' },
    { id: 'sd3', name: '닭다리 튀김', desc: '육즙 가득한 바삭한 통닭다리 구이', price: 3000, icon: '🍗' },
  ]
};

 const TOPPING_COLORS = ['#2ecc71', '#e74c3c', '#f1c40f', '#e67e22', '#9b59b6']; 

function App() {
  const [currentTab, setCurrentTab] = useState('bun');
  const [selectedBun, setSelectedBun] = useState(null);
  const [selectedPatty, setSelectedPatty] = useState(null);
  const [selectedToppings, setSelectedToppings] = useState([]);
  const [selectedSauces, setSelectedSauces] = useState([]);
  const [selectedBeverages, setSelectedBeverages] = useState([]);
  const [selectedSides, setSelectedSides] = useState([]);
  const [quantity, setQuantity] = useState(1);
  const [step, setStep] = useState(1);
  
  // ROS2 관련 상태 관리 변수
  const [orderTopic, setOrderTopic] = useState(null);

  // 컴포넌트 실행 시 ROS2 웹소켓 서버 연동
  useEffect(() => {
    // 💡 HTML에서 로드한 window 전역 객체의 ROSLIB 안전하게 가져오기
    const ROSLIB_ENV = window.ROSLIB;

    if (!ROSLIB_ENV) {
      console.error("❌ index.html에서 roslib 스크립트를 로드하지 못했습니다.");
      return;
    }

    const rosInstance = new ROSLIB_ENV.Ros({
      url: 'ws://localhost:9090' 
    });

    rosInstance.on('connection', () => {
      console.log('✅ ROS2 브릿지 서버 연동 성공');
    });

    rosInstance.on('error', (error) => {
      console.error('❌ ROS2 브릿지 에러:', error);
    });

    rosInstance.on('close', () => {
      console.log('⚠️ ROS2 브릿지 서버 연결 종료');
    });

    const topicInstance = new ROSLIB_ENV.Topic({
      ros: rosInstance,
      name: 'react_order_trigger', 
      messageType: 'std_msgs/msg/String'
    });

    setOrderTopic(topicInstance);

    return () => {
      rosInstance.close();
    };
  }, []);

  //주문 초기화(장바구니 비우기)
  const handleReset = () => {
    setSelectedBun(null); setSelectedPatty(null); setSelectedToppings([]); setSelectedSauces([]);
    setSelectedBeverages([]); setSelectedSides([]);
    setQuantity(1); setCurrentTab('bun'); setStep(1);
  };

  //각 메뉴 선택/해제 처리
  const handleSelect = (item, type) => {
    if (type === 'bun') setSelectedBun(selectedBun?.id === item.id ? null : item);
    else if (type === 'patty') setSelectedPatty(selectedPatty?.id === item.id ? null : item);
    else if (type === 'topping') {
      const isExist = selectedToppings.find(t => t.id === item.id);
      if (isExist) setSelectedToppings(selectedToppings.filter(t => t.id !== item.id));
      else setSelectedToppings([...selectedToppings, { ...item, layerColor: TOPPING_COLORS[selectedToppings.length % TOPPING_COLORS.length] }]);
    } else if (type === 'sauce') {
      const isExist = selectedSauces.find(s => s.id === item.id);
      if (isExist) setSelectedSauces(selectedSauces.filter(s => s.id !== item.id));
      else setSelectedSauces([...selectedSauces, item]);
    } else if (type === 'beverage') {
      const isExist = selectedBeverages.find(b => b.id === item.id);
      if (isExist) setSelectedBeverages(selectedBeverages.filter(b => b.id !== item.id));
      else setSelectedBeverages([...selectedBeverages, item]);
    } else if (type === 'side') {
      const isExist = selectedSides.find(s => s.id === item.id);
      if (isExist) setSelectedSides(selectedSides.filter(s => s.id !== item.id));
      else setSelectedSides([...selectedSides, item]);
    }
  };

  // 각 메뉴 제거
  const handleRemove = (type, id) => {
    if (type === 'bun') setSelectedBun(null);
    if (type === 'patty') setSelectedPatty(null);
    if (type === 'topping') setSelectedToppings(selectedToppings.filter(t => t.id !== id));
    if (type === 'sauce') setSelectedSauces(selectedSauces.filter(s => s.id !== id));
    if (type === 'beverage') setSelectedBeverages(selectedBeverages.filter(b => b.id !== id));
    if (type === 'side') setSelectedSides(selectedSides.filter(s => s.id !== id));
  };

  // 가격 계산
  const singlePrice = 
    (selectedBun?.price || 0) + 
    (selectedPatty?.price || 0) + 
    selectedToppings.reduce((s, t) => s + t.price, 0) + 
    selectedSauces.reduce((s, sc) => s + sc.price, 0) +
    selectedBeverages.reduce((s, b) => s + b.price, 0) +
    selectedSides.reduce((s, sd) => s + sd.price, 0);

  const totalAmount = singlePrice * quantity;
  const isOrderValid = selectedBun && selectedPatty;

  // '치즈 빼기' 카드가 장바구니에 담겨 있는지 검사하는 플래그
  const isCheeseRemoved = selectedToppings.some(t => t.id === 't_no_cheese');

  // 각 메뉴의 유무를 true/false로 판단하고 ROS2로 전송
  const hasTopping = selectedToppings.length > 0;
  const hasSauce   = selectedSauces.length > 0;
  const hasBeverage = selectedBeverages.length > 0;
  const hasSide    = selectedSides.length > 0;

  // 🎯 결제 완료 처리 핸들러 (ROS2 연동용 데이터 구조화 및 발행)
  const handlePaymentComplete = () => {
      const orderData = {
        cheese: !isCheeseRemoved,
        topping: hasTopping,   
        sauce: hasSauce,       
        beverage: hasBeverage, 
        side: hasSide,         
      };

      console.log("▼ 파이썬 노드로 전송할 JSON 데이터:", orderData);

      if (orderTopic) {
        const ROSLIB_ENV = window.ROSLIB;
        
        // 💡 window 객체 내부에 명확히 살아있는 Message 생성자 호출 (is not a constructor 에러 완전 박멸)
        const stringMessage = new ROSLIB_ENV.Message({
          data: JSON.stringify(orderData) 
        });
        
        orderTopic.publish(stringMessage);
        console.log("🚀 ROS2 가교 토픽 송신 완료!");
      } else {
        console.error("❌ ROS2 브릿지가 활성화되지 않았습니다.");
      }

      setStep(4);
    };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div style={styles.logo}>🍔 BURGER LAB</div>
        <div style={styles.steps}>
          <div style={styles.stepWrapper}>
            {step > 1 ? <div style={styles.stepCircleCompleted}>✓</div> : <div style={styles.stepCircleActive}>1</div>}
            <span style={{...styles.stepText, color: step >= 1 ? '#ffb703' : '#666', fontWeight: step >= 1 ? 'bold' : 'normal'}}>메뉴 선택</span>
          </div>
          <span style={styles.stepArrow}>❯</span>
          <div style={styles.stepWrapper}>
            {step > 2 ? <div style={styles.stepCircleCompleted}>✓</div> : step === 2 ? <div style={styles.stepCircleActive}>2</div> : <div style={styles.stepCircleInactive}>2</div>}
            <span style={{...styles.stepText, color: step >= 2 ? '#ffb703' : '#666', fontWeight: step >= 2 ? 'bold' : 'normal'}}>주문 확인</span>
          </div>
          <span style={styles.stepArrow}>❯</span>
          <div style={styles.stepWrapper}>
            {step >= 3 ? <div style={styles.stepCircleActive}>3</div> : <div style={styles.stepCircleInactive}>3</div>}
            <span style={{...styles.stepText, color: step >= 3 ? '#ffb703' : '#666', fontWeight: step >= 3 ? 'bold' : 'normal'}}>결제</span>
          </div>
        </div>
        <div style={styles.cartCount}>🛒 {totalAmount.toLocaleString()}원</div>
      </header>

      {step === 1 && (
        <main style={styles.main}>
          <section style={styles.menuSection}>
            <div style={styles.tabs}>
              {['bun', 'patty', 'topping', 'sauce', 'beverage', 'side'].map(tab => (
                <button key={tab} onClick={() => setCurrentTab(tab)} style={{...styles.tab, ...(currentTab === tab ? styles.activeTab : {})}}>
                  {tab === 'bun' ? '🍞 번' : tab === 'patty' ? '🥩 패티' : tab === 'topping' ? '🥗 토핑' : tab === 'sauce' ? '🧴 소스' : tab === 'beverage' ? '🥤 음료수' : '🍟 사이드'}
                  {((tab === 'bun' && selectedBun) || (tab === 'patty' && selectedPatty) || (tab === 'topping' && selectedToppings.length > 0) || (tab === 'sauce' && selectedSauces.length > 0) || (tab === 'beverage' && selectedBeverages.length > 0) || (tab === 'side' && selectedSides.length > 0)) && (
                    <span style={styles.tabBadge}>
                      {tab === 'topping' ? selectedToppings.length : tab === 'sauce' ? selectedSauces.length : tab === 'beverage' ? selectedBeverages.length : tab === 'side' ? selectedSides.length : 1}
                    </span>
                  )}
                </button>
              ))}
            </div>
            
            <div style={styles.grid}>
              {MENU_DATA[currentTab].map((item) => {
                const isSelected = 
                  currentTab === 'topping' ? selectedToppings.some(t => t.id === item.id) : 
                  currentTab === 'sauce' ? selectedSauces.some(s => s.id === item.id) : 
                  currentTab === 'beverage' ? selectedBeverages.some(b => b.id === item.id) :
                  currentTab === 'side' ? selectedSides.some(sd => sd.id === item.id) :
                  (currentTab === 'bun' ? selectedBun?.id === item.id : selectedPatty?.id === item.id);
                return (
                  <div key={item.id} onClick={() => handleSelect(item, currentTab)} style={{...styles.card, borderColor: isSelected ? '#ffb703' : '#2a2215', backgroundColor: isSelected ? '#2a2215' : '#1c1710'}}>
                    {isSelected && <div style={styles.checkBadge}>✓</div>}
                    <div style={{...styles.circle, backgroundColor: (currentTab === 'topping' || currentTab === 'beverage' || currentTab === 'side') ? '#2a2215' : item.color}}>{item.icon && <span style={{fontSize: '20px'}}>{item.icon}</span>}</div>
                    <div><div style={styles.cardTitle}>{item.name}</div><div style={styles.cardDesc}>{item.desc}</div><div style={styles.cardPrice}>{item.price === 0 ? '무료' : `+${item.price.toLocaleString()}원`}</div></div>
                  </div>
                );
              })}
            </div>
          </section>

          <aside style={styles.sidebar}>
            <h3 style={styles.sidebarTitle}>선택한 내역</h3>
            <div style={styles.sidebarContent}>
              <div style={styles.burgerGraphic}>
                <div style={styles.burgerTopBun}></div>
                {selectedToppings
                  .filter(t => t.id !== 't_no_cheese') // 👈 치즈 빼기 레이어 생성 차단!
                  .slice(3)
                  .map((t, i) => (
                    <div key={`top-${i}`} style={{...styles.burgerToppingLayer, backgroundColor: t.layerColor}}></div>
                  ))
                }
                {selectedPatty && <div style={styles.burgerPattyLayer}></div>}
                {selectedToppings
                  .filter(t => t.id !== 't_no_cheese') // 👈 치즈 빼기 레이어 생성 차단!
                  .slice(0, 3)
                  .map((t, i) => (
                    <div key={`bottom-${i}`} style={{...styles.burgerToppingLayer, backgroundColor: t.layerColor}}></div>
                  ))
                }
                <div style={styles.burgerBottomBun}></div>
              </div>
              
              <div style={styles.cartList}>
                {selectedBun && (
                  <div style={styles.selectedItem}>
                    <div style={{...styles.smallCircle, backgroundColor: selectedBun.color}}></div>
                    <div style={{flex: 1}}>{selectedBun.name}</div>
                    <span style={styles.cartItemPrice}>+{selectedBun.price.toLocaleString()}원</span>
                    <button onClick={() => handleRemove('bun')} style={styles.removeBtn}>✕</button>
                  </div>
                )}
                {selectedPatty && (
                  <div style={styles.selectedItem}>
                    <span style={{marginRight: '8px'}}>{selectedPatty.icon}</span>
                    <div style={{flex: 1}}>{selectedPatty.name}</div>
                    <span style={styles.cartItemPrice}>+{selectedPatty.price.toLocaleString()}원</span>
                    <button onClick={() => handleRemove('patty')} style={styles.removeBtn}>✕</button>
                  </div>
                )}
                {selectedToppings.map(t => (
                  <div key={t.id} style={styles.selectedItem}>
                    <span style={{marginRight: '8px'}}>{t.icon}</span>
                    <div style={{flex: 1}}>{t.name}</div>
                    <span style={styles.cartItemPrice}>+{t.price.toLocaleString()}원</span>
                    <button onClick={() => handleRemove('topping', t.id)} style={styles.removeBtn}>✕</button>
                  </div>
                ))}
                {selectedSauces.map(s => (
                  <div key={s.id} style={styles.selectedItem}>
                    <span style={{marginRight: '8px'}}>{s.icon || '🧴'}</span>
                    <div style={{flex: 1}}>{s.name}</div>
                    <span style={styles.cartItemPrice}>{s.price === 0 ? '무료' : `+${s.price.toLocaleString()}원`}</span>
                    <button onClick={() => handleRemove('sauce', s.id)} style={styles.removeBtn}>✕</button>
                  </div>
                ))}
                {selectedBeverages.map(b => (
                  <div key={b.id} style={styles.selectedItem}>
                    <span style={{marginRight: '8px'}}>{b.icon}</span>
                    <div style={{flex: 1}}>{b.name}</div>
                    <span style={styles.cartItemPrice}>+{b.price.toLocaleString()}원</span>
                    <button onClick={() => handleRemove('beverage', b.id)} style={styles.removeBtn}>✕</button>
                  </div>
                ))}
                {selectedSides.map(sd => (
                  <div key={sd.id} style={styles.selectedItem}>
                    <span style={{marginRight: '8px'}}>{sd.icon}</span>
                    <div style={{flex: 1}}>{sd.name}</div>
                    <span style={styles.cartItemPrice}>+{sd.price.toLocaleString()}원</span>
                    <button onClick={() => handleRemove('side', sd.id)} style={styles.removeBtn}>✕</button>
                  </div>
                ))}
              </div>
            </div>
            <div style={styles.totalSection}>
              <div style={styles.totalRow}><span>소계</span><span style={styles.totalPrice}>{singlePrice.toLocaleString()}원</span></div>
              <button onClick={() => setStep(2)} style={{...styles.orderButton, backgroundColor: isOrderValid ? '#ffb703' : '#332612', color: isOrderValid ? '#000' : '#735729'}  } disabled={!isOrderValid}>주문 확인 ❯</button>
            </div>
          </aside>
        </main>
      )}

      {step === 2 && (
        <main style={styles.confirmMain}>
          <h2 style={styles.confirmTitle}>주문 확인</h2>
          <div style={styles.receiptContainer}>
            <div style={styles.receiptHeader}><div style={styles.receiptLogoBox}>🍔</div><div><div style={{fontSize: '18px', fontWeight: 'bold'}}>나만의 버거 세트</div><div style={{fontSize: '13px', color: '#888'}}>커스텀 빌드 및 사이드</div></div></div>
            <div style={styles.receiptList}>
              {selectedBun && <div style={styles.receiptItem}><div>● {selectedBun.name}</div><div>+{selectedBun.price.toLocaleString()}원</div></div>}
              {selectedPatty && <div style={styles.receiptItem}><div>{selectedPatty.icon} {selectedPatty.name}</div><div>+{selectedPatty.price.toLocaleString()}원</div></div>}
              {selectedToppings.map(t => <div key={t.id} style={styles.receiptItem}><div>{t.icon} {t.name}</div><div>+{t.price.toLocaleString()}원</div></div>)}
              {selectedSauces.map(s => <div key={s.id} style={styles.receiptItem}><div>🧴 {s.name}</div><div>{s.price === 0 ? '무료' : `+${s.price.toLocaleString()}원`}</div></div>)}
              {selectedBeverages.map(b => <div style={styles.receiptItem} key={b.id}><div>{b.icon} {b.name}</div><div>+{b.price.toLocaleString()}원</div></div>)}
              {selectedSides.map(sd => <div style={styles.receiptItem} key={sd.id}><div>{sd.icon} {sd.name}</div><div>+{sd.price.toLocaleString()}원</div></div>)}
            </div>
            <div style={styles.quantitySection}><span>수량</span><div style={styles.quantityCounter}><button onClick={() => setQuantity(q => q > 1 ? q - 1 : 1)} style={styles.qtyBtn}>-</button><span>{quantity}</span><button onClick={() => setQuantity(q => q + 1)} style={styles.qtyBtn}>+</button></div></div>
            <div style={{...styles.receiptRow, borderTop: '1px solid #2a2215', paddingTop: '15px', marginTop: '10px'}}><span style={{fontSize: '18px', fontWeight: 'bold'}}>합계</span><span style={{fontSize: '20px', fontWeight: 'bold', color: '#ffb703'}}>{totalAmount.toLocaleString()}원</span></div>
          </div>
          <div style={styles.confirmBtnGroup}><button onClick={() => setStep(1)} style={styles.backBtn}>수정하기</button><button onClick={() => setStep(3)} style={styles.payBtn}>결제하기 💳</button></div>
        </main>
      )}

      {step === 3 && (
        <main style={styles.confirmMain}>
          <h2 style={styles.confirmTitle}>결제 정보</h2>
          <div style={styles.receiptContainer}>
            <div style={styles.inputWrapper}><label style={styles.inputLabel}>이름</label><input type="text" placeholder="홍길동" style={styles.formInput} /></div>
            <div style={styles.inputWrapper}><label style={styles.inputLabel}>연락처</label><input type="text" placeholder="010-0000-0000" style={styles.formInput} /></div>
            <div style={styles.inputWrapper}><label style={styles.inputLabel}>배달 주소</label><input type="text" placeholder="서울 마포구 버거거리 12번지" style={styles.formInput} /></div>
            <div style={styles.inputWrapper}><label style={styles.inputLabel}>카드 번호</label><div style={styles.creditCardBox}><div style={{fontSize: '11px', color: '#ffb703', fontWeight: 'bold'}}>VISA</div><input type="text" placeholder="••••  ••••  ••••  4242" style={styles.cardInput} /></div></div>
            <div style={{...styles.receiptRow, borderTop: '1px solid #2a2215', paddingTop: '20px', marginTop: '10px'}}><span style={{color: '#aaa'}}>결제 금액</span><span style={{fontSize: '22px', fontWeight: 'bold', color: '#ffb703'}}>{totalAmount.toLocaleString()}원</span></div>
          </div>
          <div style={styles.confirmBtnGroup}>
            <button onClick={() => setStep(2)} style={styles.backBtn}>이전</button>
            <button onClick={handlePaymentComplete} style={styles.payBtn}>
              {totalAmount.toLocaleString()}원 결제 완료
            </button>
          </div>
        </main>
      )}

      {step === 4 && (
        <main style={styles.successMain}>
          <div style={{ fontSize: '100px', marginBottom: '20px' }}>🍔</div>
          <h2 style={styles.successTitle}>주문 완료!</h2>
          <p style={styles.successDesc}>잠시 후 맛있는 버거와 사이드 메뉴가 완성됩니다.</p>
          <div style={styles.waitTimeBadge}>예상 대기시간 <span style={{color: '#ffb703'}}>12분</span></div>
          <div style={styles.orderInfoBox}><div style={styles.infoRow}><span style={{color: '#ffb703'}}>📍</span> 서울 마포구 버거거리 12번지</div><div style={styles.infoRow}><span style={{color: '#888', fontSize: '13px'}}>주문번호 480-8154</span></div></div>
          <button onClick={handleReset} style={styles.resetButton}>새로 주문하기</button>
        </main>
      )}
    </div>
  );
}

const styles = {
  container: { display: 'flex', flexDirection: 'column', minHeight: '100vh', padding: '20px 40px', backgroundColor: '#14110b', color: '#fff', fontFamily: 'system-ui' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '20px', borderBottom: '1px solid #2a2215' },
  logo: { fontSize: '24px', fontWeight: 'bold', color: '#ffb703' },
  steps: { display: 'flex', alignItems: 'center', gap: '15px' },
  stepWrapper: { display: 'flex', alignItems: 'center', gap: '8px' },
  stepText: { fontSize: '14px' },
  stepArrow: { fontSize: '12px', color: '#444' },
  stepCircleCompleted: { width: '24px', height: '24px', backgroundColor: '#ffb703', borderRadius: '50%', color: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', fontWeight: 'bold' },
  stepCircleActive: { width: '24px', height: '24px', backgroundColor: '#ffb703', borderRadius: '50%', color: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 'bold' },
  stepCircleInactive: { width: '24px', height: '24px', backgroundColor: '#221c13', borderRadius: '50%', color: '#444', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 'bold' },
  cartCount: { fontSize: '18px', fontWeight: 'bold' },
  main: { display: 'flex', marginTop: '30px', gap: '40px', flex: 1 },
  menuSection: { flex: 2 },
  tabs: { display: 'flex', gap: '10px', marginBottom: '30px', flexWrap: 'wrap' },
  tab: { display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', borderRadius: '20px', border: 'none', backgroundColor: '#221c13', color: '#888', cursor: 'pointer', fontSize: '15px' },
  activeTab: { backgroundColor: '#ffb703', color: '#000', fontWeight: 'bold' },
  tabBadge: { display: 'flex', alignItems: 'center', backgroundColor: '#000', color: '#ffb703', width: '18px', height: '18px', borderRadius: '50%', fontSize: '11px', fontWeight: 'bold', justifyContent: 'center' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px' },
  card: { position: 'relative', display: 'flex', alignItems: 'center', gap: '20px', padding: '20px', borderRadius: '15px', border: '2px solid transparent', cursor: 'pointer' },
  checkBadge: { position: 'absolute', top: '12px', right: '12px', width: '20px', height: '20px', backgroundColor: '#ffb703', borderRadius: '50%', color: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 'bold' },
  circle: { width: '40px', height: '40px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  cardTitle: { fontSize: '18px', fontWeight: 'bold', marginBottom: '5px' },
  cardDesc: { fontSize: '13px', color: '#aaa', marginBottom: '8px' },
  cardPrice: { fontSize: '14px', color: '#ffb703', fontWeight: 'bold' },
  sidebar: { flex: 1, backgroundColor: '#1c1710', borderRadius: '20px', padding: '20px', display: 'flex', flexDirection: 'column', border: '1px solid #2a2215', height: 'fit-content' },
  sidebarTitle: { fontSize: '16px', marginBottom: '20px', color: '#aaa' },
  sidebarContent: { display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' },
  cartList: { width: '100%', marginTop: '15px' },
  selectedItem: { display: 'flex', alignItems: 'center', padding: '8px 0', width: '100%', borderBottom: '1px solid #221c13', fontSize: '14px' },
  cartItemPrice: { color: '#ffb703', fontSize: '13px', marginRight: '10px' },
  smallCircle: { width: '10px', height: '10px', borderRadius: '50%', marginRight: '10px' },
  removeBtn: { background: 'none', border: 'none', color: '#555', cursor: 'pointer', fontSize: '14px' },
  burgerGraphic: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', marginBottom: '15px' },
  burgerTopBun: { width: '120px', height: '35px', backgroundColor: '#fec435', borderTopLeftRadius: '30px', borderTopRightRadius: '30px', borderBottomLeftRadius: '10px', borderBottomRightRadius: '10px' },
  burgerPattyLayer: { width: '122px', height: '18px', backgroundColor: '#873c08', borderRadius: '8px' },
  burgerToppingLayer: { width: '124px', height: '10px', borderRadius: '5px' },
  burgerBottomBun: { width: '120px', height: '20px', backgroundColor: '#ffa200', borderTopLeftRadius: '4px', borderTopRightRadius: '4px', borderBottomLeftRadius: '15px', borderBottomRightRadius: '15px' },
  totalSection: { borderTop: '1px solid #2a2215', paddingTop: '20px', width: '100%', marginTop: '20px' },
  totalRow: { display: 'flex', justifyContent: 'space-between', fontSize: '18px', marginBottom: '15px' },
  totalPrice: { color: '#ffb703', fontWeight: 'bold' },
  orderButton: { width: '100%', padding: '15px', borderRadius: '15px', border: 'none', fontSize: '16px', fontWeight: 'bold', cursor: 'pointer' },
  confirmMain: { display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '40px', flex: 1 },
  confirmTitle: { fontSize: '28px', fontWeight: 'bold', marginBottom: '30px' },
  receiptContainer: { width: '100%', maxWidth: '520px', backgroundColor: '#1c1710', borderRadius: '20px', padding: '30px', border: '1px solid #2a2215' },
  receiptHeader: { display: 'flex', alignItems: 'center', gap: '15px', paddingBottom: '20px', borderBottom: '1px solid #2a2215', marginBottom: '20px' },
  receiptLogoBox: { width: '45px', height: '45px', backgroundColor: '#2a2215', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '22px' },
  receiptList: { display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '20px' },
  receiptItem: { display: 'flex', justifyContent: 'space-between', fontSize: '15px', color: '#ddd' },
  receiptRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' },
  quantitySection: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #2a2215', paddingTop: '15px', width: '100%' },
  quantityCounter: { display: 'flex', alignItems: 'center', gap: '15px', backgroundColor: '#14110b', padding: '6px 12px', borderRadius: '30px' },
  qtyBtn: { background: 'none', border: 'none', color: '#ffb703', fontSize: '20px', cursor: 'pointer' },
  confirmBtnGroup: { display: 'flex', gap: '20px', width: '100%', maxWidth: '520px', marginTop: '30px' },
  backBtn: { flex: 1, padding: '16px', borderRadius: '15px', backgroundColor: '#2a2215', color: '#aaa', border: 'none', fontWeight: 'bold', cursor: 'pointer' },
  payBtn: { flex: 1, padding: '16px', borderRadius: '15px', backgroundColor: '#ffb703', color: '#000', border: 'none', fontWeight: 'bold', cursor: 'pointer' },
  inputWrapper: { display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '15px', width: '100%' },
  inputLabel: { fontSize: '13px', color: '#888' },
  formInput: { padding: '14px', backgroundColor: '#14110b', border: '1px solid #2a2215', borderRadius: '10px', color: '#fff' },
  creditCardBox: { backgroundColor: '#5c2306', borderRadius: '12px', padding: '16px', border: '1px solid #78310c' },
  cardInput: { background: 'none', border: 'none', color: '#fff', fontSize: '18px', outline: 'none', width: '100%', marginTop: '10px' },
  successMain: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, textAlign: 'center' },
  successTitle: { fontSize: '32px', fontWeight: 'bold', color: '#ffb703', marginBottom: '10px' },
  successDesc: { color: '#aaa', marginBottom: '20px', fontSize: '16px' },
  waitTimeBadge: { backgroundColor: '#221c13', padding: '10px 20px', borderRadius: '30px', fontSize: '15px', marginBottom: '40px' },
  orderInfoBox: { marginBottom: '50px' },
  infoRow: { marginBottom: '8px', fontSize: '16px' },
  resetButton: { backgroundColor: '#fff', color: '#000', border: 'none', padding: '14px 30px', borderRadius: '30px', fontSize: '15px', fontWeight: 'bold', cursor: 'pointer' }
};

export default App;