"""
APScheduler daily pipeline — runs at 2AM.
Orchestrates scraping → enrichment → scoring → alerts.
"""
import asyncio
import logging
import os
from datetime import datetime, date

import resend
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from db.client import get_client
from scrapers import bid4assets, govease, realauction
from enrichers import (
    fema_flood, wetlands, noaa_tornado, usgs_elevation,
    osm_access, osrm_distance, census, assessor, rentcast, liens,
)
from analyzer.scoring import (
    calculate_score, apply_auto_filters,
    ParcelData, ValuationData, DemographicsData, RiskData,
)
from analyzer.owner_financing import calculate_owner_financing
from analyzer.ai_analysis import analyze_parcel

log = logging.getLogger("landhq.scheduler")

SCRAPER_MAP = {
    "bid4assets": bid4assets.scrape_county,
    "govease": govease.scrape_county,
    "realauction": realauction.scrape_county,
}

SCORE_THRESHOLD_VALUATION = 50
SCORE_THRESHOLD_AI = 70
SCORE_THRESHOLD_ALERT = 75


async def run_pipeline():
    """Full daily pipeline: scrape → enrich → score → alert."""
    log.info("Pipeline started at %s", datetime.now())
    db = get_client()

    # Load active counties
    result = db.table("counties").select("*").eq("active", True).execute()
    counties = result.data or []
    log.info("Processing %d active counties", len(counties))

    for county in counties:
        try:
            await _process_county(db, county)
        except Exception as e:
            log.error("County %s failed: %s", county["name"], e)

    log.info("Pipeline complete at %s", datetime.now())


async def _process_county(db, county: dict):
    platform = county["auction_platform"]
    scraper = SCRAPER_MAP.get(platform)
    if not scraper:
        log.warning("No scraper for platform: %s", platform)
        return

    log.info("Scraping %s, %s via %s", county["name"], county["state"], platform)
    parcels = await scraper(
        county_id=county["auction_platform_county_id"],
        county_db_id=county["id"],
    )
    log.info("  Found %d parcels", len(parcels))

    # Fetch county demographics once
    demo_data = await census.get_county_demographics(county["name"], county["state"])

    # Upsert demographics
    if "error" not in demo_data:
        db.table("county_demographics").upsert({
            "county_id": county["id"],
            "population_latest": demo_data.get("population_latest"),
            "population_2020": demo_data.get("population_2020"),
            "growth_rate_3yr": demo_data.get("growth_rate_3yr"),
            "median_household_income": demo_data.get("median_household_income"),
            "updated_at": datetime.now().isoformat(),
        }, on_conflict="county_id").execute()

    for raw in parcels:
        await _process_parcel(db, raw, county, demo_data)


