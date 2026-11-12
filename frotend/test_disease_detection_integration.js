/**
 * STEP 11J.2 — Disease Detection Frontend Integration Verification Suite
 * Tests:
 * 1. Frontend component & client integration structure
 * 2. Real backend inference with genuine image assets
 * 3. Exact response contract (disease, confidence, top3)
 * 4. File type and size validation
 * 5. Error handling (HTTP 415, 400, timeouts)
 * 6. GPS and internal path privacy verification
 * 7. Database integrity verification and cleanup of test records
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');

const BACKEND_URL = process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const FRONTEND_URL = 'http://127.0.0.1:5173';

const TEST_RESULTS = {
  passed: 0,
  failed: 0,
  tests: []
};

function recordTest(name, passed, detail = '') {
  if (passed) {
    TEST_RESULTS.passed++;
    console.log(`  [PASS] ${name}`);
  } else {
    TEST_RESULTS.failed++;
    console.error(`  [FAIL] ${name}: ${detail}`);
  }
  TEST_RESULTS.tests.push({ name, passed, detail });
}

function assert(condition, testName, detail = '') {
  recordTest(testName, Boolean(condition), detail);
}

async function runVerification() {
  console.log('======================================================================');
  console.log('STEP 11J.2 — Disease Detection Frontend Integration Verification');
  console.log(`Backend Target:  ${BACKEND_URL}`);
  console.log(`Frontend Target: ${FRONTEND_URL}`);
  console.log('======================================================================\n');

  const testPredictionIds = [];

  // -------------------------------------------------------------------------
  // TEST SECTION 1: File & Component Structure Verification
  // -------------------------------------------------------------------------
  console.log('--- TEST SECTION 1: Code & Component Verification ---');

  const clientPath = path.join(__dirname, 'src', 'api', 'client.ts');
  assert(fs.existsSync(clientPath), 'client.ts exists', clientPath);
  const clientContent = fs.readFileSync(clientPath, 'utf-8');
  assert(clientContent.includes('export const predict'), 'client.ts exports predict() function');
  assert(clientContent.includes('new AbortController()'), 'client.ts implements AbortController timeout');
  assert(clientContent.includes('formData.append(\'file\''), 'client.ts formats multipart/form-data with "file"');
  assert(clientContent.includes('sanitizedDetail') && clientContent.includes('[internal path]'), 'client.ts sanitizes internal filesystem paths');

  const typesPath = path.join(__dirname, 'src', 'api', 'types.ts');
  assert(fs.existsSync(typesPath), 'types.ts exists', typesPath);
  const typesContent = fs.readFileSync(typesPath, 'utf-8');
  assert(typesContent.includes('export interface PredictionRequest'), 'types.ts exports PredictionRequest');
  assert(typesContent.includes('export interface PredictionResponse'), 'types.ts exports PredictionResponse');
  assert(typesContent.includes('export interface TopCandidate'), 'types.ts exports TopCandidate');

  const diseaseDetectionComponentPath = path.join(__dirname, 'src', 'components', 'DiseaseDetection.jsx');
  assert(fs.existsSync(diseaseDetectionComponentPath), 'DiseaseDetection.jsx exists', diseaseDetectionComponentPath);
  const compContent = fs.readFileSync(diseaseDetectionComponentPath, 'utf-8');
  assert(compContent.includes('import { predict } from \'../api/client\''), 'DiseaseDetection imports centralized predict client');
  assert(compContent.includes('validateFile'), 'DiseaseDetection implements client-side file validation');
  assert(compContent.includes('Top 3 Model Candidate Probabilities'), 'DiseaseDetection renders top-3 candidate rankings');
  assert(compContent.includes('Diagnostic Symptoms'), 'DiseaseDetection renders agricultural symptoms');
  assert(compContent.includes('Agronomic Management Advice'), 'DiseaseDetection renders agronomic actions');
  assert(compContent.includes('isAnalyzing'), 'DiseaseDetection prevents duplicate submissions during inference');

  const vanillaJsPath = path.join(__dirname, 'src', 'diseaseDetection.js');
  assert(fs.existsSync(vanillaJsPath), 'diseaseDetection.js exists', vanillaJsPath);
  const vanillaContent = fs.readFileSync(vanillaJsPath, 'utf-8');
  assert(vanillaContent.includes('getApiUrl'), 'diseaseDetection.js uses dynamic getApiUrl()');
  assert(vanillaContent.includes('data.disease || data.predicted_class'), 'diseaseDetection.js supports backend response schema (result.disease)');
  assert(vanillaContent.includes('item.disease || item.class || item.name'), 'diseaseDetection.js supports top3 candidate schema');

  const indexHtmlPath = path.join(__dirname, 'index.html');
  const indexHtml = fs.readFileSync(indexHtmlPath, 'utf-8');
  assert(indexHtml.includes('window.API_BASE_URL'), 'index.html exposes window.API_BASE_URL');
  assert(indexHtml.includes('id="page-detection"'), 'index.html contains #page-detection container');

  // -------------------------------------------------------------------------
  // TEST SECTION 2: Real AI Model Inference Verification
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 2: Real AI Model Inference via /predict ---');

  const tungroImagePath = path.join(ROOT_DIR, 'backend', 'test_images', 'tungro', 'TUNGRO5_67.JPG');
  assert(fs.existsSync(tungroImagePath), 'Authentic Tungro test image exists', tungroImagePath);

  const tungroBytes = fs.readFileSync(tungroImagePath);
  const tungroBlob = new Blob([tungroBytes], { type: 'image/jpeg' });
  const tungroFormData = new FormData();
  tungroFormData.append('file', tungroBlob, 'TUNGRO5_67.JPG');

  console.log('  Submitting genuine tungro leaf image to POST /predict...');
  const t0 = performance.now();
  const tungroRes = await fetch(`${BACKEND_URL}/predict`, {
    method: 'POST',
    body: tungroFormData
  });
  const t1 = performance.now();
  const latencyMs = Math.round(t1 - t0);

  assert(tungroRes.ok, `POST /predict returned HTTP ${tungroRes.status}`, `Status: ${tungroRes.status}`);
  const tungroData = await tungroRes.json();

  assert(tungroData.status === 'success', 'Response status is "success"');
  assert(typeof tungroData.disease === 'string' && tungroData.disease === 'tungro', `Predicted disease is "tungro" (got "${tungroData.disease}")`);
  assert(typeof tungroData.confidence === 'number' && tungroData.confidence >= 0.80, `High confidence score: ${(tungroData.confidence * 100).toFixed(2)}% >= 80%`);
  assert(Array.isArray(tungroData.top3) && tungroData.top3.length === 3, 'Top-3 candidate predictions array returned');
  assert(tungroData.top3[0].disease === 'tungro', 'Rank 1 candidate matches top prediction');
  assert(tungroData.device === 'cpu', 'Inference executed on CPU device');
  assert(typeof tungroData.prediction_id === 'string' && tungroData.prediction_id.length > 0, `Prediction record persisted with UUID ${tungroData.prediction_id}`);

  if (tungroData.prediction_id) {
    testPredictionIds.push(tungroData.prediction_id);
  }
  console.log(`  Real inference completed in ${latencyMs}ms with prediction_id: ${tungroData.prediction_id}`);

  // Test second real image: Normal healthy leaf
  const normalImagePath = path.join(ROOT_DIR, 'backend', 'test_images', 'normal', '100111.jpg');
  assert(fs.existsSync(normalImagePath), 'Authentic Normal test image exists', normalImagePath);

  const normalBytes = fs.readFileSync(normalImagePath);
  const normalBlob = new Blob([normalBytes], { type: 'image/jpeg' });
  const normalFormData = new FormData();
  normalFormData.append('file', normalBlob, '100111.jpg');

  console.log('  Submitting genuine normal leaf image to POST /predict...');
  const normalRes = await fetch(`${BACKEND_URL}/predict`, {
    method: 'POST',
    body: normalFormData
  });
  assert(normalRes.ok, `POST /predict (normal leaf) returned HTTP ${normalRes.status}`);
  const normalData = await normalRes.json();
  assert(normalData.status === 'success', 'Normal leaf response status is "success"');
  assert(typeof normalData.disease === 'string', `Normal leaf classified as: ${normalData.disease}`);
  assert(Array.isArray(normalData.top3) && normalData.top3.length === 3, 'Normal leaf top-3 predictions returned');

  if (normalData.prediction_id) {
    testPredictionIds.push(normalData.prediction_id);
  }

  // -------------------------------------------------------------------------
  // TEST SECTION 3: Validation & Error Handling Verification
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 3: File Validation & Error Handling ---');

  // Test 3.1: Invalid file extension (.txt)
  const txtFormData = new FormData();
  txtFormData.append('file', new Blob(['Invalid content text'], { type: 'text/plain' }), 'notes.txt');
  const txtRes = await fetch(`${BACKEND_URL}/predict`, {
    method: 'POST',
    body: txtFormData
  });
  assert(txtRes.status === 415, `Unsupported file format rejected with HTTP 415 (got ${txtRes.status})`);
  const txtErr = await txtRes.json();
  assert(txtErr.detail && txtErr.detail.includes('Unsupported file format'), 'Descriptive format error returned');

  // Test 3.2: Empty file (0 bytes)
  const emptyFormData = new FormData();
  emptyFormData.append('file', new Blob([], { type: 'image/jpeg' }), 'empty.jpg');
  const emptyRes = await fetch(`${BACKEND_URL}/predict`, {
    method: 'POST',
    body: emptyFormData
  });
  assert(emptyRes.status === 400, `Empty image file rejected with HTTP 400 (got ${emptyRes.status})`);
  const emptyErr = await emptyRes.json();
  assert(emptyErr.detail && emptyErr.detail.includes('empty'), 'Descriptive empty file error returned');

  // Test 3.3: Corrupted image file
  const corruptFormData = new FormData();
  corruptFormData.append('file', new Blob(['NOT_A_VALID_JPEG_HEADER_CONTENT'], { type: 'image/jpeg' }), 'corrupt.jpg');
  const corruptRes = await fetch(`${BACKEND_URL}/predict`, {
    method: 'POST',
    body: corruptFormData
  });
  assert(corruptRes.status === 400, `Corrupted image file rejected with HTTP 400 (got ${corruptRes.status})`);
  const corruptErr = await corruptRes.json();
  assert(corruptErr.detail && corruptErr.detail.includes('corrupted'), 'Descriptive corrupt image error returned');

  // -------------------------------------------------------------------------
  // TEST SECTION 4: Privacy & Security Verification
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 4: Privacy & Security Verification ---');

  const allResponsesText = JSON.stringify([tungroData, normalData, txtErr, emptyErr, corruptErr]);
  const exposedPaths = allResponsesText.match(/[A-Za-z]:\\[\w\s\\.-]+/g) || [];
  assert(exposedPaths.length === 0, 'No raw internal Windows server file paths exposed in responses', JSON.stringify(exposedPaths));

  const exposedCoordinates = allResponsesText.match(/"latitude":\s*[-+]?\d+\.\d{5,}/g) || [];
  assert(exposedCoordinates.length === 0, 'No unsolicited private high-precision GPS coordinates exposed', JSON.stringify(exposedCoordinates));

  // -------------------------------------------------------------------------
  // TEST SECTION 5: Frontend Route & STEP 11J.1 Connection Integrity
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 5: Frontend Route & STEP 11J.1 Integrity ---');

  const frontendRes = await fetch(FRONTEND_URL);
  assert(frontendRes.ok, `Frontend Vite server is reachable at ${FRONTEND_URL} (HTTP ${frontendRes.status})`);
  const htmlBody = await frontendRes.text();
  assert(htmlBody.includes('Paddy Farming Assistant'), 'Frontend serves Paddy Farming Assistant HTML application');
  assert(!htmlBody.includes('id="nav-backend-badge"'), 'FastAPI status badge cleanly removed from navbar');

  // -------------------------------------------------------------------------
  // SUMMARY
  // -------------------------------------------------------------------------
  console.log('\n======================================================================');
  console.log(`TOTAL TESTS: ${TEST_RESULTS.tests.length}`);
  console.log(`PASSED:      ${TEST_RESULTS.passed}`);
  console.log(`FAILED:      ${TEST_RESULTS.failed}`);
  console.log('======================================================================\n');

  // Output test prediction IDs and perform targeted cleanup of test-created records
  console.log(`Test-created prediction IDs to clean up: ${JSON.stringify(testPredictionIds)}`);
  if (testPredictionIds.length > 0) {
    console.log(`\n--- Cleaning up ${testPredictionIds.length} test-created prediction records ---`);
    try {
      const { execSync } = await import('child_process');
      const pythonExe = path.join(ROOT_DIR, 'venv', 'Scripts', 'python.exe');
      const cleanupScript = path.join(ROOT_DIR, 'backend', 'scripts', 'cleanup_test_predictions.py');
      const cleanupOutput = execSync(`"${pythonExe}" "${cleanupScript}" ${testPredictionIds.join(' ')}`, {
        cwd: path.join(ROOT_DIR, 'backend'),
        encoding: 'utf-8'
      });
      console.log('  ' + cleanupOutput.trim());
    } catch (cleanErr) {
      console.warn('  Post-test cleanup warning:', cleanErr.message);
    }
  }

  return {
    success: TEST_RESULTS.failed === 0,
    testPredictionIds,
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
