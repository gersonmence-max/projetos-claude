"""
services/geocode.py
===================
Geocoding com fallback automático.
Tenta: LocationIQ → OpenCage → Nominatim
Nunca retorna 500.
"""

import os
import logging
from typing import Tuple, Optional, Dict, Any
from services.http import fetch_json

logger = logging.getLogger(__name__)

# Chaves de API (variáveis de ambiente)
LOCATIONIQ_API_KEY = os.getenv('LOCATIONIQ_API_KEY')
OPENCAGE_API_KEY = os.getenv('OPENCAGE_API_KEY')
DEBUG = os.getenv('DEBUG', '0') == '1'


def geocode_cidade(cidade: str, estado: str = 'Massachusetts') -> Tuple[Optional[Tuple[float, float]], Optional[Dict]]:
    """
    Geocodifica uma cidade com fallback automático.
    
    Tentativa 1: LocationIQ (se LOCATIONIQ_API_KEY existir)
    Tentativa 2: OpenCage (se OPENCAGE_API_KEY existir)
    Tentativa 3: Nominatim (sempre disponível, sem chave)
    
    Args:
        cidade: Nome da cidade
        estado: Nome do estado (padrão: Massachusetts)
    
    Returns:
        ((lat, lng), None) se sucesso
        (None, error_dict) se todas as tentativas falharem
    """
    
    query = f"{cidade}, {estado}"
    logger.info(f"Geocoding: {query}")
    
    # ===== TENTATIVA 1: LocationIQ =====
    if LOCATIONIQ_API_KEY:
        lat, lng, error = _geocode_locationiq(cidade, estado)
        if error is None:
            logger.info(f"✅ LocationIQ: {cidade} → {lat}, {lng}")
            return (lat, lng), None
        else:
            logger.warning(f"LocationIQ falhou: {error.get('error')}")
    else:
        logger.debug("LocationIQ: chave não configurada")
    
    # ===== TENTATIVA 2: OpenCage =====
    if OPENCAGE_API_KEY:
        lat, lng, error = _geocode_opencage(cidade, estado)
        if error is None:
            logger.info(f"✅ OpenCage: {cidade} → {lat}, {lng}")
            return (lat, lng), None
        else:
            logger.warning(f"OpenCage falhou: {error.get('error')}")
    else:
        logger.debug("OpenCage: chave não configurada")
    
    # ===== TENTATIVA 3: Nominatim (OpenStreetMap) =====
    lat, lng, error = _geocode_nominatim(cidade, estado)
    if error is None:
        logger.info(f"✅ Nominatim: {cidade} → {lat}, {lng}")
        return (lat, lng), None
    else:
        logger.error(f"Nominatim falhou: {error.get('error')}")
    
    # ===== TODAS AS TENTATIVAS FALHARAM =====
    return None, {
        'error': f'Unable to geocode {query}. All services failed.',
        'details': 'Tried LocationIQ, OpenCage, and Nominatim'
    }


def _geocode_locationiq(cidade: str, estado: str) -> Tuple[Optional[float], Optional[float], Optional[Dict]]:
    """LocationIQ Geocoding"""
    url = "https://api.locationiq.com/v1/search.json"
    params = {
        'key': LOCATIONIQ_API_KEY,
        'q': f'{cidade}, {estado}',
        'format': 'json'
    }
    
    data, error = fetch_json('LocationIQ', url, params=params, debug=DEBUG)
    
    if error:
        return None, None, error
    
    # Validar resposta
    if not isinstance(data, list) or len(data) == 0:
        return None, None, {
            'label': 'LocationIQ',
            'error': 'No results found or invalid response format'
        }
    
    try:
        result = data[0]
        lat = float(result['lat'])
        lng = float(result['lon'])
        return lat, lng, None
    except (KeyError, ValueError, TypeError) as e:
        return None, None, {
            'label': 'LocationIQ',
            'error': f'Invalid response format: {str(e)}'
        }


def _geocode_opencage(cidade: str, estado: str) -> Tuple[Optional[float], Optional[float], Optional[Dict]]:
    """OpenCage Geocoding"""
    url = "https://api.opencagedata.com/geocode/v1/json"
    params = {
        'q': f'{cidade}, {estado}',
        'key': OPENCAGE_API_KEY,
        'limit': 1
    }
    
    data, error = fetch_json('OpenCage', url, params=params, debug=DEBUG)
    
    if error:
        return None, None, error
    
    # Validar resposta
    if not isinstance(data, dict):
        return None, None, {
            'label': 'OpenCage',
            'error': 'Invalid response format'
        }
    
    try:
        results = data.get('results', [])
        if len(results) == 0:
            return None, None, {
                'label': 'OpenCage',
                'error': 'No results found'
            }
        
        geometry = results[0].get('geometry', {})
        lat = float(geometry['lat'])
        lng = float(geometry['lng'])
        return lat, lng, None
    except (KeyError, ValueError, TypeError) as e:
        return None, None, {
            'label': 'OpenCage',
            'error': f'Invalid response format: {str(e)}'
        }


def _geocode_nominatim(cidade: str, estado: str) -> Tuple[Optional[float], Optional[float], Optional[Dict]]:
    """Nominatim Geocoding (OpenStreetMap - sem chave necessária)"""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': f'{cidade}, {estado}',
        'format': 'json',
        'limit': 1
    }
    
    data, error = fetch_json('Nominatim', url, params=params, debug=DEBUG)
    
    if error:
        return None, None, error
    
    # Validar resposta
    if not isinstance(data, list) or len(data) == 0:
        return None, None, {
            'label': 'Nominatim',
            'error': 'No results found'
        }
    
    try:
        result = data[0]
        lat = float(result['lat'])
        lng = float(result['lon'])
        return lat, lng, None
    except (KeyError, ValueError, TypeError) as e:
        return None, None, {
            'label': 'Nominatim',
            'error': f'Invalid response format: {str(e)}'
        }
