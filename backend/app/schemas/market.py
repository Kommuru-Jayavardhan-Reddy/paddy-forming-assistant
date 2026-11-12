"""
Paddy Farming Assistant - Market Price Pydantic Schemas (STEP 11F.10)
Defines request and response schemas for agricultural market mandi prices.
"""

from typing import List, Optional
from datetime import date as dt_date, datetime as dt_datetime
from pydantic import BaseModel, Field, ConfigDict

# Aliases for convenience
date = dt_date
datetime = dt_datetime


class MarketPriceItem(BaseModel):
    """
    Schema representing a single agricultural mandi commodity price quotation.
    Matches the MarketPrice ORM model.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique market price record identifier")
    market_name: str = Field(..., description="Regulated agricultural market yard or APMC mandi name")
    district: str = Field(..., description="Administrative district name")
    state: str = Field(..., description="Administrative state name")
    commodity: str = Field(default="Paddy (Dhan)", description="Standardized commodity name")
    variety: str = Field(default="Common", description="Crop variety or cultivar (e.g. Common, Grade-A, BPT 5204)")
    grade: str = Field(default="FAQ", description="Standardized trade grade (e.g. FAQ)")
    min_price: float = Field(..., description="Minimum transaction price recorded per unit")
    max_price: float = Field(..., description="Maximum transaction price recorded per unit")
    modal_price: float = Field(..., description="Modal (representative benchmark) price per unit")
    currency: str = Field(default="INR", description="Currency ISO symbol (e.g. INR)")
    unit: str = Field(default="Quintal", description="Trade measurement unit (default 1 Quintal = 100 kg)")
    price_date: date = Field(..., description="Date quotation was posted in the market (YYYY-MM-DD)")
    source: str = Field(default="Agmarknet", description="Official public portal or source of quotation")
    retrieval_timestamp: Optional[datetime] = Field(None, description="Data ingestion timestamp in UTC")
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp in UTC")


class MarketPriceListResponse(BaseModel):
    """
    Paginated response schema for listing agricultural mandi prices.
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[MarketPriceItem] = Field(default_factory=list, description="List of market price records")
    total: int = Field(default=0, description="Total count of records matching query")
    skip: int = Field(default=0, description="Offset pagination index")
    limit: int = Field(default=50, description="Maximum number of items returned")
    data_source: Optional[str] = Field("database", description="Origin of returned prices ('live_synced', 'database_cache', 'database_stale', 'empty')")
    is_stale: Optional[bool] = Field(False, description="True if records are older than freshness threshold or live retrieval failed")
    freshness_date: Optional[date] = Field(None, description="Most recent price quotation date among returned records")



class MarketSyncResponse(BaseModel):
    """
    Response schema for POST /market/sync live data synchronization.
    Provides diagnostic counts of upstream retrieved, accepted, rejected, and persisted quotes.
    """
    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., description="Sync execution status ('success', 'blocked', 'error')")
    provider: str = Field(default="Data.gov.in (Agmarknet)", description="Upstream market data provider")
    upstream_status_code: Optional[int] = Field(None, description="HTTP status code received from upstream API")
    records_retrieved: int = Field(default=0, description="Total raw records retrieved from upstream API")
    records_accepted: int = Field(default=0, description="Number of valid records accepted after validation")
    records_rejected: int = Field(default=0, description="Number of invalid records rejected")
    records_persisted: int = Field(default=0, description="Number of records inserted or updated in PostgreSQL")
    state: str = Field(default="Andhra Pradesh", description="State queried")
    district: Optional[str] = Field(None, description="District queried, if filtered")
    synced_at: datetime = Field(..., description="Timestamp when sync was executed in UTC")
    detail: str = Field(..., description="Summary or operational detail message")


class MarketSummaryResponse(BaseModel):
    """
    Response schema for GET /market/analytics/summary.
    Aggregates statistical indicators across all matching mandi observations.
    """
    model_config = ConfigDict(from_attributes=True)

    state: Optional[str] = Field(None, description="State queried")
    district: Optional[str] = Field(None, description="District queried, if filtered")
    commodity: str = Field(default="Paddy (Dhan)", description="Commodity analyzed")
    variety: Optional[str] = Field(None, description="Variety analyzed, if filtered")
    has_data: bool = Field(..., description="True if database contains matching records")
    total_observations: int = Field(default=0, description="Total number of price quotations")
    distinct_markets: int = Field(default=0, description="Count of distinct regulated mandis")
    distinct_districts: int = Field(default=0, description="Count of distinct administrative districts")
    distinct_varieties: int = Field(default=0, description="Count of distinct crop varieties")
    avg_modal_price: Optional[float] = Field(None, description="Average representative modal price in INR/Quintal")
    min_modal_price: Optional[float] = Field(None, description="Lowest recorded modal price in INR/Quintal")
    max_modal_price: Optional[float] = Field(None, description="Highest recorded modal price in INR/Quintal")
    min_transaction_price: Optional[float] = Field(None, description="Absolute minimum transaction price recorded")
    max_transaction_price: Optional[float] = Field(None, description="Absolute maximum transaction price recorded")
    earliest_price_date: Optional[date] = Field(None, description="Date of earliest matching quotation")
    latest_price_date: Optional[date] = Field(None, description="Date of most recent matching quotation")
    currency: str = Field(default="INR", description="Price currency symbol")
    unit: str = Field(default="Quintal", description="Standard measurement unit (1 Quintal = 100 kg)")


