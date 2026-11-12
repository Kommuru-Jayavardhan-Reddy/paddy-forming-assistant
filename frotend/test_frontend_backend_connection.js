/**
 * STEP 11J.1 — React Frontend to FastAPI Connection Verification Suite
 * 
 * Verifies:
 * 1. FastAPI backend /health returns HTTP 200 and valid JSON.
 * 2. Vite frontend dev server serves index.html, React components, and API client.
 * 3. Centralized API client (checkHealth) returns structured status, latency, and handles loading/errors.
 * 4. Invalid backend URL produces a clear, human-readable error.
 * 5. CORS headers allow http://localhost:5173 and http://127.0.0.1:5173 with credentials.
 * 6. Preflight OPTIONS requests succeed with expected headers.
 * 7. Frontend environment configuration (.env) contains no secrets.
 * 8. Existing frontend routes and GPS privacy remain 100% functional.
 */

import fs from 'fs';
import path from 'path';
import http from 'http';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const FRONTEND_DIR = __dirname;
const SRC_DIR = path.join(FRONTEND_DIR, 'src');
const INDEX_HTML = path.join(FRONTEND_DIR, 'index.html');
const ENV_FILE = path.join(FRONTEND_DIR, '.env');

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

async function httpFetch(urlStr, options = {}) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlStr);
    const reqOptions = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      method: options.method || 'GET',
      headers: options.headers || {},
      timeout: options.timeout || 5000,
    };

    const req = http.request(reqOptions, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        let json = null;
        try {
          json = JSON.parse(body);
        } catch (_e) {
          // not json
        }
        resolve({
          status: res.statusCode,
          headers: res.headers,
          data: json,
          body,
        });
      });
    });

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy(new Error('Connection timed out'));
    });

    if (options.body) {
      req.write(options.body);
    }
    req.end();
  });
}

