/**
 * This file will later contain the actual HTTP calls using the centralized API_BASE_URL.
 * API functions must not contain scattered hard-coded backend URLs.
 * 
 * Instead of: fetch("http://localhost:8000/predict")
 * We use: fetch(`${API_BASE_URL}/predict`)
 */
import { API_BASE_URL } from './config';
import type { 
  PredictionRequest, PredictionResponse, 
  SatelliteResponse, ClassesResponse, 
  HealthResponse, HealthCheckResult, GradcamResponse,
  LoginRequest, LoginResponse,
  CatalogFieldsResponse, FieldDetailResponse,
  FieldHealthResponse, SatelliteTimeSeriesResponse,
  PredictionRecordItem, PredictionListResponse,
  CropInsightsSummary, DiseaseDistributionItem,
  CurrentWeatherResponse, WeatherForecastResponse, FieldWeatherResponse,
  MarketPriceItem, MarketPriceListResponse, MarketSummaryResponse,
  MarketTrendsResponse, DistrictAnalyticsResponse, VarietyAnalyticsResponse,
  BuyerItem, BuyerListResponse, BuyerNearbyItem, BuyerNearbyResponse,
  ReportItem, ReportListResponse, ReportGenerateOptions,
  MultimodalPredictionResult, GradcamExplanationResult
} from './types';

/**
 * Resolves active Bearer authentication headers for protected API requests.
 * Strictly tab-scoped: only retrieves token from sessionStorage (Rectification B).
 */
export const getAuthHeaders = (): Record<string, string> => {
  if (typeof window === 'undefined') return {};
  const token = sessionStorage.getItem('authToken');
  if (token && token.trim()) {
    return { 'Authorization': `Bearer ${token.trim()}` };
  }
  return {};
};

/**
 * Dispatches session expired event on HTTP 401 Unauthorized.
 */
export const handleApiAuthError = (status: number) => {
  if (status === 401 && typeof window !== 'undefined') {
    sessionStorage.removeItem('authToken');
    sessionStorage.removeItem('isLoggedIn');
    sessionStorage.removeItem('userRole');
    sessionStorage.removeItem('username');
    sessionStorage.removeItem('farmerId');
    sessionStorage.removeItem('schemaName');
    if (typeof window.dispatchEvent === 'function') {
      window.dispatchEvent(new CustomEvent('auth:session-expired', {
        detail: { message: 'Your session has expired. Please sign in again.' }
      }));
    }
  }
};

// Centralized API Client with full error handling and connection verification
export const checkHealth = async (customBaseUrl?: string): Promise<HealthCheckResult> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const url = `${baseUrl}/health`;
  const startTime = performance.now();

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    const latencyMs = Math.round(performance.now() - startTime);

    if (!response.ok) {
      handleApiAuthError(response.status);
      return {
        connected: false,
        statusCode: response.status,
        latencyMs,
        url,
        error: `HTTP ${response.status}: ${response.statusText || 'Server Error'}`,
      };
    }

    const data: HealthResponse = await response.json();
    return {
      connected: true,
      status: data.status,
      service: data.service,
      version: data.version,
      statusCode: response.status,
      latencyMs,
      url,
    };
  } catch (err: unknown) {
    const latencyMs = Math.round(performance.now() - startTime);
    let errorMsg = 'Failed to connect to backend server.';
    if (err instanceof Error) {
      if (err.name === 'AbortError') {
        errorMsg = 'Connection timed out after 6 seconds. Server is unreachable.';
      } else {
        errorMsg = `${err.message}. Ensure the FastAPI server is running at ${baseUrl}.`;
      }
    }
    return {
      connected: false,
      latencyMs,
      url,
      error: errorMsg,
    };
  }
};

export const getClasses = async (): Promise<ClassesResponse> => {
  const response = await fetch(`${API_BASE_URL}/classes`);
  return response.json();
};

/**
 * Retrieves the catalog of agricultural fields from the FastAPI backend.
 * Endpoint: GET /fields?skip={skip}&limit={limit}
 */
