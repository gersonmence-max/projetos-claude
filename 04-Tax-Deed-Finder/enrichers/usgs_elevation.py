"""
USGS Elevation Point Query Service — gets slope/elevation for a coordinate.
Uses EPQS v1 JSON endpoint (free, no key required).
"""
import httpx

USGS_URL = "https://epqs.nationalmap.gov/v1/json"


async def get_elevation_slope(lat: float, lng: float) -> dict:
    """
    Fetches elevation at the parcel coordinate.
    Estimates slope by sampling 4 nearby points (100m offset).
    """
    delta = 0.001  # ~100 meters

    async def _elev(a: float, b: float) -> float:
        params = {"x": b, "y": a, "units": "Meters", "output": "json"}
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(USGS_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return float(data.get("value") or data.get("elevation") or 0)
            except Exception:
                return 0.0

    center = await _elev(lat, lng)
    north = await _elev(lat + delta, lng)
    south = await _elev(lat - delta, lng)
    east = await _elev(lat, lng + delta)
    west = await _elev(lat, lng - delta)

    # Estimate slope as max rise/run over ~111m
    dist_m = 111.0  # meters per 0.001 degree approx
    slopes = [
        abs(north - center) / dist_m * 100,
        abs(south - center) / dist_m * 100,
        abs(east - center) / dist_m * 100,
        abs(west - center) / dist_m * 100,
    ]
    avg_slope = sum(slopes) / len(slopes)

    return {
        "elevation_m": round(center, 1),
        "slope_percent": round(avg_slope, 2),
        "source": "usgs_epqs",
    }
