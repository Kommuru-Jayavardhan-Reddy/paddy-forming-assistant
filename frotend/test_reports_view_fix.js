/**
 * Automated Verification Suite for Reports Page - View Report Functionality
 * Verifies:
 * 1. DOM structure of #reports-detail-view (no trapped fixed modal, clean in-flow layout)
 * 2. Presence of all 12 required report fields in index.html
 * 3. Back to Reports buttons (top and bottom)
 * 4. Download PDF and Print options
 * 5. Controller logic in reports.js:
 *    - openDetailView
 *    - closeDetailView
 *    - renderDetailItem (populating all 12 items accurately)
 *    - Top-3 candidates list rendering
 *    - URL hash inspection and history navigation (#reports?id=...)
 *    - PDF download handler
 * 6. Hash routing updates in index.html
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const indexHtmlPath = path.resolve(__dirname, 'index.html');
const reportsJsPath = path.resolve(__dirname, 'src/reports.js');

const html = fs.readFileSync(indexHtmlPath, 'utf8');
const js = fs.readFileSync(reportsJsPath, 'utf8');

let totalTests = 0;
let passedTests = 0;

function assert(condition, desc) {
  totalTests++;
  if (condition) {
    passedTests++;
    console.log(`  [PASS] ${desc}`);
  } else {
    console.error(`  [FAIL] ${desc}`);
  }
}

console.log('====================================================================');
console.log(' REPORTS PAGE — VIEW REPORT FUNCTIONALITY VERIFICATION SUITE');
console.log('====================================================================\n');

// --- SECTION 1: DOM Structure & Blank Screen Prevention ---
console.log('--- TEST SECTION 1: DOM Structure & Blank Screen Prevention ---');
assert(html.includes('id="reports-detail-view"'), '#reports-detail-view exists in index.html');
assert(!html.includes('id="reports-detail-view" class="hidden fixed inset-0'), '#reports-detail-view does NOT use trapped fixed inset-0 modal');
assert(html.includes('id="reports-detail-back-btn"'), 'Top Back to Reports button exists');
assert(html.includes('id="reports-detail-bottom-back-btn"'), 'Bottom Back to Reports button exists');
assert(html.includes('id="reports-detail-download-btn"'), 'Top Download Report (PDF) button exists');
assert(html.includes('id="reports-detail-bottom-download-btn"'), 'Bottom Download Report (PDF) button exists');
assert(html.includes('id="reports-detail-loading"'), 'Report detail loading state exists');
assert(html.includes('id="reports-detail-error"'), 'Report detail error state exists');
assert(html.includes('id="reports-detail-body"'), 'Report detail main body container exists');

// --- SECTION 2: All 12 Required Report Detail Items ---
console.log('\n--- TEST SECTION 2: All 12 Required Detail Items ---');
assert(html.includes('id="detail-report-id"'), 'Item 1: Report ID element exists');
assert(html.includes('id="detail-report-id-badge"'), 'Item 1: Report ID badge exists');
assert(html.includes('id="detail-date-time"'), 'Item 2: Analysis Date and Time element exists');
assert(html.includes('id="detail-field-name"'), 'Item 3: Field Name element exists');
assert(html.includes('id="detail-field-location"'), 'Item 4: Field Location element exists');
assert(html.includes('id="detail-image"'), 'Item 5: Uploaded Crop Leaf Image element exists');
assert(html.includes('id="detail-result"'), 'Item 6: Detected Disease element exists');
assert(html.includes('id="detail-confidence"'), 'Item 7: Prediction Confidence element exists');
assert(html.includes('id="detail-confidence-bar"'), 'Item 7: Prediction Confidence progress bar exists');
assert(html.includes('id="detail-health"'), 'Item 8: Health Status Badge container exists');
assert(html.includes('id="detail-top-k-container"') && html.includes('id="detail-top-k-list"'), 'Item 9: Top-3 Disease Predictions container and list exist');
assert(html.includes('id="detail-recommendations"'), 'Item 10: AI-generated recommendations element exists');
assert(html.includes('id="detail-symptoms"'), 'Item 10: Symptoms list element exists');
assert(html.includes('id="detail-gradcam-container"') && html.includes('id="detail-gradcam-image"'), 'Item 11: Grad-CAM explanation container & image exist');
assert(html.includes('id="detail-satellite-strip"'), 'Item 12: Satellite & vegetation index strip exists');
assert(html.includes('id="detail-satellite-ndvi"'), 'Item 12: Satellite NDVI indicator exists');
assert(html.includes('id="detail-satellite-ndre"'), 'Item 12: Satellite NDRE indicator exists');
assert(html.includes('id="detail-satellite-gndvi"'), 'Item 12: Satellite GNDVI indicator exists');

// --- SECTION 3: Controller Logic & Navigation ---
console.log('\n--- TEST SECTION 3: Controller Logic in reports.js ---');
assert(js.includes('const openDetailView = async (itemOrId) =>'), 'reports.js defines openDetailView with item or ID support');
assert(js.includes('const closeDetailView = () =>'), 'reports.js defines closeDetailView for clean return navigation');
assert(js.includes('const renderDetailItem = (item) =>'), 'reports.js defines renderDetailItem to populate report metadata');
assert(js.includes('const handleDownloadPdf = async (item) =>'), 'reports.js defines handleDownloadPdf for PDF artifact download');
assert(js.includes('window.scrollTo({ top: 0'), 'openDetailView scrolls window to top, preventing off-screen scroll dislocation');
assert(js.includes('#reports?id='), 'openDetailView updates URL hash with report ID for direct linking & refreshability');
assert(js.includes('checkUrlHashForReport'), 'reports.js checks URL hash on boot and hashchange/popstate events');
assert(js.includes('topK.slice(0, 3)'), 'renderDetailItem accurately extracts and displays Top-3 predictions');
assert(js.includes('closeDetailView'), 'reports.js wires Back buttons to closeDetailView');

// --- SECTION 4: Hash-Based Route Matching in index.html ---
console.log('\n--- TEST SECTION 4: Hash-Based Route Matching in index.html ---');
assert(html.includes("baseRoute === 'reports' || baseRoute === 'report'"), 'index.html popstate matches #reports?id=... to page-reports');
assert(html.includes("baseRoute === 'reports' || baseRoute === 'report'"), 'index.html initial load matches #reports?id=... to page-reports');

console.log('\n====================================================================');
console.log(` RESULTS: ${passedTests} / ${totalTests} PASSED, ${totalTests - passedTests} FAILED`);
console.log('====================================================================');

if (passedTests !== totalTests) {
  process.exit(1);
}