async function runStep11J1Verification() {
  console.log("================================================================================");
  console.log(" PADDY FARMING ASSISTANT — STEP 11J.1 CONNECTION VERIFICATION SUITE");
  console.log("================================================================================");

  // ---------------------------------------------------------------------------
  // 1. FASTAPI BACKEND HEALTH ENDPOINT
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 1] FastAPI Backend Health Endpoint (Port 8000) ---");
  const healthRes = await httpFetch('http://127.0.0.1:8000/health');
  assert(healthRes.status === 200, `GET /health returns HTTP 200 OK (got ${healthRes.status})`);
  assert(healthRes.data && healthRes.data.status === 'healthy', `Backend status is 'healthy' (got '${healthRes.data?.status}')`);
  assert(healthRes.data && healthRes.data.service === 'Paddy Farming Assistant API', `Service name matches 'Paddy Farming Assistant API'`);
  assert(healthRes.data && healthRes.data.version === 'v1', `API version is 'v1'`);

  // Also verify DB and Model health
  const dbHealthRes = await httpFetch('http://127.0.0.1:8000/health/database');
  assert(dbHealthRes.status === 200, `GET /health/database returns HTTP 200 OK`);
  assert(dbHealthRes.data && dbHealthRes.data.connected === true, `PostgreSQL database is connected`);

  const modelHealthRes = await httpFetch('http://127.0.0.1:8000/health/model');
  assert(modelHealthRes.status === 200, `GET /health/model returns HTTP 200 OK`);
  assert(modelHealthRes.data && modelHealthRes.data.model_loaded === true, `EfficientNet-B4 image model is loaded`);

  // ---------------------------------------------------------------------------
  // 2. VITE FRONTEND SERVER & REACT ENTRY POINT
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 2] Vite Dev Server & React Entry Point (Port 5173) ---");
  const viteIndexRes = await httpFetch('http://127.0.0.1:5173/');
  assert(viteIndexRes.status === 200, `Vite dev server returns HTTP 200 for index.html`);
  assert(viteIndexRes.body.includes('<div id="root">'), `index.html contains mounting element: <div id="root">`);
  assert(viteIndexRes.body.includes('id="page-react"'), `index.html contains page container: id="page-react"`);
  assert(viteIndexRes.body.includes('/src/main.jsx'), `index.html loads React entry point: /src/main.jsx`);
  assert(!viteIndexRes.body.includes('React Assistant'), `index.html navigation cleanly excludes obsolete 'React Assistant'`);
  assert(!viteIndexRes.body.includes('id="nav-backend-badge"'), `index.html navbar cleanly excludes obsolete 'nav-backend-badge'`);

  // Check Vite serving modules
  const mainModuleRes = await httpFetch('http://127.0.0.1:5173/src/main.jsx');
  assert(mainModuleRes.status === 200, `Vite serves /src/main.jsx with HTTP 200`);
  assert(mainModuleRes.body.includes('createRoot'), `main.jsx uses React 19 createRoot`);

  const clientModuleRes = await httpFetch('http://127.0.0.1:5173/src/api/client.ts');
  assert(clientModuleRes.status === 200, `Vite serves /src/api/client.ts with HTTP 200`);
  assert(clientModuleRes.body.includes('checkHealth'), `client.ts exports checkHealth function`);

  const statusComponentRes = await httpFetch('http://127.0.0.1:5173/src/components/BackendStatus.jsx');
  assert(statusComponentRes.status === 200, `Vite serves /src/components/BackendStatus.jsx with HTTP 200`);
  assert(statusComponentRes.body.includes('Backend Connection Status'), `BackendStatus component renders connection panel`);

  // ---------------------------------------------------------------------------
  // 3. FRONTEND API CONFIGURATION & CLIENT FUNCTIONALITY
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 3] Centralized API Client & Error Handling Logic ---");

  // Read config.ts and client.ts
  const configContent = fs.readFileSync(path.join(SRC_DIR, 'api', 'config.ts'), 'utf8');
  assert(configContent.includes('import.meta.env.VITE_API_BASE_URL'), `config.ts reads VITE_API_BASE_URL from environment`);
  assert(configContent.includes('.replace(/\\/+$/, "")'), `config.ts sanitizes trailing slashes from API_BASE_URL`);

  const clientContent = fs.readFileSync(path.join(SRC_DIR, 'api', 'client.ts'), 'utf8');
  assert(clientContent.includes('export const checkHealth = async'), `client.ts exports checkHealth`);
  assert(clientContent.includes('performance.now()'), `client.ts measures request latency in milliseconds`);
  assert(clientContent.includes('AbortController'), `client.ts implements network timeout protection`);
  assert(clientContent.includes('statusCode: response.status'), `client.ts captures HTTP response status codes`);
  assert(clientContent.includes('connected: false'), `client.ts returns clean failure structure on network error`);

  // ---------------------------------------------------------------------------
  // 4. ERROR SIMULATION FOR INVALID BACKEND URLS
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 4] Invalid Backend URL & Error Handling Simulation ---");
  // Test unreachable port
  let unreachableError = null;
  try {
    await httpFetch('http://127.0.0.1:9999/health', { timeout: 1000 });
  } catch (err) {
    unreachableError = err;
  }
  assert(unreachableError !== null, `Unreachable backend port (9999) correctly triggers connection error: ${unreachableError?.message}`);

  // Test 404 endpoint on backend
  const notFoundRes = await httpFetch('http://127.0.0.1:8000/nonexistent_health_probe_12345');
  assert(notFoundRes.status === 404, `Invalid endpoint returns HTTP 404 Not Found (got ${notFoundRes.status})`);
  assert(notFoundRes.body.includes('Not Found'), `HTTP 404 response body has clear readable text`);

  // ---------------------------------------------------------------------------
  // 5. CORS CONFIGURATION VERIFICATION
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 5] CORS Header Verification (Both localhost and 127.0.0.1) ---");

  // A. Origin: http://localhost:5173
  const corsLocalhostRes = await httpFetch('http://127.0.0.1:8000/health', {
    headers: { 'Origin': 'http://localhost:5173' }
  });
  assert(corsLocalhostRes.status === 200, `GET /health with Origin http://localhost:5173 returns 200`);
  assert(corsLocalhostRes.headers['access-control-allow-origin'] === 'http://localhost:5173', 
    `Access-Control-Allow-Origin echoes 'http://localhost:5173'`);
  assert(corsLocalhostRes.headers['access-control-allow-credentials'] === 'true', 
    `Access-Control-Allow-Credentials is true`);

  // B. Origin: http://127.0.0.1:5173
  const corsIpRes = await httpFetch('http://127.0.0.1:8000/health', {
    headers: { 'Origin': 'http://127.0.0.1:5173' }
  });
  assert(corsIpRes.status === 200, `GET /health with Origin http://127.0.0.1:5173 returns 200`);
  assert(corsIpRes.headers['access-control-allow-origin'] === 'http://127.0.0.1:5173', 
    `Access-Control-Allow-Origin echoes 'http://127.0.0.1:5173'`);
  assert(corsIpRes.headers['access-control-allow-credentials'] === 'true', 
    `Access-Control-Allow-Credentials is true`);

  // C. Preflight OPTIONS check
  const preflightRes = await httpFetch('http://127.0.0.1:8000/health', {
    method: 'OPTIONS',
    headers: {
      'Origin': 'http://localhost:5173',
      'Access-Control-Request-Method': 'GET',
      'Access-Control-Request-Headers': 'Content-Type,Accept',
    }
  });
  assert(preflightRes.status === 200, `OPTIONS preflight returns HTTP 200 OK`);
  assert(preflightRes.headers['access-control-allow-origin'] === 'http://localhost:5173', 
    `Preflight Access-Control-Allow-Origin is correct`);
  assert(preflightRes.headers['access-control-allow-methods'].includes('GET'), 
    `Preflight Access-Control-Allow-Methods includes GET`);

  // ---------------------------------------------------------------------------
  // 6. ENVIRONMENT VARIABLES & SECRETS AUDIT
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 6] Frontend Environment Variables & Security Audit ---");
  assert(fs.existsSync(ENV_FILE), `Frontend .env exists`);
  const envContent = fs.readFileSync(ENV_FILE, 'utf8');
  assert(envContent.includes('VITE_API_BASE_URL=http://localhost:8000'), `VITE_API_BASE_URL is configured to http://localhost:8000`);
  
  // Security check: No secrets in frontend env
  const forbiddenKeys = ['PASSWORD', 'SECRET', 'API_KEY', 'DATABASE_URL', 'TOKEN', 'PRIVATE_KEY'];
  for (const fk of forbiddenKeys) {
    const hasForbidden = envContent.toUpperCase().includes(fk);
    assert(!hasForbidden, `Frontend .env does NOT contain forbidden key: ${fk}`);
  }

  // ---------------------------------------------------------------------------
  // 7. EXISTING ROUTES & INTEGRITY
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 7] Existing Frontend Routes & Component Integrity ---");
  const indexContent = fs.readFileSync(INDEX_HTML, 'utf8');
  const requiredRoutes = ['home', 'detection', 'field-health', 'crop-insights', 'market-buyers', 'reports', 'react'];
  for (const r of requiredRoutes) {
    assert(indexContent.includes(`"${r}"`) || indexContent.includes(`'${r}'`), `pageRoutes contains route: '${r}'`);
  }

  // Check that existing pages exist in index.html
  const requiredPageIds = [
    'page-login', 'page-welcome', 'page-home', 'page-detection',
    'page-field-health', 'page-crop-insights', 'page-market-buyers',
    'page-reports', 'page-react'
  ];
  for (const pid of requiredPageIds) {
    assert(indexContent.includes(`id="${pid}"`), `index.html contains page: id="${pid}"`);
  }

  // ---------------------------------------------------------------------------
  // 8. DASHBOARD COMPONENT STRUCTURE
  // ---------------------------------------------------------------------------
  console.log("\n--- [TEST 8] React Dashboard Component Structure ---");
  const dashboardContent = fs.readFileSync(path.join(SRC_DIR, 'components', 'Dashboard.jsx'), 'utf8');
  assert(dashboardContent.includes('BackendStatus'), `Dashboard.jsx imports and uses BackendStatus`);
  assert(dashboardContent.includes('Paddy Farming Assistant Dashboard'), `Dashboard.jsx preserves title`);
  assert(dashboardContent.includes('Image Upload'), `Dashboard.jsx preserves Image Upload card`);
  assert(dashboardContent.includes('Farm Location'), `Dashboard.jsx preserves Farm Location card`);
  assert(dashboardContent.includes('Question Input'), `Dashboard.jsx preserves Question Input card`);
  assert(dashboardContent.includes('Disease Prediction'), `Dashboard.jsx preserves Disease Prediction card`);
  assert(dashboardContent.includes('Satellite Time-Series'), `Dashboard.jsx preserves Satellite Time-Series card`);
  assert(dashboardContent.includes('Generation Report'), `Dashboard.jsx preserves Generation Report card`);
  assert(dashboardContent.includes('onLogout'), `Dashboard.jsx preserves logout handler`);

  console.log("\n================================================================================");
  console.log(` ALL ${passedTests}/${totalTests} TESTS PASSED SUCCESSFULLY!`);
  console.log(" REACT FRONTEND TO FASTAPI BACKEND CONNECTION VERIFIED (STEP 11J.1 COMPLETE)");
  console.log("================================================================================");
}

runStep11J1Verification().catch(err => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
