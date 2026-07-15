import React, { useState } from 'react';
import { authService } from '../services/api';
import './LoginPage.css';

export default function LoginPage({ onLoginSuccess}) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await authService.login(email,password);
            onLoginSuccess(); // Navigate to the main page
        } catch (err) {
            setError(err.response?.data?.detail || 'Invalid Email or Password');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-container">
            <form onSubmit={handleSubmit} className="login-form">
                <h2>FraudGuard AI</h2>

                {error && <div className="login-error">{error}</div>}

                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="login-input"
                />

                <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="login-input"
                />

                <button type="submit" disabled={loading} className="login-button">
                    {loading ? 'Authenticating...' : 'Sign In'}
                </button>
            </form>
        </div>
    );
}