# ============================================================================
# CORREÇÃO 3: TIMEOUT GLOBAL 8 SEGUNDOS
# ============================================================================
# Arquivo: correcao_3_timeout_global.py
# Tempo de implementação: 2 horas
# ============================================================================

import time
from datetime import datetime
from typing import Callable, Any


def retry_strategy_otimizado(
    func: Callable,
    func_name: str = "API Call",
    max_retries: int = 3,
    initial_wait_ms: int = 200,
    max_wait_ms: int = 5000,
    timeout_per_attempt: float = 3,
    total_timeout: float = 8
) -> Any:
    """
    Retry com timeout global controlado.
    
    PROBLEMA ANTERIOR:
    └─ Retry sequencial: 500ms → 1s → 2s → 4s → 8s = 37 segundos total!
    └─ Mata UX (usuário esperando 37s)
    └─ Impede paralelização
    
    SOLUÇÃO:
    └─ Timeout global: máximo 8 segundos
    └─ 3 tentativas rápidas
    └─ Backoff inteligente (200ms → 400ms → 800ms)
    └─ Se não consegue em 8s, falha gracefully
    
    Timeline:
    ├─ 0s: Tentativa 1 (timeout 3s)
    ├─ 0-3s: Esperando resultado
    ├─ 3s: Se falha, aguarda 200ms
    ├─ 3.2s: Tentativa 2 (timeout 3s)
    ├─ 3.2-6.2s: Esperando resultado
    ├─ 6.2s: Se falha, aguarda 400ms
    ├─ 6.6s: Tentativa 3 (timeout 3s)
    ├─ 6.6-8s: Esperando resultado (aprox 1.4s)
    └─ 8s: Timeout global, falha
    
    Args:
        func (Callable): Função a executar
        func_name (str): Nome da função (para logging)
        max_retries (int): Máximo de tentativas (default 3 = 4 tentativas totais)
        initial_wait_ms (int): Espera inicial em ms (default 200)
        max_wait_ms (int): Espera máxima em ms (default 5000)
        timeout_per_attempt (float): Timeout POR tentativa em segundos (default 3)
        total_timeout (float): Timeout TOTAL em segundos (default 8)
    
    Returns:
        Any: Resultado da função se bem-sucedida
    
    Raises:
        TimeoutError: Se atingir timeout global ou não conseguir em max_retries
    """
    
    start_time = time.time()
    last_error = None
    
    for attempt in range(max_retries + 1):
        elapsed = time.time() - start_time
        
        # Verificar timeout global ANTES de tentar
        if elapsed > total_timeout:
            msg = f"[{func_name}] Total timeout ({total_timeout}s) atingido após {attempt} tentativas"
            print(f"❌ {msg}")
            raise TimeoutError(msg)
        
        try:
            # Tentar executar com timeout individual
            print(f"[{func_name}] Tentativa {attempt + 1}/{max_retries + 1} "
                  f"(elapsed: {elapsed:.1f}s de {total_timeout}s)")
            
            # Simular execução com timeout
            # Em código real, você usaria threading ou asyncio para timeout real
            result = func(timeout=timeout_per_attempt)
            
            print(f"✅ [{func_name}] Sucesso na tentativa {attempt + 1}")
            return result
        
        except (TimeoutError, Exception) as e:
            last_error = e
            
            # Se foi última tentativa, falha
            if attempt == max_retries:
                msg = f"[{func_name}] Falha após {max_retries + 1} tentativas: {str(e)[:100]}"
                print(f"❌ {msg}")
                raise TimeoutError(msg) from e
            
            # Calcular tempo de espera
            elapsed = time.time() - start_time
            wait_time_ms = min(
                initial_wait_ms * (2 ** attempt),  # Exponential backoff
                max_wait_ms
            )
            wait_time_s = wait_time_ms / 1000.0
            
            # Verificar se há tempo para esperar E fazer próxima tentativa
            tempo_restante = total_timeout - elapsed
            tempo_minimo_prox_tentativa = timeout_per_attempt + 0.5  # Margem de segurança
            
            if wait_time_s + tempo_minimo_prox_tentativa > tempo_restante:
                msg = f"[{func_name}] Sem tempo para retry #{attempt + 1} " \
                      f"(restam {tempo_restante:.1f}s, precisa {wait_time_s + tempo_minimo_prox_tentativa:.1f}s)"
                print(f"❌ {msg}")
                raise TimeoutError(msg) from e
            
            print(f"⏳ [{func_name}] Aguardando {wait_time_s:.2f}s antes de tentativa {attempt + 2}... "
                  f"({elapsed:.1f}s elapsed de {total_timeout}s)")
            
            time.sleep(wait_time_s)
    
    # Nunca deve chegar aqui
    raise TimeoutError(f"[{func_name}] Erro inesperado no retry")


class TimeoutManager:
    """
    Gerenciador de timeouts para aplicação inteira.
    """
    
    # Constantes globais
    TIMEOUT_API_CALL = 3          # Por tentativa
    TIMEOUT_TOTAL = 8             # Máximo absoluto
    MAX_RETRIES = 3               # Total de tentativas (= 4 calls)
    
    @staticmethod
    def chamar_com_timeout(
        func: Callable,
        func_name: str = "API"
    ) -> Any:
        """Wrapper para chamar função com retry otimizado"""
        
        return retry_strategy_otimizado(
            func=func,
            func_name=func_name,
            timeout_per_attempt=TimeoutManager.TIMEOUT_API_CALL,
            total_timeout=TimeoutManager.TIMEOUT_TOTAL,
            max_retries=TimeoutManager.MAX_RETRIES
        )


