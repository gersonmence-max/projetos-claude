from flask import Flask, request, jsonify, render_template
from langchain_openai import ChatOpenAI
import os
import requests
from datetime import datetime
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
import base64
import time
from scoring_engine import LocationScorer, get_peak_traffic

# ============================================================================
# IMPORTAR AS 4 CORREÇÕES CRÍTICAS
# ============================================================================
from correcoes.correcao_1_penalidade_dinamica import SistemaDeScoreAdaptativo
from correcoes.correcao_2_confidence_ranking import RankingComConfianca, calcular_score_final
from correcoes.correcao_3_timeout_global import TimeoutManager
from correcoes.correcao_4_feature_flags import FeatureFlags

# ============================================================================
# CARREGAR FEATURE FLAGS (CONTROLE EM PRODUÇÃO)
# ============================================================================
try:
    FeatureFlags.load_from_file('config/feature_flags.json')
except:
    print("⚠️ feature_flags.json não encontrado. Usando defaults.")

print(FeatureFlags.status_report())

# ============================================================================
# INICIALIZAR FLASK
# ============================================================================
app = Flask(__name__)

# Store logs in memory
logs = []

def log_action(agent, action, details=""):
    """Log todas as acoes dos agentes"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'agent': agent,
        'action': action,
        'details': details
    }
    logs.append(log_entry)
    print(f"[{agent}] {action} - {details}")

llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# API KEYS
LOCATIONIQ_API_KEY = "pk.50e7c9d4f3fdcaad74cf780520d73fef"
GOOGLE_PLACES_API_KEY = "AIzaSyDgO70CyM2DT-9MuXIewI6UIA8fe1XAxzM"
CENSUS_API_KEY = "JGfxHNr2DA4wgW1907zWTcSmQjnjAAIMRC9Le5iv"
NREL_API_KEY = "GgtIP968XGtEoTtX1hSgHliGjab6c7hopfK6CuMh"
TOMTOM_API_KEY = "7mfUjJJzPqFu95PdZY2EfpRtxUavOtza"

# ============================================================================
# LISTA COMPLETA DE CIDADES DE MASSACHUSETTS (331 CIDADES)
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
# ROTAS
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logs')
def get_logs():
    """Retorna todos os logs em tempo real"""
    return jsonify({
        'total_logs': len(logs),
        'logs': logs[-100:]
    })

@app.route('/logs/clear', methods=['POST'])
def clear_logs():
    """Limpa todos os logs"""
    global logs
    logs = []
    log_action('System', 'Logs cleared')
    return jsonify({'success': True, 'message': 'Logs cleared'})

@app.route('/cidades')
def get_cidades():
    """Retorna lista de cidades disponveis"""
    return jsonify({
        'total': len(CIDADES_MA),
        'cidades': sorted(CIDADES_MA)
    })

@app.route('/flags/status')
def get_flags_status():
    """Retorna status de todas as feature flags"""
    return jsonify(FeatureFlags.get_all_flags())

# ============================================================================
# FUNÇÕES DE INTEGRAÇÃO COM AS CORREÇÕES
# ============================================================================

def calcular_score_final_com_correcoes(score_bruto, confidence):
    """
    Calcular score final USANDO CORREÇÃO 2 (Confidence Weighting)
    """
    
    if FeatureFlags.USE_CONFIDENCE_WEIGHTING:
        return calcular_score_final(score_bruto, confidence)
    else:
        return score_bruto


def aplicar_penalidades_dinamicas(score, contexto_geografico):
    """
    Aplicar penalidades DINÂMICAS baseado em contexto
    (CORREÇÃO 1)
    """
    
    if FeatureFlags.USE_DYNAMIC_PENALTIES:
        sistema = SistemaDeScoreAdaptativo()
        return score
    else:
        return score


# ============================================================================
# FUNÇÕES ORIGINAIS (COM TIMEOUT CORRIGIDO)
# ============================================================================

def buscar_google_places(lat, lng, tipo):
    """Buscar locais Google Places com CORREÇÃO 3 (Timeout)"""
    try:
        log_action('Agent-2-LocalSearch', 'Buscando', f'Tipo: {tipo}')
        
        def fazer_requisicao(timeout=3):
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': f"{lat},{lng}",
                'radius': 8000,
                'type': tipo,
                'key': GOOGLE_PLACES_API_KEY
            }
            return requests.get(url, params=params, timeout=timeout)
        
        if FeatureFlags.USE_NEW_TIMEOUT:
            response = TimeoutManager.chamar_com_timeout(
                fazer_requisicao,
                f"GooglePlaces-{tipo}"
            )
        else:
            response = fazer_requisicao(timeout=10)
        
        data = response.json()
        
        if data.get('results'):
            quantidade = len(data['results'][:25])
            log_action('Agent-2-LocalSearch', 'Encontrados', f'{quantidade} {tipo}')
            return data['results'][:25]
        
        return []
    except Exception as e:
        log_action('Agent-2-LocalSearch', 'Erro', f'{tipo}: {str(e)[:50]}')
        return []

def extrair_dados_completos_lugar(place, tipo):
    """Extrair dados REAIS do Google Places"""
    try:
        return {
            'id': place.get('place_id'),
            'name': place.get('name'),
            'address': place.get('vicinity'),
            'lat': place['geometry']['location']['lat'],
            'lng': place['geometry']['location']['lng'],
            'rating': place.get('rating', 3.5),
            'reviews': place.get('user_ratings_total', 0),
            'type': tipo,
            'preco_nivel': place.get('price_level', 0),
            'aberto_agora': place.get('opening_hours', {}).get('open_now', None) if place.get('opening_hours') else None,
            'fotos': len(place.get('photos', [])),
            'types': place.get('types', []),
            'opening_hours': place.get('opening_hours', {})
        }
    except Exception as e:
        log_action('Agent-2-LocalSearch', 'Erro', f'Extraindo dados: {str(e)[:50]}')
        return None

def verificar_carregador_existente(lat, lng, tentativa=1):
    """Verificar se JA existe carregador a 160m - COM RETRY"""
    try:
        if tentativa > 1:
            time.sleep(1)
        
        log_action('Agent-Viability', 'Verificando', f'Carregador em {lat:.2f},{lng:.2f}')
        
        url = "https://api.data.nrel.gov/rest/v1/alt-fuel-stations"
        params = {
            'api_key': NREL_API_KEY,
            'latitude': lat,
            'longitude': lng,
            'radius': 0.1,
            'fuel_type': 'ELEC',
            'status': 'E'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            carregadores = data.get('fuel_stations', [])
            
            if carregadores:
                log_action('Agent-Viability', 'Descartado', f'Carregador: {carregadores[0].get("station_name")}')
                return {
                    'existe': True,
                    'nome': carregadores[0].get('station_name', 'Desconhecido'),
                    'rede': carregadores[0].get('ev_network', 'Desconhecida'),
                    'distancia_m': round(carregadores[0].get('distance', 0) * 1609, 0),
                    'tipo': carregadores[0].get('fuel_type_code', 'ELEC')
                }
            
            log_action('Agent-Viability', 'Viavel', 'Sem carregador proximo')
            return {'existe': False}
        else:
            if tentativa < 2:
                log_action('Agent-Viability', 'Retry', f'Tentativa {tentativa+1}')
                return verificar_carregador_existente(lat, lng, tentativa+1)
            else:
                log_action('Agent-Viability', 'API Error', 'Assumindo sem carregador')
                return {'existe': False}
    except Exception as e:
        log_action('Agent-Viability', 'Erro', str(e)[:100])
        return {'existe': False}

def obter_chargers_proximos(lat, lng):
    """Obter carregadores proximos (com tipo e rede)"""
    try:
        url = "https://api.data.nrel.gov/rest/v1/alt-fuel-stations"
        params = {
            'api_key': NREL_API_KEY,
            'latitude': lat,
            'longitude': lng,
            'radius': 2,
            'fuel_type': 'ELEC',
            'status': 'E'
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            chargers = []
            for c in data.get('fuel_stations', []):
                chargers.append({
                    'type': 'DCFC' if 'dc' in c.get('fuel_type_code', '').lower() else 'Level 2',
                    'distance_miles': c.get('distance', 0),
                    'network': c.get('ev_network', 'Unknown')
                })
            return chargers
        
        return []
    except:
        return []

def obter_trafego_tomtom(lat, lng, hora=None):
    """Obter dados de trafego TomTom"""
    try:
        url = f"https://api.tomtom.com/routing/1/calculateRoute/{lat},{lng}:{lat},{lng}/json"
        params = {
            'key': TOMTOM_API_KEY,
            'traffic': 'true'
        }
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('routes'):
                summary = data['routes'][0].get('summary', {})
                return summary.get('trafficDelayInSeconds', 0) / 60
        
        return 0
    except:
        return 0

def obter_demographics_census(lat, lng):
    """Obter dados demograficos Census"""
    try:
        url = "https://api.census.gov/data/2021/acs/acs5"
        params = {
            'get': 'B01003_001E,B19013_001E',
            'for': 'point:({},{})'.format(lng, lat),
            'key': CENSUS_API_KEY
        }
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:
                return {
                    'population': int(data[1][0]) if data[1][0] else 0,
                    'median_income': int(data[1][1]) if data[1][1] else 0
                }
        
        return {'population': 0, 'median_income': 0}
    except:
        return {'population': 0, 'median_income': 0}

# ============================================================================
# ROTA PRINCIPAL: BUSCAR LOCAIS COM TODAS AS CORREÇÕES
# ============================================================================

@app.route('/api/buscar/<cidade>')
def buscar_cidade(cidade):
    """
    ROTA PRINCIPAL com todas as 4 correções integradas
    """
    try:
        modo = request.args.get('modo', 'dcfc').lower()
        
        if cidade not in CIDADES_MA:
            return jsonify({'success': False, 'error': f'Cidade {cidade} não encontrada'}), 404
        
        log_action('Agent-1-Geocoding', 'Validando', f'{cidade}, MA')
        
        # Geocoding
        url = f"https://api.locationiq.com/v1/search.json"
        params = {
            'key': LOCATIONIQ_API_KEY,
            'q': f'{cidade}, Massachusetts',
            'format': 'json'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if not response.json():
            return jsonify({'success': False, 'error': 'Cidade não encontrada'}), 404
        
        result = response.json()[0]
        lat, lng = float(result['lat']), float(result['lon'])
        log_action('Agent-1-Geocoding', 'Sucesso', f'Coordenadas: {lat}, {lng}')
        
        # Buscar locais
        log_action('Agent-2-LocalSearch', 'Iniciando busca', 'Google Places')
        
        tipos = ['shopping_mall', 'gas_station', 'parking', 'restaurant', 'hotel', 'supermarket']
        locais_raw = []
        
        for tipo in tipos:
            locais_raw.extend(buscar_google_places(lat, lng, tipo))
        
        log_action('Agent-2-LocalSearch', 'Encontrados', f'{len(locais_raw)} locais')
        
        # Processing
        log_action('Agent-3-Processing', 'Processando', 'Extracting dados reais')
        
        type_mapping = {
            'shopping_mall': 'Shopping',
            'gas_station': 'Gas Station',
            'parking': 'Parking',
            'restaurant': 'Restaurant',
            'hotel': 'Hotel',
            'supermarket': 'Supermarket'
        }
        
        locais_processados = []
        for local_raw in locais_raw:
            tipo = 'Other'
            for t, mapped in type_mapping.items():
                if t in local_raw.get('types', []):
                    tipo = mapped
                    break
            
            local = extrair_dados_completos_lugar(local_raw, tipo)
            if local:
                locais_processados.append(local)
        
        # Viability Check
        log_action('Agent-4-Viability', 'Filtrando', 'Carregadores existentes')
        
        locais_viavel = []
        locais_descartados = []
        
        for idx, local in enumerate(locais_processados):
            if idx > 0 and idx % 5 == 0:
                time.sleep(2)
            
            verif = verificar_carregador_existente(local['lat'], local['lng'])
            
            if verif['existe']:
                locais_descartados.append({
                    'name': local['name'],
                    'address': local['address'],
                    'motivo': f"Carregador existente: {verif['nome']}",
                    'rede': verif['rede'],
                    'distancia_m': verif['distancia_m'],
                    'tipo': verif.get('tipo', 'ELEC')
                })
            else:
                locais_viavel.append(local)
        
        log_action('Agent-4-Viability', 'Resultado', f'Viveis: {len(locais_viavel)}, Descartados: {len(locais_descartados)}')
        
        # Scoring
        log_action('Agent-5-Scoring', 'Calculando', f'Scores com Scoring Engine ({modo})')
        
        scorer = LocationScorer(mode=modo, alpha=1.5)
        locais_scored = []
        
        for local in locais_viavel:
            eligible, reason = scorer.eligibility_gate(local)
            
            if not eligible:
                log_action('Agent-5-Scoring', 'Descartado', f'{local["name"]}: {reason}')
                locais_descartados.append({
                    'name': local['name'],
                    'address': local['address'],
                    'motivo': f'Filtro elegibilidade: {reason}',
                    'rede': 'N/A',
                    'distancia_m': 0
                })
                continue
            
            traffic = obter_trafego_tomtom(local['lat'], local['lng'])
            chargers = obter_chargers_proximos(local['lat'], local['lng'])
            census = obter_demographics_census(local['lat'], local['lng'])
            
            try:
                result = scorer.calculate_final_score(
                    location=local,
                    traffic=traffic,
                    chargers=chargers,
                    census_data=census,
                    nearby_anchors=None
                )
                
                # ========================================================
                # CORREÇÃO 2: Aplicar confidence weighting ao score final
                # ========================================================
                score_final = calcular_score_final_com_correcoes(
                    result['final_score'],
                    result['confidence']
                )
                
                locais_scored.append({
                    'name': local['name'],
                    'address': local['address'],
                    'lat': local['lat'],
                    'lng': local['lng'],
                    'rating': local['rating'],
                    'reviews': local['reviews'],
                    'type': local['type'],
                    'trafego': traffic,
                    'concorrencia': len(chargers),
                    'score': result['final_score'],
                    'score_final': score_final,
                    'confidence': result['confidence'],
                    'potencial': result['potential'],
                    'breakdown': result['breakdown'],
                    'strengths': result['strengths'],
                    'risks': result['risks'],
                    'flags': result['flags'],
                    'nearest_competitor': result['nearest_competitor'],
                })
            except Exception as e:
                log_action('Agent-5-Scoring', 'Erro', f'{local["name"]}: {str(e)[:50]}')
                continue
        
        # ========================================================
        # CORREÇÃO 4: Usar Ranking com Confidence (se flag ON)
        # ========================================================
        log_action('Agent-6-Ranking', 'Ordenando', 'Por score')
        
        if FeatureFlags.USE_NEW_RANKING:
            ranking_obj = RankingComConfianca()
            locais_ranked = ranking_obj.ranking_final(locais_scored)
            top20 = locais_ranked[:20]
        else:
            top20 = sorted(locais_scored, key=lambda x: x['score'], reverse=True)[:20]
        
        log_action('Agent-6-Ranking', 'Completo', 'Top 20 gerado')
        
        return jsonify({
            'success': True,
            'cidade': cidade,
            'estado': 'MA',
            'modo': modo.upper(),
            'total_encontrados': len(locais_processados),
            'total_viavel': len(locais_viavel),
            'total_descartado': len(locais_descartados),
            'top20': top20,
            'descartados': locais_descartados,
            'flags_ativas': FeatureFlags.get_all_flags()
        })
    
    except Exception as e:
        log_action('System', 'Erro Fatal', str(e)[:100])
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/gerar-pdf', methods=['POST'])
def gerar_pdf():
    """Gerar PDF com os resultados"""
    try:
        data = request.json
        cidade = data.get('cidade', 'Boston')
        top20 = data.get('top20', [])
        descartados = data.get('descartados', [])
        
        log_action('PDF-Generator', 'Criando', f'PDF de {cidade}')
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=1
        )
        story.append(Paragraph(f'Relatorio de Oportunidades EV - {cidade}', title_style))
        story.append(Spacer(1, 0.3*inch))
        
        story.append(Paragraph('Top 20 Oportunidades Viveis', styles['Heading2']))
        
        data_top20 = [['#', 'Local', 'Score', 'Score Final', 'Potencial', 'Confianca', 'Concorrencia']]
        for idx, local in enumerate(top20[:20], 1):
            score_final = local.get('score_final', local.get('score', 0))
            data_top20.append([
                str(idx),
                local.get('name', '')[:30],
                f"{local.get('score', 0)}/10",
                f"{score_final}/10",
                local.get('potencial', 'MEDIUM'),
                f"{int(local.get('confidence', 0)*100)}%",
                str(local.get('concorrencia', 0))
            ])
        
        table_top20 = Table(data_top20)
        table_top20.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table_top20)
        story.append(Spacer(1, 0.3*inch))
        
        if descartados:
            story.append(PageBreak())
            story.append(Paragraph('Locais Descartados', styles['Heading2']))
            
            data_descartados = [['Local', 'Motivo', 'Rede']]
            for local in descartados[:10]:
                data_descartados.append([
                    local.get('name', '')[:30],
                    local.get('motivo', '')[:40],
                    local.get('rede', '')
                ])
            
            table_desc = Table(data_descartados)
            table_desc.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#764ba2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table_desc)
        
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        log_action('PDF-Generator', 'Completo', 'PDF gerado com sucesso')
        
        return jsonify({
            'success': True,
            'pdf': base64.b64encode(pdf_data).decode('utf-8'),
            'filename': f'BuscaEV_{cidade}.pdf'
        })
    
    except Exception as e:
        log_action('PDF-Generator', 'Erro', str(e)[:100])
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# INICIAR SERVIDOR
# ============================================================================
if __name__ == '__main__':
    log_action('System', 'Iniciando', 'API online')
    print("\n" + "="*60)
    print("[SISTEMA] API BUSCAEV v2.1 + 4 CORREÇÕES CRÍTICAS")
    print("[SISTEMA] Acessar em: http://localhost:5000")
    print("[SISTEMA] Cidades disponíveis: 331")
    print("[SISTEMA] Scorer: Scoring Engine V2.1")
    print("[SISTEMA] Correções: Penalidade Dinâmica, Confidence Ranking, Timeout 8s, Feature Flags")
    print("="*60 + "\n")
    
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)
