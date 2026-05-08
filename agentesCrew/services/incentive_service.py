"""
Incentive Service
=================
Calcula incentivos federais, estaduais e municipais disponíveis
para instalação de carregadores EV em Massachusetts.

Inclui:
- Federal Tax Credits (IRA)
- Massachusetts State Rebates
- Municipal Incentives
- Grant Opportunities
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class IncentiveCalculator:
    """Calcula incentivos disponíveis para projetos EV em MA"""
    
    # FEDERAL INCENTIVES (IRA - Inflation Reduction Act)
    FEDERAL_CREDITS = {
        'dcfc': {
            'max_credit': 100000,  # $100k por station
            'cost_share': 0.30,  # 30% dos custos
            'description': 'Federal Tax Credit for DCFC stations',
            'program': 'IRA Section 30C'
        },
        'level2': {
            'max_credit': 100000,
            'cost_share': 0.30,
            'description': 'Federal Tax Credit for Level 2 stations',
            'program': 'IRA Section 30C'
        }
    }
    
    # MASSACHUSETTS STATE INCENTIVES
    MA_STATE_INCENTIVES = {
        'rebate_dcfc': {
            'name': 'MOR-EV DCFC Rebate',
            'amount': 25000,  # $25k per DCFC
            'notes': 'Make-Ready and Operation Rebate for DCFC',
            'program': 'MOR-EV',
            'availability': 'Active'
        },
        'rebate_level2': {
            'name': 'MOR-EV Level 2 Rebate',
            'amount': 2500,  # $2.5k per Level 2
            'notes': 'Make-Ready and Operation Rebate for Level 2',
            'program': 'MOR-EV',
            'availability': 'Active'
        },
        'cef_grant': {
            'name': 'Clean Energy Fund Grant',
            'amount_max': 500000,
            'notes': 'Competitive grant for charging infrastructure',
            'program': 'MA Clean Energy Fund',
            'availability': 'Periodic (check for open cycles)',
            'notes_detail': 'Typically requires non-profit or municipal applicant'
        },
        'cwf_grant': {
            'name': 'Climate and Workforce Fund',
            'amount_max': 250000,
            'notes': 'Infrastructure + workforce training',
            'program': 'MA CWF',
            'availability': 'Periodic'
        }
    }
    
    # MUNICIPAL INCENTIVES (exemplos por cidade)
    MUNICIPAL_INCENTIVES = {
        'Boston': {
            'incentive': 'EV Charging Rebate',
            'amount': 5000,
            'details': 'Boston encourages EV infrastructure development',
            'contact': 'Boston Planning & Development Agency'
        },
        'Cambridge': {
            'incentive': 'Net Zero Action Plan Support',
            'amount': 3000,
            'details': 'Municipalities aligned with climate goals get support',
            'contact': 'Cambridge Community Development'
        },
        'Somerville': {
            'incentive': 'EV Infrastructure Grants',
            'amount': 4000,
            'details': 'Part of Somerville climate commitment',
            'contact': 'Somerville Sustainability Office'
        }
    }
    
    def calcular_incentivos_totais(self, locacao_dict: Dict, charger_type: str = 'both') -> Dict:
        """
        Calcula todos os incentivos disponíveis para um local
        
        Args:
            locacao_dict: Dict com dados da location (deve incluir 'type' e cidade implícita em 'address')
            charger_type: 'dcfc', 'level2', ou 'both'
        
        Returns:
            Dict com breakdown completo de incentivos
            {
                'total_incentive': float,
                'federal': {...},
                'state': {...},
                'municipal': {...},
                'notes': str,
                'sources': [...]
            }
        """
        try:
            resultado = {
                'location': locacao_dict.get('name'),
                'analysis_date': datetime.now().isoformat(),
                'federal': {},
                'state': {},
                'municipal': {},
                'total_incentive': 0,
                'notes': [],
                'sources': []
            }
            
            # FEDERAL
            if charger_type in ['dcfc', 'both']:
                fed_dcfc = self._calcular_federal_dcfc(locacao_dict)
                resultado['federal']['dcfc'] = fed_dcfc
                resultado['total_incentive'] += fed_dcfc['estimated_amount']
            
            if charger_type in ['level2', 'both']:
                fed_l2 = self._calcular_federal_level2(locacao_dict)
                resultado['federal']['level2'] = fed_l2
                resultado['total_incentive'] += fed_l2['estimated_amount']
            
            # STATE
            if charger_type in ['dcfc', 'both']:
                state_dcfc = self._calcular_state_dcfc(locacao_dict)
                resultado['state']['dcfc'] = state_dcfc
                resultado['total_incentive'] += state_dcfc['estimated_amount']
            
            if charger_type in ['level2', 'both']:
                state_l2 = self._calcular_state_level2(locacao_dict)
                resultado['state']['level2'] = state_l2
                resultado['total_incentive'] += state_l2['estimated_amount']
            
            # MUNICIPAL
            municipal = self._calcular_municipal(locacao_dict)
            resultado['municipal'] = municipal
            resultado['total_incentive'] += municipal['estimated_amount']
            
            # Adicionar fontes
            resultado['sources'] = self._listar_fontes()
            
            return resultado
        
        except Exception as e:
            logger.error(f"Erro ao calcular incentivos: {e}")
            return {
                'error': str(e),
                'location': locacao_dict.get('name'),
                'analysis_date': datetime.now().isoformat()
            }
    
    def _calcular_federal_dcfc(self, locacao_dict: Dict) -> Dict:
        """Calcula incentivos federais para DCFC"""
        # Custo típico de DCFC: $50-150k
        custo_estimado = 100000  # $100k média
        
        credit = self.FEDERAL_CREDITS['dcfc']
        incentive_amount = min(custo_estimado * credit['cost_share'], credit['max_credit'])
        
        return {
            'program': credit['program'],
            'description': credit['description'],
            'estimated_cost': custo_estimado,
            'cost_share': credit['cost_share'],
            'estimated_amount': incentive_amount,
            'max_available': credit['max_credit'],
            'details': 'IRA Section 30C provides 30% tax credit, up to $100k per site',
            'status': 'ACTIVE',
            'notes': [
                'Requires prevailing wage and registered apprenticeship',
                'Can be transferred to third party for immediate rebate',
                'Energy audits may provide additional credits'
            ]
        }
    
    def _calcular_federal_level2(self, locacao_dict: Dict) -> Dict:
        """Calcula incentivos federais para Level 2"""
        custo_estimado = 4000  # $4k por charger
        
        credit = self.FEDERAL_CREDITS['level2']
        incentive_amount = min(custo_estimado * credit['cost_share'], credit['max_credit'])
        
        return {
            'program': credit['program'],
            'description': credit['description'],
            'estimated_cost': custo_estimado,
            'cost_share': credit['cost_share'],
            'estimated_amount': incentive_amount,
            'max_available': credit['max_credit'],
            'details': 'IRA Section 30C provides 30% tax credit for Level 2 infrastructure',
            'status': 'ACTIVE',
            'notes': [
                'Lower wage requirements than DCFC',
                'Can combine multiple Level 2 chargers',
                'Prevailing wage requirements apply'
            ]
        }
    
    def _calcular_state_dcfc(self, locacao_dict: Dict) -> Dict:
        """Calcula incentivos estaduais para DCFC"""
        mor_ev = self.MA_STATE_INCENTIVES['rebate_dcfc']
        
        return {
            'program': mor_ev['program'],
            'name': mor_ev['name'],
            'estimated_amount': mor_ev['amount'],
            'description': mor_ev['notes'],
            'status': mor_ev['availability'],
            'notes': [
                'MOR-EV program provides $25k per DCFC station',
                'Covers hardware, installation, and some make-ready costs',
                'Designed to reduce upfront capital costs',
                'Application required - typically competitive process'
            ]
        }
    
    def _calcular_state_level2(self, locacao_dict: Dict) -> Dict:
        """Calcula incentivos estaduais para Level 2"""
        mor_ev = self.MA_STATE_INCENTIVES['rebate_level2']
        
        return {
            'program': mor_ev['program'],
            'name': mor_ev['name'],
            'estimated_amount': mor_ev['amount'],
            'description': mor_ev['notes'],
            'status': mor_ev['availability'],
            'notes': [
                'MOR-EV program provides $2.5k per Level 2 charger',
                'Ideal for sites installing multiple chargers',
                'Lower barrier to entry than DCFC',
                'Application required'
            ]
        }
    
    def _calcular_municipal(self, locacao_dict: Dict) -> Dict:
        """Calcula incentivos municipais baseado na cidade"""
        address = locacao_dict.get('address', '')
        
        # Extrair cidade da address (simplificado)
        for cidade, incentive_data in self.MUNICIPAL_INCENTIVES.items():
            if cidade.lower() in address.lower():
                return {
                    'city': cidade,
                    'incentive': incentive_data['incentive'],
                    'estimated_amount': incentive_data['amount'],
                    'details': incentive_data['details'],
                    'contact': incentive_data['contact'],
                    'status': 'CHECK WITH CITY',
                    'notes': [
                        f'Contact {incentive_data["contact"]} for details',
                        'Eligibility may depend on property ownership',
                        'Some require commitment to job creation'
                    ]
                }
        
        # Default se cidade não encontrada
        return {
            'city': 'Unknown',
            'incentive': 'Local incentives vary by municipality',
            'estimated_amount': 2000,  # Estimativa conservadora
            'details': 'Most MA municipalities offer some level of EV support',
            'status': 'CONTACT LOCAL GOVERNMENT',
            'notes': [
                'Contact your municipal planning/development office',
                'Many towns have sustainability committees',
                'Check for zoning variance support'
            ]
        }
    
    def _listar_fontes(self) -> List[Dict]:
        """Retorna lista de fontes de informação"""
        return [
            {
                'name': 'IRS - Alternative Fuel Vehicle Refueling Property Credit',
                'url': 'https://www.irs.gov/newsroom/irs-offers-tax-credits-for-electric-vehicle-charging-infrastructure',
                'coverage': 'Federal'
            },
            {
                'name': 'MA MOR-EV Program',
                'url': 'https://www.mass.gov/guides/make-ready-and-operation-rebate-for-electric-vehicles-mor-ev',
                'coverage': 'State'
            },
            {
                'name': 'MA Clean Energy Center',
                'url': 'https://www.masscec.com/',
                'coverage': 'State'
            },
            {
                'name': 'U.S. Department of Energy - Charging Infrastructure',
                'url': 'https://www.energy.gov/eere/ev-charging',
                'coverage': 'Federal'
            }
        ]
    
    def gerar_relatorio_incentivos(self, locacao_dict: Dict) -> str:
        """
        Gera relatório textual de incentivos
        
        Args:
            locacao_dict: Dados da localização
        
        Returns:
            Texto formatado do relatório
        """
        incentivos = self.calcular_incentivos_totais(locacao_dict, 'both')
        
        relatorio = f"""
