# backend/scorer.py
import json
from typing import Any, Dict, Optional

from anthropic import AsyncAnthropic

from config import ANTHROPIC_API_KEY

_client: Optional[AsyncAnthropic] = None


def _get_client() -> Optional[AsyncAnthropic]:
    global _client
    if ANTHROPIC_API_KEY and _client is None:
        _client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def calculate_score_breakdown(property_data: Dict[str, Any]) -> Dict[str, float]:
    """Retorna pontuação de cada componente: {a_pts, b_pts, c_pts}."""
    discount_pct = property_data.get("discount_pct") or 0.0
    fema_zone    = (property_data.get("fema_zone") or "").upper()
    population   = property_data.get("population") or 0
    income       = property_data.get("median_hh_income") or 0.0

    # A. Desconto real (50 pts)
    a_pts = min(discount_pct / 80.0 * 50.0, 50.0) if discount_pct > 0 else 0.0

    # B. Liquidez do mercado (35 pts)
    if population >= 50_000:
        pop_pts = 20.0
    elif population >= 10_000:
        pop_pts = (population - 10_000) / 40_000 * 20.0
    elif population >= 2_500:
        pop_pts = (population - 2_500) / 7_500 * 8.0
    else:
        pop_pts = 0.0

    if income >= 55_000:
        inc_pts = 15.0
    elif income >= 35_000:
        inc_pts = (income - 35_000) / 20_000 * 15.0
    elif income >= 25_000:
        inc_pts = (income - 25_000) / 10_000 * 5.0
    else:
        inc_pts = 0.0

    b_pts = pop_pts + inc_pts

    # C. Risco FEMA (15 pts)
    if not fema_zone:
        c_pts = 5.0   # neutro — sem dado
    elif fema_zone == "X":
        c_pts = 15.0
    elif fema_zone in ("X500", "B"):
        c_pts = 10.0
    elif fema_zone == "C":
        c_pts = 7.0
    else:
        c_pts = 0.0   # A, AE e outros

    return {"a_pts": round(a_pts, 1), "b_pts": round(b_pts, 1), "c_pts": round(c_pts, 1)}


def calculate_score(property_data: Dict[str, Any]) -> float:
    """Score 0-100: A(desconto 50) + B(liquidez 35) + C(FEMA 15). Sem penalidades."""
    bd = calculate_score_breakdown(property_data)
    total = bd["a_pts"] + bd["b_pts"] + bd["c_pts"]
    return round(min(max(total, 0.0), 100.0), 1)


async def generate_ai_analysis(property_data: Dict[str, Any]) -> Optional[Dict]:
    """Gera análise textual do Claude para terrenos com score >= 70.

    Desabilitada por padrão no pipeline — chame explicitamente quando necessário.
    """
    client = _get_client()
    if not client:
        return None

    if (property_data.get("score") or 0) < 70:
        return None

    prompt = f"""Analise este terreno nos EUA e responda em JSON.

Dados:
- Endereço: {property_data.get("address", "N/A")}
- Estado: {property_data.get("state", "N/A")} | Condado: {property_data.get("county", "N/A")}
- Preço total: ${property_data.get("price", 0):,.0f}
- Tamanho: {property_data.get("acres", 0):.1f} acres
- Preço/acre: ${property_data.get("price_per_acre", 0):,.0f}
- Desconto vs. mercado: {property_data.get("discount_pct", 0):.1f}%
- Zona FEMA: {property_data.get("fema_zone", "N/A")}
- Score calculado: {property_data.get("score", 0)}/100

Responda SOMENTE com JSON válido, sem texto adicional:
{{
  "resumo": "2-3 frases explicando por que este terreno é interessante ou não",
  "pontos_positivos": ["ponto 1", "ponto 2", "ponto 3"],
  "pontos_atencao": ["ponto 1", "ponto 2"],
  "veredicto": "Oportunidade forte"
}}

O veredicto deve ser exatamente um de: "Oportunidade forte", "Merece análise", "Cautela"."""

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(message.content[0].text)
    except Exception as e:
        print(f"Erro ao gerar análise Claude: {e}")
        return None
