"""
app.py - agentes_crew_2
========================
Backend EV Viability v2.1 com 4 Correcoes Criticas integradas.

Correcoes ativas:
  [1] Penalidade Dinamica    - scores adaptados ao contexto geografico
  [2] Confidence Ranking     - score ponderado por qualidade dos dados
  [3] Timeout Global 8s      - nenhuma API trava o sistema
  [4] Feature Flags          - controle em producao sem redeploy

Melhorias de base:
  - Geocoding com fallback automatico (LocationIQ > OpenCage > Nominatim)
  - fetch_json() robusto em TODAS as chamadas HTTP
  - API keys no .env (nunca hardcoded)
  - Logging estruturado
  - Nunca retorna 500 por erro de API externa
  - Health check endpoint
  - Geracao de PDF
"""

import os
import logging
import time
import base64
from datetime import datetime
from io import BytesIO

from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import requests

# ----------------------------------------------------------------------------
# Modulos do projeto (agentes_crew_2)
# ----------------------------------------------------------------------------
from scoring_engine import LocationScorer, get_peak_traffic
from services.http import fetch_json
from services.geocode import geocode_cidade

from correcoes.correcao_1_penalidade_dinamica import SistemaDeScoreAdaptativo
from correcoes.correcao_2_confidence_ranking import RankingComConfianca, calcular_score_final
from correcoes.correcao_3_timeout_global import TimeoutManager
from correcoes.correcao_4_feature_flags import FeatureFlags

# PDF (opcional - nao quebra se nao instalado)
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# ============================================================================
# CONFIGURACAO
# ============================================================================

load_dotenv()

DEBUG = os.getenv('DEBUG', '0') == '1'

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Carregar Feature Flags
try:
    FeatureFlags.load_from_file('config/feature_flags.json')
except Exception:
    logger.warning("feature_flags.json nao encontrado. Usando defaults.")

logger.info(FeatureFlags.status_report())

# ============================================================================
# FLASK
# ============================================================================

app = Flask(__name__)
logs = []  # log em memoria para /logs endpoint


def log_action(agent: str, action: str, details: str = "") -> None:
    entry = {
        'timestamp': datetime.now().isoformat(),
        'agent':     agent,
        'action':    action,
        'details':   details
    }
    logs.append(entry)
    logger.info(f"[{agent}] {action} | {details}")


# ============================================================================
# API KEYS
# ============================================================================

GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')
TOMTOM_API_KEY        = os.getenv('TOMTOM_API_KEY')
NREL_API_KEY          = os.getenv('NREL_API_KEY')
CENSUS_API_KEY        = os.getenv('CENSUS_API_KEY')
OCM_API_KEY           = os.getenv('OCM_API_KEY')

# ============================================================================
# CIDADES MASSACHUSETTS (331)
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
    'Rutland', 'Salem', 'Salisbury', 'Sandwich', 'Saugus', 'Savoy', 'Scituate', 'Seekonk', 'Sharon',
    'Sheffield', 'Shelburne', 'Sherborn', 'Shirley', 'Shrewsbury', 'Shutesbury', 'Somerset', 'Somerville',
    'South Hadley', 'Southampton', 'Southborough', 'Southbridge', 'Southwick', 'Spencer', 'Springfield',
    'Sterling', 'Stockbridge', 'Stoughton', 'Stow', 'Sturbridge', 'Sudbury', 'Sunderland', 'Sutton',
    'Swampscott', 'Swansea', 'Taunton', 'Templeton', 'Tewksbury', 'Topsfield', 'Townsend', 'Truro',
    'Tyngsborough', 'Tyngham', 'Tyringham', 'Upton', 'Uxbridge', 'Wakefield', 'Wales', 'Waltham',
    'Walpole', 'Ware', 'Wareham', 'Warren', 'Warwick', 'Washington', 'Watertown', 'Wayland', 'Webster',
    'Wellfleet', 'Wendell', 'Wenham', 'West Boylston', 'West Bridgewater', 'West Brookfield',
    'West Springfield', 'West Stockbridge', 'West Townsend', 'Westborough', 'Westford', 'Westhampton',
    'Westmoreland', 'Weston', 'Westport', 'Westwood', 'Weymouth', 'Wheaton', 'Whitinsville',
    'Wilbraham', 'Wilmington', 'Winchendon', 'Winchester', 'Windsor', 'Winthrop', 'Woburn', 'Wolcott',
    'Wolleston', 'Woodbridge', 'Woodford', 'Woodstock', 'Woodville', 'Worcester', 'Worthington',
    'Wrentham', 'Yarmouth', 'York'
]

