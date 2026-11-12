import React, { useState, useEffect, useRef } from 'react';
import { forgotPassword, verifyOtp, resendOtp, resetPassword } from '../services/auth';
import sunriseBg from '../assets/Golden-Hour Rice Field Plowing.png';

/**
 * ForgotPassword Component (Route: '/forgot-password')
 * Implements a secure 4-step Password Reset workflow with Mobile OTP Verification:
 * Step 1: Mobile Number Entry & Dispatch
 * Step 2: 6-Digit OTP Verification with Expiration & Resend Cooldown
 * Step 3: Strong Password Reset & Confirmation
 * Step 4: Success Confirmation & Login Redirection
 */
const ForgotPassword = ({ onSwitchToLogin }) => {
  // Wizard steps: 'mobile' | 'otp' | 'reset' | 'success'
  const [step, setStep] = useState('mobile');

  // Step 1: Mobile state
  const [mobileNumber, setMobileNumber] = useState('');
  const [maskedMobile, setMaskedMobile] = useState('');
  const [sessionId, setSessionId] = useState('');

  // Step 2: OTP state
  const [otpDigits, setOtpDigits] = useState(['', '', '', '', '', '']);
  const [devOtpHint, setDevOtpHint] = useState('');
  const [cooldown, setCooldown] = useState(0);
  const [otpTimeRemaining, setOtpTimeRemaining] = useState(300); // 5 minutes

  // Step 3: Password state
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [resetToken, setResetToken] = useState('');

  // UI status
  const [error, setError] = useState('');
  const [successNotice, setSuccessNotice] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // References for OTP digit inputs
  const otpInputRefs = useRef([]);

  // Timer: 60-second Resend Cooldown
  useEffect(() => {
    let interval = null;
    if (cooldown > 0) {
      interval = setInterval(() => {
        setCooldown((prev) => (prev > 1 ? prev - 1 : 0));
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [cooldown]);

  // Timer: 5-minute OTP Expiration
  useEffect(() => {
    let interval = null;
    if (step === 'otp' && otpTimeRemaining > 0) {
      interval = setInterval(() => {
        setOtpTimeRemaining((prev) => {
          if (prev <= 1) {
            setError('Verification code has expired. Please request a new code.');
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [step, otpTimeRemaining]);

  // Format seconds to MM:SS
  const formatTime = (secs) => {
    const mins = Math.floor(secs / 60);
    const remSecs = secs % 60;
    return `${String(mins).padStart(2, '0')}:${String(remSecs).padStart(2, '0')}`;
  };

  // Password Strength Checklist Checks
  const passHasMinLength = newPassword.length >= 8;
  const passHasUpper = /[A-Z]/.test(newPassword);
  const passHasLower = /[a-z]/.test(newPassword);
  const passHasDigit = /[0-9]/.test(newPassword);
  const passwordsMatch = newPassword.length > 0 && newPassword === confirmPassword;
  const isPasswordValid = passHasMinLength && passHasUpper && passHasLower && passHasDigit && passwordsMatch;

  // --------------------------------------------------------------------------
  // Step 1: Send OTP
  // --------------------------------------------------------------------------
  const handleSendOtp = async (e) => {
    if (e) e.preventDefault();
    setError('');
    setSuccessNotice('');

    const clean = mobileNumber.trim();
    if (!clean) {
      setError('Please enter your registered mobile number.');
      return;
    }

    setIsLoading(true);

    try {
      const resp = await forgotPassword(clean);
      if (resp.success) {
        setSessionId(resp.sessionId);
        setMaskedMobile(resp.maskedMobile || clean);
        setCooldown(resp.cooldownSeconds || 60);
        setOtpTimeRemaining(resp.expiresInSeconds || 300);
        setOtpDigits(['', '', '', '', '', '']);
        if (resp.devOtp) {
          setDevOtpHint(resp.devOtp);
        }
        setSuccessNotice('Verification code sent successfully!');
        setStep('otp');
        // Auto-focus first OTP input on transition
        setTimeout(() => {
          if (otpInputRefs.current[0]) {
            otpInputRefs.current[0].focus();
          }
        }, 150);
      } else {
        setError(resp.message || 'Unable to send verification code.');
      }
    } catch {
      setError('Failed to connect to authentication server. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // --------------------------------------------------------------------------
  // Step 2: Handle OTP Input & Paste
  // --------------------------------------------------------------------------
  const handleOtpDigitChange = (index, value) => {
    setError('');
    // Accept only digits
    const cleaned = value.replace(/\D/g, '');
    const newDigits = [...otpDigits];

    if (!cleaned) {
      newDigits[index] = '';
      setOtpDigits(newDigits);
      return;
    }

    // Handle single character
    newDigits[index] = cleaned[cleaned.length - 1];
    setOtpDigits(newDigits);

    // Auto-advance to next input
    if (index < 5 && cleaned) {
      if (otpInputRefs.current[index + 1]) {
        otpInputRefs.current[index + 1].focus();
      }
    }
  };

  const handleOtpKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otpDigits[index] && index > 0) {
      if (otpInputRefs.current[index - 1]) {
        otpInputRefs.current[index - 1].focus();
      }
    }
  };

  const handleOtpPaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!pasted) return;

    const newDigits = [...otpDigits];
    for (let i = 0; i < 6; i++) {
      newDigits[i] = pasted[i] || '';
    }
    setOtpDigits(newDigits);

    const nextIndex = Math.min(pasted.length, 5);
    if (otpInputRefs.current[nextIndex]) {
      otpInputRefs.current[nextIndex].focus();
    }
  };

  // --------------------------------------------------------------------------
  // Step 2: Resend OTP
  // --------------------------------------------------------------------------
  const handleResendOtp = async () => {
    if (cooldown > 0 || isLoading) return;
    setError('');
    setSuccessNotice('');
    setIsLoading(true);

    try {
      const resp = await resendOtp(sessionId);
      if (resp.success) {
        setCooldown(resp.cooldownSeconds || 60);
        setOtpTimeRemaining(resp.expiresInSeconds || 300);
        setOtpDigits(['', '', '', '', '', '']);
        if (resp.devOtp) {
          setDevOtpHint(resp.devOtp);
        }
        setSuccessNotice('A fresh verification code has been dispatched.');
        if (otpInputRefs.current[0]) {
          otpInputRefs.current[0].focus();
        }
      } else {
        setError(resp.message || 'Unable to resend verification code.');
      }
    } catch {
      setError('Unable to request a new code. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // --------------------------------------------------------------------------
  // Step 2: Verify OTP
  // --------------------------------------------------------------------------
  const handleVerifyOtp = async (e) => {
    if (e) e.preventDefault();
    setError('');
    setSuccessNotice('');

    const fullOtp = otpDigits.join('');
    if (fullOtp.length !== 6) {
      setError('Please enter all 6 digits of the verification code.');
      return;
    }

    if (otpTimeRemaining <= 0) {
      setError('Verification code has expired. Please request a new code.');
      return;
    }

    setIsLoading(true);

    try {
      const resp = await verifyOtp(sessionId, fullOtp);
      if (resp.success && resp.resetToken) {
        setResetToken(resp.resetToken);
        setSuccessNotice('Mobile number verified! Please create a new password.');
        setStep('reset');
      } else {
        setError(resp.message || 'Incorrect verification code.');
      }
    } catch {
      setError('Verification failed due to a server connection error.');
    } finally {
      setIsLoading(false);
    }
  };

  // --------------------------------------------------------------------------
  // Step 3: Complete Password Reset
  // --------------------------------------------------------------------------
  const handleResetPassword = async (e) => {
    if (e) e.preventDefault();
    setError('');
    setSuccessNotice('');

    if (!newPassword || newPassword.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (!passHasUpper || !passHasLower || !passHasDigit) {
      setError('Password must contain uppercase, lowercase, and numeric characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);

    try {
      const resp = await resetPassword(resetToken, newPassword, confirmPassword);
      if (resp.success) {
        setStep('success');
      } else {
        setError(resp.message || 'Unable to update password. Please try again.');
      }
    } catch {
      setError('Failed to update password. Please check your connection.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <style>{`
        .forgot-split-wrapper {
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
        .forgot-split-card {
          display: flex;
          flex-direction: row;
          width: 100%;
          max-width: 850px;
          min-height: 480px;
          border-radius: 28px;
          overflow: hidden;
          box-shadow: 0 20px 50px -15px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1);
          background-color: #cdd1c7;
        }
        .forgot-split-left {
          flex: 1 1 50%;
          position: relative;
          background-color: #07583c;
          background-image: linear-gradient(rgba(7, 88, 60, 0.75), rgba(7, 88, 60, 0.85)), url('${sunriseBg}');
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
        .forgot-split-right {
          flex: 1 1 50%;
          background-color: #cdd1c7;
          padding: 2.25rem 2rem;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          box-sizing: border-box;
        }
        .forgot-input-field {
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
        .forgot-input-field:focus {
          border-color: #07583c !important;
          box-shadow: 0 0 0 3px rgba(7, 88, 60, 0.15) !important;
        }
        .otp-box {
          width: 44px;
          height: 50px;
          text-align: center;
          font-size: 1.25rem;
          font-weight: 700;
          color: #07583c;
          background-color: #ffffff;
          border: 1.5px solid #bdc6bc;
          border-radius: 12px;
          outline: none;
          transition: all 0.2s ease;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        .otp-box:focus {
          border-color: #07583c !important;
          box-shadow: 0 0 0 3px rgba(7, 88, 60, 0.2) !important;
          transform: translateY(-1px);
        }
        .forgot-action-btn {
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
        .forgot-action-btn:hover:not(:disabled) {
          background-color: #064b33;
          box-shadow: 0 12px 28px rgba(7, 88, 60, 0.45);
          transform: translateY(-1px);
        }
        .forgot-action-btn:active:not(:disabled) {
          transform: translateY(0);
        }
        .forgot-action-btn:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }
        .step-progress-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background-color: #bdc6bc;
          transition: all 0.3s ease;
        }
        .step-progress-dot.active {
          width: 22px;
          border-radius: 6px;
          background-color: #07583c;
        }
        .checklist-item {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          font-size: 0.75rem;
          color: #4b5563;
          transition: color 0.2s ease;
        }
        .checklist-item.valid {
          color: #065f46;
          font-weight: 600;
        }
        @media (max-width: 840px) {
          .forgot-split-card {
            flex-direction: column !important;
            max-width: 440px !important;
            border-radius: 24px !important;
          }
          .forgot-split-left {
            padding: 2rem 1.75rem !important;
          }
          .forgot-split-right {
            padding: 2rem 1.75rem !important;
          }
        }
      `}</style>

      <div className="login-background"></div>

      <div className="forgot-split-wrapper">
        <div className="forgot-split-card screen-enter">
          
          {/* Left Panel: Branding & Security Assurance */}
          <div className="forgot-split-left">
            {/* Logo */}
            <div style={{ marginBottom: '1.25rem', filter: 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3))' }}>
              <svg width="36" height="42" viewBox="0 0 42 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path
                  d="M7 20C6 13 13 8 21 11C29 8 36 13 35 20C30 20 26 17 21 15C16 17 12 20 7 20Z"
                  stroke="#f59e0b"
                  strokeWidth="3.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path d="M21 15V43" stroke="#f59e0b" strokeWidth="3.2" strokeLinecap="round" />
              </svg>
            </div>

            <h1
              style={{
                fontSize: '1.9rem',
                fontWeight: 800,
                lineHeight: 1.2,
                color: '#ffffff',
                margin: '0 0 0.85rem 0',
                letterSpacing: '-0.02em',
                textShadow: '0 2px 6px rgba(0, 0, 0, 0.45)',
              }}
            >
              Account Security &amp;<br />Password Recovery
            </h1>

            <p
              style={{
                fontSize: '0.9rem',
                lineHeight: 1.5,
                color: 'rgba(255, 255, 255, 0.95)',
                margin: '0 0 1.5rem 0',
                maxWidth: '340px',
                textShadow: '0 1px 4px rgba(0, 0, 0, 0.4)',
              }}
            >
              Secure mobile OTP verification protects your farm data, field health records, and mandi sales information.
            </p>

            {/* Security Highlights */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.825rem', opacity: 0.9 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <svg width="16" height="16" fill="none" stroke="#f59e0b" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <span>Argon2id cryptographic password hashing</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <svg width="16" height="16" fill="none" stroke="#f59e0b" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <span>5-minute expiring single-use verification code</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <svg width="16" height="16" fill="none" stroke="#f59e0b" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <span>Brute-force protection &amp; attempt limits</span>
              </div>
            </div>
          </div>

          {/* Right Panel: Interactive Step Wizard */}
          <div className="forgot-split-right">
            <div style={{ width: '100%', maxWidth: '340px' }}>

              {/* Progress Bar Dots */}
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.4rem', marginBottom: '1rem' }}>
                <div className={`step-progress-dot ${step === 'mobile' ? 'active' : ''}`} title="Mobile Entry" />
                <div className={`step-progress-dot ${step === 'otp' ? 'active' : ''}`} title="OTP Verification" />
                <div className={`step-progress-dot ${step === 'reset' ? 'active' : ''}`} title="New Password" />
                <div className={`step-progress-dot ${step === 'success' ? 'active' : ''}`} title="Complete" />
              </div>

              {/* Header Title */}
              <h2
                style={{
                  fontSize: '1.5rem',
                  fontWeight: 800,
                  color: '#07583c',
                  textAlign: 'center',
                  margin: '0 0 0.25rem 0',
                  letterSpacing: '-0.02em',
                }}
              >
                {step === 'mobile' && 'Forgot Password?'}
                {step === 'otp' && 'Enter Verification Code'}
                {step === 'reset' && 'Create New Password'}
                {step === 'success' && 'Password Updated!'}
              </h2>

              <p
                style={{
                  fontSize: '0.85rem',
                  color: '#4b6354',
                  textAlign: 'center',
                  margin: '0 0 1.25rem 0',
                  fontWeight: 500,
                }}
              >
                {step === 'mobile' && 'Enter your registered mobile number to receive a secure OTP'}
                {step === 'otp' && `Sent to ${maskedMobile || 'your mobile'}`}
                {step === 'reset' && 'Choose a strong password to protect your farm account'}
                {step === 'success' && 'Your account credentials have been updated successfully'}
              </p>

              {/* Error Notice */}
              {error && (
                <div
                  style={{
                    backgroundColor: 'rgba(220, 38, 38, 0.12)',
                    border: '1px solid rgba(220, 38, 38, 0.35)',
                    color: '#991b1b',
                    padding: '0.65rem 0.85rem',
                    borderRadius: '12px',
                    marginBottom: '1rem',
                    fontSize: '0.825rem',
                    lineHeight: '1.4',
                    fontWeight: 500,
                  }}
                >
                  {error}
                </div>
              )}

              {/* Success Notice */}
              {successNotice && step !== 'success' && (
                <div
                  style={{
                    backgroundColor: 'rgba(6, 95, 70, 0.12)',
                    border: '1px solid rgba(6, 95, 70, 0.35)',
                    color: '#065f46',
                    padding: '0.65rem 0.85rem',
                    borderRadius: '12px',
                    marginBottom: '1rem',
                    fontSize: '0.825rem',
                    lineHeight: '1.4',
                    fontWeight: 500,
                  }}
                >
                  {successNotice}
                </div>
              )}

              {/* Dev Mode OTP Indicator (Development Only) */}
              {devOtpHint && (step === 'otp') && (
                <div
                  style={{
                    backgroundColor: '#fef3c7',
                    border: '1px dashed #d97706',
                    color: '#92400e',
                    padding: '0.5rem 0.75rem',
                    borderRadius: '10px',
                    marginBottom: '1rem',
                    fontSize: '0.775rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <span>
                    <strong>Dev Code:</strong> {devOtpHint}
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      const digits = devOtpHint.split('').slice(0, 6);
                      setOtpDigits(digits);
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#b45309',
                      fontWeight: 700,
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                      textDecoration: 'underline',
                    }}
                  >
                    Auto-Fill
                  </button>
                </div>
              )}

              {/* ========================================================= */}
              {/* STEP 1: MOBILE NUMBER ENTRY */}
              {/* ========================================================= */}
              {step === 'mobile' && (
                <form onSubmit={handleSendOtp}>
                  <div style={{ marginBottom: '1.25rem' }}>
                    <label
                      htmlFor="forgot-mobile-input"
                      style={{
                        display: 'block',
                        fontSize: '0.85rem',
                        fontWeight: 700,
                        color: '#07583c',
                        marginBottom: '0.45rem',
                      }}
                    >
                      Registered Mobile Number
                    </label>
                    <div style={{ position: 'relative', width: '100%' }}>
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
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                        </svg>
                      </div>
                      <input
                        type="tel"
                        id="forgot-mobile-input"
                        value={mobileNumber}
                        onChange={(e) => setMobileNumber(e.target.value)}
                        placeholder="e.g. 9876543210"
                        required
                        disabled={isLoading}
                        autoFocus
                        autoComplete="tel"
                        className="forgot-input-field"
                        style={{ paddingLeft: '2.75rem', paddingRight: '1rem' }}
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    id="send-otp-btn"
                    className="forgot-action-btn"
                    disabled={isLoading}
                  >
                    {isLoading ? 'Sending Verification Code...' : 'Send OTP'}
                  </button>
                </form>
              )}

              {/* ========================================================= */}
              {/* STEP 2: 6-DIGIT OTP VERIFICATION */}
              {/* ========================================================= */}
              {step === 'otp' && (
                <form onSubmit={handleVerifyOtp}>
                  <div style={{ marginBottom: '1.25rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
                      <span style={{ fontSize: '0.825rem', fontWeight: 700, color: '#07583c' }}>
                        6-Digit Code
                      </span>
                      <span style={{ fontSize: '0.775rem', color: otpTimeRemaining <= 60 ? '#dc2626' : '#4b6354', fontWeight: 600 }}>
                        Expires in {formatTime(otpTimeRemaining)}
                      </span>
                    </div>

                    {/* 6 Digit Input Boxes */}
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        gap: '0.4rem',
                      }}
                      onPaste={handleOtpPaste}
                    >
                      {otpDigits.map((digit, index) => (
                        <input
                          key={index}
                          ref={(el) => (otpInputRefs.current[index] = el)}
                          type="text"
                          inputMode="numeric"
                          maxLength={1}
                          value={digit}
                          onChange={(e) => handleOtpDigitChange(index, e.target.value)}
                          onKeyDown={(e) => handleOtpKeyDown(index, e)}
                          disabled={isLoading}
                          className="otp-box"
                          autoComplete="one-time-code"
                        />
                      ))}
                    </div>
                  </div>

                  {/* Resend OTP Bar */}
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '1.25rem',
                      fontSize: '0.8rem',
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => setStep('mobile')}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#4b6354',
                        cursor: 'pointer',
                        padding: 0,
                        textDecoration: 'underline',
                      }}
                    >
                      Change Number
                    </button>

                    <button
                      type="button"
                      id="resend-otp-btn"
                      onClick={handleResendOtp}
                      disabled={cooldown > 0 || isLoading}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: cooldown > 0 ? '#9ca3af' : '#07583c',
                        fontWeight: 700,
                        cursor: cooldown > 0 ? 'not-allowed' : 'pointer',
                        padding: 0,
                        textDecoration: cooldown > 0 ? 'none' : 'underline',
                      }}
                    >
                      {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend OTP'}
                    </button>
                  </div>

                  <button
                    type="submit"
                    id="verify-otp-btn"
                    className="forgot-action-btn"
                    disabled={isLoading || otpDigits.join('').length !== 6}
                  >
                    {isLoading ? 'Verifying Code...' : 'Verify & Continue'}
                  </button>
                </form>
              )}

              {/* ========================================================= */}
              {/* STEP 3: NEW PASSWORD & CONFIRM PASSWORD */}
              {/* ========================================================= */}
              {step === 'reset' && (
                <form onSubmit={handleResetPassword}>
                  {/* New Password */}
                  <div style={{ marginBottom: '0.85rem' }}>
                    <label
                      htmlFor="new-password-input"
                      style={{
                        display: 'block',
                        fontSize: '0.825rem',
                        fontWeight: 700,
                        color: '#07583c',
                        marginBottom: '0.35rem',
                      }}
                    >
                      New Password
                    </label>
                    <div style={{ position: 'relative', width: '100%' }}>
                      <input
                        type={showNewPassword ? 'text' : 'password'}
                        id="new-password-input"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        placeholder="At least 8 characters"
                        required
                        disabled={isLoading}
                        autoComplete="new-password"
                        className="forgot-input-field"
                        style={{ paddingLeft: '1rem', paddingRight: '2.5rem' }}
                      />
                      <button
                        type="button"
                        onClick={() => setShowNewPassword((prev) => !prev)}
                        style={{
                          position: 'absolute',
                          right: '0.75rem',
                          top: '50%',
                          transform: 'translateY(-50%)',
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          color: '#10b981',
                          padding: '0.25rem',
                        }}
                      >
                        {showNewPassword ? (
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                        ) : (
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                            <line x1="1" y1="1" x2="23" y2="23" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Confirm Password */}
                  <div style={{ marginBottom: '0.85rem' }}>
                    <label
                      htmlFor="confirm-password-input"
                      style={{
                        display: 'block',
                        fontSize: '0.825rem',
                        fontWeight: 700,
                        color: '#07583c',
                        marginBottom: '0.35rem',
                      }}
                    >
                      Confirm New Password
                    </label>
                    <div style={{ position: 'relative', width: '100%' }}>
                      <input
                        type={showConfirmPassword ? 'text' : 'password'}
                        id="confirm-password-input"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="Re-enter new password"
                        required
                        disabled={isLoading}
                        autoComplete="new-password"
                        className="forgot-input-field"
                        style={{ paddingLeft: '1rem', paddingRight: '2.5rem' }}
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword((prev) => !prev)}
                        style={{
                          position: 'absolute',
                          right: '0.75rem',
                          top: '50%',
                          transform: 'translateY(-50%)',
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          color: '#10b981',
                          padding: '0.25rem',
                        }}
                      >
                        {showConfirmPassword ? (
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                        ) : (
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                            <line x1="1" y1="1" x2="23" y2="23" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Password Strength Checklist */}
                  <div
                    style={{
                      backgroundColor: 'rgba(255, 255, 255, 0.7)',
                      padding: '0.65rem 0.85rem',
                      borderRadius: '12px',
                      marginBottom: '1.25rem',
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr',
                      gap: '0.35rem',
                    }}
                  >
                    <div className={`checklist-item ${passHasMinLength ? 'valid' : ''}`}>
                      <span>{passHasMinLength ? '✓' : '○'}</span>
                      <span>8+ characters</span>
                    </div>
                    <div className={`checklist-item ${passHasUpper ? 'valid' : ''}`}>
                      <span>{passHasUpper ? '✓' : '○'}</span>
                      <span>Uppercase (A-Z)</span>
                    </div>
                    <div className={`checklist-item ${passHasLower ? 'valid' : ''}`}>
                      <span>{passHasLower ? '✓' : '○'}</span>
                      <span>Lowercase (a-z)</span>
                    </div>
                    <div className={`checklist-item ${passHasDigit ? 'valid' : ''}`}>
                      <span>{passHasDigit ? '✓' : '○'}</span>
                      <span>Number (0-9)</span>
                    </div>
                    <div
                      className={`checklist-item ${passwordsMatch ? 'valid' : ''}`}
                      style={{ gridColumn: 'span 2' }}
                    >
                      <span>{passwordsMatch ? '✓' : '○'}</span>
                      <span>Passwords match</span>
                    </div>
                  </div>

                  <button
                    type="submit"
                    id="submit-reset-password-btn"
                    className="forgot-action-btn"
                    disabled={isLoading || !isPasswordValid}
                  >
                    {isLoading ? 'Updating Password...' : 'Reset Password'}
                  </button>
                </form>
              )}

              {/* ========================================================= */}
              {/* STEP 4: SUCCESS CONFIRMATION */}
              {/* ========================================================= */}
              {step === 'success' && (
                <div style={{ textAlign: 'center', padding: '0.5rem 0' }}>
                  <div
                    style={{
                      width: '56px',
                      height: '56px',
                      borderRadius: '50%',
                      backgroundColor: '#d1fae5',
                      color: '#065f46',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 1.25rem auto',
                    }}
                  >
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>

                  <p
                    style={{
                      fontSize: '0.9rem',
                      color: '#1f2937',
                      lineHeight: 1.5,
                      marginBottom: '1.5rem',
                      fontWeight: 500,
                    }}
                  >
                    Your password has been securely updated. You can now log in to Paddy Farming Assistant with your new credentials.
                  </p>

                  <button
                    type="button"
                    onClick={onSwitchToLogin}
                    className="forgot-action-btn"
                  >
                    Proceed to Login
                  </button>
                </div>
              )}

              {/* Bottom Navigation: Return to Login */}
              {step !== 'success' && (
                <div style={{ marginTop: '1.25rem', textAlign: 'center' }}>
                  <button
                    type="button"
                    onClick={onSwitchToLogin}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#07583c',
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      padding: '0.25rem',
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 12H5M12 19l-7-7 7-7" />
                    </svg>
                    <span>Return to Login</span>
                  </button>
                </div>
              )}

            </div>
          </div>

        </div>
      </div>
    </>
  );
};

export default ForgotPassword;

