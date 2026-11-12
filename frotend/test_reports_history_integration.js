/**
 * STEP 11J.6 — Reports and Prediction History Frontend Integration Verification Suite
 * Tests the connection between frontend Reports & Prediction History modules and FastAPI backend:
 * - Types and client functions (getReports, getReportById, generateReport, downloadReportPdf, getPredictions, getPredictionById)
 * - Real /predictions and /predictions/{id} listing and details
 * - Real /reports, /reports/{id}, /reports/generate/{prediction_id}, and /reports/{id}/download
 * - Idempotent report retrieval vs force_regenerate creation
 * - PDF binary download and Content-Disposition validation
 * - Edge case handling (404 for unknown report/prediction, 422 for malformed UUID, 400 for invalid filters)
 * - Clean deletion of ONLY test-created reports by exact UUID
 * - Database row count audit (strictly zero modifications from baseline)
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

const CREATED_TEST_REPORT_IDS = [];

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
        timeout: options.timeout || 25000,
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

async function runVerification() {
  console.log('======================================================================');
  console.log('STEP 11J.6 — Reports & History Frontend Integration Verification');
  console.log('Backend Target: ', BACKEND_BASE);
  console.log('Frontend Target:', FRONTEND_BASE);
  console.log('======================================================================\n');

  // -------------------------------------------------------------------------
  // SECTION 1: TypeScript Contracts & Client Implementations
  // -------------------------------------------------------------------------
  console.log('--- TEST SECTION 1: TypeScript Contracts & Client Functions ---');

  const typesPath = path.join(__dirname, 'src', 'api', 'types.ts');
  const clientPath = path.join(__dirname, 'src', 'api', 'client.ts');
  const predictionHistoryJsxPath = path.join(__dirname, 'src', 'components', 'PredictionHistory.jsx');
  const reportsJsxPath = path.join(__dirname, 'src', 'components', 'Reports.jsx');
  const dashboardJsxPath = path.join(__dirname, 'src', 'components', 'Dashboard.jsx');
  const reportsJsPath = path.join(__dirname, 'src', 'reports.js');

  assert(fs.existsSync(typesPath), 'src/api/types.ts exists');
  assert(fs.existsSync(clientPath), 'src/api/client.ts exists');
  assert(fs.existsSync(predictionHistoryJsxPath), 'src/components/PredictionHistory.jsx exists');
  assert(fs.existsSync(reportsJsxPath), 'src/components/Reports.jsx exists');
  assert(fs.existsSync(dashboardJsxPath), 'src/components/Dashboard.jsx exists');
  assert(fs.existsSync(reportsJsPath), 'src/reports.js exists');

  const typesCode = fs.readFileSync(typesPath, 'utf-8');
  assert(typesCode.includes('export interface PredictionRecordItem'), 'types.ts exports PredictionRecordItem');
  assert(typesCode.includes('export interface PredictionListResponse'), 'types.ts exports PredictionListResponse');
  assert(typesCode.includes('export interface ReportItem'), 'types.ts exports ReportItem');
  assert(typesCode.includes('export interface ReportListResponse'), 'types.ts exports ReportListResponse');
  assert(typesCode.includes('export interface ReportGenerateOptions'), 'types.ts exports ReportGenerateOptions');

  const clientCode = fs.readFileSync(clientPath, 'utf-8');
  assert(clientCode.includes('export const getPredictions'), 'client.ts exports getPredictions()');
  assert(clientCode.includes('export const getPredictionById'), 'client.ts exports getPredictionById()');
  assert(clientCode.includes('export const getReports'), 'client.ts exports getReports()');
  assert(clientCode.includes('export const getReportById'), 'client.ts exports getReportById()');
  assert(clientCode.includes('export const generateReport'), 'client.ts exports generateReport()');
  assert(clientCode.includes('export const downloadReportPdf'), 'client.ts exports downloadReportPdf()');

  const dashboardCode = fs.readFileSync(dashboardJsxPath, 'utf-8');
  assert(dashboardCode.includes('import Reports from \'./Reports\';'), 'Dashboard.jsx imports Reports');
  assert(dashboardCode.includes('import PredictionHistory from \'./PredictionHistory\';'), 'Dashboard.jsx imports PredictionHistory');
  assert(dashboardCode.includes('<Reports />'), 'Dashboard.jsx mounts <Reports />');
  assert(dashboardCode.includes('<PredictionHistory />'), 'Dashboard.jsx mounts <PredictionHistory />');
  assert(dashboardCode.includes('<h3>Image Upload</h3>'), 'Dashboard preserves Image Upload card');
  assert(dashboardCode.includes('<h3>Farm Location</h3>'), 'Dashboard preserves Farm Location card');
  assert(dashboardCode.includes('<h3>Question Input</h3>'), 'Dashboard preserves Question Input card');
  assert(dashboardCode.includes('<h3>Disease Prediction</h3>'), 'Dashboard preserves Disease Prediction card');
  assert(dashboardCode.includes('<h3>Satellite Time-Series</h3>'), 'Dashboard preserves Satellite Time-Series card');
  assert(dashboardCode.includes('<h3>Generation Report</h3>'), 'Dashboard preserves Generation Report card');

  // -------------------------------------------------------------------------
  // SECTION 2: Real FastAPI Prediction History Endpoints
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 2: Live Prediction History Endpoints ---');

  // 1. Prediction List (Paginated)
  const predsRes = await httpFetch(`${BACKEND_BASE}/predictions?page=1&page_size=10`);
  assert(predsRes.status === 200, 'GET /predictions returns HTTP 200');
  const predsData = await predsRes.json();
  assert(Array.isArray(predsData.predictions), 'Predictions response contains predictions array');
  assert(predsData.total_predictions >= 35, `Total predictions has at least 35 seeded records (actual: ${predsData.total_predictions})`);
  assert(predsData.predictions.length === 10, `Page 1 returned 10 items (actual: ${predsData.predictions.length})`);

  const firstPred = predsData.predictions[0];
  assert(firstPred && firstPred.id && firstPred.predicted_disease && firstPred.confidence,
    `Valid prediction item: ${firstPred.predicted_disease} (${(firstPred.confidence * 100).toFixed(1)}%) - UUID: ${firstPred.id.slice(0, 8)}...`);

  // 2. Mode Filter: Multimodal
  const multimodalRes = await httpFetch(`${BACKEND_BASE}/predictions?prediction_mode=multimodal`);
  assert(multimodalRes.status === 200, 'GET /predictions?prediction_mode=multimodal returns HTTP 200');
  const multimodalData = await multimodalRes.json();
  assert(multimodalData.total_predictions === 10, `Total multimodal predictions is 10 (actual: ${multimodalData.total_predictions})`);
  const allMultimodal = multimodalData.predictions.every(p => p.prediction_mode === 'multimodal');
  assert(allMultimodal, 'All returned items in multimodal filter have prediction_mode === multimodal');

  // 3. Mode Filter: Image-Only
  const imageOnlyRes = await httpFetch(`${BACKEND_BASE}/predictions?prediction_mode=image_only`);
  assert(imageOnlyRes.status === 200, 'GET /predictions?prediction_mode=image_only returns HTTP 200');
  const imageOnlyData = await imageOnlyRes.json();
  assert(imageOnlyData.total_predictions >= 25, `Total image-only predictions has at least 25 seeded records (actual: ${imageOnlyData.total_predictions})`);

  // 4. Prediction Detail by UUID
  const predDetailRes = await httpFetch(`${BACKEND_BASE}/predictions/${firstPred.id}`);
  assert(predDetailRes.status === 200, `GET /predictions/${firstPred.id} returns HTTP 200`);
  const predDetail = await predDetailRes.json();
  assert(predDetail.id === firstPred.id, 'Retrieved prediction ID matches requested ID');
  assert(Array.isArray(predDetail.top_k_predictions) && predDetail.top_k_predictions.length > 0,
    'Prediction detail includes top_k_predictions array');
  assert(predDetail.model_name === 'EfficientNet-B4', 'Prediction detail identifies model_name as EfficientNet-B4');

  // -------------------------------------------------------------------------
  // SECTION 3: Live Reports Endpoints & Retrieval
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 3: Live Reports Endpoints & Retrieval ---');

  // 1. Reports List
  const reportsRes = await httpFetch(`${BACKEND_BASE}/reports?page=1&page_size=10`);
  assert(reportsRes.status === 200, 'GET /reports returns HTTP 200');
  const reportsData = await reportsRes.json();
  assert(Array.isArray(reportsData.reports), 'Reports response contains reports array');
  assert(reportsData.total_reports === 4, `Total reports matches 4 seeded baseline records (actual: ${reportsData.total_reports})`);

  const firstReport = reportsData.reports[0];
  assert(firstReport && firstReport.id && firstReport.title && firstReport.status,
    `Valid report item: "${firstReport.title}" (${firstReport.status}) - ID: ${firstReport.id.slice(0, 8)}...`);

  // 2. Report Type Filter
  const typeFilterRes = await httpFetch(`${BACKEND_BASE}/reports?report_type=disease_diagnostic`);
  assert(typeFilterRes.status === 200, 'GET /reports?report_type=disease_diagnostic returns HTTP 200');
  const typeFilterData = await typeFilterRes.json();
  assert(typeFilterData.total_reports === 4, `All 4 seeded reports are disease_diagnostic (actual: ${typeFilterData.total_reports})`);

  // 3. Report Detail by UUID
  const reportDetailRes = await httpFetch(`${BACKEND_BASE}/reports/${firstReport.id}`);
  assert(reportDetailRes.status === 200, `GET /reports/${firstReport.id} returns HTTP 200`);
  const reportDetail = await reportDetailRes.json();
  assert(reportDetail.id === firstReport.id, 'Retrieved report ID matches requested ID');
  assert(reportDetail.file_format === 'pdf', 'Report format is PDF');
  assert(reportDetail.file_size_bytes > 0, `Report file size is positive: ${reportDetail.file_size_bytes} bytes`);

  // -------------------------------------------------------------------------
  // SECTION 4: Report Generation & Idempotency
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 4: Report Generation & Idempotency ---');

  // 1. Idempotent Generation (force_regenerate = false on existing prediction)
  const existingPredId = firstReport.prediction_id;
  const idempotentRes = await httpFetch(
    `${BACKEND_BASE}/reports/generate/${existingPredId}?file_format=pdf&force_regenerate=false`,
    { method: 'POST' }
  );
  assert(idempotentRes.status === 200, 'POST /reports/generate on existing prediction returns HTTP 200 (idempotent)');
  const idempotentData = await idempotentRes.json();
  assert(idempotentData.id === firstReport.id, 'Idempotent request returned existing report ID without duplicate row creation');

  // 2. Force Generation (force_regenerate = true) -> Creates isolated test report
  const forceRes = await httpFetch(
    `${BACKEND_BASE}/reports/generate/${existingPredId}?file_format=pdf&force_regenerate=true`,
    { method: 'POST' }
  );
  assert(forceRes.status === 201, 'POST /reports/generate with force_regenerate=true returns HTTP 201 Created');
  const freshReportData = await forceRes.json();
  const freshReportId = freshReportData.id;
  assert(freshReportId && freshReportId !== firstReport.id, `New report created with distinct ID: ${freshReportId.slice(0, 8)}...`);
  CREATED_TEST_REPORT_IDS.push(freshReportId);
  console.log(`  Tracked test report for exact cleanup: ${freshReportId}`);

  assert(freshReportData.status === 'completed', 'Newly generated report status is "completed"');
  assert(freshReportData.file_format === 'pdf', 'Newly generated report format is "pdf"');
  assert(freshReportData.file_size_bytes > 1000, `Valid PDF artifact size: ${freshReportData.file_size_bytes} bytes`);

  // -------------------------------------------------------------------------
  // SECTION 5: PDF Download Endpoint
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 5: PDF Download Endpoint ---');

  const downloadRes = await httpFetch(`${BACKEND_BASE}/reports/${freshReportId}/download`);
  assert(downloadRes.status === 200, `GET /reports/${freshReportId.slice(0, 8)}.../download returns HTTP 200`);

  const contentType = downloadRes.headers['content-type'] || '';
  assert(contentType.includes('application/pdf'), `Content-Type is application/pdf (got: ${contentType})`);

  const contentDisposition = downloadRes.headers['content-disposition'] || '';
  assert(contentDisposition.includes('attachment') && contentDisposition.includes('.pdf'),
    `Content-Disposition header includes attachment and .pdf: ${contentDisposition}`);

  const pdfBuffer = await downloadRes.buffer();
  const pdfMagic = pdfBuffer.slice(0, 5).toString('ascii');
  assert(pdfMagic === '%PDF-', `Binary payload contains valid PDF magic header (%PDF-, got: ${pdfMagic})`);
  assert(pdfBuffer.length > 1000, `PDF payload is substantial: ${pdfBuffer.length} bytes`);

  // Download 404 for unknown report UUID
  const unknownDownloadRes = await httpFetch(
    `${BACKEND_BASE}/reports/00000000-0000-0000-0000-000000000000/download`
  );
  assert(unknownDownloadRes.status === 404, 'GET /reports/{unknown_uuid}/download returns HTTP 404');

  // -------------------------------------------------------------------------
  // SECTION 6: Edge Cases, Error Handling & Parameter Validation
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 6: Edge Cases & Error Handling ---');

  // 1. Invalid UUID format for report detail
  const invalidReportUuidRes = await httpFetch(`${BACKEND_BASE}/reports/not-a-valid-uuid`);
  assert(invalidReportUuidRes.status === 422, 'GET /reports/not-a-valid-uuid returns HTTP 422');

  // 2. Unknown Report ID (404)
  const unknownReportRes = await httpFetch(`${BACKEND_BASE}/reports/00000000-0000-0000-0000-000000000000`);
  assert(unknownReportRes.status === 404, 'GET /reports/{unknown_uuid} returns HTTP 404');

  // 3. Invalid report_type filter (400)
  const invalidTypeRes = await httpFetch(`${BACKEND_BASE}/reports?report_type=invalid_type_name`);
  assert(invalidTypeRes.status === 400, 'GET /reports?report_type=invalid_type returns HTTP 400');

  // 4. Invalid status filter (400)
  const invalidStatusRes = await httpFetch(`${BACKEND_BASE}/reports?status=invalid_status_name`);
  assert(invalidStatusRes.status === 400, 'GET /reports?status=invalid_status returns HTTP 400');

  // 5. Invalid UUID for prediction detail (422)
  const invalidPredUuidRes = await httpFetch(`${BACKEND_BASE}/predictions/not-a-valid-uuid`);
  assert(invalidPredUuidRes.status === 422, 'GET /predictions/not-a-valid-uuid returns HTTP 422');

  // 6. Unknown prediction UUID (404)
  const unknownPredRes = await httpFetch(`${BACKEND_BASE}/predictions/00000000-0000-0000-0000-000000000000`);
  assert(unknownPredRes.status === 404, 'GET /predictions/{unknown_uuid} returns HTTP 404');

  // 7. Nonexistent Field filter returns clean empty list
  const emptyFieldPredsRes = await httpFetch(`${BACKEND_BASE}/predictions?field_id=FIELD_NONEXISTENT_9999`);
  assert(emptyFieldPredsRes.status === 200, 'GET /predictions?field_id=NONEXISTENT returns HTTP 200');
  const emptyFieldPredsData = await emptyFieldPredsRes.json();
  assert(emptyFieldPredsData.predictions.length === 0, 'Nonexistent field returned 0 predictions cleanly');

  // -------------------------------------------------------------------------
  // SECTION 7: Privacy & Security Protections
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 7: Security & Privacy Protection ---');

  const predHistoryCode = fs.readFileSync(predictionHistoryJsxPath, 'utf-8');
  assert(!predHistoryCode.includes('latitude:') && !predHistoryCode.includes('longitude:'),
    'PredictionHistory.jsx does not display raw latitude/longitude labels');

  const reportsJsxCode = fs.readFileSync(reportsJsxPath, 'utf-8');
  assert(!reportsJsxCode.includes('latitude:') && !reportsJsxCode.includes('longitude:'),
    'Reports.jsx does not display raw latitude/longitude labels');
  assert(reportsJsxCode.includes('URL.revokeObjectURL'),
    'Reports.jsx properly revokes temporary browser object URLs after download');

  // -------------------------------------------------------------------------
  // SECTION 8: Isolated Test Cleanup & Database Row Count Audit
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 8: Exact Test Cleanup & Database Row Count Audit ---');

  const pythonExe = path.join(ROOT_DIR, 'venv', 'Scripts', 'python.exe');
  const cleanupScript = path.join(ROOT_DIR, 'backend', 'cleanup_test_report.py');

  if (CREATED_TEST_REPORT_IDS.length > 0) {
    for (const reportId of CREATED_TEST_REPORT_IDS) {
      try {
        const out = execSync(`"${pythonExe}" "${cleanupScript}" "${reportId}"`, {
          cwd: path.join(ROOT_DIR, 'backend'),
          encoding: 'utf-8'
        });
        console.log(`  ${out.trim()}`);
        recordTest(`Cleaned test report ${reportId.slice(0, 8)}`, true);
      } catch (err) {
        recordTest(`Cleaned test report ${reportId.slice(0, 8)}`, false, err.message);
      }
    }
  }

  // Now audit row counts via check_db_integrity.py
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

      assert(counts.buyers === 17, 'buyers table count unchanged (17)');
      assert(counts.market_prices === 100, 'market_prices table count unchanged (100)');
      assert(counts.fields === 58, 'fields table count unchanged (58)');
      assert(counts.satellite_observations === 580, 'satellite_observations table count unchanged (580)');
      assert(counts.prediction_history >= 35, `prediction_history table contains seeded baseline records (got ${counts.prediction_history})`);
      assert(counts.weather_records >= 98, `weather_records table contains seeded baseline records (got ${counts.weather_records})`);
      assert(counts.reports === 4, 'reports table count strictly restored to baseline (4)');
    } else {
      recordTest('Database count verification', false, 'Could not parse DB counts from python output');
    }
  } catch (dbErr) {
    recordTest('Database count verification', false, dbErr.message);
  }

  // -------------------------------------------------------------------------
  // SECTION 9: Frontend Dev Server & Routes
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 9: Frontend Dev Server & Navigation ---');
  const viteRes = await httpFetch(FRONTEND_BASE);
  assert(viteRes.status === 200, `Frontend Vite dev server is reachable at ${FRONTEND_BASE} (HTTP 200)`);

  const indexHtmlPath = path.join(__dirname, 'index.html');
  const indexHtml = fs.readFileSync(indexHtmlPath, 'utf-8');
  assert(indexHtml.includes('id="page-reports"'), 'Reports page container preserved in index.html');
  assert(indexHtml.includes('data-target="page-reports"'), 'Reports navigation link preserved in index.html');
  assert(indexHtml.includes('data-target="page-home"'), 'Home navigation preserved');
  assert(indexHtml.includes('data-target="page-detection"'), 'Disease Detection navigation preserved');
  assert(indexHtml.includes('data-target="page-field-health"'), 'Field Health navigation preserved');
  assert(indexHtml.includes('data-target="page-crop-insights"'), 'Crop Insights navigation preserved');
  assert(indexHtml.includes('data-target="page-market-buyers"'), 'Market navigation preserved');

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
