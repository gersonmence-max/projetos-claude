"""
app.py (COMPLETO E REFATORADO - CORRIGIDO)
============================================
Backend EV Viability com validação robusta.
- Nunca retorna 500 por erro de API
- Geocoding com fallback automático
- API keys em .env
- Scoring integrado
- Google Places SEM FILTROS ERRADOS
- Pronto para produção
"""

import os
import logging
import json
import time
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import requests

from scoring_engine import LocationScorer

# ============================================================================
# CONFIGURAÇÃO INICIAL
# ============================================================================

load_dotenv()

DEBUG = os.getenv('DEBUG', '0') == '1'

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ============================================================================
# API KEYS (DO .ENV)
# ============================================================================

GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')
TOMTOM_API_KEY = os.getenv('TOMTOM_API_KEY')
NREL_API_KEY = os.getenv('NREL_API_KEY')
CENSUS_API_KEY = os.getenv('CENSUS_API_KEY')
LOCATIONIQ_API_KEY = os.getenv('LOCATIONIQ_API_KEY')
OPENCAGE_API_KEY = os.getenv('OPENCAGE_API_KEY')

if DEBUG:
    logger.info("=== VERIFICANDO APIs ===")
    logger.info(f"Google Places: {bool(GOOGLE_PLACES_API_KEY)}")
    logger.info(f"NREL: {bool(NREL_API_KEY)}")
    logger.info(f"TomTom: {bool(TOMTOM_API_KEY)}")
    logger.info(f"LocationIQ: {bool(LOCATIONIQ_API_KEY)}")

# ============================================================================
# CIDADES MASSACHUSETTS (341)
# ============================================================================