# ============================================================================
# FUNCOES DE API (com fetch_json robusto)
# ============================================================================

def buscar_google_places(lat: float, lng: float, tipo: str) -> list:
    """Buscar locais no Google Places com validacao robusta."""
    if not GOOGLE_PLACES_API_KEY:
        logger.warning("Google Places API key nao configurada")
        return []

    def _fazer_requisicao(timeout=8):
        url    = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            'location': f"{lat},{lng}",
            'radius':   8000,
            'type':     tipo,
            'key':      GOOGLE_PLACES_API_KEY
        }
        data, error = fetch_json('GooglePlaces', url, params=params,
                                 timeout=timeout, debug=DEBUG)
        return data, error

    # CORRECAO 3: Timeout global
    if FeatureFlags.USE_NEW_TIMEOUT:
        try:
            result = TimeoutManager.chamar_com_timeout(
                _fazer_requisicao, f"GooglePlaces-{tipo}", timeout=8
            )
            if result is None:
                return []
            data, error = result
        except TimeoutError:
            log_action('Agent-2-LocalSearch', 'Timeout', tipo)
            return []
    else:
        data, error = _fazer_requisicao(timeout=10)

    if error:
        log_action('Agent-2-LocalSearch', 'Erro API', f"{tipo}: {error.get('error')}")
        return []

    if not data:
        return []

    status = data.get('status', '')
    if status not in ('OK', 'ZERO_RESULTS'):
        msg = data.get('error_message', status)
        logger.warning(f"[GooglePlaces] Status: {status} | {msg}")
        # Propagar erro para a busca principal
        raise RuntimeError(f"Google Places API erro: {status} — {msg}")

    locais = []
    for place in data.get('results', [])[:25]:
        try:
            locais.append({
                'id':                 place.get('place_id'),
                'name':               place.get('name'),
                'address':            place.get('vicinity'),
                'lat':                place['geometry']['location']['lat'],
                'lng':                place['geometry']['location']['lng'],
                'rating':             place.get('rating', 0),
                'user_ratings_total': place.get('user_ratings_total', 0),
                'reviews':            place.get('user_ratings_total', 0),
                'type':               tipo,
                'opening_hours':      place.get('opening_hours', {}),
                'types':              place.get('types', []),
            })
        except (KeyError, TypeError):
            continue

    log_action('Agent-2-LocalSearch', 'Encontrados', f"{len(locais)} {tipo}")
    return locais


# Cache e circuit breaker para NREL
_nrel_falhou_consecutivo = 0
_NREL_MAX_FALHAS = 3  # Após 3 falhas seguidas, para de tentar

def verificar_carregador_existente(lat: float, lng: float) -> dict:
    """Verifica se ja existe carregador a menos de 160m."""
    global _nrel_falhou_consecutivo

    if not NREL_API_KEY or _nrel_falhou_consecutivo >= _NREL_MAX_FALHAS:
        return {'existe': False}

    url    = "https://api.data.nrel.gov/rest/v1/alt-fuel-stations"
    params = {
        'api_key':   NREL_API_KEY,
        'latitude':  lat,
        'longitude': lng,
        'radius':    0.1,
        'fuel_type': 'ELEC',
        'status':    'E'
    }
    data, error = fetch_json('NREL-Verify', url, params=params, timeout=8, debug=DEBUG)

    if error:
        _nrel_falhou_consecutivo += 1
        if _nrel_falhou_consecutivo >= _NREL_MAX_FALHAS:
            logger.warning(f"NREL desativado apos {_NREL_MAX_FALHAS} falhas consecutivas. Prosseguindo sem verificacao.")
        return {'existe': False}

    _nrel_falhou_consecutivo = 0  # reset ao ter sucesso
    carregadores = data.get('fuel_stations', []) if data else []
    if carregadores:
        c = carregadores[0]
        return {
            'existe':      True,
            'nome':        c.get('station_name', 'Desconhecido'),
            'rede':        c.get('ev_network', 'Desconhecida'),
            'distancia_m': round(c.get('distance', 0) * 1609, 0),
            'tipo':        'DCFC' if 'dc' in c.get('fuel_type_code', '').lower() else 'Level 2',
        }

    return {'existe': False}