INCENTIVE ANALYSIS REPORT
========================
Location: {locacao_dict.get('name')}
Address: {locacao_dict.get('address')}
Analysis Date: {datetime.now().strftime('%Y-%m-%d')}

ESTIMATED TOTAL INCENTIVES: ${incentivos.get('total_incentive', 0):,.2f}

FEDERAL INCENTIVES (IRA Section 30C)
-----------------------------------
"""
        
        if 'dcfc' in incentivos.get('federal', {}):
            dcfc = incentivos['federal']['dcfc']
            relatorio += f"""
DC Fast Charging:
  • Estimated Available: ${dcfc.get('estimated_amount', 0):,.2f}
  • Program: {dcfc.get('program', 'N/A')}
  • Status: {dcfc.get('status', 'N/A')}
"""
        
        if 'level2' in incentivos.get('federal', {}):
            l2 = incentivos['federal']['level2']
            relatorio += f"""
Level 2 Charging:
  • Estimated Available: ${l2.get('estimated_amount', 0):,.2f}
  • Program: {l2.get('program', 'N/A')}
  • Status: {l2.get('status', 'N/A')}
"""
        
        relatorio += f"""
MASSACHUSETTS STATE INCENTIVES
-----------------------------
"""
        
        if 'dcfc' in incentivos.get('state', {}):
            state_dcfc = incentivos['state']['dcfc']
            relatorio += f"""
