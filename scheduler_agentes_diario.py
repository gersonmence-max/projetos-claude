#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
⏰ SCHEDULER COM AGENTES ESPECIALIZADOS
Executa análise com 6 agentes AUTOMATICAMENTE às 2AM todos os dias
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
import schedule

# Importar o orquestrador de agentes
from orquestrador_agentes import OrquestradorAgentes

# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

def setup_logging():
    """Configura logging para o scheduler com agentes"""
    log_dir = Path("logs_scheduler")
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger("SchedulerAgentes")
    logger.setLevel(logging.DEBUG)

    # Handler para arquivo
    fh = logging.FileHandler(
        log_dir / "scheduler_agentes.log",
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
# TAREFA COM AGENTES
# ============================================================================

def executar_analise_com_agentes():
    """
    Executa análise completa com 6 AGENTES ESPECIALIZADOS.
    Chamada automaticamente às 2AM todos os dias.
    """

    logger.info("=" * 80)
    logger.info("🤖 INICIANDO ANÁLISE COM AGENTES ESPECIALIZADOS")
    logger.info(f"⏰ Horário: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    try:
        pasta_projetos = r"C:\Users\g-fil\Documents\Projetos Claude\projetos-organizados"

        # Executar orquestrador com agentes
        logger.info("\n🤖 Iniciando orquestrador com 6 agentes...\n")

        orquestrador = OrquestradorAgentes(pasta_projetos)
        orquestrador.executar()

        logger.info("\n" + "=" * 80)
        logger.info("✅ ANÁLISE COM AGENTES CONCLUÍDA COM SUCESSO")
        logger.info(f"📊 Projetos analisados: {orquestrador.projetos_encontrados}")
        logger.info(f"📝 Sugestões geradas: {orquestrador.sugestoes_totais}")
        logger.info("🤖 Agentes envolvidos: 6 (Revisor, Segurança, Performance, Arquiteto, Programador, Consolidador)")
        logger.info("=" * 80)
        logger.info(f"📁 Relatórios salvos em: sugestoes/")
        logger.info("")

    except Exception as e:
        logger.error(f"❌ ERRO NA ANÁLISE COM AGENTES: {e}", exc_info=True)

# ============================================================================
# SCHEDULER PRINCIPAL
# ============================================================================

def iniciar_scheduler():
    """Inicia o scheduler que executa análise com agentes às 2AM todos os dias"""

    logger.info("\n" + "=" * 80)
    logger.info("⏰ SCHEDULER COM AGENTES ESPECIALIZADOS INICIADO")
    logger.info("=" * 80)
    logger.info(f"⏰ Horário de execução: 02:00 (2AM)")
    logger.info(f"📅 Frequência: Todos os dias")
    logger.info(f"🤖 Agentes: 6 especializados")
    logger.info(f"📊 Status: AGUARDANDO...")
    logger.info("=" * 80 + "\n")

    # Agendar para 2AM todos os dias
    schedule.every().day.at("02:00").do(executar_analise_com_agentes)

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
    """Executa análise com agentes IMEDIATAMENTE (para testes)"""
    logger.info("🚀 Executando análise com agentes AGORA (teste manual)...\n")
    executar_analise_com_agentes()
    logger.info("\n✅ Teste concluído!")

# ============================================================================
# MENU INTERATIVO
# ============================================================================

def exibir_menu():
    """Exibe menu de opções"""
    print("\n" + "=" * 80)
    print("⏰ SCHEDULER COM AGENTES ESPECIALIZADOS")
    print("=" * 80)
    print("\n🤖 AGENTES DISPONÍVEIS:")
    print("   1. 🔍 REVISOR - Qualidade e padrões")
    print("   2. 🛡️  SEGURANÇA - Vulnerabilidades")
    print("   3. ⚡ PERFORMANCE - Gargalos e otimizações")
    print("   4. 🏗️  ARQUITETO - Design e arquitetura")
    print("   5. 💻 PROGRAMADOR - Gera código")
    print("   6. 📊 CONSOLIDADOR - Agrega e prioriza")
    print("\n" + "=" * 80)
    print("\nOpções:")
    print("  1. Iniciar scheduler (roda às 2AM todos os dias com 6 agentes)")
    print("  2. Executar análise COM AGENTES AGORA (teste)")
    print("  3. Executar análise SIMPLES AGORA (sem agentes - mais rápido)")
    print("  4. Ver logs do scheduler")
    print("  5. Sair")
    print("\n" + "=" * 80 + "\n")

# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Função principal"""

    exibir_menu()
    opcao = input("Escolha uma opção (1/2/3/4/5): ").strip()

    if opcao == "1":
        print("\n✅ Iniciando scheduler com agentes especializados...\n")
        iniciar_scheduler()

    elif opcao == "2":
        print("\n✅ Executando análise COM AGENTES agora...\n")
        executar_agora()

    elif opcao == "3":
        print("\n✅ Executando análise SIMPLES agora...\n")
        from analisador_sugestoes import AnalisadorSugestoes

        pasta_projetos = r"C:\Users\g-fil\Documents\Projetos Claude\projetos-organizados"
        analisador = AnalisadorSugestoes(pasta_projetos)
        analisador.executar()

    elif opcao == "4":
        print("\n📋 Últimas linhas do log:\n")
        log_file = Path("logs_scheduler/scheduler_agentes.log")

        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-50:]:  # Últimas 50 linhas
                    print(line, end="")
        else:
            print("❌ Nenhum log encontrado ainda")

        input("\nPressione ENTER para voltar...")
        main()

    elif opcao == "5":
        print("\n👋 Saindo...")
        sys.exit(0)

    else:
        print("\n❌ Opção inválida!")
        sys.exit(1)

if __name__ == "__main__":
    main()
