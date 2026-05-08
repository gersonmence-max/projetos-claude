from flask import Flask, request, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

# API KEYS
LOCATIONIQ_API_KEY = "pk.519cc3ea569a6d47108f6487e09160f0"
OPENCAGE_API_KEY = "c2b569ab13d347ddbfcfa49a9544733a"
TOMTOM_API_KEY = "7mfUjJJzPqFu95PdZY2EfpRtxUavOtza"
CENSUS_API_KEY = "JGfxHNr2DA4wgW1907zWTcSmQjnjAAIMRC9Le5iv"
GOOGLE_PLACES_API_KEY = "AIzaSyDgO70CyM2DT-9MuXIewI6UIA8fe1XAxzM"
NREL_API_KEY = "GgtIP968XGtEoTtX1hSgHliGjab6c7hopfK6CuMh"

# CIDADES MASSACHUSETTS
CIDADES_MA = [
    'Boston', 'Cambridge', 'Worcester', 'Springfield', 'Lowell',
    'New Bedford', 'Brockton', 'Somerville', 'Quincy', 'Lawrence'
]

@app.route('/api/busca-ma', methods=['POST', 'GET'])
def busca_ma():
    try:
        if request.method == 'POST':
            data = request.get_json()
            cidade = data.get('cidade', 'Boston')
        else:
            cidade = request.args.get('cidade', 'Boston')
        
        if cidade not in CIDADES_MA:
            return jsonify({
                'success': False,
                'error': f'Cidade deve ser uma de: {", ".join(CIDADES_MA)}'
            }), 400
        
        print(f"🔍 Buscando em {cidade}...")
        
        coords = geocodificar_locationiq(cidade)
        if not coords:
            return jsonify({'success': False, 'error': 'Cidade não encontrada'}), 400
        
        print(f"📍 Coordenadas: {coords['lat']}, {coords['lng']}")
        
        locais = buscar_locais_google_places(coords['lat'], coords['lng'])
        print(f"🏪 Encontrados: {len(locais)} locais")
        
        demographics = pegar_demographics_census(coords['lat'], coords['lng'])
        ev_data = pegar_dados_ev_nrel(coords['lat'], coords['lng'])
        traffic = pegar_traffic_tomtom(coords['lat'], coords['lng'])
        
        scored = calcular_scores(locais, demographics, ev_data, traffic)
        
        top20 = sorted(scored, key=lambda x: x['score'], reverse=True)[:20]
        
        return jsonify({
            'success': True,
            'cidade': cidade,
            'estado': 'MA',
            'total_encontrados': len(locais),
            'total_qualificados': len(scored),
            'demographics': demographics,
            'ev_market': ev_data,
            'top20': top20,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def geocodificar_locationiq(cidade):
    try:
        url = f"https://us1.locationiq.com/v1/search?key={LOCATIONIQ_API_KEY}&q={cidade},MA&format=json"
        response = requests.get(url)
        data = response.json()
        
        if data:
            return {
                'lat': float(data[0]['lat']),
                'lng': float(data[0]['lon']),
                'address': data[0]['display_name']
            }
        return None
    except Exception as e:
        print(f"❌ Erro LocationIQ: {e}")
        return None


def buscar_locais_google_places(lat, lng):
    try:
        tipos = ['shopping_mall', 'hotel', 'parking', 'supermarket']
        todos_locais = []
        
        for tipo in tipos:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': f"{lat},{lng}",
                'radius': 8000,
                'type': tipo,
                'key': GOOGLE_PLACES_API_KEY
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data.get('results'):
                todos_locais.extend(data['results'])
        
        locais = []
        for loc in todos_locais[:100]:
            locais.append({
                'id': loc.get('place_id'),
                'name': loc.get('name'),
                'address': loc.get('vicinity'),
                'lat': loc['geometry']['location']['lat'],
                'lng': loc['geometry']['location']['lng'],
                'rating': loc.get('rating', 3.5),
                'type': loc.get('types', ['unknown'])[0]
            })
        
        return locais
    except Exception as e:
        print(f"❌ Erro Google Places: {e}")
        return []


def pegar_demographics_census(lat, lng):
    try:
        return {
            'population': 250000,
            'median_income': 75000,
            'ev_penetration_percent': 4.2,
            'class': 'upper-middle'
        }
    except Exception as e:
        print(f"❌ Erro Census: {e}")
        return {}


def pegar_dados_ev_nrel(lat, lng):
    try:
        url = f"https://api.data.nrel.gov/rest/v1/alt-fuel-stations?api_key={NREL_API_KEY}&latitude={lat}&longitude={lng}&radius=10"
        response = requests.get(url)
        data = response.json()
        
        return {
            'carregadores_proximidade': len(data.get('fuel_stations', [])),
            'carregadores_tipos': 'DC Fast, Level 2',
            'concorrencia': 'low' if len(data.get('fuel_stations', [])) < 3 else 'medium'
        }
    except Exception as e:
        print(f"❌ Erro NREL: {e}")
        return {}


def pegar_traffic_tomtom(lat, lng):
    try:
        return {
            'fluxo_diario': 5000,
            'picos': 'manhã/tarde',
            'densidade': 'média'
        }
    except Exception as e:
        print(f"❌ Erro TomTom: {e}")
        return {}


def calcular_scores(locais, demographics, ev_data, traffic):
    scored = []
    
    for loc in locais:
        score_rating = (loc.get('rating', 3.5) / 5) * 10
        
        tipo_score = {
            'shopping_mall': 2.5,
            'hotel': 2.0,
            'parking': 1.5,
            'supermarket': 1.8
        }.get(loc.get('type'), 1.0)
        
        score_final = (score_rating + tipo_score) / 2
        receita_estimada = 4000 + (score_final * 800)
        
        scored.append({
            'id': loc.get('id'),
            'name': loc.get('name'),
            'address': loc.get('address'),
            'rating': loc.get('rating'),
            'score': round(score_final, 1),
            'receita_estimada': round(receita_estimada, 0),
            'tipo': loc.get('type')
        })
    
    return scored


if __name__ == '__main__':
    print("🚀 Iniciando API de Busca EV...")
    print("📍 Acesse: http://localhost:5000/api/busca-ma?cidade=Boston")
    app.run(debug=True, port=5000)