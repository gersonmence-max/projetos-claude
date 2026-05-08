# backend/routes/properties.py
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case as sql_case
from sqlalchemy.orm import Session

from database import get_db
from models import Property
from scorer import calculate_score_breakdown

router = APIRouter(prefix="/properties", tags=["properties"])

_CLASSIFICATION_ORDER = sql_case(
    (Property.classification == "FORTE", 1),
    (Property.classification == "MODERADO", 2),
    (Property.classification == "FRACO", 3),
    (Property.classification == "EVITAR", 4),
    else_=5,
)


def _prop_to_dict(p: Property, include_breakdown: bool = False) -> Dict[str, Any]:
    ai_analysis = None
    if p.ai_analysis:
        try:
            ai_analysis = json.loads(p.ai_analysis)
        except Exception:
            pass

    result: Dict[str, Any] = {
        "id": p.id,
        "source": p.source,
        "state": p.state,
        "county": p.county,
        "address": p.address,
        "lat": p.lat,
        "lng": p.lng,
        "price": p.price,
        "acres": p.acres,
        "price_per_acre": p.price_per_acre,
        "discount_pct": p.discount_pct,
        "fema_zone": p.fema_zone,
        "score": p.score,
        "classification": p.classification,
        "ai_analysis": ai_analysis,
        "listing_url": p.listing_url,
        "parcel_id": p.parcel_id,
        "sale_date": p.sale_date,
        "scraped_at": p.scraped_at.isoformat() if p.scraped_at else None,
        "passed_filters": p.passed_filters,
        "population": p.population,
        "median_hh_income": p.median_hh_income,
    }

    if include_breakdown:
        result["score_breakdown"] = calculate_score_breakdown({
            "discount_pct": p.discount_pct,
            "fema_zone": p.fema_zone,
            "population": p.population,
            "median_hh_income": p.median_hh_income,
        })

    return result


@router.get("/")
def list_properties(
    state: Optional[str] = None,
    county: Optional[str] = None,
    classification: Optional[str] = None,
    min_score: float = Query(0, ge=0, le=100),
    max_price: Optional[float] = Query(None),
    min_acres: Optional[float] = Query(None),
    max_price_per_acre: Optional[float] = Query(None),
    min_discount_pct: Optional[float] = Query(None),
    limit: int = Query(200, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Property).filter(Property.passed_filters == True)

    if state:
        q = q.filter(Property.state == state)
    if county:
        q = q.filter(Property.county.ilike(f"%{county}%"))
    if classification:
        q = q.filter(Property.classification == classification.upper())
    if min_score:
        q = q.filter(Property.score >= min_score)
    if max_price is not None:
        q = q.filter(Property.price <= max_price)
    if min_acres is not None:
        q = q.filter(Property.acres >= min_acres)
    if max_price_per_acre is not None:
        q = q.filter(Property.price_per_acre <= max_price_per_acre)
    if min_discount_pct is not None:
        q = q.filter(Property.discount_pct >= min_discount_pct)

    props = q.order_by(_CLASSIFICATION_ORDER, Property.score.desc()).limit(limit).all()
    return [_prop_to_dict(p) for p in props]


@router.get("/{property_id}")
def get_property(property_id: int, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Propriedade não encontrada")
    return _prop_to_dict(prop, include_breakdown=True)
