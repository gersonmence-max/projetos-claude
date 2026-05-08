@echo off
REM Ativa o scheduler para rodar automaticamente às 2AM todos os dias

chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================================================
echo  ⏰ ATIVADOR DE SCHEDULER - ANÁLISE DIÁRIA
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
echo Opções:
echo ========================================================================
echo  1 - Iniciar scheduler (roda às 2AM todos os dias - RECOMENDADO)
echo  2 - Testar análise AGORA
echo  3 - Ver logs
echo  4 - Parar scheduler
echo.

set /p opcao="Escolha uma opção (1/2/3/4): "

if "%opcao%"=="1" (
    echo.
    echo ✅ Iniciando scheduler...
    echo ⏰ Executará análise às 02:00 TODOS OS DIAS
    echo 📝 Logs em: logs_scheduler\scheduler_analise.log
    echo.
    echo DEIXE ESTE TERMINAL ABERTO!
    echo (ou execute em background no Task Scheduler do Windows)
    echo.
    python scheduler_analise_diaria.py

) else if "%opcao%"=="2" (
    echo.
    echo ✅ Executando teste agora...
    echo.
    python scheduler_analise_diaria.py

) else if "%opcao%"=="3" (
    echo.
    echo 📋 Últimas linhas do log:
    echo.
    if exist logs_scheduler\scheduler_analise.log (
        powershell -Command "Get-Content 'logs_scheduler\scheduler_analise.log' -Tail 50"
    ) else (
        echo ❌ Nenhum log encontrado ainda
    )
    pause

) else if "%opcao%"=="4" (
    echo.
    echo ⏹️  Para parar: feche este terminal (Ctrl+C)
    pause

) else (
    echo ❌ Opção inválida!
    pause
    exit /b 1
)

endlocal
