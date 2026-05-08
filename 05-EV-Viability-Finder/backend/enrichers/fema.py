# backend/enrichers/fema.py
from typing import Optional

import httpx

_FEMA_URL = "https://msc.fema.gov/api/public/maps/1.0/zones"


async def get_fema_zone(lat: float, lng: float) -> Optional[str]:
    """Retorna zona de inundação FEMA para as coordenadas dadas."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(_FEMA_URL, params={"lat": lat, "lon": lng})
            if resp.status_code == 200:
                data = resp.json()
                zones = data.get("flood_zones", [])
                if zones:
                    return zones[0].get("flood_zone", "X")
                return "X"
        except Exception as e:
            print(f"Erro FEMA ({lat:.4f}, {lng:.4f}): {e}")
    return None
