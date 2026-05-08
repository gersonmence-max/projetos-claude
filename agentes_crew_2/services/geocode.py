"""
services/geocode.py
===================
Geocoding com fallback automatico:
  1. LocationIQ
  2. OpenCage
  3. Nominatim (OpenStreetMap - sempre disponivel, sem key)

Nunca retorna 500. Se todas falharem, retorna (None, error_dict).
"""

import os
import logging
import time
from typing import Optional, Tuple, Dict

from services.http import fetch_json

logger = logging.getLogger(__name__)

LOCATIONIQ_API_KEY = os.getenv('LOCATIONIQ_API_KEY')
OPENCAGE_API_KEY   = os.getenv('OPENCAGE_API_KEY')


def geocode_cidade(cidade: str, debug: bool = False) -> Tuple[Optional[Tuple[float, float]], Optional[Dict]]:
    """
    Geocoding com fallback: LocationIQ -> OpenCage -> Nominatim

    Retorna:
        ((lat, lng), None)     em caso de sucesso
        (None, error_dict)     se todas as tentativas falharem
    """
    query = f"{cidade}, Massachusetts, USA"
    logger.info(f"Geocoding: {query}")

    # ------------------------------------------------------------------
    # Tentativa 1: LocationIQ
    # ------------------------------------------------------------------
    if LOCATIONIQ_API_KEY:
        url    = "https://api.locationiq.com/v1/search.json"
        params = {'key': LOCATIONIQ_API_KEY, 'q': query, 'format': 'json', 'limit': 1}
        data, error = fetch_json('LocationIQ', url, params=params, timeout=10, debug=debug)

        if error is None and isinstance(data, list) and len(data) > 0:
            try:
                lat = float(data[0]['lat'])
                lng = float(data[0]['lon'])
                logger.info(f"[LocationIQ] OK: {cidade} -> ({lat:.4f}, {lng:.4f})")
                return (lat, lng), None
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"[LocationIQ] Parse error: {e}")
        else:
            logger.warning(f"[LocationIQ] Falhou: {error.get('error') if error else 'sem dados'}")
    else:
        logger.debug("[LocationIQ] Key nao configurada, pulando")

    # ------------------------------------------------------------------
    # Tentativa 2: OpenCage
    # ------------------------------------------------------------------
    if OPENCAGE_API_KEY:
        url    = "https://api.opencagedata.com/geocode/v1/json"
        params = {'q': query, 'key': OPENCAGE_API_KEY, 'limit': 1, 'no_annotations': 1}
        data, error = fetch_json('OpenCage', url, params=params, timeout=10, debug=debug)

        if error is None and isinstance(data, dict):
            try:
                results = data.get('results', [])
                if results:
                    geo = results[0]['geometry']
                    lat = float(geo['lat'])
                    lng = float(geo['lng'])
                    logger.info(f"[OpenCage] OK: {cidade} -> ({lat:.4f}, {lng:.4f})")
                    return (lat, lng), None
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"[OpenCage] Parse error: {e}")
        else:
            logger.warning(f"[OpenCage] Falhou: {error.get('error') if error else 'sem dados'}")
    else:
        logger.debug("[OpenCage] Key nao configurada, pulando")

    # ------------------------------------------------------------------
    # Tentativa 3: Nominatim (OpenStreetMap) - sem key, sempre disponivel
    # ------------------------------------------------------------------
    time.sleep(1)  # Nominatim exige 1s entre requests
    url    = "https://nominatim.openstreetmap.org/search"
    params = {'q': query, 'format': 'json', 'limit': 1, 'countrycodes': 'us'}
    data, error = fetch_json('Nominatim', url, params=params, timeout=8, debug=debug)

    if error is None and isinstance(data, list) and len(data) > 0:
        try:
            lat = float(data[0]['lat'])
            lng = float(data[0]['lon'])
            logger.info(f"[Nominatim] OK: {cidade} -> ({lat:.4f}, {lng:.4f})")
            return (lat, lng), None
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"[Nominatim] Parse error: {e}")
    else:
        logger.warning(f"[Nominatim] Falhou: {error.get('error') if error else 'sem dados'}")

    # ------------------------------------------------------------------
    # Todas as tentativas falharam
    # ------------------------------------------------------------------
    logger.error(f"Geocoding falhou para: {cidade} (todas as APIs)")
    return None, {
        'error': f'Unable to geocode city: {cidade}',
        'details': 'LocationIQ, OpenCage and Nominatim all failed',
        'query': query
    }
