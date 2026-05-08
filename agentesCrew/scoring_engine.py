"""
BuscaEV - Scoring Engine V2.1 RELAXADO
=======================================
Motor de scoring para identificacao de locais ideais
para instalacao de carregadores eletricos em Massachusetts.

VERSAO RELAXADA: Filtros menos rigorosos para permitir mais resultados.

Arquitetura:
    - Eligibility Gate (passa/nao passa) - RELAXADO
    - 4 Motores Estrategicos: Demand, Competition, Site Fit, EV Affinity
    - Confidence ponderado pelos pesos dos motores
    - Output enriquecido com breakdown + flags

Autores: Desenvolvido com debate Claude + GPT + DeepSeek
Versao: 2.1 RELAXADO
Data: Fevereiro 2026
"""

import math
from typing import Optional


# CONFIGURACAO DE PESOS POR MODO

WEIGHTS = {
    'dcfc': {
        'demand':      0.35,
        'competition': 0.30,
        'site_fit':    0.20,
        'ev_affinity': 0.15,
    },
    'level2': {
        'demand':      0.25,
        'competition': 0.20,
        'site_fit':    0.35,
        'ev_affinity': 0.20,
    }
}

# Tempo medio de permanencia por tipo de local (em horas)
# Fonte: estimativa de mercado EV
DWELL_MULTIPLIERS = {
    'hotel':           2.0,   # 8-12h
    'movie_theater':   1.5,   # 2-3h
    'shopping_mall':   1.3,   # 1-3h
    'gym':             1.2,   # 1-2h
    'parking':         1.5,   # variavel
    'supermarket':     0.8,   # 30-45min
    'grocery_store':   0.8,
    'restaurant':      0.7,   # ~1h
    'fast_food':       0.5,
    'gas_station':     0.5,
    'cafe':            0.9,
    'hospital':        1.8,   # longas esperas
    'airport':         2.0,
}

# Ancoras EV-friendly (proxy de perfil de publico)
EV_ANCHOR_KEYWORDS = [
    'Whole Foods', "Trader Joe's", 'Apple Store',
    'Tesla', 'REI', 'Lululemon', 'Equinox'
]


# CLASSE PRINCIPAL

