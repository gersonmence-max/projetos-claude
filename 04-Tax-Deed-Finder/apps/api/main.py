"""
LandHQ FastAPI backend — serves dashboard data and triggers pipeline runs.
"""
import asyncio
import logging
import os
import sys

# Add project root to path so db/scrapers/etc are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from db.client import get_client
from scheduler.jobs import start_scheduler, run_pipeline

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("landhq.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("ENABLE_SCHEDULER", "true").lower() == "true":
        start_scheduler()
    yield


app = FastAPI(title="LandHQ API", version="1.0.0", lifespan=lifespan)

_frontend_url = os.environ.get("FRONTEND_URL", "")
_allowed_origins = ["http://localhost:3000"]
if _frontend_url:
    _allowed_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Models ----------

class SaveParcelRequest(BaseModel):
    parcel_id: str
    notes: Optional[str] = None


# ---------- Parcels ----------

@app.get("/api/parcels")
async def list_parcels(
    state: Optional[str] = None,
    county_id: Optional[str] = None,
    property_type: Optional[str] = None,
    min_score: int = Query(0, ge=0, le=100),
    max_score: int = Query(100, ge=0, le=100),
    min_bid: Optional[float] = None,
    max_bid: Optional[float] = None,
    min_acres: Optional[float] = None,
    max_acres: Optional[float] = None,
    auction_within_days: Optional[int] = None,
    road_type: Optional[str] = None,
    max_drive_time: Optional[int] = None,
    min_discount: Optional[float] = None,
    min_roi: Optional[float] = None,
    has_ai_analysis: Optional[bool] = None,
    order_by: str = Query("score_total", pattern="^(score_total|discount_percent|minimum_bid|auction_date|of_roi_percent)$"),
    order_dir: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    db = get_client()

    # Build query joining parcels + scores + risks + counties
    query = (
        db.table("parcels")
        .select(
            "id, external_id, parcel_number, address, city, state, zip, "
            "property_type, acres, sqft, bedrooms, bathrooms, year_built, zoning, "
            "gps_lat, gps_lng, auction_platform, auction_url, minimum_bid, "
            "auction_date, auction_status, county_id, "
            "counties(name, state), "
            "parcel_scores(score_total, score_discount, score_population_growth, "
            "score_road_access, score_size, score_bid_price, market_value_estimate, "
            "discount_percent, of_resale_price, of_down_payment, of_monthly_payment, "
            "of_term_months, of_total_return, of_roi_percent, of_months_to_recover, "
            "ai_recommendation, ai_analyzed_at), "
            "parcel_risks(flood_zone, wetlands_percent, tornado_risk, has_road_access, "
            "road_type, nearest_city, nearest_city_distance_miles, drive_time_minutes, "
            "passes_auto_filters, has_additional_liens, liens_amount)"
        )
        .neq("auction_status", "cancelled")
        .neq("auction_status", "sold")
    )

    if state:
        query = query.eq("state", state.upper())
    if county_id:
        query = query.eq("county_id", county_id)
    if property_type:
        query = query.eq("property_type", property_type)
    if min_bid is not None:
        query = query.gte("minimum_bid", min_bid)
    if max_bid is not None:
        query = query.lte("minimum_bid", max_bid)
    if min_acres is not None:
        query = query.gte("acres", min_acres)
    if max_acres is not None:
        query = query.lte("acres", max_acres)
    if auction_within_days is not None:
        from datetime import date, timedelta
        today_str = date.today().isoformat()
        cutoff_str = (date.today() + timedelta(days=auction_within_days)).isoformat()
        query = query.gte("auction_date", today_str).lte("auction_date", cutoff_str)

    result = query.execute()
    items = result.data or []

    # Parcelas sem enrichment (parcel_risks=None) ainda aparecem; só exclui as que falharam no auto-filter
    items = [
        i for i in items
        if (i.get("parcel_risks") is None) or (i.get("parcel_risks") or {}).get("passes_auto_filters", True)
    ]

    # Post-filter on joined table fields (Supabase limitation)
    if min_score > 0 or max_score < 100:
        items = [
            i for i in items
            if min_score <= (i.get("parcel_scores") or {}).get("score_total", 0) <= max_score
        ]
    if min_discount is not None:
        items = [
            i for i in items
            if (i.get("parcel_scores") or {}).get("discount_percent", 0) >= min_discount
        ]
    if min_roi is not None:
        items = [
            i for i in items
            if (i.get("parcel_scores") or {}).get("of_roi_percent", 0) >= min_roi
        ]
    if road_type:
        items = [
            i for i in items
            if (i.get("parcel_risks") or {}).get("road_type") == road_type
        ]
    if max_drive_time is not None:
        items = [
            i for i in items
            if (i.get("parcel_risks") or {}).get("drive_time_minutes", 0) <= max_drive_time
        ]
    if has_ai_analysis is True:
        items = [i for i in items if (i.get("parcel_scores") or {}).get("ai_analyzed_at")]

    # Sort
    reverse = order_dir == "desc"
    def sort_key(i):
        if order_by == "score_total":
            return (i.get("parcel_scores") or {}).get("score_total", 0)
        if order_by == "discount_percent":
            return (i.get("parcel_scores") or {}).get("discount_percent", 0) or 0
        if order_by == "of_roi_percent":
            return (i.get("parcel_scores") or {}).get("of_roi_percent", 0) or 0
        if order_by == "minimum_bid":
            return i.get("minimum_bid", 0)
        if order_by == "auction_date":
            return i.get("auction_date", "") or ""
        return 0
    items.sort(key=sort_key, reverse=reverse)

    total = len(items)
    start = (page - 1) * page_size
    items = items[start : start + page_size]

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.get("/api/parcels/{parcel_id}")
async def get_parcel(parcel_id: str):
    db = get_client()
    result = (
        db.table("parcels")
        .select(
            "*, counties(*), parcel_scores(*), parcel_risks(*), parcel_valuations(*)"
        )
        .eq("id", parcel_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return result.data


@app.get("/api/parcels/{parcel_id}/liens")
async def get_parcel_liens(parcel_id: str):
    """Returns all liens found for a parcel from the Clerk's Office."""
    db = get_client()
    result = (
        db.table("parcel_liens")
        .select("*")
        .eq("parcel_id", parcel_id)
        .order("recorded_date", desc=True)
        .execute()
    )
    records = result.data or []
    active = [r for r in records if not r.get("is_released")]
    surviving = [r for r in active if r.get("survives_tax_deed")]
    return {
        "records": records,
        "total": len(records),
        "active": len(active),
        "surviving": len(surviving),
        "surviving_amount": sum(r.get("lien_amount") or 0 for r in surviving),
        "surviving_types": list({r["lien_type"] for r in surviving}),
    }


@app.get("/api/dashboard/summary")
async def dashboard_summary():
    db = get_client()
    from datetime import date, timedelta

    today = date.today().isoformat()
    week = (date.today() + timedelta(days=7)).isoformat()

    total = db.table("parcels").select("id", count="exact").neq("auction_status", "cancelled").execute()
    new_today = db.table("parcels").select("id", count="exact").gte("created_at", today).execute()
    high_score = (
        db.table("parcel_scores").select("id", count="exact")
        .gte("score_total", 70)
        .execute()
    )
    soon = (
        db.table("parcels").select("id", count="exact")
        .lte("auction_date", week)
        .gte("auction_date", today)
        .neq("auction_status", "cancelled")
        .execute()
    )

    return {
        "total_monitored": total.count or 0,
        "new_today": new_today.count or 0,
        "score_70_plus": high_score.count or 0,
        "auctions_next_7_days": soon.count or 0,
    }


@app.get("/api/counties")
async def list_counties():
    db = get_client()
    result = db.table("counties").select("*").order("state").order("name").execute()
    return result.data or []


@app.patch("/api/counties/{county_id}")
async def toggle_county(county_id: str, active: bool):
    db = get_client()
    db.table("counties").update({"active": active}).eq("id", county_id).execute()
    return {"ok": True}


@app.get("/api/saved")
async def list_saved():
    db = get_client()
    result = (
        db.table("saved_parcels")
        .select("*, parcels(*, counties(name, state), parcel_scores(score_total, of_roi_percent))")
        .order("saved_at", desc=True)
        .execute()
    )
    return result.data or []


@app.post("/api/saved")
async def save_parcel(req: SaveParcelRequest):
    db = get_client()
    result = db.table("saved_parcels").insert({
        "parcel_id": req.parcel_id,
        "notes": req.notes,
    }).execute()
    return result.data[0] if result.data else {"ok": True}


@app.delete("/api/saved/{saved_id}")
async def remove_saved(saved_id: str):
    db = get_client()
    db.table("saved_parcels").delete().eq("id", saved_id).execute()
    return {"ok": True}


@app.patch("/api/saved/{saved_id}/notes")
async def update_notes(saved_id: str, notes: str):
    db = get_client()
    db.table("saved_parcels").update({"notes": notes}).eq("id", saved_id).execute()
    return {"ok": True}


@app.get("/api/analytics")
async def analytics():
    db = get_client()

    # Counties with most opportunities (score >= 50)
    county_opps = (
        db.table("parcels")
        .select("counties(name, state), parcel_scores(score_total)")
        .gte("parcel_scores.score_total", 50)
        .execute()
    )

    # Score distribution
    scores = db.table("parcel_scores").select("score_total").execute()
    score_data = [s["score_total"] for s in (scores.data or [])]
    buckets = {
        "0-24": sum(1 for s in score_data if s < 25),
        "25-49": sum(1 for s in score_data if 25 <= s < 50),
        "50-69": sum(1 for s in score_data if 50 <= s < 70),
        "70-84": sum(1 for s in score_data if 70 <= s < 85),
        "85-100": sum(1 for s in score_data if s >= 85),
    }

    return {
        "score_distribution": buckets,
        "total_scored": len(score_data),
    }


@app.post("/api/pipeline/run")
async def trigger_pipeline():
    """Manually trigger the full pipeline. Non-blocking."""
    asyncio.create_task(run_pipeline())
    return {"status": "started", "message": "Pipeline iniciado em background"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "landhq-api"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    is_dev = os.environ.get("ENVIRONMENT", "production") == "development"
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=is_dev)
