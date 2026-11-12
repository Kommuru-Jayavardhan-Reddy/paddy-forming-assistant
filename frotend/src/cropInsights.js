// ============================================================================
// STEP 7 / STEP 11J.4 / CROP INSIGHTS REDESIGN CONTROLLER
// Displays authentic diagnostic analytics, historical AI predictions,
// multimodal cross-attention metrics, and interactive filters.
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  const getApiBaseUrl = () => {
    if (typeof window !== 'undefined' && window.API_BASE_URL) {
      return String(window.API_BASE_URL).replace(/\/+$/, '');
    }
    return 'http://127.0.0.1:8000';
  };

  // Scientifically validated knowledge base for foliar paddy diseases
  const DISEASE_KNOWLEDGE = {
    bacterial_leaf_blight: {
      name: 'Bacterial Leaf Blight',
      status: 'High Risk',
      symptoms: [
        'Water-soaked lesions on leaf margins and tips',
        'Yellowish-orange wavy margins progressing down blades',
        'Grayish-white dried encrustations with bacterial ooze'
      ],
      explanation: 'Bacterial infection caused by Xanthomonas oryzae pv. oryzae. Rapid spread is favored by high humidity and excessive nitrogen fertilization. Ensure field drainage and balance fertilization.'
    },
    bacterial_leaf_streak: {
      name: 'Bacterial Leaf Streak',
      status: 'Needs Attention',
      symptoms: [
        'Narrow, yellowish-brown translucent streaks between leaf veins',
        'Amber-colored bacterial droplets exuding in morning hours',
        'Browning and drying of older infected leaf blades'
      ],
      explanation: 'Bacterial foliar streak develops rapidly during stormy weather and overhead wetness. Avoid excessive top-dressing with urea.'
    },
    bacterial_panicle_blight: {
      name: 'Bacterial Panicle Blight',
      status: 'High Risk',
      symptoms: [
        'Discolored florets turning gray-brown with dark borders',
        'Aborted grain filling leaving panicles standing upright',
        'Stem necrosis immediately below infected panicles'
      ],
      explanation: 'Panicle blight affects grain formation during heading and flowering stages under prolonged elevated nighttime temperatures.'
    },
    blast: {
      name: 'Rice Blast',
      status: 'High Risk',
      symptoms: [
        'Spindle-shaped elliptical lesions with gray centers',
        'Dark reddish-brown borders encircling foliar spots',
        'Collar rot and node neck blast in advanced stages'
      ],
      explanation: 'Magnaporthe oryzae fungal infection causing severe tissue destruction. High humidity and dense canopy accelerate disease propagation.'
    },
    brown_spot: {
      name: 'Brown Spot',
      status: 'Needs Attention',
      symptoms: [
        'Small, circular to oval dark-brown spots on leaf blades',
        'Yellow chlorotic halos surrounding lesions',
        'Seedling blight and coleoptile spotting'
      ],
      explanation: 'Foliar fungal spotting caused by Bipolaris oryzae. Typically associated with nutrient-deficient, poorly drained, or sandy soils.'
    },
    dead_heart: {
      name: 'Dead Heart (Stem Borer)',
      status: 'High Risk',
      symptoms: [
        'Central tiller shoot wilts and dries while outer leaves stay green',
        'Shoot easily pulled out from stem base with severed base',
        'Frass and larval entry holes near stem internodes'
      ],
      explanation: 'Internal larvae of Scirpophaga incertulas sever vascular bundles at the tiller base. Monitor with pheromone traps and conserve egg parasitoids.'
    },
    downy_mildew: {
      name: 'Downy Mildew',
      status: 'Needs Attention',
      symptoms: [
        'Stunted, twisted seedlings with thickened leaf blades',
        'Pale yellow chlorotic mottling across leaves',
        'Excessive tillering with shortened internodes'
      ],
      explanation: 'Soil- and water-borne oomycete infection. Occurs in waterlogged nurseries or poorly drained lowlands.'
    },
    hispa: {
      name: 'Rice Hispa',
      status: 'Needs Attention',
      symptoms: [
        'White parallel streaks where leaf surface was scraped by adults',
        'Blister mines within leaf blades created by larvae',
        'Leaves withered and appearing scorched or bleached'
      ],
      explanation: 'Dicladispa armigera beetle feeding on green parenchymal tissue. Clip infested leaf tips before transplanting.'
    },
    leaf_scald: {
      name: 'Leaf Scald',
      status: 'Needs Attention',
      symptoms: [
        'Zonate chevron-patterned bands from leaf tip backward',
        'Alternating light tan and dark brown wavy bands',
        'Premature senescence of entire flag leaf'
      ],
      explanation: 'Microdochium oryzae fungal infection. Develops rapidly in mature canopies with high humidity and close planting.'
    },
    leaf_smut: {
      name: 'Leaf Smut',
      status: 'Needs Attention',
      symptoms: [
        'Small, raised angular black pustules on leaf surface',
        'Ruptured leaf epidermis releasing dark teliospores',
        'Yellowing of heavily infested leaf tips'
      ],
      explanation: 'Entyloma oryzae fungal infection occurring near maturity. Typically causes negligible yield reduction under balanced nutrition.'
    },
    normal: {
      name: 'Normal / Healthy Crop',
      status: 'Healthy',
      symptoms: [
        'Uniform green pigmentation across entire leaf blade',
        'Intact leaf margin and tip with no necrotic lesions',
        'Healthy tiller development and vascular turgor'
      ],
      explanation: 'Crop foliar tissue exhibits optimal photosynthesis and healthy cellular structure. Continue routine water management and scouting.'
    },
    sheath_blight: {
      name: 'Sheath Blight',
      status: 'High Risk',
      symptoms: [
        'Oval greenish-gray water-soaked spots on lower sheaths',
        'Borders turn brown with bleached grayish centers',
        'Lesions coalesce and spread upward to flag leaves'
      ],
      explanation: 'Rhizoctonia solani soil-borne fungus progressing vertically up the stem. High nitrogen dosage and dense plant canopy promote severity.'
    },
    tungro: {
      name: 'Rice Tungro Disease',
      status: 'High Risk',
      symptoms: [
        'Severe plant stunting and reduced tiller count',
        'Characteristic yellow or orange-yellow leaf discoloration',
        'Delayed flowering and sterile or empty panicles'
      ],
      explanation: 'Viral complex transmitted by Nephotettix virescens (green leafhopper). Rogue out infected hills and manage vector populations.'
    }
  };

  // Status and influence badge generators
  const getBadgeHTML = (status) => {
    if (status === 'Healthy') return `<span class="status-badge status-healthy py-1 px-3 text-xs" style="background:#e8f5e9;color:#2e7d32;border:1px solid #a5d6a7;border-radius:20px;font-weight:700;">Healthy</span>`;
    if (status === 'Needs Attention') return `<span class="status-badge status-attention py-1 px-3 text-xs" style="background:#fff4e5;color:#ed6c02;border:1px solid #ffcc80;border-radius:20px;font-weight:700;">Needs Attention</span>`;
    if (status === 'High Risk') return `<span class="status-badge status-risk py-1 px-3 text-xs" style="background:#ffebee;color:#d32f2f;border:1px solid #ef9a9a;border-radius:20px;font-weight:700;">High Risk</span>`;
    return `<span class="status-badge py-1 px-3 text-xs text-gray-600 bg-gray-100 rounded-full font-medium">Unknown</span>`;
  };

  const getInfluenceBadgeHTML = (level) => {
    if (level === 'High') return `<span class="px-2.5 py-0.5 bg-red-100 text-red-700 font-bold rounded-full text-xs">High</span>`;
    if (level === 'Medium') return `<span class="px-2.5 py-0.5 bg-amber-100 text-amber-700 font-bold rounded-full text-xs">Medium</span>`;
    if (level === 'Low') return `<span class="px-2.5 py-0.5 bg-green-100 text-green-700 font-bold rounded-full text-xs">Low</span>`;
    return `<span class="px-2.5 py-0.5 bg-gray-100 text-gray-500 font-bold rounded-full text-xs">N/A</span>`;
  };

  const formatDiseaseLabel = (raw) => {
    if (!raw) return 'Unknown';
    if (DISEASE_KNOWLEDGE[raw]) return DISEASE_KNOWLEDGE[raw].name;
    return raw.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  };

  // State Management
  let allPredictions = [];
  let fieldsCatalog = [];
  let fieldLookup = new Map(); // UUID or external_field_id -> field details
  let activeFilters = {
    period: 'all',
    field: 'all',
    search: '',
    date: '',
    fieldFilterMode: 'top10',
    trendGranularity: 'monthly'
  };

  // Chart Instances
  let diseaseDistChartInstance = null;
  let predictionTrendChartInstance = null;
  let fieldPredictionChartInstance = null;
  let typeDistChartInstance = null;

  // DOM Elements - Compatibility & Deep-Dive
  const devSwitcher = document.getElementById('insights-dev-switcher');
  const loadingState = document.getElementById('insights-loading');
  const contentContainer = document.getElementById('insights-content');
  const resCondition = document.getElementById('insights-condition');
  const resConfidence = document.getElementById('insights-confidence');
  const resStatusContainer = document.getElementById('insights-status-container');
  const inflLeaf = document.getElementById('insights-infl-leaf');
  const inflHealth = document.getElementById('insights-infl-health');
  const inflField = document.getElementById('insights-infl-field');
  const inflHealthCard = document.getElementById('insights-infl-health-card');
  const inflFieldCard = document.getElementById('insights-infl-field-card');
  const photoOnlyMsg = document.getElementById('insights-photo-only-msg');
  const inflGrid = document.getElementById('insights-influences-grid');
  const timelineContainer = document.getElementById('insights-timeline-container');
  const timeline = document.getElementById('insights-timeline');
  const symptoms = document.getElementById('insights-symptoms');
  const explanation = document.getElementById('insights-explanation');

  // DOM Elements - Hero & Controls
  const periodFilterSelect = document.getElementById('insights-period-filter');
  const fieldFilterSelect = document.getElementById('insights-field-filter');
  const tableSearchInput = document.getElementById('table-search-input');
  const tableDateFilter = document.getElementById('table-date-filter');
  const btnResetFilters = document.getElementById('btn-reset-filters');
  const btnExportCsv = document.getElementById('btn-export-csv');
  const fieldCountFilter = document.getElementById('field-count-filter');
  const btnGranularityMonthly = document.getElementById('trend-granularity-monthly');
  const btnGranularityDaily = document.getElementById('trend-granularity-daily');

  // DOM Elements - Stats
  const statTotal = document.getElementById('insights-stat-total');
  const statCategories = document.getElementById('insights-stat-categories');
  const statImage = document.getElementById('insights-stat-image');
  const statMultimodal = document.getElementById('insights-stat-multimodal');
  const statTotalSub = document.getElementById('insights-stat-total-sub');
  const statCategoriesBar = document.getElementById('insights-stat-categories-bar');
  const statImageBar = document.getElementById('insights-stat-image-bar');
  const statMultimodalBar = document.getElementById('insights-stat-multimodal-bar');

  // DOM Elements - Sections
  const topDiseasesList = document.getElementById('top-diseases-list');
  const keyInsightsList = document.getElementById('key-insights-list');
  const diseaseDistLegend = document.getElementById('disease-dist-legend');
  const diseaseDistCountBadge = document.getElementById('disease-dist-count-badge');
  const predictionsTableBody = document.getElementById('predictions-table-body');
  const tableEmptyState = document.getElementById('table-empty-state');
  const tableCounter = document.getElementById('table-counter');
  const trendChartEmpty = document.getElementById('trend-chart-empty');
  const typeStatImageVal = document.getElementById('type-stat-image-val');
  const typeStatImagePct = document.getElementById('type-stat-image-pct');
  const typeStatMultimodalVal = document.getElementById('type-stat-multimodal-val');
  const typeStatMultimodalPct = document.getElementById('type-stat-multimodal-pct');

  // --------------------------------------------------------------------------
  // Data Fetching
  // --------------------------------------------------------------------------
  const fetchAllData = async () => {
    try {
      const baseUrl = getApiBaseUrl();

      // Fetch predictions history and field catalog in parallel
      const [predRes, fieldsRes] = await Promise.all([
        fetch(`${baseUrl}/predictions?page_size=100`, { headers: { 'Accept': 'application/json' } }),
        fetch(`${baseUrl}/fields?user_only=true&limit=100`, { headers: { 'Accept': 'application/json' } }).catch(() => null)
      ]);

      if (predRes.ok) {
        const predData = await predRes.json();
        allPredictions = predData.predictions || [];
      } else {
        console.warn('Could not fetch /predictions:', predRes.status);
      }

      if (fieldsRes && fieldsRes.ok) {
        const fieldsData = await fieldsRes.json();
        fieldsCatalog = fieldsData.fields || [];
        fieldLookup.clear();
        fieldsCatalog.forEach(f => {
          if (f.field_id) fieldLookup.set(f.field_id, f);
          if (f.external_field_id) fieldLookup.set(f.external_field_id, f);
        });
      }

      populateFieldFilterOptions();
      populateSwitcherFromPredictions(allPredictions);
      refreshAnalytics();

      if (allPredictions.length > 0) {
        loadInsight(allPredictions[0].id);
      }
    } catch (err) {
      console.error('Error fetching crop insights data:', err);
    }
  };

  // --------------------------------------------------------------------------
  // Filter Population & Options
  // --------------------------------------------------------------------------
  const populateFieldFilterOptions = () => {
    if (!fieldFilterSelect) return;
    const currentVal = fieldFilterSelect.value;
    fieldFilterSelect.innerHTML = '<option value="all">All Fields</option>';

    // Collect all field IDs represented in predictions
    const fieldSet = new Set();
    allPredictions.forEach(p => {
      if (p.field_id) {
        fieldSet.add(p.field_id);
      }
    });

    // Add fields that appear in prediction history
    fieldSet.forEach(fid => {
      const fieldInfo = fieldLookup.get(fid);
      const opt = document.createElement('option');
      opt.value = fid;
      const label = fieldInfo ? `${fieldInfo.field_id || fid} (${fieldInfo.field_name || 'Parcel'})` : fid;
      opt.textContent = label;
      fieldFilterSelect.appendChild(opt);
    });

    if (currentVal && Array.from(fieldFilterSelect.options).some(o => o.value === currentVal)) {
      fieldFilterSelect.value = currentVal;
    }
  };

  const populateSwitcherFromPredictions = (records) => {
    if (!devSwitcher) return;
    devSwitcher.innerHTML = '';

    records.forEach((r, idx) => {
      const opt = document.createElement('option');
      opt.value = r.id;
      const dName = formatDiseaseLabel(r.predicted_disease);
      const confPct = Math.round((r.confidence || 0) * 100);
      const modeLabel = r.prediction_mode === 'multimodal' ? 'Multimodal' : 'Image Only';
      opt.textContent = `Record ${idx + 1}: [${modeLabel}] ${dName} (${confPct}%)`;
      devSwitcher.appendChild(opt);
    });
  };

  // --------------------------------------------------------------------------
  // Filtering Engine
  // --------------------------------------------------------------------------
  const getFilteredPredictions = () => {
    let result = [...allPredictions];

    // 1. Period Filter
    if (activeFilters.period !== 'all' && result.length > 0) {
      const now = new Date();
      let cutoffDays = 30;
      if (activeFilters.period === '90d') cutoffDays = 90;
      if (activeFilters.period === '180d') cutoffDays = 180;

      // Find newest record timestamp as reference date
      const latestTime = Math.max(...result.map(r => new Date(r.created_at || now).getTime()));
      const cutoffTime = latestTime - (cutoffDays * 24 * 60 * 60 * 1000);

      result = result.filter(r => {
        const t = new Date(r.created_at).getTime();
        return t >= cutoffTime;
      });
    }

    // 2. Field Filter
    if (activeFilters.field !== 'all') {
      result = result.filter(r => {
        return r.field_id === activeFilters.field;
      });
    }

    // 3. Date Filter (exact date YYYY-MM-DD)
    if (activeFilters.date) {
      result = result.filter(r => {
        if (!r.created_at) return false;
        const dStr = r.created_at.split('T')[0];
        return dStr === activeFilters.date;
      });
    }

    // 4. Search Filter (matches disease name, field id, or date)
    if (activeFilters.search.trim()) {
      const q = activeFilters.search.trim().toLowerCase();
      result = result.filter(r => {
        const dName = (r.predicted_disease || '').toLowerCase();
        const fName = formatDiseaseLabel(r.predicted_disease).toLowerCase();
        const fId = (r.field_id || '').toLowerCase();
        const mode = (r.prediction_mode || '').toLowerCase();
        const date = (r.created_at || '').toLowerCase();
        return dName.includes(q) || fName.includes(q) || fId.includes(q) || mode.includes(q) || date.includes(q);
      });
    }

    return result;
  };

  // --------------------------------------------------------------------------
  // Analytics Refresh Orchestrator
  // --------------------------------------------------------------------------
  const refreshAnalytics = () => {
    const filtered = getFilteredPredictions();

    updateSummaryCards(filtered);
    renderDiseaseDistChart(filtered);
    renderPredictionTrendChart(filtered);
    renderTop5Diseases(filtered);
    renderKeyInsights(filtered);
    renderFieldPredictionChart(filtered);
    renderTypeDistChart(filtered);
    renderRecentPredictionsTable(filtered);
  };

  // --------------------------------------------------------------------------
  // Summary Cards (Section 4)
  // --------------------------------------------------------------------------
  const updateSummaryCards = (records) => {
    const total = records.length;
    let distinctDiseases = new Set();
    let imageOnlyCount = 0;
    let multimodalCount = 0;

    records.forEach(r => {
      if (r.predicted_disease) distinctDiseases.add(r.predicted_disease);
      if (r.prediction_mode === 'multimodal') {
        multimodalCount++;
      } else {
        imageOnlyCount++;
      }
    });

    if (statTotal) statTotal.textContent = total.toLocaleString();
    if (statCategories) statCategories.textContent = distinctDiseases.size.toString();
    if (statImage) statImage.textContent = imageOnlyCount.toLocaleString();
    if (statMultimodal) statMultimodal.textContent = multimodalCount.toLocaleString();

    // Contextual subtitles and progress visuals
    if (statTotalSub) {
      statTotalSub.textContent = `Filtered across ${allPredictions.length} total database records`;
    }
    if (statCategoriesBar) {
      const pct = Math.min(100, Math.round((distinctDiseases.size / 13) * 100));
      statCategoriesBar.style.width = `${pct}%`;
    }
    if (statImageBar) {
      const pct = total > 0 ? Math.round((imageOnlyCount / total) * 100) : 0;
      statImageBar.style.width = `${pct}%`;
    }
    if (statMultimodalBar) {
      const pct = total > 0 ? Math.round((multimodalCount / total) * 100) : 0;
      statMultimodalBar.style.width = `${pct}%`;
    }
  };

  // --------------------------------------------------------------------------
  // Disease Prediction Distribution Chart (Section 5)
  // --------------------------------------------------------------------------
  const renderDiseaseDistChart = (records) => {
    const canvas = document.getElementById('disease-dist-chart');
    if (!canvas || typeof window.Chart === 'undefined') return;

    const ctx = canvas.getContext('2d');
    const total = records.length;

    // Group counts by disease
    const counts = {};
    records.forEach(r => {
      const d = r.predicted_disease || 'unknown';
      counts[d] = (counts[d] || 0) + 1;
    });

    const sortedDiseases = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const labels = sortedDiseases.map(([d]) => formatDiseaseLabel(d));
    const dataValues = sortedDiseases.map(([, count]) => count);

    // Harmonious curated agricultural color palette
    const palette = [
      '#0d5c38', '#10b981', '#0284c7', '#3b82f6',
      '#f59e0b', '#d97706', '#8b5cf6', '#6366f1',
      '#ec4899', '#14b8a6', '#84cc16', '#64748b'
    ];
    const bgColors = labels.map((_, i) => palette[i % palette.length]);

    if (diseaseDistChartInstance) {
      diseaseDistChartInstance.destroy();
    }

    if (dataValues.length === 0) {
      dataValues.push(1);
      labels.push('No data');
      bgColors.push('#e2e8f0');
    }

    diseaseDistChartInstance = new window.Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: dataValues,
          backgroundColor: bgColors,
          borderWidth: 2,
          borderColor: '#ffffff',
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              label: (item) => {
                const count = item.parsed;
                const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                return ` ${item.label}: ${count} (${pct}%)`;
              }
            }
          }
        },
        cutout: '68%'
      }
    });

    if (diseaseDistCountBadge) {
      diseaseDistCountBadge.textContent = `${sortedDiseases.length} categories represented`;
    }

    // Populate custom breakdown legend below chart
    if (diseaseDistLegend) {
      diseaseDistLegend.innerHTML = '';
      sortedDiseases.slice(0, 6).forEach(([d, count], idx) => {
        const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
        const color = palette[idx % palette.length];
        diseaseDistLegend.innerHTML += `
          <div class="flex items-center justify-between p-2 rounded-xl bg-slate-50 border border-slate-100">
            <div class="flex items-center gap-2 truncate">
              <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" style="background-color: ${color}"></span>
              <span class="font-medium text-slate-800 truncate">${formatDiseaseLabel(d)}</span>
            </div>
            <div class="text-right flex-shrink-0 ml-2">
              <span class="font-bold text-slate-900 font-mono">${count}</span>
              <span class="text-[10px] text-slate-400 ml-1">(${pct}%)</span>
            </div>
          </div>
        `;
      });
    }
  };

  // --------------------------------------------------------------------------
  // Prediction Trend Over Time Line Chart (Section 6)
  // --------------------------------------------------------------------------
  const renderPredictionTrendChart = (records) => {
    const canvas = document.getElementById('prediction-trend-chart');
    if (!canvas || typeof window.Chart === 'undefined') return;

    const ctx = canvas.getContext('2d');

    if (records.length === 0) {
      if (predictionTrendChartInstance) predictionTrendChartInstance.destroy();
      if (trendChartEmpty) trendChartEmpty.classList.remove('hidden');
      return;
    }
    if (trendChartEmpty) trendChartEmpty.classList.add('hidden');

    // Aggregate records chronologically
    const timeBuckets = {}; // bucketKey -> { image_only: 0, multimodal: 0, sortKey: number }

    records.forEach(r => {
      if (!r.created_at) return;
      const d = new Date(r.created_at);
      let key = '';

      if (activeFilters.trendGranularity === 'daily') {
        key = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
      } else {
        key = d.toLocaleDateString('en-GB', { month: 'short', year: '2-digit' });
      }

      if (!timeBuckets[key]) {
        timeBuckets[key] = {
          label: key,
          sortTime: d.getTime(),
          image_only: 0,
          multimodal: 0
        };
      }
      if (r.prediction_mode === 'multimodal') {
        timeBuckets[key].multimodal++;
      } else {
        timeBuckets[key].image_only++;
      }
    });

    const sortedBuckets = Object.values(timeBuckets).sort((a, b) => a.sortTime - b.sortTime);
    const labels = sortedBuckets.map(b => b.label);
    const imageOnlyData = sortedBuckets.map(b => b.image_only);
    const multimodalData = sortedBuckets.map(b => b.multimodal);

    if (predictionTrendChartInstance) {
      predictionTrendChartInstance.destroy();
    }

    predictionTrendChartInstance = new window.Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Image Only',
            data: imageOnlyData,
            borderColor: '#0d5c38',
            backgroundColor: 'rgba(13, 92, 56, 0.08)',
            borderWidth: 2.5,
            pointBackgroundColor: '#0d5c38',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 1.5,
            pointRadius: 4,
            tension: 0.3,
            fill: true
          },
          {
            label: 'Multimodal',
            data: multimodalData,
            borderColor: '#7c3aed',
            backgroundColor: 'transparent',
            borderWidth: 2.5,
            borderDash: [5, 5],
            pointBackgroundColor: '#7c3aed',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 1.5,
            pointRadius: 4,
            tension: 0.3,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top',
            align: 'end',
            labels: {
              boxWidth: 12,
              font: { size: 11, weight: 'bold' }
            }
          },
          tooltip: {
            padding: 10,
            cornerRadius: 8
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 11 } }
          },
          y: {
            beginAtZero: true,
            ticks: { stepSize: 1, font: { size: 11 } },
            grid: { color: 'rgba(0, 0, 0, 0.05)' }
          }
        }
      }
    });
  };

  // --------------------------------------------------------------------------
  // Top 5 Disease Predictions (Section 7)
  // --------------------------------------------------------------------------
  const renderTop5Diseases = (records) => {
    if (!topDiseasesList) return;
    const total = records.length;

    if (total === 0) {
      topDiseasesList.innerHTML = `<div class="text-xs text-slate-400 py-6 text-center">No predictions available.</div>`;
      return;
    }

    const counts = {};
    records.forEach(r => {
      const d = r.predicted_disease || 'unknown';
      counts[d] = (counts[d] || 0) + 1;
    });

    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 5);
    const maxCount = sorted.length > 0 ? sorted[0][1] : 1;

    topDiseasesList.innerHTML = '';
    sorted.forEach(([d, count], idx) => {
      const pct = ((count / total) * 100).toFixed(1);
      const barWidth = Math.max(5, Math.round((count / maxCount) * 100));
      const knowledge = DISEASE_KNOWLEDGE[d] || { name: formatDiseaseLabel(d), status: 'Unknown' };

      topDiseasesList.innerHTML += `
        <div class="space-y-1.5 p-3 rounded-xl bg-slate-50/80 border border-slate-100 hover:border-emerald-200 transition-colors">
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center gap-2 truncate">
              <span class="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold flex items-center justify-center flex-shrink-0">${idx + 1}</span>
              <span class="font-bold text-slate-800 truncate">${knowledge.name}</span>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              ${getBadgeHTML(knowledge.status)}
              <span class="font-mono font-bold text-slate-900">${count}</span>
              <span class="text-[11px] text-slate-400 font-medium">(${pct}%)</span>
            </div>
          </div>
          <div class="w-full bg-slate-200/80 h-2 rounded-full overflow-hidden">
            <div class="bg-emerald-600 h-full rounded-full transition-all duration-500" style="width: ${barWidth}%;"></div>
          </div>
        </div>
      `;
    });
  };

  // --------------------------------------------------------------------------
  // Key Insights (Section 10)
  // --------------------------------------------------------------------------
  const renderKeyInsights = (records) => {
    if (!keyInsightsList) return;
    const total = records.length;

    if (total === 0) {
      keyInsightsList.innerHTML = `
        <div class="p-3 bg-slate-50 rounded-xl text-xs text-slate-400 text-center">
          No records found in active scope to derive statistical insights.
        </div>
      `;
      return;
    }

    const counts = {};
    let multimodalCount = 0;
    const fieldSet = new Set();

    records.forEach(r => {
      const d = r.predicted_disease || 'unknown';
      counts[d] = (counts[d] || 0) + 1;
      if (r.prediction_mode === 'multimodal') multimodalCount++;
      if (r.field_id) fieldSet.add(r.field_id);
    });

    const sortedDiseases = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const topDisease = sortedDiseases[0];
    const topPct = ((topDisease[1] / total) * 100).toFixed(1);
    const multimodalPct = ((multimodalCount / total) * 100).toFixed(1);

    keyInsightsList.innerHTML = `
      <!-- Insight 1: Predominant Disease -->
      <div class="flex items-start gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100">
        <span class="w-6 h-6 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">1</span>
        <div>
          <h4 class="text-xs font-bold text-slate-800">Predominant Diagnosis</h4>
          <p class="text-[11px] text-slate-600 mt-0.5 leading-relaxed">
            <strong>${formatDiseaseLabel(topDisease[0])}</strong> represents <strong>${topDisease[1]}</strong> records (<strong>${topPct}%</strong> of current diagnostic checks).
          </p>
        </div>
      </div>

      <!-- Insight 2: Field Parcel Linkage -->
      <div class="flex items-start gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100">
        <span class="w-6 h-6 rounded-lg bg-blue-100 text-blue-800 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">2</span>
        <div>
          <h4 class="text-xs font-bold text-slate-800">Field Parcel Coverage</h4>
          <p class="text-[11px] text-slate-600 mt-0.5 leading-relaxed">
            Inferences encompass <strong>${fieldSet.size}</strong> distinct registered agricultural field parcel(s) across Andhra Pradesh.
          </p>
        </div>
      </div>

      <!-- Insight 3: Model Modality -->
      <div class="flex items-start gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100">
        <span class="w-6 h-6 rounded-lg bg-purple-100 text-purple-800 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">3</span>
        <div>
          <h4 class="text-xs font-bold text-slate-800">Satellite Fusion Utilization</h4>
          <p class="text-[11px] text-slate-600 mt-0.5 leading-relaxed">
            <strong>${multimodalCount}</strong> predictions (<strong>${multimodalPct}%</strong>) leverage multimodal Sentinel-2 temporal cross-attention.
          </p>
        </div>
      </div>
    `;
  };

  // --------------------------------------------------------------------------
  // Field-wise Prediction Count Bar Chart (Section 8)
  // --------------------------------------------------------------------------
  const renderFieldPredictionChart = (records) => {
    const canvas = document.getElementById('field-prediction-chart');
    if (!canvas || typeof window.Chart === 'undefined') return;

    const ctx = canvas.getContext('2d');
    const fieldCounts = {};

    records.forEach(r => {
      let key = r.field_id || 'Standalone Photo';
      const info = fieldLookup.get(key);
      if (info && info.field_id) key = info.field_id;
      fieldCounts[key] = (fieldCounts[key] || 0) + 1;
    });

    let sorted = Object.entries(fieldCounts).sort((a, b) => b[1] - a[1]);
    if (activeFilters.fieldFilterMode === 'top10') {
      sorted = sorted.slice(0, 10);
    }

    const labels = sorted.map(([k]) => k);
    const dataValues = sorted.map(([, count]) => count);

    if (fieldPredictionChartInstance) {
      fieldPredictionChartInstance.destroy();
    }

    fieldPredictionChartInstance = new window.Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Prediction Records',
          data: dataValues,
          backgroundColor: '#0d5c38',
          hoverBackgroundColor: '#064e3b',
          borderRadius: 6,
          maxBarThickness: 32
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => ` ${item.parsed.y} prediction records`
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 10 } }
          },
          y: {
            beginAtZero: true,
            ticks: { stepSize: 1, font: { size: 10 } },
            grid: { color: 'rgba(0, 0, 0, 0.05)' }
          }
        }
      }
    });
  };

  // --------------------------------------------------------------------------
  // Prediction Type Distribution (Section 9)
  // --------------------------------------------------------------------------
  const renderTypeDistChart = (records) => {
    const canvas = document.getElementById('type-dist-chart');
    if (!canvas || typeof window.Chart === 'undefined') return;

    const ctx = canvas.getContext('2d');
    const total = records.length;
    let imageOnly = 0;
    let multimodal = 0;

    records.forEach(r => {
      if (r.prediction_mode === 'multimodal') multimodal++;
      else imageOnly++;
    });

    const imagePct = total > 0 ? ((imageOnly / total) * 100).toFixed(1) : '0.0';
    const multimodalPct = total > 0 ? ((multimodal / total) * 100).toFixed(1) : '0.0';

    if (typeStatImageVal) typeStatImageVal.textContent = imageOnly.toString();
    if (typeStatImagePct) typeStatImagePct.textContent = `${imagePct}% of total`;
    if (typeStatMultimodalVal) typeStatMultimodalVal.textContent = multimodal++;
    if (typeStatMultimodalVal) typeStatMultimodalVal.textContent = (multimodal - 1).toString();
    if (typeStatMultimodalPct) typeStatMultimodalPct.textContent = `${multimodalPct}% of total`;

    if (typeDistChartInstance) {
      typeDistChartInstance.destroy();
    }

    typeDistChartInstance = new window.Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Image Only', 'Multimodal'],
        datasets: [{
          data: [imageOnly, multimodal - 1],
          backgroundColor: ['#f59e0b', '#7c3aed'],
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 10, font: { size: 10, weight: 'bold' } }
          }
        },
        cutout: '65%'
      }
    });
  };

  // --------------------------------------------------------------------------
  // Recent Predictions Table (Section 11)
  // --------------------------------------------------------------------------
  const renderRecentPredictionsTable = (records) => {
    if (!predictionsTableBody) return;

    if (tableCounter) {
      tableCounter.textContent = `Showing ${records.length} of ${allPredictions.length} records`;
    }

    if (records.length === 0) {
      predictionsTableBody.innerHTML = '';
      if (tableEmptyState) tableEmptyState.classList.remove('hidden');
      return;
    }
    if (tableEmptyState) tableEmptyState.classList.add('hidden');

    // Sort chronologically descending
    const sorted = [...records].sort((a, b) => {
      const ta = new Date(a.created_at || 0).getTime();
      const tb = new Date(b.created_at || 0).getTime();
      return tb - ta;
    });

    let html = '';
    sorted.forEach((r, idx) => {
      const dName = formatDiseaseLabel(r.predicted_disease);
      const confPct = Math.round((r.confidence || 0) * 100);
      const knowledge = DISEASE_KNOWLEDGE[r.predicted_disease] || { status: 'Unknown' };

      // Field identification & location
      const fieldInfo = r.field_id ? fieldLookup.get(r.field_id) : null;
      const displayFieldId = fieldInfo ? (fieldInfo.field_id || r.field_id) : (r.field_id || '—');
      const displayLocation = fieldInfo ? (fieldInfo.field_name || 'Bhimavaram') : '—';

      // Formatted Date
      let formattedDate = '—';
      if (r.created_at) {
        try {
          const d = new Date(r.created_at);
          formattedDate = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) + ' ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
        } catch {
          formattedDate = r.created_at.slice(0, 16);
        }
      }

      // Prediction Mode Badge
      const isMultimodal = r.prediction_mode === 'multimodal';
      const modeBadge = isMultimodal
        ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">Multimodal</span>`
        : `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">Image Only</span>`;

      // Thumbnail representation
      const thumbnailSVG = `<div class="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 text-xs shadow-2xs mx-auto">🌾</div>`;

      html += `
        <tr class="hover:bg-emerald-50/50 transition-colors cursor-pointer group" data-pred-id="${r.id}">
          <td class="py-3 px-3.5 text-center font-mono text-slate-400 group-hover:text-emerald-700 font-bold">${idx + 1}</td>
          <td class="py-3 px-3.5 font-medium text-slate-700 whitespace-nowrap">${formattedDate}</td>
          <td class="py-3 px-3.5 font-mono font-bold text-slate-800">${displayFieldId}</td>
          <td class="py-3 px-3.5">
            <div class="flex items-center gap-2">
              <span class="font-bold text-slate-900">${dName}</span>
              ${getBadgeHTML(knowledge.status)}
            </div>
          </td>
          <td class="py-3 px-3.5">${modeBadge}</td>
          <td class="py-3 px-3.5 font-mono font-bold text-slate-800">${confPct}%</td>
          <td class="py-3 px-3.5 text-center">${thumbnailSVG}</td>
          <td class="py-3 px-3.5 text-slate-600">${displayLocation}</td>
        </tr>
      `;
    });

    predictionsTableBody.innerHTML = html;

    // Attach row click listeners for instant diagnostic inspection
    predictionsTableBody.querySelectorAll('tr').forEach(row => {
      row.addEventListener('click', () => {
        const pid = row.dataset.predId;
        if (pid) {
          if (devSwitcher) devSwitcher.value = pid;
          loadInsight(pid);
          // Scroll smoothly to detail container
          const target = document.getElementById('diagnostic-deepdive-container');
          if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }
      });
    });
  };

  // --------------------------------------------------------------------------
  // CSV Export Engine (Section 11)
  // --------------------------------------------------------------------------
  const exportPredictionsToCSV = (records) => {
    if (!records || records.length === 0) {
      alert('No prediction records available to export.');
      return;
    }

    const headers = ['Record_Number', 'Prediction_ID', 'Date_UTC', 'Field_ID', 'Disease_Category', 'Prediction_Type', 'Confidence_Score', 'Model_Name', 'Farmer_Question'];
    const rows = [];

    records.forEach((r, idx) => {
      const fieldInfo = r.field_id ? fieldLookup.get(r.field_id) : null;
      const fid = fieldInfo ? (fieldInfo.field_id || r.field_id) : (r.field_id || '');
      const question = (r.farmer_question || '').replace(/"/g, '""');

      rows.push([
        idx + 1,
        `"${r.id}"`,
        `"${r.created_at || ''}"`,
        `"${fid}"`,
        `"${r.predicted_disease || ''}"`,
        `"${r.prediction_mode || ''}"`,
        (r.confidence || 0).toFixed(4),
        `"${r.model_name || ''}"`,
        `"${question}"`
      ].join(','));
    });

    const csvContent = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `crop_insights_predictions_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // --------------------------------------------------------------------------
  // Single-Record Diagnostic Inspection (Step 11J.4 Compatibility)
  // --------------------------------------------------------------------------
  const loadInsight = async (identifier) => {
    if (loadingState) loadingState.classList.remove('hidden');

    try {
      const baseUrl = getApiBaseUrl();
      let record = null;

      // Check if identifier is an existing cached prediction or UUID
      if (identifier && identifier !== 'insight-1' && identifier !== 'insight-photo-only') {
        record = allPredictions.find(p => p.id === identifier);
        if (!record) {
          const res = await fetch(`${baseUrl}/predictions/${encodeURIComponent(identifier)}`);
          if (res.ok) record = await res.json();
        }
      }

      // If identifier is mock 'insight-1' or 'insight-photo-only', map to real database record
      if (!record && allPredictions.length > 0) {
        if (identifier === 'insight-photo-only') {
          record = allPredictions.find(p => p.prediction_mode === 'image_only') || allPredictions[0];
        } else {
          record = allPredictions.find(p => p.prediction_mode === 'multimodal') || allPredictions[0];
        }
      }

      if (!record) {
        if (loadingState) loadingState.classList.add('hidden');
        return;
      }

      // Fetch satellite and field health data if prediction is linked to a field
      let fieldHealthData = null;
      let timeseriesData = null;
      const isMultimodal = record.prediction_mode === 'multimodal' || !!record.field_id;

      if (record.field_id) {
        try {
          const [hRes, tsRes] = await Promise.all([
            fetch(`${baseUrl}/fields/${encodeURIComponent(record.field_id)}/health`),
            fetch(`${baseUrl}/fields/${encodeURIComponent(record.field_id)}/timeseries`)
          ]);
          if (hRes.ok) fieldHealthData = await hRes.json();
          if (tsRes.ok) timeseriesData = await tsRes.json();
        } catch {
          // Graceful network fallback
        }
      }

      const diseaseKey = record.predicted_disease || 'normal';
      const knowledge = DISEASE_KNOWLEDGE[diseaseKey] || {
        name: formatDiseaseLabel(diseaseKey),
        status: record.is_healthy ? 'Healthy' : 'High Risk',
        symptoms: ['Foliar discoloration and necrotic tissue'],
        explanation: 'AI diagnostic classification based on convolutional visual feature extraction.'
      };

      const confPct = Math.round((record.confidence || 0) * 100);
      let leafInfluence = 'Medium';
      if (record.confidence >= 0.85) leafInfluence = 'High';
      else if (record.confidence < 0.60) leafInfluence = 'Low';

      let healthInfluence = 'N/A';
      if (isMultimodal && fieldHealthData?.changes_and_trends?.ndvi) {
        const dir = fieldHealthData.changes_and_trends.ndvi.direction;
        if (dir === 'decreasing') healthInfluence = 'High';
        else if (dir === 'stable') healthInfluence = 'Medium';
        else healthInfluence = 'Low';
      }

      let fieldInfluence = 'N/A';
      if (isMultimodal && fieldHealthData?.latest_indices) {
        const ndvi = fieldHealthData.latest_indices.ndvi;
        if (ndvi < 0.25) fieldInfluence = 'High';
        else if (ndvi < 0.40) fieldInfluence = 'Medium';
        else fieldInfluence = 'Low';
      }

      // Build satellite observation timeline
      const timelineItems = [];
      if (timeseriesData && Array.isArray(timeseriesData.timesteps)) {
        timeseriesData.timesteps.forEach((ts) => {
          timelineItems.push({
            date: ts.date ? ts.date : `Timestep ${ts.timestep}`,
            change: `NDVI: ${ts.ndvi.toFixed(3)} | NDRE: ${ts.ndre.toFixed(3)}`,
            desc: `Canopy vigor index observed by Sentinel-2 (GNDVI: ${ts.gndvi.toFixed(3)}).`
          });
        });
      }

      const insight = {
        condition: knowledge.name,
        confidence: `${confPct}% confidence`,
        status: knowledge.status,
        hasFieldData: isMultimodal,
        influences: {
          leafAppearance: leafInfluence,
          cropHealthChange: healthInfluence,
          fieldCondition: fieldInfluence
        },
        timeline: timelineItems,
        symptoms: knowledge.symptoms,
        explanation: knowledge.explanation
      };

      renderInsightDetails(insight);
    } catch (err) {
      console.error('Error loading crop insight:', err);
    } finally {
      if (loadingState) loadingState.classList.add('hidden');
    }
  };

  const renderInsightDetails = (insight) => {
    if (!insight) return;

    if (resCondition) resCondition.textContent = insight.condition;
    if (resConfidence) resConfidence.textContent = insight.confidence;
    if (resStatusContainer) resStatusContainer.innerHTML = getBadgeHTML(insight.status);

    if (inflLeaf) inflLeaf.innerHTML = getInfluenceBadgeHTML(insight.influences.leafAppearance);

    if (insight.hasFieldData) {
      if (inflHealthCard) inflHealthCard.classList.remove('hidden');
      if (inflFieldCard) inflFieldCard.classList.remove('hidden');
      if (photoOnlyMsg) photoOnlyMsg.classList.add('hidden');

      if (inflHealth) inflHealth.innerHTML = getInfluenceBadgeHTML(insight.influences.cropHealthChange);
      if (inflField) inflField.innerHTML = getInfluenceBadgeHTML(insight.influences.fieldCondition);

      if (timelineContainer) timelineContainer.classList.remove('hidden');
      if (timeline) {
        timeline.innerHTML = '';
        if (insight.timeline && insight.timeline.length > 0) {
          insight.timeline.forEach(t => {
            timeline.innerHTML += `
              <div class="relative">
                <div class="absolute -left-[23px] top-1 w-3 h-3 bg-[#0d5c38] rounded-full ring-4 ring-white"></div>
                <p class="text-xs font-bold text-gray-500">${t.date}</p>
                <h4 class="font-bold text-[#0d5c38] mt-0.5">${t.change}</h4>
                <p class="text-xs text-gray-600 mt-1">${t.desc}</p>
              </div>
            `;
          });
        } else {
          timeline.innerHTML = '<p class="text-xs text-gray-500">No historical satellite timesteps available.</p>';
        }
      }
    } else {
      if (inflHealthCard) inflHealthCard.classList.add('hidden');
      if (inflFieldCard) inflFieldCard.classList.add('hidden');
      if (photoOnlyMsg) photoOnlyMsg.classList.remove('hidden');
      if (timelineContainer) timelineContainer.classList.add('hidden');
    }

    if (symptoms) {
      symptoms.innerHTML = '';
      if (insight.symptoms) {
        insight.symptoms.forEach(s => {
          symptoms.innerHTML += `
            <li class="flex items-start">
              <svg class="w-4 h-4 text-emerald-600 mr-2 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              <span class="text-slate-800 font-medium">${s}</span>
            </li>
          `;
        });
      }
    }

    if (explanation) explanation.textContent = insight.explanation;
    if (contentContainer) contentContainer.classList.remove('hidden');
  };

  // --------------------------------------------------------------------------
  // Event Listeners
  // --------------------------------------------------------------------------
  if (devSwitcher) {
    devSwitcher.addEventListener('change', (e) => {
      loadInsight(e.target.value);
    });
  }

  if (periodFilterSelect) {
    periodFilterSelect.addEventListener('change', (e) => {
      activeFilters.period = e.target.value;
      refreshAnalytics();
    });
  }

  if (fieldFilterSelect) {
    fieldFilterSelect.addEventListener('change', (e) => {
      activeFilters.field = e.target.value;
      refreshAnalytics();
    });
  }

  if (tableSearchInput) {
    tableSearchInput.addEventListener('input', (e) => {
      activeFilters.search = e.target.value;
      refreshAnalytics();
    });
  }

  if (tableDateFilter) {
    tableDateFilter.addEventListener('change', (e) => {
      activeFilters.date = e.target.value;
      refreshAnalytics();
    });
  }

  if (btnResetFilters) {
    btnResetFilters.addEventListener('click', () => {
      activeFilters.search = '';
      activeFilters.date = '';
      if (tableSearchInput) tableSearchInput.value = '';
      if (tableDateFilter) tableDateFilter.value = '';
      refreshAnalytics();
    });
  }

  if (btnExportCsv) {
    btnExportCsv.addEventListener('click', () => {
      const filtered = getFilteredPredictions();
      exportPredictionsToCSV(filtered);
    });
  }

  if (fieldCountFilter) {
    fieldCountFilter.addEventListener('change', (e) => {
      activeFilters.fieldFilterMode = e.target.value;
      renderFieldPredictionChart(getFilteredPredictions());
    });
  }

  if (btnGranularityMonthly && btnGranularityDaily) {
    btnGranularityMonthly.addEventListener('click', () => {
      activeFilters.trendGranularity = 'monthly';
      btnGranularityMonthly.classList.add('bg-white', 'text-emerald-800', 'shadow-xs');
      btnGranularityMonthly.classList.remove('text-slate-600');
      btnGranularityDaily.classList.remove('bg-white', 'text-emerald-800', 'shadow-xs');
      btnGranularityDaily.classList.add('text-slate-600');
      renderPredictionTrendChart(getFilteredPredictions());
    });

    btnGranularityDaily.addEventListener('click', () => {
      activeFilters.trendGranularity = 'daily';
      btnGranularityDaily.classList.add('bg-white', 'text-emerald-800', 'shadow-xs');
      btnGranularityDaily.classList.remove('text-slate-600');
      btnGranularityMonthly.classList.remove('bg-white', 'text-emerald-800', 'shadow-xs');
      btnGranularityMonthly.classList.add('text-slate-600');
      renderPredictionTrendChart(getFilteredPredictions());
    });
  }

  // Expose global methods
  window.loadCropInsight = loadInsight;
  window.refreshCropInsights = refreshAnalytics;

  // Initialize data on page load
  fetchAllData();
});