class LocationScorer:
    """
    Motor de scoring para avaliacao de locais para
    instalacao de carregadores EV.

    Args:
        mode (str): 'dcfc' para DC Fast Charger ou 'level2' para Level 2.
        alpha (float): Fator de escala do Competition Score.
                       Comecar com 1.5 e calibrar com dados reais.
    """

    def __init__(self, mode: str = 'dcfc', alpha: float = 1.5):
        if mode not in ('dcfc', 'level2'):
            raise ValueError("mode deve ser 'dcfc' ou 'level2'")

        self.mode = mode
        self.alpha = alpha
        self.weights = WEIGHTS[mode]

        # Decay constant da distancia por modo
        # DCFC: influencia cai mais devagar (raio maior)
        # L2: influencia cai mais rapido (raio menor)
        self.d0 = 0.7 if mode == 'dcfc' else 0.4

    # 1. ELIGIBILITY GATE - VERSAO RELAXADA

    def eligibility_gate(self, location: dict) -> tuple[bool, str]:
        """
        Avalia se o local passa para o ranking ou e eliminado.
        
        VERSAO RELAXADA: Muito menos restritiva para permitir mais resultados
        durante testes e prototipagem.

        Returns:
            (bool, str): (elegivel, motivo)
        """
        rating = location.get('rating', 0)
        reviews = location.get('user_ratings_total', 0)
        types = location.get('types', [])
        hours = location.get('opening_hours', {})

        # Hard reject: rating EXTREMAMENTE baixo (relaxado: 2.0 em vez de 3.3)
        # E com MUITOS reviews (100+) para confirmar que e realmente ruim
        if rating <= 2.0 and reviews >= 100:
            return False, "hard_reject: rating extremamente baixo com muitos reviews"

        # REMOVIDO: rejeicao por tipo de local sem estacionamento
        # (agora aceitamos shopping_mall, restaurants, etc)

        # REMOVIDO: rejeicao por horario de fechamento cedo
        # (agora aceitamos qualquer horario de operacao)

        # Praticamente tudo passa agora
        return True, "eligible"

    # 2. CONFIDENCE MULTIPLIER

    def confidence_multiplier(self, reviews: int) -> float:
        """
        Penaliza locais com poucos dados para evitar
        que 'dark horses' sem reviews subam indevidamente.
        
        VERSAO RELAXADA: menos agressiva
        """
        if reviews < 10:
            return 0.65   # dado muito insuficiente
        elif reviews < 30:
            return 0.80   # dado parcial
        elif reviews < 50:
            return 0.90   # dado razoavel
        return 1.0       # dado confiavel

    # 3. DEMAND SCORE

    def demand_score(self, traffic: dict) -> tuple[float, float]:
        """
        Avalia o fluxo de trafego no local.

        O traffic deve conter dados do horario de PICO (17-19h),
        nao tempo real. Use get_peak_traffic() para isso.

        Args:
            traffic: {
                'congestion_ratio': float (0-1),  # 0=livre, 1=parado
                'road_type': str,                 # 'highway'|'arterial'|'local'
                'confidence': float               # opcional, 0-1
            }

        Returns:
            (score 0-10, confidence 0-1)
        """
        # Fallback se dados ausentes
        if 'congestion_ratio' not in traffic or traffic['congestion_ratio'] is None:
            # Fallback neutro com confianca media
            return 5.0, 0.6

        congestion = traffic['congestion_ratio']
        conf = traffic.get('confidence', 1.0)

        # Sigmoide: ponto de inflexao em 35% de congestionamento
        # Abaixo de 20%: score cresce devagar (via tranquila)
        # Entre 30-50%: score acelera (movimento real)
        # Acima de 60%: satura (transito intenso)
        k, x0 = 12, 0.35
        score = 10 / (1 + math.exp(-k * (congestion - x0)))

        # Ajuste por tipo de via
        road_multiplier = {
            'highway':  1.3,
            'arterial': 1.0,
            'local':    0.7
        }.get(traffic.get('road_type', 'arterial'), 1.0)

        score = min(score * road_multiplier, 10.0)
        return round(score, 2), conf

    # 4. COMPETITION SCORE

    def competition_score(self, chargers: list) -> tuple[float, float]:
        """
        Avalia a concorrencia de carregadores existentes.

        Usa kernel exponencial: concorrente proximo penaliza muito,
        concorrente distante penaliza pouco (decaimento natural).

        Args:
            chargers: lista de {
                'type': str,           # 'DCFC' ou 'Level 2'
                'distance_miles': float,
                'network': str         # opcional
            }

        Returns:
            (score 0-10, confidence)
        """
        if not chargers:
            return 10.0, 1.0   # monopolio - maximo score

        penalty = 0.0
        for c in chargers:
            # DCFC pesa 2x mais que Level 2
            type_weight = 2.0 if 'DCFC' in c.get('type', '') else 1.0

            # Decaimento exponencial por distancia
            dist = c.get('distance_miles', 0)
            dist_factor = math.exp(-dist / self.d0)

            penalty += type_weight * dist_factor

        # Alpha configuravel - calibrar com dados reais
        score = max(10.0 - (penalty * self.alpha), 1.0)
        return round(score, 2), 1.0

    # 5. SITE FIT SCORE

    def site_fit_score(self, location: dict) -> tuple[float, float]:
        """
        Avalia se o local e adequado para carregadores.

        Leva em conta:
        - Tipo de local (dwell time)
        - Preco do local (indicador de qualidade)
        - Horarios de funcionamento
        - Numero de fotos (indicador de investimento)

        Returns:
            (score 0-10, confidence 0-1)
        """
        score_components = []
        conf = 1.0

        # Componente 1: Dwell multiplier (quanto tempo fica no local?)
        local_type = location.get('type', 'shopping_mall')
        dwell = DWELL_MULTIPLIERS.get(local_type, 1.0)
        dwell_score = min((dwell / 2.0) * 10, 10.0)
        score_components.append(dwell_score * 0.4)

        # Componente 2: Price level (mais caro = mais qualidade?)
        price_level = location.get('preco_nivel', 0)
        if price_level > 0:
            price_score = min((price_level / 4.0) * 10, 10.0)
        else:
            price_score = 5.5  # Relaxado: 5.0 → 5.5
            conf = 0.75  # Relaxado: 0.7 → 0.75
        score_components.append(price_score * 0.3)

        # Componente 3: Fotos (investimento na apresentacao)
        photos = location.get('fotos', 0)
        photo_score = min((photos / 10.0) * 10, 10.0) if photos > 0 else 5.0  # Relaxado: 4.0 → 5.0
        if photos == 0:
            conf = min(conf, 0.85)  # Relaxado: 0.8 → 0.85
        score_components.append(photo_score * 0.3)

        final_score = sum(score_components)
        return round(min(final_score, 10.0), 2), conf

    # 6. EV AFFINITY SCORE

    def ev_affinity_score(self, location: dict, census_data: dict = None) -> tuple[float, float]:
        """
        Avalia se o local atrai publico amigavel a EVs.

        Proxies:
        - Nome da loja (Whole Foods, Apple, Tesla = high affinity)
        - Renda mediana (> 75k = mais EVs)
        - Rating alto (clientes exigentes = EVs)

        Returns:
            (score 0-10, confidence 0-1)
        """
        score_components = []

        # Componente 1: Keywords EV-friendly no nome
        name = location.get('name', '').lower()
        has_anchor = any(kw.lower() in name for kw in EV_ANCHOR_KEYWORDS)
        anchor_score = 9.0 if has_anchor else 5.5  # Relaxado: 5.0 → 5.5
        score_components.append(anchor_score * 0.4)

        # Componente 2: Rating (clientes exigentes)
        rating = location.get('rating', 3.5)
        rating_score = (rating / 5.0) * 10
        score_components.append(rating_score * 0.35)

        # Componente 3: Renda mediana (se disponivel)
        if census_data:
            median_income = census_data.get('median_income', 75000)
            income_score = min((median_income / 100000.0) * 10, 10.0)
            score_components.append(income_score * 0.25)
        else:
            score_components.append(5.5 * 0.25)  # Relaxado: 5.0 → 5.5

        final_score = sum(score_components)
        return round(min(final_score, 10.0), 2), 1.0

    # CALCULATE FINAL SCORE

    def calculate_final_score(
        self,
        location: dict,
        traffic: dict,
        chargers: list,
        census_data: dict = None,
        nearby_anchors: list = None
    ) -> dict:
        """
        Calcula o score final ponderado com breakdown.

        Args:
            location: dados do local (Google Places)
            traffic: dados de trafego (TomTom)
            chargers: lista de carregadores proximos (NREL)
            census_data: dados demograficos (Census)
            nearby_anchors: lojas EV-friendly proximas (opcional)

        Returns:
            dict com score final, breakdown, flags, strengths, risks
        """
        # ── Calcular os 4 motores ──
        demand, demand_conf = self.demand_score(traffic)
        competition, comp_conf = self.competition_score(chargers)
        site_fit, site_conf = self.site_fit_score(location)
        ev_affinity, ev_conf = self.ev_affinity_score(location, census_data)

        # ── Confidence multiplier por reviews ──
        review_conf = self.confidence_multiplier(location.get('user_ratings_total', 0))

        # ── Score final ponderado ──
        final = (
            demand * self.weights['demand'] +
            competition * self.weights['competition'] +
            site_fit * self.weights['site_fit'] +
            ev_affinity * self.weights['ev_affinity']
        )

        # ── Confidence total @@
        total_confidence = (
            (demand_conf + comp_conf + site_conf + ev_conf) / 4.0
        ) * review_conf

        # ── Gerar flags automaticas @@
        flags, strengths, risks = self._generate_flags(
            location, traffic, chargers, demand, competition, site_fit
        )

        return {
            'name':          location.get('name', 'Desconhecido'),
            'mode':          self.mode.upper(),
            'final_score':   round(final, 1),
            'confidence':    round(total_confidence, 2),
            'potential':     self._get_potential_label(final),
            'breakdown': {
                'demand':      round(demand, 1),
                'competition': round(competition, 1),
                'site_fit':    round(site_fit, 1),
                'ev_affinity': round(ev_affinity, 1),
            },
            'strengths': strengths,
            'risks':     risks,
            'flags':     flags,
            'nearest_competitor': self._get_nearest(chargers),
        }

    # HELPERS PRIVADOS

    def _get_potential_label(self, score: float) -> str:
        if score >= 8.0:   return "VERY_HIGH"
        elif score >= 6.5: return "HIGH"
        elif score >= 5.0: return "MEDIUM"
        elif score >= 3.5: return "LOW"
        else:              return "VERY_LOW"

    def _is_24_7(self, hours: dict) -> bool:
        """Verifica se o local funciona 24h/7 dias."""
        periods = hours.get('periods', [])
        for period in periods:
            if period.get('open', {}).get('time') == '0000' and 'close' not in period:
                return True
        return False

    def _get_closing_hour(self, hours: dict) -> Optional[int]:
        """Retorna hora de fechamento (int) ou None se nao disponivel."""
        periods = hours.get('periods', [])
        for period in periods:
            close = period.get('close', {})
            time_str = close.get('time', '')
            if time_str:
                try:
                    return int(time_str[:2])
                except ValueError:
                    pass
        return None

    def _get_nearest(self, chargers: list) -> Optional[dict]:
        """Retorna o carregador mais proximo da lista."""
        if not chargers:
            return None
        nearest = min(chargers, key=lambda c: c.get('distance_miles', 999))
        return {
            'type':           nearest.get('type', 'Unknown'),
            'distance_miles': round(nearest.get('distance_miles', 0), 2),
            'network':        nearest.get('network', 'Unknown'),
        }

    def _generate_flags(
        self,
        location: dict,
        traffic: dict,
        chargers: list,
        demand: float,
        competition: float,
        site_fit: float
    ) -> tuple[list, list, list]:
        """Gera flags, pontos fortes e riscos automaticamente."""
        flags     = []
        strengths = []
        risks     = []

        # Flags de forca
        if competition >= 9.0:
            flags.append('monopoly_zone')
            strengths.append('Sem concorrencia direta - zona de monopolio')

        if demand >= 7.5:
            flags.append('high_traffic')
            strengths.append('Alto fluxo de trafego no horario de pico')

        if self._is_24_7(location.get('opening_hours', {})):
            flags.append('24_7')
            strengths.append('Funcionamento 24h - ideal para DCFC noturno')

        # Flags de risco
        closing = self._get_closing_hour(location.get('opening_hours', {}))
        if closing and closing < 22:
            flags.append('closes_early')
            risks.append(f'Fecha as {closing}h - limita uso noturno')

        if traffic.get('confidence', 1.0) < 0.7:
            flags.append('traffic_unreliable')
            risks.append('Dados de trafego com baixa confianca')

        if location.get('user_ratings_total', 0) < 15:
            flags.append('low_data')
            risks.append('Poucos reviews - dados insuficientes para analise confiavel')

        any_dcfc_near = any('DCFC' in c.get('type', '') for c in chargers)
        if any_dcfc_near:
            flags.append('dcfc_competitor_nearby')
            risks.append('Concorrente DCFC na area - impacto no ROI')

        return flags, strengths, risks


