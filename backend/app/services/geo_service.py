"""
Paddy Farming Assistant - Geospatial & Distance Calculation Service (STEP 11H.5)
Implements great-circle geographical distance calculation using the Haversine formula
to enable nearest-buyer discovery for paddy farmers.
"""

import math
from typing import Optional

# WGS84 volumetric mean Earth radius in kilometers (IUGG recommended value)
EARTH_RADIUS_KM = 6371.0088


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Computes the great-circle geographical distance in kilometers between two points
    on Earth specified by WGS84 decimal degrees using the Haversine formula.

    Numerically safe against domain errors caused by floating-point clamping.
    Returns straight-line distance (great-circle), NOT road/driving distance.

    Args:
        lat1: Latitude of point 1 in degrees (-90.0 to 90.0)
        lon1: Longitude of point 1 in degrees (-180.0 to 180.0)
        lat2: Latitude of point 2 in degrees (-90.0 to 90.0)
        lon2: Longitude of point 2 in degrees (-180.0 to 180.0)

    Returns:
        Great-circle distance in kilometers rounded to two decimal places.
    """
    if not (-90.0 <= lat1 <= 90.0 and -90.0 <= lat2 <= 90.0):
        raise ValueError(f"Latitude must be between -90.0 and +90.0 degrees (got {lat1}, {lat2})")
    if not (-180.0 <= lon1 <= 180.0 and -180.0 <= lon2 <= 180.0):
        raise ValueError(f"Longitude must be between -180.0 and +180.0 degrees (got {lon1}, {lon2})")

    if lat1 == lat2 and lon1 == lon2:
        return 0.0

    # Convert decimal degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine formulation
    sin_dphi = math.sin(delta_phi / 2.0)
    sin_dlambda = math.sin(delta_lambda / 2.0)
    a = sin_dphi * sin_dphi + math.cos(phi1) * math.cos(phi2) * sin_dlambda * sin_dlambda

    # Numerical safety clamp to avoid domain error in math.atan2 / math.sqrt
    a_clamped = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a_clamped), math.sqrt(1.0 - a_clamped))

    distance = EARTH_RADIUS_KM * c
    return round(distance, 2)
