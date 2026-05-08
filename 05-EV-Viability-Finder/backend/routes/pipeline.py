# backend/routes/pipeline.py
import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from classifier import classify_investment
from config import REGRID_API_KEY
from database import SessionLocal, get_db
from enrichers.census_profile import build_county_profiles, get_county_profile
from enrichers.fema import get_fema_zone
from enrichers.geocoder import geocode_batch
from enrichers.regrid import get_regrid_data
from enrichers.zillow_market import build_market_cache, get_market_median
from filters import FilterConfig, apply_filters, is_junk_property
from models import PipelineRun, Property
from scrapers.cosl import scrape_cosl
from scrapers.govease import scrape_govease
from scorer import calculate_score

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run")
async def run_pipeline(db: Session = Depends(get_db)):
    """Dispara o pipeline de scraping em background."""
    run = PipelineRun(status="rodando")
    db.add(run)
    db.commit()
    db.refresh(run)

    asyncio.create_task(_pipeline_task(run.id))

    return {"run_id": run.id, "status": "rodando"}


@router.get("/status/{run_id}")
async def pipeline_status_sse(run_id: int):
    """SSE stream com status em tempo real do pipeline."""

    async def generator():
        db = SessionLocal()
        try:
            while True:
                run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
                if not run:
                    yield f"data: {json.dumps({'error': 'Run não encontrado'})}\n\n"
                    break

                payload = {
                    "status": run.status,
                    "scraped": run.scraped,
                    "enriched": run.enriched,
                    "filtered": run.filtered,
                    "scored": run.scored,
                    "error_msg": run.error_msg,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                }
                yield f"data: {json.dumps(payload)}\n\n"

                if run.status in ("concluído", "erro"):
                    break

                await asyncio.sleep(1)
                db.refresh(run)
        finally:
            db.close()

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/history")
def pipeline_history(db: Session = Depends(get_db)):
    runs = (
        db.query(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "id": r.id,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "scraped": r.scraped,
            "enriched": r.enriched,
            "filtered": r.filtered,
            "scored": r.scored,
            "error_msg": r.error_msg,
        }
        for r in runs
    ]


async def _pipeline_task(run_id: int) -> None:
    """Tarefa background: scraping → enriquecimento → filtros → score → classificação."""
    db = SessionLocal()
    try:
        run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not run:
            return
        filter_config = FilterConfig()
        regrid_available = bool(REGRID_API_KEY)

        # ── 1. Scraping ──────────────────────────────────────────────────
        cosl_listings = await scrape_cosl()
        govease_listings = await scrape_govease()
        all_listings = cosl_listings + govease_listings
        run.scraped = len(all_listings)
        db.commit()

        # ── 1b. Dados de referência (paralelo) ───────────────────────────
        await asyncio.gather(
            build_market_cache(states=["AL", "AR"]),
            build_county_profiles(states=["AL", "AR"]),
        )

        # ── 1c. Geocodificação em lote (GovEase tem endereços reais) ─────
        await geocode_batch(all_listings)

        # ── 2. Enriquecimento + filtros + score ──────────────────────────
        for listing in all_listings:
            # Junk pre-filter (antes de qualquer enriquecimento caro)
            if is_junk_property(listing):
                continue

            lat = listing.get("lat")
            lng = listing.get("lng")

            if lat and lng:
                fema_zone = await get_fema_zone(lat, lng)
                if fema_zone:
                    listing["fema_zone"] = fema_zone

                if regrid_available:
                    regrid = await get_regrid_data(lat, lng)
                    if regrid:
                        for key, val in regrid.items():
                            if val is not None:
                                listing[key] = val

            price = listing.get("price")
            acres = listing.get("acres")
            if price and acres and acres > 0:
                listing["price_per_acre"] = price / acres

            # Desconto vs. mercado Redfin/Census
            market_median = get_market_median(
                listing.get("county", ""), listing.get("state", "")
            )
            if market_median and price and market_median > 0:
                if acres and acres > 0:
                    price_per_acre = price / acres
                    listing["discount_pct"] = (1 - price_per_acre / market_median) * 100
                else:
                    listing["discount_pct"] = (1 - price / market_median) * 100

            # Dados demográficos do condado (Score B - liquidez)
            profile = get_county_profile(
                listing.get("county", ""), listing.get("state", "")
            )
            if profile:
                if profile.get("population") is not None:
                    listing["population"] = profile["population"]
                if profile.get("median_hh_income") is not None:
                    listing["median_hh_income"] = profile["median_hh_income"]

            run.enriched = (run.enriched or 0) + 1
            db.commit()

            passed = apply_filters(listing, filter_config, regrid_available)
            listing["passed_filters"] = passed

            if not passed:
                continue

            run.filtered = (run.filtered or 0) + 1
            db.commit()

            listing["score"] = calculate_score(listing)

            # Classificação de investimento
            classification = classify_investment(listing)
            listing.update(classification)

            # Salvar no DB
            valid_cols = {c.name for c in Property.__table__.columns}
            prop_data = {k: v for k, v in listing.items() if k in valid_cols}

            try:
                db.add(Property(**prop_data))
                db.commit()
                run.scored = (run.scored or 0) + 1
                db.commit()
            except IntegrityError:
                db.rollback()

        run.status = "concluído"
        run.finished_at = datetime.utcnow()
        db.commit()

    except Exception as exc:
        db.rollback()
        run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if run:
            run.status = "erro"
            run.error_msg = str(exc)
            run.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