# FUNCAO AUXILIAR: DADOS DE TRAFEGO DE PICO

def get_peak_traffic(lat: float, lng: float, tomtom_fn) -> dict:
    """
    Coleta dados de trafego nos horarios de pico e retorna
    uma media ponderada - evita o bug de chamar em tempo real.

    Args:
        lat, lng: coordenadas do local
        tomtom_fn: funcao que chama a TomTom API
                   Signature: (lat, lng, hour) -> {'congestion_ratio': float, 'road_type': str}

    Returns:
        dict com congestion_ratio medio ponderado e road_type

    Horarios e pesos:
        08h (manha)   - 25%
        17h (pico)    - 50%   <- maior peso: quando EVs carregariam
        19h (saida)   - 25%
    """
    peak_schedule = {8: 0.25, 17: 0.50, 19: 0.25}

    weighted_congestion = 0.0
    road_type = 'arterial'  # fallback
    successful_calls = 0

    for hour, weight in peak_schedule.items():
        try:
            data = tomtom_fn(lat, lng, hour)
            if data and 'congestion_ratio' in data:
                weighted_congestion += data['congestion_ratio'] * weight
                road_type = data.get('road_type', road_type)
                successful_calls += 1
        except Exception:
            # Se uma chamada falhar, ignora e redistribui peso implicitamente
            pass

    if successful_calls == 0:
        return {'congestion_ratio': None, 'road_type': road_type, 'confidence': 0.0}

    confidence = successful_calls / len(peak_schedule)
    return {
        'congestion_ratio': round(weighted_congestion, 3),
        'road_type':        road_type,
        'confidence':       round(confidence, 2)
    }


