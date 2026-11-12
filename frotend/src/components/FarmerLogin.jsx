import React, { useState, useEffect } from 'react';
import { login, logout as authLogout } from '../services/auth';
import sunriseBg from '../assets/Golden-Hour Rice Field Plowing.png';

/**
 * FarmerLogin Component (Route: '/')
 * Default entry point for agricultural producers.
 * Authenticates using registered Mobile Number + Argon2id Password.
 * Guarantees Farmers cannot access Admin portals and Admins cannot access Farmer Dashboard.
 */
const FarmerLogin = ({ onLogin, onSwitchToRegister, onSwitchToAdmin, onForgotPassword, sessionNotice = '' }) => {
  const [mobileNumber, setMobileNumber] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('rememberedFarmerMobile') || localStorage.getItem('rememberedIdentifier') || '';
    }
    return '';
  });
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(() => {
    if (typeof window !== 'undefined') {
      return Boolean(localStorage.getItem('rememberedFarmerMobile') || localStorage.getItem('rememberedIdentifier'));
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

  // Reset all input fields upon logout or session termination
  useEffect(() => {
    const handleLogoutReset = () => {
      setMobileNumber('');
      setPassword('');
      setRememberMe(false);
      setError('');
      setShowPassword(false);
    };

    window.addEventListener('auth:logout', handleLogoutReset);
    window.addEventListener('auth:session-expired', handleLogoutReset);

    return () => {
      window.removeEventListener('auth:logout', handleLogoutReset);
      window.removeEventListener('auth:session-expired', handleLogoutReset);
    };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const cleanMobile = mobileNumber.trim();
    if (!cleanMobile) {
      setError('Please enter your registered mobile number.');
      return;
    }
    if (!password) {
      setError('Please enter your password.');
      return;
    }

    setIsLoading(true);

    try {
      const response = await login(cleanMobile, password, rememberMe);

      if (response.success && response.user) {
        // Enforce role isolation: Farmer Login is exclusively for farmers
        if (response.user.role !== 'farmer') {
          // Immediately purge session to prevent admin redirection into farmer views
          authLogout();
          setError('This portal is for farmers only. Administrators must sign in at /admin/login.');
          return;
        }

        // Store remembered mobile in localStorage (never tokens!)
        if (rememberMe && typeof window !== 'undefined') {
          localStorage.setItem('rememberedFarmerMobile', cleanMobile);
        } else if (typeof window !== 'undefined') {
          localStorage.removeItem('rememberedFarmerMobile');
        }

        onLogin(response.user);
      } else {
        setError(response.message || 'Invalid mobile number or password.');
      }
    } catch (err) {
      setError('Unable to connect to authentication server. Please check backend status.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <style>{`
        .farmer-split-wrapper {
          min-height: 100vh;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 1.5rem 1rem;
          box-sizing: border-box;
          position: relative;
          z-index: 10;
        }
        .farmer-split-card {
          display: flex;
          flex-direction: row;
          width: 100%;
          max-width: 850px;
          min-height: 440px;
          border-radius: 28px;
          overflow: hidden;
          box-shadow: 0 20px 50px -15px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1);
          background-color: #cdd1c7;
        }
        .farmer-split-left {
          flex: 1 1 50%;
          position: relative;
          background-color: #07583c;
          background-image: linear-gradient(rgba(7, 88, 60, 0.72), rgba(7, 88, 60, 0.82)), url('${sunriseBg}');
          background-size: cover;
          background-position: center;
          background-repeat: no-repeat;
          padding: 2.75rem 2.25rem;
          display: flex;
          flex-direction: column;
          justify-content: center;
          box-sizing: border-box;
          color: #ffffff;
        }
        .farmer-split-right {
          flex: 1 1 50%;
          background-color: #cdd1c7;
          padding: 2.5rem 2.25rem;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          box-sizing: border-box;
        }
        .farmer-input-field {
          width: 100%;
          height: 44px;
          background-color: #ffffff;
          border: 1.5px solid #bdc6bc;
          border-radius: 14px;
          font-size: 0.9rem;
          color: #111827;
          outline: none;
          box-sizing: border-box;
          transition: all 0.2s ease;
        }
        .farmer-input-field:focus {
          border-color: #07583c !important;
          box-shadow: 0 0 0 3px rgba(7, 88, 60, 0.15) !important;
        }
        .farmer-login-btn {
          width: 100%;
          height: 44px;
          background-color: #07583c;
          color: #ffffff;
          font-size: 0.95rem;
          font-weight: 700;
          border-radius: 14px;
          border: none;
          cursor: pointer;
          box-shadow: 0 10px 24px rgba(7, 88, 60, 0.35);
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          transition: all 0.2s ease;
        }
        .farmer-login-btn:hover:not(:disabled) {
          background-color: #064b33;
          box-shadow: 0 12px 28px rgba(7, 88, 60, 0.45);
          transform: translateY(-1px);
        }
        .farmer-login-btn:active:not(:disabled) {
          transform: translateY(0);
        }
        .farmer-login-btn:disabled {
          opacity: 0.75;
          cursor: not-allowed;
        }
        @media (max-width: 840px) {
          .farmer-split-card {
            flex-direction: column !important;
            max-width: 440px !important;
            border-radius: 24px !important;
          }
          .farmer-split-left {
            padding: 2rem 1.75rem !important;
          }
          .farmer-split-right {
            padding: 2rem 1.75rem !important;
          }
        }
        @media (max-width: 480px) {
          .farmer-split-wrapper {
            padding: 1rem 0.75rem !important;
          }
          .farmer-split-card {
            border-radius: 20px !important;
          }
          .farmer-split-left {
            padding: 1.75rem 1.25rem !important;
          }
          .farmer-split-right {
            padding: 1.5rem 1.25rem !important;
          }
        }
      `}</style>

      <div className="login-background"></div>

      <div className="farmer-split-wrapper">
        <div className="farmer-split-card screen-enter">
          
          {/* Left Panel (50% width): Indian Paddy Farmer Sunrise Background with Subtle Dark-Green Overlay */}
          <div
            className="farmer-split-left"
            style={{
              backgroundImage: `linear-gradient(rgba(7, 88, 60, 0.72), rgba(7, 88, 60, 0.82)), url("${sunriseBg}")`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
              backgroundRepeat: 'no-repeat',
            }}
          >
            {/* Paddy Sprout Logo matching reference */}
            <div style={{ marginBottom: '1.25rem', filter: 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3))' }}>
              <svg width="36" height="42" viewBox="0 0 42 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                {/* Sprout canopy arches */}
                <path
                  d="M7 20C6 13 13 8 21 11C29 8 36 13 35 20C30 20 26 17 21 15C16 17 12 20 7 20Z"
                  stroke="#f59e0b"
                  strokeWidth="3.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {/* Sprout center vertical stem */}
                <path
                  d="M21 15V43"
                  stroke="#f59e0b"
                  strokeWidth="3.2"
                  strokeLinecap="round"
                />
              </svg>
            </div>

            {/* Left Heading */}
            <h1
              style={{
                fontSize: '2rem',
                fontWeight: 800,
                lineHeight: 1.18,
                color: '#ffffff',
                margin: '0 0 1rem 0',
                letterSpacing: '-0.02em',
                fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                textShadow: '0 2px 6px rgba(0, 0, 0, 0.45)',
              }}
            >
              Your Paddy Farming<br />Assistant
            </h1>

            {/* Left Description */}
            <p
              style={{
                fontSize: '0.925rem',
                lineHeight: 1.5,
                color: 'rgba(255, 255, 255, 0.95)',
                margin: 0,
                fontWeight: 400,
                maxWidth: '340px',
                textShadow: '0 1px 4px rgba(0, 0, 0, 0.4)',
              }}
            >
              Check your paddy leaves, watch your field's health, and get simple advice to protect your crop.
            </p>
          </div>

          {/* Right Panel (50% width): Light Grey-Green Form */}
          <div className="farmer-split-right">
            <div style={{ width: '100%', maxWidth: '340px' }}>
              
              {/* Accessible Contract Element */}
              <span style={{ position: 'absolute', width: '1px', height: '1px', padding: 0, margin: '-1px', overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', whiteSpace: 'nowrap', border: 0 }}>
                Farmer Sign In
              </span>

              {/* Right Panel Heading */}
              <h2
                style={{
                  fontSize: '1.75rem',
                  fontWeight: 800,
                  color: '#07583c',
                  textAlign: 'center',
                  margin: '0 0 0.35rem 0',
                  letterSpacing: '-0.02em',
                }}
              >
                Paddy Farming Assistant
              </h2>

              {/* Right Panel Subtitle */}
              <p
                style={{
                  fontSize: '0.875rem',
                  fontWeight: 700,
                  color: '#07583c',
                  textAlign: 'center',
                  margin: '0 0 1.25rem 0',
                }}
              >
                Sign in to continue
              </p>

              {/* Error Notice */}
              {error && (
                <div
                  style={{
                    backgroundColor: 'rgba(220, 38, 38, 0.12)',
                    border: '1px solid rgba(220, 38, 38, 0.35)',
                    color: '#991b1b',
                    padding: '0.75rem 1rem',
                    borderRadius: '12px',
                    marginBottom: '1rem',
                    fontSize: '0.85rem',
                    lineHeight: '1.4',
                    fontWeight: 500,
                  }}
                >
                  {error}
                </div>
              )}

              {/* Form */}
              <form onSubmit={handleSubmit}>
                {/* 1. Mobile Number with User Icon */}
                <div style={{ marginBottom: '1rem' }}>
                  <label
                    htmlFor="farmer-mobile"
                    style={{
                      display: 'block',
                      fontSize: '0.875rem',
                      fontWeight: 700,
                      color: '#07583c',
                      marginBottom: '0.45rem',
                    }}
                  >
                    Mobile Number
                  </label>
                  <div style={{ position: 'relative', width: '100%' }}>
                    {/* User Silhouette Icon */}
                    <div
                      style={{
                        position: 'absolute',
                        left: '1rem',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        display: 'flex',
                        alignItems: 'center',
                        pointerEvents: 'none',
                        color: '#4b6354',
                      }}
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                    </div>

                    <input
                      type="tel"
                      id="farmer-mobile"
                      value={mobileNumber}
                      onChange={(e) => setMobileNumber(e.target.value)}
                      placeholder="Enter your mobile number"
                      required
                      disabled={isLoading}
                      autoComplete="tel"
                      className="farmer-input-field"
                      style={{ paddingLeft: '2.75rem', paddingRight: '1rem' }}
                    />
                  </div>
                </div>

                {/* 2. Password with Lock Icon & Green Eye Icon */}
                <div style={{ marginBottom: '1rem' }}>
                  <label
                    htmlFor="farmer-password"
                    style={{
                      display: 'block',
                      fontSize: '0.875rem',
                      fontWeight: 700,
                      color: '#07583c',
                      marginBottom: '0.45rem',
                    }}
                  >
                    Password
                  </label>
                  <div style={{ position: 'relative', width: '100%' }}>
                    {/* Padlock Icon */}
                    <div
                      style={{
                        position: 'absolute',
                        left: '1rem',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        display: 'flex',
                        alignItems: 'center',
                        pointerEvents: 'none',
                        color: '#4b6354',
                      }}
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                    </div>

                    <input
                      type={showPassword ? 'text' : 'password'}
                      id="farmer-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter your password"
                      required
                      disabled={isLoading}
                      autoComplete="current-password"
                      className="farmer-input-field"
                      style={{
                        paddingLeft: '2.75rem',
                        paddingRight: '2.75rem',
                        borderColor: '#07583c', // Distinctive dark green border matching active state in reference
                      }}
                    />

                    {/* 3. Green Eye Icon (Toggle visibility) */}
                    <button
                      type="button"
                      id="toggle-farmer-password"
                      onClick={() => setShowPassword((prev) => !prev)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      title={showPassword ? 'Hide password' : 'Show password'}
                      style={{
                        position: 'absolute',
                        right: '0.75rem',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        padding: '0.25rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#10b981',
                      }}
                    >
                      {showPassword ? (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      ) : (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                          <line x1="1" y1="1" x2="23" y2="23" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                {/* 4. Remember me checkbox & Forgot Password Link */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginTop: '0.85rem',
                    marginBottom: '1.2rem',
                    width: '100%',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <input
                      type="checkbox"
                      id="farmer-remember"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      disabled={isLoading}
                      style={{
                        width: '16px',
                        height: '16px',
                        cursor: 'pointer',
                        accentColor: '#07583c',
                        borderRadius: '4px',
                      }}
                    />
                    <label
                      htmlFor="farmer-remember"
                      style={{
                        fontSize: '0.875rem',
                        color: '#07583c',
                        fontWeight: 600,
                        cursor: 'pointer',
                        userSelect: 'none',
                      }}
                    >
                      Remember me
                    </label>
                  </div>

                  <button
                    type="button"
                    id="farmer-forgot-password-btn"
                    onClick={onForgotPassword}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#07583c',
                      fontSize: '0.825rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      padding: 0,
                      textDecoration: 'none',
                      transition: 'color 0.2s ease',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = '#064b33'; e.currentTarget.style.textDecoration = 'underline'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = '#07583c'; e.currentTarget.style.textDecoration = 'none'; }}
                  >
                    Forgot Password?
                  </button>
                </div>

                {/* 5. Dark green Login button with rounded corners and shadow */}
                <button
                  type="submit"
                  className="farmer-login-btn"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <span className="spinner" style={{ width: '16px', height: '16px', borderTopColor: '#ffffff' }}></span>
                      Signing In...
                    </>
                  ) : (
                    'Login'
                  )}
                </button>
              </form>

              {/* Navigation Links */}
              <div style={{ marginTop: '1.2rem', textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div>
                  <span style={{ fontSize: '0.85rem', color: '#374151', fontWeight: 500 }}>
                    New farmer?{' '}
                  </span>
                  <button
                    type="button"
                    onClick={onSwitchToRegister}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#07583c',
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      padding: 0,
                      textDecoration: 'underline',
                    }}
                  >
                    Register your farm account here
                  </button>
                </div>

                <div>
                  <button
                    type="button"
                    onClick={onSwitchToAdmin}
                    style={{
                      background: 'none',
                      border: '1px solid rgba(7, 88, 60, 0.25)',
                      borderRadius: '8px',
                      color: '#07583c',
                      fontSize: '0.785rem',
                      fontWeight: 600,
                      padding: '0.35rem 0.75rem',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = 'rgba(7, 88, 60, 0.08)';
                      e.currentTarget.style.borderColor = '#07583c';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                      e.currentTarget.style.borderColor = 'rgba(7, 88, 60, 0.25)';
                    }}
                  >
                    🛡️ System Administrator? Sign in at Admin Portal (/admin/login)
                  </button>
                </div>
              </div>

            </div>
          </div>

        </div>
      </div>
    </>
  );
};

export default FarmerLogin;

