/**
 * Paddy Farming Assistant - Frontend Authentication & Token Management Service
 * Communicates with the FastAPI backend (/api/v1/auth/*) using real Argon2id & PyJWT tokens.
 * Enforces server-derived identity as the sole source of truth.
 * Protects tokens using in-memory state with tab-scoped sessionStorage persistence.
 * Strictly prevents token storage in persistent localStorage (Rectification B).
 */

export const API_BASE_URL = (
  (typeof window !== 'undefined' && window.API_BASE_URL) ||
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) ||
  'http://127.0.0.1:8000'
).replace(/\/+$/, '');

// In-memory token and user state (safest against persistent disk scraping)
let _activeToken = null;
let _activeUser = null;
let _isHandlingUnauthorized = false;

/**
 * Initializes session on module load.
 * Strictly reads from tab-scoped sessionStorage.
 * Cleans up any legacy insecure localStorage token artifacts.
 */
const initSession = () => {
  if (typeof window === 'undefined') return;

  try {
    // Purge any legacy unencrypted tokens from persistent localStorage
    if (localStorage.getItem('authToken')) {
      localStorage.removeItem('authToken');
      localStorage.removeItem('isLoggedIn');
    }

    const token = sessionStorage.getItem('authToken');
    const role = sessionStorage.getItem('userRole');
    const username = sessionStorage.getItem('username');
    const farmerId = sessionStorage.getItem('farmerId');
    const schemaName = sessionStorage.getItem('schemaName');

    if (token && username && role) {
      _activeToken = token;
      _activeUser = {
        token,
        role,
        username,
        farmer_id: farmerId,
        schema_name: schemaName,
      };
    }
  } catch (err) {
    console.warn('Unable to initialize authentication session from storage:', err);
  }
};

initSession();

/**
 * Returns the active Bearer access token string, or null if unauthenticated.
 * Strictly tab-scoped: never returns tokens from localStorage.
 */
export const getAuthToken = () => {
  if (_activeToken) return _activeToken;
  if (typeof window !== 'undefined') {
    return sessionStorage.getItem('authToken');
  }
  return null;
};

/**
 * Returns the authenticated user claims, or null.
 */
export const getAuthUser = () => {
  if (_activeUser) return _activeUser;
  if (typeof window !== 'undefined') {
    const token = getAuthToken();
    const role = sessionStorage.getItem('userRole');
    const username = sessionStorage.getItem('username');
    const farmerId = sessionStorage.getItem('farmerId');
    const schemaName = sessionStorage.getItem('schemaName');

    if (token && username && role) {
      _activeUser = { token, role, username, farmer_id: farmerId, schema_name: schemaName };
      return _activeUser;
    }
  }
  return null;
};

/**
 * Returns true if an active authenticated session exists.
 */
export const isAuthenticated = () => {
  return Boolean(getAuthToken());
};

/**
 * Returns true if the authenticated user has verified Admin role.
 */
export const isAdmin = () => {
  const user = getAuthUser();
  return Boolean(user && user.role === 'admin');
};

/**
 * Returns HTTP Authorization header containing Bearer token for protected API calls.
 */
export const getAuthHeaders = () => {
  const token = getAuthToken();
  if (token) {
    return {
      'Authorization': `Bearer ${token}`,
    };
  }
  return {};
};

/**
 * Handles HTTP 401 Unauthorized responses idempotently across concurrent requests.
 * Prevents cascading redirect loops or race conditions during bulk widget fetches.
 */
export const handleUnauthorized = () => {
  if (!getAuthToken() && !_activeToken) {
    return; // Already logged out: prevent duplicate cycles
  }
  if (_isHandlingUnauthorized) return;
  _isHandlingUnauthorized = true;

  try {
    logout();
    if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
      window.dispatchEvent(new CustomEvent('auth:session-expired', {
        detail: { message: 'Your session has expired. Please sign in again.' },
      }));
    }
  } finally {
    _isHandlingUnauthorized = false;
  }
};

/**
 * Verifies the current session with the FastAPI backend (/api/v1/auth/me).
 * The server is the authoritative source for role and identity: any tampered
 * client storage is automatically overridden with the server-verified role.
 * 
 * @returns {Promise<{valid: boolean, user?: object, reason?: string, offline?: boolean}>}
 */
