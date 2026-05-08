"""
services/http.py
================
Utilitario centralizado para requisicoes HTTP.
Nunca lanca JSONDecodeError. Sempre retorna (data, error).
"""

import json
import logging
import requests
from typing import Optional, Dict, Tuple, Any

logger = logging.getLogger(__name__)


def fetch_json(
    label: str,
    url: str,
    params: Optional[Dict] = None,
    timeout: int = 10,
    debug: bool = False
) -> Tuple[Optional[Any], Optional[Dict]]:
    """
    Faz requisicao HTTP com validacao robusta.

    Retorna:
        (data, None)       em caso de sucesso
        (None, error_dict) em caso de falha

    Nunca lanca excecao. Nunca retorna JSONDecodeError.
    """
    try:
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'agentes-crew-2/1.0'
        }

        if debug:
            logger.debug(f"[{label}] GET {url} params={params}")

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout
        )

        # Validacao 1: Status code
        if response.status_code != 200:
            err = {
                'label': label,
                'error': f'HTTP {response.status_code}',
                'status_code': response.status_code,
                'body_preview': response.text[:200] if response.text else '(empty)'
            }
            if debug:
                logger.warning(f"[{label}] HTTP {response.status_code} | {response.text[:100]}")
            return None, err

        # Validacao 2: Content-Type deve conter json
        content_type = response.headers.get('content-type', '').lower()
        if 'json' not in content_type:
            err = {
                'label': label,
                'error': 'Response is not JSON',
                'content_type': content_type
            }
            if debug:
                logger.warning(f"[{label}] Not JSON: {content_type}")
            return None, err

        # Validacao 3: Body nao vazio
        if not response.text.strip():
            err = {'label': label, 'error': 'Empty response body'}
            if debug:
                logger.warning(f"[{label}] Empty body")
            return None, err

        # Validacao 4: Parse JSON seguro
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            err = {
                'label': label,
                'error': f'JSON parse error: {str(e)}',
                'body_preview': response.text[:200]
            }
            logger.error(f"[{label}] JSONDecodeError: {e}")
            return None, err

        if debug:
            logger.debug(f"[{label}] OK")

        return data, None

    except requests.Timeout:
        err = {'label': label, 'error': f'Timeout after {timeout}s'}
        logger.warning(f"[{label}] Timeout")
        return None, err

    except requests.ConnectionError as e:
        err = {'label': label, 'error': f'Connection error: {str(e)}'}
        logger.warning(f"[{label}] Connection error")
        return None, err

    except Exception as e:
        err = {'label': label, 'error': f'Unexpected error: {str(e)}'}
        logger.error(f"[{label}] Unexpected error: {e}")
        return None, err
