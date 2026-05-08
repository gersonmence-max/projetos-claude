@echo off
REM Ativa o scheduler com AGENTES para rodar automaticamente às 2AM todos os dias

chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================================================
echo  ⏰ ATIVADOR DE SCHEDULER COM AGENTES
echo  🤖 6 Agentes Especializados
echo ========================================================================
echo.

REM Obter caminho do projeto
for %%i in ("%~dp0\.") do set PASTA_PROJETO=%%~fi

echo 📁 Pasta do projeto: %PASTA_PROJETO%
echo.

REM Verificar se Python está instalado
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ ERRO: Python não encontrado!
    echo Instale Python 3.9+ de: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python encontrado
echo.

REM Instalar dependências
echo 📦 Instalando dependências (schedule)...
pip install schedule --break-system-packages > nul 2>&1

if errorlevel 1 (
    echo ⚠️  Aviso: Não conseguiu instalar schedule
    echo Tentando continuar...
)

echo ✅ Dependências OK
echo.

echo ========================================================================
echo 🤖 AGENTES DISPONÍVEIS:
echo ========================================================================
echo  🔍 REVISOR          - Qualidade e padrões
echo  🛡️  SEGURANÇA        - Vulnerabilidades
echo  ⚡ PERFORMANCE      - Gargalos
echo  🏗️  ARQUITETO        - Design e arquitetura
echo  💻 PROGRAMADOR      - Gera código
echo  📊 CONSOLIDADOR     - Agrega e prioriza
echo.

echo ========================================================================
echo Opções:
echo ========================================================================
echo  1 - Iniciar scheduler COM AGENTES (roda às 2AM todos os dias)
echo  2 - Executar análise COM AGENTES AGORA
echo  3 - Executar análise SIMPLES AGORA (sem agentes)
echo  4 - Ver logs
echo  5 - Parar scheduler
echo.

set /p opcao="Escolha uma opção (1/2/3/4/5): "

if "%opcao%"=="1" (
    echo.
    echo ✅ Iniciando scheduler com AGENTES...
    echo ⏰ Executará análise às 02:00 TODOS OS DIAS
    echo 🤖 Com 6 agentes especializados
    echo 📝 Logs em: logs_scheduler\scheduler_agentes.log
    echo.
    echo DEIXE ESTE TERMINAL ABERTO!
    echo (ou execute em background no Task Scheduler do Windows)
    echo.
    python scheduler_agentes_diario.py

) else if "%opcao%"=="2" (
    echo.
    echo ✅ Executando análise COM AGENTES agora...
    echo 🤖 6 agentes rodando
    echo.
    python scheduler_agentes_diario.py

) else if "%opcao%"=="3" (
    echo.
    echo ✅ Executando análise SIMPLES agora...
    echo (sem agentes - mais rápido)
    echo.
    python analisador_sugestoes.py

) else if "%opcao%"=="4" (
    echo.
    echo 📋 Últimas linhas do log COM AGENTES:
    echo.
    if exist logs_scheduler\scheduler_agentes.log (
        powershell -Command "Get-Content 'logs_scheduler\scheduler_agentes.log' -Tail 50"
    ) else (
        echo ❌ Nenhum log encontrado ainda
    )
    pause

) else if "%opcao%"=="5" (
    echo.
    echo ⏹️  Para parar: feche este terminal (Ctrl+C)
    pause

) else (
    echo ❌ Opção inválida!
    pause
    exit /b 1
)

endlocal
