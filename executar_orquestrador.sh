#!/bin/bash

# 🤖 ORQUESTRADOR MULTIPROJETOS - SCRIPT DE EXECUÇÃO
# Processa todos os 13 projetos continuamente sem pausa para revisão manual

set -e

PASTA_PROJETOS="C:/Users/g-fil/Documents/Projetos Claude/projetos-organizados"
SCRIPT_PYTHON="orquestrador_multiprojetos.py"

echo "=========================================================================="
echo "🤖 ORQUESTRADOR INTELIGENTE - MULTI-PROJETOS"
echo "=========================================================================="
echo ""
echo "📁 Pasta de Projetos: $PASTA_PROJETOS"
echo "🐍 Script: $SCRIPT_PYTHON"
echo ""

# Verificar se o script Python existe
if [ ! -f "$SCRIPT_PYTHON" ]; then
    echo "❌ Erro: $SCRIPT_PYTHON não encontrado"
    exit 1
fi

echo "⏳ Iniciando processamento..."
echo ""

# Executar Python
python3 "$SCRIPT_PYTHON"

echo ""
echo "=========================================================================="
echo "✅ ORQUESTRADOR FINALIZADO"
echo "=========================================================================="
echo ""
echo "📊 Relatórios salvos em: reports_consolidados/"
echo "📋 Próximas ações:"
echo "   1. Revise os relatórios (OPCIONAL)"
echo "   2. Execute os projetos: bash projeto_N/src/setup.sh"
echo ""
