"""
MassGIS Service
===============
Busca informações de proprietários e parcelas usando a API MassGIS
(Massachusetts Geographic Information System)

Integra dados de propriedade aos resultados de scoring.
"""

import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class MassGISService:
    """Acessa dados públicos de propriedades em Massachusetts via MassGIS"""
    
    # MassGIS endpoints (públicos, sem autenticação necessária)
    BASE_URL = "https://maps.massgis.state.ma.us/arcgis/rest/services"
    
    # Layers disponíveis no MassGIS
    PARCEL_SERVICE = f"{BASE_URL}/MassGIS/MassGIS_Data/FeatureServer"
    PROPERTY_LAYER = "32"  # Parcels layer ID
    
    def __init__(self):
        """Inicializa o serviço MassGIS"""
        self.session = requests.Session()
        self.session.timeout = 10
    
    def buscar_parcela_por_coordenadas(self, lat: float, lng: float) -> Optional[Dict]:
        """
        Busca informações da parcela usando latitude/longitude
        
        Args:
            lat: Latitude
            lng: Longitude
        
        Returns:
            Dict com informações da parcela ou None se não encontrado
            {
                'parcel_id': str,
                'address': str,
                'town': str,
                'owner': str (se disponível),
                'area_sqft': float,
                'zone': str (se disponível),
                'raw_response': dict (resposta completa da API)
            }
        """
        try:
            logger.info(f"Buscando parcela em {lat}, {lng}")
            
            # Query com geometry (ponto)
            params = {
                'geometry': f'{{"x":{lng},"y":{lat}}}',
                'geometryType': 'esriGeometryPoint',
                'inSR': '4326',  # WGS84
                'spatialRel': 'esriSpatialRelIntersects',
                'outFields': '*',
                'returnGeometry': 'true',
                'f': 'json'
            }
            
            url = f"{self.PARCEL_SERVICE}/{self.PROPERTY_LAYER}/query"
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Processar resultado
            if data.get('features') and len(data['features']) > 0:
                feature = data['features'][0]
                attributes = feature.get('attributes', {})
                
                # Normalizar campos (variam por versão do MassGIS)
                parcela = {
                    'parcel_id': attributes.get('PARCEL_ID') or attributes.get('OBJECTID'),
                    'address': attributes.get('FULL_ADDRESS') or attributes.get('ADDRESS'),
                    'town': attributes.get('TOWN'),
                    'owner': attributes.get('OWNER') or attributes.get('OWNER_NAME'),
                    'area_sqft': attributes.get('SHAPE_Area'),
                    'zone': attributes.get('ZONE'),
                    'use_code': attributes.get('USE_CODE') or attributes.get('LU_CODE'),
                    'raw_response': attributes
                }
                
                logger.info(f"Parcela encontrada: {parcela['address']}")
                return parcela
            
            logger.warning(f"Nenhuma parcela encontrada em {lat}, {lng}")
            return None
        
        except requests.RequestException as e:
            logger.error(f"Erro ao buscar parcela: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado em buscar_parcela_por_coordenadas: {e}")
            return None
    
    def buscar_por_endereco(self, endereco: str, cidade: str = "") -> Optional[Dict]:
        """
        Busca parcela por endereço (menos preciso que por coords)
        
        Args:
            endereco: Endereço da propriedade
            cidade: Cidade (opcional, melhora resultado)
        
        Returns:
            Dict com informações ou None
        """
        try:
            query = endereco
            if cidade:
                query += f", {cidade}"
            
            logger.info(f"Buscando por endereço: {query}")
            
            params = {
                'where': f"FULL_ADDRESS LIKE '%{endereco}%'",
                'outFields': '*',
                'returnGeometry': 'true',
                'f': 'json'
            }
            
            url = f"{self.PARCEL_SERVICE}/{self.PROPERTY_LAYER}/query"
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('features') and len(data['features']) > 0:
                feature = data['features'][0]
                attributes = feature.get('attributes', {})
                
                return {
                    'parcel_id': attributes.get('PARCEL_ID'),
                    'address': attributes.get('FULL_ADDRESS'),
                    'town': attributes.get('TOWN'),
                    'owner': attributes.get('OWNER'),
                    'area_sqft': attributes.get('SHAPE_Area'),
                    'raw_response': attributes
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Erro ao buscar por endereço: {e}")
            return None
    
    def enriquecer_locacao(self, locacao_dict: Dict) -> Dict:
        """
        Enriquece dados de locação com info do MassGIS
        
        Args:
            locacao_dict: Dict com dados básicos (deve ter 'lat', 'lng', 'address')
        
        Returns:
            Dict enriquecido com dados do MassGIS
        """
        try:
            parcela = self.buscar_parcela_por_coordenadas(
                locacao_dict['lat'],
                locacao_dict['lng']
            )
            
            if parcela:
                locacao_dict['massgis'] = {
                    'parcel_id': parcela['parcel_id'],
                    'owner': parcela['owner'],
                    'area_sqft': parcela['area_sqft'],
                    'town': parcela['town'],
                    'zone': parcela['zone'],
                    'use_code': parcela['use_code']
                }
            else:
                locacao_dict['massgis'] = None
            
            return locacao_dict
        
        except Exception as e:
            logger.error(f"Erro ao enriquecer locação: {e}")
            locacao_dict['massgis'] = None
            return locacao_dict
    
    def validar_zona_para_ev(self, zone_code: str) -> Dict:
        """
        Valida se a zona permite instalação de carregadores EV
        
        Args:
            zone_code: Código de zoneamento (ex: "C-2", "R-1")
        
        Returns:
            Dict com informações de compatibilidade
            {
                'compatible': bool,
                'notes': str,
                'restrictions': [str]
            }
        """
        # Simplificado - em produção, consultar código zoning local
        commercial_zones = ['C', 'B', 'Commercial', 'Business', 'Mixed']
        parking_zones = ['P', 'Parking']
        industrial_zones = ['I', 'Industrial']
        
        if not zone_code:
            return {
                'compatible': None,
                'notes': 'Zone information not available',
                'restrictions': []
            }
        
        zone_upper = zone_code.upper()
        
        # Compatibilidade
        is_commercial = any(z in zone_upper for z in commercial_zones)
        is_parking = any(z in zone_upper for z in parking_zones)
        is_industrial = any(z in zone_upper for z in industrial_zones)
        
        if is_parking or is_commercial or is_industrial:
            return {
                'compatible': True,
                'notes': f'Zone {zone_code} typically allows EV charging infrastructure',
                'restrictions': []
            }
        else:
            return {
                'compatible': False,
                'notes': f'Zone {zone_code} may have restrictions. Verify with local planning department.',
                'restrictions': ['Potential zoning variance required']
            }
    
    def calcular_taxa_propriedade(self, area_sqft: float, town: str = "") -> Optional[float]:
        """
        Estima taxa de propriedade annual (simplificado)
        
        Args:
            area_sqft: Área em sqft
            town: Cidade (opcional, para dados mais precisos)
        
        Returns:
            Valor estimado em USD ou None
        """
        try:
            if not area_sqft or area_sqft <= 0:
                return None
            
            # Taxa média de MA: ~1.20% do valor avaliado
            # Valor por sqft: ~$150-300 (varia muito por região)
            
            valor_por_sqft = 200  # Estimativa média
            valor_propriedade = area_sqft * valor_por_sqft
            taxa_annual = valor_propriedade * 0.012  # 1.2% média MA
            
            return round(taxa_annual, 2)
        
        except Exception as e:
            logger.error(f"Erro ao calcular taxa de propriedade: {e}")
            return None


class PropertyOwnerLookup:
    """Lookup de proprietários de imóveis"""
    
    # Base de dados públicos (simplificada para demo)
    # Em produção, integraria com Assessor's Offices locais
    
    PUBLIC_RECORDS_ENDPOINTS = {
        'Boston': 'https://data.boston.gov/api',
        'Cambridge': 'https://data.cambridgema.gov/api',
        'Worcester': 'https://data.worcestermass.gov/api',
        # ... adicionar mais cidades
    }
    
    @staticmethod
    def buscar_owner_info(parcel_id: str, town: str) -> Optional[Dict]:
        """
        Busca informações de proprietário via records públicos
        
        Args:
            parcel_id: ID da parcela
            town: Cidade
        
        Returns:
            Dict com info de proprietário ou None
        """
        try:
            # Demo: simular resposta
            # Em produção: chamar API de assessor's office da cidade
            
            logger.info(f"Buscando owner para parcel {parcel_id} em {town}")
            
            return {
                'name': '[Property Owner Name]',
                'phone': '[Contact Phone]',
                'email': '[Contact Email]',
                'address': '[Mailing Address]',
                'contact_status': 'To be verified',
                'last_updated': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Erro ao buscar info de proprietário: {e}")
            return None
    
    @staticmethod
    def gerar_lista_contatos(locacoes_list: List[Dict]) -> List[Dict]:
        """
        Gera lista de contatos para proprietários
        
        Args:
            locacoes_list: Lista de locações com dados de parcel
        
        Returns:
            Lista de dicts com informações de contato
        """
        contatos = []
        
        for locacao in locacoes_list:
            if locacao.get('massgis'):
                contato = {
                    'location': locacao['name'],
                    'address': locacao['address'],
                    'owner': locacao['massgis'].get('owner', 'Unknown'),
                    'parcel_id': locacao['massgis'].get('parcel_id'),
                    'phone': '[To be researched]',
                    'email': '[To be researched]'
                }
                contatos.append(contato)
        
        return contatos
