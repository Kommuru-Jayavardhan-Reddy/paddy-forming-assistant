import React, { useState, useEffect, useCallback } from 'react';
import FarmerLogin from './components/FarmerLogin';
import AdminLogin from './components/AdminLogin';
import Register from './components/Register';
import ForgotPassword from './components/ForgotPassword';
import Welcome from './components/Welcome';
import Dashboard from './components/Dashboard';
import AdminDashboard from './components/AdminDashboard';
import {
  getAuthUser,
  logout as authLogout,
  isAuthenticated,
  verifySessionWithServer
} from './services/auth';

/**
 * Normalizes URL path into standard application routes:
 * - '/' or '/farmer/login' -> Farmer Login
 * - '/admin/login' -> Admin Login
 * - '/register' -> Farmer Registration
 * - '/farmer/dashboard' -> Farmer Dashboard
 * - '/admin/dashboard' -> Admin Dashboard
 */
const getNormalizedPath = () => {
  if (typeof window === 'undefined') return '/';
  const rawPath = window.location.pathname.toLowerCase().replace(/\/+$/, '') || '/';
  if (rawPath === '/farmer/login') return '/';
  if (rawPath === '/admin') return '/admin/login';
  if (rawPath === '/farmer') return '/farmer/dashboard';
  if (rawPath === '/forgot' || rawPath === '/forgot-password') return '/forgot-password';
  return rawPath;
};