export const verifySessionWithServer = async () => {
  const token = getAuthToken();
  if (!token) {
    return { valid: false, reason: 'no_token' };
  }

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        ...getAuthHeaders(),
      },
    });

    if (res.ok) {
      const profile = await res.json();
      
      // Synchronize in-memory state with backend-verified identity
      _activeToken = token;
      _activeUser = {
        token: token,
        role: profile.role, // Server-verified role (overrides any client tampering)
        username: profile.username,
        farmer_id: profile.id,
        schema_name: profile.schema_name,
      };

      // Synchronize tab-scoped storage with server truth
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('userRole', profile.role);
        sessionStorage.setItem('username', profile.username);
        sessionStorage.setItem('farmerId', profile.id || '');
        sessionStorage.setItem('schemaName', profile.schema_name || '');
      }

      return { valid: true, user: _activeUser };
    }

    if (res.status === 401) {
      handleUnauthorized();
      return { valid: false, reason: 'expired' };
    }

    // 403 Forbidden on /me indicates deactivated account
    if (res.status === 403) {
      logout();
      return { valid: false, reason: 'forbidden' };
    }

    return { valid: false, reason: `server_error_${res.status}` };

  } catch (err) {
    console.warn('Network error while verifying session with server:', err);
    // Preserves session during temporary offline blips without destroying work
    return { valid: true, user: _activeUser, offline: true };
  }
};

/**
 * Authenticates a farmer or administrator using the real FastAPI backend.
 * Supports username, 10-digit Indian mobile number, or international E.164 mobile.
 * 
 * @param {string} identifier - Username or registered mobile number
 * @param {string} password - Plaintext password
 * @param {boolean} rememberMe - If true, remembers the username identifier in localStorage (never the token!)
 * @returns {Promise<{success: boolean, user?: object, message?: string}>}
 */
export const login = async (identifier, password, rememberMe = false) => {
  if (!identifier || !identifier.trim()) {
    return { success: false, message: 'Please enter your username or mobile number.' };
  }
  if (!password) {
    return { success: false, message: 'Please enter your password.' };
  }

  const cleanIdentifier = identifier.trim();

  // Send exact schema structure matching backend FarmerLoginRequest
  const payload = {
    username: cleanIdentifier,
    password: password,
  };

  const loginUrl = `${API_BASE_URL}/api/v1/auth/login`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    const response = await fetch(loginUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (response.ok) {
      const data = await response.json();
      
      // Verified backend AuthTokenResponse
      _activeToken = data.access_token;
      _activeUser = {
        token: data.access_token,
        role: data.role,
        username: data.username,
        farmer_id: data.farmer_id,
        schema_name: data.schema_name,
      };

      // Tab-scoped storage: strictly stored in sessionStorage (NEVER localStorage)
      sessionStorage.setItem('isLoggedIn', 'true');
      sessionStorage.setItem('authToken', data.access_token);
      sessionStorage.setItem('userRole', data.role);
      sessionStorage.setItem('username', data.username);
      sessionStorage.setItem('farmerId', data.farmer_id || '');
      sessionStorage.setItem('schemaName', data.schema_name || '');

      // Remember Me strictly remembers the login username/identifier for convenience
      if (typeof window !== 'undefined') {
        if (rememberMe) {
          localStorage.setItem('rememberedIdentifier', cleanIdentifier);
        } else {
          localStorage.removeItem('rememberedIdentifier');
        }
        // Ensure localStorage contains zero token artifacts
        localStorage.removeItem('authToken');
        localStorage.removeItem('isLoggedIn');
      }

      if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
        window.dispatchEvent(new CustomEvent('auth:login', { detail: { user: _activeUser } }));
      }

      return {
        success: true,
        user: _activeUser,
      };
    }

    if (response.status === 401) {
      let detailMsg = 'Invalid username, mobile number, or password.';
      try {
        const errJson = await response.json();
        if (errJson && errJson.detail) {
          detailMsg = errJson.detail;
        }
      } catch {
        // use default
      }
      return { success: false, message: detailMsg };
    }

    if (response.status === 403) {
      return { success: false, message: 'Account is inactive. Please contact support.' };
    }

    if (response.status === 422) {
      let validationMsg = 'Invalid request format. Please check your credentials.';
      try {
        const errJson = await response.json();
        if (errJson && errJson.detail) {
          if (Array.isArray(errJson.detail)) {
            validationMsg = errJson.detail.map(d => d.msg || d.message).join('; ');
          } else if (typeof errJson.detail === 'string') {
            validationMsg = errJson.detail;
          }
        }
      } catch {
        // use default
      }
      return { success: false, message: validationMsg };
    }

    return {
      success: false,
      message: `Authentication failed (HTTP ${response.status}). Please try again later.`,
    };

  } catch (err) {
    if (err instanceof Error) {
      if (err.name === 'AbortError') {
        return { success: false, message: 'Authentication request timed out. Please verify backend is running.' };
      }
      return { success: false, message: `Connection error: ${err.message}` };
    }
    return { success: false, message: 'Unable to connect to authentication server.' };
  }
};

