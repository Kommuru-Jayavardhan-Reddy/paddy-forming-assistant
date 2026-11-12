/**
 * Centralized TypeScript API contracts for the Paddy Farming Assistant frontend.
 * Defines the request and response shapes for all expected backend endpoints.
 */

export interface PredictionRequest {
  image: File | Blob; 
  latitude?: number;
  longitude?: number;
  question?: string;
  language?: string;
  field_id?: string;
}

export interface TopCandidate {
  disease: string;
  probability: number;
  index?: number;
  name?: string;
  class?: string;
}

export interface PredictionResponse {
  status?: string;
  disease: string;
  confidence: number;
  predicted_index?: number;
  is_healthy?: boolean;
  low_confidence?: boolean;
  top3: TopCandidate[];
  device?: string;
  note?: string;
  prediction_id?: string;
  field_id?: string;
  coordinates?: { latitude?: number; longitude?: number };
  question?: string;
  language?: string;
  prediction_mode?: string;
  temporal_attention_weights?: number[];
  satellite_timesteps?: number;
}

// Prediction History & Crop Insights Contracts (STEP 11J.4)
export interface PredictionRecordItem {
  id: string;
  field_id?: string | null;
  prediction_mode: 'image_only' | 'multimodal' | string;
  model_name: string;
  model_version: string;
  predicted_disease: string;
  predicted_class_index: number;
  confidence: number;
  is_healthy: boolean;
  low_confidence: boolean;
  top_k_predictions: TopCandidate[];
  attention_weights?: number[] | null;
  image_sha256?: string | null;
  farmer_question?: string | null;
  response_language?: string;
  inference_latency_ms?: number | null;
  device?: string;
  created_at: string;
}

export interface PredictionListResponse {
  predictions: PredictionRecordItem[];
  total_predictions: number;
  page?: number;
  page_size?: number;
}

export interface DiseaseDistributionItem {
  disease: string;
  displayName: string;
  count: number;
  percentage: number;
  avgConfidence: number;
  healthy: boolean;
}

export interface CropInsightsSummary {
  totalPredictions: number;
  imageOnlyCount: number;
  multimodalCount: number;
  healthyCount: number;
  diseasedCount: number;
  avgConfidence: number;
  diseaseDistribution: DiseaseDistributionItem[];
}

// Field Catalog & Health Contracts (STEP 11J.3)
export interface CatalogFieldItem {
  field_id: string;
  external_field_id: string;
  clean_field_id?: string;
  field_name: string;
  latitude: number;
  longitude: number;
  area_hectares?: number | null;
  crop_variety?: string | null;
  is_active: boolean;
  sentinel2_image_count: number;
  embedding_index?: number;
  sequence_index?: number;
  has_images: boolean;
}

export interface CatalogFieldsResponse {
  fields: CatalogFieldItem[];
  total_fields: number;
}

export interface FieldDetailResponse {
  id: string;
  field_id: string;
  external_field_id: string;
  clean_field_id?: string;
  field_name: string;
  latitude: number;
  longitude: number;
  area_hectares?: number | null;
  crop_variety?: string | null;
  elevation_m?: number | null;
  sowing_date?: string | null;
  is_active: boolean;
  has_images: boolean;
  observation_count: number;
}

export interface VegetationIndexValues {
  ndvi: number;
  ndre: number;
  gndvi: number;
}

export interface IndexTrendMetric {
  latest: number;
  previous: number;
  absolute_change: number;
  percentage_change?: number | null;
  baseline_first: number;
  overall_change: number;
  direction: 'increasing' | 'decreasing' | 'stable' | string;
  trend_description: string;
}

export interface IndexSummaryStatistics {
  min: number;
  max: number;
  mean: number;
}

export interface FieldDataQualityStatus {
  total_observations: number;
  valid_observations: number;
  is_complete: boolean;
  has_anomalies: boolean;
  interpolation_note: string;
}

export interface FieldHealthResponse {
  field_id: string;
  clean_field_id?: string | null;
  coordinates?: { latitude: number; longitude: number } | null;
  observation_count: number;
  latest_observation_date?: string | null;
  previous_observation_date?: string | null;
  latest_indices: VegetationIndexValues;
  previous_indices: VegetationIndexValues;
  changes_and_trends: {
    ndvi: IndexTrendMetric;
    ndre: IndexTrendMetric;
    gndvi: IndexTrendMetric;
    [key: string]: IndexTrendMetric;
  };
  summary_statistics: {
    ndvi: IndexSummaryStatistics;
    ndre: IndexSummaryStatistics;
    gndvi: IndexSummaryStatistics;
    [key: string]: IndexSummaryStatistics;
  };
  data_quality_status: FieldDataQualityStatus;
  health_classification_status: string;
  health_category?: string | null;
  advisory_summary: string;
  limitations_and_interpretation_notes: string[];
}

