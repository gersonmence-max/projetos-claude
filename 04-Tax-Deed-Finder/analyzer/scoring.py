"""
Scoring engine — pure mathematical rules, no AI.
Scores parcels 0-100 across 5 components.
Also applies automatic exclusion filters before scoring.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParcelData:
    property_type: str
    acres: Optional[float]
    minimum_bid: float


@dataclass
class ValuationData:
    market_value_estimate: Optional[float]
    assessed_value: Optional[float]


@dataclass
class DemographicsData:
    growth_rate_3yr: Optional[float]


@dataclass
class RiskData:
    flood_zone: str
    wetlands_percent: float
    is_landlocked: bool
    has_road_access: bool
    road_type: str  # paved, unpaved, none
    has_additional_liens: bool
    liens_amount: float
    drive_time_minutes: Optional[float]
    acres: Optional[float]
    assessed_value: Optional[float]


@dataclass
class ScoreResult:
    score_total: int
    score_discount: int
    score_population_growth: int
    score_road_access: int
    score_size: int
    score_bid_price: int
    discount_percent: Optional[float]
    passes_filters: bool
    filter_fail_reasons: list[str]


def apply_auto_filters(risk: RiskData) -> tuple[bool, list[str]]:
    """
    Returns (passes, fail_reasons).
    A parcel is excluded if ANY filter triggers.
    """
    reasons: list[str] = []

    HIGH_RISK_FLOOD = {"A", "AE", "AO", "AH", "VE"}
    if risk.flood_zone.upper() in HIGH_RISK_FLOOD:
        reasons.append(f"flood_zone:{risk.flood_zone}")

    if risk.wetlands_percent > 50:
        reasons.append(f"wetlands:{risk.wetlands_percent:.0f}%")

    if risk.is_landlocked:
        reasons.append("landlocked")

    if not risk.has_road_access:
        reasons.append("no_road_access")

    if risk.assessed_value is not None and 0 < risk.assessed_value < 200:
        reasons.append(f"assessed_value_too_low:{risk.assessed_value}")

    if risk.acres is not None and risk.acres < 0.1:
        reasons.append(f"too_small:{risk.acres}ac")

    if risk.has_additional_liens and risk.liens_amount > 500:
        reasons.append(f"liens:{risk.liens_amount:.0f}")

    if risk.drive_time_minutes is not None and risk.drive_time_minutes > 120:
        reasons.append(f"drive_time:{risk.drive_time_minutes:.0f}min")

    return (len(reasons) == 0, reasons)


def calculate_score(
    parcel: ParcelData,
    valuation: ValuationData,
    demographics: DemographicsData,
    risks: RiskData,
) -> ScoreResult:
    """
    Scores a parcel 0-100 across 5 components.
    Filters are applied first — failed parcels get score 0.
    """
    passes, fail_reasons = apply_auto_filters(risks)

    if not passes:
        return ScoreResult(
            score_total=0,
            score_discount=0,
            score_population_growth=0,
            score_road_access=0,
            score_size=0,
            score_bid_price=0,
            discount_percent=None,
            passes_filters=False,
            filter_fail_reasons=fail_reasons,
        )

    score_discount = 0
    discount_percent = None

    if valuation.market_value_estimate and valuation.market_value_estimate > 0:
        discount = (1 - parcel.minimum_bid / valuation.market_value_estimate) * 100
        discount_percent = round(discount, 1)
        if discount >= 80:
            score_discount = 40
        elif discount >= 60:
            score_discount = 30
        elif discount >= 40:
            score_discount = 20
        elif discount >= 20:
            score_discount = 10

    # Population growth (0-20 pts)
    score_pop = 0
    growth = demographics.growth_rate_3yr or 0
    if growth > 0:
        score_pop += 5
    if growth >= 3:
        score_pop += 5
    if growth >= 5:
        score_pop += 5
    if growth >= 7:
        score_pop += 5

    # Road access (0-20 pts)
    score_road = 0
    if risks.road_type == "paved":
        score_road = 20
    elif risks.road_type == "unpaved":
        score_road = 10

    # Size and usability (0-10 pts)
    score_size = 0
    if parcel.property_type == "house":
        score_size = 10
    elif parcel.acres is not None:
        if 0.25 <= parcel.acres <= 1:
            score_size = 10
        elif 1 < parcel.acres <= 5:
            score_size = 8
        elif parcel.acres > 5:
            score_size = 6

    # Minimum bid (0-10 pts)
    score_bid = 0
    bid = parcel.minimum_bid
    if bid < 100:
        score_bid = 10
    elif bid < 250:
        score_bid = 8
    elif bid <= 500:
        score_bid = 6
    elif bid <= 2000:
        score_bid = 4

    total = score_discount + score_pop + score_road + score_size + score_bid

    return ScoreResult(
        score_total=min(total, 100),
        score_discount=score_discount,
        score_population_growth=score_pop,
        score_road_access=score_road,
        score_size=score_size,
        score_bid_price=score_bid,
        discount_percent=discount_percent,
        passes_filters=True,
        filter_fail_reasons=[],
    )
