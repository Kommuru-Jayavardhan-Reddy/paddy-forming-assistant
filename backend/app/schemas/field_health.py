"""
Paddy Farming Assistant - Field Health Schemas (STEP 11D.4)
Defines Pydantic models for vegetation health indices, changes, trends,
and scientific disclaimers based on real Sentinel-2 satellite time-series.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class VegetationIndexValues(BaseModel):
    """Vegetation index values for a single observation timestep."""
    ndvi: float = Field(..., description="Normalized Difference Vegetation Index [-1.0 to 1.0]")
    ndre: float = Field(..., description="Normalized Difference Red Edge Index [-1.0 to 1.0]")
    gndvi: float = Field(..., description="Green Normalized Difference Vegetation Index [-1.0 to 1.0]")


class IndexTrendMetric(BaseModel):
    """Temporal change and trend metric for an individual spectral index."""
    latest: float = Field(..., description="Latest recorded observation value")
    previous: float = Field(..., description="Observation value immediately preceding the latest")
    absolute_change: float = Field(..., description="Absolute change (latest - previous)")
    percentage_change: Optional[float] = Field(
        None, description="Percentage change from previous observation (None if previous <= 0 or invalid)"
    )
    baseline_first: float = Field(..., description="Baseline observation value at initial timestep (t=1)")
    overall_change: float = Field(..., description="Overall change across full observation period (latest - baseline_first)")
    direction: str = Field(..., description="Cautious trend direction: 'increasing', 'decreasing', or 'stable'")
    trend_description: str = Field(..., description="Cautious non-prescriptive description of index trend")


class IndexSummaryStatistics(BaseModel):
    """Summary statistics across the complete 10-timestep observation trajectory."""
    min: float = Field(..., description="Minimum value recorded across all timesteps")
    max: float = Field(..., description="Maximum value recorded across all timesteps")
    mean: float = Field(..., description="Mean value across all timesteps")


class FieldDataQualityStatus(BaseModel):
    """Data quality and completeness audit for the field time-series."""
    total_observations: int = Field(default=10, description="Total planned temporal observations")
    valid_observations: int = Field(default=10, description="Number of numerically valid observations")
    is_complete: bool = Field(default=True, description="Whether full sequence is present")
    has_anomalies: bool = Field(default=False, description="Whether NaN or infinite values were detected")
    interpolation_note: str = Field(
        default="Time-series regularized via linear temporal interpolation across verified Sentinel-2 acquisition dates.",
        description="Clarification on temporal regularization methodology",
    )


class IndexClassification(BaseModel):
    """Categorical classification for an individual vegetation index."""
    category: str = Field(..., description="'healthy', 'moderate', or 'unhealthy'")
    label: str = Field(..., description="Display badge label: 'Healthy', 'Moderate', or 'Unhealthy'")
    badge_color: str = Field(..., description="Visual badge color: 'green', 'amber', or 'red'")
    condition_name: Optional[str] = Field(None, description="Condition description title (e.g. 'Low Green Vegetation Index')")
    current_status: Optional[str] = Field(None, description="Current health status (Healthy, Moderate, Unhealthy)")
    historical_trend: Optional[str] = Field(None, description="Historical trend trajectory (Improving, Stable, Declining)")
    description: str = Field(..., description="Short scientific explanation of vegetation condition")
    combined_explanation: Optional[str] = Field(
        None, description="Integrated scientific explanation connecting current health status and historical trend direction"
    )
    threshold_range: str = Field(..., description="Applied numerical threshold range")


class OverallHealthAssessment(BaseModel):
    """Overall multi-metric field health synthesis."""
    status: str = Field(..., description="'Healthy', 'Moderate Stress', 'High Vegetation Stress', or 'Insufficient Data'")
    label: str = Field(..., description="Human-readable status label")
    color: str = Field(..., description="'green', 'amber', 'red', or 'gray'")
    current_condition: Optional[str] = Field(None, description="Synthesized current vegetative condition state")
    historical_trajectory: Optional[str] = Field(None, description="Synthesized multi-temporal trend direction")
    growth_stage_context: Optional[str] = Field(None, description="Context regarding growth stage and provisional calibration")
    conflicting_indicators: Optional[List[str]] = Field(default_factory=list, description="Any detected spectral conflicts between indices")
    summary: str = Field(..., description="Multi-metric synthesis summary")
    observations: List[str] = Field(default_factory=list, description="Important satellite observations")
    stress_indicators: List[str] = Field(default_factory=list, description="Identified vegetation stress indicators")
    recommended_actions: List[str] = Field(default_factory=list, description="Actionable on-ground inspection guidance")
    scientific_disclaimer: str = Field(
        default="Satellite vegetation indices quantify canopy greenness, density, and chlorophyll reflectance; they do not diagnose specific bacterial, fungal, or viral pathogens. Low index values indicate vegetation stress, not confirmed plant disease. Field scouting is required for pathogen diagnosis.",
        description="Scientific guardrail clarifying scope of satellite indices",
    )


class ThresholdMetadata(BaseModel):
    """Metadata regarding applied classification thresholds."""
    status: str = Field(default="provisional", description="'provisional' or 'validated'")
    is_validated: bool = Field(default=False, description="Whether thresholds have local ground-truth calibration")
    source: str = Field(..., description="Scientific or empirical source reference")
    methodology: str = Field(..., description="Description of threshold derivation method")
    growth_stage_support: Optional[Dict[str, Any]] = Field(None, description="Growth stage support registry and calibration status")
    growth_stage_sensitivity: str = Field(..., description="Explanation regarding crop growth stage variation")
    boundary_definitions: Optional[Dict[str, Dict[str, str]]] = Field(None, description="Mathematical interval definitions")
    calibration_notes: str = Field(..., description="Guidance on interpreting provisional thresholds")


class FieldHealthResponse(BaseModel):
    """
    Standard response payload for GET /fields/{field_id}/health.
    Provides real measured vegetation indices, changes, trends, and
    provisional multi-metric health classifications.
    """
    field_id: str = Field(..., description="Field identifier (e.g. FIELD_01)")
    growth_stage: Optional[str] = Field(None, description="Reported or evaluated crop growth stage")
    clean_field_id: Optional[str] = Field(None, description="Standardized clean field identifier")
    coordinates: Optional[Dict[str, float]] = Field(None, description="Centroid GPS coordinates (latitude, longitude)")
    observation_count: int = Field(..., description="Number of satellite observations processed")
    latest_observation_date: Optional[str] = Field(None, description="Date of the latest observation (YYYY-MM-DD)")
    previous_observation_date: Optional[str] = Field(None, description="Date of the preceding observation (YYYY-MM-DD)")
    latest_indices: VegetationIndexValues = Field(..., description="Vegetation index values at latest observation")
    previous_indices: VegetationIndexValues = Field(..., description="Vegetation index values at preceding observation")
    changes_and_trends: Dict[str, IndexTrendMetric] = Field(
        ..., description="Changes and cautious trend directions for NDVI, NDRE, and GNDVI"
    )
    summary_statistics: Dict[str, IndexSummaryStatistics] = Field(
        ..., description="Trajectory summary statistics (min, max, mean) for each feature"
    )
    data_quality_status: FieldDataQualityStatus = Field(..., description="Data completeness and quality report")
    classifications: Optional[Dict[str, IndexClassification]] = Field(
        None, description="Healthy/Moderate/Unhealthy classifications for NDVI, NDRE, GNDVI"
    )
    overall_health: Optional[OverallHealthAssessment] = Field(
        None, description="Synthesized overall field health assessment"
    )
    threshold_metadata: Optional[ThresholdMetadata] = Field(
        None, description="Provisional threshold documentation and metadata"
    )
    health_classification_status: str = Field(
        default="unvalidated",
        description="Indicates that categorical health classification is provisional/unvalidated",
    )
    health_category: Optional[str] = Field(
        default=None,
        description="Fixed categorical health label (None because arbitrary static thresholds are unvalidated)",
    )
    advisory_summary: str = Field(..., description="Cautious agronomic summary grounded strictly in measured indices")
    limitations_and_interpretation_notes: List[str] = Field(
        ..., description="Scientifically sound interpretation notes and operational limitations"
    )


class HealthThresholds(BaseModel):
    """Calibrated agronomic NDVI thresholds for paddy canopy vigor."""
    healthy: str = Field(..., description="Threshold description for healthy canopy")
    needs_attention: str = Field(..., description="Threshold description for moderate canopy")
    high_risk: str = Field(..., description="Threshold description for stressed canopy")


class FieldHealthSummaryResponse(BaseModel):
    """Aggregate health classification summary across all monitored fields."""
    total_fields: int = Field(..., description="Total number of monitored fields")
    healthy_count: int = Field(..., description="Number of fields with NDVI >= 0.60")
    needs_attention_count: int = Field(..., description="Number of fields with 0.35 <= NDVI < 0.60")
    high_risk_count: int = Field(..., description="Number of fields with NDVI < 0.35")
    healthy_pct: float = Field(..., description="Percentage of healthy fields")
    needs_attention_pct: float = Field(..., description="Percentage of fields needing attention")
    high_risk_pct: float = Field(..., description="Percentage of high risk fields")
    mean_ndvi: float = Field(..., description="Mean latest NDVI across all fields")
    thresholds: HealthThresholds = Field(..., description="Agronomic threshold definitions")

