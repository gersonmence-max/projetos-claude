"""
RealAuction scraper — Florida, Texas, Tennessee tax deed auctions.
RealAuction provides a county-specific portal with standard URL patterns.
"""
import asyncio
from datetime import date, datetime
from typing import Optional
from playwright.async_api import async_playwright, Page

from scrapers.base import RawParcel, parse_dollar, parse_acres

SEARCH_TMPL = "https://www.realauction.com/index.cfm?zaction=AUCTION&Zmethod=PREVIEW&county={county_id}"


def _parse_date(text: str) -> Optional[date]:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _normalize_type(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ["house", "home", "sfr", "single family"]):
        return "house"
    if "commercial" in t:
        return "commercial"
    return "land"


async def _parse_auction_table(page: Page, county_db_id: str) -> list[RawParcel]:
    parcels: list[RawParcel] = []
    rows = await page.query_selector_all("table.AUCTION_ITEM tr[data-auctionid], tr.auctionRow")

    for row in rows:
        try:
            ext_id = await row.get_attribute("data-auctionid") or ""

            cells = await row.query_selector_all("td")
            texts = [((await c.inner_text()).strip()) for c in cells]

            if len(texts) < 4:
                continue

            # RealAuction typical column order: Case#, Parcel#, Address, Min Bid, Date
            parcel_number = texts[1] if len(texts) > 1 else ""
            address = texts[2] if len(texts) > 2 else ""
            bid_text = texts[3] if len(texts) > 3 else "0"
            date_text = texts[4] if len(texts) > 4 else ""

            minimum_bid = parse_dollar(bid_text) or 0.0
            if minimum_bid <= 0:
                continue

            link_el = await row.query_selector("a[href]")
            href = await link_el.get_attribute("href") if link_el else ""
            auction_url = f"https://www.realauction.com{href}" if href and href.startswith("/") else href or ""

            if not ext_id:
                ext_id = parcel_number or address[:20]

            parcels.append(RawParcel(
                external_id=f"ra-{ext_id}",
                county_id=county_db_id,
                auction_platform="realauction",
                auction_url=auction_url,
                minimum_bid=minimum_bid,
                auction_date=_parse_date(date_text),
                parcel_number=parcel_number,
                address=address,
                raw_data={"cells": texts},
            ))
        except Exception:
            continue

    return parcels


async def scrape_county(county_id: str, county_db_id: str) -> list[RawParcel]:
    """Scrape RealAuction upcoming tax deed listings for a county."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        url = SEARCH_TMPL.format(county_id=county_id)
        await page.goto(url, wait_until="load", timeout=60000)

        all_parcels: list[RawParcel] = []

        page_num = 1
        while True:
            parcels = await _parse_auction_table(page, county_db_id)
            if not parcels:
                break
            all_parcels.extend(parcels)

            next_btn = await page.query_selector(".PageRight:not(.PageDisabled), [title='Next Page']")
            if not next_btn:
                break
            await next_btn.click()
            await page.wait_for_load_state("load", timeout=60000)
            page_num += 1
            await asyncio.sleep(1)

        await browser.close()

    return all_parcels
