// ============================================================================
// PADDY FARMING ASSISTANT - HOME DASHBOARD CONTROLLER
// Complete UI/UX integration for the green-and-white agricultural dashboard:
// 1. Welcome Banner (Section A: Primary & Secondary Navigation)
// 2. Crop Health Summary (Section B: Unvalidated Status & Factual Indices)
// 3. Weather Summary (Section C: Live Open-Meteo & 3-Day Daily Forecast)
// 4. Recent Disease Detection (Section D: Predictions & Leaf Reference Images)
// 5. Market Snapshot (Section E: Agmarknet Mandi Spot Prices & Freshness)
// 6. Quick Action Workflows (Section F: 5 Core Tools)
// 7. Platform Status (Section G: Compact Service Health Indicator)
// ============================================================================

(function () {
  'use strict';

  const getApiBaseUrl = () => {
    if (typeof window !== 'undefined' && window.API_BASE_URL) {
      return String(window.API_BASE_URL).replace(/\/+$/, '');
    }
    return 'http://127.0.0.1:8000';
  };

  // Helper for safe JSON fetching with timeout and abort signal
  async function fetchJson(endpoint, options = {}, timeoutMs = 8000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const baseUrl = getApiBaseUrl();
      const response = await fetch(`${baseUrl}${endpoint}`, {
        ...options,
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
          ...(options.headers || {})
        }
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      throw err;
    }
  }

  // Formatting disease names into user-friendly titles
  function formatDiseaseName(raw) {
    if (!raw) return 'Unknown';
    const mapping = {
      'bacterial_leaf_blight': 'Bacterial Leaf Blight',
      'blast': 'Rice Blast',
      'brown_spot': 'Brown Spot',
      'tungro': 'Tungro',
      'leaf_smut': 'Leaf Smut',
      'sheath_blight': 'Sheath Blight',
      'normal': 'Healthy Leaf',
      'healthy': 'Healthy Leaf'
    };
    const key = String(raw).toLowerCase().trim();
    if (mapping[key]) return mapping[key];
    return raw.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  // Safe thumbnail asset mapping based on actual local images in public/assets/leaves/
  function getDiseaseThumbnail(diseaseName) {
    const key = String(diseaseName).toLowerCase();
    if (key.includes('blast')) {
      return '/assets/leaves/leaf-blast.jpg';
    }
    if (key.includes('brown')) {
      return '/assets/leaves/leaf-brown-spot.jpg';
    }
    if (key.includes('tungro')) {
      return '/assets/leaves/leaf-tungro.jpg';
    }
    if (key.includes('normal') || key.includes('healthy')) {
      return '/assets/leaves/leaf-normal.jpg';
    }
    // Default fallback reference leaf image
    return '/assets/leaves/leaf-normal.jpg';
  }

  // Format date helper
  function formatDate(isoString) {
    if (!isoString) return '--';
    try {
      const d = new Date(isoString);
      if (isNaN(d.getTime())) return isoString;
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return isoString;
    }
  }

  // World Meteorological Organization (WMO) Standard Code Mapping
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

  function getWeatherConditionText(condition, code) {
    if (condition && typeof condition === 'string' && condition.trim().length > 0) {
      return condition.trim();
    }
    if (code !== null && code !== undefined && WMO_CODE_MAP[code] !== undefined) {
      return WMO_CODE_MAP[code];
    }
    return 'Unavailable';
  }

  // Format short date for forecast in field timezone with noon UTC to prevent day shifting
  function formatForecastDay(dateString, timeZone = 'Asia/Kolkata') {
    if (!dateString) return '--';
    try {
      const parts = String(dateString).split('-');
      if (parts.length === 3) {
        const [year, month, day] = parts.map(Number);
        if (!isNaN(year) && !isNaN(month) && !isNaN(day)) {
          const d = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
          return d.toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            timeZone
          });
        }
      }
      const d = new Date(dateString);
      if (isNaN(d.getTime())) return dateString;
      return d.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        timeZone
      });
    } catch {
      return dateString;
    }
  }

  function formatDateTime(isoString, timeZone = 'Asia/Kolkata') {
    if (!isoString) return '--';
    try {
      let parseable = String(isoString);
      if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(parseable)) {
        parseable = `${parseable}+05:30`;
      }
      const d = new Date(parseable);
      if (isNaN(d.getTime())) return isoString;
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZone
      });
    } catch {
      return isoString;
    }
  }

  // Format Indian Rupee currency
  function formatINR(val) {
    if (val === null || val === undefined || isNaN(val)) return '--';
    return `₹${Math.round(Number(val)).toLocaleString('en-IN')}`;
  }

  // --------------------------------------------------------------------------
  // SECTION B: CROP HEALTH SUMMARY & FACTUAL VEGETATION INDICES LOADER
  // --------------------------------------------------------------------------
  async function loadCropHealthSummary() {
    const loadingEl = document.getElementById('home-health-loading');
    const contentEl = document.getElementById('home-health-content');
    const errorEl = document.getElementById('home-health-error');
    const fieldIdEl = document.getElementById('home-health-field-id');

    const ndviValEl = document.getElementById('home-ndvi-val');
    const ndviChangeEl = document.getElementById('home-ndvi-change');
    const ndviTrendBadge = document.getElementById('home-ndvi-trend-badge');

    const ndreValEl = document.getElementById('home-ndre-val');
    const ndreChangeEl = document.getElementById('home-ndre-change');
    const ndreTrendBadge = document.getElementById('home-ndre-trend-badge');

    const gndviValEl = document.getElementById('home-gndvi-val');
    const gndviChangeEl = document.getElementById('home-gndvi-change');
    const gndviTrendBadge = document.getElementById('home-gndvi-trend-badge');

    const datesEl = document.getElementById('home-indices-dates');

    if (!loadingEl || !contentEl || !errorEl) return;

    loadingEl.classList.remove('hidden');
    contentEl.classList.add('hidden');
    errorEl.classList.add('hidden');

    try {
      // Step 0: Fetch aggregate health summary for the 3 summary cards
      try {
        const summaryData = await fetchJson('/fields/health-summary');
        if (summaryData) {
          const healthyCountEl = document.getElementById('home-health-healthy-count');
          const healthySubEl = document.getElementById('home-health-healthy-sub');
          const attentionCountEl = document.getElementById('home-health-attention-count');
          const attentionSubEl = document.getElementById('home-health-attention-sub');
          const highRiskCountEl = document.getElementById('home-health-highrisk-count');
          const highRiskSubEl = document.getElementById('home-health-highrisk-sub');

          if (healthyCountEl && summaryData.healthy_count !== undefined) {
            healthyCountEl.textContent = `${summaryData.healthy_count} Fields`;
          }
          if (healthySubEl && summaryData.healthy_pct !== undefined) {
            healthySubEl.textContent = `NDVI ≥ 0.60 · High photosynthetic vigor (${summaryData.healthy_pct}%)`;
          }
          if (attentionCountEl && summaryData.needs_attention_count !== undefined) {
            attentionCountEl.textContent = `${summaryData.needs_attention_count} Fields`;
          }
          if (attentionSubEl && summaryData.needs_attention_pct !== undefined) {
            attentionSubEl.textContent = `0.35 ≤ NDVI < 0.60 · Moderate canopy density (${summaryData.needs_attention_pct}%)`;
          }
          if (highRiskCountEl && summaryData.high_risk_count !== undefined) {
            highRiskCountEl.textContent = `${summaryData.high_risk_count} Fields`;
          }
          if (highRiskSubEl && summaryData.high_risk_pct !== undefined) {
            highRiskSubEl.textContent = `NDVI < 0.35 · Canopy stress / vegetative deficit (${summaryData.high_risk_pct}%)`;
          }
        }
      } catch (sumErr) {
        console.warn('[Home Dashboard] Health summary dynamic fetch fallback:', sumErr.message);
      }

      // Step 1: Query /fields to identify available field records
      let targetFieldId = 'FIELD_01';
      try {
        const fieldsData = await fetchJson('/fields?skip=0&limit=10');
        if (fieldsData && Array.isArray(fieldsData.fields) && fieldsData.fields.length > 0) {
          const firstField = fieldsData.fields.find(f => f.has_images) || fieldsData.fields[0];
          if (firstField && firstField.field_id) {
            targetFieldId = firstField.field_id;
          }
        }
      } catch (err) {
        console.warn('[Home Dashboard] Falling back to default field for health:', err.message);
      }

      if (fieldIdEl) {
        fieldIdEl.textContent = `Field ${targetFieldId}`;
      }

      // Step 2: Fetch factual health indices from /fields/{field_id}/health
      const healthData = await fetchJson(`/fields/${encodeURIComponent(targetFieldId)}/health`);

      const latest = healthData && healthData.latest_indices ? healthData.latest_indices : null;
      const trends = healthData && healthData.changes_and_trends ? healthData.changes_and_trends : null;

      if (!latest) {
        throw new Error('Latest vegetation indices unavailable in API response');
      }

      // Format metric values safely
      const formatChange = (trendObj) => {
        if (!trendObj) return '--';
        const abs = trendObj.absolute_change !== undefined ? Number(trendObj.absolute_change) : 0;
        const pct = trendObj.percentage_change !== undefined ? Number(trendObj.percentage_change) : 0;
        const sign = abs >= 0 ? '+' : '';
        return `${sign}${abs.toFixed(4)} (${sign}${pct.toFixed(1)}%)`;
      };

      const formatTrendBadge = (badgeEl, trendObj) => {
        if (!badgeEl) return;
        const dir = trendObj && trendObj.direction ? String(trendObj.direction).toLowerCase() : 'neutral';
        if (dir === 'increasing') {
          badgeEl.textContent = 'Increasing';
          badgeEl.className = 'text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800';
        } else if (dir === 'decreasing') {
          badgeEl.textContent = 'Decreasing';
          badgeEl.className = 'text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800';
        } else {
          badgeEl.textContent = 'Stable';
          badgeEl.className = 'text-[10px] font-bold px-1.5 py-0.5 rounded bg-gray-100 text-gray-700';
        }
      };

      // Populate NDVI
      if (ndviValEl) {
        ndviValEl.textContent = latest.ndvi !== null && latest.ndvi !== undefined ? Number(latest.ndvi).toFixed(4) : '--';
      }
      if (ndviChangeEl) {
        ndviChangeEl.textContent = formatChange(trends ? trends.ndvi : null);
      }
      formatTrendBadge(ndviTrendBadge, trends ? trends.ndvi : null);

      // Populate NDRE
      if (ndreValEl) {
        ndreValEl.textContent = latest.ndre !== null && latest.ndre !== undefined ? Number(latest.ndre).toFixed(4) : '--';
      }
      if (ndreChangeEl) {
        ndreChangeEl.textContent = formatChange(trends ? trends.ndre : null);
      }
      formatTrendBadge(ndreTrendBadge, trends ? trends.ndre : null);

      // Populate GNDVI
      if (gndviValEl) {
        gndviValEl.textContent = latest.gndvi !== null && latest.gndvi !== undefined ? Number(latest.gndvi).toFixed(4) : '--';
      }
      if (gndviChangeEl) {
        gndviChangeEl.textContent = formatChange(trends ? trends.gndvi : null);
      }
      formatTrendBadge(gndviTrendBadge, trends ? trends.gndvi : null);

      // Observation Dates
      if (datesEl) {
        const obsLatest = formatDate(healthData.latest_observation_date);
        const obsPrev = formatDate(healthData.previous_observation_date);
        datesEl.textContent = `Observation: ${obsLatest} (Prior: ${obsPrev})`;
      }

      loadingEl.classList.add('hidden');
      contentEl.classList.remove('hidden');
    } catch (err) {
      console.warn('[Home Dashboard] Health indices unavailable:', err.message);
      loadingEl.classList.add('hidden');
      contentEl.classList.add('hidden');
      errorEl.classList.remove('hidden');
    }
  }

  // --------------------------------------------------------------------------
  // SECTION C: WEATHER SUMMARY & COMPACT DAILY FORECAST LOADER
  // --------------------------------------------------------------------------
  // --------------------------------------------------------------------------
  // SECTION C: WEATHER SUMMARY & COMPACT DAILY FORECAST LOADER
  // --------------------------------------------------------------------------
  async function loadWeatherSummary() {
    const loadingEl = document.getElementById('home-weather-loading');
    const contentEl = document.getElementById('home-weather-content');
    const errorEl = document.getElementById('home-weather-error');
    const tempEl = document.getElementById('home-weather-temp');
    const tempUnitEl = document.getElementById('home-weather-temp-unit');
    const condEl = document.getElementById('home-weather-condition');
    const rainEl = document.getElementById('home-weather-rain');
    const rainLabelEl = document.getElementById('home-weather-rain-label');
    const humidityEl = document.getElementById('home-weather-humidity');
    const windEl = document.getElementById('home-weather-wind');
    const updatedEl = document.getElementById('home-weather-updated');
    const providerBadgeEl = document.getElementById('home-weather-provider-badge');
    const forecastListEl = document.getElementById('home-weather-forecast-list');

    if (!loadingEl || !contentEl || !errorEl) return;

    loadingEl.classList.remove('hidden');
    contentEl.classList.add('hidden');
    errorEl.classList.add('hidden');

    try {
      // Reuses verified centroid endpoint /fields/FIELD_01/weather
      const data = await fetchJson('/fields/FIELD_01/weather');
      const current = data && data.current ? data.current : null;

      if (!current) {
        throw new Error('Current weather payload empty');
      }

      const tz = data.timezone || 'Asia/Kolkata';

      // 1. Populate Current Temperature
      if (tempEl) {
        tempEl.textContent = (current.temperature !== null && current.temperature !== undefined)
          ? Math.round(current.temperature)
          : '--';
      }
      if (tempUnitEl) {
        tempUnitEl.textContent = current.temperature_unit || '°C';
      }

      // 2. Populate Standardized Weather Condition (No invented 'Fair' or 'Overcast' defaults)
      if (condEl) {
        condEl.textContent = getWeatherConditionText(current.weather_condition, current.weather_code);
      }

      // 3. Populate Rainfall / Precipitation with accurate interval label
      const precipVal = current.precipitation !== null && current.precipitation !== undefined
        ? current.precipitation
        : (current.rain !== null && current.rain !== undefined ? current.rain : null);

      if (rainEl) {
        if (precipVal !== null && precipVal !== undefined) {
          rainEl.textContent = `${Number(precipVal).toFixed(1)} mm`;
        } else {
          rainEl.textContent = '-- mm';
        }
      }

      if (rainLabelEl) {
        if (current.interval_seconds && current.interval_seconds > 0) {
          const minutes = Math.round(current.interval_seconds / 60);
          rainLabelEl.textContent = `Rainfall (${minutes}m)`;
        } else {
          rainLabelEl.textContent = 'Rainfall (Current)';
        }
      }

      // 4. Populate Relative Humidity
      if (humidityEl) {
        humidityEl.textContent = (current.relative_humidity !== null && current.relative_humidity !== undefined)
          ? `${Math.round(current.relative_humidity)}%`
          : '--%';
      }

      // 5. Populate Wind Speed (preserving 0 for calm wind)
      if (windEl) {
        windEl.textContent = (current.wind_speed !== null && current.wind_speed !== undefined)
          ? `${Number(current.wind_speed).toFixed(1)} ${current.wind_speed_unit || 'km/h'}`
          : '-- km/h';
      }

      // 6. Provider Badge & Observation / Forecast Model Timestamps
      if (providerBadgeEl) {
        const isCached = Boolean(data.is_cached || (data.provider && data.provider.includes('Cached')));
        if (isCached) {
          providerBadgeEl.textContent = 'Cached Feed';
          providerBadgeEl.className = 'inline-flex items-center gap-1 text-[11px] font-semibold text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200';
        } else {
          providerBadgeEl.textContent = 'Live Feed';
          providerBadgeEl.className = 'inline-flex items-center gap-1 text-[11px] font-semibold text-sky-800 bg-sky-50 px-2 py-0.5 rounded border border-sky-100';
        }
      }

      if (updatedEl) {
        if (current.time) {
          updatedEl.textContent = `Forecast Time: ${formatDateTime(current.time, tz)}`;
        } else {
          updatedEl.textContent = 'Open-Meteo Feed';
        }
      }

      // 7. Populate Compact 3-Day Agro Forecast Strip (strictly upcoming 3 days)
      if (forecastListEl && Array.isArray(data.daily_forecast)) {
        forecastListEl.innerHTML = '';

        // Compute today's date in field's local timezone (YYYY-MM-DD)
        let todayStr = '';
        try {
          todayStr = new Intl.DateTimeFormat('en-CA', {
            timeZone: tz,
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
          }).format(new Date());
        } catch {
          todayStr = new Date().toISOString().split('T')[0];
        }

        // Strictly select upcoming 3 forecast days starting from tomorrow
        let upcomingDays = data.daily_forecast.filter(day => day && day.date && day.date > todayStr);

        // Fallback: If dates are historical (e.g. static tests), slice starting after index 0 to avoid presenting today as tomorrow
        if (upcomingDays.length === 0) {
          upcomingDays = data.daily_forecast.length > 3
            ? data.daily_forecast.slice(1, 4)
            : data.daily_forecast.slice(0, 3);
        } else {
          upcomingDays = upcomingDays.slice(0, 3);
        }

        if (upcomingDays.length === 0) {
          forecastListEl.innerHTML = '<span class="col-span-3 text-gray-400 py-1 text-center">Forecast data unavailable</span>';
        } else {
          upcomingDays.forEach(day => {
            const dayCard = document.createElement('div');
            dayCard.className = 'p-2 rounded-lg bg-gray-50/80 border border-gray-100 flex flex-col justify-between';

            const dayTitle = formatForecastDay(day.date, tz);
            const conditionText = getWeatherConditionText(day.weather_condition, day.weather_code);
            const tempMax = (day.temperature_max !== null && day.temperature_max !== undefined)
              ? Math.round(day.temperature_max)
              : '--';
            const tempMin = (day.temperature_min !== null && day.temperature_min !== undefined)
              ? Math.round(day.temperature_min)
              : '--';

            const dayPrecip = day.precipitation_sum !== null && day.precipitation_sum !== undefined
              ? day.precipitation_sum
              : (day.rain_sum !== null && day.rain_sum !== undefined ? day.rain_sum : null);

            const rainLabel = dayPrecip !== null && dayPrecip !== undefined
              ? `${Number(dayPrecip).toFixed(1)} mm rain`
              : '-- mm rain';

            dayCard.innerHTML = `
              <span class="text-[10px] font-bold text-gray-700 block truncate" title="${dayTitle}">${dayTitle}</span>
              <span class="text-[10px] text-emerald-800 font-medium block truncate my-1" title="${conditionText}">${conditionText}</span>
              <div class="text-[11px] font-black text-gray-900">${tempMax}° / <span class="text-gray-500 font-normal">${tempMin}°</span></div>
              <span class="text-[9px] text-sky-700 font-semibold block mt-1">${rainLabel}</span>
            `;
            forecastListEl.appendChild(dayCard);
          });
        }
      }

      loadingEl.classList.add('hidden');
      contentEl.classList.remove('hidden');
    } catch (err) {
      console.warn('[Home Dashboard] Weather fetch unavailable:', err.message);
      loadingEl.classList.add('hidden');
      contentEl.classList.add('hidden');
      errorEl.classList.remove('hidden');
    }
  }

  // --------------------------------------------------------------------------
  // SECTION D: RECENT DISEASE DETECTION LOADER
  // --------------------------------------------------------------------------
  async function loadRecentDiseases() {
    const loadingEl = document.getElementById('home-disease-loading');
    const contentEl = document.getElementById('home-disease-content');
    const emptyEl = document.getElementById('home-disease-empty');
    const errorEl = document.getElementById('home-disease-error');
    const tableBody = document.getElementById('home-disease-table-body');

    if (!loadingEl || !contentEl || !emptyEl || !errorEl || !tableBody) return;

    loadingEl.classList.remove('hidden');
    contentEl.classList.add('hidden');
    emptyEl.classList.add('hidden');
    errorEl.classList.add('hidden');

    try {
      // Reuses existing prediction history API
      const data = await fetchJson('/predictions?page=1&page_size=4');
      const records = data && Array.isArray(data.predictions) ? data.predictions : [];

      if (records.length === 0) {
        loadingEl.classList.add('hidden');
        emptyEl.classList.remove('hidden');
        return;
      }

      // Render table rows
      tableBody.innerHTML = '';
      records.forEach(record => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-emerald-50/40 transition-colors border-b border-gray-100 last:border-b-0';

        const diseaseTitle = formatDiseaseName(record.predicted_disease);
        const thumbSrc = getDiseaseThumbnail(record.predicted_disease);
        const confPercent = record.confidence !== null && record.confidence !== undefined
          ? `${(Number(record.confidence) * 100).toFixed(1)}%`
          : '--';
        const dateFormatted = formatDateTime(record.created_at);

        // Confidence badge styling
        const isHighConfidence = Number(record.confidence || 0) >= 0.85;
        const confBadgeClass = isHighConfidence
          ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
          : 'bg-amber-50 text-amber-800 border-amber-200';

        tr.innerHTML = `
          <td class="py-2.5 px-3">
            <div class="flex items-center gap-2">
              <div class="w-9 h-9 rounded-lg overflow-hidden bg-gray-100 border border-gray-200/80 flex items-center justify-center flex-shrink-0">
                <img src="${thumbSrc}" alt="${diseaseTitle}" class="w-full h-full object-cover" onerror="this.src='/assets/leaves/leaf-normal.jpg'" />
              </div>
              <span class="text-[9px] text-gray-400 font-medium leading-none">Reference</span>
            </div>
          </td>
          <td class="py-2.5 px-3 font-semibold text-gray-900">
            <span class="block">${diseaseTitle}</span>
            <span class="text-[10px] text-gray-400 font-normal capitalize">${record.prediction_mode || 'Leaf Check'}</span>
          </td>
          <td class="py-2.5 px-3">
            <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-bold border ${confBadgeClass}">
              ${confPercent}
            </span>
          </td>
          <td class="py-2.5 px-3 text-gray-500 text-[11px] whitespace-nowrap">
            ${dateFormatted}
          </td>
          <td class="py-2.5 px-3 text-right">
            <button class="nav-link px-2.5 py-1 text-[11px] font-bold text-emerald-700 hover:text-white hover:bg-emerald-700 rounded-md border border-emerald-300 transition-all cursor-pointer" data-target="page-reports">
              View
            </button>
          </td>
        `;
        tableBody.appendChild(tr);
      });

      loadingEl.classList.add('hidden');
      contentEl.classList.remove('hidden');

      // Bind dynamic nav links in table rows
      bindNavLinks(contentEl);
    } catch (err) {
      console.warn('[Home Dashboard] Disease history unavailable:', err.message);
      loadingEl.classList.add('hidden');
      contentEl.classList.add('hidden');
      emptyEl.classList.add('hidden');
      errorEl.classList.remove('hidden');
    }
  }

  // --------------------------------------------------------------------------
  // SECTION E: MARKET SNAPSHOT LOADER
  // --------------------------------------------------------------------------
  async function loadMarketSnapshot() {
    const loadingEl = document.getElementById('home-market-loading');
    const contentEl = document.getElementById('home-market-content');
    const emptyEl = document.getElementById('home-market-empty');
    const errorEl = document.getElementById('home-market-error');
    const tableBody = document.getElementById('home-market-table-body');
    const freshnessEl = document.getElementById('home-market-freshness');

    if (!loadingEl || !contentEl || !emptyEl || !errorEl || !tableBody) return;

    loadingEl.classList.remove('hidden');
    contentEl.classList.add('hidden');
    emptyEl.classList.add('hidden');
    errorEl.classList.add('hidden');

    try {
      // Reuses verified /market/prices/latest endpoint
      let data = null;
      try {
        data = await fetchJson('/market/prices/latest?commodity=Paddy%20(Dhan)&limit=4');
      } catch {
        // Fallback without commodity filter
        data = await fetchJson('/market/prices/latest?limit=4');
      }

      const items = data && Array.isArray(data.items) ? data.items : [];

      if (items.length === 0) {
        loadingEl.classList.add('hidden');
        emptyEl.classList.remove('hidden');
        return;
      }

      tableBody.innerHTML = '';
      items.forEach(item => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-emerald-50/40 transition-colors border-b border-gray-100 last:border-b-0';

        const marketName = item.market_name || 'Regulated Mandi';
        const locationText = [item.district, item.state].filter(Boolean).join(', ');
        const varietyVal = item.variety || item.grade || 'Common';
        const priceVal = formatINR(item.modal_price);
        const dateVal = formatDate(item.price_date);

        // Freshness status
        const isStale = Boolean(item.is_stale);
        const statusBadge = isStale
          ? '<span class="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-800 border border-amber-200">Stale</span>'
          : '<span class="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">DB Cache</span>';

        tr.innerHTML = `
          <td class="py-2.5 px-3">
            <span class="block font-semibold text-gray-900 truncate max-w-[150px]" title="${marketName}">${marketName}</span>
            <span class="text-[10px] text-gray-500 block truncate max-w-[150px]" title="${locationText}">${locationText || 'Mandi'}</span>
          </td>
          <td class="py-2.5 px-3 text-gray-700">
            <span class="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-700">
              ${varietyVal}
            </span>
          </td>
          <td class="py-2.5 px-3 font-bold text-emerald-800 whitespace-nowrap">
            ${priceVal} <span class="text-[10px] font-normal text-gray-500">/ Qtl</span>
          </td>
          <td class="py-2.5 px-3 text-gray-500 text-[11px] whitespace-nowrap">${dateVal}</td>
          <td class="py-2.5 px-3">
            ${statusBadge}
          </td>
        `;
        tableBody.appendChild(tr);
      });

      if (freshnessEl && data.freshness_date) {
        freshnessEl.textContent = `DB Freshness: ${formatDate(data.freshness_date)}`;
      }

      loadingEl.classList.add('hidden');
      contentEl.classList.remove('hidden');
    } catch (err) {
      console.warn('[Home Dashboard] Market prices unavailable:', err.message);
      loadingEl.classList.add('hidden');
      contentEl.classList.add('hidden');
      emptyEl.classList.add('hidden');
      errorEl.classList.remove('hidden');
    }
  }

  // --------------------------------------------------------------------------
  // SECTION G: PLATFORM STATUS LOADER
  // --------------------------------------------------------------------------
  async function loadPlatformStatus() {
    const overallDot = document.getElementById('platform-overall-dot');
    const statusText = document.getElementById('platform-status-text');
    const apiVal = document.getElementById('api-status-val');
    const dbVal = document.getElementById('db-status-val');
    const modelVal = document.getElementById('model-status-val');

    try {
      const [apiHealth, dbHealth, modelHealth] = await Promise.allSettled([
        fetchJson('/health', {}, 4000),
        fetchJson('/health/database', {}, 4000),
        fetchJson('/health/model', {}, 4000)
      ]);

      let allOk = true;

      // API check
      if (apiHealth.status === 'fulfilled' && apiHealth.value && apiHealth.value.status === 'healthy') {
        if (apiVal) apiVal.textContent = 'Online (v1)';
      } else {
        allOk = false;
        if (apiVal) apiVal.textContent = 'Degraded';
      }

      // DB check
      if (dbHealth.status === 'fulfilled' && dbHealth.value && dbHealth.value.connected === true) {
        if (dbVal) dbVal.textContent = 'Connected';
      } else {
        allOk = false;
        if (dbVal) dbVal.textContent = 'Disconnected';
      }

      // Model check
      if (modelHealth.status === 'fulfilled' && modelHealth.value && modelHealth.value.model_loaded === true) {
        if (modelVal) modelVal.textContent = 'Ready (EfficientNet-B4)';
      } else {
        if (modelVal) modelVal.textContent = 'Standby';
      }

      if (statusText) {
        statusText.textContent = allOk ? 'All agricultural services operational' : 'Partial service availability';
      }
      if (overallDot) {
        overallDot.className = allOk ? 'w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse' : 'w-2.5 h-2.5 rounded-full bg-amber-500';
      }
    } catch (err) {
      console.warn('[Home Dashboard] Status check failed:', err.message);
      if (statusText) statusText.textContent = 'Agricultural services online';
    }
  }

  // --------------------------------------------------------------------------
  // BIND NAVIGATION EVENTS
  // --------------------------------------------------------------------------
  function bindNavLinks(root = document) {
    const links = root.querySelectorAll('[data-target]');
    links.forEach(btn => {
      // Avoid duplicate listener bindings
      if (btn.dataset.bound === 'true') return;
      btn.dataset.bound = 'true';

      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const targetPage = btn.getAttribute('data-target');
        if (targetPage && typeof window.goToPage === 'function') {
          window.goToPage(targetPage);
        }
      });
    });
  }

  // --------------------------------------------------------------------------
  // MASTER INIT
  // --------------------------------------------------------------------------
  async function initHomeDashboard() {
    // Bind retry buttons
    const healthRetry = document.getElementById('home-health-retry');
    if (healthRetry) {
      healthRetry.onclick = () => loadCropHealthSummary();
    }

    const weatherRetry = document.getElementById('home-weather-retry');
    if (weatherRetry) {
      weatherRetry.onclick = () => loadWeatherSummary();
    }

    const diseaseRetry = document.getElementById('home-disease-retry');
    if (diseaseRetry) {
      diseaseRetry.onclick = () => loadRecentDiseases();
    }

    const marketRetry = document.getElementById('home-market-retry');
    if (marketRetry) {
      marketRetry.onclick = () => loadMarketSnapshot();
    }

    // Bind all initial nav links on page-home
    const pageHome = document.getElementById('page-home');
    if (pageHome) {
      bindNavLinks(pageHome);
    }

    // Trigger data loading concurrently in parallel so failure of one does not block others
    await Promise.allSettled([
      loadCropHealthSummary(),
      loadWeatherSummary(),
      loadRecentDiseases(),
      loadMarketSnapshot(),
      loadPlatformStatus()
    ]);
  }

  // Expose global refresh handle
  window.refreshHomeDashboard = initHomeDashboard;

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHomeDashboard);
  } else {
    initHomeDashboard();
  }

})();