class DailyTrendPoint(BaseModel):
    """
    Daily aggregated price point for time-series trend analysis.
    """
    model_config = ConfigDict(from_attributes=True)

    date: dt_date = Field(..., description="Observation trading date (YYYY-MM-DD)")
    avg_modal_price: float = Field(..., description="Volume-unweighted average modal price across mandis on date")
    min_modal_price: float = Field(..., description="Lowest modal price across reporting mandis on date")
    max_modal_price: float = Field(..., description="Highest modal price across reporting mandis on date")
    observation_count: int = Field(..., description="Number of mandi reports for date")
    currency: str = Field(default="INR", description="Currency symbol")
    unit: str = Field(default="Quintal", description="Unit of measurement")


class MarketTrendsResponse(BaseModel):
    """
    Response schema for GET /market/analytics/trends.
    Presents historical daily trend trajectory and direction.
    """
    model_config = ConfigDict(from_attributes=True)

    state: Optional[str] = Field(None, description="State analyzed")
    district: Optional[str] = Field(None, description="District analyzed, if filtered")
    commodity: str = Field(default="Paddy (Dhan)", description="Commodity analyzed")
    variety: Optional[str] = Field(None, description="Variety analyzed, if filtered")
    days_requested: int = Field(..., description="Number of calendar days in requested analysis window")
    days_with_data: int = Field(default=0, description="Number of distinct trading days with available reports")
    start_date: Optional[date] = Field(None, description="Earliest observation date within window")
    end_date: Optional[date] = Field(None, description="Latest observation date within window")
    total_observations: int = Field(default=0, description="Total individual mandi quotations within window")
    start_modal_price: Optional[float] = Field(None, description="Average modal price on earliest trading day in window")
    end_modal_price: Optional[float] = Field(None, description="Average modal price on latest trading day in window")
    absolute_change: Optional[float] = Field(None, description="Net price change between end and start dates in INR/Quintal")
    percentage_change: Optional[float] = Field(None, description="Percentage change over window")
    trend_direction: str = Field(default="insufficient_data", description="Trend direction: 'up', 'down', 'stable', or 'insufficient_data'")
    currency: str = Field(default="INR", description="Currency symbol")
    unit: str = Field(default="Quintal", description="Unit of measurement")
    daily_trends: List[DailyTrendPoint] = Field(default_factory=list, description="Ordered daily time series")


class DistrictPriceBenchmark(BaseModel):
    """
    District-level agricultural market price benchmark.
    """
    model_config = ConfigDict(from_attributes=True)

    district: str = Field(..., description="District name")
    avg_modal_price: float = Field(..., description="Average modal price within district")
    min_modal_price: float = Field(..., description="Lowest modal price recorded in district")
    max_modal_price: float = Field(..., description="Highest modal price recorded in district")
    difference_from_state_avg: Optional[float] = Field(None, description="Price spread relative to overall state average in INR/Quintal")
    percentage_diff_from_state_avg: Optional[float] = Field(None, description="Percentage deviation from state average")
    observation_count: int = Field(..., description="Total price quotations recorded in district")
    market_count: int = Field(..., description="Count of distinct mandis in district")
    latest_price_date: date = Field(..., description="Date of newest price report in district")
    currency: str = Field(default="INR", description="Currency symbol")
    unit: str = Field(default="Quintal", description="Unit of measurement")


class DistrictAnalyticsResponse(BaseModel):
    """
    Response schema for GET /market/analytics/districts.
    """
    model_config = ConfigDict(from_attributes=True)

    state: Optional[str] = Field(None, description="State analyzed")
    commodity: str = Field(default="Paddy (Dhan)", description="Commodity analyzed")
    days_analyzed: int = Field(..., description="Time window in days analyzed")
    state_avg_modal_price: Optional[float] = Field(None, description="Benchmark state average modal price")
    highest_price_district: Optional[str] = Field(None, description="District with highest average price")
    lowest_price_district: Optional[str] = Field(None, description="District with lowest average price")
    price_spread: Optional[float] = Field(None, description="Difference between highest and lowest district averages in INR/Quintal")
    districts: List[DistrictPriceBenchmark] = Field(default_factory=list, description="District benchmark rankings")


class VarietyPriceBenchmark(BaseModel):
    """
    Variety-level agricultural modal price benchmark.
    """
    model_config = ConfigDict(from_attributes=True)

    variety: str = Field(..., description="Crop trade variety / cultivar name")
    avg_modal_price: float = Field(..., description="Average modal price for variety")
    min_modal_price: float = Field(..., description="Lowest modal price recorded for variety")
    max_modal_price: float = Field(..., description="Highest modal price recorded for variety")
    observation_count: int = Field(..., description="Total quotation records for variety")
    district_count: int = Field(..., description="Number of districts reporting this variety")
    latest_price_date: date = Field(..., description="Date of newest price report for variety")
    currency: str = Field(default="INR", description="Currency symbol")
    unit: str = Field(default="Quintal", description="Unit of measurement")


class VarietyAnalyticsResponse(BaseModel):
    """
    Response schema for GET /market/analytics/varieties.
    """
    model_config = ConfigDict(from_attributes=True)

    state: Optional[str] = Field(None, description="State analyzed")
    commodity: str = Field(default="Paddy (Dhan)", description="Commodity analyzed")
    district: Optional[str] = Field(None, description="District analyzed, if filtered")
    days_analyzed: int = Field(..., description="Time window in days analyzed")
    premium_variety: Optional[str] = Field(None, description="Variety fetching the highest average modal price")
    standard_variety: Optional[str] = Field(None, description="Standard or baseline benchmark variety")
    varieties: List[VarietyPriceBenchmark] = Field(default_factory=list, description="Variety benchmark rankings")


