"""
correcoes/correcao_2_confidence_ranking.py
===========================================
CORRECAO 2: Ranking com Confidence Weighting.

Ajusta o score final ponderando pela confianca dos dados.
Locais com poucos dados nao devem competir igualmente com
locais que tem dados ricos.
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def calcular_score_final(score_bruto: float, confidence: float) -> float:
    """
    Ajusta o score final com base na confianca dos dados.

    Formula:
        score_final = score_bruto * (0.7 + 0.3 * confidence)

    Exemplos:
        score=9.0, confidence=1.0 -> 9.0  (sem penalidade)
        score=9.0, confidence=0.5 -> 8.55 (penalidade leve)
        score=9.0, confidence=0.0 -> 6.3  (penalidade alta)

    Parametros:
        score_bruto : score calculado (0-10)
        confidence  : confianca dos dados (0.0 a 1.0)

    Retorna:
        score ajustado (0-10)
    """
    confidence = max(0.0, min(1.0, float(confidence)))
    fator = 0.7 + (0.3 * confidence)
    score_ajustado = round(score_bruto * fator, 2)
    logger.debug(f"Confidence weighting: {score_bruto} * {fator:.2f} = {score_ajustado}")
    return round(min(10.0, max(0.0, score_ajustado)), 2)


class RankingComConfianca:
    """
    Ordena lista de locais usando score ponderado por confianca.

    Uso:
        ranking = RankingComConfianca()
        locais_ordenados = ranking.ranking_final(locais_scored)
    """

    def __init__(self, peso_score: float = 0.75, peso_confidence: float = 0.25):
        """
        Parametros:
            peso_score      : peso do score puro no ranking (default 0.75)
            peso_confidence : peso da confianca no ranking (default 0.25)
        """
        self.peso_score      = peso_score
        self.peso_confidence = peso_confidence

    def _score_composto(self, local: Dict) -> float:
        """Calcula score composto para ordenacao."""
        score = float(local.get('score_final', local.get('score', 0)) or 0)

        # Tentar extrair confidence de diferentes estruturas
        confidence = float(local.get('confidence', 0) or 0)
        if confidence == 0:
            dcfc = local.get('dcfc', {})
            if isinstance(dcfc, dict):
                confidence = float(dcfc.get('confidence', 0) or 0)

        score_composto = (score * self.peso_score) + (confidence * 10 * self.peso_confidence)
        return round(score_composto, 4)

    def ranking_final(self, locais: List[Dict]) -> List[Dict]:
        """
        Ordena locais por score composto (score + confidence).

        Parametros:
            locais : lista de dicts com 'score'/'score_final' e 'confidence'

        Retorna:
            lista ordenada do maior para o menor score composto
        """
        if not locais:
            return []

        locais_com_score = []
        for local in locais:
            score_c = self._score_composto(local)
            locais_com_score.append({**local, '_score_composto': score_c})

        ordenados = sorted(locais_com_score, key=lambda x: x['_score_composto'], reverse=True)

        # Remover campo interno antes de retornar
        for local in ordenados:
            local.pop('_score_composto', None)

        logger.debug(f"Ranking finalizado: {len(ordenados)} locais")
        return ordenados
