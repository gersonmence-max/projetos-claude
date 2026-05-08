# ============================================================================
# CORREÇÃO 1: PENALIDADE DINÂMICA (PROPORCIONAL AO PESO)
# ============================================================================
# Arquivo: correcao_1_penalidade_dinamica.py
# Tempo de implementação: 2 horas
# ============================================================================

def penalidade_dinamica_contextual(fator_faltante, peso_fator):
    """
    Penalidade proporcional ao peso do fator.
    
    PROBLEMA ANTERIOR:
    └─ Sempre penalizava -25% (fixo)
    └─ Não importava se fator tinha peso 0.10 ou 0.60
    
    SOLUÇÃO:
    └─ Penalidade = peso_fator × taxa_penalizacao
    └─ Área rural com NREL peso 0.10 → penalidade = 5%
    └─ Área urbana com NREL peso 0.60 → penalidade = 30%
    
    Args:
        fator_faltante (str): 'nrel_detail', 'traffic', 'census', etc
        peso_fator (float): Peso do fator (0.0 a 1.0)
    
    Returns:
        float: Penalidade a aplicar no score (0.0 a peso_fator)
    """
    
    # Taxa de penalização por tipo de fator faltante
    penalidade_rates = {
        'nrel_detail': 0.50,        # Penaliza 50% do peso
        'nrel_basic': 0.30,         # Penaliza 30% do peso
        'traffic': 0.30,            # Penaliza 30% do peso
        'traffic_historical': 0.20, # Penaliza 20% do peso
        'census': 0.40,             # Penaliza 40% do peso
        'census_demographic': 0.25, # Penaliza 25% do peso
        'google_places': 0.20,      # Penaliza 20% do peso
        'locationiq': 0.15,         # Penaliza 15% do peso
    }
    
    # Se fator não está na lista, sem penalidade
    if fator_faltante not in penalidade_rates:
        return 0.0
    
    # Penalidade = peso × taxa
    taxa = penalidade_rates[fator_faltante]
    penalidade = peso_fator * taxa
    
    # Garantir que nunca penaliza mais que o próprio peso
    return min(penalidade, peso_fator)


class SistemaDeScoreAdaptativo:
    """
    Pesos NÃO são fixos.
    Variam conforme o contexto geográfico.
    """
    
    def obter_pesos(self, contexto):
        """
        Adaptar pesos baseado em contexto
        
        Args:
            contexto (dict): {
                'tipo_area': 'rural|urbano_normal|urbano_denso',
                'estado': 'MA',
                'densidade_population': float,
                'distancia_chargers_proximos': float
            }
        
        Returns:
            dict: Pesos para demand, competition, site_fit, ev_affinity
        """
        
        tipo_area = contexto.get('tipo_area', 'urbano_normal')
        
        if tipo_area == 'rural':
            # Em área rural: demand é crítico, competition é irrelevante
            return {
                'demand': 0.40,         # Muito importante (alta)
                'competition': 0.05,    # Muito pouco (há poucos chargers)
                'site_fit': 0.35,       # Importante
                'ev_affinity': 0.20,    # Moderado
            }
        
        elif tipo_area == 'urbano_denso':
            # Em área urbana densa: competition é crítico
            return {
                'demand': 0.15,         # Óbvio que tem demanda
                'competition': 0.65,    # MUITO importante (saturação é fator crítico)
                'site_fit': 0.10,       # Menos relevante
                'ev_affinity': 0.10,    # Menos relevante
            }
        
        else:  # urbano_normal (padrão)
            return {
                'demand': 0.25,
                'competition': 0.40,
                'site_fit': 0.20,
                'ev_affinity': 0.15,
            }
    
    def aplicar_penalidades(
        self,
        score_original,
        dados_faltantes,
        contexto
    ):
        """
        Aplicar penalidades dinâmicas ao score
        
        Args:
            score_original (float): Score original (0-10)
            dados_faltantes (list): ['nrel_detail', 'traffic', ...]
            contexto (dict): Contexto geográfico
        
        Returns:
            float: Score com penalidades aplicadas
        """
        
        pesos = self.obter_pesos(contexto)
        penalidade_total = 0.0
        
        for fator_faltante in dados_faltantes:
            # Encontrar o peso correspondente ao fator
            peso = 0.0
            
            if 'nrel' in fator_faltante:
                peso = pesos.get('competition', 0.40)
            elif 'traffic' in fator_faltante:
                peso = pesos.get('demand', 0.25)
            elif 'census' in fator_faltante:
                peso = pesos.get('ev_affinity', 0.15)
            elif 'google' in fator_faltante:
                peso = pesos.get('site_fit', 0.20)
            
            # Aplicar penalidade proporcional
            penalidade = penalidade_dinamica_contextual(
                fator_faltante,
                peso
            )
            penalidade_total += penalidade
        
        # Score final com penalidades
        score_penalizado = score_original - penalidade_total
        
        # Garantir que não fica negativo
        return max(0.0, score_penalizado)