/**
 * Registers a new farmer using the backend registration endpoint.
 * Server strictly enforces role='farmer' (privilege escalation is impossible).
 * 
 * @param {object} farmerData - Farmer registration attributes
 * @returns {Promise<{success: boolean, profile?: object, message?: string}>}
 */
export const registerFarmer = async (farmerData) => {
  const { username, password, mobile_number, full_name, farm_name, village } = farmerData;

  if (!username || username.trim().length < 3) {
    return { success: false, message: 'Username must be at least 3 characters long.' };
  }
  if (!password || password.length < 8) {
    return { success: false, message: 'Password must be at least 8 characters long.' };
  }
  if (!mobile_number || !mobile_number.trim()) {
    return { success: false, message: 'Mobile number is required.' };
  }

  const cleanMobile = mobile_number.trim().replace(/[\s\-\.\(\)]/g, '');
  const indianMobileRegex = /^(\+91|0)?[6-9]\d{9}$/;
  if (!indianMobileRegex.test(cleanMobile)) {
    return { success: false, message: 'Please enter a valid 10-digit Indian mobile number (e.g. 9876543210 or +919876543210).' };
  }

  if (!full_name || !full_name.trim()) {
    return { success: false, message: 'Full name is required.' };
  }

  // Strictly construct FarmerRegisterRequest payload (excluding any role/admin keys)
  const payload = {
    username: username.trim(),
    password: password,
    mobile_number: mobile_number.trim(),
    full_name: full_name.trim(),
    farm_name: farm_name ? farm_name.trim() : null,
    village: village ? village.trim() : null,
  };

  const registerUrl = `${API_BASE_URL}/api/v1/auth/register`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // Allow time for schema provisioning

    const response = await fetch(registerUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (response.status === 201) {
      const profile = await response.json();
      return { success: true, profile };
    }

    if (response.status >= 500) {
      return {
        success: false,
        message: 'Registration failed due to a server error. Please try again later.',
      };
    }

    let errorDetail = 'Registration failed.';
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        if (Array.isArray(errJson.detail)) {
          errorDetail = errJson.detail.map(d => d.msg || d.message).join('; ');
        } else if (typeof errJson.detail === 'string') {
          errorDetail = errJson.detail;
        }
      }
    } catch {
      errorDetail = `Server error (HTTP ${response.status}).`;
    }

    return { success: false, message: errorDetail };

  } catch (err) {
    if (err instanceof Error) {
      if (err.name === 'AbortError') {
        return { success: false, message: 'Registration timed out. Database provisioning took too long.' };
      }
      return { success: false, message: `Connection error: ${err.message}` };
    }
    return { success: false, message: 'Unable to connect to registration server.' };
  }
};

/**
 * Retrieves the profile of the currently authenticated user from /api/v1/auth/me.
 */
export const getCurrentProfile = async () => {
  const token = getAuthToken();
  if (!token) return null;

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        ...getAuthHeaders(),
      },
    });

    if (res.ok) {
      return await res.json();
    }
    if (res.status === 401) {
      handleUnauthorized();
    }
    return null;
  } catch (err) {
    console.warn('Failed to fetch current user profile:', err);
    return null;
  }
};

/**
 * Retrieves administrative system diagnostic status from /api/v1/admin/system-status.
 * Strictly requires verified Admin token.
 * Note: HTTP 403 Forbidden throws an authorization error without destroying valid farmer session.
 */
