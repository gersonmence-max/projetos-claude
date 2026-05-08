# backend/classifier.py
"""Classifica terrenos em FORTE / MODERADO / FRACO / EVITAR."""
from typing import Any, Dict


def classify_property(prop: Dict[str, Any]) -> Dict[str, str]:
    """Retorna {"classification": "FORTE"|"MODERADO"|"FRACO"|"EVITAR"}.

    FORTE  — score>=75, FEMA segura, pop>=15k, desconto>=50%
    MODERADO — score>=55, 2+ dos 3 critérios acima
    EVITAR — FEMA A/AE com score<65, ou mercado muito pequeno com score<70
    FRACO  — demais (baixa prioridade)
    """
    score        = prop.get("score") or 0.0
    discount_pct = prop.get("discount_pct") or 0.0
    fema_zone    = (prop.get("fema_zone") or "").upper()
    population   = prop.get("population") or 0

    fema_safe  = fema_zone in ("X", "X500", "B")
    big_market = population >= 15_000
    big_disc   = discount_pct >= 50.0

    # EVITAR — checagens de segurança primeiro
    if fema_zone in ("A", "AE") and score < 65:
        return {"classification": "EVITAR"}
    if 0 < population < 5_000 and score < 70:
        return {"classification": "EVITAR"}

    # FORTE — todos os 3 critérios obrigatórios
    if score >= 75 and fema_safe and big_market and big_disc:
        return {"classification": "FORTE"}

    # MODERADO — pelo menos 2 dos 3 critérios
    criteria = sum([fema_safe, big_market, big_disc])
    if score >= 55 and criteria >= 2:
        return {"classification": "MODERADO"}

    return {"classification": "FRACO"}


# Alias para compatibilidade com pipeline.py (que importa classify_investment)
def classify_investment(prop: Dict[str, Any]) -> Dict[str, str]:
    return classify_property(prop)