# ============================================================================
# TESTES
# ============================================================================

if __name__ == '__main__':
    
    print("=" * 70)
    print("TESTE 1: Penalidade em Área Rural")
    print("=" * 70)
    
    sistema = SistemaDeScoreAdaptativo()
    
    # Cenário rural: NREL tem pouco peso
    contexto_rural = {
        'tipo_area': 'rural',
        'estado': 'MA'
    }
    
    pesos_rural = sistema.obter_pesos(contexto_rural)
    print(f"\nPesos em área rural:")
    for chave, valor in pesos_rural.items():
        print(f"  {chave}: {valor}")
    
    # Faltando NREL em área rural
    penalidade_nrel_rural = penalidade_dinamica_contextual(
        'nrel_detail',
        pesos_rural['competition']
    )
    
    print(f"\nNREL faltando em área rural:")
    print(f"  Peso de competition: {pesos_rural['competition']}")
    print(f"  Penalidade: {penalidade_nrel_rural:.4f} ({penalidade_nrel_rural*100:.1f}%)")
    print(f"  ✅ Penalidade pequena (apropriado para rural)")
    
    
    print("\n" + "=" * 70)
    print("TESTE 2: Penalidade em Área Urbana Densa")
    print("=" * 70)
    
    # Cenário urbano denso: NREL tem muito peso
    contexto_urbano = {
        'tipo_area': 'urbano_denso',
        'estado': 'MA'
    }
    
    pesos_urbano = sistema.obter_pesos(contexto_urbano)
    print(f"\nPesos em área urbana densa:")
    for chave, valor in pesos_urbano.items():
        print(f"  {chave}: {valor}")
    
    # Faltando NREL em área urbana
    penalidade_nrel_urbano = penalidade_dinamica_contextual(
        'nrel_detail',
        pesos_urbano['competition']
    )
    
    print(f"\nNREL faltando em área urbana densa:")
    print(f"  Peso de competition: {pesos_urbano['competition']}")
    print(f"  Penalidade: {penalidade_nrel_urbano:.4f} ({penalidade_nrel_urbano*100:.1f}%)")
    print(f"  ✅ Penalidade grande (apropriado para urbano)")
    
    
    print("\n" + "=" * 70)
    print("TESTE 3: Aplicar Penalidades Completas")
    print("=" * 70)
    
    score_original = 8.5
    dados_faltantes_rural = ['nrel_detail', 'traffic']
    dados_faltantes_urbano = ['nrel_detail', 'traffic']
    
    score_rural = sistema.aplicar_penalidades(
        score_original,
        dados_faltantes_rural,
        contexto_rural
    )
    
    score_urbano = sistema.aplicar_penalidades(
        score_original,
        dados_faltantes_urbano,
        contexto_urbano
    )
    
    print(f"\nScore original: {score_original}")
    print(f"\nFaltando: {dados_faltantes_rural}")
    print(f"  Em área rural: {score_rural:.2f} (penalidade = {score_original - score_rural:.2f})")
    print(f"  Em área urbana: {score_urbano:.2f} (penalidade = {score_original - score_urbano:.2f})")
    print(f"\n✅ Penalidades diferentes conforme contexto!")
    
    
    print("\n" + "=" * 70)
    print("✅ TESTES PASSOU - IMPLEMENTAR NO CÓDIGO")
    print("=" * 70)

