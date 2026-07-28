// src/App.jsx
import React, { useState } from 'react';
import LoginPage from './pages/LoginPage.jsx';
import SignupPage from './pages/SignupPage.jsx';
import DashboardPage from './pages/DashboardPage';

function App() {
  const [currentPage, setCurrentPage] = useState('login'); // 'login', 'signup', or 'dashboard'

  const handleSuccess = () => {
    setCurrentPage('dashboard');
  };

  // 1️⃣ Create the logout handler
  const handleLogout = () => {
    setCurrentPage('login');
  };

  return (
    <div>
      {currentPage === 'dashboard' ? (
        /* 2️⃣ Pass the handleLogout function to DashboardPage */
        <DashboardPage onLogout={handleLogout} />
      ) : currentPage === 'login' ? (
        <div>
          <LoginPage onLoginSuccess={handleSuccess} />
          <p style={{ textAlign: 'center', marginTop: '-3rem', background: '#f3f4f6', paddingBottom: '1rem' }}>
            Don't have an account?{' '}
            <span
              onClick={() => setCurrentPage('signup')}
              style={{ color: '#2563eb', cursor: 'pointer', textDecoration: 'underline' }}
            >
              Sign up here
            </span>
          </p>
        </div>
      ) : (
        <SignupPage onNavigateToLogin={() => setCurrentPage('login')} />
      )}
    </div>
  );
}

export default App;