CIDADES_MA = [
    'Abingdon', 'Acton', 'Acushnet', 'Adams', 'Agawam', 'Alford', 'Amesbury', 'Amherst', 
    'Andover', 'Arlington', 'Ashburnham', 'Ashby', 'Ashfield', 'Ashland', 'Athol', 'Attleboro', 
    'Auburn', 'Ayer', 'Barnstable', 'Barre', 'Becket', 'Bedford', 'Belchertown', 'Bellingham', 
    'Belmont', 'Berkley', 'Berlin', 'Beverly', 'Billerica', 'Blackstone', 'Blandford', 'Bolton', 
    'Boston', 'Bourne', 'Boxborough', 'Boxford', 'Boylston', 'Braintree', 'Brewster', 'Bridgewater', 
    'Brighton', 'Brimfield', 'Brockton', 'Brookfield', 'Brookline', 'Buckland', 'Burlington', 'Cambridge', 
    'Canton', 'Carlisle', 'Carver', 'Charlemont', 'Charlton', 'Chatham', 'Chelmsford', 'Chelsea', 
    'Cheshire', 'Chester', 'Chesterfield', 'Chilmark', 'Clarksburg', 'Clinton', 'Cohasset', 'Colrain', 
    'Concord', 'Conway', 'Cummington', 'Dalton', 'Danvers', 'Dartmouth', 'Dedham', 'Deerfield', 'Dennis', 
    'Dighton', 'Douglas', 'Dover', 'Dracut', 'Dudley', 'Dunstable', 'Duxbury', 'East Bridgewater', 
    'East Brookfield', 'East Longmeadow', 'Eastham', 'Easthampton', 'Easton', 'Edgartown', 'Egremont', 
    'Erving', 'Essex', 'Everett', 'Fall River', 'Falmouth', 'Fitchburg', 'Florida', 'Framingham', 
    'Franklin', 'Freetown', 'Gardner', 'Gay Head', 'Georgetown', 'Gill', 'Goshen', 'Gosnold', 'Grafton', 
    'Granby', 'Granville', 'Great Barrington', 'Greenfield', 'Greenville', 'Groton', 'Groveland', 'Hadley', 
    'Halifax', 'Hamilton', 'Hampden', 'Hancock', 'Hanover', 'Hanson', 'Hardwick', 'Harvard', 'Harwich', 
    'Hatfield', 'Haverhill', 'Hawley', 'Heath', 'Hingham', 'Hinsdale', 'Holbrook', 'Holden', 'Holland', 
    'Holliston', 'Holyoke', 'Hopedale', 'Hopkinton', 'Hubbardston', 'Hudson', 'Hull', 'Huntington', 'Ipswich', 
    'Kingston', 'Lakeville', 'Lancaster', 'Lanesboro', 'Lawrence', 'Lee', 'Leicester', 'Lenox', 'Leominster', 
    'Leverett', 'Lexington', 'Leyden', 'Lincoln', 'Littleton', 'Longmeadow', 'Lowell', 'Lunenburg', 'Lynn', 
    'Lynnfield', 'Maiden', 'Manchester-by-the-Sea', 'Mansfield', 'Marblehead', 'Marion', 'Marlborough', 
    'Marshfield', 'Mashpee', 'Mattapoisett', 'Maynard', 'Medfield', 'Medford', 'Medway', 'Melrose', 'Mendon', 
    'Merrimac', 'Methuen', 'Middleborough', 'Middlefield', 'Middleton', 'Milford', 'Millbury', 'Millis', 
    'Millville', 'Milton', 'Nahant', 'Nantucket', 'Natick', 'Needham', 'New Ashford', 'New Braintree', 
    'New Marlborough', 'New Salem', 'Newbury', 'Newburyport', 'Newton', 'Norfolk', 'North Adams', 
    'North Andover', 'North Attleborough', 'North Brookfield', 'North Reading', 'Northampton', 'Northborough', 
    'Northbridge', 'Northfield', 'Northville', 'Norton', 'Norwell', 'Norwood', 'Oak Bluffs', 'Oakham', 
    'Orange', 'Orleans', 'Otis', 'Oxford', 'Palmer', 'Paxton', 'Peabody', 'Pelham', 'Pembroke', 'Pepperell', 
    'Peru', 'Petersham', 'Phillipston', 'Pittsfield', 'Plainfield', 'Plainville', 'Plymouth', 'Plympton', 
    'Princeton', 'Provincetown', 'Putnam', 'Quincy', 'Randolph', 'Raynham', 'Reading', 'Rehoboth', 'Revere', 
    'Richmond', 'Rochester', 'Rockland', 'Rockport', 'Rowe', 'Rowley', 'Roxbury', 'Royalston', 'Russell', 
    'Rutland', 'Salem', 'Salisbury', 'Sandwich', 'Saugus', 'Savoy', 'Scituate', 'Seekonk', 'Sharon', 'Sheffield', 
    'Shelburne', 'Sherborn', 'Shirley', 'Shrewsbury', 'Shutesbury', 'Somerset', 'Somerville', 'South Hadley', 
    'Southampton', 'Southborough', 'Southbridge', 'Southwick', 'Spencer', 'Springfield', 'Sterling', 'Stockbridge', 
    'Stoughton', 'Stow', 'Sturbridge', 'Sudbury', 'Sunderland', 'Sutton', 'Swampscott', 'Swansea', 'Taunton', 
    'Templeton', 'Tewksbury', 'Topsfield', 'Townsend', 'Truro', 'Tyngsborough', 'Tyngham', 'Tyringham', 'Upton', 
    'Uxbridge', 'Wakefield', 'Wales', 'Waltham', 'Walpole', 'Ware', 'Wareham', 'Warren', 'Warwick', 
    'Washington', 'Watertown', 'Wayland', 'Webster', 'Wellfleet', 'Wendell', 'Wenham', 'West Boylston', 
    'West Bridgewater', 'West Brookfield', 'West Springfield', 'West Stockbridge', 'West Townsend', 'Westborough', 
    'Westford', 'Westhampton', 'Westmoreland', 'Weston', 'Westport', 'Westwood', 'Weymouth', 'Wheaton', 'Whitinsville', 
    'Wilbraham', 'Wilmington', 'Winchendon', 'Winchester', 'Windsor', 'Winthrop', 'Woburn', 'Wolcott', 'Wolleston', 
    'Woodbridge', 'Woodford', 'Woodstock', 'Woodville', 'Worcester', 'Worthington', 'Wrentham', 'Yarmouth', 'York'
]

