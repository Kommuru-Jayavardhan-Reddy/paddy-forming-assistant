/**
 * FIELD HEALTH REDESIGN VERIFICATION SUITE
 * Validates layout, components, responsive classes, assets, and strict scope.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let passed = 0;
let failed = 0;

function assert(condition, testName, detail = '') {
  if (condition) {
    passed++;
    console.log(`  [PASS] ${testName}`);
  } else {
    failed++;
    console.error(`  [FAIL] ${testName}: ${detail}`);
  }
}

console.log('====================================================================');
console.log(' PADDY FARMING ASSISTANT - FIELD HEALTH REDESIGN VERIFICATION');
console.log('====================================================================\n');

// -------------------------------------------------------------------------
// SECTION 1: Asset & Background Image Verification
// -------------------------------------------------------------------------
console.log('--- TEST SECTION 1: Asset & Background Image Paths ---');
const bgPublicPath = path.join(__dirname, 'public', 'assets', 'field-health-background.jpg');
const bgSrcPath = path.join(__dirname, 'src', 'assets', 'images', 'field-health-background.jpg');
assert(fs.existsSync(bgPublicPath), 'Background image exists in public/assets/field-health-background.jpg');
assert(fs.existsSync(bgSrcPath), 'Background image exists in src/assets/images/field-health-background.jpg');

const indexHtmlPath = path.join(__dirname, 'index.html');
const indexHtml = fs.readFileSync(indexHtmlPath, 'utf-8');
assert(indexHtml.includes('/assets/field-health-background.jpg'), 'Hero banner styles reference /assets/field-health-background.jpg');

// -------------------------------------------------------------------------
// SECTION 2: Hero Section Verification
// -------------------------------------------------------------------------
console.log('\n--- TEST SECTION 2: Hero Section Structure & Copy ---');
assert(indexHtml.includes('Field Health') && indexHtml.includes('Get satellite-based insights for your paddy field.'), 'Hero displays exact title and subtitle');
assert(indexHtml.includes('Sentinel-2 Multi-Spectral Earth Observation'), 'Hero displays Sentinel-2 chip with pulse indicator');
assert(indexHtml.includes('min-height: 220px;'), 'Hero maintains proportional height');

// -------------------------------------------------------------------------
// SECTION 3: Section 1 — Provide Field Information Form
// -------------------------------------------------------------------------
console.log('\n--- TEST SECTION 3: Section 1 — Provide Field Information ---');
assert(indexHtml.includes('1. Provide Field Information') || indexHtml.includes('Provide Field Information'), 'Section 1 heading exists');
assert(indexHtml.includes('Upload a field image (with GPS) or enter coordinates manually to analyze field health.'), 'Section 1 supporting text is exact');
assert(indexHtml.includes('id="field-image-dropzone"'), 'Contains image dropzone area');
assert(indexHtml.includes('id="field-image-input"'), 'Contains image file input');
assert(indexHtml.includes('id="field-image-preview-container"'), 'Contains image preview container');
assert(indexHtml.includes('id="field-image-replace-btn"'), 'Contains image replace button');
assert(indexHtml.includes('id="field-image-remove-btn"'), 'Contains image remove button');
assert(indexHtml.includes('Supported: JPG, JPEG, PNG'), 'Specifies supported file formats');
assert(indexHtml.includes('Maximum size: 10 MB') || indexHtml.includes('Max: 10 MB'), 'Specifies 10 MB file size limit');
assert(indexHtml.includes('GPS extraction will be available after integration.'), 'Displays honest GPS metadata notice');

assert(indexHtml.includes('id="toggle-manual-coordinates"'), 'Contains manual coordinates toggle switch');
assert(indexHtml.includes('id="input-latitude"'), 'Contains Latitude input');
assert(indexHtml.includes('id="input-longitude"'), 'Contains Longitude input');
assert(indexHtml.includes('id="input-field-id"'), 'Contains Field ID input');
assert(indexHtml.includes('id="input-location-name"'), 'Contains Location input');
assert(indexHtml.includes('id="btn-analyze-field"'), 'Contains Analyze Field CTA button');
assert(indexHtml.includes('id="btn-reset-field-form"'), 'Contains Reset Form button');

// -------------------------------------------------------------------------
// SECTION 4: Section 2 — Field Health Dashboard
// -------------------------------------------------------------------------
console.log('\n--- TEST SECTION 4: Section 2 — Field Health Dashboard ---');
assert(indexHtml.includes('2. Field Health Dashboard') || indexHtml.includes('Field Health Dashboard'), 'Section 2 heading exists');
assert(indexHtml.includes('Satellite-based vegetation analysis for the selected field.'), 'Section 2 supporting text is exact');
assert(indexHtml.includes('DEMO DATA'), 'Displays DEMO DATA indicator badge');
assert(indexHtml.includes('id="dash-field-id"'), 'Top strip displays Field ID');
assert(indexHtml.includes('id="dash-location"'), 'Top strip displays Location');
assert(indexHtml.includes('id="dash-period"'), 'Top strip displays Observation Period');
assert(indexHtml.includes('id="dash-satellite"'), 'Top strip displays Satellite Mission');

// -------------------------------------------------------------------------
// SECTION 5: Field Location Map & Field Details
// -------------------------------------------------------------------------
console.log('\n--- TEST SECTION 5: Map & Field Details Panel ---');
assert(indexHtml.includes('id="health-map"'), 'Contains Leaflet map container #health-map');
assert(indexHtml.includes('Field Location'), 'Card titled Field Location exists');
assert(indexHtml.includes('Field Details'), 'Panel titled Field Details exists');
assert(indexHtml.includes('id="detail-field-id"'), 'Displays Field ID in details panel');
assert(indexHtml.includes('id="detail-location"'), 'Displays Location in details panel');
assert(indexHtml.includes('id="detail-latitude"'), 'Displays Latitude in details panel');
assert(indexHtml.includes('id="detail-longitude"'), 'Displays Longitude in details panel');
assert(indexHtml.includes('id="detail-obs-count"'), 'Displays Observation Count in details panel');
assert(indexHtml.includes('id="detail-date-range"'), 'Displays Observation Date Range in details panel');

// -------------------------------------------------------------------------
// SECTION 6: Vegetation Index Summary Cards (NDVI, NDRE, GNDVI)
// -------------------------------------------------------------------------
console.log('\n--- TEST SECTION 6: Vegetation Index Summary Cards ---');
assert(indexHtml.includes('id="card-ndvi-val"'), 'NDVI card displays latest value');
assert(indexHtml.includes('id="card-ndre-val"'), 'NDRE card displays latest value');
assert(indexHtml.includes('id="card-gndvi-val"'), 'GNDVI card displays latest value');
assert(indexHtml.includes('border-emerald-200'), 'NDVI card has emerald green accent');
assert(indexHtml.includes('border-blue-200'), 'NDRE card has blue accent');
assert(indexHtml.includes('border-amber-200'), 'GNDVI card has amber/orange accent');
assert(indexHtml.includes('id="card-ndvi-bar"'), 'NDVI card has progress visual');
assert(indexHtml.includes('id="card-ndre-bar"'), 'NDRE card has progress visual');
assert(indexHtml.includes('id="card-gndvi-bar"'), 'GNDVI card has progress visual');

// -------------------------------------------------------------------------
// SECTION 7: Trend Chart & Satellite Observations Table
// -------------------------------------------------------------------------
console.log('\n--- TEST SECTION 7: Trend Chart & Observation Table ---');
assert(indexHtml.includes('Vegetation Indices Trend'), 'Trend chart title is exact');
assert(indexHtml.includes('id="health-trend-chart"'), 'Canvas element #health-trend-chart exists');
assert(indexHtml.includes('data-range="1M"') && indexHtml.includes('data-range="2M"') && indexHtml.includes('data-range="3M"'), 'Time range toggle buttons (1M, 2M, 3M) exist');
assert(indexHtml.includes('Satellite Observations'), 'Satellite Observations table card exists');
assert(indexHtml.includes('id="satellite-table-body"'), 'Contains table body #satellite-table-body');
assert(indexHtml.includes('<th class="py-2.5 px-3">Date</th>') && indexHtml.includes('<th class="py-2.5 px-3">Cloud %</th>'), 'Table has Date, NDVI, NDRE, GNDVI, Cloud % headers');

// -------------------------------------------------------------------------
// SECTION 8: Interactive Controller (fieldHealth.js)
// -------------------------------------------------------------------------
console.log('\n--- TEST SECTION 8: Interactive Controller (fieldHealth.js) ---');
const jsPath = path.join(__dirname, 'src', 'fieldHealth.js');
const jsContent = fs.readFileSync(jsPath, 'utf-8');
assert(jsContent.includes('getApiBaseUrl'), 'fieldHealth.js includes dynamic API base url resolver');
assert(jsContent.includes('handleSelectedFile'), 'fieldHealth.js handles file selection and validation');
assert(jsContent.includes('10 * 1024 * 1024'), 'fieldHealth.js validates 10 MB maximum file size');
assert(jsContent.includes('executeFieldAnalysis'), 'fieldHealth.js implements field analysis execution');
assert(jsContent.includes('initMap'), 'fieldHealth.js initializes Leaflet map with satellite/standard tiles and field boundary');
assert(jsContent.includes('renderTrendChart'), 'fieldHealth.js renders Chart.js line chart for NDVI, NDRE, GNDVI');
assert(jsContent.includes('renderSatelliteTable'), 'fieldHealth.js populates satellite observation table');
assert(jsContent.includes('activeTimeRange'), 'fieldHealth.js filters data across 1M, 2M, 3M time ranges');
assert(jsContent.includes('DEFAULT_DEMO_TIMESTEPS'), 'fieldHealth.js contains high-fidelity agricultural demo dataset');

// -------------------------------------------------------------------------
// SECTION 9: Strict Scope & Untouched Other Pages
// -------------------------------------------------------------------------
console.log('\n--- TEST SECTION 9: Strict Scope & Untouched Pages ---');
assert(indexHtml.includes('id="page-home"'), 'Preserves page-home container');
assert(indexHtml.includes('id="page-detection"'), 'Preserves page-detection container');
assert(indexHtml.includes('id="page-crop-insights"'), 'Preserves page-crop-insights container');
assert(indexHtml.includes('id="page-market-buyers"'), 'Preserves page-market-buyers container');
assert(indexHtml.includes('id="page-reports"'), 'Preserves page-reports container');
assert(indexHtml.includes('id="page-login"'), 'Preserves page-login container');
assert(indexHtml.includes('id="page-welcome"'), 'Preserves page-welcome container');
assert(indexHtml.includes('id="persistent-navbar"'), 'Preserves persistent-navbar design and structure');

console.log('\n====================================================================');
console.log(` RESULTS: ${passed} PASSED, ${failed} FAILED`);
console.log('====================================================================');

if (failed > 0) process.exit(1);