export interface TimeStepObservation {
  timestep: number;
  date?: string | null;
  ndvi: number;
  ndre: number;
  gndvi: number;
}

export interface SatelliteTimeSeriesResponse {
  field_id: string;
  clean_field_id?: string;
  sequence_index: number;
  features: string[];
  total_timesteps: number;
  coordinates?: { latitude: number; longitude: number };
  has_dates: boolean;
  timesteps: TimeStepObservation[];
}

export interface SatelliteRecord {
  field_id: string;
  date: string; // ISO date string
  NDVI: number;
  NDRE: number;
  GNDVI: number;
}

export type SatelliteResponse = SatelliteRecord[];

// 13 Paddy disease classes expected
export interface DiseaseClass {
  name: string;
  description: string;
}

export type ClassesResponse = DiseaseClass[];

export interface HealthResponse {
  status: string;
  service?: string;
  version?: string;
}

export interface HealthCheckResult {
  connected: boolean;
  status?: string;
  service?: string;
  version?: string;
  statusCode?: number;
  latencyMs?: number;
  url: string;
  error?: string;
}

export interface GradcamResponse {
  image_url: string;
}

// Authentic Backend Authentication Contracts (STEP 4A)
export interface LoginRequest {
  username?: string;
  mobile_number?: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
  username: string;
  farmer_id: string;
  schema_name: string | null;
}

export interface FarmerRegisterRequest {
  username: string;
  password: string;
  mobile_number?: string;
  full_name?: string;
  farm_name?: string;
  village?: string;
}

