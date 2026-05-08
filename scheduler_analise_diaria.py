#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
⏰ SCHEDULER DE ANÁLISE DIÁRIA
Executa análise de sugestões AUTOMATICAMENTE às 2AM todos os dias
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
import schedule

# Importar o analisador
from analisador_sugestoes import AnalisadorSugestoes

# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

def setup_logging():
    """Configura logging para o scheduler"""
    log_dir = Path("logs_scheduler")
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger("SchedulerAnalise")
    logger.setLevel(logging.DEBUG)

    # Handler para arquivo
    fh = logging.FileHandler(
        log_dir / "scheduler_analise.log",
        encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)

    # Handler para console
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger

logger = setup_logging()

# ============================================================================
# TAREFA DE ANÁLISE DIÁRIA
# ============================================================================

def executar_analise_diaria():
    """
    Executa análise de sugestões.
    Chamada automaticamente às 2AM todos os dias.
    """

    logger.info("=" * 80)
    logger.info("🔍 INICIANDO ANÁLISE DIÁRIA DE SUGESTÕES")
    logger.info(f"⏰ Horário: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    try:
        pasta_projetos = r"C:\Users\g-fil\Documents\Projetos Claude\projetos-organizados"

        # Executar analisador
        analisador = AnalisadorSugestoes(pasta_projetos)
        analisador.executar()

        logger.info("=" * 80)
        logger.info("✅ ANÁLISE DIÁRIA CONCLUÍDA COM SUCESSO")
        logger.info(f"📊 Projetos analisados: {analisador.projetos_encontrados}")
        logger.info(f"📝 Sugestões geradas: {analisador.sugestoes_totais}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ ERRO NA ANÁLISE DIÁRIA: {e}", exc_info=True)

# ============================================================================
# SCHEDULER PRINCIPAL
# ============================================================================

def iniciar_scheduler():
    """Inicia o scheduler que executa análise às 2AM todos os dias"""

    logger.info("\n" + "=" * 80)
    logger.info("⏰ SCHEDULER DE ANÁLISE DIÁRIA INICIADO")
    logger.info("=" * 80)
    logger.info(f"Horário de execução: 02:00 (2AM)")
    logger.info(f"Frequência: Todos os dias")
    logger.info(f"Status: AGUARDANDO...")
    logger.info("=" * 80 + "\n")

    # Agendar para 2AM todos os dias
    schedule.every().day.at("02:00").do(executar_analise_diaria)

    logger.info(f"📅 Próxima execução agendada para: 02:00")
    logger.info("⏳ Aguardando hora agendada...\n")

    # Loop infinito - mantém scheduler rodando
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar a cada minuto

    except KeyboardInterrupt:
        logger.info("\n" + "=" * 80)
        logger.info("⏹️  SCHEDULER INTERROMPIDO PELO USUÁRIO")
        logger.info("=" * 80)
        sys.exit(0)

    except Exception as e:
        logger.critical(f"❌ ERRO CRÍTICO NO SCHEDULER: {e}", exc_info=True)
        sys.exit(1)

# ============================================================================
# EXECUÇÃO MANUAL (para testar)
# ============================================================================

def executar_agora():
    """Executa análise imediatamente (para testes)"""
    logger.info("🚀 Executando análise AGORA (teste manual)...\n")
    executar_analise_diaria()
    logger.info("\n✅ Teste concluído!")

# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Função principal"""

    print("\n" + "=" * 80)
    print("⏰ SCHEDULER DE ANÁLISE DIÁRIA")
    print("=" * 80)
    print("\nOpções:")
    print("  1. Iniciar scheduler (roda às 2AM todos os dias)")
    print("  2. Executar análise AGORA (teste)")
    print("  3. Sair")
    print("\n" + "=" * 80 + "\n")

    opcao = input("Escolha uma opção (1/2/3): ").strip()

    if opcao == "1":
        print("\n✅ Iniciando scheduler automático...\n")
        iniciar_scheduler()

    elif opcao == "2":
        print("\n✅ Executando análise agora...\n")
        executar_agora()

    elif opcao == "3":
        print("\n👋 Saindo...")
        sys.exit(0)

    else:
        print("\n❌ Opção inválida!")
        sys.exit(1)

if __name__ == "__main__":
    main()
