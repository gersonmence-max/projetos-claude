#!/bin/bash
# install.sh — Instalação automática do ClipForge
# Execute: bash install.sh

set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     ClipForge — Instalação           ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Python ────────────────────────────────────────────────────────────────────
echo "[1/5] Verificando Python..."
if ! command -v python3 &>/dev/null; then
    echo "  ERRO: Python 3 não encontrado."
    echo "  Instale em: https://python.org/downloads"
    exit 1
fi
PY=$(python3 --version)
echo "  ✓ $PY"

# ── pip install ────────────────────────────────────────────────────────────────
echo ""
echo "[2/5] Instalando dependências Python..."
pip install -r requirements.txt --quiet
echo "  ✓ Dependências instaladas"

# ── Playwright ────────────────────────────────────────────────────────────────
echo ""
echo "[3/5] Instalando Chromium para Kwai (Playwright)..."
playwright install chromium --quiet 2>/dev/null || echo "  (Playwright Chromium — opcional para Kwai)"

# ── FFmpeg ────────────────────────────────────────────────────────────────────
echo ""
echo "[4/5] Verificando FFmpeg..."
if command -v ffmpeg &>/dev/null; then
    echo "  ✓ FFmpeg já instalado"
else
    echo "  FFmpeg não encontrado."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  Instalando via Homebrew..."
        if command -v brew &>/dev/null; then
            brew install ffmpeg
        else
            echo "  ATENÇÃO: Instale manualmente: https://ffmpeg.org/download.html"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "  Instalando via apt..."
        sudo apt-get install -y ffmpeg 2>/dev/null || echo "  ATENÇÃO: Execute: sudo apt install ffmpeg"
    else
        echo "  Windows: baixe em https://ffmpeg.org/download.html"
        echo "  e adicione ao PATH do sistema"
    fi
fi

# ── Ollama ────────────────────────────────────────────────────────────────────
echo ""
echo "[5/5] Verificando Ollama (LLM local)..."
if command -v ollama &>/dev/null; then
    echo "  ✓ Ollama instalado"
    echo "  Baixando modelo mistral:7b-instruct (pode demorar na 1ª vez)..."
    ollama pull mistral:7b-instruct 2>/dev/null &
    echo "  (download em background — o sistema funciona sem ele no início)"
else
    echo "  Ollama não encontrado."
    echo "  Para instalar (opcional mas melhora a qualidade):"
    if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "    curl -fsSL https://ollama.com/install.sh | sh"
        echo "    ollama pull mistral:7b-instruct"
    else
        echo "    https://ollama.com/download"
    fi
fi

# ── Pasta de clips ────────────────────────────────────────────────────────────
mkdir -p clips

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     Instalação concluída!            ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "Para iniciar o ClipForge:"
echo ""
echo "    python app.py"
echo ""
echo "Depois abra no navegador:"
echo ""
echo "    http://localhost:5000"
echo ""
