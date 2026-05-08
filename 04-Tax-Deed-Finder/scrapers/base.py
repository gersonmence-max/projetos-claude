from dataclasses import dataclass, field
from datetime import date
from typing import Optional
import re


@dataclass
class RawParcel:
    external_id: str
    county_id: str
    auction_platform: str
    auction_url: str
    minimum_bid: float
    auction_date: Optional[date]
    auction_status: str = "upcoming"
    parcel_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    property_type: str = "land"
    acres: Optional[float] = None
    sqft: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    year_built: Optional[int] = None
    zoning: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    raw_data: dict = field(default_factory=dict)


def parse_dollar(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(text))
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_acres(text: str) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"([\d,.]+)\s*(?:ac|acre|acres)?", str(text), re.IGNORECASE)
    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return None
    return None
