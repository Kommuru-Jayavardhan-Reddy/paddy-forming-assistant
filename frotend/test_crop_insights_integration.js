/**
 * STEP 11J.4 — Crop Insights Frontend Integration Verification Suite
 * Tests the connection between the frontend Crop Insights modules and FastAPI backend:
 * - Types and client functions
 * - Real /predictions, /predictions/{id}, and /classes endpoints
 * - Statistical aggregation & distribution calculations
 * - Multimodal vs Image-only handling
 * - Edge case handling (404 for unknown prediction, 422/400 for invalid UUID)
 * - Coordinate privacy and server path protection
 * - Database row count audit (strictly zero modifications)
 */

import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');

const BACKEND_BASE = 'http://127.0.0.1:8000';
const FRONTEND_BASE = 'http://127.0.0.1:5173';

const TEST_RESULTS = {
  total: 0,
  passed: 0,
  failed: 0,
  tests: []
};

function recordTest(name, passed, details = '') {
  TEST_RESULTS.total++;
  if (passed) {
    TEST_RESULTS.passed++;
    console.log(`  [PASS] ${name}`);
  } else {
    TEST_RESULTS.failed++;
    console.error(`  [FAIL] ${name}: ${details}`);
  }
  TEST_RESULTS.tests.push({ name, passed, details });
}

function assert(condition, message) {
  recordTest(message, Boolean(condition), condition ? '' : 'Assertion condition failed');
}

async function httpFetch(url, options = {}) {
  const parsed = new URL(url);
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        protocol: parsed.protocol,
        hostname: parsed.hostname,
        port: parsed.port,
        path: parsed.pathname + parsed.search,
        method: options.method || 'GET',
        headers: options.headers || {},
        timeout: options.timeout || 10000,
      },
      (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          resolve({
            status: res.statusCode,
            headers: res.headers,
            text: () => Promise.resolve(data),
            json: () => {
              try {
                return Promise.resolve(JSON.parse(data));
              } catch (e) {
                return Promise.reject(new Error(`Failed to parse JSON: ${data.slice(0, 100)}`));
              }
            }
          });
        });
      }
    );

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`HTTP request timed out: ${url}`));
    });

    if (options.body) {
      req.write(options.body);
    }
    req.end();
  });
}

