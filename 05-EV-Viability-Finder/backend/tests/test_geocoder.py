# backend/tests/test_geocoder.py
"""Testa geocoder com respostas mockadas (sem chamadas de rede reais)."""
import sys, os, asyncio, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import AsyncMock, patch

import enrichers.geocoder as geo_module
from enrichers.geocoder import is_legal_description, _normalize, geocode_batch


def test_legal_description_detecta_township():
    assert is_legal_description("T12N R5E Section 24, Garland County AR") is True


def test_legal_description_detecta_nw():
    assert is_legal_description("NW 1/4 SW 1/4 Sec 5") is True


def test_legal_description_rejeita_endereco_normal():
    assert is_legal_description("123 Main St, Little Rock, AR") is False


def test_normalize():
    assert _normalize("  123  Main St  ") == "123 main st"


@pytest.mark.asyncio
async def test_geocode_usa_cache():
    geo_module._cache = {"123 main st, ar": [34.5, -92.3]}
    geo_module._cache_loaded = True
    result = await geo_module.geocode("123 Main St, AR")
    assert result == (34.5, -92.3)


@pytest.mark.asyncio
async def test_geocode_legal_description_retorna_none():
    geo_module._cache = {}
    geo_module._cache_loaded = True
    result = await geo_module.geocode("NW Quarter Section 12 Township 5N")
    assert result is None


@pytest.mark.asyncio
async def test_geocode_cache_none_nao_refaz_chamada():
    """Se cache tem None (tentativa prévia falhou), não faz nova chamada de rede."""
    geo_module._cache = {"456 oak ave, ar": None}
    geo_module._cache_loaded = True
    with patch("enrichers.geocoder._census_geocode") as mock_census:
        result = await geo_module.geocode("456 Oak Ave, AR")
    assert result is None
    mock_census.assert_not_called()


@pytest.mark.asyncio
async def test_geocode_batch_preenche_lat_lng():
    geo_module._cache = {}
    geo_module._cache_loaded = True
    listings = [
        {"address": "789 Pine Rd, Hope, AR", "price": 500},
        {"address": "T5N R3E Sec 12", "price": 200},  # legal desc → skip
        {"address": "321 Oak St, Selma, AL", "lat": 32.4, "lng": -87.0},  # já tem coords → skip
    ]
    fake_result = (34.5, -92.5)
    with patch("enrichers.geocoder.geocode", new=AsyncMock(return_value=fake_result)):
        await geocode_batch(listings)
    # Apenas o primeiro deve ter sido geocodificado
    assert listings[0].get("lat") == 34.5
    assert listings[1].get("lat") is None
    assert listings[2].get("lat") == 32.4  # inalterado
