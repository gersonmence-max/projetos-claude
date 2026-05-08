"""
FWS Wetlands Mapper — estimates wetland coverage % for a parcel bounding box.
Uses the US Fish & Wildlife Service WMS/WFS endpoint (free, no key).
"""
import httpx
from typing import Optional

FWS_WFS_URL = "https://fwspublicservices.wim.usgs.gov/server/rest/services/Wetlands/MapServer/0/query"


async def get_wetlands_percent(lat: float, lng: float, acres: float = 1.0) -> dict:
    """
    Queries FWS wetlands layer for a ~1-mile buffer around coordinates.
    Returns estimated wetland percentage of parcel area.
    """
    # Build a simple bounding box ~0.01 degrees (~0.7 miles) around point
    delta = max(0.005, min(0.02, (acres ** 0.5) * 0.003))
    envelope = f"{lng - delta},{lat - delta},{lng + delta},{lat + delta}"

    params = {
        "geometry": envelope,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "WETLAND_TYPE,ACRES",
        "returnGeometry": "false",
        "f": "json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(FWS_WFS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])

            if not features:
                return {"wetlands_percent": 0.0, "source": "fws_no_data"}

            wetland_acres = sum(
                f["attributes"].get("ACRES") or 0 for f in features
            )
            parcel_acres = max(acres, 0.1)
            pct = min(100.0, (wetland_acres / parcel_acres) * 100)
            return {"wetlands_percent": round(pct, 1), "source": "fws_wetlands"}
        except Exception as e:
            return {"wetlands_percent": 0.0, "source": f"fws_error:{e}"}
