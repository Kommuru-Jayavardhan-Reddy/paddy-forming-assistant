"""
Paddy Farming Assistant - Report Pydantic Schemas (STEP 11I.2)
Defines request and response schemas for diagnostic report generation and retrieval.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class ReportResponse(BaseModel):
    """
    Schema representing a compiled diagnostic or agronomic report.
    Protects privacy: excludes raw filesystem paths and internal storage locations.
    """
    id: UUID = Field(..., description="Unique report document identifier")
    prediction_id: Optional[UUID] = Field(None, description="Associated disease prediction run identifier")
    field_id: Optional[UUID] = Field(None, description="Associated agricultural field parcel identifier")
    report_type: str = Field(..., description="Category: 'disease_diagnostic', 'field_health_summary', etc.")
    title: str = Field(..., description="Human-readable title of the compiled report")
    summary: Optional[str] = Field(None, description="Executive summary of key findings and advisories")
    status: str = Field(..., description="Document generation status: 'completed', 'generating', 'failed'")
    file_format: str = Field(default="json", description="Report artifact format ('json', 'pdf')")
    file_size_bytes: Optional[int] = Field(None, description="Document artifact size in bytes")
    report_metadata: Optional[Dict[str, Any]] = Field(None, description="Detailed diagnostic parameters, candidate predictions, and advisory disclaimer")
    generated_by: str = Field(default="system", description="Process that generated report")
    created_at: datetime = Field(..., description="Report generation timestamp in UTC")


class ReportListResponse(BaseModel):
    """
    Paginated list of compiled reports.
    """
    reports: List[ReportResponse] = Field(..., description="List of report records")
    total_reports: int = Field(..., description="Total count matching query filters")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=50, description="Items per page")


class ReportGenerateRequest(BaseModel):
    """
    Optional payload for triggering report generation.
    """
    force_regenerate: bool = Field(default=False, description="Whether to generate a fresh report if one already exists")
    file_format: str = Field(default="json", description="Target artifact format ('json', 'pdf')")
