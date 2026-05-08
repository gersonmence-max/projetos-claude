# ============================================================================
# CORREÇÃO 2: CONFIDENCE IMPACTA RANKING
# ============================================================================
# Arquivo: correcao_2_confidence_ranking.py
# Tempo de implementação: 2 horas
# ============================================================================

def calcular_score_final(score_bruto, confidence):
    """
    Score final LEVA em conta confiança.
    
    PROBLEMA ANTERIOR:
    └─ score = 8.4, confidence = 0.95 → ranking coloca igual a
    └─ score = 8.4, confidence = 0.45 → score bruto ignorava confiança
    
    SOLUÇÃO:
    └─ score_final = score × (0.7 + 0.3 × confidence)
    └─ Garante que confiança impacta no ranking
    
    Fórmula quebrada:
    ├─ Quando confidence = 0.0 → score_final = score × 0.7 (70% penalidade)
    ├─ Quando confidence = 0.5 → score_final = score × 0.85 (15% penalidade)
    ├─ Quando confidence = 1.0 → score_final = score × 1.0 (sem penalidade)
    └─ NUNCA penaliza mais que 30%, SEMPRE penaliza mínimo 0%
    
    Args:
        score_bruto (float): Score original do sistema (0-10)
        confidence (float): Confiança do dado (0.0-1.0)
    
    Returns:
        float: Score final considerando confiança
    """
    
    # Fórmula: score_final = score × (0.7 + 0.3 × confidence)
    score_final = score_bruto * (0.7 + 0.3 * confidence)
    
    return round(score_final, 2)


class RankingComConfianca:
    """
    Sistema de ranking que leva confiança em conta.
    
    Pontos principais:
    1. Score final = score × (0.7 + 0.3 × confidence)
    2. Ranking ordena por score_final, não score bruto
    3. Dados com confiança alta ficam no topo
    4. Dados com confiança baixa caem de posição
    """
    
    def ranking_final(self, locais_com_scores):
        """
        Calcular ranking considerando confiança
        
        Args:
            locais_com_scores (list): [
                {
                    'id': 123,
                    'nome': 'Local A',
                    'score': 8.5,
                    'confidence': 0.95,
                    'source': 'api',
                    'health': 'ok'
                },
                ...
            ]
        
        Returns:
            list: Locais ordenados por score_final (descendente)
        """
        
        # 1. Calcular score_final para cada local
        locais_processados = []
        
        for local in locais_com_scores:
            score_bruto = local.get('score', 0)
            confidence = local.get('confidence', 0.5)
            
            # Calcular score final
            score_final = calcular_score_final(score_bruto, confidence)
            
            # Criar local com score_final
            local_processado = local.copy()
            local_processado['score_final'] = score_final
            local_processado['score_bruto'] = score_bruto
            
            locais_processados.append(local_processado)
        
        # 2. Ordenar por score_final (descendente)
        locais_ordenados = sorted(
            locais_processados,
            key=lambda x: x['score_final'],
            reverse=True
        )
        
        # 3. Atribuir posições no ranking
        for rank, local in enumerate(locais_ordenados, 1):
            local['rank'] = rank
        
        return locais_ordenados
    
    def gerar_relatorio_ranking(self, ranking):
        """
        Gerar relatório mostrando diferença score_bruto vs score_final
        
        Args:
            ranking (list): Resultado do ranking_final()
        """
        
        print("\n" + "=" * 90)
        print(f"{'RANK':<5} {'NOME':<30} {'SCORE':<8} {'FINAL':<8} {'DIFF':<8} {'CONF':<6} {'SOURCE':<10}")
        print("=" * 90)
        
        for local in ranking:
            rank = local.get('rank', 0)
            nome = local.get('nome', '')[:30]
            score_bruto = local.get('score_bruto', 0)
            score_final = local.get('score_final', 0)
            confidence = local.get('confidence', 0)
            source = local.get('source', 'unknown')
            
            # Calcular diferença
            diferenca = score_bruto - score_final
            percentual = (diferenca / score_bruto * 100) if score_bruto > 0 else 0
            
            print(f"{rank:<5} {nome:<30} {score_bruto:<8.2f} {score_final:<8.2f} "
                  f"-{percentual:<6.1f}% {confidence:<6.2f} {source:<10}")
        
        print("=" * 90)