# EXEMPLO DE USO

if __name__ == '__main__':
    # Dados simulados - substituir por chamadas reais as APIs
    location_example = {
        'name': 'Meadow Glen Mall',
        'rating': 4.4,
        'user_ratings_total': 512,
        'types': ['shopping_mall', 'point_of_interest'],
        'opening_hours': {
            'open_now': True,
            'periods': [{'open': {'time': '1000'}, 'close': {'time': '2100'}}]
        },
        'fotos': 15,
        'preco_nivel': 2,
        'type': 'shopping_mall'
    }

    traffic_example = {
        'congestion_ratio': 0.52,   # 52% de congestionamento no pico
        'road_type': 'arterial',
        'confidence': 1.0
    }

    chargers_example = [
        {'type': 'Level 2', 'distance_miles': 1.2, 'network': 'ChargePoint'},
        {'type': 'Level 2', 'distance_miles': 2.1, 'network': 'Blink'},
    ]

    census_example = {
        'median_income': 82000,
        'density': 3200
    }

    # Modo DCFC
    scorer = LocationScorer(mode='dcfc', alpha=1.5)

    # Verificar elegibilidade
    eligible, reason = scorer.eligibility_gate(location_example)
    print(f"\nElegibilidade: {eligible} - {reason}")

    if eligible:
        result = scorer.calculate_final_score(
            location    = location_example,
            traffic     = traffic_example,
            chargers    = chargers_example,
            census_data = census_example,
            nearby_anchors = None
        )

        print(f"\n{'='*50}")
        print(f"  {result['name']} [{result['mode']}]")
        print(f"{'='*50}")
        print(f"  Score Final:  {result['final_score']} / 10")
        print(f"  Potencial:    {result['potential']}")
        print(f"  Confianca:    {result['confidence']}")
        print(f"\n  Breakdown:")
        for motor, score in result['breakdown'].items():
            print(f"    {motor:<15} {score}")
        print(f"\n  Pontos Fortes:")
        for s in result['strengths']:
            print(f"    [+] {s}")
        print(f"\n  Riscos:")
        for r in result['risks']:
            print(f"    [-] {r}")
        if result['nearest_competitor']:
            nc = result['nearest_competitor']
            print(f"\n  Concorrente mais proximo:")
            print(f"    {nc['type']} - {nc['distance_miles']}mi ({nc['network']})")
        print(f"{'='*50}\n")
