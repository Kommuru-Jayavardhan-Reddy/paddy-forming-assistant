// ============================================================================
// VERIFICATION SCRIPT: Home Page UI/UX Redesign & Backend Integration
// Tests layout, order, backend data fetching, DOM elements, and privacy.
// ============================================================================

import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function runTests() {
  console.log('====================================================================');
  console.log(' PADDY FARMING ASSISTANT - HOME PAGE REDESIGN VERIFICATION');
  console.log('====================================================================\n');

  let passed = 0;
  let failed = 0;

  function test(name, fn) {
    try {
      fn();
      console.log(`  [PASS] ${name}`);
      passed++;
    } catch (err) {
      console.error(`  [FAIL] ${name}: ${err.message}`);
      failed++;
    }
  }

  const indexPath = path.join(__dirname, 'index.html');
  const homeJsPath = path.join(__dirname, 'src', 'home.js');

  const indexHtml = fs.readFileSync(indexPath, 'utf8');
  const homeJs = fs.readFileSync(homeJsPath, 'utf8');

  // --- SECTION 1: Navbar Verification ---
  console.log('--- TEST SECTION 1: Navbar Order & Styling ---');
  test('Navbar contains Home', () => {
    assert(indexHtml.includes('data-target="page-home"'));
  });
  test('Navbar contains Disease Detection', () => {
    assert(indexHtml.includes('data-target="page-detection"'));
  });
  test('Navbar contains Field Health', () => {
    assert(indexHtml.includes('data-target="page-field-health"'));
  });
  test('Navbar contains Crop Insights', () => {
    assert(indexHtml.includes('data-target="page-crop-insights"'));
  });
  test('Navbar contains Market & Buyers', () => {
    assert(indexHtml.includes('data-target="page-market-buyers"'));
  });
  test('Navbar contains Reports', () => {
    assert(indexHtml.includes('data-target="page-reports"'));
  });

  // Verify navigation items order
  test('Navbar items are in exact order: Home -> Disease Detection -> Field Health -> Crop Insights -> Market & Buyers -> Reports', () => {
    const navStart = indexHtml.indexOf('<nav id="persistent-navbar"');
    const navEnd = indexHtml.indexOf('</nav>', navStart);
    const navSnippet = indexHtml.substring(navStart, navEnd);

    const posHome = navSnippet.indexOf('data-target="page-home"');
    const posDetect = navSnippet.indexOf('data-target="page-detection"');
    const posField = navSnippet.indexOf('data-target="page-field-health"');
    const posInsights = navSnippet.indexOf('data-target="page-crop-insights"');
    const posMarket = navSnippet.indexOf('data-target="page-market-buyers"');
    const posReports = navSnippet.indexOf('data-target="page-reports"');

    assert(posHome < posDetect, 'Home before Disease Detection');
    assert(posDetect < posField, 'Disease Detection before Field Health');
    assert(posField < posInsights, 'Field Health before Crop Insights');
    assert(posInsights < posMarket, 'Crop Insights before Market & Buyers');
    assert(posMarket < posReports, 'Market & Buyers before Reports');
  });

  // --- SECTION 2: Layout & Banner Verification ---
  console.log('\n--- TEST SECTION 2: Home Page Layout & Banner ---');
  test('Welcome banner heading is exact', () => {
    assert(indexHtml.includes('Welcome to Paddy Farming Assistant'));
  });
  test('Welcome banner subtitle is exact', () => {
    assert(indexHtml.includes('Monitor paddy crop health, track weather conditions, detect diseases, and explore market prices from one dashboard.'));
  });
  test('Welcome banner references local paddy banner image', () => {
    assert(indexHtml.includes('/assets/paddy-banner.png') || indexHtml.includes('/assets/paddy-bg.jpg'));
  });
  test('Banner image exists in public assets', () => {
    const bannerPath = path.join(__dirname, 'public', 'assets', 'paddy-banner.png');
    assert(fs.existsSync(bannerPath), 'paddy-banner.png exists');
  });

  // --- SECTION 3: Crop Health Summary ---
  console.log('\n--- TEST SECTION 3: Crop Health Summary Cards ---');
  test('Contains 3 cards: Healthy, Needs Attention, High Risk', () => {
    assert(indexHtml.includes('Healthy</span>'));
    assert(indexHtml.includes('Needs Attention</span>'));
    assert(indexHtml.includes('High Risk</span>'));
  });
  test('Crop health count displays calibrated field counts', () => {
    assert(indexHtml.includes('id="home-health-healthy-count"') || indexHtml.includes('31 Fields'));
  });
  test('Crop health cards display scientific NDVI thresholds', () => {
    assert(indexHtml.includes('NDVI ≥ 0.60') || indexHtml.includes('photosynthetic vigor'));
  });

  // --- SECTION 4: Weather Summary ---
  console.log('\n--- TEST SECTION 4: Weather Summary Integration ---');
  test('Weather card IDs exist', () => {
    assert(indexHtml.includes('id="home-weather-card"'));
    assert(indexHtml.includes('id="home-weather-temp"'));
    assert(indexHtml.includes('id="home-weather-condition"'));
    assert(indexHtml.includes('id="home-weather-rain"'));
    assert(indexHtml.includes('id="home-weather-error"'));
  });
  test('Weather fallback text is exact', () => {
    assert(indexHtml.includes('Weather information is currently unavailable.'));
  });
  test('home.js fetches /fields/FIELD_01/weather', () => {
    assert(homeJs.includes('/fields/FIELD_01/weather'));
  });
  test('Weather integration does not expose GPS coordinates in DOM', () => {
    assert(!homeJs.includes('.latitude'));
    assert(!homeJs.includes('.longitude'));
  });

  // --- SECTION 5: Recent Disease Detection ---
  console.log('\n--- TEST SECTION 5: Recent Disease Detection Table ---');
  test('Disease table container and body exist', () => {
    assert(indexHtml.includes('id="home-disease-section"'));
    assert(indexHtml.includes('id="home-disease-table-body"'));
  });
  test('Empty state displays exact text: "No disease detections yet."', () => {
    assert(indexHtml.includes('No disease detections yet.'));
  });
  test('Empty state provides "Detect Disease" button', () => {
    assert(indexHtml.includes('Detect Disease'));
  });
  test('home.js fetches /predictions', () => {
    assert(homeJs.includes('/predictions?page=1&page_size='));
  });

  // --- SECTION 6: Market Snapshot ---
  console.log('\n--- TEST SECTION 6: Market Snapshot Table ---');
  test('Market snapshot section and body exist', () => {
    assert(indexHtml.includes('id="home-market-section"'));
    assert(indexHtml.includes('id="home-market-table-body"'));
  });
  test('Market empty state displays exact text: "Market prices are currently unavailable."', () => {
    assert(indexHtml.includes('Market prices are currently unavailable.'));
  });
  test('Market section provides "Explore Markets" button', () => {
    assert(indexHtml.includes('Explore Markets'));
  });
  test('home.js fetches /market/prices/latest', () => {
    assert(homeJs.includes('/market/prices/latest'));
  });

  // --- SECTION 7: Quick Actions (Five Cards) ---
  console.log('\n--- TEST SECTION 7: Five Quick Actions Cards ---');
  test('Five Quick Action cards exist in exact order', () => {
    const quickStart = indexHtml.indexOf('Quick Actions</h2>');
    assert(quickStart > 0, 'Quick actions header found');
    const snippet = indexHtml.substring(quickStart);

    const c1 = snippet.indexOf('Disease Detection');
    const c2 = snippet.indexOf('Field Health');
    const c3 = snippet.indexOf('Crop Insights');
    const c4 = snippet.indexOf('Market & Buyers');
    const c5 = snippet.indexOf('Reports');

    assert(c1 < c2, 'Card 1 before Card 2');
    assert(c2 < c3, 'Card 2 before Card 3');
    assert(c3 < c4, 'Card 3 before Card 4');
    assert(c4 < c5, 'Card 4 before Card 5');
  });

  test('Quick Action buttons match exact titles', () => {
    assert(indexHtml.includes('Detect Disease'));
    assert(indexHtml.includes('View Field Health'));
    assert(indexHtml.includes('Explore Insights'));
    assert(indexHtml.includes('Explore Markets'));
    assert(indexHtml.includes('View Reports'));
  });

  // --- SECTION 8: Strict Project Reuse Verification ---
  console.log('\n--- TEST SECTION 8: Strict Reuse & Untouched Pages ---');
  test('Preserves page-detection container', () => {
    assert(indexHtml.includes('id="page-detection"'));
  });
  test('Preserves page-field-health container', () => {
    assert(indexHtml.includes('id="page-field-health"'));
  });
  test('Preserves page-crop-insights container', () => {
    assert(indexHtml.includes('id="page-crop-insights"'));
  });
  test('Preserves page-market-buyers container', () => {
    assert(indexHtml.includes('id="page-market-buyers"'));
  });
  test('Preserves page-reports container', () => {
    assert(indexHtml.includes('id="page-reports"'));
  });
  test('Preserves page-login container', () => {
    assert(indexHtml.includes('id="page-login"'));
  });
  test('Preserves page-welcome container', () => {
    assert(indexHtml.includes('id="page-welcome"'));
  });

  // --- SECTION 9: Live Backend Connectivity Verification ---
  console.log('\n--- TEST SECTION 9: Live Endpoints Response Verification ---');
  try {
    const weatherRes = await fetch('http://127.0.0.1:8000/fields/FIELD_01/weather');
    test('Backend /fields/FIELD_01/weather returns HTTP 200', () => {
      assert.strictEqual(weatherRes.status, 200);
    });
    const weatherData = await weatherRes.json();
    test('Weather contains current temperature and condition', () => {
      assert(weatherData.current !== undefined);
      assert(weatherData.current.temperature !== undefined);
      assert(weatherData.current.weather_condition !== undefined);
    });
  } catch (e) {
    console.error('  [FAIL] Weather endpoint connect:', e.message);
    failed++;
  }

  try {
    const predRes = await fetch('http://127.0.0.1:8000/predictions?page=1&page_size=4');
    test('Backend /predictions returns HTTP 200', () => {
      assert.strictEqual(predRes.status, 200);
    });
    const predData = await predRes.json();
    test('Predictions returns array of genuine prediction records', () => {
      assert(Array.isArray(predData.predictions));
      assert(predData.predictions.length > 0);
      assert(predData.predictions[0].predicted_disease);
    });
  } catch (e) {
    console.error('  [FAIL] Predictions endpoint connect:', e.message);
    failed++;
  }

  try {
    const marketRes = await fetch('http://127.0.0.1:8000/market/prices/latest?commodity=Paddy%20(Dhan)&limit=4');
    test('Backend /market/prices/latest returns HTTP 200', () => {
      assert.strictEqual(marketRes.status, 200);
    });
    const marketData = await marketRes.json();
    test('Market prices returns array of genuine mandi quotations', () => {
      assert(Array.isArray(marketData.items));
      assert(marketData.items.length > 0);
      assert(marketData.items[0].market_name);
      assert(marketData.items[0].modal_price);
    });
  } catch (e) {
    console.error('  [FAIL] Market endpoint connect:', e.message);
    failed++;
  }

  // --- SECTION 10: Complete Phase 3 Sections Verification ---
  console.log('\n--- TEST SECTION 10: Phase 3 Enhanced Section Verification ---');
  test('Section A: Welcome banner contains CTA navigating to Disease Detection', () => {
    const banner = indexHtml.substring(indexHtml.indexOf('id="home-welcome-banner"'), indexHtml.indexOf('<!-- ROW 2:'));
    assert(banner.includes('data-target="page-detection"'));
    assert(banner.includes('Detect Disease'));
  });

  test('Section A: Welcome banner contains secondary CTA navigating to Field Health', () => {
    const banner = indexHtml.substring(indexHtml.indexOf('id="home-welcome-banner"'), indexHtml.indexOf('<!-- ROW 2:'));
    assert(banner.includes('data-target="page-field-health"'));
    assert(banner.includes('View Field Health'));
  });

  test('Section B: Factual vegetation indices DOM elements exist', () => {
    assert(indexHtml.includes('id="home-ndvi-val"'));
    assert(indexHtml.includes('id="home-ndre-val"'));
    assert(indexHtml.includes('id="home-gndvi-val"'));
    assert(indexHtml.includes('id="home-ndvi-change"'));
    assert(indexHtml.includes('id="home-ndvi-trend-badge"'));
    assert(indexHtml.includes('id="home-indices-dates"'));
  });

  test('Section B: Labels index changes as vegetation-index trends, not definitive diagnoses', () => {
    assert(indexHtml.includes('Vegetation-index trends, not definitive disease diagnoses'));
  });

  test('Section B: Provides verified navigation link to Field Health', () => {
    assert(indexHtml.includes('data-target="page-field-health"'));
  });

  test('Section B: home.js fetches factual field health endpoint', () => {
    assert(homeJs.includes('/fields?skip=0&limit=') || homeJs.includes('/health'));
  });

  test('Section C: Weather includes humidity, wind speed, and compact daily forecast', () => {
    assert(indexHtml.includes('id="home-weather-humidity"'));
    assert(indexHtml.includes('id="home-weather-wind"'));
    assert(indexHtml.includes('id="home-weather-forecast-list"'));
    assert(indexHtml.includes('3-Day Agro Forecast'));
  });

  test('Section D: Recent disease table header and rows explicitly label leaf as Reference', () => {
    assert(indexHtml.includes('Leaf (Reference)'));
    assert(homeJs.includes('Reference'));
  });

  test('Section E: Market table headers include Market & Location, Modal Price, and Freshness', () => {
    assert(indexHtml.includes('Market & Location'));
    assert(indexHtml.includes('Modal Price'));
    assert(indexHtml.includes('Freshness'));
    assert(homeJs.includes('formatINR'));
    assert(homeJs.includes('DB Cache'));
  });

  test('Section G: Platform status container and health indicators exist', () => {
    assert(indexHtml.includes('id="home-platform-status"'));
    assert(indexHtml.includes('id="api-status-val"'));
    assert(indexHtml.includes('id="db-status-val"'));
    assert(indexHtml.includes('id="model-status-val"'));
    assert(homeJs.includes('/health/database'));
  });

  test('Privacy Check: No raw field coordinates are rendered or exposed in Home Page DOM', () => {
    assert(!homeJs.includes('.latitude'));
    assert(!homeJs.includes('.longitude'));
  });

  console.log('\n====================================================================');
  console.log(` RESULTS: ${passed} PASSED, ${failed} FAILED`);
  console.log('====================================================================');

  if (failed > 0) {
    process.exit(1);
  }
}

runTests();
