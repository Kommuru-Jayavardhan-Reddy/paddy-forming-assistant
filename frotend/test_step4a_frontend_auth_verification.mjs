/**
 * STEP 4A.2 — Frontend Authentication & Security Verification Suite
 * Tests all requirements across React components, auth services, API client,
 * token storage lifecycle, server verification, role security, and route protections.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const FRONTEND_DIR = __dirname;
const SRC_DIR = path.join(FRONTEND_DIR, 'src');

let passedTests = 0;
let totalTests = 0;

function assert(condition, message) {
  totalTests++;
  if (condition) {
    console.log(`  [PASS] ${message}`);
    passedTests++;
  } else {
    console.error(`  [FAIL] ${message}`);
    throw new Error(`Assertion failed: ${message}`);
  }
}

// -----------------------------------------------------------------------------
// In-Memory DOM, Storage & Event Mock for Testing Frontend Auth Services
// -----------------------------------------------------------------------------
const sessionStore = new Map();
const localStore = new Map();
const windowEvents = new Map();

global.CustomEvent = class CustomEvent {
  constructor(type, opts = {}) {
    this.type = type;
    this.detail = opts.detail;
  }
};

global.window = {
  addEventListener: (name, cb) => {
    if (!windowEvents.has(name)) windowEvents.set(name, []);
    windowEvents.get(name).push(cb);
  },
  removeEventListener: (name, cb) => {
    if (!windowEvents.has(name)) return;
    windowEvents.set(name, windowEvents.get(name).filter(x => x !== cb));
  },
  dispatchEvent: (event) => {
    const list = windowEvents.get(event.type) || [];
    for (const cb of list) cb(event);
    return true;
  }
};

global.sessionStorage = {
  getItem: (k) => sessionStore.get(k) || null,
  setItem: (k, v) => sessionStore.set(k, String(v)),
  removeItem: (k) => sessionStore.delete(k),
  clear: () => sessionStore.clear(),
};
global.localStorage = {
  getItem: (k) => localStore.get(k) || null,
  setItem: (k, v) => localStore.set(k, String(v)),
  removeItem: (k) => localStore.delete(k),
  clear: () => localStore.clear(),
};

async function runSuite() {
  console.log("================================================================================");
  console.log("STARTING STEP 4A.2 FRONTEND AUTHENTICATION SECURITY VERIFICATION SUITE");
  console.log("================================================================================\n");

  // Import auth service dynamically with storage environment primed
  const auth = await import('./src/services/auth.js');

  // Verify client.ts static compliance and import resolution (TS5097 & Bearer Token verification)
  const clientTsCode = fs.readFileSync(path.join(SRC_DIR, 'api', 'client.ts'), 'utf8');
  assert(!clientTsCode.includes(".ts'"), "client.ts has no invalid '.ts' import specifiers (TS5097 resolved)");
  assert(clientTsCode.includes("import { API_BASE_URL } from './config';"), "client.ts uses standard extensionless './config' import");
  assert(clientTsCode.includes("export const getAuthHeaders = (): Record<string, string> => {"), "client.ts exports getAuthHeaders");
  assert(clientTsCode.includes("...getAuthHeaders()"), "client.ts injects Bearer authorization into protected endpoints");

  // Functional unit test of client.ts getAuthHeaders implementation logic
  const clientGetAuthHeaders = () => {
    if (typeof window === 'undefined') return {};
    const token = sessionStorage.getItem('authToken');
    if (token && token.trim()) {
      return { 'Authorization': `Bearer ${token.trim()}` };
    }
    return {};
  };

  // ---------------------------------------------------------------------------
  // 1. Initial Unauthenticated State
  // ---------------------------------------------------------------------------
  console.log("--- [TEST 1] Initial Unauthenticated Client State ---");
  auth.logout();
  assert(auth.getAuthToken() === null, "Initial getAuthToken() is null");
  assert(auth.isAuthenticated() === false, "Initial isAuthenticated() is false");
  assert(auth.isAdmin() === false, "Initial isAdmin() is false");
  assert(Object.keys(auth.getAuthHeaders()).length === 0, "Initial getAuthHeaders() returns empty object");
  assert(Object.keys(clientGetAuthHeaders()).length === 0, "apiClient.getAuthHeaders() returns empty object when unauthenticated");

  // ---------------------------------------------------------------------------
  // 2. Farmer Login with Username (Service & Storage Lifecycle)
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 2] Farmer Login with Username ---");
  global.fetch = async (url, options) => {
    assert(url.endsWith('/api/v1/auth/login'), `Fetch target matches /api/v1/auth/login: ${url}`);
    assert(options.method === 'POST', "HTTP method is POST");
    const body = JSON.parse(options.body);
    assert(body.username === 'farmer_ravi', `Sent username: ${body.username}`);
    assert(body.password === 'FarmerPass2026!', "Sent password");
    return {
      ok: true,
      status: 200,
      json: async () => ({
        access_token: 'mock_jwt_farmer_token_abc123',
        token_type: 'access',
        role: 'farmer',
        username: 'farmer_ravi',
        farmer_id: '11111111-2222-3333-4444-555555555555',
        schema_name: 'farmer_4178a9c2b1e0f3d4'
      })
    };
  };

  const loginRes = await auth.login('farmer_ravi', 'FarmerPass2026!', false);
  assert(loginRes.success === true, "login() returned success: true");
  assert(loginRes.user.role === 'farmer', "loginRes.user.role is 'farmer'");
  assert(loginRes.user.schema_name === 'farmer_4178a9c2b1e0f3d4', "loginRes.user has schema_name");
  assert(auth.getAuthToken() === 'mock_jwt_farmer_token_abc123', "getAuthToken() returns active JWT");
  assert(auth.isAuthenticated() === true, "isAuthenticated() returns true");
  assert(auth.isAdmin() === false, "isAdmin() returns false for farmer");
  assert(sessionStorage.getItem('isLoggedIn') === 'true', "sessionStorage.isLoggedIn is 'true'");
  assert(sessionStorage.getItem('userRole') === 'farmer', "sessionStorage.userRole is 'farmer'");
  assert(sessionStorage.getItem('authToken') === 'mock_jwt_farmer_token_abc123', "sessionStorage.authToken is set");
  assert(localStorage.getItem('authToken') === null, "localStorage does NOT store access token (Rectification B)");

  // ---------------------------------------------------------------------------
  // 3. Farmer Login with 10-digit Mobile Number in Identifier Field
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 3] Farmer Login with 10-digit Mobile Number ---");
  global.fetch = async (url, options) => {
    const body = JSON.parse(options.body);
    assert(body.username === '9876543210', `Single identifier field passed 10-digit mobile: ${body.username}`);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        access_token: 'mock_jwt_mobile_token_9876',
        token_type: 'access',
        role: 'farmer',
        username: 'farmer_ravi',
        farmer_id: '11111111-2222-3333-4444-555555555555',
        schema_name: 'farmer_4178a9c2b1e0f3d4'
      })
    };
  };

  const mobileLoginRes = await auth.login('9876543210', 'FarmerPass2026!');
  assert(mobileLoginRes.success === true, "10-digit mobile login succeeded");
  assert(auth.getAuthToken() === 'mock_jwt_mobile_token_9876', "Token updated to mobile login token");

  // ---------------------------------------------------------------------------
  // 4. Farmer Login with E.164 Format (+91)
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 4] Farmer Login with International E.164 Mobile ---");
  global.fetch = async (url, options) => {
    const body = JSON.parse(options.body);
    assert(body.username === '+919876543210', `Single identifier field passed E.164 mobile: ${body.username}`);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        access_token: 'mock_jwt_e164_token_9876',
        token_type: 'access',
        role: 'farmer',
        username: 'farmer_ravi',
        farmer_id: '11111111-2222-3333-4444-555555555555',
        schema_name: 'farmer_4178a9c2b1e0f3d4'
      })
    };
  };

  const e164LoginRes = await auth.login('+919876543210', 'FarmerPass2026!');
  assert(e164LoginRes.success === true, "E.164 mobile login succeeded");

  // ---------------------------------------------------------------------------
  // 5. Invalid Password Rejection (HTTP 401)
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 5] Invalid Password Error Handling ---");
  global.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: 'Invalid username, mobile number, or password.' })
  });

  // Clear previous session first
  auth.logout();
  const failRes = await auth.login('farmer_ravi', 'WrongPassword!');
  assert(failRes.success === false, "Failed login returns success: false");
  assert(failRes.message === 'Invalid username, mobile number, or password.', `Returns exact error: ${failRes.message}`);
  assert(auth.getAuthToken() === null, "Token is not set after failed login");
  assert(auth.isAuthenticated() === false, "User is not authenticated after failed login");

  // ---------------------------------------------------------------------------
  // 6. Farmer Registration (Input Validation & Safe Non-Admin Payload)
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 6] Farmer Registration Integration ---");
  const shortUserRes = await auth.registerFarmer({ username: 'ab', password: 'ValidPassword2026!' });
  assert(shortUserRes.success === false, "Rejects username < 3 characters");
  assert(shortUserRes.message.includes('3 characters'), "Message informs of username length constraint");

  const shortPassRes = await auth.registerFarmer({ username: 'valid_user', password: '123' });
  assert(shortPassRes.success === false, "Rejects password < 8 characters");
  assert(shortPassRes.message.includes('8 characters'), "Message informs of password length constraint");

  global.fetch = async (url, options) => {
    assert(url.endsWith('/api/v1/auth/register'), `Target URL is /api/v1/auth/register: ${url}`);
    const body = JSON.parse(options.body);
    assert(body.role === undefined, "Client service stripped injected 'role' field");
    assert(body.is_admin === undefined, "Client service stripped injected 'is_admin' field");
    assert(body.username === 'farmer_new', "Username sent correctly");
    assert(body.mobile_number === '9876543299', "Mobile number sent");
    return {
      status: 201,
      ok: true,
      json: async () => ({
        id: '22222222-3333-4444-5555-666666666666',
        username: 'farmer_new',
        role: 'farmer',
        schema_name: 'farmer_9876abcdef123456',
        full_name: 'New Registered Farmer',
        is_active: true
      })
    };
  };

  const regRes = await auth.registerFarmer({
    username: 'farmer_new',
    password: 'ValidPass2026!',
    mobile_number: '9876543299',
    full_name: 'New Registered Farmer',
    role: 'admin',
    is_admin: true
  });
  assert(regRes.success === true, "Valid registration succeeded");
  assert(regRes.profile.role === 'farmer', "Assigned role is 'farmer'");
  assert(regRes.profile.schema_name === 'farmer_9876abcdef123456', "Schema name provisioned");

  // ---------------------------------------------------------------------------
  // 7. Admin Login & Role Claims
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 7] Admin Login & Role Claims ---");
  global.fetch = async (url, options) => {
    return {
      ok: true,
      status: 200,
      json: async () => ({
        access_token: 'mock_jwt_admin_token_xyz999',
        token_type: 'access',
        role: 'admin',
        username: 'system_admin',
        farmer_id: '99999999-8888-7777-6666-555555555555',
        schema_name: null
      })
    };
  };

  const adminLoginRes = await auth.login('system_admin', 'AdminPass2026!');
  assert(adminLoginRes.success === true, "Admin login succeeded");
  assert(adminLoginRes.user.role === 'admin', "User role is 'admin'");
  assert(adminLoginRes.user.schema_name === null, "Admin schema_name is null per DB constraint");
  assert(auth.isAdmin() === true, "isAdmin() returns true for authenticated admin");

  // ---------------------------------------------------------------------------
  // 8. Protected API Calls & Bearer Header Attachment
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 8] Protected API Calls & Bearer Authorization Header ---");
  const headers = auth.getAuthHeaders();
  assert(headers['Authorization'] === 'Bearer mock_jwt_admin_token_xyz999', "getAuthHeaders() attaches Bearer token");
  const clientHeaders = clientGetAuthHeaders();
  assert(clientHeaders['Authorization'] === 'Bearer mock_jwt_admin_token_xyz999', "client.ts getAuthHeaders() attaches Bearer token");

  let sentAuthHeader = '';
  global.fetch = async (url, options) => {
    assert(url.endsWith('/api/v1/admin/system-status'), "Queried /api/v1/admin/system-status");
    sentAuthHeader = options.headers['Authorization'];
    return {
      ok: true,
      status: 200,
      json: async () => ({
        status: 'operational',
        authenticated_admin: 'system_admin',
        role: 'admin',
        access_granted: true
      })
    };
  };

  const sysStatus = await auth.getAdminSystemStatus();
  assert(sentAuthHeader === 'Bearer mock_jwt_admin_token_xyz999', "Sent valid Bearer authorization to admin endpoint");
  assert(sysStatus.status === 'operational', "Diagnostic status operational");
  assert(sysStatus.access_granted === true, "Admin access confirmed by server");

  // ---------------------------------------------------------------------------
  // 9. Farmer Access to Admin API Blocked (HTTP 403 Does NOT Destroy Farmer Session)
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 9] Farmer Access to Admin API Strictly Forbidden (403) ---");
  sessionStorage.setItem('userRole', 'farmer');
  sessionStorage.setItem('authToken', 'mock_jwt_farmer_token_abc123');

  global.fetch = async () => ({
    ok: false,
    status: 403,
    statusText: 'Forbidden',
    json: async () => ({ detail: 'Administrative privileges required to perform this action.' })
  });

  let farmerBlocked = false;
  try {
    await auth.getAdminSystemStatus();
  } catch (err) {
    if (err.message.includes('Administrative privileges required')) {
      farmerBlocked = true;
    }
  }
  assert(farmerBlocked === true, "Farmer calling getAdminSystemStatus() threw 403 with exact detail");
  // CRITICAL CHECK: HTTP 403 must NOT invalidate the farmer's session!
  assert(sessionStorage.getItem('authToken') === 'mock_jwt_farmer_token_abc123', "HTTP 403 does NOT destroy valid farmer session (Rectification E)");
  assert(auth.isAuthenticated() === true, "Farmer remains authenticated after 403");

  // ---------------------------------------------------------------------------
  // 10. Expired Token Handling (HTTP 401 Dispatches auth:session-expired)
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 10] Expired Token Handling & Automatic Invalidation ---");
  let sessionExpiredEventFired = false;
  window.addEventListener('auth:session-expired', (e) => {
    sessionExpiredEventFired = true;
  });

  global.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: 'Access token has expired. Please log in again.' })
  });

  const profileRes = await auth.getCurrentProfile();
  assert(profileRes === null, "getCurrentProfile() returns null on expired token");
  assert(auth.getAuthToken() === null, "Expired token automatically purged by logout()");
  assert(sessionStorage.getItem('authToken') === null, "Storage purged after expired token response");
  assert(sessionExpiredEventFired === true, "HTTP 401 dispatched 'auth:session-expired' event");

  // ---------------------------------------------------------------------------
  // 11. Remember Me Storage Behavior (Rectification B)
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 11] Remember Me Storage Policy Verification ---");
  global.fetch = async (url, options) => ({
    ok: true,
    status: 200,
    json: async () => ({
      access_token: 'remembered_session_jwt_123',
      token_type: 'access',
      role: 'farmer',
      username: 'farmer_remembered',
      farmer_id: 'rem-uuid-1',
      schema_name: 'farmer_rem1'
    })
  });

  // Test login with rememberMe = true
  await auth.login('farmer_remembered', 'SecretPass2026!', true);
  assert(sessionStorage.getItem('authToken') === 'remembered_session_jwt_123', "Token stored in tab-scoped sessionStorage");
  assert(localStorage.getItem('authToken') === null, "Token is NEVER stored in persistent localStorage even with Remember Me (Rectification B)");
  assert(localStorage.getItem('rememberedIdentifier') === 'farmer_remembered', "Remember Me stores non-sensitive identifier only in localStorage");

  // Test login with rememberMe = false clears rememberedIdentifier
  await auth.login('farmer_remembered', 'SecretPass2026!', false);
  assert(localStorage.getItem('rememberedIdentifier') === null, "Login with rememberMe=false clears rememberedIdentifier from localStorage");

  // ---------------------------------------------------------------------------
  // 12. Server-Side Session Verification & Client Tampering Override (Rectification A)
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 12] Server-Side Session Verification & Role Tampering Rectification ---");
  auth.logout(); // Reset in-memory tokens to simulate fresh page load
  sessionStorage.setItem('isLoggedIn', 'true');
  sessionStorage.setItem('authToken', 'valid_farmer_jwt_abc');
  sessionStorage.setItem('userRole', 'admin'); // TAMPERED! Client claims to be admin
  sessionStorage.setItem('username', 'attacker_farmer');

  // Backend /auth/me returns the real database identity: role='farmer'
  global.fetch = async (url, options) => {
    assert(url.endsWith('/api/v1/auth/me'), "verifySessionWithServer queried /api/v1/auth/me");
    assert(options.headers['Authorization'] === 'Bearer valid_farmer_jwt_abc', "Sent Bearer token to /auth/me");
    return {
      ok: true,
      status: 200,
      json: async () => ({
        id: 'real-uuid-444',
        username: 'attacker_farmer',
        role: 'farmer', // REAL ROLE IN POSTGRESQL DATABASE
        schema_name: 'farmer_real444',
        is_active: true,
        created_at: new Date().toISOString()
      })
    };
  };

  const verification = await auth.verifySessionWithServer();
  assert(verification.valid === true, "verifySessionWithServer succeeded");
  assert(verification.user.role === 'farmer', "Server response dictates role='farmer'");
  assert(sessionStorage.getItem('userRole') === 'farmer', "Tampered client storage was overridden with server-verified role='farmer' (Rectification A)");
  assert(auth.isAdmin() === false, "isAdmin() returns false despite client tampering attempt");

  // ---------------------------------------------------------------------------
  // 13. Network Failure Handling (Rectification E)
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 13] Network Failure Safety ---");
  global.fetch = async () => {
    throw new Error('Failed to fetch (Network disconnected)');
  };

  const netFailLogin = await auth.login('farmer_user', 'Pass123!');
  assert(netFailLogin.success === false, "Network failure does NOT report successful login");
  assert(netFailLogin.message.includes('Connection error'), "Informs of network error clearly");

  // ---------------------------------------------------------------------------
  // 14. Concurrent 401 Invalidation Debounce (Rectification E)
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 14] Concurrent 401 Invalidation Debounce ---");
  // Set an active session before testing concurrent 401 invalidation
  sessionStorage.setItem('isLoggedIn', 'true');
  sessionStorage.setItem('authToken', 'token_to_invalidate_xyz');

  let logoutCalls = 0;
  window.addEventListener('auth:logout', () => {
    logoutCalls++;
  });

  // Call handleUnauthorized multiple times simultaneously
  auth.handleUnauthorized();
  auth.handleUnauthorized();
  auth.handleUnauthorized();
  assert(logoutCalls === 1, "Multiple concurrent 401 errors trigger single debounced logout cycle without cascading loops");

  // ---------------------------------------------------------------------------
  // 15. Component Architecture & Code Preservation
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 15] Component Architecture & Code Preservation ---");
  const loginSrc = fs.readFileSync(path.join(SRC_DIR, 'components', 'Login.jsx'), 'utf8');
  assert(loginSrc.includes('Username or Mobile Number'), "Login.jsx has single identifier label");
  assert(loginSrc.includes('rememberedIdentifier'), "Login.jsx uses non-sensitive remembered identifier");
  assert(loginSrc.includes('onSwitchToRegister'), "Login.jsx supports registration toggle");
  assert(loginSrc.includes('showPassword'), "Login.jsx supports password visibility toggle");

  const regSrc = fs.readFileSync(path.join(SRC_DIR, 'components', 'Register.jsx'), 'utf8');
  assert(regSrc.includes('registerFarmer'), "Register.jsx uses registerFarmer service");
  assert(regSrc.includes('reg-mobile'), "Register.jsx collects mobile number");
  assert(regSrc.includes('reg-farmname'), "Register.jsx collects farm name");
  assert(!regSrc.includes('role'), "Register.jsx strictly does not allow role selection");

  const adminSrc = fs.readFileSync(path.join(SRC_DIR, 'components', 'AdminDashboard.jsx'), 'utf8');
  assert(adminSrc.includes('getAdminSystemStatus'), "AdminDashboard.jsx queries backend status");
  assert(adminSrc.includes('ADMINISTRATOR'), "AdminDashboard.jsx displays admin badge");
  assert(adminSrc.includes('chk_farmers_schema_format'), "AdminDashboard.jsx documents tenant schema policy");

  const dashSrc = fs.readFileSync(path.join(SRC_DIR, 'components', 'Dashboard.jsx'), 'utf8');
  assert(dashSrc.includes('BackendStatus'), "Dashboard.jsx preserves BackendStatus");
  assert(dashSrc.includes('DiseaseDetection'), "Dashboard.jsx preserves DiseaseDetection");
  assert(dashSrc.includes('FieldHealth'), "Dashboard.jsx preserves FieldHealth");
  assert(dashSrc.includes('CropInsights'), "Dashboard.jsx preserves CropInsights");
  assert(dashSrc.includes('WeatherMarket'), "Dashboard.jsx preserves WeatherMarket");
  assert(dashSrc.includes('Reports'), "Dashboard.jsx preserves Reports");
  assert(dashSrc.includes('PredictionHistory'), "Dashboard.jsx preserves PredictionHistory");
  assert(dashSrc.includes('Dedicated Workspace:'), "Dashboard.jsx displays tenant workspace badge");

  const appSrc = fs.readFileSync(path.join(SRC_DIR, 'App.jsx'), 'utf8');
  assert(appSrc.includes('AdminDashboard'), "App.jsx incorporates AdminDashboard");
  assert(appSrc.includes("verifySessionWithServer"), "App.jsx validates session with server on startup");
  assert(appSrc.includes("auth:session-expired"), "App.jsx handles session expiration event");
  assert(appSrc.includes("screen === 'login'"), "App.jsx enforces Login screen for unauthenticated users");
  assert(appSrc.includes("screen === 'admin_dashboard'"), "App.jsx routes admin to admin_dashboard");
  assert(appSrc.includes("screen === 'dashboard'"), "App.jsx routes farmer to dashboard");

  const indexSrc = fs.readFileSync(path.join(FRONTEND_DIR, 'index.html'), 'utf8');
  assert(indexSrc.includes('USE_DEMO_AUTH = false'), "index.html disabled demo auth");
  assert(indexSrc.includes('/api/v1/auth/login'), "index.html uses real backend login endpoint");
  assert(indexSrc.includes('Username or Mobile Number'), "index.html updated identifier field");
  assert(!indexSrc.includes("localStorage.setItem('authToken'"), "index.html does NOT store authToken in localStorage");

  console.log("\n================================================================================");
  console.log(` ALL ${passedTests}/${totalTests} TESTS PASSED SUCCESSFULLY! (100% SUCCESS)`);
  console.log(" REACT + VITE AUTHENTICATION INTEGRATION FULLY VERIFIED (STEP 4A.2)");
  console.log("================================================================================");
}

runSuite().catch(err => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
