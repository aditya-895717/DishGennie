"""
Distance helpers for the "maids near me" search.

Deliberately plain Python + a bounding-box prefilter rather than PostGIS:
Architecture.md §11 lists GeoDjango/PostGIS as a future scale-up, and the
current catchment is a handful of maids per city. The bounding box keeps the
rows pulled out of Postgres proportional to the search radius; the exact
haversine filter then runs over that small set.
"""
import math

EARTH_RADIUS_KM = 6371.0
KM_PER_DEGREE_LAT = 111.0
DEFAULT_RADIUS_KM = 10.0
MAX_RADIUS_KM = 100.0


def parse_coordinate(value, limit):
    """Return a float in [-limit, limit], or None if it isn't a usable number."""
    if value in (None, ''):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number) or abs(number) > limit:
        return None
    return number


def parse_radius_km(value):
    try:
        radius = float(value)
    except (TypeError, ValueError):
        return DEFAULT_RADIUS_KM
    if radius <= 0:
        return DEFAULT_RADIUS_KM
    return min(radius, MAX_RADIUS_KM)


def bounding_box(lat, lng, radius_km):
    """Coarse lat/lng window enclosing the circle, for the SQL prefilter."""
    lat_delta = radius_km / KM_PER_DEGREE_LAT
    # Longitude degrees shrink towards the poles; guard the cos(90°) → 0 case.
    cos_lat = max(math.cos(math.radians(lat)), 0.01)
    lng_delta = radius_km / (KM_PER_DEGREE_LAT * cos_lat)
    return (
        max(lat - lat_delta, -90.0),
        min(lat + lat_delta, 90.0),
        lng - lng_delta,
        lng + lng_delta,
    )


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def maid_coordinates(profile):
    """Best known position for a maid: her last tracked fix, else the
    coordinates saved on her account. Returns (lat, lng) or None."""
    for lat, lng in (
        (profile.current_lat, profile.current_lng),
        (profile.user.latitude, profile.user.longitude),
    ):
        if lat is not None and lng is not None:
            return float(lat), float(lng)
    return None
