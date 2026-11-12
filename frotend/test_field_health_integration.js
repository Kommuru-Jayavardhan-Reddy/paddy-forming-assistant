/**
 * STEP 11J.3 — Field Health Frontend Integration Verification Suite
 * Tests:
 * 1. Code & Component Structure Verification (client.ts, types.ts, FieldHealth.jsx, fieldHealth.js)
 * 2. Live Backend Field Endpoints (/fields, /fields/{id}, /health, /timeseries)
 * 3. Exact Multi-Spectral Response Schemas (NDVI, NDRE, GNDVI, changes_and_trends)
 * 4. Graceful Error Handling for Unknown Fields & Empty Data
 * 5. Privacy Protection (Raw coordinates & internal paths hidden)
 * 6. Existing Routes & Navigation Integrity
 * 7. Database Integrity Verification (all 7 tables remain unmodified)
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
  console.log('STEP 11J.3 — Field Health Frontend Integration Verification');
  console.log(`Backend Target:  ${BACKEND_URL}`);
  console.log(`Frontend Target: ${FRONTEND_URL}`);
  console.log('======================================================================\n');

  // -------------------------------------------------------------------------
  // TEST SECTION 1: Code & Component Structure Verification
  // -------------------------------------------------------------------------
  console.log('--- TEST SECTION 1: Code & Component Verification ---');

  const clientPath = path.join(__dirname, 'src', 'api', 'client.ts');
  assert(fs.existsSync(clientPath), 'client.ts exists', clientPath);
  const clientContent = fs.readFileSync(clientPath, 'utf-8');
  assert(clientContent.includes('export const getFields'), 'client.ts exports getFields()');
  assert(clientContent.includes('export const getField ='), 'client.ts exports getField()');
  assert(clientContent.includes('export const getFieldHealth'), 'client.ts exports getFieldHealth()');
  assert(clientContent.includes('export const getFieldTimeSeries'), 'client.ts exports getFieldTimeSeries()');

  const typesPath = path.join(__dirname, 'src', 'api', 'types.ts');
  assert(fs.existsSync(typesPath), 'types.ts exists', typesPath);
  const typesContent = fs.readFileSync(typesPath, 'utf-8');
  assert(typesContent.includes('export interface CatalogFieldsResponse'), 'types.ts exports CatalogFieldsResponse');
  assert(typesContent.includes('export interface FieldDetailResponse'), 'types.ts exports FieldDetailResponse');
  assert(typesContent.includes('export interface FieldHealthResponse'), 'types.ts exports FieldHealthResponse');
  assert(typesContent.includes('export interface SatelliteTimeSeriesResponse'), 'types.ts exports SatelliteTimeSeriesResponse');
  assert(typesContent.includes('export interface VegetationIndexValues'), 'types.ts exports VegetationIndexValues');

  const fieldHealthCompPath = path.join(__dirname, 'src', 'components', 'FieldHealth.jsx');
  assert(fs.existsSync(fieldHealthCompPath), 'FieldHealth.jsx exists', fieldHealthCompPath);
  const compContent = fs.readFileSync(fieldHealthCompPath, 'utf-8');
  assert(compContent.includes('getFieldHealth'), 'FieldHealth.jsx calls getFieldHealth');
  assert(compContent.includes('getFieldTimeSeries'), 'FieldHealth.jsx calls getFieldTimeSeries');
  assert(compContent.includes('#dcfce7') || compContent.includes('Healthy'), 'FieldHealth.jsx implements Green = Healthy color scheme');
  assert(compContent.includes('#fef3c7') || compContent.includes('Needs Attention'), 'FieldHealth.jsx implements Amber = Needs Attention color scheme');
  assert(compContent.includes('#fee2e2') || compContent.includes('High Risk'), 'FieldHealth.jsx implements Red = High Risk color scheme');
  assert(compContent.includes('NDVI'), 'FieldHealth.jsx displays NDVI metric');
  assert(compContent.includes('NDRE'), 'FieldHealth.jsx displays NDRE metric');
  assert(compContent.includes('GNDVI'), 'FieldHealth.jsx displays GNDVI metric');

  const dashboardPath = path.join(__dirname, 'src', 'components', 'Dashboard.jsx');
  const dashContent = fs.readFileSync(dashboardPath, 'utf-8');
  assert(dashContent.includes('FieldHealth'), 'Dashboard.jsx imports and mounts FieldHealth component');

  const vanillaJsPath = path.join(__dirname, 'src', 'fieldHealth.js');
  assert(fs.existsSync(vanillaJsPath), 'fieldHealth.js exists', vanillaJsPath);
  const vanillaContent = fs.readFileSync(vanillaJsPath, 'utf-8');
  assert(vanillaContent.includes('getApiBaseUrl'), 'fieldHealth.js implements dynamic getApiBaseUrl');
  assert(vanillaContent.includes('/fields/'), 'fieldHealth.js fetches field records from /fields');
  assert(vanillaContent.includes('/health'), 'fieldHealth.js fetches field health from /health');
  assert(vanillaContent.includes('/timeseries'), 'fieldHealth.js fetches satellite time-series from /timeseries');

  const indexHtmlPath = path.join(__dirname, 'index.html');
  const indexHtml = fs.readFileSync(indexHtmlPath, 'utf-8');
  assert(indexHtml.includes('id="page-field-health"'), 'index.html contains #page-field-health');
  assert(indexHtml.includes('id="health-field-selector"'), 'index.html contains #health-field-selector');
  assert(indexHtml.includes('id="health-trend-chart"'), 'index.html contains #health-trend-chart canvas');

  // -------------------------------------------------------------------------
  // TEST SECTION 2: Real Backend Endpoint Verification
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 2: Real FastAPI Backend Endpoints ---');

  // Test 2.1: GET /fields
  console.log('  Testing GET /fields...');
  const fieldsRes = await fetch(`${BACKEND_URL}/fields?limit=100`);
  assert(fieldsRes.ok, `GET /fields returned HTTP ${fieldsRes.status}`);
  const fieldsData = await fieldsRes.json();
  assert(Array.isArray(fieldsData.fields), 'Fields response contains fields array');
  assert(fieldsData.total_fields === 58, `Total fields is 58 (got ${fieldsData.total_fields})`);
  assert(fieldsData.fields.length > 0, `Fields array is populated (count: ${fieldsData.fields.length})`);

  const firstField = fieldsData.fields[0];
  const testFieldId = firstField.field_id;
  assert(typeof testFieldId === 'string' && testFieldId.length > 0, `Field has valid identifier: ${testFieldId}`);
  assert(typeof firstField.field_name === 'string', `Field has field_name: ${firstField.field_name}`);

  // Test 2.2: GET /fields/{field_id}
  console.log(`  Testing GET /fields/${testFieldId}...`);
  const fieldDetailRes = await fetch(`${BACKEND_URL}/fields/${testFieldId}`);
  assert(fieldDetailRes.ok, `GET /fields/${testFieldId} returned HTTP ${fieldDetailRes.status}`);
  const fieldDetail = await fieldDetailRes.json();
  assert(fieldDetail.field_id === testFieldId, `Field ID matches requested: ${fieldDetail.field_id}`);
  assert(fieldDetail.observation_count === 10, `Field has 10 satellite observations`);

  // Test 2.3: GET /fields/{field_id}/health
  console.log(`  Testing GET /fields/${testFieldId}/health...`);
  const healthRes = await fetch(`${BACKEND_URL}/fields/${testFieldId}/health`);
  assert(healthRes.ok, `GET /fields/${testFieldId}/health returned HTTP ${healthRes.status}`);
  const healthData = await healthRes.json();
  assert(healthData.field_id === testFieldId, 'Health response field_id matches');
  assert(healthData.latest_indices && typeof healthData.latest_indices.ndvi === 'number', 'Latest indices contains numeric NDVI');
  assert(typeof healthData.latest_indices.ndre === 'number', 'Latest indices contains numeric NDRE');
  assert(typeof healthData.latest_indices.gndvi === 'number', 'Latest indices contains numeric GNDVI');
  assert(healthData.changes_and_trends && healthData.changes_and_trends.ndvi, 'Changes and trends contains NDVI');
  assert(['increasing', 'decreasing', 'stable'].includes(healthData.changes_and_trends.ndvi.direction), `NDVI direction is cautious: ${healthData.changes_and_trends.ndvi.direction}`);
  assert(typeof healthData.advisory_summary === 'string' && healthData.advisory_summary.length > 0, 'Advisory summary is provided');
  assert(Array.isArray(healthData.limitations_and_interpretation_notes), 'Interpretation notes array provided');

  // Test 2.4: GET /fields/{field_id}/timeseries
  console.log(`  Testing GET /fields/${testFieldId}/timeseries...`);
  const tsRes = await fetch(`${BACKEND_URL}/fields/${testFieldId}/timeseries`);
  assert(tsRes.ok, `GET /fields/${testFieldId}/timeseries returned HTTP ${tsRes.status}`);
  const tsData = await tsRes.json();
  assert(tsData.field_id === testFieldId, 'Time-series field_id matches');
  assert(tsData.total_timesteps === 10, `Total timesteps is 10 (got ${tsData.total_timesteps})`);
  assert(Array.isArray(tsData.timesteps) && tsData.timesteps.length === 10, 'Timesteps array contains 10 observations');
  assert(tsData.features.includes('NDVI') && tsData.features.includes('NDRE') && tsData.features.includes('GNDVI'), 'Features include NDVI, NDRE, GNDVI');

  const firstTimestep = tsData.timesteps[0];
  assert(typeof firstTimestep.timestep === 'number', 'Timestep has sequence number');
  assert(typeof firstTimestep.ndvi === 'number', 'Timestep has numeric NDVI');
  assert(typeof firstTimestep.ndre === 'number', 'Timestep has numeric NDRE');
  assert(typeof firstTimestep.gndvi === 'number', 'Timestep has numeric GNDVI');

  // -------------------------------------------------------------------------
  // TEST SECTION 3: Edge Cases, Unknown Fields & Error Handling
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 3: Edge Cases & Error Handling ---');

  const invalidFieldId = 'FIELD_UNKNOWN_9999';
  console.log(`  Testing error response for unknown field: ${invalidFieldId}...`);

  const invFieldRes = await fetch(`${BACKEND_URL}/fields/${invalidFieldId}`);
  assert(invFieldRes.status === 404, `Unknown field returns HTTP 404 (got ${invFieldRes.status})`);
  const invFieldErr = await invFieldRes.json();
  assert(invFieldErr.error === 'FieldNotFoundError', 'Error type is FieldNotFoundError');

  const invHealthRes = await fetch(`${BACKEND_URL}/fields/${invalidFieldId}/health`);
  assert(invHealthRes.status === 404, `Unknown field health returns HTTP 404 (got ${invHealthRes.status})`);

  const invTsRes = await fetch(`${BACKEND_URL}/fields/${invalidFieldId}/timeseries`);
  assert(invTsRes.status === 404, `Unknown field time-series returns HTTP 404 (got ${invTsRes.status})`);

  // -------------------------------------------------------------------------
  // TEST SECTION 4: Privacy & Coordinate Protection
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 4: Privacy & Security Verification ---');

  const allApiResponses = JSON.stringify([fieldsData, fieldDetail, healthData, tsData, invFieldErr]);
  const exposedPaths = allApiResponses.match(/[A-Za-z]:\\[\w\s\\.-]+/g) || [];
  assert(exposedPaths.length === 0, 'No raw internal Windows server file paths exposed', JSON.stringify(exposedPaths));

  // Check that frontend files don't render raw coordinate strings in user-facing UI labels
  assert(!compContent.includes('Latitude:') && !compContent.includes('Longitude:'), 'FieldHealth.jsx does not display raw latitude/longitude labels');

  // -------------------------------------------------------------------------
  // TEST SECTION 5: Frontend Route & Service Integrity
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 5: Frontend Route & Service Integrity ---');

  const feRes = await fetch(FRONTEND_URL);
  assert(feRes.ok, `Frontend Vite dev server is reachable at ${FRONTEND_URL} (HTTP ${feRes.status})`);

  const html = await feRes.text();
  assert(html.includes('page-detection'), 'Disease Detection route preserved in navigation');
  assert(html.includes('page-field-health'), 'Field Health route preserved in navigation');
  assert(html.includes('page-react'), 'React Assistant route preserved in navigation');

  // -------------------------------------------------------------------------
  // TEST SECTION 6: Database Integrity Check (All 7 tables)
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
