# backend/scrapers/zillow.py
import asyncio
import json
import random
from typing import Any, Dict, List, Optional

import httpx

STATES = ["AL", "AR"]

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

_STATE_CONFIG = {
    "AL": {
        "mapBounds": {"north": 35.0, "south": 30.1, "east": -84.8, "west": -88.5},
        "regionId": 8,
    },
    "AR": {
        "mapBounds": {"north": 36.5, "south": 33.0, "east": -89.6, "west": -94.6},
        "regionId": 9,
    },
}

_SEARCH_URL = "https://www.zillow.com/search/GetSearchPageState.htm"


def _build_headers() -> Dict[str, str]:
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.zillow.com/",
        "X-Requested-With": "XMLHttpRequest",
    }


def _parse_listing(listing: Dict[str, Any], state: str) -> Optional[Dict[str, Any]]:
    """Extrai campos relevantes de uma listagem Zillow."""
    hdp = listing.get("hdpData", {}).get("homeInfo", {})
    home_type = hdp.get("homeType", "")

    if home_type not in ("LOT", "LAND"):
        return None

    price = hdp.get("price") or listing.get("price")
    acres_raw = hdp.get("lotAreaValue")
    lot_unit = hdp.get("lotAreaUnit", "")

    acres = None
    if acres_raw:
        if lot_unit == "sqft":
            acres = acres_raw / 43_560
        elif lot_unit == "acres":
            acres = acres_raw

    detail_url = listing.get("detailUrl", "")

    return {
        "source": "zillow",
        "state": state,
        "county": hdp.get("county", ""),
        "address": listing.get("address", ""),
        "lat": hdp.get("latitude"),
        "lng": hdp.get("longitude"),
        "price": float(price) if price else None,
        "acres": float(acres) if acres else None,
        "listing_url": f"https://www.zillow.com{detail_url}" if detail_url else "",
    }


async def scrape_zillow(state: str) -> List[Dict[str, Any]]:
    """Raspa listagens de terrenos do Zillow para um estado."""
    results: List[Dict[str, Any]] = []
    config = _STATE_CONFIG[state]

    for page in range(1, 6):
        search_query_state = {
            "pagination": {"currentPage": page},
            "isMapVisible": False,
            "filterState": {
                "lot": {"value": True},
                "land": {"value": True},
                "mf": {"value": False},
                "con": {"value": False},
                "apa": {"value": False},
                "manu": {"value": False},
                "tow": {"value": False},
                "ac": {"min": 1},
                "price": {"max": 500_000},
            },
            "isEntryPoint": False,
            "regionSelection": [{"regionId": config["regionId"], "regionType": 2}],
            "mapBounds": config["mapBounds"],
        }

        params = {
            "searchQueryState": json.dumps(search_query_state),
            "wants": json.dumps({"cat1": ["listResults", "mapResults"]}),
            "requestId": random.randint(1, 20),
        }

        async with httpx.AsyncClient(
            headers=_build_headers(), timeout=30, follow_redirects=True
        ) as client:
            try:
                resp = await client.get(_SEARCH_URL, params=params)
                if resp.status_code != 200:
                    print(f"Zillow {state} página {page}: status {resp.status_code}")
                    break

                data = resp.json()
                listings = (
                    data.get("cat1", {})
                    .get("searchResults", {})
                    .get("listResults", [])
                )

                if not listings:
                    break

                for listing in listings:
                    parsed = _parse_listing(listing, state)
                    if parsed:
                        results.append(parsed)

                print(f"Zillow {state} página {page}: {len(listings)} listagens")
                await asyncio.sleep(random.uniform(2.5, 5.0))

            except Exception as e:
                print(f"Erro Zillow {state} página {page}: {e}")
                break

    return results


async def scrape_all_states() -> List[Dict[str, Any]]:
    """Raspa todos os estados configurados."""
    results: List[Dict[str, Any]] = []
    for state in STATES:
        state_results = await scrape_zillow(state)
        results.extend(state_results)
        print(f"Zillow {state}: {len(state_results)} terrenos encontrados")
        await asyncio.sleep(random.uniform(3.0, 6.0))
    return results
