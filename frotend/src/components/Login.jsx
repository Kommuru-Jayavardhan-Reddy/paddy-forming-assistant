import React, { useState, useEffect } from 'react';
import { login } from '../services/auth';

const Login = ({ onLogin, onSwitchToRegister, sessionNotice = '' }) => {
  const [identifier, setIdentifier] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('rememberedIdentifier') || '';
    }
    return '';
  });
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(() => {
    if (typeof window !== 'undefined') {
      return Boolean(localStorage.getItem('rememberedIdentifier'));
    }
    return false;
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (sessionNotice) {
      setError(sessionNotice);
    }
  }, [sessionNotice]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const cleanIdentifier = identifier.trim();
    if (!cleanIdentifier) {
      setError('Please enter your username or mobile number.');
      return;
    }
    if (!password) {
      setError('Please enter your password.');
      return;
    }

    setIsLoading(true);

    try {
      const response = await login(cleanIdentifier, password, rememberMe);

      if (response.success && response.user) {
        onLogin(response.user);
      } else {
        setError(response.message || 'Login failed. Please verify your credentials.');
      }
    } catch (err) {
      setError('An unexpected error occurred while logging in. Please check backend status.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <div className="login-background"></div>
      <div className="glass-panel screen-enter" style={{ maxWidth: '420px', width: '100%', margin: '1rem auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '48px', height: '48px', borderRadius: '12px', background: 'rgba(16, 185, 129, 0.15)', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '1.5rem' }}>🌾</span>
          </div>
          <h1 style={{ fontSize: '1.75rem', margin: '0 0 0.25rem 0' }}>Paddy Farming Assistant</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Sign in with Username or Registered Mobile
          </p>
        </div>

        {error && (
          <div
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#fca5a5',
              padding: '0.75rem',
              borderRadius: '8px',
              marginBottom: '1rem',
              fontSize: '0.875rem',
              lineHeight: '1.4',
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label htmlFor="identifier">Username or Mobile Number</label>
            <input
              type="text"
              id="identifier"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="e.g. farmer1 or 9876543210"
              required
              disabled={isLoading}
              autoComplete="username"
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Supports username, Indian 10-digit, or +91 E.164 mobile.
            </span>
          </div>

          <div className="input-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="password">Password</label>
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  padding: 0,
                }}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
            <input
              type={showPassword ? 'text' : 'password'}
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              disabled={isLoading}
              autoComplete="current-password"
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1.25rem', gap: '0.5rem' }}>
            <input
              type="checkbox"
              id="remember-me"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              disabled={isLoading}
              style={{ cursor: 'pointer', accentColor: 'var(--accent-color)' }}
            />
            <label htmlFor="remember-me" style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', cursor: 'pointer', userSelect: 'none' }}>
              Remember my username on this device
            </label>
          </div>

          <button
            type="submit"
            className="btn"
            style={{ width: '100%' }}
            disabled={isLoading}
          >
            {isLoading ? 'Authenticating...' : 'Sign In'}
          </button>

          {onSwitchToRegister && (
            <div style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.875rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>New farmer? </span>
              <button
                type="button"
                onClick={onSwitchToRegister}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--accent-color)',
                  cursor: 'pointer',
                  fontWeight: 600,
                  textDecoration: 'underline',
                }}
              >
                Register Account
              </button>
            </div>
          )}
        </form>
      </div>
    </>
  );
};

export default Login;
