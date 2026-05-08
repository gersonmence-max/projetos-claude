"""
scoring_engine.py
=================
Motor de scoring para avaliar viabilidade de locais
para instalacao de carregadores EV em Massachusetts.

Reconstruido a partir dos outputs reais do sistema (output.txt)
e documentacao de auditoria. Compativel com app.py.

Output de referencia usado na reconstrucao:
  Meadow Glen Mall [DCFC]
  Score Final:  9.1 / 10
  Potencial:    VERY HIGH
  Confianca:    0.98
  Breakdown: demand=8.8, competition=9.7, site_fit=10.0, ev_affinity=8.6
"""

import math
from typing import Tuple, Optional, Dict, Any, List


# ============================================================================
# CONSTANTES
# ============================================================================

POTENTIAL_THRESHOLDS = {
    'VERY HIGH': 8.5,
    'HIGH':      7.0,
    'MEDIUM':    5.0,
    'LOW':       0.0,
}

TYPE_BASE_SCORES = {
    'shopping_mall': {'demand': 8.5, 'site_fit': 9.5, 'ev_affinity': 8.0},
    'Shopping':      {'demand': 8.5, 'site_fit': 9.5, 'ev_affinity': 8.0},
    'hotel':         {'demand': 7.0, 'site_fit': 8.5, 'ev_affinity': 8.5},
    'Hotel':         {'demand': 7.0, 'site_fit': 8.5, 'ev_affinity': 8.5},
    'parking':       {'demand': 7.5, 'site_fit': 9.0, 'ev_affinity': 7.0},
    'Parking':       {'demand': 7.5, 'site_fit': 9.0, 'ev_affinity': 7.0},
    'supermarket':   {'demand': 7.8, 'site_fit': 8.0, 'ev_affinity': 7.5},
    'Supermarket':   {'demand': 7.8, 'site_fit': 8.0, 'ev_affinity': 7.5},
    'gas_station':   {'demand': 7.2, 'site_fit': 7.5, 'ev_affinity': 6.5},
    'Gas Station':   {'demand': 7.2, 'site_fit': 7.5, 'ev_affinity': 6.5},
    'restaurant':    {'demand': 6.5, 'site_fit': 6.5, 'ev_affinity': 6.0},
    'Restaurant':    {'demand': 6.5, 'site_fit': 6.5, 'ev_affinity': 6.0},
}

DEFAULT_BASE_SCORES = {'demand': 6.0, 'site_fit': 6.0, 'ev_affinity': 6.0}

SCORE_WEIGHTS = {
    'dcfc': {
        'demand':      0.30,
        'competition': 0.30,
        'site_fit':    0.25,
        'ev_affinity': 0.15,
    },
    'level2': {
        'demand':      0.25,
        'competition': 0.25,
        'site_fit':    0.30,
        'ev_affinity': 0.20,
    }
}

ELIGIBILITY_CONFIG = {
    'dcfc':   {'min_rating': 3.0, 'min_reviews': 10},
    'level2': {'min_rating': 2.5, 'min_reviews': 5},
}


# ============================================================================
# FUNCAO AUXILIAR PUBLICA
# ============================================================================

def get_peak_traffic(location: Dict) -> float:
    """
    Estima trafego de pico baseado no tipo e popularidade do local.
    Retorna valor entre 0-10.
    Usada externamente pelo app.py.
    """
    tipo = str(location.get('type', '')).lower()
    rating = float(location.get('rating', 3.5))
    reviews = int(location.get('user_ratings_total', location.get('reviews', 0)))

    base = {
        'shopping_mall': 8.5,
        'shopping':      8.5,
        'hotel':         6.5,
        'parking':       7.0,
        'supermarket':   7.5,
        'gas_station':   6.0,
        'restaurant':    5.5,
    }.get(tipo, 5.0)

    if reviews > 500:
        pop_boost = 1.0
    elif reviews > 200:
        pop_boost = 0.6
    elif reviews > 50:
        pop_boost = 0.3
    else:
        pop_boost = 0.0

    rating_factor = max(0.0, (rating - 3.0) * 0.2)

    return round(min(10.0, base + pop_boost + rating_factor), 2)


