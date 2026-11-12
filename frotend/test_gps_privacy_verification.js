/**
 * Frontend GPS Privacy & Buyer Directory Verification Suite
 * Tests that raw coordinates and technical metadata are completely hidden from UI,
 * verifies district filtering, empty nearby-buyer state, and API functionality.
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

async function httpGet(urlStr) {
  return new Promise((resolve, reject) => {
    http.get(urlStr, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(body) });
        } catch (e) {
          resolve({ status: res.statusCode, raw: body });
        }
      });
    }).on('error', reject);
  });
}

async function runTests() {
  console.log("================================================================================");
  console.log(" PADDY FARMING ASSISTANT — FRONTEND GPS PRIVACY VERIFICATION SUITE");
  console.log("================================================================================");

  // ---------------------------------------------------------------------------
  // 1. STATIC CODE AUDIT FOR RAW COORDINATES IN UI TEMPLATES
  // ---------------------------------------------------------------------------
  console.log("\n--- [AUDIT 1] Inspecting Frontend Files for GPS Coordinate Exposure ---");

  const filesToCheck = [
    INDEX_HTML,
    path.join(SRC_DIR, 'market.js'),
    path.join(SRC_DIR, 'data.js'),
    path.join(SRC_DIR, 'reports.js'),
    path.join(SRC_DIR, 'home.js'),
    path.join(SRC_DIR, 'fieldHealth.js'),
    path.join(SRC_DIR, 'cropInsights.js'),
    path.join(SRC_DIR, 'diseaseDetection.js'),
    path.join(SRC_DIR, 'components', 'Dashboard.jsx'),
  ];

  for (const file of filesToCheck) {
    assert(fs.existsSync(file), `File exists: ${path.basename(file)}`);
    const content = fs.readFileSync(file, 'utf8');

    // 1. Ensure no raw coordinate interpolation in rendered HTML
    // E.g. ${buyer.latitude}, ${buyer.lat}, ${buyer.longitude}, ${buyer.lng}
    const hasRenderedLat = content.includes('${buyer.latitude}') || content.includes('${buyer.lat}');
    const hasRenderedLon = content.includes('${buyer.longitude}') || content.includes('${buyer.lng}');
    assert(!hasRenderedLat, `${path.basename(file)} does not render buyer latitude to DOM`);
    assert(!hasRenderedLon, `${path.basename(file)} does not render buyer longitude to DOM`);

    // 2. Ensure coordinate_source and verification metadata are not rendered in UI
    const hasRenderedCoordSrc = content.includes('${buyer.coordinate_source}') || content.includes('${buyer.source_reference}');
    assert(!hasRenderedCoordSrc, `${path.basename(file)} does not render coordinate_source in DOM`);

    // 3. Ensure no "GPS Coordinates" technical labels displayed in farmer UI
    if (file.endsWith('Dashboard.jsx')) {
      assert(!content.includes('GPS Coordinates'), `Dashboard.jsx omits "GPS Coordinates" technical label`);
      assert(content.includes('Farm Location'), `Dashboard.jsx uses user-friendly "Farm Location"`);
    }
  }

  // ---------------------------------------------------------------------------
  // 2. NEARBY BUYER EMPTY-STATE VERIFICATION
  // ---------------------------------------------------------------------------
  console.log("\n--- [AUDIT 2] Verifying Nearby Buyer Empty-State Notice ---");

  const indexHtmlContent = fs.readFileSync(INDEX_HTML, 'utf8');
  const marketJsContent = fs.readFileSync(path.join(SRC_DIR, 'market.js'), 'utf8');

  const EXPECTED_EMPTY_MSG = "Nearby buyer locations are not available yet. You can browse buyers by district.";
  assert(indexHtmlContent.includes(EXPECTED_EMPTY_MSG), `index.html contains exact empty notice: "${EXPECTED_EMPTY_MSG}"`);
  assert(marketJsContent.includes(EXPECTED_EMPTY_MSG), `market.js handles empty nearby search with exact notice: "${EXPECTED_EMPTY_MSG}"`);

  // Ensure district browsing fallback button exists
  assert(indexHtmlContent.includes('id="market-fallback-district-btn"'), `index.html has fallback button: market-fallback-district-btn`);
  assert(marketJsContent.includes('fallbackDistrictBtn.addEventListener'), `market.js binds event listener to fallback district button`);

  // ---------------------------------------------------------------------------
  // 3. DISTRICT FILTERING VERIFICATION
  // ---------------------------------------------------------------------------
  console.log("\n--- [AUDIT 3] Verifying District Filtering Implementation ---");

  assert(indexHtmlContent.includes('id="market-district-selector"'), `index.html has district selector: market-district-selector`);
  const districts = ['Kakinada', 'West Godavari', 'SPSR Nellore', 'Krishna', 'Guntur', 'Eluru', 'East Godavari', 'Nandyal'];
  for (const d of districts) {
    assert(indexHtmlContent.includes(`<option value="${d}">${d}</option>`), `index.html district selector includes option: ${d}`);
  }

  assert(marketJsContent.includes('districtMatches = ('), `market.js implements district filtering predicate`);
  assert(marketJsContent.includes('selectedDistrict = e.target.value.trim()'), `market.js listens for district selection changes`);

  // ---------------------------------------------------------------------------
  // 4. BROWSER LOCATION PERMISSION FLOW AUDIT
  // ---------------------------------------------------------------------------
  console.log("\n--- [AUDIT 4] Verifying Permission-Based Geolocation Flow ---");

  // Geolocation must NOT be called on load
  const hasAutoGeolocation = marketJsContent.includes('navigator.geolocation.getCurrentPosition(') && !marketJsContent.includes('btnNearby.addEventListener');
  assert(!hasAutoGeolocation, `market.js does NOT silently collect location on page load`);

  // Geolocation is wrapped in user click
  assert(marketJsContent.includes('btnNearby.addEventListener(\'click\''), `market.js requests location ONLY upon clicking "Find Nearest Buyers"`);
  assert(marketJsContent.includes('Location access was denied or is unavailable. You can browse buyers by district.'), `market.js handles denied location permission gracefully with friendly message`);

  // ---------------------------------------------------------------------------
  // 5. LIVE BACKEND ENDPOINT INTEGRATION AND DATA PRIVACY
  // ---------------------------------------------------------------------------
  console.log("\n--- [API INTEGRATION] Testing Live Backend Responses & Field Sanitation ---");

  try {
    const healthRes = await httpGet('http://127.0.0.1:8000/health');
    assert(healthRes.status === 200, `Backend is running on port 8000: ${JSON.stringify(healthRes.data)}`);

    // Test GET /buyers
    const buyersRes = await httpGet('http://127.0.0.1:8000/buyers?limit=100');
    assert(buyersRes.status === 200, `GET /buyers returns 200 OK`);
    assert(buyersRes.data.total === 17, `GET /buyers returns exactly 17 authentic buyers (got ${buyersRes.data.total})`);

    // Verify district filtering directly against API
    const kakinadaRes = await httpGet('http://127.0.0.1:8000/buyers?district=Kakinada');
    assert(kakinadaRes.status === 200 && kakinadaRes.data.total === 3, `GET /buyers?district=Kakinada returns 3 buyers`);

    const nelloreRes = await httpGet('http://127.0.0.1:8000/buyers?district=SPSR%20Nellore');
    assert(nelloreRes.status === 200 && nelloreRes.data.total === 4, `GET /buyers?district=SPSR Nellore returns 4 buyers`);

    // Test GET /buyers/nearby
    const nearbyRes = await httpGet('http://127.0.0.1:8000/buyers/nearby?lat=16.5062&lon=80.6480');
    assert(nearbyRes.status === 200, `GET /buyers/nearby returns 200 OK`);
    assert(nearbyRes.data.total === 0, `GET /buyers/nearby correctly returns 0 buyers when coordinates are unlocated`);
    assert(Array.isArray(nearbyRes.data.items) && nearbyRes.data.items.length === 0, `GET /buyers/nearby items array is empty`);

    // Test Market prices endpoint
    const pricesRes = await httpGet('http://127.0.0.1:8000/market/prices?limit=5');
    assert(pricesRes.status === 200 && pricesRes.data.total === 100, `GET /market/prices returns 200 OK with 100 prices`);
  } catch (err) {
    console.error("  [ERROR] Backend connection failed:", err.message);
    throw err;
  }

  // ---------------------------------------------------------------------------
  // 6. BUYER CARD RENDERING CONTENT INTEGRITY
  // ---------------------------------------------------------------------------
  console.log("\n--- [AUDIT 6] Verifying Buyer Card Attributes in market.js ---");

  assert(marketJsContent.includes('buyer.business_name || buyer.name'), `Card renders enterprise business name`);
  assert(marketJsContent.includes('formatBuyerType(buyer.buyer_type)'), `Card renders friendly formatted buyer type`);
  assert(marketJsContent.includes('buyer.address_summary'), `Card renders address summary when available`);
  assert(marketJsContent.includes('isVerified'), `Card renders verification badge`);
  assert(marketJsContent.includes('km away'), `Card renders friendly distance when available`);
  assert(marketJsContent.includes('buyer.price'), `Card renders price or MSP rate`);

  // Map safety
  assert(marketJsContent.includes('mapContainer.classList.add(\'hidden\')'), `Map is safely hidden when no buyers have coordinates`);
  assert(marketJsContent.includes('mapEmptyNotice.classList.remove(\'hidden\')'), `Friendly map unavailable notice is shown when coordinates are pending`);

  console.log("\n================================================================================");
  console.log(` ALL ${passedTests}/${totalTests} TESTS PASSED SUCCESSFULLY!`);
  console.log(" ZERO RAW GPS COORDINATES EXPOSED IN FARMER-FACING FRONTEND");
  console.log("================================================================================");
}

runTests().catch(err => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
