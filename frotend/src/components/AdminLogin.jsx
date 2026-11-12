import React, { useState, useEffect } from 'react';
import { login, logout as authLogout } from '../services/auth';

/**
 * AdminLogin Component (Route: '/admin/login')
 * Isolated administrative entry point.
 * Authenticates using Administrator Username + Argon2id Password.
 * Guarantees Farmers cannot access Admin Dashboard and Admins are directed exclusively to /admin/dashboard.
 */
const AdminLogin = ({ onLogin, onSwitchToFarmer, sessionNotice = '' }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
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

    const cleanUsername = username.trim();
    if (!cleanUsername) {
      setError('Please enter your administrator username.');
      return;
    }
    if (!password) {
      setError('Please enter your administrator password.');
      return;
    }

    setIsLoading(true);

    try {
      // Admin credentials are never persisted in localStorage (rememberMe = false)
      const response = await login(cleanUsername, password, false);

      if (response.success && response.user) {
        // Enforce strict administrative authorization boundary:
        if (response.user.role !== 'admin') {
          // Immediately purge session to block non-admin accounts
          authLogout();
          setError('Access denied: This login portal is restricted to system administrators.');
          return;
        }

        onLogin(response.user);
      } else {
        setError(response.message || 'Invalid administrator username or password.');
      }
    } catch (err) {
      setError('Unable to connect to authentication server. Please check backend status.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <div className="login-background" style={{ filter: 'brightness(0.7) contrast(1.1)' }}></div>
      <div
        className="glass-panel screen-enter"
        style={{
          maxWidth: '460px',
          width: '100%',
          margin: '2rem auto',
          padding: '2.25rem 2rem',
          boxSizing: 'border-box',
          border: '1px solid rgba(239, 68, 68, 0.25)',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4)',
        }}
      >
        {/* Administrator Security Header */}
        <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '56px',
              height: '56px',
              borderRadius: '16px',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.35)',
              marginBottom: '0.75rem',
            }}
          >
            <span style={{ fontSize: '1.75rem' }}>🛡️</span>
          </div>

          <div style={{ marginBottom: '0.4rem' }}>
            <span
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.2)',
                color: '#f87171',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                padding: '0.2rem 0.65rem',
                borderRadius: '6px',
                fontSize: '0.725rem',
                fontWeight: 700,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              RESTRICTED ACCESS
            </span>
          </div>

          <h1 style={{ fontSize: '1.65rem', margin: '0.4rem 0 0.25rem 0', color: 'var(--text-primary)' }}>
            System Administration
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>
            Authorized administrative personnel only
          </p>
        </div>

        {/* Error Notice */}
        {error && (
          <div
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              color: '#fca5a5',
              padding: '0.85rem 1rem',
              borderRadius: '10px',
              marginBottom: '1.25rem',
              fontSize: '0.875rem',
              lineHeight: '1.45',
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Admin Username Field */}
          <div className="input-group">
            <label htmlFor="admin-username" style={{ fontWeight: 600 }}>
              Administrator Username
            </label>
            <input
              type="text"
              id="admin-username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. admin"
              required
              disabled={isLoading}
              autoComplete="username"
              style={{ fontSize: '0.95rem' }}
            />
          </div>

          {/* Password Field */}
          <div className="input-group" style={{ marginTop: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="admin-password" style={{ fontWeight: 600 }}>
                Password
              </label>
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--accent-color)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  padding: 0,
                }}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
            <input
              type={showPassword ? 'text' : 'password'}
              id="admin-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter administrator password"
              required
              disabled={isLoading}
              autoComplete="current-password"
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isLoading}
            style={{
              width: '100%',
              marginTop: '1.5rem',
              padding: '0.85rem',
              fontSize: '0.975rem',
              fontWeight: 700,
              backgroundColor: '#b91c1c',
              borderColor: '#991b1b',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            {isLoading ? (
              <>
                <span className="spinner" style={{ width: '16px', height: '16px' }}></span>
                Authenticating Administrator...
              </>
            ) : (
              'Authenticate Administrator'
            )}
          </button>
        </form>

        {/* Return to Farmer Sign In */}
        <div style={{ marginTop: '1.75rem', paddingTop: '1.25rem', borderTop: '1px solid var(--surface-border)', textAlign: 'center' }}>
          <button
            type="button"
            onClick={onSwitchToFarmer}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              fontSize: '0.85rem',
              cursor: 'pointer',
              textDecoration: 'underline',
              padding: 0,
            }}
          >
            ← Return to Farmer Sign In (/)
          </button>
        </div>

      </div>
    </>
  );
};

export default AdminLogin;

