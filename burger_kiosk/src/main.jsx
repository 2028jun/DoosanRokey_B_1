import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import App from './App';       // 기존 키오스크 화면
import AdminApp from './AdminApp'; // 방금 만든 관리자 화면

ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App />} />        {/* 기본 경로 */}
      <Route path="/admin" element={<AdminApp />} /> {/* 관리자 경로 */}
    </Routes>
  </BrowserRouter>
);
