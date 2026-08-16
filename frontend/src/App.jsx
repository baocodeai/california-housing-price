import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { UserPage } from './pages/UserPage';
import { AdminPage } from './pages/AdminPage';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* User Valuation Studio Page */}
        <Route path="/" element={<UserPage />} />
        
        {/* Dedicated Admin MLOps Dashboard Page */}
        <Route path="/admin" element={<AdminPage />} />
        
        {/* Catch-all redirect to Home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
