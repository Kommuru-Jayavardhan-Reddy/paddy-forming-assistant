"""
Paddy Farming Assistant - Field Pydantic Schemas (STEP 11F.8)
Defines request and response schemas for agricultural field operations.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal
from datetime import date
from pydantic import BaseModel, Field


class FieldItemResponse(BaseModel):
    """
    Schema for a field item in the fields catalog response.
    Maintains full backward compatibility with frontend consumers.
    """
    field_id: str = Field(..., description="Authoritative external identifier (e.g. 'FIELD_01')")
    external_field_id: str = Field(..., description="Natural unique field identifier")
    clean_field_id: Optional[str] = Field(None, description="Cluster clean identifier")
    field_name: Optional[str] = Field(None, description="Human-readable field name")
    latitude: float = Field(..., description="Centroid WGS84 latitude")
    longitude: float = Field(..., description="Centroid WGS84 longitude")
    area_hectares: Optional[float] = Field(None, description="Surface area in hectares")
    crop_variety: Optional[str] = Field(None, description="Cultivated paddy variety")
    is_active: bool = Field(default=True, description="Active status")
    has_images: bool = Field(default=False, description="Flag indicating presence of paired leaf images")
    is_user_created: bool = Field(default=False, description="Flag indicating if field is user-entered")


class FieldListResponse(BaseModel):
    """
    Paginated response schema for GET /fields.
    """
    fields: List[FieldItemResponse] = Field(..., description="List of agricultural fields")
    total_fields: int = Field(..., description="Total count of fields matching query")
    page: Optional[int] = Field(default=1, description="Current page number")
    page_size: Optional[int] = Field(default=100, description="Items per page")


class FieldDetailResponse(FieldItemResponse):
    """
    Detailed response schema for GET /fields/{field_id}.
    """
    id: UUID = Field(..., description="Internal PostgreSQL UUID primary key")
    elevation_m: Optional[float] = Field(None, description="Elevation in meters")
    sowing_date: Optional[date] = Field(None, description="Sowing or transplantation date")
    observation_count: Optional[int] = Field(default=0, description="Number of associated satellite observations")


class FieldCreateRequest(BaseModel):
    """
    Schema for creating a new user-entered agricultural field.
    """
    field_name: str = Field(..., min_length=1, max_length=150, description="Name or title of the field")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude coordinate")
    external_field_id: Optional[str] = Field(None, max_length=50, description="Custom field identifier (optional)")
    area_hectares: Optional[float] = Field(None, ge=0.01, description="Field area in hectares")
    crop_variety: Optional[str] = Field(None, max_length=100, description="Planted crop or paddy variety")


class FieldGpsExtractResponse(BaseModel):
    """
    Schema for GPS extraction from image (EXIF or OCR).
    """
    found: bool = Field(..., description="Whether valid GPS coordinates were extracted")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude coordinate")
    latitude_ref: Optional[str] = Field(None, description="Latitude hemisphere ('N' or 'S')")
    longitude_ref: Optional[str] = Field(None, description="Longitude hemisphere ('E' or 'W')")
    source: str = Field(..., description="Extraction source ('EXIF Metadata', 'Image Text (OCR)', or 'None')")
    status: str = Field(..., description="Extraction outcome status ('Successful' or 'Not Found')")
    location_name: Optional[str] = Field(None, description="Human-readable location name or address")
    village: Optional[str] = Field(None, description="Detected village name")
    date_time: Optional[str] = Field(None, description="Detected photo timestamp")
    message: Optional[str] = Field(None, description="Informational message or failure reason")


