// src/App.jsx
import React, { useState } from 'react';
import LoginPage from './pages/LoginPage.jsx';
import SignupPage from './pages/SignupPage.jsx';
import DashboardPage from './pages/DashboardPage';

function App() {
  const [currentPage, setCurrentPage] = useState('login'); // 'login', 'signup', or 'dashboard'
  const [theme, setTheme] = useState(() => localStorage.getItem('fraudguard-theme') || 'light');

  const toggleTheme = () => {
    const nextTheme = theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('fraudguard-theme', nextTheme);
    setTheme(nextTheme);
  };

  const handleSuccess = () => {
    setCurrentPage('dashboard');
  };

  // 1️⃣ Create the logout handler
  const handleLogout = () => {
    setCurrentPage('login');
  };

  return (
    <div className="app-shell" data-theme={theme}>
      {currentPage !== 'dashboard' && (
        <button
          type="button"
          className="theme-toggle auth-theme-toggle"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          aria-pressed={theme === 'dark'}
        >
          <span className="theme-toggle-icon" aria-hidden="true">{theme === 'light' ? '☾' : '☀'}</span>
          <span>{theme === 'light' ? 'Dark mode' : 'Light mode'}</span>
        </button>
      )}
      {currentPage === 'dashboard' ? (
        /* 2️⃣ Pass the handleLogout function to DashboardPage */
        <DashboardPage onLogout={handleLogout} theme={theme} onToggleTheme={toggleTheme} />
      ) : currentPage === 'login' ? (
        <div>
          <LoginPage onLoginSuccess={handleSuccess} />
          <p style={{ textAlign: 'center', marginTop: '-3rem', background: 'var(--bg-primary)', color: 'var(--text-secondary)', paddingBottom: '1rem' }}>
            Don't have an account?{' '}
            <span
              onClick={() => setCurrentPage('signup')}
              style={{ color: 'var(--primary)', cursor: 'pointer', textDecoration: 'underline' }}
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
