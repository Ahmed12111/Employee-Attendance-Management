"""
gps.py — GPS utilities and geofencing validation.
"""

import math
from typing import Tuple
from backend.config import settings

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in meters between two points
    on the earth (specified in decimal degrees) using Haversine formula.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371000  # Radius of earth in meters
    return c * r

def validate_location(employee_lat: float, employee_lon: float) -> Tuple[bool, float, str]:
    """
    Validates if the given coordinates are within the allowed radius of the company.
    Returns: (is_valid: bool, distance: float, message: str)
    """
    company_lat = settings.COMPANY_LATITUDE
    company_lon = settings.COMPANY_LONGITUDE
    allowed_radius = settings.ALLOWED_RADIUS_METERS

    distance = haversine_distance(company_lat, company_lon, employee_lat, employee_lon)
    distance_rounded = round(distance, 1)

    if distance_rounded <= allowed_radius:
        return True, distance_rounded, "Within allowed area."
    else:
        return False, distance_rounded, "You are outside the allowed attendance area."