MOR-EV DCFC Program:
  • Estimated Available: ${state_dcfc.get('estimated_amount', 0):,.2f}
  • Status: {state_dcfc.get('status', 'N/A')}
"""
        
        if 'level2' in incentivos.get('state', {}):
            state_l2 = incentivos['state']['level2']
            relatorio += f"""
MOR-EV Level 2 Program:
  • Estimated Available: ${state_l2.get('estimated_amount', 0):,.2f}
  • Status: {state_l2.get('status', 'N/A')}
"""
        
        municipal = incentivos.get('municipal', {})
        relatorio += f"""
MUNICIPAL INCENTIVES
-------------------
City/Town: {municipal.get('city', 'Contact local government')}
Available Incentives: ${municipal.get('estimated_amount', 0):,.2f}
Status: {municipal.get('status', 'CHECK WITH CITY')}

NEXT STEPS
----------
1. Verify federal IRA eligibility (prevailing wage, apprenticeship)
2. Apply to MA MOR-EV program
3. Contact municipal government for local opportunities
4. Coordinate timing of applications
5. Track all expenditures for tax credit documentation

SOURCES FOR MORE INFORMATION
---------------------------
"""
        
        for fonte in incentivos.get('sources', []):
            relatorio += f"\n• {fonte['name']}: {fonte['url']}"
        
        return relatorio
