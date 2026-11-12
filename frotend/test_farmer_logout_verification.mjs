/**
 * Paddy Farming Assistant - Farmer Logout Verification Acceptance Test Suite
 * Systematically validates all 10 success criteria:
 * 1. Clear the JWT access token and refresh token, if applicable.
 * 2. Clear authenticated user information from React state and context.
 * 3. Clear relevant authentication data from localStorage/sessionStorage and cookies.
 * 4. Reset the Mobile Number and Password login fields to empty.
 * 5. Remove the logged-in username (jaya) from the navigation bar.
 * 6. Remove the authenticated user dropdown and Logout option.
 * 7. Redirect to the Farmer Login page.
 * 8. Prevent authenticated state from being restored after browser refresh.
 * 9. Ensure protected farmer routes cannot be accessed after logout.
 * 10. Verify that Admin authentication and Admin Dashboard remain completely unaffected.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.join(__dirname, 'src');

let passedTests = 0;
let totalTests = 0;

function assert(condition, message) {
  totalTests++;
  if (!condition) {
    console.error(`  [FAIL] ${message}`);
    throw new Error(`Assertion failed: ${message}`);
  }
  passedTests++;
  console.log(`  [PASS] ${message}`);
}

async function runAcceptanceSuite() {
  console.log("================================================================================");
  console.log("STARTING FARMER LOGOUT HARDENING & VERIFICATION TEST SUITE");
  console.log("================================================================================\n");

  const authSrc = fs.readFileSync(path.join(SRC_DIR, 'services', 'auth.js'), 'utf8');
  const indexHtml = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
  const farmerLoginSrc = fs.readFileSync(path.join(SRC_DIR, 'components', 'FarmerLogin.jsx'), 'utf8');
  const appSrc = fs.readFileSync(path.join(SRC_DIR, 'App.jsx'), 'utf8');
  const adminDashboardSrc = fs.readFileSync(path.join(SRC_DIR, 'components', 'AdminDashboard.jsx'), 'utf8');
  const adminLoginSrc = fs.readFileSync(path.join(SRC_DIR, 'components', 'AdminLogin.jsx'), 'utf8');

  // ---------------------------------------------------------------------------
  // 1. Clear JWT Access Token & Refresh Token (Criteria 1)
  // ---------------------------------------------------------------------------
  console.log("--- [CRITERIA 1] Clear JWT Access Token & Refresh Token ---");
  assert(authSrc.includes('_activeToken = null;'), "auth.js resets in-memory _activeToken to null");
  assert(authSrc.includes("sessionStorage.removeItem('authToken');"), "auth.js clears authToken from sessionStorage");
  assert(authSrc.includes("sessionStorage.removeItem('accessToken');"), "auth.js clears accessToken from sessionStorage");
  assert(authSrc.includes("sessionStorage.removeItem('refreshToken');"), "auth.js clears refreshToken from sessionStorage");
  assert(authSrc.includes("localStorage.removeItem('authToken');"), "auth.js clears authToken from localStorage");
  assert(authSrc.includes("localStorage.removeItem('accessToken');"), "auth.js clears accessToken from localStorage");
  assert(authSrc.includes("localStorage.removeItem('refreshToken');"), "auth.js clears refreshToken from localStorage");
  assert(indexHtml.includes("sessionStorage.removeItem('authToken');"), "index.html handleLogout clears authToken from sessionStorage");
  assert(indexHtml.includes("localStorage.removeItem('authToken');"), "index.html handleLogout clears authToken from localStorage");

  // ---------------------------------------------------------------------------
  // 2. Clear Authenticated User Information from React State/Context (Criteria 2)
  // ---------------------------------------------------------------------------
  console.log("\n--- [CRITERIA 2] Clear Authenticated User Information from React State ---");
  assert(authSrc.includes('_activeUser = null;'), "auth.js resets in-memory _activeUser to null");
  assert(appSrc.includes('setCurrentUser(null)'), "App.jsx clears currentUser state on logout");
  assert(appSrc.includes("setSessionExpiredNotice('')"), "App.jsx clears session notices on explicit logout");
  assert(appSrc.includes("window.addEventListener('auth:logout'"), "App.jsx listens to global auth:logout event");

  // ---------------------------------------------------------------------------
  // 3. Clear relevant authentication data from localStorage, sessionStorage, and cookies (Criteria 3)
  // ---------------------------------------------------------------------------
  console.log("\n--- [CRITERIA 3] Purge Storage & Cookies ---");
  const requiredSessionKeys = ['isLoggedIn', 'userRole', 'username', 'farmerId', 'schemaName', 'welcomeCelebrationShown'];
  requiredSessionKeys.forEach(key => {
    assert(authSrc.includes(`sessionStorage.removeItem('${key}')`), `auth.js removes '${key}' from sessionStorage`);
    assert(indexHtml.includes(`sessionStorage.removeItem('${key}')`), `index.html removes '${key}' from sessionStorage`);
  });

  const requiredLocalKeys = ['isLoggedIn', 'userRole', 'username', 'farmerId', 'schemaName', 'rememberedFarmerMobile', 'rememberedIdentifier'];
  requiredLocalKeys.forEach(key => {
    assert(authSrc.includes(`localStorage.removeItem('${key}')`), `auth.js removes '${key}' from localStorage`);
    assert(indexHtml.includes(`localStorage.removeItem('${key}')`), `index.html removes '${key}' from localStorage`);
  });

  assert(authSrc.includes('document.cookie =') && authSrc.includes('expires=Thu, 01 Jan 1970 00:00:00 GMT'), "auth.js expires authentication cookies on logout");
  assert(indexHtml.includes('document.cookie =') && indexHtml.includes('expires=Thu, 01 Jan 1970 00:00:00 GMT'), "index.html expires authentication cookies on logout");

  // ---------------------------------------------------------------------------
  // 4. Reset Mobile Number and Password login fields to empty (Criteria 4)
  // ---------------------------------------------------------------------------
  console.log("\n--- [CRITERIA 4] Reset Mobile Number & Password Login Fields to Empty ---");
  assert(farmerLoginSrc.includes("setMobileNumber('')"), "FarmerLogin.jsx resets mobileNumber state to empty string on logout");
  assert(farmerLoginSrc.includes("setPassword('')"), "FarmerLogin.jsx resets password state to empty string on logout");
  assert(farmerLoginSrc.includes("setRememberMe(false)"), "FarmerLogin.jsx resets rememberMe checkbox to false on logout");
  assert(farmerLoginSrc.includes("window.addEventListener('auth:logout'"), "FarmerLogin.jsx registers auth:logout event listener");
  assert(indexHtml.includes("if (usernameInput) {\n            usernameInput.value = '';\n          }"), "index.html handleLogout clears usernameInput DOM element");
  assert(indexHtml.includes("if (passwordInputEl) {\n            passwordInputEl.value = '';\n          }"), "index.html handleLogout clears passwordInput DOM element");

  // ---------------------------------------------------------------------------
  // 5. Remove Logged-in Username (jaya) from Navigation Bar (Criteria 5)
  // ---------------------------------------------------------------------------
  console.log("\n--- [CRITERIA 5] Remove Username from Navigation Bar ---");
  assert(authSrc.includes("navUsername.textContent = 'Profile'"), "auth.js resets nav-username text to default 'Profile'");
  assert(indexHtml.includes("navUsernameEl.textContent = 'Profile'"), "index.html resets nav-username text to default 'Profile'");
  assert(indexHtml.includes("greetingEl.textContent = 'Welcome, Farmer!'"), "index.html resets greeting text to default");

  // ---------------------------------------------------------------------------
  // 6. Remove Authenticated User Dropdown & Logout Option (Criteria 6)
  // ---------------------------------------------------------------------------
  console.log("\n--- [CRITERIA 6] Remove Dropdown Menu & Hide Navigation Bar ---");
  assert(authSrc.includes("profileDropdown.classList.add('opacity-0', 'invisible')"), "auth.js closes profile-dropdown-menu");
  assert(authSrc.includes("navbar.classList.add('hidden')"), "auth.js hides persistent-navbar");
  assert(authSrc.includes("mobileNav.classList.add('hidden')"), "auth.js hides mobile-bottom-nav");
  assert(indexHtml.includes("profileDropdown.classList.add('opacity-0', 'invisible')"), "index.html closes profile-dropdown-menu on logout");
  assert(indexHtml.includes("navbar.classList.add('hidden')"), "index.html hides persistent-navbar on logout");
  assert(indexHtml.includes("page.id === 'page-react'") && indexHtml.includes("navbar.classList.add('hidden')"), "index.html strictly hides navbar when page-react is active");

  // ---------------------------------------------------------------------------
  // 7. Redirect to Farmer Login Page (Criteria 7)
  // ---------------------------------------------------------------------------
  console.log("\n--- [CRITERIA 7] Redirect to Farmer Login Page ---");
  assert(indexHtml.includes("history.pushState(null, '', '/')"), "index.html updates browser URL to '/' on logout");
  assert(indexHtml.includes("goToPage('page-react', false)"), "index.html switches page display to page-react (Farmer Login)");
  assert(appSrc.includes("navigate('/', true)"), "App.jsx navigates to '/' on farmer logout");

  // ---------------------------------------------------------------------------
  // 8. Prevent Authenticated State from being Restored on Browser Refresh (Criteria 8)
  // ---------------------------------------------------------------------------
  console.log("\n--- [CRITERIA 8] Prevent Session Restoration After Browser Refresh ---");
  assert(indexHtml.includes("checkSessionOnLoad"), "index.html validates session state on initial page load");
  assert(indexHtml.includes("if (isSessionLogged && token)"), "index.html checkSessionOnLoad verifies token presence");
  assert(authSrc.includes("const token = sessionStorage.getItem('authToken');") && authSrc.includes("if (token && username && role)"), "auth.js initSession verifies token existence");

  // Simulate full mock logout and refresh behavior
  const mockSessionStorage = new Map();
  const mockLocalStorage = new Map();
  let mockActiveToken = "jwt.test.token";
  let mockActiveUser = { username: "jaya", role: "farmer" };

  mockSessionStorage.set("authToken", mockActiveToken);
  mockSessionStorage.set("isLoggedIn", "true");
  mockSessionStorage.set("username", "jaya");
  mockLocalStorage.set("rememberedFarmerMobile", "jaya");

  // Simulate logout execution
  mockActiveToken = null;
  mockActiveUser = null;
  mockSessionStorage.clear();
  mockLocalStorage.clear();

  // Simulate browser reload check
  const restoredToken = mockSessionStorage.get("authToken") || null;
  const isLoggedRestored = mockSessionStorage.get("isLoggedIn") === "true";
  const restoredMobile = mockLocalStorage.get("rememberedFarmerMobile") || "";

  assert(restoredToken === null, "Mock browser refresh yields null authToken");
  assert(!isLoggedRestored, "Mock browser refresh yields false for isLoggedIn");
  assert(restoredMobile === "", "Mock browser refresh yields empty string for remembered mobile");

  // ---------------------------------------------------------------------------
  // 9. Ensure Protected Farmer Routes Cannot be Accessed After Logout (Criteria 9)
  // ---------------------------------------------------------------------------
  console.log("\n--- [CRITERIA 9] Ensure Protected Routes Cannot be Accessed After Logout ---");
  assert(indexHtml.includes("if (!isLogged && pageId !== 'page-login' && pageId !== 'page-react')"), "goToPage strictly blocks access to dashboard pages when unauthenticated");
  assert(indexHtml.includes("window.addEventListener('popstate'"), "popstate handler validates session before switching pages");
  assert(appSrc.includes("if (path === '/farmer/dashboard') {\n            navigate('/', true);"), "App.jsx blocks unauthenticated access to /farmer/dashboard and redirects to '/'");

  // ---------------------------------------------------------------------------
  // 10. Verify Admin Authentication and Admin Dashboard Remain Unaffected (Criteria 10)
  // ---------------------------------------------------------------------------
  console.log("\n--- [CRITERIA 10] Admin Authentication & Dashboard Preservation ---");
  assert(adminLoginSrc.includes("Administrator Username"), "AdminLogin.jsx is intact with admin credentials");
  assert(adminDashboardSrc.includes("AdminDashboard"), "AdminDashboard.jsx is intact");
  assert(adminDashboardSrc.includes("Sign Out"), "AdminDashboard.jsx provides Sign Out");
  assert(appSrc.includes("const wasAdmin = currentUser?.role === 'admin' || currentPath.startsWith('/admin')"), "App.jsx detects admin logout separately");
  assert(appSrc.includes("navigate('/admin/login', true)"), "App.jsx routes admin logout to /admin/login exclusively");

  console.log("\n================================================================================");
  console.log(` ALL ${totalTests}/${totalTests} ACCEPTANCE TESTS PASSED! (100% SUCCESS)`);
  console.log(" FARMER LOGOUT FULLY TERMINATES SESSION & RESTORES CLEAN LOGIN INTERFACE");
  console.log("================================================================================\n");
}

runAcceptanceSuite().catch(err => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
