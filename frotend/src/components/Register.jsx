import React, { useState } from 'react';
import { registerFarmer } from '../services/auth';

const Register = ({ onSwitchToLogin, onRegisterSuccess }) => {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
    mobile_number: '',
    full_name: '',
    farm_name: '',
    village: '',
  });

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Client-side validations consistent with backend rules
    if (!formData.username || formData.username.trim().length < 3) {
      setError('Farmer username must be at least 3 characters long.');
      return;
    }

    if (!formData.password || formData.password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    // Mobile Number - Mandatory validation
    const trimmedMobile = (formData.mobile_number || '').trim();
    if (!trimmedMobile) {
      setError('Mobile number is required.');
      return;
    }

    const cleanMobile = trimmedMobile.replace(/[\s\-\.\(\)]/g, '');
    const indianMobileRegex = /^(\+91|0)?[6-9]\d{9}$/;
    if (!indianMobileRegex.test(cleanMobile)) {
      setError('Please enter a valid 10-digit Indian mobile number (e.g. 9876543210 or +919876543210).');
      return;
    }

    // Full Name - Mandatory validation
    const trimmedFullName = (formData.full_name || '').trim();
    if (!trimmedFullName) {
      setError('Full name is required.');
      return;
    }

    setIsLoading(true);

    try {
      const response = await registerFarmer({
        username: formData.username.trim(),
        password: formData.password,
        mobile_number: trimmedMobile,
        full_name: trimmedFullName,
        farm_name: formData.farm_name ? formData.farm_name.trim() : undefined,
        village: formData.village ? formData.village.trim() : undefined,
      });

      if (response.success) {
        setSuccess('Farmer registered successfully! Dedicated database schema provisioned. Redirecting to login...');
        setTimeout(() => {
          if (onRegisterSuccess) {
            onRegisterSuccess(formData.username);
          } else if (onSwitchToLogin) {
            onSwitchToLogin();
          }
        }, 1800);
      } else {
        setError(response.message || 'Registration failed. Please check your details.');
      }
    } catch (err) {
      setError('An unexpected error occurred during registration.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <div className="login-background"></div>
      <div
        className="glass-panel screen-enter"
        style={{
          maxWidth: '520px',
          width: '100%',
          margin: '2rem auto',
          padding: '2.25rem 2rem',
          boxSizing: 'border-box',
        }}
      >
        {/* Header with Farmer Badge */}
        <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '54px',
              height: '54px',
              borderRadius: '16px',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              marginBottom: '0.75rem',
            }}
          >
            <span style={{ fontSize: '1.65rem' }}>🌾</span>
          </div>
          <h1 style={{ fontSize: '1.75rem', margin: '0 0 0.35rem 0', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
            Paddy Farming Assistant
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.925rem', margin: 0, fontWeight: 500 }}>
            Register New Farmer Account
          </p>
          <span style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', opacity: 0.8, display: 'block', marginTop: '0.2rem' }}>
            A dedicated database schema and isolated workspace will be provisioned
          </span>
        </div>

        {error && (
          <div
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.35)',
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

        {success && (
          <div
            style={{
              backgroundColor: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              color: '#86efac',
              padding: '0.85rem 1rem',
              borderRadius: '10px',
              marginBottom: '1.25rem',
              fontSize: '0.875rem',
              lineHeight: '1.45',
            }}
          >
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ width: '100%', boxSizing: 'border-box' }}>
          {/* Farmer Username */}
          <div className="input-group">
            <label htmlFor="reg-username">Farmer Username *</label>
            <input
              type="text"
              id="reg-username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder="Enter your farmer username"
              required
              minLength={3}
              maxLength={100}
              disabled={isLoading}
              autoComplete="username"
            />
          </div>

          {/* Password & Confirm Password with Green Visibility Eye Icons */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
              gap: '0.85rem',
              width: '100%',
              marginBottom: '1.15rem',
            }}
          >
            {/* Password */}
            <div className="input-group" style={{ minWidth: 0, marginBottom: 0 }}>
              <label htmlFor="reg-password">Password *</label>
              <div style={{ position: 'relative', width: '100%' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="reg-password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Min 8 chars"
                  required
                  minLength={8}
                  disabled={isLoading}
                  autoComplete="new-password"
                  style={{ paddingRight: '2.4rem' }}
                />
                <button
                  type="button"
                  id="toggle-reg-password"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  title={showPassword ? 'Hide password' : 'Show password'}
                  style={{
                    position: 'absolute',
                    right: '0.65rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '0.2rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#10b981',
                  }}
                >
                  {showPassword ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* Confirm Password */}
            <div className="input-group" style={{ minWidth: 0, marginBottom: 0 }}>
              <label htmlFor="reg-confirm-password">Confirm Password *</label>
              <div style={{ position: 'relative', width: '100%' }}>
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  id="reg-confirm-password"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="Repeat password"
                  required
                  minLength={8}
                  disabled={isLoading}
                  autoComplete="new-password"
                  style={{ paddingRight: '2.4rem' }}
                />
                <button
                  type="button"
                  id="toggle-reg-confirm-password"
                  onClick={() => setShowConfirmPassword((prev) => !prev)}
                  aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                  title={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                  style={{
                    position: 'absolute',
                    right: '0.65rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '0.2rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#10b981',
                  }}
                >
                  {showConfirmPassword ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Mobile Number - Mandatory */}
          <div className="input-group">
            <label htmlFor="reg-mobile">Mobile Number *</label>
            <input
              type="tel"
              id="reg-mobile"
              name="mobile_number"
              value={formData.mobile_number}
              onChange={handleChange}
              placeholder="Enter your mobile number"
              required
              maxLength={20}
              disabled={isLoading}
              autoComplete="tel"
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
              Enables secure mobile-based password login.
            </span>
          </div>

          {/* Full Name - Mandatory */}
          <div className="input-group">
            <label htmlFor="reg-fullname">Full Name *</label>
            <input
              type="text"
              id="reg-fullname"
              name="full_name"
              value={formData.full_name}
              onChange={handleChange}
              placeholder="Enter your full name"
              required
              maxLength={150}
              disabled={isLoading}
              autoComplete="name"
            />
          </div>

          {/* Farm Name & Village (2-column grid with minWidth 0) */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
              gap: '0.85rem',
              width: '100%',
              marginBottom: '1.25rem',
            }}
          >
            <div className="input-group" style={{ minWidth: 0, marginBottom: 0 }}>
              <label htmlFor="reg-farmname">Farm Name (Optional)</label>
              <input
                type="text"
                id="reg-farmname"
                name="farm_name"
                value={formData.farm_name}
                onChange={handleChange}
                placeholder="e.g. Delta Farm"
                maxLength={150}
                disabled={isLoading}
              />
            </div>

            <div className="input-group" style={{ minWidth: 0, marginBottom: 0 }}>
              <label htmlFor="reg-village">Village / Locality (Optional)</label>
              <input
                type="text"
                id="reg-village"
                name="village"
                value={formData.village}
                onChange={handleChange}
                placeholder="e.g. Thanjavur"
                maxLength={100}
                disabled={isLoading}
              />
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isLoading}
            style={{
              width: '100%',
              marginTop: '0.5rem',
              padding: '0.85rem',
              fontSize: '1rem',
              fontWeight: 600,
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            {isLoading ? (
              <>
                <span className="spinner" style={{ width: '16px', height: '16px' }}></span>
                Provisioning Workspace...
              </>
            ) : (
              'Register as Farmer'
            )}
          </button>

          {/* Return to Sign In */}
          <div style={{ textAlign: 'center', marginTop: '1.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--surface-border)', fontSize: '0.875rem' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Already have an account? </span>
            <button
              type="button"
              onClick={onSwitchToLogin}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-color)',
                cursor: 'pointer',
                fontWeight: 600,
                textDecoration: 'underline',
                padding: 0,
              }}
            >
              Sign In
            </button>
          </div>
        </form>
      </div>
    </>
  );
};

export default Register;
