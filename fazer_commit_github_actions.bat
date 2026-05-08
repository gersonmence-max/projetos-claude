@echo off
REM =============================================================================
REM  COMMIT GITHUB ACTIONS - Ativa automação no GitHub
REM =============================================================================

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ============================================================================
echo.
echo  GIT COMMIT - Ativando Automacao GitHub Actions
echo.
echo ============================================================================
echo.

REM Verifica se é um repositório git
if not exist ".git" (
    echo ERRO: Nao e um repositorio git!
    pause
    exit /b 1
)

echo Adicionando arquivos...
git add .github/workflows/orquestrador-agentes-diario.yml
git add README_GITHUB_ACTIONS.md

echo.
echo Status:
git status --short

echo.
echo ============================================================================
echo.

echo Fazendo commit...
git commit -m "ci: adicionar github actions para orquestrador diario automatico

- workflow: orquestrador-agentes-diario.yml
- roda 2AM (5AM UTC) todo dia
- descobre projetos dinamicamente
- executa 6 agentes (revisor, seguranca, performance, arquiteto, programador, consolidador)
- faz commit automatico dos resultados
- totalmente sem intervencao manual"

if %errorlevel% equ 0 (
    echo.
    echo [OK] Commit feito com sucesso!
    echo.
    echo Fazendo push...
    git push

    if %errorlevel% equ 0 (
        echo.
        echo ============================================================================
        echo  SUCESSO! GitHub Actions ATIVADO!
        echo ============================================================================
        echo.
        echo A partir de agora, TODOS OS DIAS as 2AM:
        echo   • GitHub Actions dispara automaticamente
        echo   • Descobre seus projetos
        echo   • Executa 6 agentes especializados
        echo   • Gera sugestoes e relatorios
        echo   • Faz commit automático
        echo.
        echo Para acompanhar:
        echo   1. Va para seu repositorio no GitHub
        echo   2. Clique em "Actions"
        echo   3. Veja todas as execucoes do workflow
        echo.
    ) else (
        echo.
        echo AVISO: Commit feito, mas erro ao fazer push
        echo Execute manualmente: git push
        echo.
    )
) else (
    echo.
    echo ERRO ao fazer commit!
    echo.
)

pause
