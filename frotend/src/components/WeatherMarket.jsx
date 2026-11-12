import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  getFields,
  getFieldWeather,
  getMarketPrices,
  getLatestMarketPrices,
  getMarketSummary,
  getMarketTrends,
  getVarietyAnalytics,
  getBuyers,
  getNearbyBuyers
} from '../api/client';

const WMO_CODE_MAP = {
  0: 'Clear sky',
  1: 'Mainly clear',
  2: 'Partly cloudy',
  3: 'Overcast',
  45: 'Fog',
  48: 'Depositing rime fog',
  51: 'Light drizzle',
  53: 'Moderate drizzle',
  55: 'Dense drizzle',
  56: 'Light freezing drizzle',
  57: 'Dense freezing drizzle',
  61: 'Slight rain',
  63: 'Moderate rain',
  65: 'Heavy rain',
  66: 'Light freezing rain',
  67: 'Heavy freezing rain',
  71: 'Slight snow fall',
  73: 'Moderate snow fall',
  75: 'Heavy snow fall',
  77: 'Snow grains',
  80: 'Slight rain showers',
  81: 'Moderate rain showers',
  82: 'Violent rain showers',
  85: 'Slight snow showers',
  86: 'Heavy snow showers',
  95: 'Thunderstorm',
  96: 'Thunderstorm with slight hail',
  99: 'Thunderstorm with heavy hail'
};