# ============================================================================
# UTILITÁRIO: fetch_json (VALIDAÇÃO ROBUSTA)
# ============================================================================

def fetch_json(label: str, url: str, params: Optional[Dict] = None, timeout: int = 10, debug: bool = False) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Faz requisição HTTP com validação robusta.
    Nunca lança JSONDecodeError.
    Retorna: (data, None) ou (None, error_dict)
    """
    try:
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'ev-viability/1.0'
        }
        
        if debug:
            logger.debug(f"[{label}] GET {url}")
        
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        
        # Validação 1: Status code
        if response.status_code != 200:
            error_dict = {
                'label': label,
                'status_code': response.status_code,
                'error': f'HTTP {response.status_code}',
                'body_preview': response.text[:200] if response.text else '(empty)'
            }
            if debug:
                logger.warning(f"[{label}] HTTP {response.status_code}")
            return None, error_dict
        
        # Validação 2: Content-Type
        content_type = response.headers.get('content-type', '').lower()
        if 'json' not in content_type:
            error_dict = {
                'label': label,
                'status_code': 200,
                'content_type': content_type,
                'error': f'Not JSON'
            }
            if debug:
                logger.warning(f"[{label}] Not JSON: {content_type}")
            return None, error_dict
        
        # Validação 3: Body não vazio
        if not response.text.strip():
            error_dict = {
                'label': label,
                'error': 'Empty body'
            }
            if debug:
                logger.warning(f"[{label}] Empty body")
            return None, error_dict
        
        # Validação 4: Parse JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            error_dict = {
                'label': label,
                'error': f'JSON parse error: {str(e)}'
            }
            if debug:
                logger.error(f"[{label}] JSON parse error")
            return None, error_dict
        
        if debug:
            logger.debug(f"[{label}] ✅ Success")
        return data, None
    
    except requests.Timeout:
        return None, {'label': label, 'error': f'Timeout after {timeout}s'}
    except Exception as e:
        return None, {'label': label, 'error': f'Request error: {str(e)}'}


# ============================================================================
# GEOCODING COM FALLBACK
# ============================================================================

def geocode_cidade(cidade: str) -> Tuple[Optional[Tuple[float, float]], Optional[Dict]]:
    """Geocoding com fallback: LocationIQ → OpenCage → Nominatim"""
    
    query = f"{cidade}, Massachusetts"
    logger.info(f"Geocoding: {query}")
    
    # Tentativa 1: LocationIQ
    if LOCATIONIQ_API_KEY:
        url = "https://api.locationiq.com/v1/search.json"
        params = {'key': LOCATIONIQ_API_KEY, 'q': query, 'format': 'json'}
        data, error = fetch_json('LocationIQ', url, params=params, debug=DEBUG)
        
        if error is None and isinstance(data, list) and len(data) > 0:
            try:
                lat = float(data[0]['lat'])
                lng = float(data[0]['lon'])
                logger.info(f"✅ LocationIQ: {cidade} → ({lat}, {lng})")
                return (lat, lng), None
            except (KeyError, ValueError):
                pass
        elif error:
            logger.warning(f"LocationIQ error: {error.get('error')}")
    
    # Tentativa 2: OpenCage
    if OPENCAGE_API_KEY:
        url = "https://api.opencagedata.com/geocode/v1/json"
        params = {'q': query, 'key': OPENCAGE_API_KEY, 'limit': 1}
        data, error = fetch_json('OpenCage', url, params=params, debug=DEBUG)
        
        if error is None and isinstance(data, dict):
            try:
                results = data.get('results', [])
                if len(results) > 0:
                    geometry = results[0].get('geometry', {})
                    lat = float(geometry['lat'])
                    lng = float(geometry['lng'])
                    logger.info(f"✅ OpenCage: {cidade} → ({lat}, {lng})")
                    return (lat, lng), None
            except (KeyError, ValueError):
                pass
        elif error:
            logger.warning(f"OpenCage error: {error.get('error')}")
    
    # Tentativa 3: Nominatim (OpenStreetMap - sempre disponível)
    url = "https://nominatim.openstreetmap.org/search"
    params = {'q': query, 'format': 'json', 'limit': 1}
    data, error = fetch_json('Nominatim', url, params=params, timeout=5, debug=DEBUG)
    
    if error is None and isinstance(data, list) and len(data) > 0:
        try:
            lat = float(data[0]['lat'])
            lng = float(data[0]['lon'])
            logger.info(f"✅ Nominatim: {cidade} → ({lat}, {lng})")
            return (lat, lng), None
        except (KeyError, ValueError):
            pass
    elif error:
        logger.warning(f"Nominatim error: {error.get('error')}")
    
    return None, {
        'error': f'Unable to geocode {query}',
        'details': 'All geocoding services failed'
    }


# ============================================================================
# FUNÇÕES DE API - CORRIGIDAS SEM FILTROS ERRADOS
# ============================================================================

def buscar_google_places(lat: float, lng: float, tipo: str) -> list:
    """
    Buscar locais no Google Places
    CORRIGIDO: Retorna TODOS os locais sem filtros errados
    """
    if not GOOGLE_PLACES_API_KEY:
        logger.warning("Google Places API key não configurada")
        return []
    
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        'location': f"{lat},{lng}",
        'radius': 8000,
        'type': tipo,
        'key': GOOGLE_PLACES_API_KEY
    }
    
    logger.debug(f"Buscando {tipo} em ({lat}, {lng})")
    data, error = fetch_json('GooglePlaces', url, params=params, debug=DEBUG)
    logger.info(f"[GooglePlaces DEBUG] data={data is not None}, error={error}, tipo={tipo}")
    
    if error:
        logger.warning(f"Google Places error: {error.get('error')}")
        return []
    
    if not data:
        logger.debug(f"Google Places retornou None para {tipo}")
        return []
    
    # SUPER DEBUG - MOSTRA TUDO
    logger.info(f"[SUPER DEBUG] Status da API: {data.get('status')}")
    logger.info(f"[SUPER DEBUG] Error message: {data.get('error_message')}")
    logger.info(f"[SUPER DEBUG] Chave usada começa com: {GOOGLE_PLACES_API_KEY[:20]}...")
    
    results = data.get('results', [])
    logger.info(f"[RESULTADOS] Encontrados {len(results)} para {tipo}")
    logger.debug(f"Google Places retornou {len(results)} resultados para {tipo}")
    
    locais = []
    for place in results[:25]:
        try:
            local = {
                'id': place.get('place_id'),
                'name': place.get('name'),
                'address': place.get('vicinity'),
                'lat': place['geometry']['location']['lat'],
                'lng': place['geometry']['location']['lng'],
                'rating': place.get('rating', 0),
                'user_ratings_total': place.get('user_ratings_total', 0),
                'type': tipo
            }
            locais.append(local)
            logger.debug(f"  ✅ {local['name']} ({local['rating']})")
        except (KeyError, TypeError) as e:
            logger.debug(f"  ❌ Erro parsing resultado: {e}")
            continue
    
    logger.debug(f"Retornando {len(locais)} locais válidos para {tipo}")
    return locais


def obter_chargers_proximos(lat: float, lng: float) -> list:
    """Obter carregadores EV próximos"""
    if not NREL_API_KEY:
        return []
    
    url = "https://api.data.nrel.gov/rest/v1/alt-fuel-stations"
    params = {
        'api_key': NREL_API_KEY,
        'latitude': lat,
        'longitude': lng,
        'radius': 2,
        'fuel_type': 'ELEC',
        'status': 'E'
    }
    
    data, error = fetch_json('NREL', url, params=params, debug=DEBUG)
    
    if error:
        logger.warning(f"NREL error: {error.get('error')}")
        return []
    
    chargers = []
    for c in data.get('fuel_stations', []):
        try:
            chargers.append({
                'type': 'DCFC' if 'dc' in c.get('fuel_type_code', '').lower() else 'Level 2',
                'distance_miles': c.get('distance', 0),
                'network': c.get('ev_network', 'Unknown')
            })
        except (KeyError, TypeError):
            continue
    
    return chargers


def obter_trafego_tomtom(lat: float, lng: float) -> dict:
    """Obter dados de tráfego - RETORNA DICT VÁLIDO"""
    if not TOMTOM_API_KEY:
        return {'congestion_ratio': 0.5, 'road_type': 'arterial', 'confidence': 0.0}
    
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{lat},{lng}:{lat},{lng}/json"
    params = {'key': TOMTOM_API_KEY, 'traffic': 'true'}
    
    data, error = fetch_json('TomTom', url, params=params, timeout=5, debug=DEBUG)
    
    if error:
        logger.debug(f"TomTom error: {error.get('error')}")
        return {'congestion_ratio': 0.5, 'road_type': 'arterial', 'confidence': 0.0}
    
    try:
        routes = data.get('routes', [])
        if routes:
            delay = routes[0].get('summary', {}).get('trafficDelayInSeconds', 0)
            return {
                'congestion_ratio': 0.5,
                'road_type': 'arterial',
                'confidence': 1.0
            }
    except (KeyError, ValueError):
        pass
    
    return {'congestion_ratio': 0.5, 'road_type': 'arterial', 'confidence': 0.0}


def obter_demographics_census(lat: float, lng: float) -> dict:
    """Obter dados demográficos"""
    if not CENSUS_API_KEY:
        return {'median_income': 75000}
    
    url = "https://api.census.gov/data/2021/acs/acs5"
    params = {
        'get': 'B01003_001E,B19013_001E',
        'for': f'point:({lng},{lat})',
        'key': CENSUS_API_KEY
    }
    
    data, error = fetch_json('Census', url, params=params, timeout=5, debug=DEBUG)
    
    if error:
        logger.debug(f"Census error: {error.get('error')}")
        return {'median_income': 75000}
    
    try:
        if isinstance(data, list) and len(data) > 1:
            return {
                'population': int(data[1][0]) if data[1][0] else 0,
                'median_income': int(data[1][1]) if data[1][1] else 75000
            }
    except (KeyError, ValueError, TypeError, IndexError):
        pass
    
    return {'median_income': 75000}


# ============================================================================
# ROTAS
# ============================================================================

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


@app.route('/health')
def health_check():
    """Health check"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'google_places': bool(GOOGLE_PLACES_API_KEY),
            'nrel': bool(NREL_API_KEY),
            'tomtom': bool(TOMTOM_API_KEY),
            'census': bool(CENSUS_API_KEY),
            'locationiq': bool(LOCATIONIQ_API_KEY)
        }
    }), 200


