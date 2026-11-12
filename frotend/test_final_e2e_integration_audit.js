/**
 * STEP 11J.7 — Final Comprehensive End-to-End Integration Testing & Audit Suite
 * 
 * Performs an end-to-end integration audit across:
 * - TASK 1: Backend Health, DB Connectivity, Model Warm-up, CORS, and Error Handling
 * - TASK 2: Disease Detection (Image-Only with EfficientNet-B4 & Multimodal with Cross-Attention)
 * - TASK 3: Field Health & Satellite Monitoring (Sentinel-2 NDVI/NDRE/GNDVI & Time Series)
 * - TASK 4: Crop Insights & Attention Distribution (Authentic Predictions, No Mock Data)
 * - TASK 5: Weather, Mandi Market Prices, and Verified Buyers Directory
 * - TASK 6: Reports Archive & Certified PDF Generation/Download
 * - TASK 7: Frontend Dev Server, Build Bundle, and Route Integrity
 * - TASK 8: Security & Privacy Audits (No Leaked Secrets, No Server Paths, No Raw GPS)
 * - TASK 9: Database Baseline Integrity & Isolated Exact Test Cleanup
 */

import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

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

const TRACKED_TEST_PREDICTION_IDS = [];
const TRACKED_TEST_REPORT_IDS = [];

function recordTest(section, name, passed, details = '') {
  TEST_RESULTS.total++;
  if (passed) {
    TEST_RESULTS.passed++;
    console.log(`  [PASS] [${section}] ${name}`);
  } else {
    TEST_RESULTS.failed++;
    console.error(`  [FAIL] [${section}] ${name}: ${details}`);
  }
  TEST_RESULTS.tests.push({ section, name, passed, details });
}

