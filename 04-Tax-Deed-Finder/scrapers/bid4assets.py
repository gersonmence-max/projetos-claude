"""
Bid4Assets scraper using Playwright authenticated session.
Collects tax deed auctions for configured counties.
"""
import os
import json
import asyncio
from datetime import date, datetime
from typing import Optional
from playwright.async_api import async_playwright, Page, BrowserContext

from scrapers.base import RawParcel, parse_dollar, parse_acres


BID4ASSETS_BASE = "https://www.bid4assets.com"
LOGIN_URL = f"{BID4ASSETS_BASE}/myaccount/login"
SEARCH_URL = f"{BID4ASSETS_BASE}/auctions?type=tax-deed&page={{page}}&county={{county_id}}"


async def _login(context: BrowserContext) -> Page:
    page = await context.new_page()
    page.set_default_timeout(90000)
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=90000)
    await asyncio.sleep(3)  # allow JS/Cloudflare to settle

    # Detect bot-block pages before trying to fill the form
    content = await page.content()
    if "cloudflare" in content.lower() or "checking your browser" in content.lower():
        await asyncio.sleep(8)
        await page.wait_for_load_state("networkidle", timeout=30000)

    # Try multiple field name conventions (site has changed these before)
    username_sel = (
        'input[name="Username"], input[name="username"], '
        'input[name="Email"], input[name="email"], input[type="email"]'
    )
    await page.wait_for_selector(username_sel, timeout=60000)
    await page.fill(username_sel, os.environ["BID4ASSETS_EMAIL"])
    await page.fill('input[name="Password"], input[name="password"], input[type="password"]', os.environ["BID4ASSETS_PASSWORD"])
    await page.click('button[type="submit"], input[type="submit"], input[name="Login"]')
    await page.wait_for_load_state("networkidle", timeout=60000)
    return page


async def _parse_listing_page(page: Page, county_id: str, county_db_id: str) -> list[RawParcel]:
    parcels: list[RawParcel] = []
    cards = await page.query_selector_all(".auction-item, .property-card, [data-auction-id]")

    for card in cards:
        try:
            ext_id = await card.get_attribute("data-auction-id") or ""
            if not ext_id:
                id_el = await card.query_selector("[data-id], .auction-id")
                if id_el:
                    ext_id = (await id_el.inner_text()).strip()

            title_el = await card.query_selector(".auction-title, h3, .property-address")
            title = (await title_el.inner_text()).strip() if title_el else ""

            bid_el = await card.query_selector(".current-bid, .minimum-bid, .starting-bid")
            bid_text = (await bid_el.inner_text()).strip() if bid_el else "0"
            minimum_bid = parse_dollar(bid_text) or 0.0

            date_el = await card.query_selector(".auction-date, .end-date, time")
            date_text = (await date_el.inner_text()).strip() if date_el else ""
            auction_date = _parse_date(date_text)

            link_el = await card.query_selector("a[href]")
            href = await link_el.get_attribute("href") if link_el else ""
            auction_url = f"{BID4ASSETS_BASE}{href}" if href and href.startswith("/") else href or ""

            acres_el = await card.query_selector(".acres, [data-acres]")
            acres_text = (await acres_el.inner_text()).strip() if acres_el else ""

            type_el = await card.query_selector(".property-type, [data-type]")
            type_text = (await type_el.inner_text()).strip().lower() if type_el else "land"
            property_type = _normalize_type(type_text)

            raw = {"title": title, "bid_text": bid_text, "date_text": date_text}

            if not ext_id or minimum_bid <= 0:
                continue

            parcels.append(RawParcel(
                external_id=f"b4a-{ext_id}",
                county_id=county_db_id,
                auction_platform="bid4assets",
                auction_url=auction_url,
                minimum_bid=minimum_bid,
                auction_date=auction_date,
                address=title,
                property_type=property_type,
                acres=parse_acres(acres_text),
                raw_data=raw,
            ))
        except Exception:
            continue

    return parcels


def _parse_date(text: str) -> Optional[date]:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _normalize_type(text: str) -> str:
    if any(w in text for w in ["house", "home", "residence", "sfr", "single"]):
        return "house"
    if any(w in text for w in ["commercial", "retail", "office"]):
        return "commercial"
    return "land"


async def scrape_county(county_id: str, county_db_id: str) -> list[RawParcel]:
    """Scrape all tax deed listings for a county from Bid4Assets."""
    if not os.environ.get("BID4ASSETS_EMAIL") or not os.environ.get("BID4ASSETS_PASSWORD"):
        raise ValueError("BID4ASSETS_EMAIL/PASSWORD not configured")

    all_parcels: list[RawParcel] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await _login(context)

        page_num = 1
        while True:
            url = SEARCH_URL.format(page=page_num, county_id=county_id)
            await page.goto(url, wait_until="load", timeout=60000)

            items = await _parse_listing_page(page, county_id, county_db_id)
            if not items:
                break

            all_parcels.extend(items)

            # Check for next page
            next_btn = await page.query_selector(".pagination-next:not(.disabled), [aria-label='Next']")
            if not next_btn:
                break
            page_num += 1
            await asyncio.sleep(1.5)

        await browser.close()

    return all_parcels