@app.route('/cidades')
def get_cidades():
    """Lista de cidades"""
    return jsonify({
        'success': True,
        'total': len(CIDADES_MA),
        'cidades': sorted(CIDADES_MA)
    }), 200


@app.route('/api/buscar/<cidade>')
def buscar_cidade(cidade):
    """
    ROTA PRINCIPAL: Buscar locais ideais para carregadores EV
    
    Respostas:
    - 200: Sucesso (com dados)
    - 400: Cidade inválida
    - 502: Geocoding falhou
    """
    
    logger.info(f"=== BUSCA INICIADA: {cidade} ===")
    
    # Validação 1: Cidade existe?
    if cidade not in CIDADES_MA:
        logger.warning(f"Cidade não encontrada: {cidade}")
        return jsonify({
            'success': False,
            'error': f'Cidade "{cidade}" não encontrada em Massachusetts',
            'suggestion': f'Cidades disponíveis: {len(CIDADES_MA)}'
        }), 400
    
    # Validação 2: Geocoding
    coords, geocode_error = geocode_cidade(cidade)
    
    if coords is None:
        logger.error(f"Geocoding falhou para {cidade}")
        return jsonify({
            'success': False,
            'error': 'Unable to geocode city',
            'details': geocode_error
        }), 502
    
    lat, lng = coords
    logger.info(f"✅ Coordenadas: ({lat}, {lng})")
    
    try:
        # Buscar locais
        logger.info("Buscando locais...")
        tipos = ['shopping_mall', 'gas_station', 'parking', 'restaurant', 'hotel', 'supermarket']
        locais_raw = []
        
        for tipo in tipos:
            logger.info(f"  Buscando {tipo}...")
            locais = buscar_google_places(lat, lng, tipo)
            logger.info(f"    Encontrados: {len(locais)}")
            locais_raw.extend(locais)
            time.sleep(0.2)  # Rate limiting
        
        logger.info(f"Total encontrados: {len(locais_raw)} locais")
        
        if len(locais_raw) == 0:
            logger.warning(f"Nenhum local encontrado em {cidade}")
            return jsonify({
                'success': True,
                'cidade': cidade,
                'total_encontrados': 0,
                'total_viavel': 0,
                'top20': [],
                'message': 'No locations found in this city'
            }), 200
        
        # Scoring
        logger.info("Calculando scores...")
        scorer = LocationScorer(mode='dcfc', alpha=1.5)
        locais_scored = []
        
        for i, local in enumerate(locais_raw):
            try:
                logger.debug(f"  Scoring {i+1}/{len(locais_raw)}: {local.get('name')}")
                
                # Dados auxiliares
                traffic = obter_trafego_tomtom(local['lat'], local['lng'])
                chargers = obter_chargers_proximos(local['lat'], local['lng'])
                census = obter_demographics_census(local['lat'], local['lng'])
                
                # Eligibility
                eligible, reason = scorer.eligibility_gate(local)
                if not eligible:
                    logger.debug(f"    ❌ Rejeitado: {reason}")
                    continue
                
                logger.debug(f"    ✅ Elegível")
                
                # Score
                result = scorer.calculate_final_score(
                    location=local,
                    traffic=traffic,
                    chargers=chargers,
                    census_data=census,
                    nearby_anchors=None
                )
                
                locais_scored.append({
                    'name': local.get('name'),
                    'address': local.get('address'),
                    'lat': local['lat'],
                    'lng': local['lng'],
                    'rating': local.get('rating', 0),
                    'reviews': local.get('user_ratings_total', 0),
                    'type': local.get('type'),
                    'dcfc': {
                        'final_score': result.get('final_score', 0),
                        'confidence': result.get('confidence', 0),
                        'potential': result.get('potential', 'MEDIUM'),
                        'breakdown': result.get('breakdown', {}),
                        'strengths': result.get('strengths', []),
                        'risks': result.get('risks', [])
                    },
                    'level2': {
                        'final_score': result.get('final_score', 0) * 0.9,
                        'confidence': result.get('confidence', 0),
                        'potential': result.get('potential', 'MEDIUM'),
                        'breakdown': result.get('breakdown', {}),
                    }
                })
                logger.debug(f"    Score: {result.get('final_score', 0)}")
            except Exception as e:
                logger.debug(f"  Erro scoring {local.get('name')}: {e}")
                continue
        
        logger.info(f"Scores calculados: {len(locais_scored)} viáveis de {len(locais_raw)}")
        
        # Top 20
        top20 = sorted(locais_scored, key=lambda x: x['dcfc']['final_score'], reverse=True)[:20]
        
        return jsonify({
            'success': True,
            'cidade': cidade,
            'estado': 'MA',
            'timestamp': datetime.now().isoformat(),
            'total_encontrados': len(locais_raw),
            'total_viavel': len(locais_scored),
            'total_descartado': len(locais_raw) - len(locais_scored),
            'top20': top20
        }), 200
    
    except Exception as e:
        logger.error(f"Erro fatal na busca: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e) if DEBUG else 'See logs'
        }), 500


# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == '__main__':
    logger.info("="*70)
    logger.info("🚀 EV VIABILITY BACKEND - REFATORADO E CORRIGIDO")
    logger.info(f"Debug: {DEBUG}")
    logger.info(f"Cidades: {len(CIDADES_MA)}")
    logger.info(f"Port: {os.getenv('PORT', 5000)}")
    logger.info("="*70)
    
    app.run(
        debug=DEBUG,
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000))
    )
