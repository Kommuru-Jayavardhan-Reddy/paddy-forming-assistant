// ============================================================================
// STEP 5 / 11C: REAL DISEASE DETECTION INTEGRATION (PREMIUM UI/UX CONTROLLER)
// Connects leaf photo upload to the live FastAPI backend (EfficientNet-B4).
// Sends FormData with 'file' field to http://127.0.0.1:8000/predict
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  // Central API URL resolver using centralized config
  const getApiUrl = () => {
    const base = (typeof window !== 'undefined' && window.API_BASE_URL)
      ? String(window.API_BASE_URL).replace(/\/+$/, '')
      : 'http://127.0.0.1:8000';
    return `${base}/predict`;
  };

  const sanitizeMessage = (msg) => {
    if (!msg || typeof msg !== 'string') return '';
    return msg
      .replace(/[A-Za-z]:\\[^"'\n\r\t<>]*/g, '[internal server path]')
      .replace(/\/[\w.-]+(\/[\w.-]+)+/g, '[internal server path]');
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // 13 Disease classes knowledge base for accurate agricultural descriptions
  const DISEASE_INFO = {
    bacterial_leaf_blight: {
      displayName: 'Bacterial Leaf Blight',
      badgeType: 'risk',
      badgeText: 'High Risk',
      symptoms: 'Water-soaked lesions on leaf margins and tips that turn yellow to grayish-white with characteristic wavy edges.',
      action: 'Avoid excessive nitrogen fertilization. Ensure good field drainage, avoid clipping seedlings, and apply recommended copper-based bactericides if advised locally.'
    },
    bacterial_leaf_streak: {
      displayName: 'Bacterial Leaf Streak',
      badgeType: 'attention',
      badgeText: 'Needs Attention',
      symptoms: 'Narrow, yellowish-brown translucent streaks between leaf veins that may exude tiny amber-colored bacterial droplets.',
      action: 'Manage nitrogen application carefully. Drain excess stagnant water to reduce canopy humidity and apply recommended protective treatments.'
    },
    bacterial_panicle_blight: {
      displayName: 'Bacterial Panicle Blight',
      badgeType: 'risk',
      badgeText: 'High Risk',
      symptoms: 'Discolored florets turning gray-brown with dark borders; aborted grains leaving affected panicles standing upright.',
      action: 'Plant certified clean seed. Avoid excessive nitrogen fertilizer during booting/heading and apply preventive treatments during early flowering.'
    },
    blast: {
      displayName: 'Rice Blast',
      badgeType: 'risk',
      badgeText: 'High Risk',
      symptoms: 'Spindle-shaped or diamond-shaped lesions with grayish-white centers and dark brown to reddish margins.',
      action: 'Apply recommended systemic fungicides (such as tricyclazole or isoprothiolane). Avoid high nitrogen doses and maintain shallow water in the field.'
    },
    brown_spot: {
      displayName: 'Brown Spot',
      badgeType: 'attention',
      badgeText: 'Needs Attention',
      symptoms: 'Small, circular to oval dark-brown spots with yellow halos evenly distributed across the leaf blade.',
      action: 'Improve soil fertility by providing balanced NPK nutrients (especially potassium and zinc). Treat seeds with fungicide before subsequent planting.'
    },
    dead_heart: {
      displayName: 'Dead Heart (Stem Borer)',
      badgeType: 'risk',
      badgeText: 'High Risk',
      symptoms: 'Drying and withering of the central tiller shoot caused by internal larvae feeding, while outer leaves may temporarily remain green.',
      action: 'Install pheromone traps for pest monitoring. Conserve beneficial predators and apply recommended insect pest control at the egg-hatch stage.'
    },
    downy_mildew: {
      displayName: 'Downy Mildew',
      badgeType: 'attention',
      badgeText: 'Needs Attention',
      symptoms: 'Stunted seedlings with pale yellowish chlorotic blotches or twisting, curling, and thickening of leaf blades.',
      action: 'Ensure adequate field drainage to avoid prolonged waterlogging. Remove severely infected hills from the nursery.'
    },
    hispa: {
      displayName: 'Rice Hispa',
      badgeType: 'attention',
      badgeText: 'Needs Attention',
      symptoms: 'White parallel translucent streaks where adult beetles scraped green leaf tissue, leaving only the lower epidermal layer.',
      action: 'Sweep net to reduce adult beetle populations. Clip infested leaf tips before transplanting, or apply recommended agricultural insecticides.'
    },
    leaf_scald: {
      displayName: 'Leaf Scald',
      badgeType: 'attention',
      badgeText: 'Needs Attention',
      symptoms: 'Zonate, oblong chevron-patterned lesions extending from leaf tips with alternating light and dark brown bands.',
      action: 'Use balanced fertilizer applications. Avoid excess nitrogen, maintain plant spacing for ventilation, and apply protective fungicides if necessary.'
    },
    leaf_smut: {
      displayName: 'Leaf Smut',
      badgeType: 'attention',
      badgeText: 'Needs Attention',
      symptoms: 'Small, raised, angular black spots or pustules scattered on mature leaves, covered by the leaf epidermis.',
      action: 'Leaf smut usually causes low yield impact. Maintain balanced crop nutrition and avoid excessive nitrogen fertilizer.'
    },
    normal: {
      displayName: 'Normal / Healthy Crop',
      badgeType: 'healthy',
      badgeText: 'Healthy',
      symptoms: 'Leaves exhibit uniform green pigmentation, healthy structure, and no visible fungal spots or pest damage.',
      action: 'Maintain your current watering and nutrient schedule. Continue regular field scouting every few days.'
    },
    sheath_blight: {
      displayName: 'Sheath Blight',
      badgeType: 'risk',
      badgeText: 'High Risk',
      symptoms: 'Oval or irregular greenish-gray water-soaked spots on leaf sheaths near the water level that progress upward.',
      action: 'Ensure appropriate hill spacing for air flow, avoid excessive nitrogen, and apply recommended fungicides (e.g., validamycin or azoxystrobin).'
    },
    tungro: {
      displayName: 'Rice Tungro Disease',
      badgeType: 'risk',
      badgeText: 'High Risk',
      symptoms: 'Distinct yellow to orange discoloration of leaves starting from the tip downward, accompanied by stunted tillers (viral infection spread by green leafhopper).',
      action: 'Manage the green leafhopper vector with recommended insecticides. Rogue out infected hills promptly and rotate with resistant varieties.'
    }
  };

  // Views & Containers
  const viewEmpty = document.getElementById('detection-view-empty');
  const viewLoading = document.getElementById('detection-view-loading');
  const viewBadPhoto = document.getElementById('detection-view-bad-photo');
  const viewResult = document.getElementById('detection-view-result');

  // Preview Containers
  const selectedImageEmpty = document.getElementById('selected-image-empty');
  const selectedImagePreviewContainer = document.getElementById('selected-image-preview-container');
  const selectedFileName = document.getElementById('selected-file-name');
  const selectedFileMeta = document.getElementById('selected-file-meta');
  const selectedFileSize = document.getElementById('selected-file-size');

  // Interactive Buttons & Inputs
  const photoInput = document.getElementById('leaf-photo-input');
  const dropzone = document.getElementById('detection-dropzone');
  const btnBrowseFiles = document.getElementById('btn-browse-files');
  const btnChooseAction = document.getElementById('btn-choose-action');
  const btnAnalyzeAction = document.getElementById('btn-analyze-action');
  const analyzeBtnText = document.getElementById('analyze-btn-text');
  const analyzeActionIcon = document.getElementById('analyze-action-icon');
  const analyzeActionSpinner = document.getElementById('analyze-action-spinner');
  const btnReplaceImage = document.getElementById('btn-replace-image');
  const btnRemoveImage = document.getElementById('btn-remove-image');
  const btnBadPhotoRetake = document.getElementById('btn-bad-photo-retake');
  const btnErrorRetry = document.getElementById('btn-error-retry');
  const btnDetectAnother = document.getElementById('btn-detect-another');

  // Compatibility / Legacy triggers
  const btnTakePhoto = document.getElementById('btn-take-photo');
  const btnChooseGallery = document.getElementById('btn-choose-gallery');
  const btnUsePhoto = document.getElementById('btn-use-photo');
  const btnRetakePhoto = document.getElementById('btn-retake-photo');

  // Image Elements
  const previewImg = document.getElementById('preview-image');
  const resultImg = document.getElementById('result-image');
  const resultHighlight = document.getElementById('result-highlight');

  // Result Elements
  const resName = document.getElementById('result-disease-name');
  const resConfidence = document.getElementById('result-confidence');
  const resBadgeContainer = document.getElementById('result-badge-container');
  const resTop3Container = document.getElementById('result-top3-container');
  const resSymptoms = document.getElementById('result-symptoms');
  const resAction = document.getElementById('result-action');
  const resPredictionId = document.getElementById('result-prediction-id');

  // Summary Metrics Elements
  const summaryDiseaseName = document.getElementById('summary-disease-name');
  const summaryConfidence = document.getElementById('summary-confidence');

  // Workflow Progress Indicators
  const stepNode1 = document.getElementById('step-node-1');
  const stepLabel1 = document.getElementById('step-label-1');
  const stepLine1 = document.getElementById('step-line-1');
  const stepNode2 = document.getElementById('step-node-2');
  const stepLabel2 = document.getElementById('step-label-2');
  const stepLine2 = document.getElementById('step-line-2');
  const stepNode3 = document.getElementById('step-node-3');
  const stepLabel3 = document.getElementById('step-label-3');

  // Error Elements
  const errorTitle = document.getElementById('error-view-title');
  const errorMessage = document.getElementById('error-view-message');
  const errorTips = document.getElementById('error-view-tips');

  // State Management & Race Condition Guards
  let currentFile = null;
  let currentObjectUrl = null;
  let isAnalyzing = false;
  let currentPredictionRequestId = 0;
  let activeAbortController = null;

  // Cleanup helper for object URLs
  const cleanupObjectUrl = () => {
    if (currentObjectUrl) {
      URL.revokeObjectURL(currentObjectUrl);
      currentObjectUrl = null;
    }
  };

  // Workflow Step State Updater
  const updateWorkflowStep = (step) => {
    // Step 1: Upload leaf image
    // Step 2: Analyze with AI
    // Step 3: Review diagnosis
    if (step === 1) {
      if (stepNode1) {
        stepNode1.className = 'w-8 h-8 rounded-full bg-[#15803d] text-white font-bold text-xs flex items-center justify-center shadow-xs transition-all duration-300';
      }
      if (stepLabel1) stepLabel1.className = 'text-xs font-bold text-slate-900 mt-1.5 whitespace-nowrap';
      if (stepLine1) stepLine1.className = 'w-10 sm:w-16 h-0.5 bg-slate-200 transition-all duration-300 -mt-6';
      
      if (stepNode2) {
        stepNode2.className = 'w-8 h-8 rounded-full border-2 border-slate-300 bg-white text-slate-600 font-bold text-xs flex items-center justify-center shadow-xs transition-all duration-300';
      }
      if (stepLabel2) stepLabel2.className = 'text-xs font-semibold text-slate-500 mt-1.5 whitespace-nowrap';
      if (stepLine2) stepLine2.className = 'w-10 sm:w-16 h-0.5 bg-slate-200 transition-all duration-300 -mt-6';

      if (stepNode3) {
        stepNode3.className = 'w-8 h-8 rounded-full border-2 border-slate-300 bg-white text-slate-600 font-bold text-xs flex items-center justify-center shadow-xs transition-all duration-300';
      }
      if (stepLabel3) stepLabel3.className = 'text-xs font-semibold text-slate-500 mt-1.5 whitespace-nowrap';
    } else if (step === 2) {
      if (stepNode1) {
        stepNode1.className = 'w-8 h-8 rounded-full bg-[#15803d] text-white font-bold text-xs flex items-center justify-center shadow-xs transition-all duration-300';
      }
      if (stepLine1) stepLine1.className = 'w-10 sm:w-16 h-0.5 bg-[#15803d] transition-all duration-300 -mt-6';

      if (stepNode2) {
        stepNode2.className = 'w-8 h-8 rounded-full bg-[#15803d] text-white font-bold text-xs flex items-center justify-center shadow-xs transition-all duration-300';
      }
      if (stepLabel2) stepLabel2.className = 'text-xs font-bold text-slate-900 mt-1.5 whitespace-nowrap';
      if (stepLine2) stepLine2.className = 'w-10 sm:w-16 h-0.5 bg-slate-200 transition-all duration-300 -mt-6';

      if (stepNode3) {
        stepNode3.className = 'w-8 h-8 rounded-full border-2 border-slate-300 bg-white text-slate-600 font-bold text-xs flex items-center justify-center shadow-xs transition-all duration-300';
      }
      if (stepLabel3) stepLabel3.className = 'text-xs font-semibold text-slate-500 mt-1.5 whitespace-nowrap';
    } else if (step === 3) {
      if (stepNode1) {
        stepNode1.className = 'w-8 h-8 rounded-full bg-[#15803d] text-white font-bold text-xs flex items-center justify-center shadow-xs transition-all duration-300';
      }
      if (stepLine1) stepLine1.className = 'w-10 sm:w-16 h-0.5 bg-[#15803d] transition-all duration-300 -mt-6';

      if (stepNode2) {
        stepNode2.className = 'w-8 h-8 rounded-full bg-[#15803d] text-white font-bold text-xs flex items-center justify-center shadow-xs transition-all duration-300';
      }
      if (stepLine2) stepLine2.className = 'w-10 sm:w-16 h-0.5 bg-[#15803d] transition-all duration-300 -mt-6';

      if (stepNode3) {
        stepNode3.className = 'w-8 h-8 rounded-full bg-[#15803d] text-white font-bold text-xs flex items-center justify-center shadow-xs transition-all duration-300';
      }
      if (stepLabel3) stepLabel3.className = 'text-xs font-bold text-slate-900 mt-1.5 whitespace-nowrap';
    }
  };

  // Collection of workspace views for clean and mutually exclusive state switching
  const allWorkspaceViews = [
    { el: viewEmpty, name: 'empty' },
    { el: viewLoading, name: 'loading' },
    { el: viewBadPhoto, name: 'error' },
    { el: viewResult, name: 'result' }
  ];

  // Dedicated helper to ensure loading state is completely extinguished
  const hideLoading = () => {
    if (viewLoading) {
      viewLoading.classList.add('hidden');
      viewLoading.style.display = 'none';
    }
  };

  // Helper to switch right workspace views with clean inline-style & class hygiene
  const showWorkspaceState = (state) => {
    // state: 'empty' | 'loading' | 'error' | 'result'
    allWorkspaceViews.forEach(({ el, name }) => {
      if (!el) return;
      if (name === state) {
        el.classList.remove('hidden');
        el.style.display = 'flex';
      } else {
        el.classList.add('hidden');
        el.style.display = 'none';
      }
    });
  };

  const formatClassName = (rawClass) => {
    if (!rawClass) return 'Unknown Condition';
    if (DISEASE_INFO[rawClass]) return DISEASE_INFO[rawClass].displayName;
    return rawClass.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  };

  const getBadgeHTML = (type, text) => {
    if (type === 'healthy') {
      return `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">${text || 'Healthy'}</span>`;
    }
    if (type === 'attention') {
      return `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">${text || 'Needs Attention'}</span>`;
    }
    if (type === 'risk') {
      return `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">${text || 'High Risk'}</span>`;
    }
    return `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-300">${text || 'Unknown'}</span>`;
  };

  // Display structured error states
  const showInvalidFileError = (msg) => {
    hideLoading();
    if (errorTitle) errorTitle.textContent = 'Invalid Image File';
    if (errorMessage) errorMessage.textContent = msg || 'Please select a valid JPG, JPEG, or PNG image of a paddy leaf.';
    if (errorTips) {
      errorTips.innerHTML = `
        <p class="font-bold text-amber-900 mb-1">Supported File Requirements:</p>
        <ul class="text-amber-800 space-y-1 text-xs">
          <li>• Formats accepted: <strong>.jpg, .jpeg, .png, .webp</strong></li>
          <li>• Maximum file size: <strong>5 MB</strong> (up to 10 MB accepted)</li>
          <li>• Make sure the image clearly captures a rice / paddy leaf.</li>
        </ul>
      `;
    }
    if (btnErrorRetry) btnErrorRetry.classList.add('hidden');
    showWorkspaceState('error');
  };

  const showNetworkError = (msg) => {
    hideLoading();
    if (errorTitle) errorTitle.textContent = 'AI Server Connection Failed';
    if (errorMessage) errorMessage.textContent = msg || 'Could not connect to the AI model server at http://127.0.0.1:8000.';
    if (errorTips) {
      errorTips.innerHTML = `
        <p class="font-bold text-amber-900 mb-1">Backend Connection Checklist:</p>
        <ul class="text-amber-800 space-y-1 text-xs">
          <li>• Confirm FastAPI backend is active on <code class="bg-amber-100 px-1 py-0.5 rounded font-mono text-[11px]">http://127.0.0.1:8000</code></li>
          <li>• Check backend terminal logs for model loading status.</li>
          <li>• Confirm port 8000 is not blocked by local firewall.</li>
        </ul>
      `;
    }
    if (btnErrorRetry) btnErrorRetry.classList.remove('hidden');
    showWorkspaceState('error');
  };

  const showApiError = (status, detail) => {
    hideLoading();
    if (errorTitle) errorTitle.textContent = 'Model Prediction Error';
    if (errorMessage) errorMessage.textContent = `Server responded with HTTP ${status}.`;
    if (errorTips) {
      errorTips.innerHTML = `
        <p class="font-bold text-amber-900 mb-1">Server Details:</p>
        <p class="text-amber-900 text-xs font-mono bg-white/70 p-2 rounded border border-amber-200 break-words mb-2">${detail || 'No detailed error message was returned.'}</p>
        <ul class="text-amber-800 space-y-1 text-xs">
          <li>• <strong>503 Service Unavailable:</strong> Model weights or checkpoint are still loading.</li>
          <li>• <strong>400 Bad Request:</strong> The uploaded image could not be decoded.</li>
        </ul>
      `;
    }
    if (btnErrorRetry) btnErrorRetry.classList.remove('hidden');
    showWorkspaceState('error');
  };

  // Render Top 3 Predictions list with percentage bars
  const renderTop3 = (top3) => {
    if (!resTop3Container) return;

    if (!top3 || !Array.isArray(top3) || top3.length === 0) {
      resTop3Container.innerHTML = '<p class="text-xs text-slate-400">No prediction ranking data returned.</p>';
      return;
    }

    resTop3Container.innerHTML = top3.map((item, index) => {
      const className = item.disease || item.class || item.name || '';
      const prob = typeof item.probability === 'number' ? item.probability : (typeof item.confidence === 'number' ? item.confidence : 0);
      const conf = prob <= 1.0 ? prob * 100 : prob;
      const isTop = index === 0;
      const formattedName = formatClassName(className);
      const percentStr = `${conf.toFixed(1)}%`;
      const barColor = isTop ? 'bg-[#15803d]' : 'bg-slate-400';
      const textColor = isTop ? 'text-[#15803d] font-bold' : 'text-slate-700 font-medium';

      return `
        <div class="flex items-center justify-between text-xs py-2 px-3 rounded-lg ${isTop ? 'bg-emerald-50/90 border border-emerald-200' : 'bg-slate-50 border border-slate-200/60'}">
          <div class="flex items-center space-x-2.5 min-w-0 pr-2">
            <span class="w-5 h-5 rounded-full ${isTop ? 'bg-[#15803d] text-white' : 'bg-slate-200 text-slate-600'} text-[11px] font-bold flex items-center justify-center flex-shrink-0">
              ${index + 1}
            </span>
            <span class="${textColor} truncate">${formattedName}</span>
          </div>
          <div class="flex items-center space-x-2.5 flex-shrink-0">
            <div class="w-20 sm:w-28 bg-slate-200 rounded-full h-1.5 overflow-hidden">
              <div class="${barColor} h-full rounded-full transition-all duration-500" style="width: ${Math.min(100, Math.max(0, conf))}%"></div>
            </div>
            <span class="text-xs font-bold ${isTop ? 'text-[#15803d]' : 'text-slate-600'} w-12 text-right">${percentStr}</span>
          </div>
        </div>
      `;
    }).join('');
  };

  // Render real prediction results from backend
  const renderPredictionResult = (data) => {
    // Guarantees loading state is completely extinguished before revealing results
    hideLoading();

    const rawClass = data.disease || data.predicted_class || data.predicted_disease || 'unknown';
    const rawConfidence = typeof data.confidence === 'number' ? data.confidence : 0;
    const confidenceVal = rawConfidence <= 1.0 ? rawConfidence * 100 : rawConfidence;
    const top3 = data.top3 || data.top_3 || data.top_3_predictions || [];

    const info = DISEASE_INFO[rawClass] || {
      displayName: formatClassName(rawClass),
      badgeType: rawClass === 'normal' ? 'healthy' : 'attention',
      badgeText: rawClass === 'normal' ? 'Healthy' : 'Needs Attention',
      symptoms: `Observed leaf abnormalities consistent with ${formatClassName(rawClass)}.`,
      action: 'Consult local agricultural extension specialists for tailored field intervention advice.'
    };

    // Update Result Text
    if (resName) resName.textContent = info.displayName;

    let confCategory = 'Low confidence';
    if (confidenceVal >= 80) confCategory = 'High confidence';
    else if (confidenceVal >= 50) confCategory = 'Moderate confidence';

    const formattedConf = `${confidenceVal.toFixed(1)}% — ${confCategory}`;
    if (resConfidence) resConfidence.textContent = formattedConf;

    if (resBadgeContainer) {
      resBadgeContainer.innerHTML = getBadgeHTML(info.badgeType, info.badgeText);
    }

    // Update bottom summary cards
    if (summaryDiseaseName) summaryDiseaseName.textContent = info.displayName;
    if (summaryConfidence) summaryConfidence.textContent = `${confidenceVal.toFixed(1)}%`;

    // Render Real Top 3 Ranking
    renderTop3(top3);

    // Update symptoms & agronomic recommendations
    if (resSymptoms) resSymptoms.textContent = info.symptoms;
    if (resAction) resAction.textContent = info.action;

    // Display prediction ID if present
    if (data.prediction_id && resPredictionId) {
      resPredictionId.innerHTML = `ID: <code class="font-mono text-slate-700">${data.prediction_id.slice(0, 8)}...</code>`;
      resPredictionId.classList.remove('hidden');
    }

    if (resultHighlight) {
      resultHighlight.classList.add('hidden');
    }

    // Advance workflow indicator to Step 3
    updateWorkflowStep(3);

    // Switch workspace display strictly to 'result'
    showWorkspaceState('result');
  };

  // Perform genuine inference request via FastAPI /predict
  const analyzeLeafPhoto = async () => {
    // Prevent duplicate submission triggers
    if (isAnalyzing) return;

    if (!currentFile) {
      showInvalidFileError('No photo selected. Please choose a leaf image first.');
      return;
    }

    // Validate MIME type & file extension
    const validMimes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    const validExts = /\.(jpe?g|png|webp)$/i;
    if (!validMimes.includes(currentFile.type) && !validExts.test(currentFile.name)) {
      showInvalidFileError(`Selected file "${currentFile.name}" is not supported. Please upload a JPG, JPEG, PNG, or WebP image.`);
      return;
    }

    if (currentFile.size === 0) {
      showInvalidFileError('Selected image file is empty (0 bytes). Please choose a valid image.');
      return;
    }

    if (currentFile.size > 10 * 1024 * 1024) {
      showInvalidFileError('Image file is too large. Maximum supported size is 10 MB.');
      return;
    }

    // Track this specific request to prevent race conditions
    isAnalyzing = true;
    const requestId = ++currentPredictionRequestId;

    // Cancel any previous in-flight controller
    if (activeAbortController) {
      try { activeAbortController.abort(); } catch {}
      activeAbortController = null;
    }
    activeAbortController = new AbortController();

    // Set UI to loading state
    if (btnAnalyzeAction) {
      btnAnalyzeAction.disabled = true;
      btnAnalyzeAction.className = 'w-full py-3 px-4 rounded-xl bg-emerald-700 text-white text-sm font-bold flex items-center justify-center space-x-2 shadow-sm cursor-not-allowed opacity-90';
    }
    if (analyzeBtnText) analyzeBtnText.textContent = 'Analyzing Image...';
    if (analyzeActionIcon) analyzeActionIcon.classList.add('hidden');
    if (analyzeActionSpinner) analyzeActionSpinner.classList.remove('hidden');

    if (btnUsePhoto) {
      btnUsePhoto.disabled = true;
    }

    // Show workspace loading view exclusively
    showWorkspaceState('loading');

    // Build multipart/form-data request using the expected 'file' field name
    const formData = new FormData();
    formData.append('file', currentFile, currentFile.name);

    const timeoutId = setTimeout(() => {
      if (activeAbortController) activeAbortController.abort();
    }, 35000);

    try {
      const response = await fetch(getApiUrl(), {
        method: 'POST',
        body: formData,
        signal: activeAbortController.signal
      });
      clearTimeout(timeoutId);

      // Discard stale response if a newer action occurred
      if (requestId !== currentPredictionRequestId) return;

      if (!response.ok) {
        let errorDetail = '';
        try {
          const errData = await response.json();
          errorDetail = errData.detail || errData.error || '';
        } catch {
          errorDetail = await response.text();
        }
        showApiError(response.status, sanitizeMessage(errorDetail));
        return;
      }

      const result = await response.json();
      const detectedDisease = result.disease || result.predicted_class || result.predicted_disease;

      if (!result || typeof detectedDisease !== 'string') {
        showApiError(response.status, 'Invalid response format received from prediction API.');
        return;
      }

      renderPredictionResult(result);

    } catch (err) {
      clearTimeout(timeoutId);
      if (requestId !== currentPredictionRequestId) return;

      console.error('Prediction API request error:', err);
      if (err && err.name === 'AbortError') {
        showNetworkError('The model prediction request timed out after 35 seconds. Please check that the server is responsive and try again.');
      } else {
        showNetworkError(`Unable to connect to the prediction server at ${getApiUrl()}. Please verify the backend service is running.`);
      }
    } finally {
      if (requestId === currentPredictionRequestId) {
        isAnalyzing = false;
        activeAbortController = null;
        hideLoading();

        if (btnAnalyzeAction && currentFile) {
          btnAnalyzeAction.disabled = false;
          btnAnalyzeAction.className = 'w-full py-3 px-4 rounded-xl bg-[#15803d] hover:bg-[#166534] text-white text-sm font-bold flex items-center justify-center space-x-2 shadow-sm transition-all active:scale-[0.99] cursor-pointer';
        }
        if (analyzeBtnText) analyzeBtnText.textContent = 'Analyze Image';
        if (analyzeActionIcon) analyzeActionIcon.classList.remove('hidden');
        if (analyzeActionSpinner) analyzeActionSpinner.classList.add('hidden');

        if (btnUsePhoto) {
          btnUsePhoto.disabled = false;
        }
      }
    }
  };

  // Helper to select a file and render preview with full state reset
  const handleSelectedFile = (file) => {
    if (!file) return;

    // Invalidate pending prediction request to prevent race conditions
    currentPredictionRequestId++;
    if (activeAbortController) {
      try { activeAbortController.abort(); } catch {}
      activeAbortController = null;
    }
    isAnalyzing = false;
    hideLoading();

    const validExts = /\.(jpe?g|png|webp)$/i;
    const validMimes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!validMimes.includes(file.type) && !validExts.test(file.name)) {
      showInvalidFileError(`"${file.name}" is not a supported format. Please upload a JPG, PNG, or WebP image.`);
      return;
    }

    if (file.size === 0) {
      showInvalidFileError('The selected image file is empty (0 bytes). Please select a valid photo.');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      showInvalidFileError(`Image file size (${formatFileSize(file.size)}) exceeds the maximum 10 MB limit.`);
      return;
    }

    cleanupObjectUrl();
    currentFile = file;
    currentObjectUrl = URL.createObjectURL(file);

    // Update Preview Image
    if (previewImg) previewImg.src = currentObjectUrl;
    if (resultImg) resultImg.src = currentObjectUrl;

    // Update File Metadata
    if (selectedFileName) selectedFileName.textContent = file.name;
    if (selectedFileMeta) selectedFileMeta.textContent = `${formatFileSize(file.size)} • Ready for analysis`;
    if (selectedFileSize) {
      selectedFileSize.textContent = formatFileSize(file.size);
      selectedFileSize.classList.remove('hidden');
    }

    // Toggle Preview Containers
    if (selectedImageEmpty) {
      selectedImageEmpty.classList.add('hidden');
      selectedImageEmpty.style.display = 'none';
    }
    if (selectedImagePreviewContainer) {
      selectedImagePreviewContainer.classList.remove('hidden');
      selectedImagePreviewContainer.style.display = 'block';
    }

    // Enable "Analyze Image" button
    if (btnAnalyzeAction) {
      btnAnalyzeAction.disabled = false;
      btnAnalyzeAction.className = 'w-full py-3 px-4 rounded-xl bg-[#15803d] hover:bg-[#166534] text-white text-sm font-bold flex items-center justify-center space-x-2 shadow-sm transition-all active:scale-[0.99] cursor-pointer';
    }
    if (analyzeBtnText) analyzeBtnText.textContent = 'Analyze Image';
    if (analyzeActionIcon) analyzeActionIcon.classList.remove('hidden');
    if (analyzeActionSpinner) analyzeActionSpinner.classList.add('hidden');

    // Update Workflow Progress to Step 2
    updateWorkflowStep(2);

    // Clear previous prediction results & error, return workspace to clean empty ready state
    if (summaryDiseaseName) summaryDiseaseName.textContent = '—';
    if (summaryConfidence) summaryConfidence.textContent = '—';
    if (resName) resName.textContent = '—';
    if (resConfidence) resConfidence.textContent = '—';
    if (resBadgeContainer) resBadgeContainer.innerHTML = '';
    if (resTop3Container) resTop3Container.innerHTML = '';
    if (resSymptoms) resSymptoms.textContent = '';
    if (resAction) resAction.textContent = '';
    if (resPredictionId) resPredictionId.classList.add('hidden');

    showWorkspaceState('empty');
  };

  // Reset / Clear state completely to initial IDLE state
  const handleReset = () => {
    // Invalidate pending prediction request
    currentPredictionRequestId++;
    if (activeAbortController) {
      try { activeAbortController.abort(); } catch {}
      activeAbortController = null;
    }
    isAnalyzing = false;
    hideLoading();
    cleanupObjectUrl();
    currentFile = null;

    if (photoInput) photoInput.value = '';
    if (previewImg) previewImg.src = '';
    if (resultImg) resultImg.src = '';

    // Reset Selected Image preview containers
    if (selectedImagePreviewContainer) {
      selectedImagePreviewContainer.classList.add('hidden');
      selectedImagePreviewContainer.style.display = 'none';
    }
    if (selectedImageEmpty) {
      selectedImageEmpty.classList.remove('hidden');
      selectedImageEmpty.style.display = 'flex';
    }
    if (selectedFileSize) selectedFileSize.classList.add('hidden');

    // Reset summary cards
    if (summaryDiseaseName) summaryDiseaseName.textContent = '—';
    if (summaryConfidence) summaryConfidence.textContent = '—';
    if (resName) resName.textContent = '—';
    if (resConfidence) resConfidence.textContent = '—';
    if (resBadgeContainer) resBadgeContainer.innerHTML = '';
    if (resTop3Container) resTop3Container.innerHTML = '';
    if (resSymptoms) resSymptoms.textContent = '';
    if (resAction) resAction.textContent = '';
    if (resPredictionId) resPredictionId.classList.add('hidden');

    // Disable "Analyze Image" button
    if (btnAnalyzeAction) {
      btnAnalyzeAction.disabled = true;
      btnAnalyzeAction.className = 'w-full py-3 px-4 rounded-xl bg-slate-200 text-slate-400 text-sm font-bold flex items-center justify-center space-x-2 transition-all cursor-not-allowed';
    }
    if (analyzeBtnText) analyzeBtnText.textContent = 'Analyze Image';
    if (analyzeActionIcon) analyzeActionIcon.classList.remove('hidden');
    if (analyzeActionSpinner) analyzeActionSpinner.classList.add('hidden');

    // Return to Step 1 in workflow progress
    updateWorkflowStep(1);

    // Return right workspace to empty state
    showWorkspaceState('empty');
  };

  // Open file selector helper
  const triggerFileSelect = () => {
    if (isAnalyzing) return;
    if (photoInput) photoInput.click();
  };

  // Attach File Select Triggers
  if (btnBrowseFiles) btnBrowseFiles.addEventListener('click', triggerFileSelect);
  if (btnChooseAction) btnChooseAction.addEventListener('click', triggerFileSelect);
  if (btnReplaceImage) btnReplaceImage.addEventListener('click', triggerFileSelect);
  if (btnTakePhoto) btnTakePhoto.addEventListener('click', triggerFileSelect);
  if (btnChooseGallery) btnChooseGallery.addEventListener('click', triggerFileSelect);

  // File Input Change Event
  if (photoInput) {
    photoInput.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) {
        handleSelectedFile(file);
      }
    });
  }

  // Drag and Drop Event Listeners on Dropzone
  if (dropzone) {
    ['dragenter', 'dragover'].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!isAnalyzing) {
          dropzone.classList.add('border-emerald-500', 'bg-emerald-50/80');
        }
      });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('border-emerald-500', 'bg-emerald-50/80');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      if (isAnalyzing) return;
      const dt = e.dataTransfer;
      const file = dt && dt.files && dt.files[0];
      if (file) {
        handleSelectedFile(file);
      }
    });

    // Clicking dropzone body also triggers file picker
    dropzone.addEventListener('click', (e) => {
      if (isAnalyzing) return;
      // If user clicked directly on Browse Files button, do not double-trigger
      if (e.target.closest('#btn-browse-files')) return;
      triggerFileSelect();
    });
  }

  // Remove / Reset Actions
  if (btnRemoveImage) btnRemoveImage.addEventListener('click', handleReset);
  if (btnRetakePhoto) btnRetakePhoto.addEventListener('click', handleReset);
  if (btnBadPhotoRetake) btnBadPhotoRetake.addEventListener('click', handleReset);
  if (btnDetectAnother) btnDetectAnother.addEventListener('click', handleReset);

  // Analyze Action Triggers
  if (btnAnalyzeAction) btnAnalyzeAction.addEventListener('click', analyzeLeafPhoto);
  if (btnUsePhoto) btnUsePhoto.addEventListener('click', analyzeLeafPhoto);

  // Error Retry
  if (btnErrorRetry) {
    btnErrorRetry.addEventListener('click', () => {
      if (currentFile) {
        analyzeLeafPhoto();
      } else {
        handleReset();
      }
    });
  }

  // Clean up object URLs on page unload to prevent memory leaks
  window.addEventListener('beforeunload', cleanupObjectUrl);
});
