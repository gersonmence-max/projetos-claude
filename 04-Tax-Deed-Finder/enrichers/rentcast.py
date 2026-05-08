"""
Market value estimation — uses Rentcast API if key is set,
otherwise falls back to assessor value * 1.2 (free).
"""
import os
import httpx
from typing import Optional

RENTCAST_URL = "https://api.rentcast.io/v1"
# Each state sets its own assessment ratio by law
STATE_ASSESSMENT_RATIO = {
    "TX": 1.00,  # 100% of market value
    "FL": 1.00,  # 100% of market value
    "NC": 1.00,  # 100% of market value
    "GA": 2.50,  # assessed at 40% → multiply by 2.5
    "TN": 4.00,  # assessed at 25% → multiply by 4.0
    "AR": 5.00,  # assessed at 20% → multiply by 5.0
}


async def get_market_value(
    address: str,
    city: str,
    state: str,
    zip_code: str,
    property_type: str = "land",
    bedrooms: Optional[int] = None,
    bathrooms: Optional[float] = None,
    sqft: Optional[int] = None,
    assessed_value: Optional[float] = None,
) -> dict:
    api_key = os.environ.get("RENTCAST_API_KEY", "")

    if api_key and api_key not in ("placeholder", "..."):
        result = await _fetch_rentcast(api_key, address, city, state, zip_code, bedrooms, bathrooms, sqft)
        if result.get("market_value_estimate"):
            return result

    # Free fallback: assessor value converted to market value using state ratio
    if assessed_value and assessed_value > 0:
        multiplier = STATE_ASSESSMENT_RATIO.get(state.upper(), 1.2)
        return {
            "market_value_estimate": round(assessed_value * multiplier, 2),
            "comparable_sales": [],
            "source": f"assessor_estimate_{state.upper()}",
        }

    return {"error": "no_valuation_available", "market_value_estimate": None}


async def _fetch_rentcast(api_key, address, city, state, zip_code, bedrooms, bathrooms, sqft) -> dict:
    headers = {"X-Api-Key": api_key}
    full_address = f"{address}, {city}, {state} {zip_code}".strip(", ")

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            params = {"address": full_address}
            if bedrooms:
                params["bedrooms"] = bedrooms
            if bathrooms:
                params["bathrooms"] = bathrooms
            if sqft:
                params["squareFootage"] = sqft

            resp = await client.get(f"{RENTCAST_URL}/avm/value", headers=headers, params=params)
            if resp.status_code == 200:
                data = resp.json()
                price = data.get("price") or data.get("value") or data.get("priceRangeLow")
                return {
                    "market_value_estimate": float(price) if price else None,
                    "comparable_sales": (data.get("comparables") or [])[:5],
                    "source": "rentcast_avm",
                }
        except Exception:
            pass

        try:
            resp = await client.get(f"{RENTCAST_URL}/properties", headers=headers, params={"address": full_address})
            if resp.status_code == 200:
                data = resp.json()
                item = data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else None
                if item:
                    price = item.get("price") or item.get("lastSalePrice") or item.get("assessedValue")
                    return {
                        "market_value_estimate": float(price) if price else None,
                        "comparable_sales": [],
                        "source": "rentcast_property",
                    }
        except Exception:
            pass

    return {"error": "rentcast_failed", "market_value_estimate": None}
