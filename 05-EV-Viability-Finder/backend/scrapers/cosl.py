# backend/scrapers/cosl.py
import asyncio
from typing import Any, Dict, List

import httpx

_BASE_URL = "https://auction.cosl.org"
_ENDPOINT = "/auctions/ongoing-auctions_grid_read"
_PAGE_SIZE = 100


def _parse_cosl_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Converte um item da API COSL para o schema do pipeline."""
    county_raw = item.get("CoSLCountyName") or ""
    county = county_raw.title()  # "SALINE" → "Saline"

    section = item.get("Section") or ""
    township = item.get("Township") or ""
    range_ = item.get("Range") or ""
    address = f"Sec {section}-{township}-{range_}, {county} County, AR".strip(", ")

    prop_id = item.get("CoSLPropertyId")
    listing_url = f"{_BASE_URL}/auctions?id={prop_id}" if prop_id else None

    end_raw = item.get("End")
    sale_date = None
    if end_raw:
        # "2026-05-15T20:00:00Z" → "2026-05-15"
        sale_date = end_raw[:10]

    acreage = item.get("Acreage")
    # API returns CurrentBid (the live bid amount), not StartingBid
    current_bid = item.get("CurrentBid")

    return {
        "source": "cosl",
        "state": "AR",
        "county": county,
        "address": address,
        "lat": None,
        "lng": None,
        "price": float(current_bid) if current_bid is not None else None,
        # Acreage=0.0 is valid for urban lots in COSL — store as-is, filter allows None/0
        "acres": float(acreage) if acreage is not None else None,
        "parcel_id": item.get("CoSLParcelNumber"),
        "sale_date": sale_date,
        "listing_url": listing_url,
    }


async def scrape_cosl() -> List[Dict[str, Any]]:
    """Raspa todos os leilões ativos do COSL Arkansas."""
    results: List[Dict[str, Any]] = []
    fetched = 0
    page = 1

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        while True:
            params = {"page": page, "pageSize": _PAGE_SIZE}
            try:
                resp = await client.get(_BASE_URL + _ENDPOINT, params=params)
                if resp.status_code != 200:
                    print(f"COSL página {page}: status {resp.status_code}")
                    break

                data = resp.json()
                items = data.get("Data") or []
                total = data.get("Total") or 0

                if not items:
                    break

                fetched += len(items)
                for item in items:
                    parsed = _parse_cosl_item(item)
                    if parsed["listing_url"]:
                        results.append(parsed)

                print(f"COSL página {page}: {len(items)} imóveis (total: {total})")

                if fetched >= total or len(items) < _PAGE_SIZE:
                    break

                page += 1
                await asyncio.sleep(2.0)

            except Exception as e:
                print(f"Erro COSL página {page}: {e}")
                break

    print(f"COSL total: {len(results)} imóveis")
    return results
