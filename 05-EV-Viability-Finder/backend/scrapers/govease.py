# backend/scrapers/govease.py
import asyncio
import re
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

_BASE_URL = "https://liveauctions.govease.com"
_REFRESH_ENDPOINT = "/OpenAuction/RefreshBidDownAuctions"
_PAGE_SIZE = 50

# Condados do Alabama confirmados no GovEase.
# O scraper também tenta descobrir mais dinamicamente em _discover_counties().
_AL_COUNTIES_FALLBACK = [
    {"id": 1252, "slug": "alcolbert", "name": "Colbert"},
    {"id": 1309, "slug": "alhale",    "name": "Hale"},
]


def _parse_face_value(text: str) -> Optional[float]:
    """Converte '$3,450.00' → 3450.0. Retorna None se não parsear."""
    cleaned = re.sub(r"[^\d.]", "", text.strip())
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _parse_grid_html(
    html: str, county_id: int, county_name: str
) -> List[Dict[str, Any]]:
    """Extrai propriedades do HTML da resposta GovEase."""
    results = []
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("tbody tr")

    county_slug = "al" + county_name.lower().replace(" ", "")

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 9:
            continue
        try:
            # Cell layout (11 cols): [0]empty [1]empty [2]internal_id [3]parcel_id
            # [4]owner_or_address [5]face_value [6]property_address [7]auction_name [8]type ...
            parcel_id = cells[3].get_text(strip=True)
            # cell[6] is the property street address; cell[4] is sometimes owner name
            address = cells[6].get_text(strip=True) or cells[4].get_text(strip=True)
            face_value_text = cells[5].get_text(strip=True)
            price = _parse_face_value(face_value_text)

            if not parcel_id:
                continue

            # Use parcel_id as fragment to make listing_url unique
            listing_url = f"{_BASE_URL}/al/{county_slug}/{county_id}/browsebiddown#{parcel_id}"

            results.append({
                "source": "govease",
                "state": "AL",
                "county": county_name,
                "address": address,
                "lat": None,
                "lng": None,
                "price": price,
                "acres": None,
                "parcel_id": parcel_id,
                "sale_date": None,
                "listing_url": listing_url,
            })
        except Exception:
            continue

    return results


async def _discover_counties(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Tenta descobrir condados do Alabama na página principal do GovEase."""
    try:
        resp = await client.get(f"{_BASE_URL}/al/")
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        counties = []
        pattern = re.compile(r"/al/([^/]+)/(\d+)/browsebiddown")
        seen_ids: set = set()

        for a_tag in soup.find_all("a", href=pattern):
            href = a_tag.get("href", "")
            match = pattern.search(href)
            if match:
                slug = match.group(1)
                county_id = int(match.group(2))
                if county_id not in seen_ids:
                    seen_ids.add(county_id)
                    name = slug[2:].title()  # "alcolbert" → "Colbert"
                    counties.append({"id": county_id, "slug": slug, "name": name})

        return counties
    except Exception as e:
        print(f"GovEase: erro ao descobrir condados: {e}")
        return []


async def _scrape_county(
    client: httpx.AsyncClient, county: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Raspa todos os leilões de um condado Alabama."""
    results = []
    page = 1

    while True:
        params = {
            "countyId": county["id"],
            "stateAbbr": "al",
            "pageNumber": page,
            "pageSize": _PAGE_SIZE,
            "orderBy": "",
            "orderDesc": "false",
        }
        try:
            resp = await client.get(_BASE_URL + _REFRESH_ENDPOINT, params=params)
            if resp.status_code != 200:
                print(f"GovEase {county['name']}: status {resp.status_code}")
                break

            data = resp.json()
            if not data.get("Result"):
                break

            grid_html = data.get("Grid") or ""
            page_results = _parse_grid_html(
                grid_html, county_id=county["id"], county_name=county["name"]
            )

            if not page_results:
                break

            results.extend(page_results)
            print(f"GovEase {county['name']} página {page}: {len(page_results)} imóveis")

            if len(page_results) < _PAGE_SIZE:
                break

            page += 1
            await asyncio.sleep(2.0)

        except Exception as e:
            print(f"Erro GovEase {county['name']} página {page}: {e}")
            break

    return results


async def scrape_govease() -> List[Dict[str, Any]]:
    """Raspa todos os leilões ativos do GovEase para Alabama."""
    results = []

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        counties = await _discover_counties(client)
        if not counties:
            print("GovEase: usando lista de condados hardcoded")
            counties = _AL_COUNTIES_FALLBACK

        print(f"GovEase: {len(counties)} condados encontrados")

        for county in counties:
            county_results = await _scrape_county(client, county)
            results.extend(county_results)
            await asyncio.sleep(2.0)

    print(f"GovEase total: {len(results)} imóveis")
    return results
