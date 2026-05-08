# backend/tests/test_census_profile.py
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import enrichers.census_profile as census_module
from enrichers.census_profile import (
    get_county_profile,
    build_county_profiles,
    _normalize_county,
    _parse_int,
)


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------

def test_normalize_county_removes_state_suffix():
    assert _normalize_county("Carroll County, Arkansas") == "carroll"


def test_normalize_county_handles_different_states():
    assert _normalize_county("Mobile County, Alabama") == "mobile"


def test_normalize_county_lowercases():
    assert _normalize_county("Jefferson County, Alabama") == "jefferson"


def test_parse_int_normal_value():
    assert _parse_int("50000") == 50000


def test_parse_int_missing_sentinel_returns_none():
    assert _parse_int("-666666666") is None


def test_parse_int_invalid_string_returns_none():
    assert _parse_int("N/A") is None


def test_parse_int_none_input_returns_none():
    assert _parse_int(None) is None


# ---------------------------------------------------------------------------
# Tests for get_county_profile (cache-based, no HTTP)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_caches():
    """Reset module caches before each test to ensure isolation."""
    census_module._county_cache = {}
    census_module._state_cache = {}
    yield
    census_module._county_cache = {}
    census_module._state_cache = {}


def test_get_county_profile_returns_cached_data():
    census_module._county_cache[("washington", "AL")] = {
        "population": 180000,
        "median_hh_income": 52000,
        "housing_units": 75000,
    }
    result = get_county_profile("Washington", "AL")
    assert result["population"] == 180000
    assert result["median_hh_income"] == 52000
    assert result["housing_units"] == 75000


def test_get_county_profile_normalizes_county_name():
    census_module._county_cache[("benton", "AR")] = {
        "population": 279000,
        "median_hh_income": 68000,
        "housing_units": 110000,
    }
    # Should match even with different casing and whitespace
    result = get_county_profile("  Benton  ", "ar")
    assert result["population"] == 279000


def test_get_county_profile_uses_state_fallback():
    census_module._state_cache["AL"] = {
        "population": 50000,
        "median_hh_income": 45000,
        "housing_units": 20000,
    }
    # County not in cache — should return state fallback
    result = get_county_profile("unknown_county", "AL")
    assert result["population"] == 50000
    assert result["median_hh_income"] == 45000


def test_get_county_profile_returns_empty_dict_when_no_data():
    result = get_county_profile("nonexistent", "TX")
    assert result == {}


def test_get_county_profile_county_takes_priority_over_fallback():
    census_module._county_cache[("mobile", "AL")] = {
        "population": 413000,
        "median_hh_income": 48000,
        "housing_units": 180000,
    }
    census_module._state_cache["AL"] = {
        "population": 50000,
        "median_hh_income": 45000,
        "housing_units": 20000,
    }
    result = get_county_profile("Mobile", "AL")
    # County-level data should win
    assert result["population"] == 413000


# ---------------------------------------------------------------------------
# Integration test — mocks the HTTP call to Census API
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_county_profiles_populates_cache():
    """Tests that build_county_profiles correctly parses Census API response."""
    # Census API returns header row + data rows
    mock_response_al = [
        ["B01003_001E", "B19013_001E", "B25001_001E", "NAME", "state", "county"],
        ["182265", "51382", "76433", "Mobile County, Alabama", "01", "097"],
        ["659892", "60244", "278501", "Jefferson County, Alabama", "01", "073"],
        ["-666666666", "35000", "5000", "Suppressed County, Alabama", "01", "999"],
    ]
    mock_response_ar = [
        ["B01003_001E", "B19013_001E", "B25001_001E", "NAME", "state", "county"],
        ["279141", "68472", "111200", "Benton County, Arkansas", "05", "007"],
    ]

    def make_mock_response(data):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = data
        return mock_resp

    call_count = 0

    async def mock_get(url, params=None):
        nonlocal call_count
        state_fips = params.get("in", "").replace("state:", "")
        if state_fips == "01":
            return make_mock_response(mock_response_al)
        elif state_fips == "05":
            return make_mock_response(mock_response_ar)
        return make_mock_response([[]])

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = mock_get

    with patch("enrichers.census_profile.httpx.AsyncClient", return_value=mock_client):
        await build_county_profiles(states=["AL", "AR"])

    # Verify AL county was cached
    mobile_profile = get_county_profile("Mobile", "AL")
    assert mobile_profile["population"] == 182265
    assert mobile_profile["median_hh_income"] == 51382
    assert mobile_profile["housing_units"] == 76433

    # Verify suppressed value becomes None
    suppressed = get_county_profile("Suppressed", "AL")
    assert suppressed["population"] is None
    assert suppressed["median_hh_income"] == 35000

    # Verify AR county was cached
    benton_profile = get_county_profile("Benton", "AR")
    assert benton_profile["population"] == 279141

    # Verify state-level fallback was computed for AL
    al_fallback = census_module._state_cache.get("AL")
    assert al_fallback is not None
    assert al_fallback["median_hh_income"] is not None


@pytest.mark.asyncio
async def test_build_county_profiles_handles_api_error_gracefully():
    """Tests that a failing API call leaves cache empty without raising."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("enrichers.census_profile.httpx.AsyncClient", return_value=mock_client):
        # Should not raise
        await build_county_profiles(states=["AL"])

    # Cache should be empty
    assert get_county_profile("Mobile", "AL") == {}