const WeatherMarket = () => {
  const [activeTab, setActiveTab] = useState('weather'); // 'weather' | 'market' | 'buyers'

  // ---------------------------------------------------------------------------
  // STATE: Field Weather
  // ---------------------------------------------------------------------------
  const [fieldList, setFieldList] = useState([]);
  const [selectedFieldId, setSelectedFieldId] = useState('FIELD_01');
  const [weatherData, setWeatherData] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(true);
  const [weatherError, setWeatherError] = useState(null);

  // ---------------------------------------------------------------------------
  // STATE: Market Prices
  // ---------------------------------------------------------------------------
  const [marketSummary, setMarketSummary] = useState(null);
  const [latestPrices, setLatestPrices] = useState([]);
  const [varietyAnalytics, setVarietyAnalytics] = useState([]);
  const [marketTrends, setMarketTrends] = useState(null);
  const [selectedVariety, setSelectedVariety] = useState('All');
  const [marketLoading, setMarketLoading] = useState(true);
  const [marketError, setMarketError] = useState(null);

  // ---------------------------------------------------------------------------
  // STATE: Buyers Directory
  // ---------------------------------------------------------------------------
  const [buyers, setBuyers] = useState([]);
  const [buyerTypeFilter, setBuyerTypeFilter] = useState('all');
  const [buyerDistrictFilter, setBuyerDistrictFilter] = useState('all');
  const [buyerSearchQuery, setBuyerSearchQuery] = useState('');
  const [nearbyStatus, setNearbyStatus] = useState(null);
  const [nearbyNotice, setNearbyNotice] = useState(false);
  const [buyersLoading, setBuyersLoading] = useState(true);
  const [buyersError, setBuyersError] = useState(null);

  // ---------------------------------------------------------------------------
  // DATA LOADERS
  // ---------------------------------------------------------------------------

  // 1. Initial fields for weather selector
  useEffect(() => {
    let isMounted = true;
    getFields(0, 50)
      .then(res => {
        if (!isMounted) return;
        const list = res.fields || [];
        setFieldList(list);
        if (list.length > 0) {
          setSelectedFieldId(list[0].field_id);
        }
      })
      .catch(err => {
        console.warn('Could not load fields for weather selector:', err);
      });
    return () => { isMounted = false; };
  }, []);

  // 2. Load weather for selected field
  const loadWeather = useCallback(async (fieldId) => {
    setWeatherLoading(true);
    setWeatherError(null);
    try {
      const data = await getFieldWeather(fieldId, 7);
      setWeatherData(data);
    } catch (err) {
      console.error('Field weather fetch error:', err);
      setWeatherError(err instanceof Error ? err.message : 'Weather data temporarily unavailable.');
    } finally {
      setWeatherLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedFieldId) {
      loadWeather(selectedFieldId);
    }
  }, [selectedFieldId, loadWeather]);

  // 3. Load market prices & analytics
  const loadMarketData = useCallback(async () => {
    setMarketLoading(true);
    setMarketError(null);
    try {
      const [sumRes, latestRes, varRes, trendRes] = await Promise.all([
        getMarketSummary({ commodity: 'Paddy (Dhan)' }),
        getLatestMarketPrices({ commodity: 'Paddy (Dhan)', limit: 30 }),
        getVarietyAnalytics({ commodity: 'Paddy (Dhan)', days: 30 }).catch(() => ({ varieties: [] })),
        getMarketTrends({ days: 30 }).catch(() => null)
      ]);
      setMarketSummary(sumRes);
      setLatestPrices(latestRes.items || []);
      setVarietyAnalytics(varRes.varieties || []);
      setMarketTrends(trendRes);
    } catch (err) {
      console.error('Market data fetch error:', err);
      setMarketError(err instanceof Error ? err.message : 'Market prices temporarily unavailable.');
    } finally {
      setMarketLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMarketData();
  }, [loadMarketData]);

  // 4. Load buyers directory
  const loadBuyers = useCallback(async () => {
    setBuyersLoading(true);
    setBuyersError(null);
    try {
      const res = await getBuyers({ limit: 100 });
      setBuyers(res.items || []);
    } catch (err) {
      console.error('Buyers fetch error:', err);
      setBuyersError(err instanceof Error ? err.message : 'Buyers directory temporarily unavailable.');
    } finally {
      setBuyersLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBuyers();
  }, [loadBuyers]);

  // ---------------------------------------------------------------------------
  // NEARBY BUYERS DISCOVERY (Privacy-Safe)
  // ---------------------------------------------------------------------------
  const handleFindNearbyBuyers = () => {
    if (!navigator.geolocation) {
      setNearbyStatus('Geolocation is not supported by your browser.');
      setNearbyNotice(true);
      return;
    }

    setNearbyStatus('Requesting device location permission...');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        setNearbyStatus('Searching for nearby verified grain procurement centers...');
        try {
          const res = await getNearbyBuyers(pos.coords.latitude, pos.coords.longitude, 50);
          if (res.items && res.items.length > 0) {
            setBuyers(res.items);
            setNearbyStatus(`Found ${res.items.length} nearby procurement centers.`);
            setNearbyNotice(false);
          } else {
            setNearbyNotice(true);
            setNearbyStatus('Nearby buyer locations are not available yet. Showing all district buyers.');
          }
        } catch {
          setNearbyNotice(true);
          setNearbyStatus('Nearby buyer locations are not available yet. You can browse buyers by district.');
        }
      },
      () => {
        setNearbyNotice(true);
        setNearbyStatus('Location access denied. You can browse buyers by district below.');
      },
      { timeout: 8000 }
    );
  };

  // ---------------------------------------------------------------------------
  // FILTERED LISTS
  // ---------------------------------------------------------------------------
  const filteredPrices = useMemo(() => {
    if (selectedVariety === 'All') return latestPrices;
    return latestPrices.filter(p => p.variety.toLowerCase().includes(selectedVariety.toLowerCase()));
  }, [latestPrices, selectedVariety]);

  const distinctDistricts = useMemo(() => {
    const set = new Set();
    buyers.forEach(b => { if (b.district) set.add(b.district); });
    return Array.from(set).sort();
  }, [buyers]);

  const filteredBuyers = useMemo(() => {
    return buyers.filter(b => {
      if (buyerTypeFilter !== 'all' && b.buyer_type !== buyerTypeFilter) return false;
      if (buyerDistrictFilter !== 'all' && b.district !== buyerDistrictFilter) return false;
      if (buyerSearchQuery) {
        const q = buyerSearchQuery.toLowerCase();
        const name = (b.business_name || '').toLowerCase();
        const dist = (b.district || '').toLowerCase();
        const vars = Array.isArray(b.preferred_varieties) ? b.preferred_varieties.join(' ').toLowerCase() : '';
        if (!name.includes(q) && !dist.includes(q) && !vars.includes(q)) return false;
      }
      return true;
    });
  }, [buyers, buyerTypeFilter, buyerDistrictFilter, buyerSearchQuery]);

  return (
    <section 
      aria-label="Weather, Market Prices, and Buyers Directory"
      style={{
        marginTop: '2rem',
        marginBottom: '2rem',
        backgroundColor: '#ffffff',
        borderRadius: '16px',
        border: '1px solid #e0e0e0',
        padding: '1.75rem',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.05)'
      }}
    >
      {/* Header & Tabs */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <span style={{ fontSize: '1.5rem' }}>🌦️</span>
            <h3 style={{ margin: 0, fontSize: '1.35rem', color: '#0d5c38', fontWeight: 700 }}>
              Meteorology & Market Intelligence
            </h3>
          </div>
          <p style={{ margin: 0, fontSize: '0.875rem', color: '#666' }}>
            Open-Meteo agro-weather forecasts, live APMC mandi commodity prices, and verified grain buyers
          </p>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', gap: '0.5rem', background: '#f5f5f5', padding: '0.25rem', borderRadius: '8px' }}>
          {[
            { id: 'weather', label: '🌤️ Field Weather & Forecast' },
            { id: 'market', label: '📈 Mandi Prices & Analytics' },
            { id: 'buyers', label: '🏢 Verified Grain Buyers' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '0.45rem 0.9rem',
                fontSize: '0.825rem',
                fontWeight: activeTab === tab.id ? 600 : 500,
                color: activeTab === tab.id ? '#0d5c38' : '#666',
                background: activeTab === tab.id ? '#ffffff' : 'transparent',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                boxShadow: activeTab === tab.id ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                transition: 'all 0.2s ease'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* =================================================================== */}
      {/* TAB 1: FIELD WEATHER & AGRO-METEOROLOGY                             */}
      {/* =================================================================== */}
      {activeTab === 'weather' && (
        <div>
          {/* Field Selection Toolbar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <label htmlFor="weather-field-select" style={{ fontSize: '0.85rem', fontWeight: 600, color: '#333' }}>
                Select Paddy Field:
              </label>
              <select
                id="weather-field-select"
                value={selectedFieldId}
                onChange={(e) => setSelectedFieldId(e.target.value)}
                style={{
                  padding: '0.4rem 0.75rem',
                  borderRadius: '6px',
                  border: '1px solid #0d5c38',
                  backgroundColor: '#fff',
                  fontSize: '0.85rem',
                  color: '#0d5c38',
                  fontWeight: 600
                }}
              >
                {fieldList.map(f => (
                  <option key={f.field_id} value={f.field_id}>
                    {f.field_id} — {f.field_name}
                  </option>
                ))}
              </select>
            </div>

            {weatherData?.current?.time && (
              <span style={{ fontSize: '0.75rem', color: '#777' }}>
                Observed: {weatherData.current.time.replace('T', ' ')} (Provider: {weatherData.provider})
              </span>
            )}
          </div>

          {weatherError && (
            <div style={{ backgroundColor: '#ffebee', color: '#c62828', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' }}>
              <strong>Weather Notice:</strong> {weatherError}
              <button onClick={() => loadWeather(selectedFieldId)} style={{ marginLeft: '1rem', padding: '0.25rem 0.5rem', background: '#d32f2f', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Retry</button>
            </div>
          )}

          {weatherLoading && (
            <div style={{ textAlign: 'center', padding: '2.5rem', color: '#0d5c38' }}>
              ⏳ Loading real-time atmospheric measurements from Open-Meteo...
            </div>
          )}

          {!weatherLoading && weatherData && weatherData.current && (
            <div>
              {/* Current Weather KPI Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '10px', border: '1px solid #e2ece6' }}>
                  <span style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Temperature</span>
                  <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#0d5c38', marginTop: '0.25rem' }}>
                    {weatherData.current.temperature !== null ? `${weatherData.current.temperature}°C` : '--'}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>
                    Condition: {weatherData.current.weather_condition || (weatherData.current.weather_code !== null && weatherData.current.weather_code !== undefined && WMO_CODE_MAP[weatherData.current.weather_code] ? WMO_CODE_MAP[weatherData.current.weather_code] : 'Unavailable')}
                  </span>
                </div>

                <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '10px', border: '1px solid #e2ece6' }}>
                  <span style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Relative Humidity</span>
                  <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#0288d1', marginTop: '0.25rem' }}>
                    {weatherData.current.relative_humidity !== null ? `${weatherData.current.relative_humidity}%` : '--'}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Canopy moisture index</span>
                </div>

                <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '10px', border: '1px solid #e2ece6' }}>
                  <span style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Precipitation</span>
                  <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#5c6bc0', marginTop: '0.25rem' }}>
                    {weatherData.current.precipitation !== null && weatherData.current.precipitation !== undefined ? `${weatherData.current.precipitation} mm` : '-- mm'}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Current liquid rain</span>
                </div>

                <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '10px', border: '1px solid #e2ece6' }}>
                  <span style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Wind Speed</span>
                  <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#795548', marginTop: '0.25rem' }}>
                    {weatherData.current.wind_speed !== null ? `${weatherData.current.wind_speed} km/h` : '--'}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>At 10m altitude</span>
                </div>
              </div>

              {/* 7-Day Multi-Day Daily Forecast */}
              <div style={{ backgroundColor: '#fafbfc', border: '1px solid #e5e9ec', borderRadius: '12px', padding: '1.25rem', marginBottom: '1rem' }}>
                <h4 style={{ margin: '0 0 1rem 0', fontSize: '0.95rem', color: '#0d5c38', fontWeight: 600 }}>
                  7-Day Agro-Meteorological Daily Forecast
                </h4>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem' }}>
                  {weatherData.daily_forecast.map((day) => {
                    const isRainy = (day.precipitation_sum || 0) > 5;
                    const dayCond = day.weather_condition || (day.weather_code !== null && day.weather_code !== undefined && WMO_CODE_MAP[day.weather_code] ? WMO_CODE_MAP[day.weather_code] : 'Unavailable');
                    const dayRain = day.precipitation_sum !== null && day.precipitation_sum !== undefined ? `${day.precipitation_sum}mm` : '--';
                    return (
                      <div key={day.date} style={{ background: '#ffffff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '0.85rem', textAlign: 'center' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#555', display: 'block' }}>
                          {day.date.slice(5)}
                        </span>
                        <div style={{ fontSize: '1.2rem', margin: '0.35rem 0' }}>
                          {isRainy ? '🌧️' : '⛅'}
                        </div>
                        <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0d5c38' }}>
                          {day.temperature_max}° / {day.temperature_min}°C
                        </div>
                        <span style={{ fontSize: '0.7rem', color: '#666', display: 'block', marginTop: '0.25rem' }}>
                          Rain: {dayRain}
                        </span>
                        <span style={{ fontSize: '0.65rem', color: '#888', display: 'block' }}>
                          {dayCond}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Agricultural Spraying & Decision Advisory */}
              <div style={{ backgroundColor: '#e8f5e9', border: '1px solid #c8e6c9', borderRadius: '10px', padding: '1rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#2e7d32' }}>
                  💡 Agro-Meteorological Spraying Guidance:
                </span>
                <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.8rem', color: '#1b5e20', lineHeight: 1.5 }}>
                  {weatherData.current.precipitation > 0 || (weatherData.daily_forecast[0]?.precipitation_sum || 0) > 10
                    ? 'Avoid applying foliar bactericides or systemic fungicides today due to imminent precipitation wash-off risks.'
                    : 'Favorable spraying window: Current wind speeds and low precipitation support efficient foliar spraying in the early morning.'}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 2: MANDI PRICES & MARKET ANALYTICS                              */}
      {/* =================================================================== */}
      {activeTab === 'market' && (
        <div>
          {/* Summary KPI Cards */}
          {marketSummary && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
              <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '10px', border: '1px solid #e2ece6' }}>
                <span style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>State Modal Average</span>
                <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#0d5c38', marginTop: '0.25rem' }}>
                  ₹{Math.round(marketSummary.avg_modal_price || 0).toLocaleString()}
                </div>
                <span style={{ fontSize: '0.75rem', color: '#888' }}>per quintal (Paddy Dhan)</span>
              </div>

              <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '10px', border: '1px solid #e2ece6' }}>
                <span style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Price Range</span>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#2c3e50', marginTop: '0.25rem' }}>
                  ₹{marketSummary.min_modal_price} - ₹{marketSummary.max_modal_price}
                </div>
                <span style={{ fontSize: '0.75rem', color: '#888' }}>min / max modal quote</span>
              </div>

              <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '10px', border: '1px solid #e2ece6' }}>
                <span style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Total Quotations</span>
                <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#0288d1', marginTop: '0.25rem' }}>
                  {marketSummary.total_observations}
                </div>
                <span style={{ fontSize: '0.75rem', color: '#888' }}>across {marketSummary.distinct_districts} AP districts</span>
              </div>

              <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '10px', border: '1px solid #e2ece6' }}>
                <span style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Active Mandis</span>
                <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#795548', marginTop: '0.25rem' }}>
                  {marketSummary.distinct_markets}
                </div>
                <span style={{ fontSize: '0.75rem', color: '#888' }}>latest: {marketSummary.latest_price_date || 'Oct 2026'}</span>
              </div>
            </div>
          )}

          {/* Variety Filter Toolbar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#333' }}>Filter by Variety:</span>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {['All', 'Common', 'BPT 5204', 'Swarna', 'Samba Masuri'].map(v => (
                <button
                  key={v}
                  onClick={() => setSelectedVariety(v)}
                  style={{
                    padding: '0.3rem 0.75rem',
                    borderRadius: '16px',
                    fontSize: '0.75rem',
                    fontWeight: selectedVariety === v ? 700 : 500,
                    color: selectedVariety === v ? '#fff' : '#444',
                    background: selectedVariety === v ? '#0d5c38' : '#f0f0f0',
                    border: 'none',
                    cursor: 'pointer'
                  }}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>

          {/* Latest Mandi Quotations Feed */}
          <div style={{ backgroundColor: '#ffffff', border: '1px solid #e0e0e0', borderRadius: '12px', overflow: 'hidden', marginBottom: '1.5rem' }}>
            <div style={{ padding: '0.85rem 1.25rem', backgroundColor: '#fafafa', borderBottom: '1px solid #e0e0e0', fontWeight: 600, fontSize: '0.85rem', color: '#333' }}>
              Latest APMC Mandi Spot Prices (Andhra Pradesh)
            </div>
            <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f5f5f5', color: '#555' }}>
                    <th style={{ padding: '0.6rem 1rem' }}>Mandi Market</th>
                    <th style={{ padding: '0.6rem 1rem' }}>District</th>
                    <th style={{ padding: '0.6rem 1rem' }}>Variety</th>
                    <th style={{ padding: '0.6rem 1rem' }}>Arrival Date</th>
                    <th style={{ padding: '0.6rem 1rem', textAlign: 'right' }}>Modal Price</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPrices.slice(0, 10).map((item, idx) => (
                    <tr key={item.id || idx} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '0.6rem 1rem', fontWeight: 600, color: '#1a3826' }}>{item.market_name || item.market}</td>
                      <td style={{ padding: '0.6rem 1rem', color: '#555' }}>{item.district}</td>
                      <td style={{ padding: '0.6rem 1rem', color: '#555' }}>{item.variety}</td>
                      <td style={{ padding: '0.6rem 1rem', color: '#777' }}>{item.price_date || item.arrival_date}</td>
                      <td style={{ padding: '0.6rem 1rem', fontWeight: 700, color: '#0d5c38', textAlign: 'right' }}>
                        ₹{item.modal_price ? Number(item.modal_price).toLocaleString() : '--'}/qtl
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 3: VERIFIED GRAIN BUYERS DIRECTORY                              */}
      {/* =================================================================== */}
      {activeTab === 'buyers' && (
        <div>
          {/* Nearby Action Bar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              {/* Type Filter */}
              <select
                value={buyerTypeFilter}
                onChange={e => setBuyerTypeFilter(e.target.value)}
                style={{ padding: '0.4rem 0.75rem', borderRadius: '6px', border: '1px solid #ccc', fontSize: '0.8rem' }}
              >
                <option value="all">All Buyer Types</option>
                <option value="mill">Rice Mill</option>
                <option value="fpo">FPO</option>
                <option value="government_agency">Government Agency</option>
                <option value="trader">Trader</option>
                <option value="wholesaler">Wholesaler</option>
              </select>

              {/* District Filter */}
              <select
                value={buyerDistrictFilter}
                onChange={e => setBuyerDistrictFilter(e.target.value)}
                style={{ padding: '0.4rem 0.75rem', borderRadius: '6px', border: '1px solid #ccc', fontSize: '0.8rem' }}
              >
                <option value="all">All Districts</option>
                {distinctDistricts.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>

              <input
                type="text"
                placeholder="Search buyer name or variety..."
                value={buyerSearchQuery}
                onChange={e => setBuyerSearchQuery(e.target.value)}
                style={{ padding: '0.4rem 0.75rem', borderRadius: '6px', border: '1px solid #ccc', fontSize: '0.8rem', minWidth: '220px' }}
              />
            </div>

            <button
              onClick={handleFindNearbyBuyers}
              style={{
                padding: '0.45rem 1rem',
                backgroundColor: '#0d5c38',
                color: '#ffffff',
                border: 'none',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem'
              }}
            >
              📍 Find Nearest Buyers
            </button>
          </div>

          {/* Privacy Notice Banner */}
          {nearbyNotice && (
            <div style={{
              backgroundColor: '#fff8e1',
              border: '1px solid #ffe082',
              color: '#8d6e63',
              padding: '0.75rem 1rem',
              borderRadius: '8px',
              fontSize: '0.8rem',
              marginBottom: '1rem'
            }}>
              ℹ️ <strong>Nearby Notice:</strong> {nearbyStatus || 'Nearby buyer locations are not available yet. You can browse buyers by district.'}
            </div>
          )}

          {/* Buyers Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {filteredBuyers.length === 0 ? (
              <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '2rem', color: '#777' }}>
                No buyers found matching your criteria.
              </div>
            ) : (
              filteredBuyers.map(b => {
                const isVerified = (b.verification_status || '').toLowerCase() === 'verified';
                return (
                  <div 
                    key={b.id}
                    style={{
                      backgroundColor: '#ffffff',
                      border: '1px solid #e0e0e0',
                      borderRadius: '10px',
                      padding: '1.15rem',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.03)'
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                        <h4 style={{ margin: 0, fontSize: '1rem', color: '#0d5c38', fontWeight: 700 }}>
                          {b.business_name}
                        </h4>
                        <span style={{
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          padding: '0.2rem 0.5rem',
                          borderRadius: '12px',
                          color: isVerified ? '#2e7d32' : '#ed6c02',
                          backgroundColor: isVerified ? '#e8f5e9' : '#fff4e5'
                        }}>
                          {isVerified ? '✓ Verified' : 'Pending'}
                        </span>
                      </div>

                      <span style={{ fontSize: '0.75rem', color: '#666', display: 'block', marginBottom: '0.5rem' }}>
                        Type: {b.buyer_type?.toUpperCase()} | District: {b.district}
                      </span>

                      <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.75rem', color: '#555', lineHeight: 1.4 }}>
                        {b.address_summary || `${b.district}, Andhra Pradesh`}
                      </p>

                      {b.preferred_varieties && b.preferred_varieties.length > 0 && (
                        <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                          {b.preferred_varieties.map((v, i) => (
                            <span key={i} style={{ fontSize: '0.65rem', background: '#f0f4f1', color: '#0d5c38', padding: '0.15rem 0.4rem', borderRadius: '4px' }}>
                              {v}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: '0.5rem', marginTop: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.7rem', color: '#888' }}>
                        Min: {b.min_procurement_quintals ? `${b.min_procurement_quintals} qtl` : 'Open'}
                      </span>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#0d5c38' }}>
                        {b.contact_phone ? `📞 ${b.contact_phone}` : '🏢 APEDA Listed'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </section>
  );
};

export default WeatherMarket;
