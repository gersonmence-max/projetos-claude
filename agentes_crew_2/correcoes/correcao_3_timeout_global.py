"""
correcoes/correcao_3_timeout_global.py
=======================================
CORRECAO 3: Timeout Global para chamadas de API.

Garante que nenhuma chamada de API trave o sistema indefinidamente.
Timeout padrao de 8 segundos com retry configuravel.
"""

import time
import logging
import threading
from typing import Callable, Any, Optional, Dict

logger = logging.getLogger(__name__)

TIMEOUT_PADRAO = 8  # segundos


class TimeoutManager:
    """
    Gerencia timeouts globais para chamadas de API externas.

    Uso:
        resultado = TimeoutManager.chamar_com_timeout(
            funcao,
            "NomeDaAPI",
            timeout=8
        )
    """

    @staticmethod
    def chamar_com_timeout(
        funcao: Callable,
        label: str,
        timeout: int = TIMEOUT_PADRAO,
        *args,
        **kwargs
    ) -> Any:
        """
        Executa funcao com timeout. Se exceder, lanca TimeoutError.

        Parametros:
            funcao  : callable a executar
            label   : nome da API (para logging)
            timeout : segundos maximos de espera (default 8)

        Retorna:
            resultado da funcao

        Lanca:
            TimeoutError se o tempo for excedido
        """
        resultado = [None]
        excecao   = [None]

        def worker():
            try:
                resultado[0] = funcao(*args, **kwargs)
            except Exception as e:
                excecao[0] = e

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            logger.warning(f"[{label}] Timeout apos {timeout}s")
            raise TimeoutError(f"[{label}] Timeout apos {timeout}s")

        if excecao[0]:
            raise excecao[0]

        return resultado[0]

    @staticmethod
    def chamar_com_retry(
        funcao: Callable,
        label: str,
        timeout: int = TIMEOUT_PADRAO,
        max_tentativas: int = 2,
        espera_entre_tentativas: float = 1.0,
        *args,
        **kwargs
    ) -> Any:
        """
        Executa funcao com timeout e retry automatico.

        Parametros:
            funcao                   : callable a executar
            label                    : nome da API (para logging)
            timeout                  : segundos maximos por tentativa
            max_tentativas           : numero maximo de tentativas
            espera_entre_tentativas  : segundos de espera entre tentativas

        Retorna:
            resultado da funcao ou None se todas as tentativas falharem
        """
        ultimo_erro = None

        for tentativa in range(1, max_tentativas + 1):
            try:
                if tentativa > 1:
                    logger.info(f"[{label}] Tentativa {tentativa}/{max_tentativas}")
                    time.sleep(espera_entre_tentativas)

                resultado = TimeoutManager.chamar_com_timeout(
                    funcao, label, timeout, *args, **kwargs
                )
                return resultado

            except TimeoutError as e:
                ultimo_erro = e
                logger.warning(f"[{label}] Tentativa {tentativa} timeout")
            except Exception as e:
                ultimo_erro = e
                logger.warning(f"[{label}] Tentativa {tentativa} erro: {e}")

        logger.error(f"[{label}] Todas as {max_tentativas} tentativas falharam: {ultimo_erro}")
        return None
