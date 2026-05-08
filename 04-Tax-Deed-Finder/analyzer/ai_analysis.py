"""
Anthropic API fine analysis — only for parcels with score >= 70.
Uses claude-sonnet-4-20250514 with prompt caching for repeated schema sections.
"""
import os
import json
import anthropic
from typing import Optional

ANALYSIS_PROMPT_SYSTEM = """Você é um especialista em investimentos em terrenos e imóveis baratos nos EUA usando a estratégia de tax deed e owner financing. Analise imóveis e forneça pareceres práticos em português para investidores brasileiros."""

ANALYSIS_PROMPT_TEMPLATE = """Analise este imóvel e forneça um parecer objetivo em português:

DADOS DO IMÓVEL:
{parcel_data}

DADOS DE MERCADO:
{valuation_data}

DADOS DE RISCO:
{risk_data}

DADOS DEMOGRÁFICOS DO CONDADO:
{demographics_data}

CALCULADORA OWNER FINANCING:
{owner_financing_data}

Forneça exatamente neste formato:

RESUMO: [2 frases descrevendo o imóvel e por que apareceu na análise]

PONTOS POSITIVOS:
- [ponto 1]
- [ponto 2]
- [ponto 3]

PONTOS DE ATENÇÃO:
- [risco ou limitação 1]
- [risco ou limitação 2]

ESTRATÉGIA SUGERIDA: [owner financing / revenda rápida / land banking — com justificativa em 2-3 frases]

RECOMENDAÇÃO: [COMPRAR / MONITORAR / IGNORAR] — [justificativa em 1 frase]"""


def _format_parcel(p: dict) -> str:
    return (
        f"Endereço: {p.get('address', 'N/A')}, {p.get('city', '')}, {p.get('state', '')}\n"
        f"Tipo: {p.get('property_type', 'land')}\n"
        f"Área: {p.get('acres', 'N/A')} acres\n"
        f"Lance mínimo: ${p.get('minimum_bid', 0):,.0f}\n"
        f"Data do leilão: {p.get('auction_date', 'N/A')}\n"
        f"Zoneamento: {p.get('zoning', 'N/A')}\n"
        f"Condado: {p.get('county_name', 'N/A')}"
    )


def _format_valuation(v: dict) -> str:
    return (
        f"Valor avaliado pelo assessor: ${v.get('assessed_value', 0) or 0:,.0f}\n"
        f"Valor de mercado estimado: ${v.get('market_value_estimate', 0) or 0:,.0f}\n"
        f"Desconto sobre mercado: {v.get('discount_percent', 0) or 0:.1f}%\n"
        f"Fonte: {v.get('valuation_source', 'N/A')}"
    )


def _format_risk(r: dict) -> str:
    return (
        f"Zona de inundação: {r.get('flood_zone', 'X')}\n"
        f"Wetlands: {r.get('wetlands_percent', 0):.0f}% da área\n"
        f"Risco de tornado: {r.get('tornado_risk', 'low')}\n"
        f"Acesso por estrada: {'Sim' if r.get('has_road_access') else 'Não'} ({r.get('road_type', 'N/A')})\n"
        f"Distância da cidade mais próxima: {r.get('nearest_city_distance_miles', 'N/A')} milhas até {r.get('nearest_city', 'N/A')}\n"
        f"Tempo de direção: {r.get('drive_time_minutes', 'N/A')} minutos\n"
        f"Ônus adicionais: {'Sim — $' + str(r.get('liens_amount', 0)) if r.get('has_additional_liens') else 'Não'}"
    )


def _format_demographics(d: dict) -> str:
    return (
        f"Crescimento populacional 3 anos: {d.get('growth_rate_3yr', 0) or 0:.1f}%\n"
        f"População atual: {d.get('population_latest', 'N/A'):,}\n"
        f"Renda familiar mediana: ${d.get('median_household_income', 0) or 0:,}\n"
        f"Condado: {d.get('county_name', 'N/A')}, {d.get('state', 'N/A')}"
    )


def _format_owner_financing(of: dict) -> str:
    return (
        f"Preço de revenda sugerido (65% do mercado): ${of.get('resale_price', 0):,.0f}\n"
        f"Entrada (10%): ${of.get('down_payment', 0):,.0f}\n"
        f"Parcela mensal: ${of.get('monthly_payment', 0):,.0f}/mês por {of.get('term_months', 24)} meses\n"
        f"Retorno total: ${of.get('total_return', 0):,.0f}\n"
        f"ROI: {of.get('roi_percent', 0):.0f}%\n"
        f"Meses para recuperar investimento: {of.get('months_to_recover', 0):.0f}"
    )


async def analyze_parcel(
    parcel: dict,
    valuation: dict,
    risk: dict,
    demographics: dict,
    owner_financing: dict,
) -> dict:
    """
    Sends parcel data to Anthropic API for fine analysis.
    Returns analysis text and recommendation.
    Only called for score >= 70.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "placeholder":
        return {"error": "anthropic_no_key"}

    client = anthropic.Anthropic(api_key=api_key)

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        parcel_data=_format_parcel(parcel),
        valuation_data=_format_valuation(valuation),
        risk_data=_format_risk(risk),
        demographics_data=_format_demographics(demographics),
        owner_financing_data=_format_owner_financing(owner_financing),
    )

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": ANALYSIS_PROMPT_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )

        text = message.content[0].text if message.content else ""
        recommendation = "monitorar"
        if "RECOMENDAÇÃO: COMPRAR" in text.upper():
            recommendation = "comprar"
        elif "RECOMENDAÇÃO: IGNORAR" in text.upper():
            recommendation = "ignorar"

        return {
            "ai_analysis": text,
            "ai_recommendation": recommendation,
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        }
    except Exception as e:
        return {"error": str(e)}