export const getAdminSystemStatus = async () => {
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/system-status`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
      ...getAuthHeaders(),
    },
  });

  if (!res.ok) {
    if (res.status === 401) {
      handleUnauthorized();
    }
    let detail = '';
    try {
      const err = await res.json();
      detail = err.detail || '';
    } catch {
      detail = res.statusText;
    }
    throw new Error(detail || `Admin verification failed (HTTP ${res.status}).`);
  }

  return await res.json();
};

/**
 * Clears authentication tokens and resets client session state.
 * Fully purges tab-scoped sessionStorage, persistent localStorage, and cookies.
 * Resets navigation bar user badge, dropdown menu, and dispatches auth:logout event.
 */
export const logout = () => {
  _activeToken = null;
  _activeUser = null;

  if (typeof window !== 'undefined') {
    // 1 & 3: Purge tab-scoped sessionStorage
    sessionStorage.removeItem('isLoggedIn');
    sessionStorage.removeItem('authToken');
    sessionStorage.removeItem('accessToken');
    sessionStorage.removeItem('refreshToken');
    sessionStorage.removeItem('userRole');
    sessionStorage.removeItem('username');
    sessionStorage.removeItem('farmerId');
    sessionStorage.removeItem('schemaName');
    sessionStorage.removeItem('welcomeCelebrationShown');

    // 1 & 3: Purge persistent localStorage including saved login credentials
    localStorage.removeItem('isLoggedIn');
    localStorage.removeItem('authToken');
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('userRole');
    localStorage.removeItem('username');
    localStorage.removeItem('farmerId');
    localStorage.removeItem('schemaName');
    localStorage.removeItem('rememberedFarmerMobile');
    localStorage.removeItem('rememberedIdentifier');

    // 3: Expire authentication cookies across domain and paths
    try {
      document.cookie.split(';').forEach((c) => {
        const eqPos = c.indexOf('=');
        const name = eqPos > -1 ? c.substring(0, eqPos).trim() : c.trim();
        if (name) {
          document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;`;
        }
      });
    } catch (_) {}

    // 5 & 6: Clean DOM navbar username, hide dropdown, and hide top/bottom navigation bars
    try {
      const navUsername = document.getElementById('nav-username');
      if (navUsername) {
        navUsername.textContent = 'Profile';
      }

      const profileDropdown = document.getElementById('profile-dropdown-menu');
      if (profileDropdown) {
        profileDropdown.classList.add('opacity-0', 'invisible');
      }

      const navbar = document.getElementById('persistent-navbar');
      if (navbar) {
        navbar.classList.add('hidden');
      }

      const mobileNav = document.getElementById('mobile-bottom-nav');
      if (mobileNav) {
        mobileNav.classList.add('hidden');
      }

      const readabilityLayer = document.getElementById('readability-layer');
      if (readabilityLayer) {
        readabilityLayer.classList.remove('opacity-100');
      }
    } catch (_) {}

    if (typeof window.dispatchEvent === 'function') {
      window.dispatchEvent(new CustomEvent('auth:logout'));
    }
  }

  return { success: true };
};

/**
 * Initiates the Forgot Password workflow by requesting a 6-digit OTP.
 * 
 * @param {string} mobileNumber - Farmer's registered Indian mobile number
 * @returns {Promise<{success: boolean, sessionId?: string, maskedMobile?: string, devOtp?: string, message?: string}>}
 */
export const forgotPassword = async (mobileNumber) => {
  if (!mobileNumber || !mobileNumber.trim()) {
    return { success: false, message: 'Please enter your registered mobile number.' };
  }

  const cleanMobile = mobileNumber.trim();
  const url = `${API_BASE_URL}/api/v1/auth/forgot-password`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000);

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ mobile_number: cleanMobile }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    const data = await response.json();

    if (response.ok && data.success) {
      return {
        success: true,
        sessionId: data.session_id,
        maskedMobile: data.masked_mobile,
        expiresInSeconds: data.expires_in_seconds,
        cooldownSeconds: data.cooldown_seconds,
        devOtp: data.dev_otp,
        message: data.message,
      };
    }

    let errorMsg = data.detail || 'Unable to send verification code. Please check your number.';
    if (Array.isArray(errorMsg)) {
      errorMsg = errorMsg[0]?.msg || JSON.stringify(errorMsg);
    }
    return { success: false, message: errorMsg };
  } catch (err) {
    console.error('Error requesting password reset OTP:', err);
    return {
      success: false,
      message: 'Unable to connect to authentication server. Please check your internet or try again later.',
    };
  }
};

