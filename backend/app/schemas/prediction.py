"""
Paddy Farming Assistant - Prediction Pydantic Schemas (STEP 11F.8)
Defines schemas for prediction history records and audit queries.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class PredictionRecordResponse(BaseModel):
    """
    Schema representing a persisted AI diagnostic prediction record.
    """
    id: UUID = Field(..., description="Unique prediction identifier")
    field_id: Optional[UUID] = Field(None, description="Linked field identifier, if provided")
    prediction_mode: str = Field(..., description="'image_only' (13 classes) or 'multimodal' (11 classes)")
    model_name: str = Field(..., description="AI model architecture name")
    model_version: str = Field(..., description="Checkpoint artifact identifier")
    predicted_disease: str = Field(..., description="Top predicted disease label")
    predicted_class_index: int = Field(..., description="Model class index (0-12 or 0-10)")
    confidence: float = Field(..., description="Softmax confidence probability score [0.0 - 1.0]")
    is_healthy: bool = Field(default=False, description="Whether leaf is classified as normal (healthy)")
    low_confidence: bool = Field(default=False, description="Flag indicating low confidence (< 0.60)")
    top_k_predictions: List[Dict[str, Any]] = Field(default_factory=list, description="Top candidates list")
    attention_weights: Optional[List[float]] = Field(None, description="10-step attention weights for multimodal")
    image_sha256: Optional[str] = Field(None, description="SHA-256 hash of input image")
    farmer_question: Optional[str] = Field(None, description="Farmer advisory query text")
    response_language: str = Field(default="en", description="Advisory language")
    inference_latency_ms: Optional[float] = Field(None, description="Inference latency in milliseconds")
    device: str = Field(default="cpu", description="Execution hardware device")
    created_at: datetime = Field(..., description="Inference creation timestamp in UTC")


class PredictionListResponse(BaseModel):
    """
    Paginated response schema for listing historical predictions.
    """
    predictions: List[PredictionRecordResponse] = Field(..., description="List of prediction records")
    total_predictions: int = Field(..., description="Total count of predictions matching query")
    page: Optional[int] = Field(default=1, description="Current page number")
    page_size: Optional[int] = Field(default=50, description="Items per page")