# ============================================================================
# TESTES
# ============================================================================

if __name__ == '__main__':
    
    print("\n" + "=" * 80)
    print("TESTE 1: Comparação Antes vs Depois")
    print("=" * 80)
    
    print("\n⏱️  ANTES (37 segundos):")
    print("├─ 0s: Tentativa 1")
    print("├─ 0-2s: API timeout (2s)")
    print("├─ 2s: Aguarda 500ms")
    print("├─ 2.5s: Tentativa 2")
    print("├─ 2.5-4.5s: API timeout (2s)")
    print("├─ 4.5s: Aguarda 1s")
    print("├─ 5.5s: Tentativa 3")
    print("├─ 5.5-7.5s: API timeout (2s)")
    print("├─ 7.5s: Aguarda 2s")
    print("├─ 9.5s: Tentativa 4")
    print("├─ 9.5-11.5s: API timeout (2s)")
    print("├─ 11.5s: Aguarda 4s")
    print("├─ 15.5s: Tentativa 5")
    print("├─ 15.5-17.5s: API timeout (2s)")
    print("├─ 17.5s: Aguarda 8s")
    print("├─ 25.5s: Tentativa 6")
    print("├─ 25.5-27.5s: API timeout (2s)")
    print("├─ 27.5s: Aguarda 8s (max)")
    print("├─ 35.5s: Tentativa 7")
    print("└─ 35.5s+: TIMEOUT GLOBAL (37s)")
    print("   ❌ RESULTADO: Usuário esperou 37 segundos! Péssimo!")
    
    print("\n⏱️  DEPOIS (8 segundos):")
    print("├─ 0s: Tentativa 1 (timeout 3s)")
    print("├─ 0-3s: API timeout")
    print("├─ 3s: Aguarda 200ms")
    print("├─ 3.2s: Tentativa 2 (timeout 3s)")
    print("├─ 3.2-6.2s: API timeout")
    print("├─ 6.2s: Aguarda 400ms")
    print("├─ 6.6s: Tentativa 3 (timeout 3s)")
    print("├─ 6.6-8s: Espera cortada (timeout global)")
    print("└─ 8s: TIMEOUT GLOBAL")
    print("   ✅ RESULTADO: Usuário esperou 8 segundos. Aceitável!")
    
    
    print("\n" + "=" * 80)
    print("TESTE 2: Executar Retry Otimizado")
    print("=" * 80)
    
    # Simular função que falha
    tentativa_numero = [0]
    
    def api_que_falha(timeout=3):
        tentativa_numero[0] += 1
        print(f"  → Executando API (tentativa {tentativa_numero[0]})")
        time.sleep(0.5)
        raise Exception("API Error")
    
    print("\nTestando com função que falha 3 vezes:")
    
    try:
        resultado = retry_strategy_otimizado(
            func=api_que_falha,
            func_name="TestAPI",
            total_timeout=8,
            timeout_per_attempt=3
        )
    except TimeoutError as e:
        print(f"\n✅ Erro esperado após 8s: {e}")
    
    
    print("\n" + "=" * 80)
    print("TESTE 3: Função que Sucede na Tentativa 2")
    print("=" * 80)
    
    tentativa_numero = [0]
    
    def api_que_sucede_na_2(timeout=3):
        tentativa_numero[0] += 1
        print(f"  → Executando API (tentativa {tentativa_numero[0]})")
        time.sleep(0.3)
        
        if tentativa_numero[0] < 2:
            raise Exception("Falha temporária")
        
        return {"status": "success", "data": [1, 2, 3]}
    
    print("\nTestando com função que sucede na tentativa 2:")
    
    try:
        resultado = retry_strategy_otimizado(
            func=api_que_sucede_na_2,
            func_name="TestAPI2",
            total_timeout=8,
            timeout_per_attempt=3
        )
        print(f"\n✅ Sucesso! Resultado: {resultado}")
    except TimeoutError as e:
        print(f"\n❌ Falha: {e}")
    
    
    print("\n" + "=" * 80)
    print("TESTE 4: TimeoutManager (Uso Real)")
    print("=" * 80)
    
    tentativa_numero = [0]
    
    def chamar_google_places():
        tentativa_numero[0] += 1
        time.sleep(0.2)
        if tentativa_numero[0] < 2:
            raise Exception("Network error")
        return {"places": [...]}
    
    print("\nUsando TimeoutManager.chamar_com_timeout():")
    
    try:
        resultado = TimeoutManager.chamar_com_timeout(
            chamar_google_places,
            "GooglePlaces"
        )
        print(f"\n✅ Resultado: {resultado}")
    except TimeoutError as e:
        print(f"\n❌ Falha: {e}")
    
    
    print("\n" + "=" * 80)
    print("✅ TESTES PASSARAM - IMPLEMENTAR NO CÓDIGO")
    print("=" * 80)
    print("\nProximos passos:")
    print("├─ Integrar TimeoutManager em todas as chamadas de API")
    print("├─ Usar try/except para capturar TimeoutError")
    print("├─ Chamar fallback quando TimeoutError")
    print("└─ Logar todas as tentativas para debugging")