def obter_chargers_proximos(lat: float, lng: float) -> list:
    """Obtem carregadores proximos (raio 2mi)."""
    global _nrel_falhou_consecutivo

    if not NREL_API_KEY or _nrel_falhou_consecutivo >= _NREL_MAX_FALHAS:
        return []

    url    = "https://api.data.nrel.gov/rest/v1/alt-fuel-stations"
    params = {
        'api_key':   NREL_API_KEY,
        'latitude':  lat,
        'longitude': lng,
        'radius':    2,
        'fuel_type': 'ELEC',
        'status':    'E'
    }
    data, error = fetch_json('NREL-Nearby', url, params=params, timeout=8, debug=DEBUG)

    if error or not data:
        _nrel_falhou_consecutivo += 1
        return []

    _nrel_falhou_consecutivo = 0
    chargers = []
    for c in data.get('fuel_stations', []):
        try:
            ev_level = c.get('ev_level1_evse_num') or 0
            ev_l2    = c.get('ev_level2_evse_num') or 0
            ev_dc    = c.get('ev_dc_fast_num') or 0
            dist_mi  = round(c.get('distance', 0), 2)
            dist_km  = round(dist_mi * 1.609, 2)

            if ev_dc > 0:
                ctype = 'DCFC'
            elif ev_l2 > 0:
                ctype = 'Level 2'
            else:
                ctype = 'Level 1'

            chargers.append({
                'type':         ctype,
                'distance_mi':  dist_mi,
                'distance_km':  dist_km,
                'network':      c.get('ev_network', 'Desconhecida'),
                'name':         c.get('station_name', ''),
                'address':      c.get('street_address', ''),
                'plugs_l2':     int(ev_l2),
                'plugs_dcfc':   int(ev_dc),
            })
        except (KeyError, TypeError):
            continue

    # Ordenar por distância
    chargers.sort(key=lambda x: x['distance_mi'])
    return chargers



def _ocm_query(lat, lng, raio_km, levelid, maxresults=5):
    """Busca OCM por nível específico."""
    url = 'https://api.openchargemap.io/v3/poi/'
    params = {
        'latitude': lat, 'longitude': lng,
        'distance': raio_km, 'distanceunit': 'km',
        'maxresults': maxresults, 'countrycode': 'US',
        'output': 'json', 'key': OCM_API_KEY,
        'levelid': levelid,
    }
    data, error = fetch_json(f'OCM-L{levelid}', url, params=params, timeout=8, debug=DEBUG)
    return data or []


def obter_chargers_ocm(lat: float, lng: float, raio_km: float = 5.0) -> list:
    """Busca carregadores DCFC e Level 2 via Open Charge Map API."""
    if not OCM_API_KEY:
        return []

    def parse_stations(stations, force_type=None):
        results = []
        for station in stations:
            try:
                addr     = station.get('AddressInfo', {})
                conns    = station.get('Connections', [])
                dist_km  = round(addr.get('Distance', 0), 2)
                dist_mi  = round(dist_km * 0.621371, 2)
                name     = addr.get('Title', '')
                operator = (station.get('OperatorInfo') or {}).get('Title', 'Desconhecida')
                max_kw   = max((c.get('PowerKW') or 0 for c in conns), default=0)
                n_plugs  = len(conns)
                n_dcfc   = sum(1 for c in conns if (c.get('Level') or {}).get('IsFastChargeCapable', False))
                n_l2     = n_plugs - n_dcfc

                ctype = force_type or ('DCFC' if n_dcfc > 0 else 'Level 2')

                results.append({
                    'type':        ctype,
                    'distance_km': dist_km,
                    'distance_mi': dist_mi,
                    'name':        name,
                    'address':     addr.get('AddressLine1', ''),
                    'network':     operator,
                    'plugs_total': n_plugs,
                    'plugs_l2':    n_l2,
                    'plugs_dcfc':  n_dcfc,
                    'max_kw':      max_kw,
                    'source':      'OCM',
                })
            except (KeyError, TypeError):
                continue
        return results

    # Busca separada por nível 3 (DCFC) e nível 2 (L2)
    dcfc_stations = _ocm_query(lat, lng, raio_km=10.0, levelid=3, maxresults=5)
    l2_stations   = _ocm_query(lat, lng, raio_km=5.0,  levelid=2, maxresults=5)

    chargers = parse_stations(dcfc_stations, force_type='DCFC') + parse_stations(l2_stations, force_type='Level 2')
    chargers.sort(key=lambda x: x['distance_km'])

    logger.debug(f"[OCM] DCFC: {len(dcfc_stations)} | L2: {len(l2_stations)}")
    return chargers


