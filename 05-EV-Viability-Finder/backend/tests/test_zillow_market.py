# backend/tests/test_zillow_market.py
import pytest
import sys
import os
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import enrichers.zillow_market as zillow_module
from enrichers.zillow_market import (
    get_market_median,
    build_market_cache,
)


# ---------------------------------------------------------------------------
# Fixture: Reset caches before each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_caches():
    """Reset module caches before each test to ensure isolation."""
    zillow_module._market_cache = {}
    zillow_module._state_cache = {}
    yield
    zillow_module._market_cache = {}
    zillow_module._state_cache = {}


# ---------------------------------------------------------------------------
# Test 1: get_market_median returns None when cache is empty
# ---------------------------------------------------------------------------

def test_get_market_median_returns_none_when_cache_empty():
    """Calling get_market_median before build_market_cache should return None."""
    # Cache is empty (reset by fixture)
    result = get_market_median("Carroll", "AR")
    assert result is None


# ---------------------------------------------------------------------------
# Test 2: get_market_median returns county value when in cache
# ---------------------------------------------------------------------------

def test_get_market_median_returns_county_value():
    """Injecting data into _market_cache should return that value."""
    # Directly inject data into cache
    zillow_module._market_cache[("carroll", "AR")] = 5000.0

    result = get_market_median("Carroll", "AR")
    assert result == 5000.0


# ---------------------------------------------------------------------------
# Test 3: get_market_median normalizes county names
# ---------------------------------------------------------------------------

def test_get_market_median_normalizes_county_name():
    """County name normalization should handle mixed-case input."""
    # Inject with lowercase key
    zillow_module._market_cache[("carroll", "AR")] = 4500.0

    # Call with mixed case
    result = get_market_median("  CarRoll  ", "ar")
    assert result == 4500.0


# ---------------------------------------------------------------------------
# Test 4: get_market_median uses state fallback for unknown county
# ---------------------------------------------------------------------------

def test_get_market_median_uses_state_fallback():
    """When county is unknown, should use state-level fallback."""
    # Inject only into state cache
    zillow_module._state_cache["AR"] = 4000.0

    # Query for an unknown county
    result = get_market_median("UnknownCounty", "AR")
    assert result == 4000.0


# ---------------------------------------------------------------------------
# Test 5: build_market_cache falls back to Census on Redfin failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_market_cache_falls_back_to_census_on_redfin_failure():
    """When Redfin fails, should populate cache from Census ACS."""

    # Mock _build_from_redfin to raise RuntimeError
    async def mock_redfin_error(states):
        raise RuntimeError("Redfin HTTP 404")

    # Mock _build_from_census to return valid data
    async def mock_census_success(states):
        return {("carroll", "AR"): 5000.0}

    with patch(
        "enrichers.zillow_market._build_from_redfin",
        side_effect=mock_redfin_error,
    ):
        with patch(
            "enrichers.zillow_market._build_from_census",
            side_effect=mock_census_success,
        ):
            await build_market_cache(states=["AR"])

    # Verify cache was populated from Census
    assert ("carroll", "AR") in zillow_module._market_cache
    assert zillow_module._market_cache[("carroll", "AR")] == 5000.0

    # Verify state fallback was computed (median of the single county)
    assert "AR" in zillow_module._state_cache
    assert zillow_module._state_cache["AR"] == 5000.0


# ---------------------------------------------------------------------------
# Test 6: build_market_cache computes state fallback from multiple counties
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_market_cache_computes_state_fallback():
    """State fallback should be the median of all county values."""

    # Mock _build_from_redfin to return multiple counties
    async def mock_redfin_success(states):
        return {
            ("carroll", "AR"): 4000.0,
            ("washington", "AR"): 5000.0,
            ("benton", "AR"): 6000.0,
        }

    with patch(
        "enrichers.zillow_market._build_from_redfin",
        side_effect=mock_redfin_success,
    ):
        await build_market_cache(states=["AR"])

    # Verify state fallback is the median: median(4000, 5000, 6000) = 5000
    assert zillow_module._state_cache["AR"] == 5000.0


# ---------------------------------------------------------------------------
# Test 7: build_market_cache normalizes state names
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_market_cache_handles_multiple_states():
    """Should handle multiple states in a single call."""

    async def mock_redfin_success(states):
        return {
            ("carroll", "AR"): 5000.0,
            ("mobile", "AL"): 6000.0,
        }

    with patch(
        "enrichers.zillow_market._build_from_redfin",
        side_effect=mock_redfin_success,
    ):
        await build_market_cache(states=["AL", "AR"])

    # Verify both states have entries in state cache
    assert "AL" in zillow_module._state_cache
    assert "AR" in zillow_module._state_cache
    assert zillow_module._state_cache["AL"] == 6000.0
    assert zillow_module._state_cache["AR"] == 5000.0


# ---------------------------------------------------------------------------
# Test 8: get_market_median uses county over state fallback
# ---------------------------------------------------------------------------

def test_get_market_median_prefers_county_over_state():
    """County-level value should take priority over state fallback."""
    # Inject both county and state data
    zillow_module._market_cache[("carroll", "AR")] = 5000.0
    zillow_module._state_cache["AR"] = 3000.0

    # Should return county value, not state fallback
    result = get_market_median("Carroll", "AR")
    assert result == 5000.0
