# backend/filters.py
import re as _re
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class FilterConfig:
    max_price: float = 500_000
    min_acres: float = 0.0
    min_discount_pct: float = 10.0
    max_price_per_acre: float = 10_000


# Palavras-chave que indicam parcelas sem valor de revenda
_JUNK_KEYWORDS = _re.compile(
    r"\b(right.of.way|row\b|easement|drainage|alley|utility|pipeline|"
    r"railroad|right of way|r/w|canal|ditch|median|buffer|common area|"
    r"common element|open space|unbuildable|landlocked)\b",
    _re.IGNORECASE,
)

_FLOOD_JUNK_ZONES = {"VE", "V"}  # zonas costeiras de alto risco


def is_junk_property(listing: dict) -> bool:
    """Retorna True se a propriedade for claramente inviável.

    Critérios:
    - Endereço/descrição contém palavras-chave de faixa de servidão ou área comum
    - Preço < $25 (provavelmente taxa sem ativo real)
    - Acres < 0,02 (menos de 800 m² — lote urbano mínimo)
    - Zona FEMA VE ou V (zona costeira de inundação extrema)
    """
    address = (listing.get("address") or "").lower()
    parcel  = (listing.get("parcel_id") or "").lower()
    text    = address + " " + parcel

    if _JUNK_KEYWORDS.search(text):
        return True

    price = listing.get("price") or 0.0
    if 0 < price < 25:
        return True

    acres = listing.get("acres")
    if acres is not None and 0 < acres < 0.10:
        return True

    fema_zone = (listing.get("fema_zone") or "").upper()
    if fema_zone in _FLOOD_JUNK_ZONES:
        return True

    return False


def apply_filters(
    property_data: Dict[str, Any],
    config: FilterConfig,
    regrid_available: bool,
) -> bool:
    """Retorna True se a propriedade passa em todos os filtros."""

    # ── Hard eliminations (always applied) ───────────────────────────
    fema_zone = (property_data.get("fema_zone") or "").upper()
    if fema_zone in ("A", "AE", "AO", "AH", "VE", "V"):
        return False

    population = property_data.get("population")
    if population is not None and 0 < population < 2_500:
        return False

    # ── Configurable filters ──────────────────────────────────────────
    price = property_data.get("price")
    if price is not None and price > config.max_price:
        return False

    acres = property_data.get("acres")
    if acres is not None and acres < config.min_acres:
        return False

    discount_pct = property_data.get("discount_pct")
    if discount_pct is not None and discount_pct < config.min_discount_pct:
        return False

    price_per_acre = property_data.get("price_per_acre")
    if price_per_acre is not None and price_per_acre > config.max_price_per_acre:
        return False

    return True