def obter_chargers_combinados(lat: float, lng: float) -> list:
    """Combina NREL + OCM, remove duplicatas por distância próxima."""
    nrel = obter_chargers_proximos(lat, lng)
    ocm  = obter_chargers_ocm(lat, lng, raio_km=5.0)

    # Se OCM retornou dados, usa OCM (mais detalhado)
    # Se não, usa NREL como fallback
    if ocm:
        logger.debug(f"[Chargers] OCM: {len(ocm)} | NREL: {len(nrel)}")
        return ocm
    else:
        logger.debug(f"[Chargers] Usando NREL fallback: {len(nrel)}")
        return nrel


def obter_trafego_tomtom(lat: float, lng: float) -> dict:
    """Obtem dados de trafego TomTom."""
    default = {'congestion_ratio': 0.5, 'road_type': 'arterial', 'confidence': 0.0}

    if not TOMTOM_API_KEY:
        return default

    url    = f"https://api.tomtom.com/routing/1/calculateRoute/{lat},{lng}:{lat},{lng}/json"
    params = {'key': TOMTOM_API_KEY, 'traffic': 'true'}
    data, error = fetch_json('TomTom', url, params=params, timeout=5, debug=DEBUG)

    if error or not data:
        return default

    try:
        routes = data.get('routes', [])
        if routes:
            delay = routes[0].get('summary', {}).get('trafficDelayInSeconds', 0)
            congestion = min(1.0, delay / 600)
            return {'congestion_ratio': congestion, 'road_type': 'arterial', 'confidence': 1.0}
    except (KeyError, TypeError, ValueError):
        pass

    return default


def obter_demographics_census(lat: float, lng: float) -> dict:
    """Obtem dados demograficos do Census."""
    default = {'median_income': 75000, 'population': 0}

    if not CENSUS_API_KEY:
        return default

    url    = "https://api.census.gov/data/2021/acs/acs5"
    params = {
        'get': 'B01003_001E,B19013_001E',
        'for': f'point:({lng},{lat})',
        'key': CENSUS_API_KEY
    }
    data, error = fetch_json('Census', url, params=params, timeout=5, debug=DEBUG)

    if error or not data:
        return default

    try:
        if isinstance(data, list) and len(data) > 1:
            return {
                'population':    int(data[1][0]) if data[1][0] else 0,
                'median_income': int(data[1][1]) if data[1][1] else 75000,
            }
    except (KeyError, ValueError, TypeError, IndexError):
        pass

    return default


# ============================================================================
# ROTAS
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
def health_check():
    return jsonify({
        'success':   True,
        'status':    'healthy',
        'version':   'agentes_crew_2 v2.1',
        'timestamp': datetime.now().isoformat(),
        'env': {
            'debug':             DEBUG,
            'has_google_places': bool(GOOGLE_PLACES_API_KEY),
            'has_nrel':          bool(NREL_API_KEY),
            'has_tomtom':        bool(TOMTOM_API_KEY),
            'has_census':        bool(CENSUS_API_KEY),
        },
        'flags': FeatureFlags.get_all_flags()
    }), 200


@app.route('/cidades')
def get_cidades():
    return jsonify({
        'success': True,
        'total':   len(CIDADES_MA),
        'cidades': sorted(CIDADES_MA)
    }), 200


@app.route('/logs')
def get_logs():
    return jsonify({'total_logs': len(logs), 'logs': logs[-100:]}), 200


@app.route('/logs/clear', methods=['POST'])
def clear_logs():
    global logs
    logs = []
    log_action('System', 'Logs limpos')
    return jsonify({'success': True}), 200


@app.route('/flags/status')
def get_flags():
    return jsonify(FeatureFlags.get_all_flags()), 200