export interface FarmerProfileResponse {
  id: string;
  username: string;
  mobile_number?: string | null;
  normalized_mobile?: string | null;
  role: string;
  schema_name?: string | null;
  full_name?: string | null;
  farm_name?: string | null;
  village?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AdminSystemStatusResponse {
  status: string;
  authenticated_admin: string;
  role: string;
  access_granted: boolean;
}

// Weather Contracts (STEP 11J.5)
export interface WeatherCoordinates {
  latitude: number;
  longitude: number;
  elevation?: number | null;
}

export interface WeatherUnits {
  temperature: string;
  relative_humidity: string;
  precipitation: string;
  wind_speed: string;
}

export interface CurrentWeatherObservation {
  time?: string | null;
  interval_seconds?: number | null;
  temperature?: number | null;
  temperature_unit?: string;
  relative_humidity?: number | null;
  relative_humidity_unit?: string;
  precipitation?: number | null;
  precipitation_unit?: string;
  rain?: number | null;
  rain_unit?: string;
  wind_speed?: number | null;
  wind_speed_unit?: string;
  weather_code?: number | null;
  weather_condition?: string | null;
}

export interface DailyForecastItem {
  date: string;
  temperature_max?: number | null;
  temperature_min?: number | null;
  temperature_unit?: string;
  precipitation_sum?: number | null;
  precipitation_unit?: string;
  rain_sum?: number | null;
  rain_sum_unit?: string;
  wind_speed_max?: number | null;
  wind_speed_unit?: string;
  weather_code?: number | null;
  weather_condition?: string | null;
}

export interface CurrentWeatherResponse {
  provider: string;
  coordinates: WeatherCoordinates;
  timezone?: string | null;
  current?: CurrentWeatherObservation | null;
  units: WeatherUnits;
}

export interface WeatherForecastResponse {
  provider: string;
  coordinates: WeatherCoordinates;
  timezone?: string | null;
  daily_forecast: DailyForecastItem[];
  units: WeatherUnits;
}

export interface FieldWeatherResponse {
  field_id: string;
  requested_field_id: string;
  clean_field_id?: string | null;
  provider: string;
  coordinates: WeatherCoordinates;
  timezone?: string | null;
  timezone_abbreviation?: string | null;
  utc_offset_seconds?: number | null;
  current?: CurrentWeatherObservation | null;
  daily_forecast: DailyForecastItem[];
  units: WeatherUnits;
}

// Market Prices Contracts (STEP 11J.5)
export interface MarketPriceItem {
  id: string | number;
  state: string;
  district: string;
  market?: string;
  market_name?: string;
  commodity: string;
  variety: string;
  arrival_date?: string;
  price_date?: string;
  min_price: number;
  max_price: number;
  modal_price: number;
  currency: string;
  unit: string;
  data_source?: string;
  source?: string;
  created_at?: string;
}

export interface MarketPriceListResponse {
  items: MarketPriceItem[];
  total: number;
  skip?: number;
  limit?: number;
  data_source?: string;
  is_stale?: boolean;
  freshness_date?: string | null;
}

export interface MarketSummaryResponse {
  state?: string | null;
  district?: string | null;
  commodity: string;
  variety?: string | null;
  has_data: boolean;
  total_observations: number;
  distinct_markets: number;
  distinct_districts: number;
  distinct_varieties: number;
  avg_modal_price?: number | null;
  min_modal_price?: number | null;
  max_modal_price?: number | null;
  min_transaction_price?: number | null;
  max_transaction_price?: number | null;
  earliest_price_date?: string | null;
  latest_price_date?: string | null;
  currency: string;
  unit: string;
}

export interface MarketTrendsDailyItem {
  date: string;
  avg_modal_price?: number | null;
  min_modal_price?: number | null;
  max_modal_price?: number | null;
  observation_count: number;
  currency: string;
  unit: string;
}

export interface MarketTrendsResponse {
  state?: string | null;
  district?: string | null;
  commodity: string;
  variety?: string | null;
  days_requested: number;
  days_with_data: number;
  start_date?: string | null;
  end_date?: string | null;
  total_observations: number;
  start_modal_price?: number | null;
  end_modal_price?: number | null;
  absolute_change?: number | null;
  percentage_change?: number | null;
  trend_direction: string;
  currency: string;
  unit: string;
  daily_trends: MarketTrendsDailyItem[];
}

export interface DistrictBenchmarkItem {
  district: string;
  state?: string;
  commodity?: string;
  variety?: string | null;
  average_price?: number;
  modal_price?: number;
  min_price?: number;
  max_price?: number;
  quotation_count?: number;
  latest_arrival_date?: string;
  relative_premium_percent?: number | null;
}

export interface DistrictAnalyticsResponse {
  days_analyzed?: number;
  days?: number;
  state: string;
  commodity: string;
  variety?: string | null;
  state_avg_modal_price?: number;
  highest_price_district?: string;
  lowest_price_district?: string;
  price_spread?: number;
  districts: DistrictBenchmarkItem[];
  total_districts?: number;
  overall_average_price?: number;
}

export interface VarietyBenchmarkItem {
  variety: string;
  commodity?: string;
  average_price?: number;
  modal_price?: number;
  min_price?: number;
  max_price?: number;
  quotation_count?: number;
  latest_arrival_date?: string;
  relative_premium_percent?: number | null;
}

export interface VarietyAnalyticsResponse {
  days_analyzed?: number;
  days?: number;
  state: string;
  district?: string | null;
  commodity: string;
  premium_variety?: string;
  standard_variety?: string;
  varieties: VarietyBenchmarkItem[];
  total_varieties?: number;
  overall_average_price?: number;
}

// Buyer Directory Contracts (STEP 11J.5)
export interface BuyerItem {
  id: string;
  business_name: string;
  buyer_type: 'mill' | 'fpo' | 'government_agency' | 'wholesaler' | 'trader' | string;
  district: string;
  state: string;
  address_summary: string;
  contact_person?: string | null;
  contact_phone?: string | null;
  contact_email?: string | null;
  preferred_varieties?: string[];
  min_procurement_quintals?: number | null;
  verification_status: 'verified' | 'pending' | 'unverified' | string;
  verification_notes?: string | null;
  is_active: boolean;
  latitude?: number | null;
  longitude?: number | null;
  coordinate_source?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface BuyerListResponse {
  items: BuyerItem[];
  total: number;
  skip?: number;
  limit?: number;
}

export interface BuyerNearbyItem extends BuyerItem {
  distance_km: number;
}

export interface BuyerNearbyResponse {
  items: BuyerNearbyItem[];
  total: number;
  skip?: number;
  limit?: number;
  farmer_latitude: number;
  farmer_longitude: number;
  search_radius_km?: number | null;
}

// Reports & Documents Contracts (STEP 11J.6)
export interface ReportItem {
  id: string;
  prediction_id?: string | null;
  field_id?: string | null;
  report_type: 'disease_diagnostic' | 'field_health_summary' | 'seasonal_advisory' | 'market_intelligence' | string;
  title: string;
  summary?: string | null;
  status: 'completed' | 'generating' | 'failed' | string;
  file_format: 'json' | 'pdf' | string;
  file_size_bytes?: number | null;
  report_metadata?: Record<string, any> | null;
  generated_by?: string;
  created_at: string;
}

export interface ReportListResponse {
  reports: ReportItem[];
  total_reports: number;
  page?: number;
  page_size?: number;
}

export interface ReportGenerateOptions {
  force_regenerate?: boolean;
  file_format?: 'json' | 'pdf';
}

// Multimodal Cross-Attention & Explainability Contracts
export interface MultimodalPredictionResult {
  status: string;
  prediction_mode: string;
  field_id: string;
  predicted_class: string;
  disease?: string;
  confidence: number;
  top_3_predictions: Array<{ disease: string; probability: number; index: number }>;
  temporal_attention_weights: number[];
  prediction_id?: string;
  device?: string;
  note?: string;
}

export interface GradcamExplanationResult {
  status: string;
  predicted_class: string;
  target_class: string;
  target_layer: string;
  heatmap_intensity_max: number;
  heatmap_intensity_mean: number;
  overlay_image: string; // Base64 URI
  visualization_url?: string;
}

