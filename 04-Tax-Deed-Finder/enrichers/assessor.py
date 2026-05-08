"""
County assessor enricher — fetches assessed value and parcel details.
Each county has its own portal; we use a strategy pattern keyed by assessor_api_type.
"""
import httpx
import re
from typing import Optional
from playwright.async_api import async_playwright


async def get_assessor_data(
    parcel_number: str,
    county_name: str,
    state: str,
    assessor_url: str,
    assessor_api_type: str,
) -> dict:
    """
    Dispatcher: routes to the correct assessor fetch strategy.
    Returns assessed_value, market_value, acres, property_type, zoning.
    """
    try:
        if assessor_api_type == "rest":
            return await _fetch_rest(parcel_number, county_name, state, assessor_url)
        elif assessor_api_type == "scrape":
            return await _fetch_scrape(parcel_number, county_name, state, assessor_url)
        else:
            return {"error": f"unknown assessor_api_type: {assessor_api_type}"}
    except Exception as e:
        return {"error": str(e)}


async def _fetch_rest(parcel_number: str, county_name: str, state: str, base_url: str) -> dict:
    """
    Generic REST assessor fetch — handles counties with JSON APIs.
    Tries common query patterns used by Tyler Technologies / Aumentum portals.
    """
    search_endpoints = [
        f"{base_url}/api/property/{parcel_number}",
        f"{base_url}/api/parcels?apn={parcel_number}",
        f"{base_url}/search?parcel={parcel_number}&format=json",
    ]
    async with httpx.AsyncClient(timeout=15) as client:
        for url in search_endpoints:
            try:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code == 200 and "json" in resp.headers.get("content-type", ""):
                    data = resp.json()
                    return _normalize_assessor_json(data)
            except Exception:
                continue
    return {"error": "rest_not_found"}


async def _fetch_scrape(parcel_number: str, county_name: str, state: str, base_url: str) -> dict:
    """
    Playwright-based assessor scrape for counties with web portals.
    Handles qPublic, Tyler Technologies, and CAMA portals.
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(base_url, wait_until="networkidle", timeout=20000)

            # Try common search input selectors
            search_selectors = [
                'input[name="parcel"]', 'input[name="apn"]',
                'input[name="ParcelNumber"]', 'input[id*="parcel"]',
                'input[placeholder*="parcel"]', 'input[placeholder*="APN"]',
                '#parcelSearch', '#searchInput',
            ]
            for sel in search_selectors:
                el = await page.query_selector(sel)
                if el:
                    await el.fill(parcel_number)
                    await page.keyboard.press("Enter")
                    await page.wait_for_load_state("networkidle")
                    break

            # Extract assessed value
            value_selectors = [
                '.assessed-value', '[data-field="assessed_value"]',
                'td:has-text("Assessed") + td', 'td:has-text("Total Value") + td',
                '.property-value', '#assessedValue',
            ]
            assessed_value = None
            for sel in value_selectors:
                el = await page.query_selector(sel)
                if el:
                    text = await el.inner_text()
                    assessed_value = _parse_dollar_from_text(text)
                    if assessed_value:
                        break

            # Extract acres
            acres_selectors = [
                '.acres', '[data-field="acres"]', 'td:has-text("Acres") + td',
                'td:has-text("Land Size") + td', '#acres',
            ]
            acres = None
            for sel in acres_selectors:
                el = await page.query_selector(sel)
                if el:
                    text = await el.inner_text()
                    acres = _parse_acres_from_text(text)
                    if acres:
                        break

            # Extract zoning
            zoning_selectors = [
                '.zoning', '[data-field="zoning"]', 'td:has-text("Zoning") + td',
                'td:has-text("Land Use") + td',
            ]
            zoning = None
            for sel in zoning_selectors:
                el = await page.query_selector(sel)
                if el:
                    zoning = (await el.inner_text()).strip()[:50]
                    break

        except Exception:
            assessed_value = acres = zoning = None
        finally:
            await browser.close()

    return {
        "assessed_value": assessed_value,
        "acres_from_assessor": acres,
        "zoning": zoning,
        "source": "assessor_scrape",
    }


def _normalize_assessor_json(data: dict) -> dict:
    """Normalize various assessor JSON response shapes."""
    if isinstance(data, list):
        data = data[0] if data else {}
    return {
        "assessed_value": _parse_dollar_from_text(str(
            data.get("assessed_value") or data.get("totalValue") or data.get("assessedValue") or 0
        )),
        "acres_from_assessor": data.get("acres") or data.get("landSize"),
        "zoning": data.get("zoning") or data.get("landUse"),
        "source": "assessor_rest",
    }


def _parse_dollar_from_text(text: str) -> Optional[float]:
    cleaned = re.sub(r"[^\d.]", "", str(text))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _parse_acres_from_text(text: str) -> Optional[float]:
    match = re.search(r"([\d,.]+)", str(text))
    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return None
    return None
