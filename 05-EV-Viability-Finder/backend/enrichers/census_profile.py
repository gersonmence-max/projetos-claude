# backend/enrichers/census_profile.py
"""Busca dados demográficos por condado via Census Bureau ACS.

Fonte: American Community Survey 5-year estimates (2022) — gratuito, oficial, sem API key.
Variáveis:
  B01003_001E = população total
  B19013_001E = renda mediana domiciliar ($)
  B25001_001E = total de unidades habitacionais (proxy de atividade de mercado)

Usados no scorer para calcular liquidez do mercado local.
"""
import statistics
from typing import Dict, Optional, Tuple

import httpx

# State FIPS codes
_STATE_FIPS = {"AL": "01", "AR": "05"}

# (county_lower, state_upper) → {population, median_hh_income, housing_units}
_county_cache: Dict[Tuple[str, str], dict] = {}

# Médias estaduais como fallback
_state_cache: Dict[str, dict] = {}

_CENSUS_URL = "https://api.census.gov/data/2022/acs/acs5"

# Sentinel do Census para dados suprimidos/ausentes
_MISSING_SENTINEL = -666666666


def _normalize_county(name: str) -> str:
    """Remove sufixos como 'County, Arkansas' e normaliza para lower.

    Census retorna 'Carroll County, Arkansas' — queremos 'carroll'.
    """
    return name.split(" County")[0].strip().lower()


def _parse_int(value) -> Optional[int]:
    """Converte valor do Census para int, retornando None para dados ausentes."""
    try:
        v = int(value)
        if v == _MISSING_SENTINEL:
            return None
        return v
    except (ValueError, TypeError):
        return None


async def _fetch_state_demographics(state: str) -> Dict[str, dict]:
    """Retorna {county_lower: {population, median_hh_income, housing_units}} para o estado."""
    fips = _STATE_FIPS.get(state.upper())
    if not fips:
        return {}

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(
                _CENSUS_URL,
                params={
                    "get": "B01003_001E,B19013_001E,B25001_001E,NAME",
                    "for": "county:*",
                    "in": f"state:{fips}",
                },
            )
            if resp.status_code != 200:
                print(f"Census demographics API {state}: status {resp.status_code}")
                return {}

            rows = resp.json()
            # Primeira linha é cabeçalho:
            # ['B01003_001E', 'B19013_001E', 'B25001_001E', 'NAME', 'state', 'county']
            result = {}
            for row in rows[1:]:
                try:
                    county_name = _normalize_county(row[3])
                    result[county_name] = {
                        "population": _parse_int(row[0]),
                        "median_hh_income": _parse_int(row[1]),
                        "housing_units": _parse_int(row[2]),
                    }
                except (ValueError, IndexError):
                    continue

            print(f"Census demographics {state}: {len(result)} condados carregados")
            return result

        except Exception as e:
            print(f"Census demographics API {state} erro: {e}")
            return {}


def _compute_state_averages(county_data: Dict[str, dict]) -> dict:
    """Calcula médias estaduais para uso como fallback."""
    populations = [v["population"] for v in county_data.values() if v.get("population") is not None]
    incomes = [v["median_hh_income"] for v in county_data.values() if v.get("median_hh_income") is not None]
    units = [v["housing_units"] for v in county_data.values() if v.get("housing_units") is not None]

    return {
        "population": int(statistics.median(populations)) if populations else None,
        "median_hh_income": int(statistics.median(incomes)) if incomes else None,
        "housing_units": int(statistics.median(units)) if units else None,
    }


async def build_county_profiles(states: list = None) -> None:
    """Busca e armazena em cache os dados demográficos por condado.

    Deve ser chamada uma vez por execução do pipeline.
    """
    global _county_cache, _state_cache
    if states is None:
        states = ["AL", "AR"]

    _county_cache = {}
    _state_cache = {}

    for state in states:
        county_data = await _fetch_state_demographics(state)
        for county, profile in county_data.items():
            _county_cache[(county, state.upper())] = profile

        if county_data:
            _state_cache[state.upper()] = _compute_state_averages(county_data)

    print(
        f"Cache demográfico (Census): {len(_county_cache)} condados | "
        f"fallbacks: {list(_state_cache.keys())}"
    )


def get_county_profile(county: str, state: str) -> dict:
    """Retorna dados demográficos do condado.

    Tenta condado primeiro; usa médias estaduais como fallback.
    Retorna {} se nenhum dado disponível.

    Returns:
        dict com chaves: population, median_hh_income, housing_units
        Valores podem ser int ou None para dados ausentes.
    """
    key = (county.strip().lower(), state.strip().upper())
    profile = _county_cache.get(key)
    if profile is not None:
        return profile

    fallback = _state_cache.get(state.strip().upper())
    if fallback is not None:
        return fallback

    return {}
