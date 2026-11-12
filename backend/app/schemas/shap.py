"""
Paddy Farming Assistant - SHAP Explanation Schemas (STEP 11D.6)
Defines structured response schemas for the temporal cross-attention SHAP explanation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TimestepFeatureAttribution(BaseModel):
    """
    Detailed attribution of a single satellite feature at a specific timestep.
    Preserves exact temporal association (1 to 10), observation date, and feature name (NDVI, NDRE, GNDVI).
    """
    timestep: int = Field(
        ...,
        description="Temporal observation index (1 to 10) corresponding to Sentinel-2 timeline.",
        ge=1,
        le=10,
    )
    observation_date: Optional[str] = Field(
        None,
        description="Authoritative Sentinel-2 acquisition date (YYYY-MM-DD), if available.",
    )
    feature: str = Field(
        ...,
        description="Vegetation index feature name (NDVI, NDRE, or GNDVI).",
    )
    satellite_value_raw: float = Field(
        ...,
        description="Original unnormalized satellite vegetation index observation.",
    )
    satellite_value_normalized: float = Field(
        ...,
        description="Normalized satellite value fed into the temporal BiLSTM encoder.",
    )
    shap_value: float = Field(
        ...,
        description="Signed SHAP attribution value for the target class logit.",
    )
    contribution: str = Field(
        ...,
        description="Qualitative direction: 'positive', 'negative', or 'neutral'.",
    )
    absolute_shap_value: float = Field(
        ...,
        description="Absolute attribution magnitude indicating feature importance.",
    )


class FeatureImportanceSummary(BaseModel):
    """
    Aggregated feature-level attribution summary across all 10 timesteps.
    """
    feature: str = Field(
        ...,
        description="Vegetation index feature name (NDVI, NDRE, or GNDVI).",
    )
    mean_absolute_shap: float = Field(
        ...,
        description="Mean absolute SHAP value across the 10 timesteps.",
    )
    positive_shap_sum: float = Field(
        ...,
        description="Sum of positive contributions pushing toward the target class.",
    )
    negative_shap_sum: float = Field(
        ...,
        description="Sum of negative contributions pushing away from the target class.",
    )
    net_shap: float = Field(
        ...,
        description="Net signed attribution sum across all 10 timesteps.",
    )


class StrongestContribution(BaseModel):
    """
    Ranked top contribution entry (positive or negative) with descriptive explanation.
    """
    rank: int = Field(..., description="Contribution rank (1 = strongest impact).", ge=1)
    timestep: int = Field(..., description="Timestep (1 to 10).", ge=1, le=10)
    observation_date: Optional[str] = Field(
        None,
        description="Authoritative Sentinel-2 acquisition date (YYYY-MM-DD), if available.",
    )
    feature: str = Field(..., description="Vegetation index (NDVI, NDRE, GNDVI).")
    satellite_value_raw: float = Field(..., description="Observed raw satellite index value.")
    shap_value: float = Field(..., description="Signed SHAP attribution score.")
    direction: str = Field(..., description="Impact direction: 'positive' or 'negative'.")
    impact_description: str = Field(
        ...,
        description="Human-interpretable explanation of how this feature influenced the class logit.",
    )


class SHAPExplanationResponse(BaseModel):
    """
    Standardized API response schema for POST /explain/shap.
    """
    status: str = Field("success", description="Status string ('success').")
    field_id: str = Field(..., description="Queried canonical field identifier.")
    predicted_class: str = Field(..., description="Multimodal model's top predicted disease class.")
    predicted_index: int = Field(..., description="Zero-based index of the predicted class.")
    confidence: float = Field(..., description="Softmax confidence probability for top predicted class.")
    target_class: str = Field(..., description="Disease class for which SHAP attributions were computed.")
    target_index: int = Field(..., description="Zero-based index of the target class.")
    explanation_target_model: str = Field(
        "TemporalCrossAttentionModel (Controlled Step 7L)",
        description="Exact deep learning architecture and checkpoint explained.",
    )
    explanation_scope: str = Field(
        "conditional_satellite_input",
        description="Explicit scope: 'conditional_satellite_input' (explains temporal satellite branch conditioned on the fixed leaf image embedding).",
    )
    explanation_modality: str = Field(
        "Satellite Temporal Time-Series (conditioned on EfficientNet-B4 image features)",
        description="Input modality explained and conditioning context.",
    )
    input_feature_names: List[str] = Field(
        ["NDVI", "NDRE", "GNDVI"],
        description="List of satellite feature names in canonical order.",
    )
    shap_dimensions: List[int] = Field(
        [10, 3],
        description="Shape of the raw SHAP attributions array [timesteps, features].",
    )
    explanation_method: str = Field(
        "GradientExplainer",
        description="SHAP explainer algorithm used (GradientExplainer).",
    )
    background_samples_count: int = Field(
        20,
        description="Number of verified background field sequences used as reference baseline.",
    )
    nsamples: int = Field(
        100,
        description="Number of Monte Carlo background samples evaluated per explanation.",
    )
    target_logit: float = Field(
        ...,
        description="Unnormalized model output score (logit) for the target disease class.",
    )
    feature_importance_summary: List[FeatureImportanceSummary] = Field(
        ...,
        description="Summary of overall importance for each vegetation index across all timesteps.",
    )
    top_positive_contributions: List[StrongestContribution] = Field(
        ...,
        description="Top temporal feature observations that most increased the target disease logit.",
    )
    top_negative_contributions: List[StrongestContribution] = Field(
        ...,
        description="Top temporal feature observations that most decreased the target disease logit.",
    )
    timestep_attributions: List[TimestepFeatureAttribution] = Field(
        ...,
        description="Complete list of all 30 (10 timesteps x 3 features) attribution records.",
    )
    limitations_note: str = Field(
        ...,
        description="Scientific interpretability disclaimer regarding attribution bounds and causality.",
    )
