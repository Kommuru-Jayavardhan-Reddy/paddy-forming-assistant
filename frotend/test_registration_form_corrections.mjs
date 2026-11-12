/**
 * Paddy Farming Assistant - Farmer Registration Form UI & Validation Acceptance Tests
 * Verifies all UI, validation, and accessibility corrections requested in:
 * FARMER REGISTRATION FORM — UI & VALIDATION CORRECTIONS
 */

import fs from 'fs';
import path from 'path';
import assert from 'assert';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.join(__dirname, 'src');

console.log('='.repeat(80));
console.log('STARTING FARMER REGISTRATION FORM UI & VALIDATION ACCEPTANCE TEST SUITE');
console.log('='.repeat(80));

let passCount = 0;
let failCount = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  [PASS] ${name}`);
    passCount++;
  } catch (err) {
    console.error(`  [FAIL] ${name}: ${err.message}`);
    failCount++;
  }
}

const regCode = fs.readFileSync(path.join(SRC_DIR, 'components', 'Register.jsx'), 'utf8');
const authServiceCode = fs.readFileSync(path.join(SRC_DIR, 'services', 'auth.js'), 'utf8');
const farmerLoginCode = fs.readFileSync(path.join(SRC_DIR, 'components', 'FarmerLogin.jsx'), 'utf8');
const adminLoginCode = fs.readFileSync(path.join(SRC_DIR, 'components', 'AdminLogin.jsx'), 'utf8');

console.log('\n--- [SECTION 1] Farmer Username UI Requirements ---');
test('1.1 Field label is changed to "Farmer Username *"', () => {
  assert(regCode.includes('<label htmlFor="reg-username">Farmer Username *</label>'),
    'Label must be exactly "Farmer Username *"');
  assert(!regCode.includes('<label htmlFor="reg-username">Username *</label>'),
    'Old "Username *" label must be removed');
});

test('1.2 Placeholder is changed to "Enter your farmer username"', () => {
  assert(regCode.includes('placeholder="Enter your farmer username"'),
    'Placeholder must be "Enter your farmer username"');
});

test('1.3 Example placeholder "e.g. farmer_ravi" is removed', () => {
  assert(!regCode.includes('e.g. farmer_ravi'),
    'Example placeholder "e.g. farmer_ravi" must be removed');
});

test('1.4 Username validation enforces min length >= 3 and informs user', () => {
  assert(regCode.includes('Farmer username must be at least 3 characters long.'),
    'Client validation message for username must mention farmer username constraint');
});

console.log('\n--- [SECTION 2] Password Visibility Eye Icon Requirements ---');
test('2.1 Password eye icon color is theme green (#10b981)', () => {
  assert(regCode.includes('stroke="#10b981"'),
    'SVG eye icons must use theme green stroke #10b981');
  assert(regCode.includes("color: '#10b981'"),
    'Eye toggle button color must be #10b981');
});

test('2.2 Password show/hide state is implemented', () => {
  assert(regCode.includes('const [showPassword, setShowPassword] = useState(false);'),
    'Password show/hide state must be defined');
  assert(regCode.includes('const [showConfirmPassword, setShowConfirmPassword] = useState(false);'),
    'Confirm password show/hide state must be defined');
});

test('2.3 Password field toggles between text and password types', () => {
  assert(regCode.includes("type={showPassword ? 'text' : 'password'}"),
    'Password input type must dynamically toggle between text and password');
  assert(regCode.includes("type={showConfirmPassword ? 'text' : 'password'}"),
    'Confirm password input type must dynamically toggle between text and password');
});

test('2.4 Icon remains visible in both password states (hidden and visible)', () => {
  // Eye open SVG path
  assert(regCode.includes('d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"'),
    'Eye open SVG path must be present when password is shown');
  // Slashed eye SVG path
  assert(regCode.includes('d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"'),
    'Eye slashed SVG path must be present when password is hidden');
});

test('2.5 FarmerLogin component also features consistent green password eye icon', () => {
  assert(farmerLoginCode.includes('stroke="#10b981"'),
    'FarmerLogin must also share the green password visibility icon');
  assert(farmerLoginCode.includes("type={showPassword ? 'text' : 'password'}"),
    'FarmerLogin toggles password visibility');
});

console.log('\n--- [SECTION 3] Mobile Number Mandatory Requirements ---');
test('3.1 "(Optional)" label is removed from Mobile Number', () => {
  assert(!regCode.includes('Mobile Number (Optional)'),
    '"(Optional)" must be removed from Mobile Number');
});

test('3.2 Label is changed to "Mobile Number *"', () => {
  assert(regCode.includes('<label htmlFor="reg-mobile">Mobile Number *</label>'),
    'Label must be exactly "Mobile Number *"');
});

test('3.3 Placeholder is changed to "Enter your mobile number"', () => {
  assert(regCode.includes('placeholder="Enter your mobile number"'),
    'Placeholder must be "Enter your mobile number"');
});

test('3.4 HTML required attribute is present on Mobile Number input', () => {
  const mobileInputMatch = regCode.match(/id="reg-mobile"[\s\S]*?\/>/);
  assert(mobileInputMatch && mobileInputMatch[0].includes('required'),
    'Mobile number input must have required attribute');
});

test('3.5 Frontend validates Indian mobile format and rejects invalid numbers', () => {
  assert(regCode.includes('indianMobileRegex') || regCode.includes('[6-9]\\d{9}'),
    'Frontend code must validate Indian mobile regex starting with 6-9');
  assert(regCode.includes('Please enter a valid 10-digit Indian mobile number'),
    'Clear validation error message must be shown for invalid Indian mobile');
  assert(regCode.includes('Mobile number is required.'),
    'Clear validation error message must be shown when mobile is empty');
});

test('3.6 AuthService validates required mobile before sending request', () => {
  assert(authServiceCode.includes('Mobile number is required.'),
    'auth.js registerFarmer must validate mobile_number presence');
  assert(authServiceCode.includes('Please enter a valid 10-digit Indian mobile number'),
    'auth.js registerFarmer must validate Indian mobile format');
});

console.log('\n--- [SECTION 4] Full Name Mandatory Requirements ---');
test('4.1 "(Optional)" label is removed from Full Name', () => {
  assert(!regCode.includes('Full Name (Optional)'),
    '"(Optional)" must be removed from Full Name');
});

test('4.2 Label is changed to "Full Name *"', () => {
  assert(regCode.includes('<label htmlFor="reg-fullname">Full Name *</label>'),
    'Label must be exactly "Full Name *"');
});

test('4.3 Placeholder is changed to "Enter your full name"', () => {
  assert(regCode.includes('placeholder="Enter your full name"'),
    'Placeholder must be "Enter your full name"');
});

test('4.4 HTML required attribute is present on Full Name input', () => {
  const fullNameMatch = regCode.match(/id="reg-fullname"[\s\S]*?\/>/);
  assert(fullNameMatch && fullNameMatch[0].includes('required'),
    'Full name input must have required attribute');
});

test('4.5 Frontend rejects empty or whitespace-only Full Name with clear message', () => {
  assert(regCode.includes('Full name is required.'),
    'Clear validation message "Full name is required." must be displayed');
  assert(authServiceCode.includes('Full name is required.'),
    'auth.js must validate full name presence');
});

console.log('\n--- [SECTION 5] Design & Cross-Role Isolation Preservation ---');
test('5.1 Glass-panel and login-background preserved', () => {
  assert(regCode.includes('className="login-background"'),
    'Paddy background layer preserved');
  assert(regCode.includes('className="glass-panel screen-enter"'),
    'Glass panel styling preserved');
});

test('5.2 Form input grid maintains minWidth: 0 and responsive minmax(0, 1fr)', () => {
  assert(regCode.includes('gridTemplateColumns: \'repeat(2, minmax(0, 1fr))\''),
    'Two-column grid uses minmax(0, 1fr)');
  assert(regCode.includes('minWidth: 0'),
    'Grid child items maintain minWidth: 0');
});

test('5.3 Farmer registration does not include or expose Admin role selection', () => {
  assert(!regCode.includes('<select'), 'No role dropdown in registration');
  assert(!regCode.includes('name="role"'), 'No role input in registration');
});

test('5.4 Admin login remains isolated and intact', () => {
  assert(adminLoginCode.includes('/admin/login') || adminLoginCode.includes('Administrator Sign In'),
    'Admin login maintains dedicated admin branding and isolated entry');
  assert(adminLoginCode.includes("role !== 'admin'"),
    'Admin login continues strictly verifying admin role claim');
});

console.log('\n' + '='.repeat(80));
console.log(`TOTAL ACCEPTANCE TESTS: ${passCount + failCount}`);
console.log(`PASSED: ${passCount}`);
console.log(`FAILED: ${failCount}`);
console.log('='.repeat(80) + '\n');

assert(failCount === 0, `${failCount} tests failed!`);