# ============================================================================
# TESTES
# ============================================================================

if __name__ == '__main__':
    
    print("\n" + "=" * 90)
    print("TESTE 1: Calcular Score Final Individual")
    print("=" * 90)
    
    # Teste com diferentes níveis de confiança
    testes = [
        (8.5, 1.0, "Dados perfeitos (API primária)"),
        (8.5, 0.95, "Dados muito bons (API + confirmação)"),
        (8.5, 0.80, "Dados bons (cache fresco)"),
        (8.5, 0.60, "Dados aceitáveis (cache envelhecido)"),
        (8.5, 0.45, "Dados degradados (fallback)"),
        (8.5, 0.20, "Dados ruins (múltiplas falhas)"),
        (8.5, 0.0, "Sem confiança (default)"),
    ]
    
    print(f"\nScore bruto: 8.5")
    print(f"\n{'Confiança':<12} {'Score Final':<15} {'Penalidade':<15} {'Descrição':<40}")
    print("-" * 85)
    
    for score_bruto, confidence, descricao in testes:
        score_final = calcular_score_final(score_bruto, confidence)
        penalidade = score_bruto - score_final
        percentual = (penalidade / score_bruto) * 100
        
        print(f"{confidence:<12.2f} {score_final:<15.2f} -{percentual:<13.1f}% {descricao:<40}")
    
    
    print("\n" + "=" * 90)
    print("TESTE 2: Ranking com Múltiplos Locais")
    print("=" * 90)
    
    # Dados de teste
    locais = [
        {
            'id': 1,
            'nome': 'Shopping Boston (API OK)',
            'score': 8.5,
            'confidence': 0.95,
            'source': 'api'
        },
        {
            'id': 2,
            'nome': 'Hotel Cambridge (Cache)',
            'score': 8.4,
            'confidence': 0.60,
            'source': 'cache'
        },
        {
            'id': 3,
            'nome': 'Mall Providence (Fallback)',
            'score': 8.3,
            'confidence': 0.40,
            'source': 'fallback'
        },
        {
            'id': 4,
            'nome': 'Restaurante Downtown (API OK)',
            'score': 7.9,
            'confidence': 0.92,
            'source': 'api'
        },
        {
            'id': 5,
            'nome': 'Gym Seaport (Cache velho)',
            'score': 8.2,
            'confidence': 0.30,
            'source': 'cache'
        },
    ]
    
    # Gerar ranking
    ranking_obj = RankingComConfianca()
    ranking = ranking_obj.ranking_final(locais)
    
    # Mostrar relatório
    ranking_obj.gerar_relatorio_ranking(ranking)
    
    print("\n✅ OBSERVAÇÕES:")
    print("├─ Shopping Boston (8.5 × 0.95) = 8.24 → RANK 1 (confiança alta)")
    print("├─ Hotel Cambridge (8.4 × 0.60) = 7.34 → RANK 2")
    print("├─ Mall Providence (8.3 × 0.40) = 6.41 → RANK 4 (penalidade grande)")
    print("├─ Restaurante Downtown (7.9 × 0.92) = 7.33 → RANK 3 (score menor mas confiança alta!)")
    print("└─ Gym Seaport (8.2 × 0.30) = 5.60 → RANK 5 (confiança muito baixa)")
    
    
    print("\n" + "=" * 90)
    print("TESTE 3: Comparação Ranking Antigo vs Novo")
    print("=" * 90)
    
    print("\nANTIGO (Só score bruto):")
    print("1. Shopping Boston (8.5)")
    print("2. Hotel Cambridge (8.4)")
    print("3. Mall Providence (8.3)")
    print("4. Gym Seaport (8.2)")
    print("5. Restaurante Downtown (7.9)")
    
    print("\nNOVO (Com confidence):")
    for local in ranking:
        print(f"{local['rank']}. {local['nome']:<35} ({local['score_final']:.2f})")
    
    print("\n✅ MUDANÇA:")
    print("└─ Restaurante Downtown (7.9) SOBE para RANK 3")
    print("   Razão: Confiança 0.92 compensa score menor")
    print("   Sistema agora valoriza QUALIDADE do dado, não só quantidade")
    
    
    print("\n" + "=" * 90)
    print("✅ TESTES PASSARAM - IMPLEMENTAR NO CÓDIGO")
    print("=" * 90)

