// src/App.jsx
import React, { useState } from 'react';
import LoginPage from './pages/LoginPage.jsx';
import SignupPage from './pages/SignupPage.jsx';

function App() {
  const [currentPage, setCurrentPage] = useState('login'); // 'login' or 'signup'

  const handleSuccess = () => {
    alert("Logged in successfully!");
  };

  return (
    <div>
      {currentPage === 'login' ? (
        <div>
          <LoginPage onLoginSuccess={handleSuccess} />
          <p style={{ textAlign: 'center', marginTop: '-3rem', background: '#f3f4f6', paddingBottom: '3rem' }}>
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