async def _process_parcel(db, raw, county: dict, demo_data: dict):
    # Upsert parcel
    parcel_row = {
        "county_id": raw.county_id,
        "external_id": raw.external_id,
        "parcel_number": raw.parcel_number,
        "address": raw.address,
        "city": raw.city,
        "state": raw.state or county["state"],
        "zip": raw.zip,
        "property_type": raw.property_type,
        "acres": raw.acres,
        "sqft": raw.sqft,
        "bedrooms": raw.bedrooms,
        "bathrooms": raw.bathrooms,
        "year_built": raw.year_built,
        "zoning": raw.zoning,
        "gps_lat": raw.gps_lat,
        "gps_lng": raw.gps_lng,
        "auction_platform": raw.auction_platform,
        "auction_url": raw.auction_url,
        "minimum_bid": raw.minimum_bid,
        "auction_date": raw.auction_date.isoformat() if raw.auction_date else None,
        "auction_status": raw.auction_status,
        "raw_data": raw.raw_data,
        "updated_at": datetime.now().isoformat(),
    }
    result = db.table("parcels").upsert(
        parcel_row, on_conflict="county_id,external_id"
    ).execute()
    parcel_id = result.data[0]["id"] if result.data else None
    if not parcel_id:
        return

    lat = raw.gps_lat
    lng = raw.gps_lng
    if not lat or not lng:
        return  # skip enrichment without coordinates

    # --- Enrichment (all in parallel) ---
    flood_task = fema_flood.get_flood_zone(lat, lng)
    wetlands_task = wetlands.get_wetlands_percent(lat, lng, raw.acres or 1.0)
    tornado_task = noaa_tornado.get_tornado_risk(lat, lng, county["state"])
    elev_task = usgs_elevation.get_elevation_slope(lat, lng)
    road_task = osm_access.get_road_access(lat, lng)
    city_task = osrm_distance.get_nearest_city(lat, lng)
    assessor_task = assessor.get_assessor_data(
        raw.parcel_number or "",
        county["name"],
        county["state"],
        county.get("assessor_url", ""),
        county.get("assessor_api_type", "scrape"),
    )

    (flood, wetland, tornado, elev, road, city, assess) = await asyncio.gather(
        flood_task, wetlands_task, tornado_task, elev_task, road_task, city_task, assessor_task
    )

    risk_row = {
        "parcel_id": parcel_id,
        "flood_zone": flood.get("flood_zone", "X"),
        "flood_zone_source": flood.get("source"),
        "wetlands_percent": wetland.get("wetlands_percent", 0),
        "wetlands_source": wetland.get("source"),
        "tornado_risk": tornado.get("tornado_risk", "low"),
        "tornado_f2_count_10yr": tornado.get("tornado_f2_count_10yr", 0),
        "slope_percent": elev.get("slope_percent", 0),
        "has_road_access": road.get("has_road_access", True),
        "road_type": road.get("road_type", "paved"),
        "nearest_city": city.get("nearest_city"),
        "nearest_city_distance_miles": city.get("nearest_city_distance_miles"),
        "nearest_city_population": city.get("nearest_city_population"),
        "drive_time_minutes": city.get("drive_time_minutes"),
        "has_additional_liens": False,
        "liens_amount": 0,
        "is_landlocked": False,
        "checked_at": datetime.now().isoformat(),
    }

    # --- Passo 6: Clerk's Office liens check ---
    owner_name = assess.get("owner_name") or raw.address or ""
    liens_result = await liens.check_liens(
        parcel_id=parcel_id,
        owner_name=owner_name,
        address=raw.address or "",
        county_name=county["name"],
        state=county["state"],
    )
    # Apply liens data to risk_row before saving
    risk_row["has_additional_liens"] = liens_result.has_additional_liens
    risk_row["liens_amount"] = liens_result.surviving_amount

    # Re-evaluate filters now that liens data is real
    risk_data = RiskData(
        flood_zone=risk_row["flood_zone"],
        wetlands_percent=risk_row["wetlands_percent"],
        is_landlocked=risk_row["is_landlocked"],
        has_road_access=risk_row["has_road_access"],
        road_type=risk_row["road_type"],
        has_additional_liens=risk_row["has_additional_liens"],
        liens_amount=risk_row["liens_amount"],
        drive_time_minutes=risk_row["drive_time_minutes"],
        acres=raw.acres,
        assessed_value=assess.get("assessed_value"),
    )
    passes, fail_reasons = apply_auto_filters(risk_data)
    risk_row["passes_auto_filters"] = passes
    risk_row["filter_fail_reasons"] = fail_reasons

    db.table("parcel_risks").upsert(risk_row, on_conflict="parcel_id").execute()
    await liens.save_liens_to_db(db, liens_result)

    if not passes:
        return

    # Update assessor data on parcel
    if assess.get("assessed_value"):
        db.table("parcels").update({
            "zoning": assess.get("zoning") or raw.zoning,
            "acres": assess.get("acres_from_assessor") or raw.acres,
        }).eq("id", parcel_id).execute()

    # Quick score (no Rentcast yet) to decide if we fetch market value
    quick_score = calculate_score(
        ParcelData(property_type=raw.property_type, acres=raw.acres, minimum_bid=raw.minimum_bid),
        ValuationData(market_value_estimate=None, assessed_value=assess.get("assessed_value")),
        DemographicsData(growth_rate_3yr=demo_data.get("growth_rate_3yr")),
        risk_data,
    )

    market_value = None
    comparable_sales = []

    if quick_score.score_total >= SCORE_THRESHOLD_VALUATION:
        rent_data = await rentcast.get_market_value(
            address=raw.address or "",
            city=raw.city or city.get("nearest_city", ""),
            state=raw.state or county["state"],
            zip_code=raw.zip or "",
            property_type=raw.property_type,
            bedrooms=raw.bedrooms,
            bathrooms=raw.bathrooms,
            sqft=raw.sqft,
        )
        market_value = rent_data.get("market_value_estimate")
        comparable_sales = rent_data.get("comparable_sales", [])

        valuation_row = {
            "parcel_id": parcel_id,
            "assessed_value": assess.get("assessed_value"),
            "market_value_estimate": market_value,
            "price_per_acre": (market_value / raw.acres) if market_value and raw.acres else None,
            "comparable_sales": comparable_sales,
            "valuation_source": rent_data.get("source", "unknown"),
            "checked_at": datetime.now().isoformat(),
        }
        db.table("parcel_valuations").upsert(valuation_row, on_conflict="parcel_id").execute()

    # Final score with market value
    final_score = calculate_score(
        ParcelData(property_type=raw.property_type, acres=raw.acres, minimum_bid=raw.minimum_bid),
        ValuationData(market_value_estimate=market_value, assessed_value=assess.get("assessed_value")),
        DemographicsData(growth_rate_3yr=demo_data.get("growth_rate_3yr")),
        risk_data,
    )

    # Owner financing
    of_result = None
    if market_value:
        of_result = calculate_owner_financing(raw.minimum_bid, market_value)

    score_row = {
        "parcel_id": parcel_id,
        "score_total": final_score.score_total,
        "score_discount": final_score.score_discount,
        "score_population_growth": final_score.score_population_growth,
        "score_road_access": final_score.score_road_access,
        "score_size": final_score.score_size,
        "score_bid_price": final_score.score_bid_price,
        "minimum_bid": raw.minimum_bid,
        "market_value_estimate": market_value,
        "discount_percent": final_score.discount_percent,
        "of_resale_price": of_result.resale_price if of_result else None,
        "of_down_payment": of_result.down_payment if of_result else None,
        "of_monthly_payment": of_result.monthly_payment if of_result else None,
        "of_term_months": of_result.term_months if of_result else None,
        "of_total_return": of_result.total_return if of_result else None,
        "of_roi_percent": of_result.roi_percent if of_result else None,
        "of_months_to_recover": of_result.months_to_recover if of_result else None,
        "scored_at": datetime.now().isoformat(),
    }

    # AI analysis for high-score parcels
    if final_score.score_total >= SCORE_THRESHOLD_AI and market_value:
        ai = await analyze_parcel(
            parcel={**vars(raw), "county_name": county["name"]},
            valuation={
                "assessed_value": assess.get("assessed_value"),
                "market_value_estimate": market_value,
                "discount_percent": final_score.discount_percent,
                "valuation_source": "rentcast",
            },
            risk=risk_row,
            demographics={**demo_data, "county_name": county["name"], "state": county["state"]},
            owner_financing=vars(of_result) if of_result else {},
        )
        score_row["ai_analysis"] = ai.get("ai_analysis")
        score_row["ai_recommendation"] = ai.get("ai_recommendation")
        score_row["ai_analyzed_at"] = datetime.now().isoformat()

    db.table("parcel_scores").upsert(score_row, on_conflict="parcel_id").execute()

    # Alert for very high scores
    if final_score.score_total >= SCORE_THRESHOLD_ALERT:
        await _send_alert(db, parcel_id, raw, final_score.score_total, county)


