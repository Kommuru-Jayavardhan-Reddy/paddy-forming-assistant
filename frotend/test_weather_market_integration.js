/**
 * STEP 11J.5 — Weather and Market Frontend Integration Verification Suite
 * Tests the connection between the frontend Weather/Market/Buyer modules and FastAPI backend:
 * - Types and client functions (Weather, Mandi Prices, Market Analytics, Buyer Directory)
 * - Real /weather/current, /weather/forecast, and /fields/{field_id}/weather endpoints
 * - Real /market/prices, /market/prices/latest, /market/analytics/summary, /trends, /districts, /varieties
 * - Real /buyers, /buyers/{id}, and /buyers/nearby endpoints and filtering
 * - Edge case handling (404 for unknown field/buyer, 422 for invalid forecast days)
 * - Coordinate privacy and server path protection
 * - Database cleanup of test-created weather records (restoring strictly to baseline)
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
        timeout: options.timeout || 15000,
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
              } catch {
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
  console.log('STEP 11J.5 — Weather and Market Frontend Integration Verification');
  console.log('Backend Target: ', BACKEND_BASE);
  console.log('Frontend Target:', FRONTEND_BASE);
  console.log('======================================================================\n');

  // -------------------------------------------------------------------------
  // SECTION 1: TypeScript Contracts & Client Implementations
  // -------------------------------------------------------------------------
  console.log('--- TEST SECTION 1: TypeScript Contracts & Client Functions ---');

  const typesPath = path.join(__dirname, 'src', 'api', 'types.ts');
  const clientPath = path.join(__dirname, 'src', 'api', 'client.ts');
  const weatherMarketJsxPath = path.join(__dirname, 'src', 'components', 'WeatherMarket.jsx');
  const dashboardJsxPath = path.join(__dirname, 'src', 'components', 'Dashboard.jsx');
  const marketJsPath = path.join(__dirname, 'src', 'market.js');
  const homeJsPath = path.join(__dirname, 'src', 'home.js');

  assert(fs.existsSync(typesPath), 'src/api/types.ts exists');
  assert(fs.existsSync(clientPath), 'src/api/client.ts exists');
  assert(fs.existsSync(weatherMarketJsxPath), 'src/components/WeatherMarket.jsx exists');
  assert(fs.existsSync(dashboardJsxPath), 'src/components/Dashboard.jsx exists');
  assert(fs.existsSync(marketJsPath), 'src/market.js exists');
  assert(fs.existsSync(homeJsPath), 'src/home.js exists');

  const typesCode = fs.readFileSync(typesPath, 'utf-8');
  assert(typesCode.includes('export interface CurrentWeatherResponse'), 'types.ts exports CurrentWeatherResponse');
  assert(typesCode.includes('export interface WeatherForecastResponse'), 'types.ts exports WeatherForecastResponse');
  assert(typesCode.includes('export interface FieldWeatherResponse'), 'types.ts exports FieldWeatherResponse');
  assert(typesCode.includes('export interface MarketPriceListResponse'), 'types.ts exports MarketPriceListResponse');
  assert(typesCode.includes('export interface MarketSummaryResponse'), 'types.ts exports MarketSummaryResponse');
  assert(typesCode.includes('export interface MarketTrendsResponse'), 'types.ts exports MarketTrendsResponse');
  assert(typesCode.includes('export interface DistrictAnalyticsResponse'), 'types.ts exports DistrictAnalyticsResponse');
  assert(typesCode.includes('export interface VarietyAnalyticsResponse'), 'types.ts exports VarietyAnalyticsResponse');
  assert(typesCode.includes('export interface BuyerListResponse'), 'types.ts exports BuyerListResponse');
  assert(typesCode.includes('export interface BuyerNearbyResponse'), 'types.ts exports BuyerNearbyResponse');

  const clientCode = fs.readFileSync(clientPath, 'utf-8');
  assert(clientCode.includes('export const getCurrentWeather'), 'client.ts exports getCurrentWeather()');
  assert(clientCode.includes('export const getWeatherForecast'), 'client.ts exports getWeatherForecast()');
  assert(clientCode.includes('export const getFieldWeather'), 'client.ts exports getFieldWeather()');
  assert(clientCode.includes('export const getMarketPrices'), 'client.ts exports getMarketPrices()');
  assert(clientCode.includes('export const getLatestMarketPrices'), 'client.ts exports getLatestMarketPrices()');
  assert(clientCode.includes('export const getMarketSummary'), 'client.ts exports getMarketSummary()');
  assert(clientCode.includes('export const getMarketTrends'), 'client.ts exports getMarketTrends()');
  assert(clientCode.includes('export const getDistrictAnalytics'), 'client.ts exports getDistrictAnalytics()');
  assert(clientCode.includes('export const getVarietyAnalytics'), 'client.ts exports getVarietyAnalytics()');
  assert(clientCode.includes('export const getBuyers'), 'client.ts exports getBuyers()');
  assert(clientCode.includes('export const getBuyerById'), 'client.ts exports getBuyerById()');
  assert(clientCode.includes('export const getNearbyBuyers'), 'client.ts exports getNearbyBuyers()');

  const dashboardCode = fs.readFileSync(dashboardJsxPath, 'utf-8');
  assert(dashboardCode.includes('import WeatherMarket from \'./WeatherMarket\';'), 'Dashboard.jsx imports WeatherMarket');
  assert(dashboardCode.includes('<WeatherMarket />'), 'Dashboard.jsx mounts <WeatherMarket />');
  assert(dashboardCode.includes('<h3>Image Upload</h3>'), 'Dashboard preserves Image Upload card');
  assert(dashboardCode.includes('<h3>Farm Location</h3>'), 'Dashboard preserves Farm Location card');
  assert(dashboardCode.includes('<h3>Question Input</h3>'), 'Dashboard preserves Question Input card');
  assert(dashboardCode.includes('<h3>Disease Prediction</h3>'), 'Dashboard preserves Disease Prediction card');
  assert(dashboardCode.includes('<h3>Satellite Time-Series</h3>'), 'Dashboard preserves Satellite Time-Series card');
  assert(dashboardCode.includes('<h3>Generation Report</h3>'), 'Dashboard preserves Generation Report card');

  // -------------------------------------------------------------------------
  // SECTION 2: Real FastAPI Weather Endpoints
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 2: Live Weather Endpoints ---');

  // 1. Current Weather
  const weatherCurrentRes = await httpFetch(
    `${BACKEND_BASE}/weather/current?latitude=10.787&longitude=79.1378&timezone=Asia/Kolkata`
  );
  assert(weatherCurrentRes.status === 200, 'GET /weather/current returns HTTP 200');
  const weatherCurrentData = await weatherCurrentRes.json();
  assert(weatherCurrentData && weatherCurrentData.provider, 'Current weather includes provider info');
  assert(weatherCurrentData.current && typeof weatherCurrentData.current.temperature === 'number',
    `Current temperature observation returned: ${weatherCurrentData.current?.temperature}°C`);
  assert(weatherCurrentData.units && weatherCurrentData.units.temperature, 'Current weather includes units schema');

  // 2. Weather Forecast (7-day)
  const weatherForecastRes = await httpFetch(
    `${BACKEND_BASE}/weather/forecast?latitude=10.787&longitude=79.1378&forecast_days=7&timezone=Asia/Kolkata`
  );
  assert(weatherForecastRes.status === 200, 'GET /weather/forecast returns HTTP 200');
  const weatherForecastData = await weatherForecastRes.json();
  assert(Array.isArray(weatherForecastData.daily_forecast), 'Daily forecast is an array');
  assert(weatherForecastData.daily_forecast.length === 7, `Daily forecast contains 7 days (actual: ${weatherForecastData.daily_forecast?.length})`);
  assert(weatherForecastData.daily_forecast[0].date && weatherForecastData.daily_forecast[0].temperature_max !== undefined,
    'Daily forecast contains valid date and temperature items');

  // 3. Field-specific Weather
  const fieldWeatherRes = await httpFetch(
    `${BACKEND_BASE}/fields/FIELD_01/weather?forecast_days=7`
  );
  assert(fieldWeatherRes.status === 200, 'GET /fields/FIELD_01/weather returns HTTP 200');
  const fieldWeatherData = await fieldWeatherRes.json();
  assert(fieldWeatherData.field_id === 'FIELD_01', 'Field weather field_id is FIELD_01');
  assert(fieldWeatherData.current && typeof fieldWeatherData.current.temperature === 'number',
    `Field current temperature returned: ${fieldWeatherData.current?.temperature}°C`);
  assert(fieldWeatherData.daily_forecast && fieldWeatherData.daily_forecast.length === 7,
    'Field weather includes 7-day daily forecast');

  // -------------------------------------------------------------------------
  // SECTION 3: Live Market Prices & Analytics Endpoints
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 3: Live Market Prices & Analytics ---');

  // 1. Mandi Prices List
  const marketPricesRes = await httpFetch(`${BACKEND_BASE}/market/prices?limit=10`);
  assert(marketPricesRes.status === 200, 'GET /market/prices returns HTTP 200');
  const marketPricesData = await marketPricesRes.json();
  assert(Array.isArray(marketPricesData.items), 'Market prices items is an array');
  assert(marketPricesData.total === 100, `Market prices total count matches 100 seeded records (actual: ${marketPricesData.total})`);
  const firstPrice = marketPricesData.items[0];
  const marketName = firstPrice?.market_name || firstPrice?.market;
  assert(firstPrice && firstPrice.commodity && marketName && firstPrice.modal_price,
    `Valid price record found: ${firstPrice?.commodity} - ${firstPrice?.variety} at ${marketName} (Rs ${firstPrice?.modal_price})`);

  // 2. Latest Prices
  const latestPricesRes = await httpFetch(`${BACKEND_BASE}/market/prices/latest?commodity=Paddy%20(Dhan)&limit=5`);
  assert(latestPricesRes.status === 200, 'GET /market/prices/latest returns HTTP 200');
  const latestPricesData = await latestPricesRes.json();
  assert(Array.isArray(latestPricesData.items) && latestPricesData.items.length > 0,
    `Latest prices returned ${latestPricesData.items?.length} items`);

  // 3. Market Summary
  const marketSummaryRes = await httpFetch(`${BACKEND_BASE}/market/analytics/summary?commodity=Paddy%20(Dhan)`);
  assert(marketSummaryRes.status === 200, 'GET /market/analytics/summary returns HTTP 200');
  const marketSummaryData = await marketSummaryRes.json();
  assert(marketSummaryData.has_data === true, 'Market summary has_data is true');
  assert(marketSummaryData.avg_modal_price > 0, `Average modal price calculated: Rs ${marketSummaryData.avg_modal_price}/quintal`);
  assert(marketSummaryData.distinct_markets > 0, `Distinct markets counted: ${marketSummaryData.distinct_markets}`);

  // 4. Market Trends
  const marketTrendsRes = await httpFetch(`${BACKEND_BASE}/market/analytics/trends?days=30`);
  assert(marketTrendsRes.status === 200, 'GET /market/analytics/trends returns HTTP 200');
  const marketTrendsData = await marketTrendsRes.json();
  assert(Array.isArray(marketTrendsData.daily_trends), 'Market trends daily_trends is an array');
  assert(marketTrendsData.trend_direction !== undefined, `Trend direction detected: ${marketTrendsData.trend_direction}`);

  // 5. District Analytics
  const districtAnalyticsRes = await httpFetch(`${BACKEND_BASE}/market/analytics/districts?days=30`);
  assert(districtAnalyticsRes.status === 200, 'GET /market/analytics/districts returns HTTP 200');
  const districtAnalyticsData = await districtAnalyticsRes.json();
  assert(Array.isArray(districtAnalyticsData.districts), 'District benchmarks is an array');
  const distCount = districtAnalyticsData.districts?.length || districtAnalyticsData.total_districts;
  assert(distCount > 0, `Total districts analyzed: ${distCount}`);

  // 6. Variety Analytics
  const varietyAnalyticsRes = await httpFetch(`${BACKEND_BASE}/market/analytics/varieties?days=30`);
  assert(varietyAnalyticsRes.status === 200, 'GET /market/analytics/varieties returns HTTP 200');
  const varietyAnalyticsData = await varietyAnalyticsRes.json();
  assert(Array.isArray(varietyAnalyticsData.varieties), 'Variety benchmarks is an array');
  const varCount = varietyAnalyticsData.varieties?.length || varietyAnalyticsData.total_varieties;
  assert(varCount > 0, `Total varieties analyzed: ${varCount}`);

  // -------------------------------------------------------------------------
  // SECTION 4: Live Buyers Endpoints & Filters
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 4: Live Buyers Endpoints & Filters ---');

  // 1. Buyers List
  const buyersRes = await httpFetch(`${BACKEND_BASE}/buyers?limit=50`);
  assert(buyersRes.status === 200, 'GET /buyers returns HTTP 200');
  const buyersData = await buyersRes.json();
  assert(Array.isArray(buyersData.items), 'Buyers items is an array');
  assert(buyersData.total === 17, `Buyers total count matches 17 seeded records (actual: ${buyersData.total})`);

  // 2. Buyer by ID
  const firstBuyerId = buyersData.items[0].id;
  const buyerByIdRes = await httpFetch(`${BACKEND_BASE}/buyers/${firstBuyerId}`);
  assert(buyerByIdRes.status === 200, `GET /buyers/${firstBuyerId} returns HTTP 200`);
  const buyerByIdData = await buyerByIdRes.json();
  assert(buyerByIdData.id === firstBuyerId, 'Retrieved buyer ID matches requested ID');
  assert(buyerByIdData.business_name, `Buyer business name: ${buyerByIdData.business_name}`);
  assert(buyerByIdData.district, `Buyer district: ${buyerByIdData.district}`);
  assert(buyerByIdData.verification_status, `Buyer verification status: ${buyerByIdData.verification_status}`);

  // 3. Buyer Filtering by District (Kakinada from seeded data)
  const districtFilterRes = await httpFetch(`${BACKEND_BASE}/buyers?district=Kakinada`);
  assert(districtFilterRes.status === 200, 'GET /buyers?district=Kakinada returns HTTP 200');
  const districtFilterData = await districtFilterRes.json();
  const allKakinada = districtFilterData.items.every(b => b.district === 'Kakinada');
  assert(allKakinada && districtFilterData.items.length > 0,
    `District filtering returned ${districtFilterData.items.length} Kakinada buyers`);

  // 4. Buyer Filtering by Buyer Type
  const typeFilterRes = await httpFetch(`${BACKEND_BASE}/buyers?buyer_type=mill`);
  assert(typeFilterRes.status === 200, 'GET /buyers?buyer_type=mill returns HTTP 200');
  const typeFilterData = await typeFilterRes.json();
  const allMills = typeFilterData.items.every(b => b.buyer_type === 'mill');
  assert(allMills && typeFilterData.items.length > 0,
    `Buyer type filtering returned ${typeFilterData.items.length} rice mill buyers`);

  // 5. Buyer Filtering by Verification Status
  const statusFilterRes = await httpFetch(`${BACKEND_BASE}/buyers?verification_status=verified`);
  assert(statusFilterRes.status === 200, 'GET /buyers?verification_status=verified returns HTTP 200');
  const statusFilterData = await statusFilterRes.json();
  const allVerified = statusFilterData.items.every(b => b.verification_status === 'verified');
  assert(allVerified && statusFilterData.items.length > 0,
    `Verification filtering returned ${statusFilterData.items.length} verified buyers`);

  // 6. Nearby Buyers Discovery (Graceful null handling when coordinates are null)
  const nearbyRes = await httpFetch(`${BACKEND_BASE}/buyers/nearby?lat=10.787&lon=79.1378&radius_km=50`);
  assert(nearbyRes.status === 200, 'GET /buyers/nearby returns HTTP 200');
  const nearbyData = await nearbyRes.json();
  assert(Array.isArray(nearbyData.items), 'Nearby buyers items is an array');
  assert(nearbyData.farmer_latitude === 10.787 && nearbyData.farmer_longitude === 79.1378,
    'Nearby response echoes farmer coordinates correctly');
  assert(nearbyData.total === 0, 'Total nearby buyers with coordinates is 0 (as expected for privacy-seeded records)');

  // -------------------------------------------------------------------------
  // SECTION 5: Edge Cases, Error Handling & Parameter Validation
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 5: Edge Cases & Error Handling ---');

  // 1. Invalid forecast days (> 7)
  const invalidForecastRes = await httpFetch(
    `${BACKEND_BASE}/weather/forecast?latitude=10.787&longitude=79.1378&forecast_days=14`
  );
  assert(invalidForecastRes.status === 400 || invalidForecastRes.status === 422,
    `GET /weather/forecast with forecast_days=14 returns client error (HTTP ${invalidForecastRes.status})`);

  // 2. Unknown Field Weather (404)
  const unknownFieldWeatherRes = await httpFetch(`${BACKEND_BASE}/fields/FIELD_UNKNOWN_999/weather`);
  assert(unknownFieldWeatherRes.status === 404, 'GET /fields/FIELD_UNKNOWN_999/weather returns HTTP 404');

  // 3. Unknown Buyer ID (404)
  const unknownBuyerRes = await httpFetch(`${BACKEND_BASE}/buyers/00000000-0000-0000-0000-000000000000`);
  assert(unknownBuyerRes.status === 404, 'GET /buyers/{nonexistent_uuid} returns HTTP 404');

  // 4. Invalid buyer UUID format (422)
  const invalidUuidRes = await httpFetch(`${BACKEND_BASE}/buyers/not-a-valid-uuid`);
  assert(invalidUuidRes.status === 422, 'GET /buyers/invalid-uuid returns HTTP 422');

  // -------------------------------------------------------------------------
  // SECTION 6: Security, Privacy & Confidentiality Checks
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 6: Security & Privacy Protection ---');

  const weatherMarketCode = fs.readFileSync(weatherMarketJsxPath, 'utf-8');
  assert(!weatherMarketCode.includes('latitude:') && !weatherMarketCode.includes('longitude:'),
    'WeatherMarket.jsx does not display raw latitude/longitude labels');
  assert(weatherMarketCode.includes('Nearby buyer locations are not available yet. You can browse buyers by district.'),
    'WeatherMarket.jsx contains user-friendly fallback text for nearby buyers');

  const marketJsCode = fs.readFileSync(marketJsPath, 'utf-8');
  assert(marketJsCode.includes('Nearby buyer locations are not available yet. You can browse buyers by district.'),
    'market.js contains friendly empty-state notice for nearby buyers');
  assert(!marketJsCode.includes('Raw GPS') && !marketJsCode.includes('latitude:'),
    'market.js preserves GPS privacy and hides raw coordinates');

  // -------------------------------------------------------------------------
  // SECTION 7: Test Cleanup of Weather Records & Database Row Count Audit
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 7: Database Cleanup & Row Count Audit ---');

  const pythonExe = path.join(ROOT_DIR, 'venv', 'Scripts', 'python.exe');
  const cleanupScript = path.join(ROOT_DIR, 'backend', 'cleanup_weather_test_records.py');

  try {
    const cleanOut = execSync(`"${pythonExe}" "${cleanupScript}"`, {
      cwd: path.join(ROOT_DIR, 'backend'),
      encoding: 'utf-8'
    });
    console.log(`  Cleaned up test-created weather records (${cleanOut.trim()}).`);
    recordTest('Test record cleanup', true);
  } catch (cleanErr) {
    recordTest('Test record cleanup', false, cleanErr.message);
  }

  // Now run check_db_integrity.py
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
      assert(counts.weather_records === 98, 'weather_records table count strictly restored to baseline (98)');
      assert(counts.reports === 4, 'reports table count unchanged (4)');
    } else {
      recordTest('Database count verification', false, 'Could not parse DB counts from python output');
    }
  } catch (dbErr) {
    recordTest('Database count verification', false, dbErr.message);
  }

  // -------------------------------------------------------------------------
  // SECTION 8: Frontend dev server and routes
  // -------------------------------------------------------------------------
  console.log('\n--- TEST SECTION 8: Frontend Dev Server & Navigation ---');
  const viteRes = await httpFetch(FRONTEND_BASE);
  assert(viteRes.status === 200, `Frontend Vite dev server is reachable at ${FRONTEND_BASE} (HTTP 200)`);

  const indexHtmlPath = path.join(__dirname, 'index.html');
  const indexHtml = fs.readFileSync(indexHtmlPath, 'utf-8');
  assert(indexHtml.includes('data-target="page-market-buyers"'), 'Market & Buyers navigation route preserved');
  assert(indexHtml.includes('data-target="page-home"'), 'Home navigation route preserved');
  assert(indexHtml.includes('data-target="page-crop-insights"'), 'Crop Insights navigation route preserved');

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
