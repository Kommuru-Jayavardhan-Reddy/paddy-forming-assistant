"""
Paddy Farming Assistant - Pydantic Schemas for Weather Endpoints (STEP 11E.4)
Defines structured response models for current weather, multi-day forecast,
and field-level meteorological advisories using Open-Meteo observations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class WeatherCoordinates(BaseModel):
    """Geographic WGS84 coordinates and elevation for meteorological observation."""
    latitude: float = Field(..., description="WGS84 latitude coordinate")
    longitude: float = Field(..., description="WGS84 longitude coordinate")
    elevation: Optional[float] = Field(None, description="Elevation above sea level in meters")


class WeatherUnits(BaseModel):
    """Standardized measurement units for atmospheric observations."""
    temperature: str = Field(default="°C", description="Temperature measurement unit")
    relative_humidity: str = Field(default="%", description="Relative humidity measurement unit")
    precipitation: str = Field(default="mm", description="Precipitation/rainfall measurement unit")
    wind_speed: str = Field(default="km/h", description="Wind speed measurement unit")


class CurrentWeatherObservation(BaseModel):
    """Real-time atmospheric observations from Open-Meteo."""
    time: Optional[str] = Field(None, description="ISO-8601 observation timestamp")
    interval_seconds: Optional[int] = Field(None, description="Observation update interval in seconds")
    temperature: Optional[float] = Field(None, description="Surface air temperature at 2m (°C)")
    temperature_unit: str = Field(default="°C", description="Temperature unit")
    relative_humidity: Optional[float] = Field(None, description="Relative humidity at 2m (%)")
    relative_humidity_unit: str = Field(default="%", description="Humidity unit")
    precipitation: Optional[float] = Field(None, description="Total current precipitation (mm)")
    precipitation_unit: str = Field(default="mm", description="Precipitation unit")
    rain: Optional[float] = Field(None, description="Current liquid rainfall (mm)")
    rain_unit: str = Field(default="mm", description="Rain unit")
    wind_speed: Optional[float] = Field(None, description="Wind speed at 10m (km/h)")
    wind_speed_unit: str = Field(default="km/h", description="Wind speed unit")
    weather_code: Optional[int] = Field(None, description="World Meteorological Organization (WMO) numeric code")
    weather_condition: Optional[str] = Field(None, description="Descriptive weather condition name")


class DailyForecastItem(BaseModel):
    """Daily forecast summary metrics for agricultural planning."""
    date: str = Field(..., description="Forecast date (YYYY-MM-DD)")
    temperature_max: Optional[float] = Field(None, description="Maximum predicted daytime temperature (°C)")
    temperature_min: Optional[float] = Field(None, description="Minimum predicted nighttime temperature (°C)")
    temperature_unit: str = Field(default="°C", description="Temperature unit")
    precipitation_sum: Optional[float] = Field(None, description="Expected daily precipitation sum (mm)")
    precipitation_unit: str = Field(default="mm", description="Precipitation unit")
    rain_sum: Optional[float] = Field(None, description="Expected daily rain sum (mm)")
    rain_sum_unit: str = Field(default="mm", description="Rain unit")
    wind_speed_max: Optional[float] = Field(None, description="Maximum predicted wind gust/speed (km/h)")
    wind_speed_unit: str = Field(default="km/h", description="Wind speed unit")
    weather_code: Optional[int] = Field(None, description="WMO numeric weather code")
    weather_condition: Optional[str] = Field(None, description="Descriptive daily condition name")


class CurrentWeatherResponse(BaseModel):
    """Response schema for GET /weather/current."""
    provider: str = Field(default="Open-Meteo", description="Weather data provider")
    coordinates: WeatherCoordinates = Field(..., description="Observation geographic coordinates")
    timezone: Optional[str] = Field(None, description="Timezone name")
    current: Optional[CurrentWeatherObservation] = Field(None, description="Current atmospheric observation")
    units: WeatherUnits = Field(..., description="Standard measurement units")


class WeatherForecastResponse(BaseModel):
    """Response schema for GET /weather/forecast."""
    provider: str = Field(default="Open-Meteo", description="Weather data provider")
    coordinates: WeatherCoordinates = Field(..., description="Observation geographic coordinates")
    timezone: Optional[str] = Field(None, description="Timezone name")
    daily_forecast: List[DailyForecastItem] = Field(default_factory=list, description="List of daily forecast summaries")
    units: WeatherUnits = Field(..., description="Standard measurement units")


class FieldWeatherResponse(BaseModel):
    """Response schema for GET /fields/{field_id}/weather."""
    field_id: str = Field(..., description="Canonical field identifier (e.g., FIELD_01)")
    requested_field_id: str = Field(..., description="Original requested field identifier")
    clean_field_id: Optional[str] = Field(None, description="Clean field cluster identifier")
    provider: str = Field(default="Open-Meteo", description="Weather data provider")
    coordinates: WeatherCoordinates = Field(..., description="Resolved field centroid coordinates")
    timezone: Optional[str] = Field(None, description="Timezone name")
    timezone_abbreviation: Optional[str] = Field(None, description="Timezone abbreviation (e.g., IST)")
    utc_offset_seconds: Optional[int] = Field(None, description="UTC offset in seconds")
    current: Optional[CurrentWeatherObservation] = Field(None, description="Current atmospheric observation")
    daily_forecast: List[DailyForecastItem] = Field(default_factory=list, description="List of daily forecast summaries")
    units: WeatherUnits = Field(..., description="Standard measurement units")
