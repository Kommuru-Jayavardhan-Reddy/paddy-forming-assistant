"""
Paddy Farming Assistant - Buyer Pydantic Schemas (STEP 11F.10)
Defines request and response schemas for verified grain buyers, millers, and procurement agencies.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class BuyerItem(BaseModel):
    """
    Schema representing a verified wholesale grain buyer, miller, or agricultural procurement entity.
    Matches the Buyer ORM model.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique buyer identifier")
    business_name: str = Field(..., description="Registered legal enterprise or business trade name")
    buyer_type: str = Field(..., description="Entity category: 'mill', 'fpo', 'government_agency', 'wholesaler', 'trader'")
    district: str = Field(..., description="Administrative district location")
    state: str = Field(..., description="Administrative state location")
    address_summary: Optional[str] = Field(None, description="General business yard or market location address")
    contact_person: Optional[str] = Field(None, description="Designated procurement officer name")
    contact_phone: Optional[str] = Field(None, description="Verified business contact phone number")
    contact_email: Optional[str] = Field(None, description="Verified business contact email address")
    preferred_varieties: Optional[List[str]] = Field(default_factory=list, description="Accepted paddy varieties (e.g. ['BPT 5204', 'IR 64'])")
    min_procurement_quintals: Optional[float] = Field(None, description="Minimum batch procurement quantity in quintals")
    verification_status: str = Field(default="pending", description="Verification state: 'verified', 'pending', or 'unverified'")
    verification_notes: Optional[str] = Field(None, description="Administrative verification notes")
    is_active: bool = Field(default=True, description="Operational active status flag")
    latitude: Optional[float] = Field(None, description="WGS84 latitude coordinate")
    longitude: Optional[float] = Field(None, description="WGS84 longitude coordinate")
    coordinate_source: Optional[str] = Field(None, description="Provenance authority of verified coordinates")
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp in UTC")
    updated_at: Optional[datetime] = Field(None, description="Record update timestamp in UTC")


class BuyerListResponse(BaseModel):
    """
    Paginated response schema for listing verified buyers and grain procurement enterprises.
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[BuyerItem] = Field(default_factory=list, description="List of verified buyers and procurement entities")
    total: int = Field(default=0, description="Total count of buyers matching query")
    skip: int = Field(default=0, description="Offset pagination index")
    limit: int = Field(default=50, description="Maximum number of items returned")


class BuyerNearbyItem(BuyerItem):
    """
    Verified buyer profile augmented with great-circle geographical distance from farmer's location.
    """
    distance_km: float = Field(..., description="Great-circle geographical distance in kilometers (Haversine)")


class BuyerNearbyResponse(BaseModel):
    """
    Paginated response schema for GPS-based nearest-buyer search results.
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[BuyerNearbyItem] = Field(default_factory=list, description="Nearby buyers ranked by geographical distance ascending")
    total: int = Field(default=0, description="Total eligible buyers matching spatial radius and category filters")
    skip: int = Field(default=0, description="Offset pagination index")
    limit: int = Field(default=50, description="Maximum number of items returned")
    farmer_latitude: float = Field(..., description="Queried farmer WGS84 latitude")
    farmer_longitude: float = Field(..., description="Queried farmer WGS84 longitude")
    search_radius_km: Optional[float] = Field(None, description="Applied search radius boundary in kilometers, if specified")
    disclaimer: str = Field(
        default="Straight-line geographical distance (Haversine); actual road travel distance may vary.",
        description="Legal and technical distance disclaimer",
    )
