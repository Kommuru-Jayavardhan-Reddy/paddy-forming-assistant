"""
Paddy Farming Assistant - Multimodal Prediction Schemas (STEP 11D.3)
Defines Pydantic models for multimodal disease classification responses.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class MultimodalTopPrediction(BaseModel):
    """Individual disease candidate within top-k predictions."""
    disease: str = Field(..., description="Disease class name")
    probability: float = Field(..., description="Softmax confidence probability [0.0 - 1.0]")
    index: int = Field(..., description="Class index in the 11-class multimodal model")


class MultimodalPredictionResponse(BaseModel):
    """
    Standard response payload for POST /predict/multimodal.
    Clearly distinguishes multimodal prediction from image-only inference.
    """
    prediction_mode: str = Field(
        default="multimodal",
        description="Indicates whether prediction used multimodal or image-only inference",
    )
    field_id: str = Field(..., description="Verified field identifier used for satellite retrieval")
    predicted_class: str = Field(..., description="Top predicted paddy disease class")
    confidence: float = Field(..., description="Confidence score of top prediction [0.0 - 1.0]")
    top_3_predictions: List[MultimodalTopPrediction] = Field(
        ..., description="Top 3 candidate predictions with softmax probabilities"
    )
    image_model_status: str = Field(
        default="loaded", description="Loading and operational status of the EfficientNet-B4 image backbone"
    )
    satellite_model_status: str = Field(
        default="loaded", description="Operational status of the Sentinel-2 BiLSTM temporal encoder"
    )
    fusion_model_status: str = Field(
        default="loaded", description="Operational status of the Cross-Attention fusion network"
    )
    temporal_attention_weights: Optional[List[float]] = Field(
        default=None, description="Normalized cross-attention weights across the 10 satellite timesteps"
    )
    satellite_timesteps: int = Field(default=10, description="Number of satellite observations processed")
    device: str = Field(default="cpu", description="Hardware device used for local inference")
    note: str = Field(
        default="Multimodal prediction fuses leaf visual features with field satellite time-series for advisory guidance.",
        description="Scientifically grounded advisory note",
    )
    prediction_id: Optional[str] = Field(
        default=None,
        description="Unique database UUID for the persisted inference record",
    )
