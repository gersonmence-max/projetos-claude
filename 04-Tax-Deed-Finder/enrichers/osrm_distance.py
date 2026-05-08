"""
OSRM (Open Source Routing Machine) — drive time to nearest city with 50k+ population.
Uses public OSRM demo instance. Major US cities preloaded.
"""
import httpx
from typing import Optional
import math

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

# Cities with 50k+ population (lat, lng, name, population)
CITIES_50K = [
    # Texas
    (30.2672, -97.7431, "Austin", 961855),
    (29.7604, -95.3698, "Houston", 2304580),
    (32.7767, -96.7970, "Dallas", 1345047),
    (29.4241, -98.4936, "San Antonio", 1509874),
    (32.7555, -97.3308, "Fort Worth", 935508),
    (33.2148, -97.1331, "Denton", 139869),
    (29.5519, -95.0982, "Pearland", 125828),
    (30.5052, -97.8203, "Georgetown", 80386),
    # Georgia
    (33.7490, -84.3880, "Atlanta", 498715),
    (34.2979, -85.1647, "Rome", 36303),
    (34.0007, -84.0002, "Gainesville", 43871),
    (33.9526, -83.9874, "Athens", 126913),
    # Tennessee
    (36.1627, -86.7816, "Nashville", 689447),
    (35.1495, -90.0490, "Memphis", 633104),
    (35.9606, -83.9207, "Knoxville", 190740),
    (35.8456, -86.3903, "Murfreesboro", 152769),
    (35.9251, -87.0894, "Columbia", 40962),
    # Arkansas
    (36.3729, -94.2088, "Bentonville", 52376),
    (36.3634, -94.2157, "Rogers", 69779),
    (36.0822, -94.1719, "Fayetteville", 99388),
    (34.7465, -92.2896, "Little Rock", 202591),
    (34.7209, -92.3521, "North Little Rock", 66708),
    (34.5248, -92.0754, "Benton", 36256),
    (35.0854, -92.4421, "Conway", 68843),
    # Florida
    (28.5383, -81.3792, "Orlando", 307573),
    (27.9506, -82.4572, "Tampa", 399700),
    (27.3364, -82.5307, "Sarasota", 54842),
    (29.6520, -82.3250, "Gainesville", 133997),
    (28.0836, -81.9498, "Lakeland", 112641),
    (28.2919, -81.4076, "Kissimmee", 80337),
    (29.1872, -82.1401, "Ocala", 63591),
    (29.9012, -81.3124, "St. Augustine", 15415),
    # North Carolina
    (35.7796, -78.6382, "Raleigh", 467665),
    (35.2271, -80.8431, "Charlotte", 897964),
    (36.0726, -79.7920, "Greensboro", 299035),
    (35.9940, -78.8986, "Durham", 278993),
    (36.0999, -80.2442, "Winston-Salem", 247945),
    (35.4685, -80.6185, "Concord", 105240),
    (35.5651, -80.8499, "Kannapolis", 53014),
]


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


async def get_nearest_city(lat: float, lng: float) -> dict:
    """
    Finds the nearest city with 50k+ population and gets drive time via OSRM.
    Falls back to straight-line distance estimate if OSRM fails.
    """
    # Sort candidates by straight-line distance, take top 3
    candidates = sorted(CITIES_50K, key=lambda c: _haversine_km(lat, lng, c[0], c[1]))[:3]
    nearest = candidates[0]
    straight_km = _haversine_km(lat, lng, nearest[0], nearest[1])
    straight_miles = straight_km * 0.621371

    # Try OSRM for drive time
    async with httpx.AsyncClient(timeout=15) as client:
        for city in candidates:
            try:
                url = f"{OSRM_URL}/{lng},{lat};{city[1]},{city[0]}"
                resp = await client.get(url, params={"overview": "false"})
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") == "Ok":
                    route = data["routes"][0]
                    duration_min = route["duration"] / 60
                    distance_miles = route["distance"] / 1609.34
                    return {
                        "nearest_city": city[2],
                        "nearest_city_population": city[3],
                        "nearest_city_distance_miles": round(distance_miles, 1),
                        "drive_time_minutes": round(duration_min, 0),
                        "source": "osrm",
                    }
            except Exception:
                continue

    # Fallback: estimate drive time as straight-line / 60 km/h
    est_minutes = (straight_km / 60) * 60
    return {
        "nearest_city": nearest[2],
        "nearest_city_population": nearest[3],
        "nearest_city_distance_miles": round(straight_miles, 1),
        "drive_time_minutes": round(est_minutes, 0),
        "source": "straight_line_estimate",
    }