function App() {
  const [currentUser, setCurrentUser] = useState(() => getAuthUser());
  const [sessionExpiredNotice, setSessionExpiredNotice] = useState('');
  const [currentPath, setCurrentPath] = useState(getNormalizedPath);

  // Synchronize screen state for test suite backward compatibility and rendering
  const [screen, setScreen] = useState(() => {
    const user = getAuthUser();
    const path = getNormalizedPath();

    if (path === '/admin/login') return 'admin_login';
    if (path === '/register') return 'register';
    if (path === '/forgot-password') return 'forgot_password';
    if (path === '/admin/dashboard' && user?.role === 'admin') return 'admin_dashboard';
    if (path === '/farmer/dashboard' && user?.role === 'farmer') return 'dashboard';

    if (!user || !user.token) {
      if (path === '/admin/login') return 'admin_login';
      if (path === '/forgot-password') return 'forgot_password';
      return 'login';
    }
    return user.role === 'admin' ? 'admin_dashboard' : 'dashboard';
  });

  // Centralized route navigation with HTML5 History API
  const navigate = useCallback((toPath, replace = false) => {
    const targetPath = toPath.toLowerCase().replace(/\/+$/, '') || '/';
    if (typeof window !== 'undefined') {
      if (replace) {
        window.history.replaceState(null, '', targetPath);
      } else if (window.location.pathname !== targetPath) {
        window.history.pushState(null, '', targetPath);
      }
    }
    setCurrentPath(targetPath);

    // Sync legacy screen state
    if (targetPath === '/admin/login') setScreen('admin_login');
    else if (targetPath === '/register') setScreen('register');
    else if (targetPath === '/forgot-password') setScreen('forgot_password');
    else if (targetPath === '/admin/dashboard') setScreen('admin_dashboard');
    else if (targetPath === '/farmer/dashboard') setScreen('dashboard');
    else setScreen('login');
  }, []);

  // Popstate listener for browser Back/Forward navigation
  useEffect(() => {
    const handlePopState = () => {
      const path = getNormalizedPath();
      setCurrentPath(path);
      if (path === '/admin/login') setScreen('admin_login');
      else if (path === '/register') setScreen('register');
      else if (path === '/forgot-password') setScreen('forgot_password');
      else if (path === '/admin/dashboard') setScreen('admin_dashboard');
      else if (path === '/farmer/dashboard') setScreen('dashboard');
      else setScreen('login');
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Server-authoritative session synchronization and role enforcement
  useEffect(() => {
    let isMounted = true;

    const syncAndVerify = async () => {
      const user = getAuthUser();
      const path = getNormalizedPath();

      if (!user || !user.token) {
        if (isMounted) {
          setCurrentUser(null);
          // Protect private dashboards against unauthenticated access:
          if (path === '/farmer/dashboard') {
            navigate('/', true);
          } else if (path === '/admin/dashboard') {
            navigate('/admin/login', true);
          }
        }
        return;
      }

      // Authoritative server-side verification via /api/v1/auth/me
      const verification = await verifySessionWithServer();
      if (!isMounted) return;

      if (verification.valid && verification.user) {
        setCurrentUser(verification.user);

        // Strict cross-role isolation:
        if (verification.user.role === 'admin') {
          // Administrator cannot access farmer dashboard or public farmer login
          if (path === '/' || path === '/register' || path === '/farmer/dashboard') {
            navigate('/admin/dashboard', true);
          } else if (path === '/admin/login') {
            navigate('/admin/dashboard', true);
          }
        } else if (verification.user.role === 'farmer') {
          // Farmer cannot access admin portal or admin dashboard
          if (path === '/admin/login' || path === '/admin/dashboard' || path === '/farmer/dashboard') {
            if (typeof window !== 'undefined' && typeof window.goToWelcomePage === 'function') {
              window.goToWelcomePage(verification.user);
            }
          }
        }
      } else if (!verification.valid) {
        setCurrentUser(null);
        const notice = verification.reason === 'forbidden'
          ? 'Account is inactive or disabled.'
          : 'Your session has expired. Please sign in again.';
        setSessionExpiredNotice(notice);

        if (path.startsWith('/admin')) {
          navigate('/admin/login', true);
        } else {
          navigate('/', true);
        }
      }
    };

    syncAndVerify();

    // Centralized event listeners
    const handleSessionExpired = (e) => {
      if (isMounted) {
        setCurrentUser(null);
        setSessionExpiredNotice(e?.detail?.message || 'Session expired. Please log in again.');
        if (getNormalizedPath().startsWith('/admin')) {
          navigate('/admin/login', true);
        } else {
          navigate('/', true);
        }
      }
    };

    const handleExternalLogout = () => {
      if (isMounted) {
        setCurrentUser(null);
        setSessionExpiredNotice('');
        if (getNormalizedPath().startsWith('/admin')) {
          navigate('/admin/login', true);
        } else {
          navigate('/', true);
        }
      }
    };

    window.addEventListener('auth:session-expired', handleSessionExpired);
    window.addEventListener('auth:logout', handleExternalLogout);

    return () => {
      isMounted = false;
      window.removeEventListener('auth:session-expired', handleSessionExpired);
      window.removeEventListener('auth:logout', handleExternalLogout);
    };
  }, [navigate]);

  // Handler for successful Farmer Login - starts directly from existing Welcome page with Get Started button
  const handleFarmerLogin = (user) => {
    setCurrentUser(user);
    setSessionExpiredNotice('');
    // Start directly from existing Welcome page with Get Started button (Dashboard removed from login flow)
    if (typeof window !== 'undefined') {
      if (typeof window.goToWelcomePage === 'function') {
        window.goToWelcomePage(user);
      } else if (typeof window.goToPage === 'function') {
        window.goToPage('page-welcome', false);
        if (typeof window.startWelcomeCelebration === 'function') {
          setTimeout(window.startWelcomeCelebration, 400);
        }
      }
    }
  };

  // Handler for successful Admin Login
  const handleAdminLogin = (user) => {
    setCurrentUser(user);
    setSessionExpiredNotice('');
    // Successful admin login redirects exclusively to /admin/dashboard
    navigate('/admin/dashboard', true);
  };

  const handleLogout = () => {
    const wasAdmin = currentUser?.role === 'admin' || currentPath.startsWith('/admin');
    authLogout();
    setCurrentUser(null);
    setSessionExpiredNotice('');
    if (wasAdmin) {
      navigate('/admin/login', true);
    } else {
      navigate('/', true);
    }
  };

  return (
    <div className="app-container">
      {/* 1. Admin Login View (Route: '/admin/login') */}
      {(currentPath === '/admin/login' || screen === 'admin_login') && (
        <AdminLogin
          onLogin={handleAdminLogin}
          onSwitchToFarmer={() => navigate('/')}
          sessionNotice={sessionExpiredNotice}
        />
      )}

      {/* 2. Farmer Registration View (Route: '/register') */}
      {(currentPath === '/register' || screen === 'register') && (
        <Register
          onSwitchToLogin={() => navigate('/')}
          onRegisterSuccess={() => navigate('/')}
        />
      )}

      {/* 2b. Forgot Password View (Route: '/forgot-password') */}
      {(currentPath === '/forgot-password' || screen === 'forgot_password') && (
        <ForgotPassword
          onSwitchToLogin={() => navigate('/')}
        />
      )}

      {/* 3. Farmer Dashboard removed from login flow - starts directly on Welcome page */}
      {(currentPath === '/farmer/dashboard' || screen === 'dashboard') && (
        currentUser?.role === 'farmer' ? null : (
          <div className="glass-panel" style={{ maxWidth: '500px', margin: '3rem auto', textAlign: 'center', padding: '2rem' }}>
            <h3 style={{ color: '#ef4444', marginBottom: '1rem' }}>Access Denied</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              You do not have permission to view this page.
            </p>
            <button className="btn btn-primary" onClick={handleLogout}>
              Return to Login
            </button>
          </div>
        )
      )}

      {/* 4. Administrator Dashboard (Route: '/admin/dashboard') - Protected for Admins only */}
      {(currentPath === '/admin/dashboard' || screen === 'admin_dashboard') && (
        currentUser?.role === 'admin' ? (
          <AdminDashboard user={currentUser} onLogout={handleLogout} />
        ) : (
          <div className="glass-panel" style={{ maxWidth: '500px', margin: '3rem auto', textAlign: 'center', padding: '2rem' }}>
            <h3 style={{ color: '#ef4444', marginBottom: '1rem' }}>Administrative Access Required</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              This portal requires verified system administrator privileges (HTTP 403 Forbidden).
            </p>
            <button className="btn btn-primary" onClick={handleLogout}>
              Sign In as Administrator
            </button>
          </div>
        )
      )}

      {/* 5. Default Route ('/' or '/farmer/login') -> Farmer Login */}
      {((currentPath === '/' || currentPath === '/farmer/login') && screen !== 'admin_login' && screen !== 'register' && screen !== 'forgot_password' && screen !== 'dashboard' && screen !== 'admin_dashboard') && (
        <FarmerLogin
          onLogin={handleFarmerLogin}
          onSwitchToRegister={() => navigate('/register')}
          onSwitchToAdmin={() => navigate('/admin/login')}
          onForgotPassword={() => navigate('/forgot-password')}
          sessionNotice={sessionExpiredNotice}
        />
      )}

      {/* Backward-compatible fallback for legacy tests asserting screen === 'login' */}
      {(screen === 'login' && currentPath !== '/' && currentPath !== '/farmer/login' && currentPath !== '/admin/login' && currentPath !== '/register' && currentPath !== '/forgot-password' && currentPath !== '/farmer/dashboard' && currentPath !== '/admin/dashboard') && (
        <FarmerLogin
          onLogin={handleFarmerLogin}
          onSwitchToRegister={() => navigate('/register')}
          onSwitchToAdmin={() => navigate('/admin/login')}
          onForgotPassword={() => navigate('/forgot-password')}
          sessionNotice={sessionExpiredNotice}
        />
      )}
    </div>
  );
}

export default App;
