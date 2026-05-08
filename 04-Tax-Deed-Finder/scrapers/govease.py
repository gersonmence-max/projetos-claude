"""
GovEase scraper — Georgia and North Carolina tax deed auctions.
Portal: liveauctions.govease.com (ASP.NET MVC, server-rendered HTML).
"""
import os
import asyncio
import logging
from datetime import date, datetime
from typing import Optional
from playwright.async_api import async_playwright, Page

from scrapers.base import RawParcel, parse_dollar, parse_acres

log = logging.getLogger("landhq.govease")

GOVEASE_BASE = "https://liveauctions.govease.com"
LOGIN_URL = f"{GOVEASE_BASE}/Account/Login"


def _parse_date(text: str) -> Optional[date]:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text.strip()[:19], fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _normalize_type(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ["house", "home", "sfr", "residential structure"]):
        return "house"
    if any(w in t for w in ["commercial", "retail"]):
        return "commercial"
    return "land"


async def _login(page: Page) -> None:
    page.set_default_timeout(90000)
    await page.goto(LOGIN_URL, wait_until="networkidle", timeout=90000)
    # ASP.NET Identity login — try common field name conventions
    email_sel = 'input[name="Email"], input[name="UserName"], input[id="Email"], input[type="email"]'
    await page.wait_for_selector(email_sel, timeout=60000)
    await page.fill(email_sel, os.environ["GOVEASE_EMAIL"])
    await page.fill('input[name="Password"], input[type="password"]', os.environ["GOVEASE_PASSWORD"])
    await page.click('button[type="submit"], input[type="submit"]')
    await page.wait_for_load_state("networkidle", timeout=60000)


async def _parse_auction_page(page: Page, county_db_id: str) -> list[RawParcel]:
    """Parse server-rendered HTML auction listing page."""
    parcels: list[RawParcel] = []

    # GovEase ASP.NET MVC — try common table/card selectors
    rows = await page.query_selector_all(
        "table tbody tr, .auction-item, .property-item, [data-auction-id], .auction-row"
    )

    for row in rows:
        try:
            text = (await row.inner_text()).strip()
            if not text:
                continue

            # Extract auction ID from data attribute or link
            ext_id = await row.get_attribute("data-auction-id") or ""
            if not ext_id:
                link = await row.query_selector("a[href*='/Auction/'], a[href*='/auction/']")
                if link:
                    href = await link.get_attribute("href") or ""
                    ext_id = href.rstrip("/").split("/")[-1]

            if not ext_id:
                continue

            # Address
            addr_el = await row.query_selector(
                ".address, .property-address, td:first-child, [data-address]"
            )
            address = (await addr_el.inner_text()).strip() if addr_el else ""

            # Minimum bid
            bid_el = await row.query_selector(
                ".minimum-bid, .starting-bid, .current-bid, [data-bid], td:nth-child(3)"
            )
            bid_text = (await bid_el.inner_text()).strip() if bid_el else "0"
            minimum_bid = parse_dollar(bid_text) or 0.0
            if minimum_bid <= 0:
                continue

            # Auction date
            date_el = await row.query_selector(".auction-date, .sale-date, time, [data-date]")
            date_text = (await date_el.inner_text()).strip() if date_el else ""
            auction_date = _parse_date(date_text)

            # Link
            link_el = await row.query_selector("a[href]")
            href = await link_el.get_attribute("href") if link_el else ""
            auction_url = f"{GOVEASE_BASE}{href}" if href and href.startswith("/") else href or ""

            parcels.append(RawParcel(
                external_id=f"ge-{ext_id}",
                county_id=county_db_id,
                auction_platform="govease",
                auction_url=auction_url,
                minimum_bid=minimum_bid,
                auction_date=auction_date,
                address=address,
                raw_data={"address": address, "bid_text": bid_text, "date_text": date_text},
            ))
        except Exception:
            continue

    return parcels


async def scrape_county(county_id: str, county_db_id: str) -> list[RawParcel]:
    """Scrape GovEase auctions for a county."""
    if not os.environ.get("GOVEASE_EMAIL") or not os.environ.get("GOVEASE_PASSWORD"):
        raise ValueError("GOVEASE_EMAIL/PASSWORD not configured")

    all_parcels: list[RawParcel] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page = await context.new_page()
        await _login(page)

        # county_id format: "dawson-ga" → county name "Dawson", state "GA"
        parts = county_id.rsplit("-", 1)
        county_name = parts[0].replace("-", " ").title() if len(parts) == 2 else county_id
        state_abbr = parts[1].upper() if len(parts) == 2 else ""

        # Try auction listing URLs (ASP.NET MVC conventions + name-based)
        candidate_urls = [
            f"{GOVEASE_BASE}/Auctions?county={county_id}",
            f"{GOVEASE_BASE}/Auctions/Index?county={county_id}",
            f"{GOVEASE_BASE}/Auction?county={county_id}",
            f"{GOVEASE_BASE}/Auctions?state={state_abbr}&county={county_name}",
            f"{GOVEASE_BASE}/Auctions?search={county_name}+{state_abbr}",
            f"{GOVEASE_BASE}/Auctions",
        ]

        working_url: Optional[str] = None
        for url in candidate_urls:
            try:
                resp = await page.goto(url, wait_until="networkidle", timeout=30000)
                if resp and resp.ok and "login" not in page.url.lower():
                    # If main listing page, try to find county-specific link
                    if url == f"{GOVEASE_BASE}/Auctions":
                        content = await page.content()
                        county_link = await page.query_selector(
                            f'a[href*="{county_name.lower()}"], a[href*="{county_id}"]'
                        )
                        if county_link:
                            href = await county_link.get_attribute("href") or ""
                            working_url = f"{GOVEASE_BASE}{href}" if href.startswith("/") else href
                            await page.goto(working_url, wait_until="networkidle", timeout=30000)
                            items = await _parse_auction_page(page, county_db_id)
                            all_parcels.extend(items)
                        break

                    items = await _parse_auction_page(page, county_db_id)
                    if items:
                        working_url = url
                        all_parcels.extend(items)
                        break
                    content = await page.content()
                    if "auction" in content.lower():
                        working_url = url
                        break
            except Exception:
                continue

        if working_url:
            # Paginate remaining pages
            page_num = 2
            while True:
                sep = "&" if "?" in working_url else "?"
                url = f"{working_url}{sep}page={page_num}"
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(1)
                    items = await _parse_auction_page(page, county_db_id)
                    if not items:
                        break
                    all_parcels.extend(items)
                    page_num += 1
                except Exception:
                    break
        else:
            log.warning("GovEase: could not find auction listing URL for county %s", county_id)

        await browser.close()

    return all_parcels