# ============================================================================
# ROTA PRINCIPAL
# ============================================================================

@app.route('/api/buscar/<cidade>')
def buscar_cidade(cidade):
    """
    Busca os melhores locais para carregadores EV em uma cidade de MA.

    Returns:
        200: sucesso com top20
        400: cidade invalida
        502: geocoding falhou
        500: erro interno
    """
    modo = request.args.get('modo', 'dcfc').lower()
    log_action('System', 'Busca iniciada', f"{cidade} | modo={modo}")

    # ------------------------------------------------------------------
    # Validacao: cidade existe?
    # ------------------------------------------------------------------
    if cidade not in CIDADES_MA:
        return jsonify({
            'success': False,
            'error':   f'Cidade "{cidade}" nao encontrada em Massachusetts',
            'available_cities': len(CIDADES_MA)
        }), 400

    # ------------------------------------------------------------------
    # Geocoding com fallback (CORRECAO base)
    # ------------------------------------------------------------------
    log_action('Agent-1-Geocoding', 'Geocoding', cidade)
    coords, geocode_error = geocode_cidade(cidade, debug=DEBUG)

    if coords is None:
        log_action('Agent-1-Geocoding', 'Falha', str(geocode_error))
        return jsonify({
            'success': False,
            'error':   'Unable to geocode city',
            'details': geocode_error
        }), 502

    lat, lng = coords
    log_action('Agent-1-Geocoding', 'OK', f"({lat:.4f}, {lng:.4f})")

    try:
        # ------------------------------------------------------------------
        # Buscar locais
        # ------------------------------------------------------------------
        log_action('Agent-2-LocalSearch', 'Iniciando', 'Google Places')
        tipos = ['shopping_mall', 'gas_station', 'parking', 'restaurant', 'hotel', 'supermarket']
        locais_raw = []

        api_error = None
        for tipo in tipos:
            try:
                locais_raw.extend(buscar_google_places(lat, lng, tipo))
            except RuntimeError as e:
                api_error = str(e)
                logger.error(f"[Agent-2-LocalSearch] {api_error}")
                break
            time.sleep(0.2)

        log_action('Agent-2-LocalSearch', 'Total', f"{len(locais_raw)} locais")

        if api_error and not locais_raw:
            return jsonify({
                'success': False,
                'error':   'Erro na API de busca de locais',
                'details': api_error,
                'api':     'Google Places',
                'solucao': 'Verifique o faturamento em console.cloud.google.com → APIs e Serviços → Painel'
            }), 502

        if not locais_raw:
            return jsonify({
                'success':          True,
                'cidade':           cidade,
                'total_encontrados': 0,
                'total_viavel':     0,
                'top20':            [],
                'descartados':      [],
                'message':          'Nenhum local encontrado nesta cidade'
            }), 200

        # ------------------------------------------------------------------
        # Viability check: carregador ja existe?
        # ------------------------------------------------------------------
        log_action('Agent-4-Viability', 'Filtrando', 'Carregadores existentes')
        locais_viavel     = []
        locais_descartados = []

        for idx, local in enumerate(locais_raw):
            if idx > 0 and idx % 5 == 0:
                time.sleep(1)

            verif = verificar_carregador_existente(local['lat'], local['lng'])
            if verif['existe']:
                locais_descartados.append({
                    'name':        local['name'],
                    'address':     local['address'],
                    'motivo':      f"Carregador existente: {verif['nome']}",
                    'rede':        verif['rede'],
                    'distancia_m': verif['distancia_m'],
                    'tipo':        verif.get('tipo', 'ELEC'),
                })
            else:
                locais_viavel.append(local)

        log_action('Agent-4-Viability', 'Resultado',
                   f"Viaveis: {len(locais_viavel)} | Descartados: {len(locais_descartados)}")

        # ------------------------------------------------------------------
        # Scoring com as 4 correcoes
        # ------------------------------------------------------------------
        log_action('Agent-5-Scoring', 'Calculando', f"Modo: {modo.upper()}")
        scorer       = LocationScorer(mode=modo, alpha=1.5)
        sistema_pen  = SistemaDeScoreAdaptativo()
        locais_scored = []

        for local in locais_viavel:
            # Eligibility gate
            eligible, reason = scorer.eligibility_gate(local)
            if not eligible:
                locais_descartados.append({
                    'name':        local['name'],
                    'address':     local['address'],
                    'motivo':      f'Elegibilidade: {reason}',
                    'rede':        'N/A',
                    'distancia_m': 0,
                })
                continue

            # Dados auxiliares
            traffic  = obter_trafego_tomtom(local['lat'], local['lng'])
            chargers = obter_chargers_combinados(local['lat'], local['lng'])
            census   = obter_demographics_census(local['lat'], local['lng'])

            try:
                result = scorer.calculate_final_score(
                    location=local,
                    traffic=traffic,
                    chargers=chargers,
                    census_data=census,
                    nearby_anchors=None
                )

                score_bruto = result['final_score']
                confidence  = result['confidence']

                # CORRECAO 1: Penalidades dinamicas
                if FeatureFlags.USE_DYNAMIC_PENALTIES:
                    contexto = sistema_pen.inferir_contexto(local, chargers, census)
                    score_bruto = sistema_pen.aplicar(score_bruto, contexto)

                # CORRECAO 2: Confidence weighting
                if FeatureFlags.USE_CONFIDENCE_WEIGHTING:
                    score_final = calcular_score_final(score_bruto, confidence)
                else:
                    score_final = score_bruto

                locais_scored.append({
                    'name':             local['name'],
                    'address':          local['address'],
                    'lat':              local['lat'],
                    'lng':              local['lng'],
                    'rating':           local.get('rating', 0),
                    'reviews':          local.get('user_ratings_total', 0),
                    'type':             local.get('type'),
                    'score':            result['final_score'],
                    'score_final':      score_final,
                    'confidence':       confidence,
                    'potencial':        result['potential'],
                    'breakdown':        result['breakdown'],
                    'strengths':        result['strengths'],
                    'risks':            result['risks'],
                    'flags':            result['flags'],
                    'nearest_competitor': result['nearest_competitor'],
                    'trafego':          traffic,
                    'concorrencia':     len(chargers),
                    'nearest_l2':       next((c for c in chargers if c['type']=='Level 2'), None),
                    'nearest_dcfc':     next((c for c in chargers if c['type']=='DCFC'), None),
                })

            except Exception as e:
                logger.error(f"Erro scoring {local.get('name')}: {e}", exc_info=DEBUG)
                continue

        # ------------------------------------------------------------------
        # Ranking (CORRECAO 4)
        # ------------------------------------------------------------------
        log_action('Agent-6-Ranking', 'Ordenando', f"{len(locais_scored)} locais")

        if FeatureFlags.USE_NEW_RANKING:
            ranking_obj = RankingComConfianca()
            top20 = ranking_obj.ranking_final(locais_scored)[:20]
        else:
            top20 = sorted(locais_scored, key=lambda x: x['score_final'], reverse=True)[:20]

        log_action('Agent-6-Ranking', 'Completo', f"Top {len(top20)} gerado")

        return jsonify({
            'success':           True,
            'cidade':            cidade,
            'estado':            'MA',
            'modo':              modo.upper(),
            'timestamp':         datetime.now().isoformat(),
            'total_encontrados': len(locais_raw),
            'total_viavel':      len(locais_viavel),
            'total_descartado':  len(locais_descartados),
            'top20':             top20,
            'descartados':       locais_descartados,
            'flags_ativas':      FeatureFlags.get_all_flags(),
        }), 200

    except Exception as e:
        log_action('System', 'Erro Fatal', str(e)[:200])
        logger.error(f"Erro fatal: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error':   'Internal server error',
            'details': str(e) if DEBUG else 'Ative DEBUG=1 para detalhes'
        }), 500


