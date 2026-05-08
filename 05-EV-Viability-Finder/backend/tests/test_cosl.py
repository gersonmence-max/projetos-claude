# backend/tests/test_cosl.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.cosl import _parse_cosl_item


def _make_item(**kwargs):
    base = {
        "CoSLParcelNumber": "931-00001-000",
        "CoSLCountyName": "SALINE",
        "CoSLPropertyId": 99,
        "Acreage": 5.2,
        "CurrentBid": 4250.00,   # API field is CurrentBid, not StartingBid
        "End": "2026-05-15T20:00:00Z",
        "Section": "03",
        "Township": "07S",
        "Range": "09W",
        "Owner": "JOHN DOE",
    }
    base.update(kwargs)
    return base


def test_parse_basic_fields():
    result = _parse_cosl_item(_make_item())
    assert result["source"] == "cosl"
    assert result["state"] == "AR"
    assert result["county"] == "Saline"
    assert result["price"] == 4250.00
    assert result["acres"] == 5.2
    assert result["parcel_id"] == "931-00001-000"
    assert result["sale_date"] == "2026-05-15"
    assert result["listing_url"] == "https://auction.cosl.org/auctions?id=99"


def test_parse_address_from_legal_description():
    result = _parse_cosl_item(_make_item())
    assert "03-07S-09W" in result["address"]
    assert "Saline" in result["address"]


def test_parse_missing_acreage_returns_none():
    result = _parse_cosl_item(_make_item(Acreage=None))
    assert result["acres"] is None


def test_parse_missing_bid_returns_none():
    result = _parse_cosl_item(_make_item(CurrentBid=None))
    assert result["price"] is None


def test_parse_end_date_formats():
    result = _parse_cosl_item(_make_item(End="2026-12-31T23:59:00Z"))
    assert result["sale_date"] == "2026-12-31"


def test_parse_missing_end_date():
    result = _parse_cosl_item(_make_item(End=None))
    assert result["sale_date"] is None


def test_parse_missing_prop_id_gives_none_url():
    result = _parse_cosl_item(_make_item(CoSLPropertyId=None))
    assert result["listing_url"] is None
