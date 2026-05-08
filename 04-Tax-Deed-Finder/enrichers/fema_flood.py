"""
FEMA National Flood Hazard Layer (NFHL) — flood zone lookup by coordinates.
Uses the FEMA ArcGIS REST service (free, no key required).
"""
import httpx
from typing import Optional

FEMA_URL = (
    "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
)


async def get_flood_zone(lat: float, lng: float) -> dict:
    """
    Returns flood zone designation for a coordinate.
    Zone X = minimal risk. A/AE/VE = high risk.
    """
    params = {
        "geometry": f"{lng},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "FLD_ZONE,ZONE_SUBTY,DFIRM_ID",
        "returnGeometry": "false",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(FEMA_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])
            if features:
                attrs = features[0]["attributes"]
                zone = attrs.get("FLD_ZONE") or "X"
                return {"flood_zone": zone, "source": "fema_nfhl"}
            return {"flood_zone": "X", "source": "fema_nfhl_no_data"}
        except Exception as e:
            return {"flood_zone": "UNKNOWN", "source": f"fema_error:{e}"}
