"""
OpenStreetMap Overpass API — road access check for a parcel coordinate.
Queries nearest highway within 200m to determine road type.
"""
import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Highway types in order of quality
PAVED_HIGHWAYS = {"motorway", "trunk", "primary", "secondary", "tertiary",
                  "unclassified", "residential", "service", "living_street"}
UNPAVED_HIGHWAYS = {"track", "path", "bridleway", "cycleway", "footway"}


async def get_road_access(lat: float, lng: float, radius_m: int = 200) -> dict:
    """
    Checks for road access within radius_m meters of coordinate.
    Returns has_road_access=True and road_type='paved'|'unpaved'|'none'.
    """
    query = f"""
    [out:json][timeout:15];
    way(around:{radius_m},{lat},{lng})[highway];
    out tags 1;
    """
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.post(OVERPASS_URL, data={"data": query})
            resp.raise_for_status()
            data = resp.json()
            elements = data.get("elements", [])

            if not elements:
                return {"has_road_access": False, "road_type": "none", "source": "osm_overpass"}

            for el in elements:
                tags = el.get("tags", {})
                highway = tags.get("highway", "")
                surface = tags.get("surface", "")

                if highway in PAVED_HIGHWAYS:
                    is_paved = surface in {"asphalt", "concrete", "paved"} or surface == "" or highway in {
                        "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential"
                    }
                    road_type = "paved" if is_paved else "unpaved"
                    return {"has_road_access": True, "road_type": road_type, "source": "osm_overpass"}

                if highway in UNPAVED_HIGHWAYS:
                    return {"has_road_access": True, "road_type": "unpaved", "source": "osm_overpass"}

            return {"has_road_access": True, "road_type": "unpaved", "source": "osm_overpass"}

        except Exception as e:
            return {"has_road_access": True, "road_type": "paved", "source": f"osm_error:{e}"}
