import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.gps import validate_location
from backend.config import settings

print("--- GPS Configuration ---")
print(f"Company Location: {settings.COMPANY_LATITUDE}, {settings.COMPANY_LONGITUDE}")
print(f"Allowed Radius: {settings.ALLOWED_RADIUS_METERS}m\n")

print("--- Backend Validation Tests ---")
# Test 1: Exact location
valid, dist, msg = validate_location(29.870403, 31.317111)
print(f"Test 1 (Exact Match): \n  Valid={valid} \n  Distance={dist}m \n  Msg='{msg}'\n")

# Test 2: Edge case (approx 73 meters away)
# 1 degree lat is ~111km, so 73m is ~0.00065 degrees
valid, dist, msg = validate_location(29.870403 + 0.00065, 31.317111)
print(f"Test 2 (Inside Radius ~73m): \n  Valid={valid} \n  Distance={dist}m \n  Msg='{msg}'\n")

# Test 3: Outside radius (approx 120 meters away)
valid, dist, msg = validate_location(29.870403 + 0.00110, 31.317111)
print(f"Test 3 (Outside Radius ~120m): \n  Valid={valid} \n  Distance={dist}m \n  Msg='{msg}'\n")