async def _send_alert(db, parcel_id: str, raw, score: int, county: dict):
    email = os.environ.get("ALERT_EMAIL", "")
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not email or not api_key or api_key == "placeholder":
        return

    resend.api_key = api_key
    subject = f"🏠 LandHQ: Nova oportunidade score {score} — {raw.address or raw.external_id}"
    body = f"""
    <h2>Nova oportunidade no LandHQ</h2>
    <p><strong>Score:</strong> {score}/100</p>
    <p><strong>Endereço:</strong> {raw.address or 'N/A'}</p>
    <p><strong>Condado:</strong> {county['name']}, {county['state']}</p>
    <p><strong>Lance mínimo:</strong> ${raw.minimum_bid:,.0f}</p>
    <p><strong>Data do leilão:</strong> {raw.auction_date}</p>
    <p><a href="{raw.auction_url}">Ver leilão</a></p>
    """
    try:
        resend.Emails.send({
            "from": "LandHQ <alerts@landhq.app>",
            "to": [email],
            "subject": subject,
            "html": body,
        })
        db.table("alerts").insert({
            "parcel_id": parcel_id,
            "alert_type": "new_opportunity",
            "score_at_alert": score,
            "email_sent_to": email,
        }).execute()
    except Exception as e:
        log.error("Alert send failed: %s", e)


def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(hour=2, minute=0),
        id="daily_pipeline",
        name="Daily property collection",
        replace_existing=True,
    )
    scheduler.start()
    log.info("Scheduler started — pipeline runs daily at 02:00")
    return scheduler
