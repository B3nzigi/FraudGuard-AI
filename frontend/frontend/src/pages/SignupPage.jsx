import React, {useState} from 'react';
import { authService } from '../services/api.js';
import './SignupPage.css';

export default function SignupPage({ onNavigateToLogin }) {
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await authService.register(firstName, lastName, email, password);
            setSuccess(true);
            setTimeout(() => {
                onNavigateToLogin();
            }, 2000);
        } catch (err) {
            setError(err.response?.data?.detail || 'Registration failed.Try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="signup-container">
            <form onSubmit={handleSubmit} className="signup-form">
                <h2> Create Admin Account </h2>

                {error && <div className="signup-error">{error}</div>}
                {success && <div className="signup-success">Account created! Redrirecting to Signin Page</div>}

                <input
                    type="text"
                    placeholder="First Name"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    required
                    className="signup-input"
                    disabled={success}
                />

                <input
                    type="text"
                    placeholder="Last Name"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    required
                    className="signup-input"
                    disabled={success}
                />

                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="signup-input"
                    disabled={success}
                />

                <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="signup-input"
                    disabled={success}
                />

                <button type="submit" disabled={loading || success} className="signup-button">
                    {loading ? 'Creating Account...' : 'Sign Up'}
                </button>

                <p className="auth-toggle">
                    Already have an account? <span onClick={onNavigateToLogin}>Login here</span>
                </p>
            </form>
        </div>
    );
}