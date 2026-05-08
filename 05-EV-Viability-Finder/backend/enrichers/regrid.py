# backend/enrichers/regrid.py
from typing import Any, Dict, Optional

import httpx

from config import REGRID_API_KEY

_REGRID_URL = "https://app.regrid.com/api/v2/parcels/point"


async def get_regrid_data(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    """Retorna dados de parcela do Regrid. Retorna None se sem chave de API."""
    if not REGRID_API_KEY:
        return None

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                _REGRID_URL,
                params={"lat": lat, "lon": lng, "token": REGRID_API_KEY},
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            features = data.get("parcels", {}).get("features", [])
            if not features:
                return None

            fields = features[0].get("properties", {}).get("fields", {})
            acres = fields.get("ll_gisacre")
            land_val = fields.get("landval")

            avg_ppa = None
            if acres and float(acres) > 0 and land_val:
                avg_ppa = float(land_val) / float(acres)

            return {
                "acres": float(acres) if acres else None,
                "zoning": fields.get("zoning"),
                "avg_price_per_acre": avg_ppa,
                "has_road_access": bool(fields.get("road_access")),
                "utilities_available": bool(fields.get("utilities")),
            }
        except Exception as e:
            print(f"Erro Regrid ({lat:.4f}, {lng:.4f}): {e}")
    return None