function assert(section, condition, message) {
  recordTest(section, message, Boolean(condition), condition ? '' : 'Assertion condition failed');
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
        timeout: options.timeout || 30000,
      },
      (res) => {
        const chunks = [];
        res.on('data', (chunk) => { chunks.push(chunk); });
        res.on('end', () => {
          const buffer = Buffer.concat(chunks);
          const text = buffer.toString('utf-8');
          resolve({
            status: res.statusCode,
            headers: res.headers,
            buffer: () => Promise.resolve(buffer),
            text: () => Promise.resolve(text),
            json: () => {
              try {
                return Promise.resolve(JSON.parse(text));
              } catch {
                return Promise.reject(new Error(`Failed to parse JSON: ${text.slice(0, 100)}`));
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

function buildMultipartFormData(fields, fileField) {
  const boundary = `----PaddyFormBoundary${Date.now()}`;
  const buffers = [];

  for (const [key, val] of Object.entries(fields)) {
    buffers.push(Buffer.from(
      `--${boundary}\r\nContent-Disposition: form-data; name="${key}"\r\n\r\n${val}\r\n`
    ));
  }

  if (fileField) {
    buffers.push(Buffer.from(
      `--${boundary}\r\nContent-Disposition: form-data; name="${fileField.name}"; filename="${fileField.filename}"\r\nContent-Type: ${fileField.contentType}\r\n\r\n`
    ));
    buffers.push(fileField.data);
    buffers.push(Buffer.from('\r\n'));
  }

  buffers.push(Buffer.from(`--${boundary}--\r\n`));
  const body = Buffer.concat(buffers);

  return {
    headers: {
      'Content-Type': `multipart/form-data; boundary=${boundary}`,
      'Content-Length': body.length.toString(),
    },
    body,
  };
}

async function runComprehensiveAudit() {
  console.log('======================================================================');
  console.log('STEP 11J.7 — FINAL INTEGRATION AUDIT & END-TO-END VERIFICATION');
  console.log('Backend Target: ', BACKEND_BASE);
  console.log('Frontend Target:', FRONTEND_BASE);
  console.log('======================================================================\n');

  // =========================================================================
  // TASK 1: BACKEND HEALTH & INFRASTRUCTURE
  // =========================================================================
  console.log('--- TASK 1: Backend Health, Connectivity & Infrastructure ---');

  // 1. Root / health
  const healthRes = await httpFetch(`${BACKEND_BASE}/health`);
  assert('TASK 1', healthRes.status === 200, 'GET /health returns HTTP 200 OK');
  const healthData = await healthRes.json();
  assert('TASK 1', healthData.status === 'healthy', `Backend service status is "healthy" (got: ${healthData.status})`);
  assert('TASK 1', healthData.service === 'Paddy Farming Assistant API', 'Service identity confirmed');

  // 2. Database connectivity
  const dbHealthRes = await httpFetch(`${BACKEND_BASE}/health/database`);
  assert('TASK 1', dbHealthRes.status === 200, 'GET /health/database returns HTTP 200 OK');
  const dbHealthData = await dbHealthRes.json();
  assert('TASK 1', dbHealthData.connected === true && dbHealthData.status === 'healthy', 'PostgreSQL database connectivity confirmed');

  // 3. Model warm-up readiness
  const modelHealthRes = await httpFetch(`${BACKEND_BASE}/health/model`);
  assert('TASK 1', modelHealthRes.status === 200, 'GET /health/model returns HTTP 200 OK');
  const modelHealthData = await modelHealthRes.json();
  assert('TASK 1', modelHealthData.model_loaded === true, 'EfficientNet-B4 AI model is loaded');
  assert('TASK 1', modelHealthData.device === 'cpu', `Inference device confirmed as CPU (got: ${modelHealthData.device})`);

  // 4. CORS verification
  const corsRes = await httpFetch(`${BACKEND_BASE}/health`, {
    headers: { 'Origin': 'http://127.0.0.1:5173' }
  });
  assert('TASK 1', corsRes.headers['access-control-allow-origin'] === 'http://127.0.0.1:5173',
    'CORS header correctly echoes frontend origin http://127.0.0.1:5173');
  assert('TASK 1', corsRes.headers['access-control-allow-credentials'] === 'true',
    'CORS allow-credentials is true');

  // 5. Global Error Handling
  const notFoundRes = await httpFetch(`${BACKEND_BASE}/api/v1/nonexistent_endpoint_xyz`);
  assert('TASK 1', notFoundRes.status === 404, 'Unmapped routes return HTTP 404 cleanly');

  // =========================================================================
  // TASK 2: DISEASE DETECTION (IMAGE-ONLY & MULTIMODAL)
  // =========================================================================
  console.log('\n--- TASK 2: Disease Detection AI Inference (Image-Only & Multimodal) ---');

  const tungroImagePath = path.join(ROOT_DIR, 'backend', 'test_images', 'tungro', 'TUNGRO5_67.JPG');
  const normalImagePath = path.join(ROOT_DIR, 'backend', 'test_images', 'normal', '100111.jpg');
  assert('TASK 2', fs.existsSync(tungroImagePath), 'Authentic Tungro test image exists');
  assert('TASK 2', fs.existsSync(normalImagePath), 'Authentic Normal test image exists');

  // 1. Image-Only Prediction (EfficientNet-B4)
  const tungroBytes = fs.readFileSync(tungroImagePath);
  const multipartImageOnly = buildMultipartFormData(
    { language: 'en', question: 'What disease affects this leaf?' },
    { name: 'file', filename: 'TUNGRO5_67.JPG', contentType: 'image/jpeg', data: tungroBytes }
  );

  const predictRes = await httpFetch(`${BACKEND_BASE}/predict`, {
    method: 'POST',
    headers: multipartImageOnly.headers,
    body: multipartImageOnly.body,
  });

  assert('TASK 2', predictRes.status === 200, 'POST /predict (Image-Only) returns HTTP 200');
  const predictData = await predictRes.json();
  assert('TASK 2', predictData.disease === 'tungro', `Image-only classified leaf correctly as "tungro" (got: ${predictData.disease})`);
  assert('TASK 2', predictData.confidence >= 0.80, `High confidence score: ${(predictData.confidence * 100).toFixed(2)}% >= 80%`);
  assert('TASK 2', Array.isArray(predictData.top3) && predictData.top3.length === 3, 'Top-3 candidates array returned');
  assert('TASK 2', predictData.device === 'cpu', 'Image inference executed on CPU device');
  assert('TASK 2', Boolean(predictData.prediction_id), `Prediction persisted with UUID: ${predictData.prediction_id}`);
  if (predictData.prediction_id) {
    TRACKED_TEST_PREDICTION_IDS.push(predictData.prediction_id);
  }

  // 2. Multimodal Prediction (EfficientNet-B4 + Sentinel-2 Time-Series Cross-Attention)
  const multipartMultimodal = buildMultipartFormData(
    { field_id: 'FIELD_01' },
    { name: 'file', filename: 'TUNGRO5_67.JPG', contentType: 'image/jpeg', data: tungroBytes }
  );

  const multimodalRes = await httpFetch(`${BACKEND_BASE}/predict/multimodal`, {
    method: 'POST',
    headers: multipartMultimodal.headers,
    body: multipartMultimodal.body,
  });

  assert('TASK 2', multimodalRes.status === 200, 'POST /predict/multimodal returns HTTP 200');
  const multimodalData = await multimodalRes.json();
  assert('TASK 2', multimodalData.prediction_mode === 'multimodal', 'Prediction mode is explicitly "multimodal"');
  assert('TASK 2', Array.isArray(multimodalData.temporal_attention_weights), 'Multimodal inference returns temporal_attention_weights');
  assert('TASK 2', multimodalData.temporal_attention_weights.length === 10,
    `Temporal attention weights match 10 satellite timesteps (got: ${multimodalData.temporal_attention_weights?.length})`);
  assert('TASK 2', multimodalData.satellite_timesteps === 10, 'Satellite timesteps count is 10');
  assert('TASK 2', Boolean(multimodalData.prediction_id), `Multimodal prediction persisted with UUID: ${multimodalData.prediction_id}`);
  if (multimodalData.prediction_id) {
    TRACKED_TEST_PREDICTION_IDS.push(multimodalData.prediction_id);
  }

  // 3. Supported Classes Verification (13 Classes)
  const classesRes = await httpFetch(`${BACKEND_BASE}/classes`);
  assert('TASK 2', classesRes.status === 200, 'GET /classes returns HTTP 200');
  const classesData = await classesRes.json();
  const classesList = classesData.classes || classesData;
  assert('TASK 2', Array.isArray(classesList) && classesList.length === 13,
    `Supported classes count matches 13 paddy conditions (got: ${classesList.length})`);

  // 4. Input Validation & Error Handling
  // Unsupported format
  const invalidExtMultipart = buildMultipartFormData(
    {},
    { name: 'file', filename: 'test.txt', contentType: 'text/plain', data: Buffer.from('not an image') }
  );
  const invalidExtRes = await httpFetch(`${BACKEND_BASE}/predict`, {
    method: 'POST',
    headers: invalidExtMultipart.headers,
    body: invalidExtMultipart.body,
  });
  assert('TASK 2', invalidExtRes.status === 415, 'Unsupported file format rejected with HTTP 415');

  // Empty image file
  const emptyFileMultipart = buildMultipartFormData(
    {},
    { name: 'file', filename: 'empty.jpg', contentType: 'image/jpeg', data: Buffer.alloc(0) }
  );
  const emptyFileRes = await httpFetch(`${BACKEND_BASE}/predict`, {
    method: 'POST',
    headers: emptyFileMultipart.headers,
    body: emptyFileMultipart.body,
  });
  assert('TASK 2', emptyFileRes.status === 400, 'Empty image file rejected with HTTP 400');

  // =========================================================================
  // TASK 3: FIELD HEALTH & SATELLITE MONITORING
  // =========================================================================
  console.log('\n--- TASK 3: Field Health & Satellite Monitoring ---');

  // 1. Fields Catalog
  const fieldsRes = await httpFetch(`${BACKEND_BASE}/fields`);
  assert('TASK 3', fieldsRes.status === 200, 'GET /fields returns HTTP 200');
  const fieldsData = await fieldsRes.json();
  assert('TASK 3', fieldsData.total_fields === 58, `Catalog contains 58 agricultural fields (actual: ${fieldsData.total_fields})`);

  // 2. Field Detail
  const fieldDetailRes = await httpFetch(`${BACKEND_BASE}/fields/FIELD_01`);
  assert('TASK 3', fieldDetailRes.status === 200, 'GET /fields/FIELD_01 returns HTTP 200');
  const fieldDetailData = await fieldDetailRes.json();
  assert('TASK 3', fieldDetailData.field_id === 'FIELD_01', 'Field identifier is FIELD_01');
  assert('TASK 3', fieldDetailData.observation_count === 10, 'Field has 10 satellite observations');

  // 3. Field Health Analysis
  const fieldHealthRes = await httpFetch(`${BACKEND_BASE}/fields/FIELD_01/health`);
  assert('TASK 3', fieldHealthRes.status === 200, 'GET /fields/FIELD_01/health returns HTTP 200');
  const fieldHealthData = await fieldHealthRes.json();
  assert('TASK 3', typeof fieldHealthData.latest_indices?.ndvi === 'number',
    `Latest NDVI index is numeric: ${fieldHealthData.latest_indices?.ndvi}`);
  assert('TASK 3', typeof fieldHealthData.latest_indices?.ndre === 'number',
    `Latest NDRE index is numeric: ${fieldHealthData.latest_indices?.ndre}`);
  assert('TASK 3', typeof fieldHealthData.latest_indices?.gndvi === 'number',
    `Latest GNDVI index is numeric: ${fieldHealthData.latest_indices?.gndvi}`);
  assert('TASK 3', Boolean(fieldHealthData.advisory_summary), 'Agronomic advisory summary is present');

  // 4. Satellite Time-Series (10 Timesteps)
  const timeseriesRes = await httpFetch(`${BACKEND_BASE}/fields/FIELD_01/timeseries`);
  assert('TASK 3', timeseriesRes.status === 200, 'GET /fields/FIELD_01/timeseries returns HTTP 200');
  const timeseriesData = await timeseriesRes.json();
  assert('TASK 3', timeseriesData.total_timesteps === 10, 'Satellite time series contains 10 observations');
  assert('TASK 3', Array.isArray(timeseriesData.timesteps) && timeseriesData.timesteps.length === 10,
    'Timesteps array is populated with 10 observations');

  // 5. Unknown Field (404)
  const unknownFieldRes = await httpFetch(`${BACKEND_BASE}/fields/FIELD_UNKNOWN_9999`);
  assert('TASK 3', unknownFieldRes.status === 404, 'Unknown field returns HTTP 404');

  // =========================================================================
  // TASK 4: CROP INSIGHTS & ATTENTION DISTRIBUTION
  // =========================================================================
  console.log('\n--- TASK 4: Crop Insights & Attention Distribution ---');

  const historyRes = await httpFetch(`${BACKEND_BASE}/predictions?page_size=50`);
  assert('TASK 4', historyRes.status === 200, 'GET /predictions returns HTTP 200');
  const historyData = await historyRes.json();
  assert('TASK 4', historyData.total_predictions >= 35, `History includes seeded predictions (count: ${historyData.total_predictions})`);

  // Multimodal attention weights are validated as attention vectors (not SHAP)
  const mmRecord = historyData.predictions.find(p => p.prediction_mode === 'multimodal' && p.attention_weights);
  assert('TASK 4', Boolean(mmRecord), 'Multimodal prediction with attention weights found in history');
  if (mmRecord) {
    assert('TASK 4', Array.isArray(mmRecord.attention_weights) && mmRecord.attention_weights.length === 10,
      'Attention weights vector has 10 timesteps representing cross-attention');
  }

  // =========================================================================
  // TASK 5: WEATHER, MANDI PRICES & BUYERS DIRECTORY
  // =========================================================================
  console.log('\n--- TASK 5: Weather, Mandi Prices & Buyers Directory ---');

  // 1. Current Weather
  const weatherCurrRes = await httpFetch(
    `${BACKEND_BASE}/weather/current?latitude=10.787&longitude=79.1378&timezone=Asia/Kolkata`
  );
  assert('TASK 5', weatherCurrRes.status === 200, 'GET /weather/current returns HTTP 200');
  const weatherCurrData = await weatherCurrRes.json();
  assert('TASK 5', typeof weatherCurrData.current?.temperature === 'number',
    `Current temperature returned: ${weatherCurrData.current?.temperature}°C`);

  // 2. Weather Forecast (7 Days)
  const weatherForeRes = await httpFetch(
    `${BACKEND_BASE}/weather/forecast?latitude=10.787&longitude=79.1378&forecast_days=7&timezone=Asia/Kolkata`
  );
  assert('TASK 5', weatherForeRes.status === 200, 'GET /weather/forecast returns HTTP 200');
  const weatherForeData = await weatherForeRes.json();
  assert('TASK 5', weatherForeData.daily_forecast?.length === 7, '7-day daily forecast returned');

  // 3. Field Weather
  const fieldWeatherRes = await httpFetch(`${BACKEND_BASE}/fields/FIELD_01/weather`);
  assert('TASK 5', fieldWeatherRes.status === 200, 'GET /fields/FIELD_01/weather returns HTTP 200');

  // 4. Mandi Spot Prices (100 seeded records)
  const marketPricesRes = await httpFetch(`${BACKEND_BASE}/market/prices?limit=10`);
  assert('TASK 5', marketPricesRes.status === 200, 'GET /market/prices returns HTTP 200');
  const marketPricesData = await marketPricesRes.json();
  assert('TASK 5', marketPricesData.total === 100, `Market prices total count matches 100 seeded records (actual: ${marketPricesData.total})`);

  // 5. Market Summary
  const marketSumRes = await httpFetch(`${BACKEND_BASE}/market/analytics/summary?commodity=Paddy%20(Dhan)`);
  assert('TASK 5', marketSumRes.status === 200, 'GET /market/analytics/summary returns HTTP 200');
  const marketSumData = await marketSumRes.json();
  assert('TASK 5', marketSumData.avg_modal_price > 0, `Average modal price calculated: ₹${marketSumData.avg_modal_price}/quintal`);

  // 6. Buyers Directory (17 seeded records)
  const buyersRes = await httpFetch(`${BACKEND_BASE}/buyers?limit=50`);
  assert('TASK 5', buyersRes.status === 200, 'GET /buyers returns HTTP 200');
  const buyersData = await buyersRes.json();
  assert('TASK 5', buyersData.total === 17, `Buyers total count matches 17 seeded records (actual: ${buyersData.total})`);

  // 7. Nearby Buyers with Null Coordinates Fallback
  const nearbyRes = await httpFetch(`${BACKEND_BASE}/buyers/nearby?lat=10.787&lon=79.1378&radius_km=50`);
  assert('TASK 5', nearbyRes.status === 200, 'GET /buyers/nearby returns HTTP 200');
  const nearbyData = await nearbyRes.json();
  assert('TASK 5', nearbyData.total === 0, 'Nearby buyers returns 0 when coordinates are null (preserves privacy)');

  // =========================================================================
  // TASK 6: REPORTS ARCHIVE & PDF DOWNLOAD
  // =========================================================================
  console.log('\n--- TASK 6: Reports Archive & PDF Download ---');

  // 1. Reports List (4 baseline records)
  const reportsRes = await httpFetch(`${BACKEND_BASE}/reports`);
  assert('TASK 6', reportsRes.status === 200, 'GET /reports returns HTTP 200');
  const reportsData = await reportsRes.json();
  assert('TASK 6', reportsData.total_reports >= 4, `Reports total count includes 4 baseline records (actual: ${reportsData.total_reports})`);

  // 2. Generate Report for genuine prediction (force_regenerate=true)
  const existingPredId = '04dd0f48-859a-4a9d-8cc0-f58385b07ef0';
  const genReportRes = await httpFetch(
    `${BACKEND_BASE}/reports/generate/${existingPredId}?file_format=pdf&force_regenerate=true`,
    { method: 'POST' }
  );
  assert('TASK 6', genReportRes.status === 201, 'POST /reports/generate with force_regenerate=true returns HTTP 201 Created');
  const genReportData = await genReportRes.json();
  assert('TASK 6', Boolean(genReportData.id), `Report compiled with ID: ${genReportData.id}`);
  if (genReportData.id) {
    TRACKED_TEST_REPORT_IDS.push(genReportData.id);
  }

  // 3. Download Generated PDF Artifact
  const downloadRes = await httpFetch(`${BACKEND_BASE}/reports/${genReportData.id}/download`);
  assert('TASK 6', downloadRes.status === 200, 'GET /reports/{id}/download returns HTTP 200');
  const downloadContentType = downloadRes.headers['content-type'] || '';
  assert('TASK 6', downloadContentType.includes('application/pdf'), 'Content-Type is application/pdf');

  const pdfBuf = await downloadRes.buffer();
  const magic = pdfBuf.slice(0, 5).toString('ascii');
  assert('TASK 6', magic === '%PDF-', `Binary stream begins with valid %PDF- magic header (got: ${magic})`);

  // =========================================================================
  // TASK 7: FRONTEND END-TO-END & BUILD
  // =========================================================================
  console.log('\n--- TASK 7: Frontend Dev Server, Build & Module Integrity ---');

  // 1. Vite server reachable
  const viteRes = await httpFetch(FRONTEND_BASE);
  assert('TASK 7', viteRes.status === 200, `Vite dev server is online at ${FRONTEND_BASE}`);

  // 2. npm run build execution
  try {
    const buildOutput = execSync('npm run build', {
      cwd: path.join(ROOT_DIR, 'frotend'),
      encoding: 'utf-8',
    });
    const builtOk = buildOutput.includes('built in') || buildOutput.includes('dist/index.html');
    assert('TASK 7', builtOk, 'npm run build completed cleanly without compilation errors');
  } catch (buildErr) {
    recordTest('TASK 7', 'npm run build', false, buildErr.message);
  }

  // 3. Navigation containers integrity
  const indexHtml = fs.readFileSync(path.join(ROOT_DIR, 'frotend', 'index.html'), 'utf-8');
  assert('TASK 7', indexHtml.includes('id="page-detection"'), 'Disease detection page container preserved');
  assert('TASK 7', indexHtml.includes('id="page-field-health"'), 'Field health page container preserved');
  assert('TASK 7', indexHtml.includes('id="page-crop-insights"'), 'Crop insights page container preserved');
  assert('TASK 7', indexHtml.includes('id="page-market-buyers"'), 'Market & buyers page container preserved');
  assert('TASK 7', indexHtml.includes('id="page-reports"'), 'Reports page container preserved');
  assert('TASK 7', indexHtml.includes('id="page-home"'), 'Home page container preserved');
  assert('TASK 7', indexHtml.includes('id="page-react"'), 'React assistant page container preserved');

  // =========================================================================
  // TASK 8: SECURITY & PRIVACY AUDIT
  // =========================================================================
  console.log('\n--- TASK 8: Security & Privacy Audits ---');

  const envContent = fs.readFileSync(path.join(ROOT_DIR, 'frotend', '.env'), 'utf-8');
  assert('TASK 8', !envContent.includes('PASSWORD') && !envContent.includes('SECRET'),
    'Frontend .env does not expose passwords or secrets');
  assert('TASK 8', envContent.includes('VITE_API_BASE_URL'),
    'Frontend uses centralized VITE_API_BASE_URL configuration');

  const gitignoreContent = fs.readFileSync(path.join(ROOT_DIR, 'frotend', '.gitignore'), 'utf-8');
  assert('TASK 8', gitignoreContent.includes('.env'), '.env is listed in .gitignore');

  // Check no raw GPS exposed in labels
  const weatherMarketCode = fs.readFileSync(path.join(ROOT_DIR, 'frotend', 'src', 'components', 'WeatherMarket.jsx'), 'utf-8');
  assert('TASK 8', !weatherMarketCode.includes('latitude:') && !weatherMarketCode.includes('longitude:'),
    'WeatherMarket.jsx does not display raw latitude/longitude labels');

  const predHistoryCode = fs.readFileSync(path.join(ROOT_DIR, 'frotend', 'src', 'components', 'PredictionHistory.jsx'), 'utf-8');
  assert('TASK 8', !predHistoryCode.includes('latitude:') && !predHistoryCode.includes('longitude:'),
    'PredictionHistory.jsx does not display raw latitude/longitude labels');

  // =========================================================================
  // TASK 9: EXACT TEST CLEANUP & DATABASE ROW COUNT AUDIT
  // =========================================================================
  console.log('\n--- TASK 9: Isolated Cleanup & Final Database Integrity Audit ---');

  const pythonExe = path.join(ROOT_DIR, 'venv', 'Scripts', 'python.exe');

  // 1. Clean test predictions
  if (TRACKED_TEST_PREDICTION_IDS.length > 0) {
    const cleanPredScript = path.join(ROOT_DIR, 'backend', 'cleanup_test_prediction.py');
    for (const predId of TRACKED_TEST_PREDICTION_IDS) {
      try {
        execSync(`"${pythonExe}" "${cleanPredScript}" "${predId}"`, {
          cwd: path.join(ROOT_DIR, 'backend'),
          encoding: 'utf-8'
        });
        console.log(`  Cleaned test prediction: ${predId.slice(0, 8)}...`);
      } catch (err) {
        console.warn(`  Warning: failed to clean test prediction ${predId}:`, err.message);
      }
    }
  }

  // 2. Clean test reports
  if (TRACKED_TEST_REPORT_IDS.length > 0) {
    const cleanReportScript = path.join(ROOT_DIR, 'backend', 'cleanup_test_report.py');
    for (const repId of TRACKED_TEST_REPORT_IDS) {
      try {
        execSync(`"${pythonExe}" "${cleanReportScript}" "${repId}"`, {
          cwd: path.join(ROOT_DIR, 'backend'),
          encoding: 'utf-8'
        });
        console.log(`  Cleaned test report: ${repId.slice(0, 8)}...`);
      } catch (err) {
        console.warn(`  Warning: failed to clean test report ${repId}:`, err.message);
      }
    }
  }

  // 3. Clean test weather cache records (id > 117)
  const cleanWeatherScript = path.join(ROOT_DIR, 'backend', 'cleanup_weather_test_records.py');
  try {
    execSync(`"${pythonExe}" "${cleanWeatherScript}"`, {
      cwd: path.join(ROOT_DIR, 'backend'),
      encoding: 'utf-8'
    });
    console.log('  Cleaned test-created weather records (restored to baseline).');
  } catch (err) {
    console.warn('  Warning: failed to clean weather records:', err.message);
  }

  // 4. Verify exact database row counts
  try {
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

      assert('TASK 9', counts.buyers === 17, 'buyers table count unchanged (17)');
      assert('TASK 9', counts.market_prices === 100, 'market_prices table count unchanged (100)');
      assert('TASK 9', counts.fields === 58, 'fields table count unchanged (58)');
      assert('TASK 9', counts.satellite_observations === 580, 'satellite_observations table count unchanged (580)');
      assert('TASK 9', counts.prediction_history >= 35, 'prediction_history table preserved baseline (>= 35)');
      assert('TASK 9', counts.weather_records >= 98, 'weather_records table preserved baseline (>= 98)');
      assert('TASK 9', counts.reports === 4, 'reports table strictly restored to baseline (4)');
    } else {
      recordTest('TASK 9', 'Database count verification', false, 'Could not parse DB counts from python output');
    }
  } catch (dbErr) {
    recordTest('TASK 9', 'Database count verification', false, dbErr.message);
  }

  // =========================================================================
  // SUMMARY
  // =========================================================================
  console.log('\n======================================================================');
  console.log(`TOTAL AUDIT TESTS: ${TEST_RESULTS.tests.length}`);
  console.log(`PASSED:            ${TEST_RESULTS.passed}`);
  console.log(`FAILED:            ${TEST_RESULTS.failed}`);
  console.log('======================================================================\n');

  return {
    success: TEST_RESULTS.failed === 0,
    summary: TEST_RESULTS,
  };
}

runComprehensiveAudit()
  .then((res) => {
    if (!res.success) {
      process.exit(1);
    }
  })
  .catch((err) => {
    console.error('Unhandled audit execution error:', err);
    process.exit(1);
  });
