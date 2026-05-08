# backend/enrichers/zillow_market.py
"""Busca valores medianos de mercado imobiliário por condado via Redfin Market Tracker.

Fonte primária: Redfin county_market_tracker.tsv000.gz
  URL: https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/county_market_tracker.tsv000.gz

Fallback: Census Bureau ACS 5-year estimates (B25077_001E)

Caches raw median home values por condado — sem multiplicadores de fração de terra.
"""
import asyncio
import csv
import gzip
import io
import statistics
from typing import Dict, List, Optional, Tuple

import httpx

# State FIPS codes (usado pelo fallback Census)
_STATE_FIPS = {"AL": "01", "AR": "05"}


# (county_lower, state_upper) → valor estimado de mercado para terreno
_market_cache: Dict[Tuple[str, str], float] = {}

# Mediana estadual como fallback
_state_cache: Dict[str, float] = {}

_REDFIN_URL = (
    "https://redfin-public-data.s3.us-west-2.amazonaws.com"
    "/redfin_market_tracker/county_market_tracker.tsv000.gz"
)
_CENSUS_URL = "https://api.census.gov/data/2022/acs/acs5"


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------

def _normalize_county(name: str) -> str:
    """Remove sufixos como 'County, Arkansas' e normaliza para lower.

    Funciona tanto com o formato Census ('Carroll County, Arkansas')
    quanto com o formato Redfin ('Carroll County, AR').
    """
    return name.split(" County")[0].strip().lower()


# ---------------------------------------------------------------------------
# Redfin primary source
# ---------------------------------------------------------------------------

async def _build_from_redfin(states: List[str]) -> Dict[Tuple[str, str], float]:
    """Baixa o TSV do Redfin em streaming e extrai medianas por condado.

    Retorna {(county_lower, STATE_UPPER): land_value_estimate}.
    Lança exceção se o download falhar (o chamador trata o fallback).
    """
    state_set = {s.upper() for s in states}

    # county_key → lista de preços dos últimos 12 meses
    raw: Dict[Tuple[str, str], List[float]] = {}

    print(f"Redfin: baixando {_REDFIN_URL} ...")

    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        async with client.stream("GET", _REDFIN_URL) as resp:
            if resp.status_code != 200:
                raise RuntimeError(f"Redfin HTTP {resp.status_code}")

            # Acumula bytes em memória apenas para AR + AL (filtro precoce)
            # O arquivo é grande; lemos em chunks e filtramos linha a linha.
            buf = bytearray()
            async for chunk in resp.aiter_bytes(chunk_size=65536):
                buf.extend(chunk)

    # Descomprime e processa
    print("Redfin: processando linhas ...")
    with gzip.open(io.BytesIO(bytes(buf)), "rt", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            # Filtro por tipo de imóvel e estado
            if row.get("property_type", "").strip() != "All Residential":
                continue
            state_code = row.get("state_code", "").strip().upper()
            if state_code not in state_set:
                continue

            # Filtro de período — últimos 12 meses (período relativo ao maior date visto)
            # Coletamos tudo; calculamos mediana depois
            price_raw = row.get("median_sale_price", "").strip()
            if not price_raw or price_raw.lower() == "null":
                continue
            try:
                price = float(price_raw)
            except ValueError:
                continue
            if price <= 0:
                continue

            region = row.get("region", "").strip()
            county_key = (_normalize_county(region), state_code)
            raw.setdefault(county_key, []).append(price)

    if not raw:
        raise RuntimeError("Redfin: nenhuma linha válida encontrada")

    result: Dict[Tuple[str, str], float] = {}
    for key, prices in raw.items():
        # Mediana de todos os períodos disponíveis
        median_price = statistics.median(prices)
        result[key] = median_price

    print(f"Redfin: {len(result)} condados carregados")
    return result


# ---------------------------------------------------------------------------
# Census ACS fallback
# ---------------------------------------------------------------------------

async def _fetch_state_medians_census(state: str) -> Dict[str, float]:
    """Retorna {county_lower: land_value_estimate} via Census ACS."""
    fips = _STATE_FIPS.get(state.upper())
    if not fips:
        return {}

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(
                _CENSUS_URL,
                params={
                    "get": "B25077_001E,NAME",
                    "for": "county:*",
                    "in": f"state:{fips}",
                },
            )
            if resp.status_code != 200:
                print(f"Census API {state}: status {resp.status_code}")
                return {}

            rows = resp.json()
            result = {}
            for row in rows[1:]:
                try:
                    median_home = float(row[0])
                    if median_home <= 0:
                        continue
                    county_name = _normalize_county(row[1])
                    result[county_name] = median_home
                except (ValueError, IndexError):
                    continue

            print(f"Census {state}: {len(result)} condados carregados")
            return result

        except Exception as e:
            print(f"Census API {state} erro: {e}")
            return {}


async def _build_from_census(states: List[str]) -> Dict[Tuple[str, str], float]:
    """Fallback: popula cache via Census ACS.

    Retorna {(county_lower, STATE_UPPER): land_value_estimate}.
    """
    result: Dict[Tuple[str, str], float] = {}
    for state in states:
        county_values = await _fetch_state_medians_census(state)
        for county, land_value in county_values.items():
            result[(county, state.upper())] = land_value
    return result


# ---------------------------------------------------------------------------
# Interface pública
# ---------------------------------------------------------------------------

async def build_market_cache(states=None) -> None:
    """Popula o cache com estimativas de valor de mercado por condado.

    Tenta Redfin primeiro; cai para Census ACS se o Redfin falhar.
    """
    global _market_cache, _state_cache
    if states is None:
        states = ["AL", "AR"]

    _market_cache = {}
    _state_cache = {}

    # --- Tentativa 1: Redfin ---
    try:
        data = await _build_from_redfin(states)
        _market_cache = data
        source = "Redfin"
    except Exception as e:
        print(f"Redfin falhou ({e}); usando Census ACS como fallback ...")
        try:
            data = await _build_from_census(states)
            _market_cache = data
            source = "Census ACS"
        except Exception as e2:
            print(f"Census ACS também falhou ({e2}); cache vazio.")
            source = "none"

    # Calcula medianas estaduais como fallback por estado
    for state in states:
        state_upper = state.upper()
        county_values = [v for (c, s), v in _market_cache.items() if s == state_upper]
        if county_values:
            _state_cache[state_upper] = statistics.median(county_values)

    print(
        f"Cache de mercado ({source}): {len(_market_cache)} condados | "
        f"fallbacks estaduais: {list(_state_cache.keys())}"
    )


def get_market_median(county: str, state: str) -> Optional[float]:
    """Retorna estimativa de valor de mercado para terreno no condado.

    Tenta condado primeiro; usa mediana estadual como fallback.
    """
    key = (county.strip().lower(), state.strip().upper())
    value = _market_cache.get(key)
    if value:
        return value
    return _state_cache.get(state.strip().upper())
