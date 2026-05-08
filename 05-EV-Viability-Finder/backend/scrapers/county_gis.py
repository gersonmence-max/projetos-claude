# backend/scrapers/county_gis.py
import asyncio
from typing import Any, Dict, List, Optional

import httpx

_COUNTY_ENDPOINTS: List[Dict[str, str]] = [
    {
        "state": "AL",
        "county": "Jefferson",
        "url": "https://gis.jeffersoncountyal.gov/arcgis/rest/services/ParcelViewer/MapServer/0/query",
    },
    {
        "state": "AL",
        "county": "Madison",
        "url": "https://gis.madisoncountyal.gov/arcgis/rest/services/Parcels/MapServer/0/query",
    },
    {
        "state": "AL",
        "county": "Mobile",
        "url": "https://www.mobilecountyal.gov/arcgis/rest/services/Parcels/MapServer/0/query",
    },
    {
        "state": "AR",
        "county": "Pulaski",
        "url": "https://maps.pulaskicounty.net/arcgis/rest/services/Parcels/FeatureServer/0/query",
    },
    {
        "state": "AR",
        "county": "Benton",
        "url": "https://gis.bentoncountyar.gov/arcgis/rest/services/Parcels/MapServer/0/query",
    },
]

_ARCGIS_PARAMS = {
    "where": "LAND_USE_CODE IN ('V', 'VAC', 'VACANT', 'AG', 'FARM') OR ACRES >= 1",
    "outFields": "ADDRESS,SITUS_ADDR,LAND_USE,LAND_USE_CODE,ZONING,ACRES,ROAD_ACCESS,UTILITIES,ASSESSED_VALUE",
    "returnGeometry": "true",
    "geometryType": "esriGeometryEnvelope",
    "f": "json",
    "resultRecordCount": "100",
}


def _parse_arcgis_feature(feature: Dict, endpoint: Dict) -> Optional[Dict[str, Any]]:
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry", {})

    address = attrs.get("ADDRESS") or attrs.get("SITUS_ADDR") or ""
    acres = attrs.get("ACRES")
    assessed_value = attrs.get("ASSESSED_VALUE")

    lat = geometry.get("y")
    lng = geometry.get("x")

    rings = geometry.get("rings")
    if rings and not lat:
        try:
            all_x = [pt[0] for ring in rings for pt in ring]
            all_y = [pt[1] for ring in rings for pt in ring]
            lng = sum(all_x) / len(all_x)
            lat = sum(all_y) / len(all_y)
        except Exception:
            pass

    return {
        "source": "county_gis",
        "state": endpoint["state"],
        "county": endpoint["county"],
        "address": address,
        "lat": float(lat) if lat else None,
        "lng": float(lng) if lng else None,
        "acres": float(acres) if acres else None,
        "zoning": attrs.get("ZONING") or attrs.get("LAND_USE_CODE"),
        "has_road_access": bool(attrs.get("ROAD_ACCESS")),
        "utilities_available": bool(attrs.get("UTILITIES")),
        "avg_price_per_acre": (
            float(assessed_value) / float(acres)
            if assessed_value and acres and float(acres) > 0
            else None
        ),
    }


async def query_county(endpoint: Dict[str, str]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(endpoint["url"], params=_ARCGIS_PARAMS)
            if resp.status_code != 200:
                print(f"GIS {endpoint['county']}: status {resp.status_code}")
                return results

            data = resp.json()
            features = data.get("features", [])

            for feature in features:
                parsed = _parse_arcgis_feature(feature, endpoint)
                if parsed and parsed.get("acres") and parsed["acres"] >= 1:
                    results.append(parsed)

            print(f"GIS {endpoint['county']}: {len(results)} parcelas")
        except Exception as e:
            print(f"Erro GIS {endpoint['county']}: {e}")

    return results


async def scrape_all_counties() -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for endpoint in _COUNTY_ENDPOINTS:
        county_results = await query_county(endpoint)
        results.extend(county_results)
        await asyncio.sleep(1.0)
    return results
