# backend/enrichers/geocoder.py
"""Geocodifica endereços de rua para (lat, lng).

Fonte primária: Census Geocoder (gratuito, sem chave)
Fallback: Nominatim/OpenStreetMap (gratuito, sem chave, 1 req/s)

Cache persistente: backend/geocache.json
  Formato: {"endereço normalizado": [lat, lng] | null}
  null = tentativa prévia falhou (não tenta novamente)
"""
import asyncio
import json
import os
import re

import httpx

_CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "geocache.json")
_cache: dict = {}
_cache_loaded = False

# Semáforo para respeitar limite de 1 req/s do Nominatim
_nominatim_sem = asyncio.Semaphore(1)

# Regex para detectar descrições legais (COSL) — não tenta geocodificar
_LEGAL_DESC = re.compile(
    r"\b(sec\s*\d|t\s*\d+\s*[ns]|r\s*\d+\s*[ew]|nw\s*\d|sw\s*\d|ne\s*\d|se\s*\d|"
    r"township|range|section|lot\s*\d+\s+block|parcel)\b",
    re.IGNORECASE,
)


def _load_cache() -> None:
    global _cache, _cache_loaded
    if _cache_loaded:
        return
    if os.path.exists(_CACHE_PATH):
        try:
            with open(_CACHE_PATH, encoding="utf-8") as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}
    _cache_loaded = True


def _save_cache() -> None:
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"geocache: erro ao salvar: {e}")


def _normalize(address: str) -> str:
    return " ".join(address.strip().lower().split())


def is_legal_description(address: str) -> bool:
    """Retorna True se o endereço parecer uma descrição legal (não geocodificável)."""
    return bool(_LEGAL_DESC.search(address))


async def _census_geocode(address: str, client: httpx.AsyncClient):
    """Tenta Census Geocoder. Retorna [lat, lng] ou None."""
    try:
        resp = await client.get(
            "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
            params={
                "address": address,
                "benchmark": "2020",
                "format": "json",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        matches = data.get("result", {}).get("addressMatches", [])
        if not matches:
            return None
        coords = matches[0]["coordinates"]
        return [float(coords["y"]), float(coords["x"])]
    except Exception:
        return None


async def _nominatim_geocode(address: str, client: httpx.AsyncClient):
    """Fallback Nominatim. Respeita limite 1 req/s via semáforo."""
    async with _nominatim_sem:
        try:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": "buscador-de-terrenos/1.0"},
                timeout=10,
            )
            await asyncio.sleep(1.1)
            if resp.status_code != 200:
                return None
            results = resp.json()
            if not results:
                return None
            return [float(results[0]["lat"]), float(results[0]["lon"])]
        except Exception:
            return None


async def geocode(address: str):
    """Retorna (lat, lng) ou None. Usa cache; persiste após cada resultado."""
    _load_cache()

    if not address or is_legal_description(address):
        return None

    key = _normalize(address)
    if key in _cache:
        cached = _cache[key]
        return (cached[0], cached[1]) if cached else None

    async with httpx.AsyncClient() as client:
        coords = await _census_geocode(address, client)
        if coords is None:
            coords = await _nominatim_geocode(address, client)

    _cache[key] = coords  # None → "tentou, falhou"
    _save_cache()

    return (coords[0], coords[1]) if coords else None


async def geocode_batch(listings: list) -> None:
    """Geocodifica in-place todos os listings que têm endereço mas não têm lat/lng."""
    _load_cache()
    to_geocode = [
        l for l in listings
        if l.get("address") and not l.get("lat") and not l.get("lng")
        and not is_legal_description(l.get("address", ""))
    ]
    if not to_geocode:
        return

    print(f"Geocoder: {len(to_geocode)} endereços para geocodificar ...")
    results = await asyncio.gather(*[geocode(l["address"]) for l in to_geocode])
    for listing, result in zip(to_geocode, results):
        if result:
            listing["lat"], listing["lng"] = result
    print("Geocoder: concluído.")