# ============================================================================
# GERACAO DE PDF
# ============================================================================

@app.route('/api/gerar-pdf', methods=['POST'])
def gerar_pdf():
    """Gera PDF com os resultados da busca."""
    if not FeatureFlags.USE_PDF_GENERATION:
        return jsonify({'success': False, 'error': 'PDF desativado via feature flag'}), 403

    if not PDF_AVAILABLE:
        return jsonify({'success': False, 'error': 'reportlab nao instalado'}), 500

    try:
        data        = request.json or {}
        cidade      = data.get('cidade', 'Massachusetts')
        top20       = data.get('top20', [])
        descartados = data.get('descartados', [])

        log_action('PDF-Generator', 'Criando', f"PDF de {cidade}")

        buffer = BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=letter)
        story  = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#2d6a4f'),
            spaceAfter=20,
            alignment=1
        )
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#555555'),
            spaceAfter=20,
            alignment=1
        )

        story.append(Paragraph(f'Relatorio EV Viability - {cidade}, MA', title_style))
        story.append(Paragraph(
            f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")} | agentes_crew_2 v2.1',
            subtitle_style
        ))
        story.append(Spacer(1, 0.2 * inch))

        # Top 20
        story.append(Paragraph('Top 20 Oportunidades', styles['Heading2']))
        story.append(Spacer(1, 0.1 * inch))

        header = [['#', 'Local', 'Score', 'Score Final', 'Potencial', 'Confianca', 'Tipo']]
        rows   = []
        for idx, loc in enumerate(top20[:20], 1):
            rows.append([
                str(idx),
                str(loc.get('name', ''))[:35],
                f"{loc.get('score', 0):.1f}/10",
                f"{loc.get('score_final', loc.get('score', 0)):.1f}/10",
                str(loc.get('potencial', 'MEDIUM')),
                f"{int(loc.get('confidence', 0) * 100)}%",
                str(loc.get('type', ''))[:15],
            ])

        table = Table(header + rows, colWidths=[0.3*inch, 2.2*inch, 0.7*inch,
                                                0.8*inch, 0.9*inch, 0.8*inch, 0.9*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND',  (0, 0), (-1, 0),  colors.HexColor('#2d6a4f')),
            ('TEXTCOLOR',   (0, 0), (-1, 0),  colors.whitesmoke),
            ('FONTNAME',    (0, 0), (-1, 0),  'Helvetica-Bold'),
            ('FONTSIZE',    (0, 0), (-1, 0),  9),
            ('ALIGN',       (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE',    (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4f0')]),
            ('GRID',        (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('TOPPADDING',  (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(table)

        # Descartados
        if descartados:
            story.append(PageBreak())
            story.append(Paragraph('Locais Descartados', styles['Heading2']))
            story.append(Spacer(1, 0.1 * inch))

            d_header = [['Local', 'Motivo', 'Rede']]
            d_rows   = []
            for loc in descartados[:30]:
                d_rows.append([
                    str(loc.get('name', ''))[:35],
                    str(loc.get('motivo', ''))[:45],
                    str(loc.get('rede', 'N/A'))[:20],
                ])

            d_table = Table(d_header + d_rows, colWidths=[2.2*inch, 3.2*inch, 1.5*inch])
            d_table.setStyle(TableStyle([
                ('BACKGROUND',  (0, 0), (-1, 0),  colors.HexColor('#764ba2')),
                ('TEXTCOLOR',   (0, 0), (-1, 0),  colors.whitesmoke),
                ('FONTNAME',    (0, 0), (-1, 0),  'Helvetica-Bold'),
                ('FONTSIZE',    (0, 0), (-1, -1), 8),
                ('ALIGN',       (0, 0), (-1, -1), 'LEFT'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f4ff')]),
                ('GRID',        (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('TOPPADDING',  (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(d_table)

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        log_action('PDF-Generator', 'Completo', f"{len(pdf_bytes)} bytes")

        return jsonify({
            'success':  True,
            'pdf':      base64.b64encode(pdf_bytes).decode('utf-8'),
            'filename': f'BuscaEV_{cidade}_{datetime.now().strftime("%Y%m%d")}.pdf'
        }), 200

    except Exception as e:
        log_action('PDF-Generator', 'Erro', str(e)[:100])
        logger.error(f"Erro PDF: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# INICIAR
# ============================================================================

@app.route('/api/gerar-pdf-rota', methods=['POST'])
def gerar_pdf_rota():
    """Gera PDF do roteiro de visitas selecionados."""
    if not PDF_AVAILABLE:
        return jsonify({'success': False, 'error': 'reportlab nao instalado'}), 500
    try:
        data    = request.json or {}
        cidade  = data.get('cidade', 'Massachusetts')
        locais  = data.get('locais', [])
        dist_km = data.get('dist_km', '—')
        tempo   = data.get('tempo', '—')

        buffer = BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=letter,
                                   leftMargin=0.75*inch, rightMargin=0.75*inch,
                                   topMargin=0.75*inch, bottomMargin=0.75*inch)
        story  = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('RT', parent=styles['Heading1'],
            fontSize=20, textColor=colors.HexColor('#1a73e8'), spaceAfter=6, alignment=1)
        sub_style = ParagraphStyle('RS', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor('#718096'), spaceAfter=18, alignment=1)
        stop_name = ParagraphStyle('SN', parent=styles['Normal'],
            fontSize=12, textColor=colors.HexColor('#e2e8f0'), fontName='Helvetica-Bold', spaceBefore=8)
        stop_addr = ParagraphStyle('SA', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor('#718096'), spaceAfter=4)
        stop_info = ParagraphStyle('SI', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor('#68d391'))

        story.append(Paragraph(f'Roteiro de Visitas — {cidade}, MA', title_style))
        story.append(Paragraph(
            f'{len(locais)} paradas  ·  {dist_km} km estimados  ·  {tempo}  ·  {datetime.now().strftime("%d/%m/%Y %H:%M")}',
            sub_style))

        # tabela resumo
        header = [['Parada', 'Local', 'Endereço', 'Score', 'Potencial']]
        rows = []
        for i, loc in enumerate(locais, 1):
            rows.append([
                str(i),
                str(loc.get('name',''))[:30],
                str(loc.get('address',''))[:38],
                f"{(loc.get('score_final') or loc.get('score') or 0):.1f}",
                str(loc.get('potencial',''))
            ])
        tbl = Table(header + rows, colWidths=[0.55*inch, 1.8*inch, 2.6*inch, 0.7*inch, 1.0*inch])
        tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0),  colors.HexColor('#1a73e8')),
            ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
            ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
            ('FONTSIZE',      (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.HexColor('#1a1f2e'), colors.HexColor('#111827')]),
            ('TEXTCOLOR',     (0,1), (-1,-1), colors.HexColor('#e2e8f0')),
            ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#2d3748')),
            ('ALIGN',         (0,0), (-1,-1), 'LEFT'),
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING',    (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.3*inch))

        # detalhes por parada
        story.append(Paragraph('Detalhes das Paradas', styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        for i, loc in enumerate(locais, 1):
            score = (loc.get('score_final') or loc.get('score') or 0)
            conf  = int((loc.get('confidence') or 0) * 100)
            bd    = loc.get('breakdown') or {}
            story.append(Paragraph(f"{i}. {loc.get('name','')}", stop_name))
            story.append(Paragraph(f"📍 {loc.get('address','—')}", stop_addr))
            story.append(Paragraph(
                f"Score: {score:.1f}/10  ·  Potencial: {loc.get('potencial','')}  ·  Confiança: {conf}%  ·  "
                f"Demand: {bd.get('demand',0)}  Competition: {bd.get('competition',0)}  "
                f"Site Fit: {bd.get('site_fit',0)}  EV Affinity: {bd.get('ev_affinity',0)}",
                stop_info))
            strengths = loc.get('strengths') or []
            risks     = loc.get('risks') or []
            if strengths:
                story.append(Paragraph('  ✓ ' + '   ✓ '.join(strengths[:2]), stop_addr))
            if risks:
                story.append(Paragraph('  ⚠ ' + '   ⚠ '.join(risks[:2]), stop_addr))
            story.append(Spacer(1, 0.05*inch))

        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph('Gerado por agentes_crew_2 v2.1 — EV Viability Finder', sub_style))

        doc.build(story)
        pdf_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        filename = f"roteiro_{cidade.lower().replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        return jsonify({'success': True, 'pdf': pdf_b64, 'filename': filename})
    except Exception as e:
        logger.error(f'Erro PDF rota: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  EV VIABILITY BACKEND - agentes_crew_2 v2.1")
    print("  4 Correcoes Criticas Ativas")
    print(f"  Debug: {DEBUG}")
    print(f"  Cidades: {len(CIDADES_MA)}")
    print(f"  Acesse: http://localhost:5000")
    print("=" * 60 + "\n")

    log_action('System', 'Startup', 'agentes_crew_2 iniciado')
    app.run(
        debug=DEBUG,
        host='127.0.0.1',
        port=int(os.getenv('PORT', 5000)),
        use_reloader=False
    )
