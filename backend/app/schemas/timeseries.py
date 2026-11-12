"""
Paddy Farming Assistant - Pydantic Schemas for Satellite Time-Series (STEP 11D.2)
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class SatelliteTimestep(BaseModel):
    """
    Represents a single temporal observation in the Sentinel-2 sequence.
    """
    timestep: int = Field(..., description="1-indexed timestep sequence number (1 to 10)")
    date: Optional[str] = Field(None, description="Observation date (YYYY-MM-DD), if available from project artifacts")
    ndvi: float = Field(..., description="Normalized Difference Vegetation Index")
    ndre: float = Field(..., description="Normalized Difference Red Edge")
    gndvi: float = Field(..., description="Green Normalized Difference Vegetation Index")


class SatelliteTimeSeriesResponse(BaseModel):
    """
    Response schema for GET /fields/{field_id}/timeseries.
    """
    field_id: str = Field(..., description="Authoritative field identifier (e.g., FIELD_01)")
    clean_field_id: Optional[str] = Field(None, description="Clean field cluster identifier (e.g., CLEAN_FIELD_001)")
    sequence_index: int = Field(..., description="0-indexed sequence position in bilstm_sequences.npy")
    features: List[str] = Field(default=["NDVI", "NDRE", "GNDVI"], description="Ordered list of feature names")
    total_timesteps: int = Field(default=10, description="Total number of timesteps in the sequence")
    coordinates: Optional[Dict[str, float]] = Field(None, description="Field centroid coordinates (latitude, longitude)")
    has_dates: bool = Field(..., description="Whether observation dates are available from project artifacts")
    timesteps: List[SatelliteTimestep] = Field(..., description="Chronological list of 10 satellite observations")
