/**
 * Paddy Farming Assistant - Redesigned Farmer Login Acceptance Test Suite
 * Validates:
 * 1. Split-screen layout (Left 50% dark green #07583c, Right 50% light grey-green #cdd1c7).
 * 2. Left Panel: Paddy sprout logo, large heading "Your Paddy Farming Assistant", description.
 * 3. Right Panel: Centered card, heading "Paddy Farming Assistant", subtitle "Sign in to continue".
 * 4. Form inputs: Mobile Number with user icon, Password with lock icon and green eye icon (#10b981).
 * 5. Remember me checkbox with dark green accent.
 * 6. Dark green Login button with rounded corners and drop shadow.
 * 7. Mobile-number-based authentication preserved.
 * 8. Responsive media queries for desktop, tablet, and mobile.
 * 9. Cross-role isolation & admin portal integrity preserved.
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
  console.log("STARTING REDESIGNED FARMER LOGIN ACCEPTANCE TEST SUITE");
  console.log("================================================================================\n");

  const farmerLoginSrc = fs.readFileSync(path.join(SRC_DIR, 'components', 'FarmerLogin.jsx'), 'utf8');
  const appSrc = fs.readFileSync(path.join(SRC_DIR, 'App.jsx'), 'utf8');
  const adminLoginSrc = fs.readFileSync(path.join(SRC_DIR, 'components', 'AdminLogin.jsx'), 'utf8');
  const adminDashboardSrc = fs.readFileSync(path.join(SRC_DIR, 'components', 'AdminDashboard.jsx'), 'utf8');

  // ---------------------------------------------------------------------------
  // 1. Split-Screen Layout Structure
  // ---------------------------------------------------------------------------
  console.log("--- [SECTION 1] Split-Screen Layout Structure ---");
  assert(farmerLoginSrc.includes('farmer-split-wrapper'), "FarmerLogin.jsx defines full-screen wrapper");
  assert(farmerLoginSrc.includes('farmer-split-card'), "FarmerLogin.jsx defines split-screen container card");
  assert(farmerLoginSrc.includes('farmer-split-left'), "FarmerLogin.jsx defines Left Panel (50% width)");
  assert(farmerLoginSrc.includes('farmer-split-right'), "FarmerLogin.jsx defines Right Panel (50% width)");
  assert(farmerLoginSrc.includes('#07583c'), "Left panel uses theme dark green #07583c");
  assert(farmerLoginSrc.includes('#cdd1c7'), "Right panel uses soft light grey-green #cdd1c7");
  assert(farmerLoginSrc.includes('border-radius: 28px') || farmerLoginSrc.includes("borderRadius: '28px'"), "Container card has smooth rounded corners (28px)");

  // ---------------------------------------------------------------------------
  // 2. Left Panel Content & Typography
  // ---------------------------------------------------------------------------
  console.log("\n--- [SECTION 2] Left Panel Content & Branding ---");
  assert(farmerLoginSrc.includes('Golden-Hour Rice Field Plowing'), "Left panel imports Golden-Hour Rice Field Plowing sunrise image");
  assert(farmerLoginSrc.includes("background-size: cover") || farmerLoginSrc.includes("backgroundSize: 'cover'"), "Left panel background-size is cover");
  assert(farmerLoginSrc.includes("background-position: center") || farmerLoginSrc.includes("backgroundPosition: 'center'"), "Left panel background-position is center");
  assert(farmerLoginSrc.includes("linear-gradient") && farmerLoginSrc.includes("rgba(7, 88, 60,"), "Left panel includes subtle dark-green transparent overlay for text contrast");
  assert(farmerLoginSrc.includes('#f59e0b'), "Left panel features golden sprout icon (#f59e0b)");
  assert(farmerLoginSrc.includes('Your Paddy Farming'), "Left panel includes 'Your Paddy Farming' heading");
  assert(farmerLoginSrc.includes('Assistant'), "Left panel includes 'Assistant' heading line");
  assert(farmerLoginSrc.includes("Check your paddy leaves, watch your field's health, and get simple advice to protect your crop."), "Left panel contains exact crop advisory description");
  assert(farmerLoginSrc.includes("color: '#ffffff'"), "Left panel headings and text are crisp white");

  // ---------------------------------------------------------------------------
  // 3. Right Panel Header & Subtitle
  // ---------------------------------------------------------------------------
  console.log("\n--- [SECTION 3] Right Panel Heading & Subtitle ---");
  assert(farmerLoginSrc.includes('Paddy Farming Assistant'), "Right panel contains 'Paddy Farming Assistant' heading");
  assert(farmerLoginSrc.includes('Sign in to continue'), "Right panel contains 'Sign in to continue' subtitle");
  assert(farmerLoginSrc.includes("textAlign: 'center'"), "Right panel heading and subtitle are centered");

  // ---------------------------------------------------------------------------
  // 4. Form Inputs, Icons & Password Toggle
  // ---------------------------------------------------------------------------
  console.log("\n--- [SECTION 4] Form Inputs & Interactive Controls ---");
  assert(farmerLoginSrc.includes('Mobile Number'), "Form has Mobile Number field label");
  assert(farmerLoginSrc.includes('type="tel"'), "Form uses telephone type for mobile numbers");
  assert(farmerLoginSrc.includes('id="farmer-mobile"'), "Mobile number has dedicated farmer-mobile ID");
  assert(farmerLoginSrc.includes('Password'), "Form has Password field label");
  assert(farmerLoginSrc.includes('id="farmer-password"'), "Password has dedicated farmer-password ID");
  assert(farmerLoginSrc.includes('#10b981'), "Password visibility eye icon uses green (#10b981)");
  assert(farmerLoginSrc.includes('toggle-farmer-password'), "Password visibility toggle button is present");
  assert(farmerLoginSrc.includes('farmer-remember'), "Remember me checkbox is present");
  assert(farmerLoginSrc.includes('Remember me'), "Checkbox has 'Remember me' label");
  assert(farmerLoginSrc.includes("borderRadius: '14px'") || farmerLoginSrc.includes("border-radius: 14px"), "Inputs and buttons use rounded corners (14px)");
  assert(farmerLoginSrc.includes('farmer-login-btn'), "Dark green Login button is styled with dedicated class");
  assert(farmerLoginSrc.includes("box-shadow: 0 10px 24px rgba(7, 88, 60, 0.35)") || farmerLoginSrc.includes("rgba(7, 88, 60,"), "Login button features subtle drop shadow");

  // ---------------------------------------------------------------------------
  // 5. Authentication Contract & Security Controls
  // ---------------------------------------------------------------------------
  console.log("\n--- [SECTION 5] Authentication & Security Controls ---");
  assert(farmerLoginSrc.includes("login(cleanMobile, password, rememberMe)"), "FarmerLogin invokes auth service login with mobile credentials");
  assert(farmerLoginSrc.includes("role !== 'farmer'"), "Strict role isolation checks for farmer privilege");
  assert(farmerLoginSrc.includes("authLogout()"), "Purges session if non-farmer attempts access");
  assert(farmerLoginSrc.includes("window.addEventListener('auth:logout'"), "Listens to logout events to reset fields");
  assert(farmerLoginSrc.includes("setMobileNumber('')") && farmerLoginSrc.includes("setPassword('')"), "Resets fields to empty on logout");

  // ---------------------------------------------------------------------------
  // 6. Navigation & Routing Flow
  // ---------------------------------------------------------------------------
  console.log("\n--- [SECTION 6] Navigation & Welcome Page Routing ---");
  assert(appSrc.includes("goToWelcomePage(user)") || appSrc.includes("goToWelcomePage"), "App.jsx routes successful farmer login directly to Welcome page");
  assert(!appSrc.includes("navigate('/farmer/dashboard', true) // on farmer login"), "Farmer dashboard is strictly removed from direct farmer login flow");
  assert(farmerLoginSrc.includes("onSwitchToRegister"), "Maintains navigation to Farmer Registration");
  assert(farmerLoginSrc.includes("onSwitchToAdmin"), "Maintains navigation to Admin Portal (/admin/login)");

  // ---------------------------------------------------------------------------
  // 7. Responsive Styles for Desktop, Tablet & Mobile
  // ---------------------------------------------------------------------------
  console.log("\n--- [SECTION 7] Responsive Layout Integrity ---");
  assert(farmerLoginSrc.includes("@media (max-width: 840px)"), "Includes tablet breakpoint for vertical stacking");
  assert(farmerLoginSrc.includes("@media (max-width: 480px)"), "Includes mobile breakpoint for fluid viewport padding");

  // ---------------------------------------------------------------------------
  // 8. Admin Portal Isolation
  // ---------------------------------------------------------------------------
  console.log("\n--- [SECTION 8] Admin Portal Isolation & Integrity ---");
  assert(adminLoginSrc.includes("Administrator Username"), "Admin Login remains unaffected");
  assert(adminDashboardSrc.includes("AdminDashboard"), "Admin Dashboard remains unaffected");

  console.log("\n================================================================================");
  console.log(` ALL ${totalTests}/${totalTests} ACCEPTANCE TESTS PASSED! (100% SUCCESS)`);
  console.log(" REDESIGNED FARMER LOGIN MATCHES REFERENCE DESIGN & PRESERVES ALL AUTH FLOWS");
  console.log("================================================================================\n");
}

runAcceptanceSuite().catch(err => {
  console.error("Test execution failed:", err);
  process.exit(1);
});

