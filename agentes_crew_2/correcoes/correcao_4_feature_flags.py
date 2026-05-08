"""
correcoes/correcao_4_feature_flags.py
=======================================
CORRECAO 4: Feature Flags para controle em producao.

Permite ativar/desativar funcionalidades sem redeploy.
Configurado via arquivo JSON ou variaveis de ambiente.
"""

import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class FeatureFlags:
    """
    Controle de feature flags para o sistema EV Viability.

    Flags disponiveis:
        USE_DYNAMIC_PENALTIES    : ativa CORRECAO 1 (penalidades dinamicas)
        USE_CONFIDENCE_WEIGHTING : ativa CORRECAO 2 (confidence ranking)
        USE_NEW_TIMEOUT          : ativa CORRECAO 3 (timeout global 8s)
        USE_NEW_RANKING          : ativa CORRECAO 4 (ranking por confidence)
        USE_PDF_GENERATION       : ativa geracao de PDF
        USE_NOMINATIM_FALLBACK   : ativa fallback Nominatim no geocoding
        DEBUG_API_CALLS          : loga detalhes de cada chamada de API

    Uso:
        FeatureFlags.load_from_file('config/feature_flags.json')
        if FeatureFlags.USE_CONFIDENCE_WEIGHTING:
            score = calcular_score_final(score_bruto, confidence)
    """

    # Defaults (todos ON = sistema completo ativo)
    USE_DYNAMIC_PENALTIES    = True
    USE_CONFIDENCE_WEIGHTING = True
    USE_NEW_TIMEOUT          = True
    USE_NEW_RANKING          = True
    USE_PDF_GENERATION       = True
    USE_NOMINATIM_FALLBACK   = True
    DEBUG_API_CALLS          = False

    _loaded_from_file = False

    @classmethod
    def load_from_file(cls, path: str) -> None:
        """
        Carrega flags de um arquivo JSON.

        Formato esperado:
        {
            "USE_DYNAMIC_PENALTIES": true,
            "USE_CONFIDENCE_WEIGHTING": true,
            "USE_NEW_TIMEOUT": true,
            "USE_NEW_RANKING": true,
            "USE_PDF_GENERATION": true,
            "USE_NOMINATIM_FALLBACK": true,
            "DEBUG_API_CALLS": false
        }
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                flags = json.load(f)

            for key, value in flags.items():
                if hasattr(cls, key):
                    setattr(cls, key, bool(value))
                    logger.debug(f"Flag carregada: {key} = {value}")
                else:
                    logger.warning(f"Flag desconhecida ignorada: {key}")

            cls._loaded_from_file = True
            logger.info(f"Feature flags carregadas de: {path}")

        except FileNotFoundError:
            logger.warning(f"feature_flags.json nao encontrado em {path}. Usando defaults.")
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear feature_flags.json: {e}. Usando defaults.")
        except Exception as e:
            logger.error(f"Erro ao carregar feature flags: {e}. Usando defaults.")

    @classmethod
    def load_from_env(cls) -> None:
        """Carrega flags de variaveis de ambiente (prefixo FF_)."""
        mapping = {
            'FF_DYNAMIC_PENALTIES':    'USE_DYNAMIC_PENALTIES',
            'FF_CONFIDENCE_WEIGHTING': 'USE_CONFIDENCE_WEIGHTING',
            'FF_NEW_TIMEOUT':          'USE_NEW_TIMEOUT',
            'FF_NEW_RANKING':          'USE_NEW_RANKING',
            'FF_PDF_GENERATION':       'USE_PDF_GENERATION',
            'FF_NOMINATIM_FALLBACK':   'USE_NOMINATIM_FALLBACK',
            'FF_DEBUG_API_CALLS':      'DEBUG_API_CALLS',
        }
        for env_key, attr in mapping.items():
            val = os.getenv(env_key)
            if val is not None:
                setattr(cls, attr, val.lower() in ('1', 'true', 'yes', 'on'))

    @classmethod
    def get_all_flags(cls) -> Dict[str, bool]:
        """Retorna dict com todas as flags e seus valores atuais."""
        return {
            'USE_DYNAMIC_PENALTIES':    cls.USE_DYNAMIC_PENALTIES,
            'USE_CONFIDENCE_WEIGHTING': cls.USE_CONFIDENCE_WEIGHTING,
            'USE_NEW_TIMEOUT':          cls.USE_NEW_TIMEOUT,
            'USE_NEW_RANKING':          cls.USE_NEW_RANKING,
            'USE_PDF_GENERATION':       cls.USE_PDF_GENERATION,
            'USE_NOMINATIM_FALLBACK':   cls.USE_NOMINATIM_FALLBACK,
            'DEBUG_API_CALLS':          cls.DEBUG_API_CALLS,
            '_loaded_from_file':        cls._loaded_from_file,
        }

    @classmethod
    def status_report(cls) -> str:
        """Retorna string formatada com status de todas as flags."""
        lines = ["", "=" * 50, "FEATURE FLAGS STATUS", "=" * 50]
        for key, value in cls.get_all_flags().items():
            if key.startswith('_'):
                continue
            status = "ON " if value else "OFF"
            lines.append(f"  [{status}] {key}")
        lines.append("=" * 50)
        return "\n".join(lines)