# ============================================================================
# LOCATION SCORER
# ============================================================================

class LocationScorer:
    """
    Calcula score de viabilidade para instalacao de carregadores EV.

    Parametros:
        mode  : 'dcfc' ou 'level2'
        alpha : fator de boost para locais de alta confianca (default 1.5)

    Uso:
        scorer = LocationScorer(mode='dcfc', alpha=1.5)
        eligible, reason = scorer.eligibility_gate(location)
        result = scorer.calculate_final_score(location, traffic, chargers, census_data)
    """

    def __init__(self, mode: str = 'dcfc', alpha: float = 1.5):
        self.mode = mode.lower() if mode.lower() in ('dcfc', 'level2') else 'dcfc'
        self.alpha = alpha
        self.weights = SCORE_WEIGHTS[self.mode]
        self.eligibility = ELIGIBILITY_CONFIG[self.mode]

    # ------------------------------------------------------------------
    # ELIGIBILITY GATE
    # ------------------------------------------------------------------

    def eligibility_gate(self, location: Dict) -> Tuple[bool, str]:
        """
        Verifica se o local passa nos criterios minimos.

        Retorna:
            (True, 'eligible')          se passar
            (False, 'motivo da rejeicao') se falhar
        """
        rating  = float(location.get('rating', 0) or 0)
        reviews = int(location.get('user_ratings_total',
                      location.get('reviews', 0)) or 0)
        name    = location.get('name', 'Unknown')

        # Se nao tem rating (Google nao retornou), deixa passar com aviso
        if rating > 0 and rating < self.eligibility['min_rating']:
            return False, f"Rating {rating} abaixo do minimo {self.eligibility['min_rating']}"

        # Se nao tem reviews (Google nao retornou), deixa passar
        if reviews > 0 and reviews < self.eligibility['min_reviews']:
            return False, f"Reviews {reviews} abaixo do minimo {self.eligibility['min_reviews']}"

        return True, 'eligible'

    # ------------------------------------------------------------------
    # SUB-SCORES
    # ------------------------------------------------------------------

    def _demand_score(self, location: Dict, traffic: Any) -> float:
        tipo   = str(location.get('type', '')).lower()
        base   = TYPE_BASE_SCORES.get(tipo, DEFAULT_BASE_SCORES)['demand']
        rating = float(location.get('rating', 3.5) or 3.5)
        reviews = int(location.get('user_ratings_total',
                      location.get('reviews', 0)) or 0)

        # Ajuste por rating (acima de 4.0 boost, abaixo penaliza)
        rating_adj = (rating - 4.0) * 0.4

        # Boost por volume de reviews
        if reviews > 1000:
            rev_boost = 1.5
        elif reviews > 500:
            rev_boost = 1.0
        elif reviews > 200:
            rev_boost = 0.6
        elif reviews > 50:
            rev_boost = 0.3
        else:
            rev_boost = 0.0

        # Trafego
        if isinstance(traffic, dict):
            congestion = float(traffic.get('congestion_ratio', 0.5))
            traffic_adj = (congestion - 0.5) * 1.5
        elif isinstance(traffic, (int, float)):
            traffic_adj = float(traffic) * 0.1
        else:
            traffic_adj = 0.0

        score = base + rating_adj + rev_boost + traffic_adj
        return round(min(10.0, max(0.0, score)), 1)

    def _competition_score(self, chargers: List) -> Tuple[float, Optional[Dict]]:
        """
        Score de competicao: sem concorrencia = 10, muita = baixo.
        Retorna (score, nearest_competitor_dict_ou_None)
        """
        if not chargers:
            return 10.0, None

        # Ordenar por distancia
        sorted_chargers = sorted(chargers, key=lambda c: float(c.get('distance_miles', 99)))
        nearest = sorted_chargers[0]
        dist = float(nearest.get('distance_miles', 1.0))
        n    = len(chargers)

        if n == 0:
            score = 10.0
        elif dist > 2.0:
            score = 9.5
        elif dist > 1.0:
            score = 8.5
        elif dist > 0.5:
            score = 7.0
        elif dist > 0.2:
            score = 5.5
        else:
            score = 4.0

        # Penalidade adicional por volume
        score = max(1.0, score - (n - 1) * 0.4)

        nearest_info = {
            'type':    nearest.get('type', 'Level 2'),
            'network': nearest.get('network', 'Unknown'),
            'distance_miles': round(dist, 1)
        }

        return round(score, 1), nearest_info

    def _site_fit_score(self, location: Dict) -> float:
        tipo = str(location.get('type', '')).lower()
        base = TYPE_BASE_SCORES.get(tipo, DEFAULT_BASE_SCORES)['site_fit']

        # Penalizar se ha indicacao de fechamento cedo
        opening_hours = location.get('opening_hours', {})
        if isinstance(opening_hours, dict):
            periods = opening_hours.get('periods', [])
            for period in periods:
                close_time = str(period.get('close', {}).get('time', '2300'))
                try:
                    if int(close_time) < 2200:
                        base -= 1.0
                        break
                except (ValueError, TypeError):
                    pass

        return round(min(10.0, max(0.0, base)), 1)

    def _ev_affinity_score(self, location: Dict, census_data: Dict) -> float:
        tipo = str(location.get('type', '')).lower()
        base = TYPE_BASE_SCORES.get(tipo, DEFAULT_BASE_SCORES)['ev_affinity']

        median_income = int(census_data.get('median_income', 75000) or 75000)

        if median_income > 120000:
            income_boost = 2.0
        elif median_income > 90000:
            income_boost = 1.2
        elif median_income > 75000:
            income_boost = 0.7
        elif median_income > 60000:
            income_boost = 0.3
        else:
            income_boost = 0.0

        score = base + income_boost
        return round(min(10.0, max(0.0, score)), 1)

    # ------------------------------------------------------------------
    # CONFIDENCE
    # ------------------------------------------------------------------

    def _compute_confidence(self, location: Dict, chargers: List, census_data: Dict) -> float:
        score = 0.0
        total = 0.0

        # Rating disponivel?
        rating = float(location.get('rating', 0) or 0)
        if rating > 0:
            score += 0.3
        total += 0.3

        # Reviews disponiveis?
        reviews = int(location.get('user_ratings_total', location.get('reviews', 0)) or 0)
        if reviews > 20:
            score += 0.25
        elif reviews > 0:
            score += 0.15
        total += 0.25

        # Dados de carregadores proximos?
        if chargers is not None:
            score += 0.25
        total += 0.25

        # Dados demograficos?
        if census_data and census_data.get('median_income', 0) > 0:
            score += 0.2
        total += 0.2

        confidence = score / total if total > 0 else 0.5
        return round(min(1.0, confidence), 2)

    # ------------------------------------------------------------------
    # STRENGTHS & RISKS
    # ------------------------------------------------------------------

    def _get_potential(self, score: float) -> str:
        for label, threshold in POTENTIAL_THRESHOLDS.items():
            if score >= threshold:
                return label
        return 'LOW'

    def _get_strengths(self, scores: Dict, chargers: List, location: Dict) -> List[str]:
        strengths = []

        if scores['competition'] >= 9.5:
            strengths.append("Sem concorrencia direta - zona de monopolio")
        elif scores['competition'] >= 8.0:
            strengths.append("Baixa concorrencia na area")

        if scores['demand'] >= 8.0:
            strengths.append("Alto fluxo de trafego no horario de pico")
        elif scores['demand'] >= 7.0:
            strengths.append("Fluxo de trafego consistente")

        if scores['site_fit'] >= 9.5:
            strengths.append("Site ideal para instalacao de carregador")
        elif scores['site_fit'] >= 8.0:
            strengths.append("Boa adequacao do site")

        if scores['ev_affinity'] >= 8.5:
            strengths.append("Alta afinidade EV na regiao - renda elevada")
        elif scores['ev_affinity'] >= 7.5:
            strengths.append("Boa afinidade EV na regiao")

        return strengths

    def _get_risks(self, scores: Dict, location: Dict) -> List[str]:
        risks = []

        opening_hours = location.get('opening_hours', {})
        if isinstance(opening_hours, dict):
            periods = opening_hours.get('periods', [])
            for period in periods:
                close_time = str(period.get('close', {}).get('time', '2300'))
                try:
                    if int(close_time) < 2200:
                        risks.append("Fecha antes das 22h - limita uso noturno")
                        break
                except (ValueError, TypeError):
                    pass

        if scores['competition'] < 5.0:
            risks.append("Alta concorrencia com carregadores existentes")

        if scores['demand'] < 5.0:
            risks.append("Baixo fluxo de trafego estimado")

        if scores['ev_affinity'] < 5.5:
            risks.append("Baixa penetracao EV na regiao")

        return risks

    # ------------------------------------------------------------------
    # CALCULATE FINAL SCORE (metodo principal)
    # ------------------------------------------------------------------

    def calculate_final_score(
        self,
        location: Dict,
        traffic: Any = None,
        chargers: Optional[List] = None,
        census_data: Optional[Dict] = None,
        nearby_anchors: Optional[List] = None
    ) -> Dict:
        """
        Calcula o score final de viabilidade do local.

        Retorna dict com:
            final_score, confidence, potential, breakdown,
            strengths, risks, flags, nearest_competitor
        """
        if chargers is None:
            chargers = []
        if census_data is None:
            census_data = {}

        # Sub-scores
        demand_s      = self._demand_score(location, traffic)
        competition_s, nearest_competitor = self._competition_score(chargers)
        site_fit_s    = self._site_fit_score(location)
        ev_affinity_s = self._ev_affinity_score(location, census_data)

        breakdown = {
            'demand':      demand_s,
            'competition': competition_s,
            'site_fit':    site_fit_s,
            'ev_affinity': ev_affinity_s,
        }

        # Weighted average
        w = self.weights
        final_score = (
            demand_s      * w['demand']      +
            competition_s * w['competition'] +
            site_fit_s    * w['site_fit']    +
            ev_affinity_s * w['ev_affinity']
        )
        final_score = round(min(10.0, max(0.0, final_score)), 1)

        # Confidence
        confidence = self._compute_confidence(location, chargers, census_data)

        # Boost por alta confianca
        if confidence >= 0.9 and final_score >= 7.0:
            final_score = round(min(10.0, final_score * (1 + (self.alpha - 1) * 0.05)), 1)

        potential  = self._get_potential(final_score)
        strengths  = self._get_strengths(breakdown, chargers, location)
        risks      = self._get_risks(breakdown, location)

        # Flags
        flags = []
        if competition_s >= 9.5:
            flags.append('MONOPOLY_ZONE')
        if demand_s >= 8.5:
            flags.append('HIGH_TRAFFIC')
        if final_score >= 8.5:
            flags.append('PRIORITY_TARGET')
        if confidence < 0.5:
            flags.append('LOW_DATA_CONFIDENCE')

        return {
            'final_score':        final_score,
            'confidence':         confidence,
            'potential':          potential,
            'breakdown':          breakdown,
            'strengths':          strengths,
            'risks':              risks,
            'flags':              flags,
            'nearest_competitor': nearest_competitor,
            'mode':               self.mode,
        }