async function runVerification() {
  console.log('======================================================================');
  console.log('STEP 11J.4 — Crop Insights Frontend Integration Verification');
  console.log('Backend Target: ', BACKEND_BASE);
  console.log('Frontend Target:', FRONTEND_BASE);
  console.log('======================================================================\n');

  // -------------------------------------------------------------------------
  // SECTION 1: Code and Component Verification
  // -------------------------------------------------------------------------
  console.log('--- TEST SECTION 1: Code & Component Verification ---');

  const clientPath = path.join(__dirname, 'src', 'api', 'client.ts');
  const clientExists = fs.existsSync(clientPath);
  assert(clientExists, 'client.ts exists');
  const clientCode = clientExists ? fs.readFileSync(clientPath, 'utf-8') : '';
  assert(clientCode.includes('getPredictions'), 'client.ts exports getPredictions()');
  assert(clientCode.includes('getPredictionById'), 'client.ts exports getPredictionById()');
  assert(clientCode.includes('getCropInsightsSummary'), 'client.ts exports getCropInsightsSummary()');
  assert(clientCode.includes('getClasses'), 'client.ts exports getClasses()');

  const typesPath = path.join(__dirname, 'src', 'api', 'types.ts');
  const typesExists = fs.existsSync(typesPath);
  assert(typesExists, 'types.ts exists');
  const typesCode = typesExists ? fs.readFileSync(typesPath, 'utf-8') : '';
  assert(typesCode.includes('interface PredictionRecordItem'), 'types.ts exports PredictionRecordItem');
  assert(typesCode.includes('interface PredictionListResponse'), 'types.ts exports PredictionListResponse');
  assert(typesCode.includes('interface CropInsightsSummary'), 'types.ts exports CropInsightsSummary');
  assert(typesCode.includes('interface DiseaseDistributionItem'), 'types.ts exports DiseaseDistributionItem');

  const cropInsightsJsxPath = path.join(__dirname, 'src', 'components', 'CropInsights.jsx');
  const cropInsightsJsxExists = fs.existsSync(cropInsightsJsxPath);
  assert(cropInsightsJsxExists, 'CropInsights.jsx exists');
  const cropInsightsJsxCode = cropInsightsJsxExists ? fs.readFileSync(cropInsightsJsxPath, 'utf-8') : '';
  assert(cropInsightsJsxCode.includes('getPredictions'), 'CropInsights.jsx calls getPredictions');
  assert(cropInsightsJsxCode.includes('getCropInsightsSummary'), 'CropInsights.jsx calls getCropInsightsSummary');
  assert(cropInsightsJsxCode.includes('getPredictionById'), 'CropInsights.jsx calls getPredictionById');
  assert(cropInsightsJsxCode.includes('#2e7d32'), 'CropInsights.jsx implements Healthy color scheme');
  assert(cropInsightsJsxCode.includes('#ed6c02'), 'CropInsights.jsx implements Needs Attention color scheme');
  assert(cropInsightsJsxCode.includes('#d32f2f'), 'CropInsights.jsx implements High Risk color scheme');
  assert(cropInsightsJsxCode.includes('attention_weights'), 'CropInsights.jsx visualizes multimodal attention weights');
  assert(cropInsightsJsxCode.includes('DISEASE_KNOWLEDGE_BASE'), 'CropInsights.jsx includes scientific disease knowledge');

  const dashboardPath = path.join(__dirname, 'src', 'components', 'Dashboard.jsx');
  const dashCode = fs.readFileSync(dashboardPath, 'utf-8');
  assert(dashCode.includes('import CropInsights from \'./CropInsights\''), 'Dashboard.jsx imports CropInsights component');
  assert(dashCode.includes('<CropInsights />'), 'Dashboard.jsx mounts CropInsights component');

  const cropInsightsJsPath = path.join(__dirname, 'src', 'cropInsights.js');
  const cropInsightsJsExists = fs.existsSync(cropInsightsJsPath);
  assert(cropInsightsJsExists, 'cropInsights.js exists');
  const cropInsightsJsCode = cropInsightsJsExists ? fs.readFileSync(cropInsightsJsPath, 'utf-8') : '';
  assert(cropInsightsJsCode.includes('getApiBaseUrl'), 'cropInsights.js implements dynamic getApiBaseUrl');
  assert(cropInsightsJsCode.includes('/predictions'), 'cropInsights.js queries /predictions endpoint');
  assert(cropInsightsJsCode.includes('DISEASE_KNOWLEDGE'), 'cropInsights.js defines disease symptoms and explanations');

  const indexPath = path.join(__dirname, 'index.html');
  const indexHtml = fs.readFileSync(indexPath, 'utf-8');
  assert(indexHtml.includes('id="page-crop-insights"'), 'index.html contains #page-crop-insights');
  assert(indexHtml.includes('id="insights-dev-switcher"'), 'index.html contains #insights-dev-switcher');
  assert(indexHtml.includes('id="insights-influences-grid"'), 'index.html contains #insights-influences-grid');

  // -------------------------------------------------------------------------
  // SECTION 2: Real Backend Endpoints Verification
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 2: Real FastAPI Backend Endpoints ---');

  // Test 1: GET /predictions
  console.log('  Testing GET /predictions...');
  const predRes = await httpFetch(`${BACKEND_BASE}/predictions?page_size=50`);
  assert(predRes.status === 200, `GET /predictions returned HTTP 200 (got ${predRes.status})`);
  const predData = await predRes.json();
  assert(Array.isArray(predData.predictions), 'Predictions response contains predictions array');
  assert(predData.total_predictions >= 35, `Total predictions is at least 35 seeded records (got ${predData.total_predictions})`);
  assert(predData.predictions.length > 0, `Predictions array is populated (count: ${predData.predictions.length})`);

  const samplePred = predData.predictions[0];
  assert(Boolean(samplePred.id), `Prediction has UUID: ${samplePred.id}`);
  assert(Boolean(samplePred.predicted_disease), `Prediction has predicted_disease: ${samplePred.predicted_disease}`);
  assert(typeof samplePred.confidence === 'number', `Prediction has numeric confidence: ${samplePred.confidence}`);
  assert(Boolean(samplePred.model_name), `Prediction has model_name: ${samplePred.model_name}`);

  // Test 2: Multimodal predictions filter
  console.log('  Testing GET /predictions?prediction_mode=multimodal...');
  const mmRes = await httpFetch(`${BACKEND_BASE}/predictions?prediction_mode=multimodal&page_size=20`);
  assert(mmRes.status === 200, `GET /predictions?prediction_mode=multimodal returned HTTP 200`);
  const mmData = await mmRes.json();
  assert(mmData.total_predictions === 10, `Total multimodal predictions is 10 (got ${mmData.total_predictions})`);
  const sampleMM = mmData.predictions[0];
  assert(sampleMM.prediction_mode === 'multimodal', 'Prediction mode is multimodal');
  assert(Array.isArray(sampleMM.attention_weights), 'Multimodal prediction contains attention_weights array');
  assert(sampleMM.attention_weights.length === 10, `Attention weights has 10 timesteps (got ${sampleMM.attention_weights.length})`);
  assert(Boolean(sampleMM.field_id), `Multimodal prediction links to field_id: ${sampleMM.field_id}`);

  // Test 3: Image-only predictions filter
  console.log('  Testing GET /predictions?prediction_mode=image_only...');
  const imgRes = await httpFetch(`${BACKEND_BASE}/predictions?prediction_mode=image_only&page_size=30`);
  assert(imgRes.status === 200, `GET /predictions?prediction_mode=image_only returned HTTP 200`);
  const imgData = await imgRes.json();
  assert(imgData.total_predictions >= 25, `Total image-only predictions is at least 25 seeded records (got ${imgData.total_predictions})`);

  // Test 4: GET /predictions/{prediction_id}
  console.log(`  Testing GET /predictions/${samplePred.id}...`);
  const singleRes = await httpFetch(`${BACKEND_BASE}/predictions/${samplePred.id}`);
  assert(singleRes.status === 200, `GET /predictions/{id} returned HTTP 200`);
  const singleData = await singleRes.json();
  assert(singleData.id === samplePred.id, 'Single prediction ID matches requested ID');
  assert(singleData.predicted_disease === samplePred.predicted_disease, 'Disease matches list item');

  // Test 5: GET /classes
  console.log('  Testing GET /classes...');
  const classRes = await httpFetch(`${BACKEND_BASE}/classes`);
  assert(classRes.status === 200, `GET /classes returned HTTP 200`);
  const classData = await classRes.json();
  assert(Array.isArray(classData.classes), 'Classes array returned');
  assert(classData.classes.length === 13, `Supported disease classes is 13 (got ${classData.classes.length})`);
  assert(classData.classes.includes('tungro'), 'Classes list includes tungro');
  assert(classData.classes.includes('sheath_blight'), 'Classes list includes sheath_blight');
  assert(classData.classes.includes('normal'), 'Classes list includes normal');

  // -------------------------------------------------------------------------
  // SECTION 3: Edge Cases & Error Handling
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 3: Edge Cases & Error Handling ---');

  console.log('  Testing error response for unknown prediction UUID: 00000000-0000-0000-0000-000000000000...');
  const unknownRes = await httpFetch(`${BACKEND_BASE}/predictions/00000000-0000-0000-0000-000000000000`);
  assert(unknownRes.status === 404, `Unknown prediction returns HTTP 404 (got ${unknownRes.status})`);

  console.log('  Testing error response for invalid UUID format...');
  const invalidUuidRes = await httpFetch(`${BACKEND_BASE}/predictions/not-a-valid-uuid-format`);
  assert(invalidUuidRes.status === 400 || invalidUuidRes.status === 422, `Invalid UUID returns HTTP 400/422 (got ${invalidUuidRes.status})`);

  console.log('  Testing error response for invalid prediction mode...');
  const invalidModeRes = await httpFetch(`${BACKEND_BASE}/predictions?prediction_mode=ultrasound`);
  assert(invalidModeRes.status === 400, `Invalid prediction_mode returns HTTP 400 (got ${invalidModeRes.status})`);

  // -------------------------------------------------------------------------
  // SECTION 4: Privacy & Security Verification
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 4: Privacy & Security Verification ---');

  const predJsonText = JSON.stringify(predData);
  const internalPathMatch = predJsonText.match(/[A-Za-z]:\\[Users|Windows|paddy]/i);
  assert(!internalPathMatch, 'No raw internal Windows server file paths exposed in /predictions');

  assert(!cropInsightsJsxCode.includes('latitude:') && !cropInsightsJsxCode.includes('longitude:'),
    'CropInsights.jsx does not display raw latitude/longitude labels');

  // -------------------------------------------------------------------------
  // SECTION 5: Frontend Route & Service Integrity
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 5: Frontend Route & Service Integrity ---');

  const viteRes = await httpFetch(FRONTEND_BASE);
  assert(viteRes.status === 200, `Frontend Vite dev server is reachable at ${FRONTEND_BASE} (HTTP 200)`);
  assert(indexHtml.includes('data-target="page-crop-insights"'), 'Crop Insights navigation preserved');
  assert(indexHtml.includes('data-target="page-detection"'), 'Disease Detection route preserved');
  assert(indexHtml.includes('data-target="page-field-health"'), 'Field Health route preserved');
  assert(indexHtml.includes('id="page-react"'), 'React page container preserved');

  // -------------------------------------------------------------------------
  // SECTION 6: Database Integrity Audit
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 6: Database Integrity Audit ---');
  try {
    const { execSync } = await import('child_process');
    const pythonExe = path.join(ROOT_DIR, 'venv', 'Scripts', 'python.exe');
    const checkScript = path.join(ROOT_DIR, 'backend', 'check_db_integrity.py');
    const auditOut = execSync(`"${pythonExe}" "${checkScript}"`, {
      cwd: path.join(ROOT_DIR, 'backend'),
      encoding: 'utf-8'
    });

    const match = auditOut.match(/DB_COUNTS:(\{.*\})/);
    if (match) {
      const counts = JSON.parse(match[1]);
      console.log('  Database Row Counts Verified:');
      console.log('   - buyers:                ', counts.buyers, '(expected: 17)');
      console.log('   - market_prices:         ', counts.market_prices, '(expected: 100)');
      console.log('   - fields:                ', counts.fields, '(expected: 58)');
      console.log('   - satellite_observations:', counts.satellite_observations, '(expected: 580)');
      console.log('   - prediction_history:    ', counts.prediction_history, '(expected: 35)');
      console.log('   - weather_records:       ', counts.weather_records, '(expected: 98)');
      console.log('   - reports:               ', counts.reports, '(expected: 4)');

      assert(counts.buyers === 17, 'buyers table count unchanged (17)');
      assert(counts.market_prices === 100, 'market_prices table count unchanged (100)');
      assert(counts.fields === 58, 'fields table count unchanged (58)');
      assert(counts.satellite_observations === 580, 'satellite_observations table count unchanged (580)');
      assert(counts.prediction_history >= 35, `prediction_history table contains seeded baseline records (got ${counts.prediction_history})`);
      assert(counts.weather_records >= 98, `weather_records table contains seeded baseline records (got ${counts.weather_records})`);
      assert(counts.reports === 4, 'reports table count unchanged (4)');
    } else {
      recordTest('Database count verification', false, 'Could not parse DB counts from python output');
    }
  } catch (dbErr) {
    recordTest('Database count verification', false, dbErr.message);
  }

  // -------------------------------------------------------------------------
  // SUMMARY
  // -------------------------------------------------------------------------
  console.log('\n======================================================================');
  console.log(`TOTAL TESTS: ${TEST_RESULTS.tests.length}`);
  console.log(`PASSED:      ${TEST_RESULTS.passed}`);
  console.log(`FAILED:      ${TEST_RESULTS.failed}`);
  console.log('======================================================================\n');

  return {
    success: TEST_RESULTS.failed === 0,
    summary: TEST_RESULTS
  };
}

runVerification()
  .then((res) => {
    if (!res.success) {
      process.exit(1);
    }
  })
  .catch((err) => {
    console.error('Unhandled test verification error:', err);
    process.exit(1);
  });