/**
 * Resends a fresh 6-digit OTP under the 60-second cooldown rule.
 * 
 * @param {string} sessionId - UUID session identifier
 * @returns {Promise<{success: boolean, devOtp?: string, message?: string}>}
 */
export const resendOtp = async (sessionId) => {
  if (!sessionId) {
    return { success: false, message: 'Invalid session. Please restart password reset.' };
  }

  const url = `${API_BASE_URL}/api/v1/auth/resend-otp`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000);

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ session_id: sessionId }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    const data = await response.json();

    if (response.ok && data.success) {
      return {
        success: true,
        sessionId: data.session_id,
        expiresInSeconds: data.expires_in_seconds,
        cooldownSeconds: data.cooldown_seconds,
        devOtp: data.dev_otp,
        message: data.message,
      };
    }

    let errorMsg = data.detail || 'Unable to resend OTP at this time.';
    if (Array.isArray(errorMsg)) {
      errorMsg = errorMsg[0]?.msg || JSON.stringify(errorMsg);
    }
    return { success: false, message: errorMsg };
  } catch (err) {
    console.error('Error resending OTP:', err);
    return {
      success: false,
      message: 'Unable to connect to authentication server. Please try again.',
    };
  }
};

/**
 * Verifies the entered 6-digit OTP code against the backend.
 * 
 * @param {string} sessionId - UUID session identifier
 * @param {string} otp - 6-digit numeric OTP code
 * @returns {Promise<{success: boolean, resetToken?: string, message?: string}>}
 */
export const verifyOtp = async (sessionId, otp) => {
  if (!sessionId) {
    return { success: false, message: 'Invalid session. Please restart password reset.' };
  }
  if (!otp || otp.trim().length !== 6) {
    return { success: false, message: 'Please enter the complete 6-digit verification code.' };
  }

  const url = `${API_BASE_URL}/api/v1/auth/verify-otp`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000);

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        otp: otp.trim(),
      }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    const data = await response.json();

    if (response.ok && data.success) {
      return {
        success: true,
        resetToken: data.reset_token,
        message: data.message,
      };
    }

    let errorMsg = data.detail || 'Invalid verification code.';
    if (Array.isArray(errorMsg)) {
      errorMsg = errorMsg[0]?.msg || JSON.stringify(errorMsg);
    }
    return { success: false, message: errorMsg };
  } catch (err) {
    console.error('Error verifying OTP:', err);
    return {
      success: false,
      message: 'Unable to verify code with server. Please try again.',
    };
  }
};

/**
 * Resets the password using the verified single-use reset token.
 * 
 * @param {string} resetToken - Verified authorization token
 * @param {string} newPassword - New password
 * @param {string} confirmPassword - Confirm password
 * @returns {Promise<{success: boolean, message?: string}>}
 */
export const resetPassword = async (resetToken, newPassword, confirmPassword) => {
  if (!resetToken) {
    return { success: false, message: 'Missing reset authorization token. Please restart password reset.' };
  }
  if (!newPassword || newPassword.length < 8) {
    return { success: false, message: 'Password must be at least 8 characters long.' };
  }
  if (newPassword !== confirmPassword) {
    return { success: false, message: 'New password and confirm password do not match.' };
  }

  const url = `${API_BASE_URL}/api/v1/auth/reset-password`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000);

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        reset_token: resetToken,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    const data = await response.json();

    if (response.ok && data.success) {
      return {
        success: true,
        message: data.message || 'Password updated successfully.',
      };
    }

    let errorMsg = data.detail || 'Unable to update password. Please try again.';
    if (Array.isArray(errorMsg)) {
      errorMsg = errorMsg[0]?.msg || JSON.stringify(errorMsg);
    }
    return { success: false, message: errorMsg };
  } catch (err) {
    console.error('Error resetting password:', err);
    return {
      success: false,
      message: 'Unable to update password. Please check your internet connection.',
    };
  }
};
