"""
correcoes/correcao_1_penalidade_dinamica.py
============================================
CORRECAO 1: Sistema de Score Adaptativo com Penalidades Dinamicas.

Aplica penalidades baseadas no contexto geografico real do local,
ao inves de penalidades fixas por tipo de estabelecimento.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SistemaDeScoreAdaptativo:
    """
    Aplica penalidades e bonificacoes dinamicas ao score de um local
    baseado em contexto geografico, demografico e competitivo.

    Uso:
        sistema = SistemaDeScoreAdaptativo()
        score_ajustado = sistema.aplicar(score_bruto, contexto)
    """

    # Penalidades por contexto (em pontos, subtraidos do score 0-10)
    PENALIDADES = {
        'alta_concorrencia':    2.0,
        'baixa_renda':          1.0,
        'area_industrial':      1.5,
        'acesso_restrito':      2.0,
        'zona_residencial':     0.8,
        'fechamento_cedo':      1.2,
        'sem_estacionamento':   1.8,
    }

    # Bonificacoes por contexto
    BONIFICACOES = {
        'monopolio_area':       2.0,
        'alta_renda':           1.5,
        'corredor_comercial':   1.2,
        'ponto_turistico':      1.0,
        'acesso_rodovia':       0.8,
        'estacionamento_amplo': 1.0,
    }

    def __init__(self):
        self.penalidades_aplicadas  = []
        self.bonificacoes_aplicadas = []

    def aplicar(self, score_bruto: float, contexto_geografico: Dict) -> float:
        """
        Aplica penalidades e bonificacoes dinamicas ao score.

        Parametros:
            score_bruto          : score original (0-10)
            contexto_geografico  : dict com flags do contexto

        Retorna:
            score ajustado (0-10)
        """
        self.penalidades_aplicadas  = []
        self.bonificacoes_aplicadas = []
        score = score_bruto

        # Aplicar penalidades
        for flag, valor in self.PENALIDADES.items():
            if contexto_geografico.get(flag, False):
                score -= valor
                self.penalidades_aplicadas.append({'flag': flag, 'valor': -valor})
                logger.debug(f"Penalidade aplicada: {flag} (-{valor})")

        # Aplicar bonificacoes
        for flag, valor in self.BONIFICACOES.items():
            if contexto_geografico.get(flag, False):
                score += valor
                self.bonificacoes_aplicadas.append({'flag': flag, 'valor': valor})
                logger.debug(f"Bonificacao aplicada: {flag} (+{valor})")

        score_final = round(max(0.0, min(10.0, score)), 2)
        logger.debug(f"Score: {score_bruto} -> {score_final}")
        return score_final

    def relatorio(self) -> Dict:
        """Retorna relatorio das penalidades e bonificacoes aplicadas."""
        total_penalidades  = sum(p['valor'] for p in self.penalidades_aplicadas)
        total_bonificacoes = sum(b['valor'] for b in self.bonificacoes_aplicadas)
        return {
            'penalidades':        self.penalidades_aplicadas,
            'bonificacoes':       self.bonificacoes_aplicadas,
            'total_penalidades':  total_penalidades,
            'total_bonificacoes': total_bonificacoes,
            'ajuste_liquido':     total_bonificacoes + total_penalidades,
        }

    def inferir_contexto(self, location: Dict, chargers: list, census_data: Dict) -> Dict:
        """
        Infere flags de contexto automaticamente a partir dos dados disponiveis.
        Util quando nao ha contexto explicito disponivel.
        """
        contexto = {}

        # Alta concorrencia
        if len(chargers) >= 4:
            contexto['alta_concorrencia'] = True

        # Monopolio (sem concorrencia)
        if len(chargers) == 0:
            contexto['monopolio_area'] = True

        # Renda
        median_income = census_data.get('median_income', 75000)
        if median_income > 100000:
            contexto['alta_renda'] = True
        elif median_income < 50000:
            contexto['baixa_renda'] = True

        # Fechamento cedo
        opening_hours = location.get('opening_hours', {})
        if isinstance(opening_hours, dict):
            periods = opening_hours.get('periods', [])
            for period in periods:
                close_time = str(period.get('close', {}).get('time', '2300'))
                try:
                    if int(close_time) < 2100:
                        contexto['fechamento_cedo'] = True
                        break
                except (ValueError, TypeError):
                    pass

        return contexto
