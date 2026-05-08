"""
services/http.py
================
Utilitário centralizado para requisições HTTP com validação robusta.
Nunca lança JSONDecodeError - sempre retorna (data, error_dict)
"""

import requests
import json
import logging
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Headers padrão para todas as requisições
DEFAULT_HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'ev-viability/1.0'
}

GLOBAL_TIMEOUT = 10  # segundos


def sanitize_url(url: str, params: Dict) -> str:
    """Remove chaves sensíveis da URL para logging"""
    sensitive_keys = ['key', 'api_key', 'token', 'password']
    sanitized = url
    if params:
        for key in sensitive_keys:
            if key in params:
                sanitized += f"&{key}=***REDACTED***"
    return sanitized


def fetch_json(
    label: str,
    url: str,
    params: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    timeout: int = GLOBAL_TIMEOUT,
    debug: bool = False
) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Faz requisição HTTP e retorna (data, error_dict).
    
    Args:
        label: Nome do serviço (ex: 'LocationIQ', 'Google Places')
        url: URL da API
        params: Parâmetros da query
        headers: Headers customizados (mescla com DEFAULT_HEADERS)
        timeout: Timeout em segundos
        debug: Se True, loga mais detalhes
    
    Returns:
        (data, None) se sucesso
        (None, error_dict) se erro
    
    error_dict contém:
        - label: nome do serviço
        - status_code: HTTP status (se aplicável)
        - content_type: Content-Type da resposta (se aplicável)
        - error: descrição do erro
        - url_sanitizada: URL sem chaves sensíveis
        - body_preview: primeiros 200 chars do body (se aplicável)
    """
    
    try:
        # Mesclar headers
        req_headers = DEFAULT_HEADERS.copy()
        if headers:
            req_headers.update(headers)
        
        # Log de início
        if debug:
            logger.debug(f"[{label}] GET {sanitize_url(url, params)}")
        
        # Fazer requisição
        response = requests.get(
            url,
            params=params,
            headers=req_headers,
            timeout=timeout
        )
        
        # ===== VALIDAÇÃO 1: Status Code =====
        if response.status_code != 200:
            error_dict = {
                'label': label,
                'status_code': response.status_code,
                'error': f'HTTP {response.status_code}',
                'url_sanitizada': sanitize_url(url, params),
                'body_preview': response.text[:200] if response.text else '(empty)'
            }
            if debug:
                logger.warning(f"[{label}] HTTP {response.status_code}: {response.text[:100]}")
            return None, error_dict
        
        # ===== VALIDAÇÃO 2: Content-Type =====
        content_type = response.headers.get('content-type', '').lower()
        if 'json' not in content_type:
            error_dict = {
                'label': label,
                'status_code': 200,
                'content_type': content_type,
                'error': f'Response is not JSON (content-type: {content_type})',
                'url_sanitizada': sanitize_url(url, params),
                'body_preview': response.text[:200] if response.text else '(empty)'
            }
            if debug:
                logger.warning(f"[{label}] Not JSON: {content_type}")
            return None, error_dict
        
        # ===== VALIDAÇÃO 3: Body não vazio =====
        if not response.text.strip():
            error_dict = {
                'label': label,
                'status_code': 200,
                'content_type': content_type,
                'error': 'Response body is empty',
                'url_sanitizada': sanitize_url(url, params),
                'body_preview': '(empty)'
            }
            if debug:
                logger.warning(f"[{label}] Empty body")
            return None, error_dict
        
        # ===== VALIDAÇÃO 4: Parse JSON =====
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            error_dict = {
                'label': label,
                'status_code': 200,
                'content_type': content_type,
                'error': f'JSON parse error: {str(e)}',
                'url_sanitizada': sanitize_url(url, params),
                'body_preview': response.text[:200]
            }
            if debug:
                logger.error(f"[{label}] JSON parse error: {e}")
            return None, error_dict
        
        # ===== SUCESSO =====
        if debug:
            logger.debug(f"[{label}] ✅ Success")
        return data, None
    
    except requests.Timeout:
        error_dict = {
            'label': label,
            'error': f'Timeout after {timeout}s',
            'url_sanitizada': sanitize_url(url, params)
        }
        if debug:
            logger.error(f"[{label}] Timeout")
        return None, error_dict
    
    except requests.RequestException as e:
        error_dict = {
            'label': label,
            'error': f'Request error: {str(e)}',
            'url_sanitizada': sanitize_url(url, params)
        }
        if debug:
            logger.error(f"[{label}] Request error: {e}")
        return None, error_dict
    
    except Exception as e:
        error_dict = {
            'label': label,
            'error': f'Unexpected error: {str(e)}',
            'url_sanitizada': sanitize_url(url, params)
        }
        logger.error(f"[{label}] Unexpected error: {e}")
        return None, error_dict