export const getFields = async (
  skip = 0,
  limit = 100,
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<CatalogFieldsResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${baseUrl}/fields?skip=${skip}&limit=${limit}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`Failed to load fields (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') {
        throw new Error('Fields request timed out after 10 seconds.');
      }
      throw err;
    }
    throw new Error('Unable to connect to backend fields service.');
  }
};

/**
 * Retrieves detailed field record by field identifier (e.g. 'FIELD_01').
 * Endpoint: GET /fields/{field_id}
 */
export const getField = async (
  fieldId: string,
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<FieldDetailResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${baseUrl}/fields/${encodeURIComponent(fieldId)}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      if (res.status === 404) {
        throw new Error(`Field '${fieldId}' was not found in the field catalog.`);
      }
      throw new Error(`Failed to load field '${fieldId}' (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') {
        throw new Error('Field details request timed out after 10 seconds.');
      }
      throw err;
    }
    throw new Error('Unable to connect to backend service.');
  }
};

/**
 * Retrieves field vegetation health and temporal trends computed from Sentinel-2 observations.
 * Endpoint: GET /fields/{field_id}/health
 */
export const getFieldHealth = async (
  fieldId: string,
  customBaseUrl?: string,
  timeoutMs = 12000
): Promise<FieldHealthResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${baseUrl}/fields/${encodeURIComponent(fieldId)}/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      if (res.status === 404) {
        throw new Error(`Field '${fieldId}' was not found in the field catalog.`);
      } else if (res.status === 503) {
        throw new Error(`Vegetation health data is temporarily unavailable for field '${fieldId}'.`);
      }
      throw new Error(`Health assessment failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') {
        throw new Error('Field health assessment request timed out.');
      }
      throw err;
    }
    throw new Error('Unable to connect to field health service.');
  }
};

/**
 * Retrieves chronological Sentinel-2 satellite time-series observations for a field.
 * Endpoint: GET /fields/{field_id}/timeseries
 */
export const getFieldTimeSeries = async (
  fieldId: string,
  startDate?: string,
  endDate?: string,
  customBaseUrl?: string,
  timeoutMs = 12000
): Promise<SatelliteTimeSeriesResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let url = `${baseUrl}/fields/${encodeURIComponent(fieldId)}/timeseries`;
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  const queryString = params.toString();
  if (queryString) url += `?${queryString}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      if (res.status === 404) {
        throw new Error(`Field '${fieldId}' was not found in the field catalog.`);
      } else if (res.status === 503) {
        throw new Error(`Satellite time-series observations are not available for field '${fieldId}'.`);
      }
      throw new Error(`Time-series query failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') {
        throw new Error('Satellite time-series request timed out.');
      }
      throw err;
    }
    throw new Error('Unable to connect to satellite time-series service.');
  }
};

/**
 * Retrieves historical disease prediction records from PostgreSQL.
 * Endpoint: GET /predictions
 */
export const getPredictions = async (
  filters: {
    page?: number;
    pageSize?: number;
    predictionMode?: string;
    disease?: string;
    fieldId?: string;
    predictionId?: string;
    startDate?: string;
    endDate?: string;
  } = {},
  customBaseUrl?: string,
  timeoutMs = 12000
): Promise<PredictionListResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const params = new URLSearchParams();
  if (filters.page) params.append('page', filters.page.toString());
  if (filters.pageSize) params.append('page_size', filters.pageSize.toString());
  if (filters.predictionMode) params.append('prediction_mode', filters.predictionMode);
  if (filters.disease) params.append('disease', filters.disease);
  if (filters.fieldId) params.append('field_id', filters.fieldId);
  if (filters.predictionId) params.append('prediction_id', filters.predictionId);
  if (filters.startDate) params.append('start_date', filters.startDate);
  if (filters.endDate) params.append('end_date', filters.endDate);

  const queryString = params.toString();
  const url = `${baseUrl}/predictions${queryString ? `?${queryString}` : ''}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`Failed to retrieve predictions (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Predictions query request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to prediction history service.');
  }
};

/**
 * Retrieves full details for a single diagnostic prediction inference log by UUID.
 * Endpoint: GET /predictions/{prediction_id}
 */
export const getPredictionById = async (
  predictionId: string,
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<PredictionRecordItem> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  const url = `${baseUrl}/predictions/${encodeURIComponent(predictionId)}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      if (res.status === 404) {
        throw new Error(`Prediction record '${predictionId}' was not found.`);
      }
      throw new Error(`Failed to retrieve prediction (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Prediction query request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to prediction service.');
  }
};

/**
 * Computes authentic statistical crop insights from genuine prediction records.
 */
export const getCropInsightsSummary = async (
  customBaseUrl?: string
): Promise<CropInsightsSummary> => {
  const response = await getPredictions({ pageSize: 100 }, customBaseUrl);
  const records = response.predictions || [];
  const total = response.total_predictions || records.length;

  let imageOnly = 0;
  let multimodal = 0;
  let healthy = 0;
  let diseased = 0;
  let totalConf = 0;
  const countsByDisease: Record<string, { count: number; totalConf: number; healthy: boolean }> = {};

  for (const r of records) {
    if (r.prediction_mode === 'multimodal') multimodal++;
    else imageOnly++;

    if (r.is_healthy || r.predicted_disease === 'normal') healthy++;
    else diseased++;

    totalConf += (r.confidence || 0);

    const d = r.predicted_disease || 'unknown';
    if (!countsByDisease[d]) {
      countsByDisease[d] = { count: 0, totalConf: 0, healthy: r.is_healthy || d === 'normal' };
    }
    countsByDisease[d].count++;
    countsByDisease[d].totalConf += (r.confidence || 0);
  }

  const distribution: DiseaseDistributionItem[] = Object.entries(countsByDisease)
    .map(([disease, stat]) => ({
      disease,
      displayName: disease.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
      count: stat.count,
      percentage: total > 0 ? parseFloat(((stat.count / total) * 100).toFixed(1)) : 0,
      avgConfidence: stat.count > 0 ? parseFloat(((stat.totalConf / stat.count) * 100).toFixed(1)) : 0,
      healthy: stat.healthy,
    }))
    .sort((a, b) => b.count - a.count);

  return {
    totalPredictions: total,
    imageOnlyCount: imageOnly,
    multimodalCount: multimodal,
    healthyCount: healthy,
    diseasedCount: diseased,
    avgConfidence: records.length > 0 ? parseFloat(((totalConf / records.length) * 100).toFixed(1)) : 0,
    diseaseDistribution: distribution,
  };
};

export const getSatelliteData = async (fieldId: string): Promise<SatelliteResponse> => {
  const response = await fetch(`${API_BASE_URL}/satellite/${fieldId}`);
  return response.json();
};

export const getGradcam = async (imageId: string): Promise<GradcamResponse> => {
  const response = await fetch(`${API_BASE_URL}/gradcam/${imageId}`);
  return response.json();
};

export const predict = async (
  request: PredictionRequest | FormData,
  customBaseUrl?: string,
  timeoutMs = 30000
): Promise<PredictionResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const url = `${baseUrl}/predict`;

  let formData: FormData;
  if (request instanceof FormData) {
    formData = request;
  } else {
    formData = new FormData();
    formData.append('file', request.image);
    if (request.latitude !== undefined && request.latitude !== null) {
      formData.append('latitude', request.latitude.toString());
    }
    if (request.longitude !== undefined && request.longitude !== null) {
      formData.append('longitude', request.longitude.toString());
    }
    if (request.question) formData.append('question', request.question);
    if (request.language) formData.append('language', request.language);
    if (request.field_id) formData.append('field_id', request.field_id);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { ...getAuthHeaders() },
      body: formData,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      handleApiAuthError(response.status);
      let errorDetail = '';
      try {
        const errJson = await response.json();
        errorDetail = errJson.detail || errJson.error || '';
      } catch {
        errorDetail = await response.text();
      }

      // Sanitize server error details against private local paths or secrets
      const sanitizedDetail = errorDetail
        .replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]')
        .replace(/\/[^"'\n\r\t]+\/[^"'\n\r\t]+/g, '[internal path]');

      if (response.status === 415) {
        throw new Error(sanitizedDetail || 'Unsupported file format. Please upload a JPG, JPEG, or PNG image.');
      } else if (response.status === 413) {
        throw new Error(sanitizedDetail || 'Image file is too large. Maximum supported size is 10 MB.');
      } else if (response.status === 400) {
        throw new Error(sanitizedDetail || 'Image file is invalid, empty, or corrupted. Please provide a clear paddy leaf image.');
      } else if (response.status === 503) {
        throw new Error(sanitizedDetail || 'AI model service is currently unavailable. Please verify model checkpoints.');
      } else {
        throw new Error(`Inference request failed (HTTP ${response.status}): ${sanitizedDetail || response.statusText || 'Server Error'}`);
      }
    }

    const rawData = await response.json();

    // Normalize response payload for both image-only and multimodal endpoints
    const diseaseName = rawData.disease || rawData.predicted_class || rawData.predicted_disease || 'unknown';
    const confidenceScore = typeof rawData.confidence === 'number' ? rawData.confidence : 0;
    
    // Normalize top candidates list
    const rawTop = rawData.top3 || rawData.top_3 || rawData.top_3_predictions || [];
    const top3 = Array.isArray(rawTop)
      ? rawTop.map((item: any) => ({
          disease: item.disease || item.class || item.name || 'unknown',
          probability: typeof item.probability === 'number' ? item.probability : (typeof item.confidence === 'number' ? item.confidence : 0),
          index: item.index,
          name: item.name || item.disease,
          class: item.class || item.disease,
        }))
      : [];

    return {
      status: rawData.status || 'success',
      disease: diseaseName,
      confidence: confidenceScore,
      predicted_index: rawData.predicted_index,
      is_healthy: rawData.is_healthy ?? (diseaseName === 'normal'),
      low_confidence: rawData.low_confidence ?? (confidenceScore < 0.60),
      top3,
      device: rawData.device || 'cpu',
      note: rawData.note,
      prediction_id: rawData.prediction_id,
      field_id: rawData.field_id,
      prediction_mode: rawData.prediction_mode || 'image_only',
      temporal_attention_weights: rawData.temporal_attention_weights,
      satellite_timesteps: rawData.satellite_timesteps,
    };
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') {
        throw new Error(`Inference request timed out after ${Math.round(timeoutMs / 1000)} seconds. Please try again.`);
      }
      throw err;
    }
    throw new Error('Network error: Unable to connect to prediction service.');
  }
};

/**
 * Executes multimodal disease prediction fusing leaf image and field satellite time-series.
 * Endpoint: POST /predict/multimodal
 */
export const predictMultimodal = async (
  file: File | Blob,
  fieldId: string,
  customBaseUrl?: string,
  timeoutMs = 35000
): Promise<MultimodalPredictionResult> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const url = `${baseUrl}/predict/multimodal`;
  const formData = new FormData();
  formData.append('file', file);
  formData.append('field_id', fieldId);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { ...getAuthHeaders() },
      body: formData,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let errorDetail = '';
      try {
        const errJson = await res.json();
        errorDetail = errJson.detail || errJson.error || '';
      } catch {
        errorDetail = await res.text();
      }
      const sanitized = errorDetail
        .replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]')
        .replace(/\/[^"'\n\r\t]+\/[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(sanitized || `Multimodal inference failed (HTTP ${res.status})`);
    }

    const data = await res.json();
    return {
      status: data.status || 'success',
      prediction_mode: data.prediction_mode || 'multimodal',
      field_id: data.field_id,
      predicted_class: data.predicted_class,
      disease: data.predicted_class,
      confidence: data.confidence,
      top_3_predictions: data.top_3_predictions || [],
      temporal_attention_weights: data.temporal_attention_weights || [],
      prediction_id: data.prediction_id,
      device: data.device,
      note: data.note,
    };
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Multimodal inference request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to multimodal prediction service.');
  }
};

/**
 * Computes Grad-CAM explainability heatmap overlay for an uploaded paddy leaf image.
 * Endpoint: POST /explain/gradcam
 */
export const generateGradcam = async (
  file: File | Blob,
  targetClass?: string,
  customBaseUrl?: string,
  timeoutMs = 30000
): Promise<GradcamExplanationResult> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const url = `${baseUrl}/explain/gradcam`;
  const formData = new FormData();
  formData.append('file', file);
  if (targetClass) formData.append('target_class', targetClass);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { ...getAuthHeaders() },
      body: formData,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let errorDetail = '';
      try {
        const errJson = await res.json();
        errorDetail = errJson.detail || errJson.error || '';
      } catch {
        errorDetail = await res.text();
      }
      const sanitized = errorDetail
        .replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]')
        .replace(/\/[^"'\n\r\t]+\/[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(sanitized || `Grad-CAM explanation failed (HTTP ${res.status})`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Grad-CAM request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to Grad-CAM service.');
  }
};

// =====================================================================
// WEATHER ENDPOINTS (STEP 11J.5)
// =====================================================================

export const getCurrentWeather = async (
  latitude: number,
  longitude: number,
  timezone = 'Asia/Kolkata',
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<CurrentWeatherResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  const url = `${baseUrl}/weather/current?latitude=${latitude}&longitude=${longitude}&timezone=${encodeURIComponent(timezone)}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`Current weather request failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Weather request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to weather service.');
  }
};

export const getWeatherForecast = async (
  latitude: number,
  longitude: number,
  forecastDays = 7,
  timezone = 'Asia/Kolkata',
  customBaseUrl?: string,
  timeoutMs = 12000
): Promise<WeatherForecastResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  const url = `${baseUrl}/weather/forecast?latitude=${latitude}&longitude=${longitude}&forecast_days=${forecastDays}&timezone=${encodeURIComponent(timezone)}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`Weather forecast request failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Weather forecast timed out.');
      throw err;
    }
    throw new Error('Unable to connect to weather service.');
  }
};

export const getFieldWeather = async (
  fieldId: string,
  forecastDays = 7,
  timezone?: string,
  customBaseUrl?: string,
  timeoutMs = 12000
): Promise<FieldWeatherResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const params = new URLSearchParams();
  params.append('forecast_days', forecastDays.toString());
  if (timezone) params.append('timezone', timezone);
  const url = `${baseUrl}/fields/${encodeURIComponent(fieldId)}/weather?${params.toString()}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      if (res.status === 404) {
        throw new Error(`Field '${fieldId}' was not found in field catalog.`);
      }
      throw new Error(`Field weather query failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Field weather request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to field weather service.');
  }
};

// =====================================================================
// MARKET PRICES & ANALYTICS ENDPOINTS (STEP 11J.5)
// =====================================================================

export const getMarketPrices = async (
  filters: {
    district?: string;
    commodity?: string;
    variety?: string;
    state?: string;
    forceLive?: boolean;
    skip?: number;
    limit?: number;
  } = {},
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<MarketPriceListResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const params = new URLSearchParams();
  if (filters.district) params.append('district', filters.district);
  if (filters.commodity) params.append('commodity', filters.commodity);
  if (filters.variety) params.append('variety', filters.variety);
  if (filters.state) params.append('state', filters.state);
  if (filters.forceLive !== undefined) params.append('force_live', String(filters.forceLive));
  if (filters.skip !== undefined) params.append('skip', filters.skip.toString());
  if (filters.limit !== undefined) params.append('limit', filters.limit.toString());

  const queryString = params.toString();
  const url = `${baseUrl}/market/prices${queryString ? `?${queryString}` : ''}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`Market prices query failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Market prices request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to market prices service.');
  }
};

export const getLatestMarketPrices = async (
  filters: {
    district?: string;
    commodity?: string;
    state?: string;
    forceLive?: boolean;
    limit?: number;
  } = {},
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<MarketPriceListResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const params = new URLSearchParams();
  if (filters.district) params.append('district', filters.district);
  if (filters.commodity) params.append('commodity', filters.commodity);
  if (filters.state) params.append('state', filters.state);
  if (filters.forceLive !== undefined) params.append('force_live', String(filters.forceLive));
  if (filters.limit !== undefined) params.append('limit', filters.limit.toString());

  const queryString = params.toString();
  const url = `${baseUrl}/market/prices/latest${queryString ? `?${queryString}` : ''}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`Latest prices query failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Latest prices request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to market service.');
  }
};

export const getMarketSummary = async (
  filters: {
    state?: string;
    district?: string;
    commodity?: string;
    variety?: string;
  } = {},
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<MarketSummaryResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const params = new URLSearchParams();
  if (filters.state) params.append('state', filters.state);
  if (filters.district) params.append('district', filters.district);
  if (filters.commodity) params.append('commodity', filters.commodity);
  if (filters.variety) params.append('variety', filters.variety);

  const queryString = params.toString();
  const url = `${baseUrl}/market/analytics/summary${queryString ? `?${queryString}` : ''}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`Market summary query failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Market summary request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to market analytics service.');
  }
};

export const getMarketTrends = async (
  filters: {
    days?: number;
    state?: string;
    district?: string;
    commodity?: string;
    variety?: string;
  } = {},
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<MarketTrendsResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const params = new URLSearchParams();
  if (filters.days) params.append('days', filters.days.toString());
  if (filters.state) params.append('state', filters.state);
  if (filters.district) params.append('district', filters.district);
  if (filters.commodity) params.append('commodity', filters.commodity);
  if (filters.variety) params.append('variety', filters.variety);

  const queryString = params.toString();
  const url = `${baseUrl}/market/analytics/trends${queryString ? `?${queryString}` : ''}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`Market trends query failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Market trends request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to market trends service.');
  }
};

export const getDistrictAnalytics = async (
  filters: {
    days?: number;
    state?: string;
    commodity?: string;
    variety?: string;
  } = {},
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<DistrictAnalyticsResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const params = new URLSearchParams();
  if (filters.days) params.append('days', filters.days.toString());
  if (filters.state) params.append('state', filters.state);
  if (filters.commodity) params.append('commodity', filters.commodity);
  if (filters.variety) params.append('variety', filters.variety);

  const queryString = params.toString();
  const url = `${baseUrl}/market/analytics/districts${queryString ? `?${queryString}` : ''}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`District analytics query failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('District analytics request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to district analytics service.');
  }
};

export const getVarietyAnalytics = async (
  filters: {
    days?: number;
    state?: string;
    district?: string;
    commodity?: string;
  } = {},
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<VarietyAnalyticsResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const params = new URLSearchParams();
  if (filters.days) params.append('days', filters.days.toString());
  if (filters.state) params.append('state', filters.state);
  if (filters.district) params.append('district', filters.district);
  if (filters.commodity) params.append('commodity', filters.commodity);

  const queryString = params.toString();
  const url = `${baseUrl}/market/analytics/varieties${queryString ? `?${queryString}` : ''}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`Variety analytics query failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Variety analytics request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to variety analytics service.');
  }
};

// =====================================================================
// BUYER DIRECTORY & NEARBY BUYERS (STEP 11J.5)
// =====================================================================

export const getBuyers = async (
  filters: {
    district?: string;
    buyerType?: string;
    state?: string;
    verificationStatus?: string;
    skip?: number;
    limit?: number;
  } = {},
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<BuyerListResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const params = new URLSearchParams();
  if (filters.district) params.append('district', filters.district);
  if (filters.buyerType) params.append('buyer_type', filters.buyerType);
  if (filters.state) params.append('state', filters.state);
  if (filters.verificationStatus) params.append('verification_status', filters.verificationStatus);
  if (filters.skip !== undefined) params.append('skip', filters.skip.toString());
  if (filters.limit !== undefined) params.append('limit', filters.limit.toString());

  const queryString = params.toString();
  const url = `${baseUrl}/buyers${queryString ? `?${queryString}` : ''}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`Buyers query failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Buyers request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to buyers directory service.');
  }
};

export const getBuyerById = async (
  buyerId: string,
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<BuyerItem> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  const url = `${baseUrl}/buyers/${encodeURIComponent(buyerId)}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      if (res.status === 404) {
        throw new Error(`Buyer '${buyerId}' was not found in directory.`);
      }
      throw new Error(`Buyer query failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Buyer request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to buyer profile service.');
  }
};

export const getNearbyBuyers = async (
  lat: number,
  lon: number,
  radiusKm?: number,
  filters: {
    district?: string;
    buyerType?: string;
    state?: string;
    verificationStatus?: string;
    skip?: number;
    limit?: number;
  } = {},
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<BuyerNearbyResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const params = new URLSearchParams();
  params.append('lat', lat.toString());
  params.append('lon', lon.toString());
  if (radiusKm) params.append('radius_km', radiusKm.toString());
  if (filters.district) params.append('district', filters.district);
  if (filters.buyerType) params.append('buyer_type', filters.buyerType);
  if (filters.state) params.append('state', filters.state);
  if (filters.verificationStatus) params.append('verification_status', filters.verificationStatus);
  if (filters.skip !== undefined) params.append('skip', filters.skip.toString());
  if (filters.limit !== undefined) params.append('limit', filters.limit.toString());

  const url = `${baseUrl}/buyers/nearby?${params.toString()}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`Nearby buyers query failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Nearby buyers request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to nearby buyers service.');
  }
};

// =====================================================================
// REPORTS & DOCUMENTS ENDPOINTS (STEP 11J.6)
// =====================================================================

/**
 * Retrieves a paginated list of compiled diagnostic reports from PostgreSQL.
 * Endpoint: GET /reports
 */
export const getReports = async (
  filters: {
    predictionId?: string;
    fieldId?: string;
    reportType?: string;
    status?: string;
    page?: number;
    pageSize?: number;
  } = {},
  customBaseUrl?: string,
  timeoutMs = 12000
): Promise<ReportListResponse> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const params = new URLSearchParams();
  if (filters.predictionId) params.append('prediction_id', filters.predictionId);
  if (filters.fieldId) params.append('field_id', filters.fieldId);
  if (filters.reportType) params.append('report_type', filters.reportType);
  if (filters.status) params.append('status', filters.status);
  if (filters.page) params.append('page', filters.page.toString());
  if (filters.pageSize) params.append('page_size', filters.pageSize.toString());

  const queryString = params.toString();
  const url = `${baseUrl}/reports${queryString ? `?${queryString}` : ''}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`Failed to retrieve reports (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Reports query request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to reports service.');
  }
};

/**
 * Retrieves full details for a single diagnostic report by UUID.
 * Endpoint: GET /reports/{report_id}
 */
export const getReportById = async (
  reportId: string,
  customBaseUrl?: string,
  timeoutMs = 10000
): Promise<ReportItem> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  const url = `${baseUrl}/reports/${encodeURIComponent(reportId)}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      if (res.status === 404) {
        throw new Error(`Report '${reportId}' was not found.`);
      }
      throw new Error(`Failed to retrieve report (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Report query request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to report service.');
  }
};

/**
 * Compiles and generates a diagnostic report for an existing prediction record.
 * Endpoint: POST /reports/generate/{prediction_id}
 */
export const generateReport = async (
  predictionId: string,
  options: {
    fileFormat?: 'json' | 'pdf';
    forceRegenerate?: boolean;
  } = {},
  customBaseUrl?: string,
  timeoutMs = 25000
): Promise<ReportItem> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const params = new URLSearchParams();
  if (options.fileFormat) params.append('file_format', options.fileFormat);
  if (options.forceRegenerate !== undefined) params.append('force_regenerate', String(options.forceRegenerate));

  const queryString = params.toString();
  const url = `${baseUrl}/reports/generate/${encodeURIComponent(predictionId)}${queryString ? `?${queryString}` : ''}`;

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Accept': 'application/json', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      throw new Error(`Report generation failed (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Report generation request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to report generation service.');
  }
};

/**
 * Downloads a compiled PDF report artifact as a Blob.
 * Endpoint: GET /reports/{report_id}/download
 */
export const downloadReportPdf = async (
  reportId: string,
  regenerate = false,
  customBaseUrl?: string,
  timeoutMs = 25000
): Promise<{ blob: Blob; filename: string }> => {
  const baseUrl = (customBaseUrl !== undefined && customBaseUrl.trim() !== '' ? customBaseUrl : API_BASE_URL).replace(/\/+$/, '');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const params = new URLSearchParams();
  if (regenerate) params.append('regenerate', 'true');
  const queryString = params.toString();
  const url = `${baseUrl}/reports/${encodeURIComponent(reportId)}/download${queryString ? `?${queryString}` : ''}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/pdf', ...getAuthHeaders() },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      handleApiAuthError(res.status);
      let detail = '';
      try { const err = await res.json(); detail = err.detail || err.error || ''; } catch { detail = await res.text(); }
      const sanitized = detail.replace(/[A-Za-z]:\\[^"'\n\r\t]+/g, '[internal path]');
      if (res.status === 404) {
        throw new Error(`Report artifact '${reportId}' was not found.`);
      }
      throw new Error(`Failed to download report PDF (HTTP ${res.status}): ${sanitized || res.statusText}`);
    }

    // Extract filename from Content-Disposition header if available
    let filename = `paddy_disease_report_${reportId}.pdf`;
    const disposition = res.headers.get('content-disposition');
    if (disposition) {
      const match = disposition.match(/filename=["']?([^"';]+)["']?/i);
      if (match && match[1]) {
        filename = match[1].trim();
      }
    }

    const blob = await res.blob();
    return { blob, filename };
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === 'AbortError') throw new Error('Report download request timed out.');
      throw err;
    }
    throw new Error('Unable to connect to report download service.');
  }
};



// Real FastAPI Authentication Integration (STEP 4A)
export const authenticate = async (request: LoginRequest): Promise<LoginResponse> => {
  const payload = {
    username: request.username || request.mobile_number || '',
    password: request.password,
  };
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
      handleApiAuthError(response.status);
    let detail = 'Authentication failed.';
    try {
      const err = await response.json();
      detail = err.detail || detail;
    } catch {
      detail = `HTTP ${response.status}`;
    }
    throw new Error(detail);
  }

  return response.json();
};
