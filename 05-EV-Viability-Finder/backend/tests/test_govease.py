# backend/tests/test_govease.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.govease import _parse_grid_html, _parse_face_value


# Real GovEase API: 11 cells per row
# [0]empty [1]empty [2]internal_id [3]parcel_id [4]owner_or_address
# [5]face_value [6]property_address [7]auction_name [8]type [9]empty [10]empty
_SAMPLE_GRID = """
<table>
  <thead>
    <tr>
      <th></th><th></th><th>#</th><th>Parcel #</th><th>Owner</th>
      <th>Face Value</th><th>Address</th><th>Auction Name</th>
      <th>Type</th><th></th><th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td></td>
      <td></td>
      <td>23641</td>
      <td>13-01-02-1-001-002.000</td>
      <td>JANE DOE LLC</td>
      <td>$3,450.00</td>
      <td>123 Main St, Colbert, AL</td>
      <td>2026 Colbert County Tax Lien Auction</td>
      <td>Tax Lien</td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td></td>
      <td></td>
      <td>23642</td>
      <td>98-76-54-321.000</td>
      <td>BOB SMITH</td>
      <td>$1,200.50</td>
      <td>456 Oak Ave, Colbert, AL</td>
      <td>2026 Colbert County Tax Lien Auction</td>
      <td>Tax Deed</td>
      <td></td>
      <td></td>
    </tr>
  </tbody>
</table>
"""


def test_parse_grid_returns_two_rows():
    results = _parse_grid_html(_SAMPLE_GRID, county_id=1252, county_name="Colbert")
    assert len(results) == 2


def test_parse_first_row_fields():
    results = _parse_grid_html(_SAMPLE_GRID, county_id=1252, county_name="Colbert")
    r = results[0]
    assert r["source"] == "govease"
    assert r["state"] == "AL"
    assert r["county"] == "Colbert"
    assert r["parcel_id"] == "13-01-02-1-001-002.000"
    assert r["address"] == "123 Main St, Colbert, AL"
    assert r["price"] == 3450.00
    assert r["listing_url"] == "https://liveauctions.govease.com/al/alcolbert/1252/browsebiddown#13-01-02-1-001-002.000"


def test_parse_face_value():
    assert _parse_face_value("$3,450.00") == 3450.00
    assert _parse_face_value("$1,200.50") == 1200.50
    assert _parse_face_value("") is None
    assert _parse_face_value("N/A") is None


def test_parse_empty_grid_returns_empty_list():
    results = _parse_grid_html("<table><tbody></tbody></table>", county_id=1252, county_name="Colbert")
    assert results == []


def test_parse_malformed_row_skipped():
    bad_html = "<table><tbody><tr><td>only one cell</td></tr></tbody></table>"
    results = _parse_grid_html(bad_html, county_id=1252, county_name="Colbert")
    assert results == []
