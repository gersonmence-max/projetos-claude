@echo off
REM =============================================================================
REM  SETUP GIT AUTOMÁTICO - Inicializa repositório e conecta ao GitHub
REM =============================================================================

setlocal enabledelayedexpansion

cd /d "%~dp0"

cls
echo.
echo ============================================================================
echo.
echo  🚀 SETUP GIT AUTOMÁTICO - Projetos Claude
echo.
echo ============================================================================
echo.

REM Verifica se já é um repositório git
if exist ".git" (
    echo ✅ Já é um repositório git!
    echo.
    git remote -v
    echo.
    pause
    exit /b 0
)

echo Inicializando repositório Git...
git init

REM Configura git local
git config user.name "Gerson Mence"
git config user.email "gersonmence@gmail.com"

echo ✅ Repositório inicializado

echo.
echo ============================================================================
echo.
echo Agora preciso do URL do repositório GitHub.
echo.
echo Se NÃO criou ainda no GitHub:
echo   1. Vá em https://github.com/new
echo   2. Nome: projetos-claude
echo   3. Descrição: Projetos Claude - Orquestrador de Agentes
echo   4. Público ou Privado (sua escolha)
echo   5. Clique "Create repository"
echo   6. Copie a URL HTTPS
echo.
echo ============================================================================
echo.

set /p repo_url="Cole aqui a URL do repositório GitHub: "

if "%repo_url%"=="" (
    echo ❌ ERRO: URL não pode estar vazia!
    pause
    exit /b 1
)

echo.
echo Conectando ao repositório...
git remote add origin %repo_url%

echo ✅ Repositório conectado: %repo_url%

echo.
echo Adicionando arquivos...
git add .

echo.
echo Fazendo commit inicial...
git commit -m "initial: orquestrador de agentes com github actions

- 6 agentes especializados
- análise automática 2AM
- descoberta dinâmica de projetos
- sugestões geradas automaticamente"

echo.
echo Fazendo push (primeira vez)...
git branch -M main
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ============================================================================
    echo  ✅ SUCESSO! Repositório criado e conectado!
    echo ============================================================================
    echo.
    echo Próximos passos:
    echo   1. GitHub Actions já está ativado
    echo   2. Workflow roda TODOS OS DIAS às 2AM
    echo   3. Vá em https://github.com/gersonmence-max/projetos-claude
    echo   4. Clique em "Actions" para acompanhar
    echo.
    echo A partir de agora:
    echo   ✅ Descobre seus projetos automaticamente
    echo   ✅ Executa 6 agentes (Revisor, Segurança, Performance, etc)
    echo   ✅ Gera sugestões automaticamente
    echo   ✅ Faz commit dos resultados
    echo   ✅ TUDO SEM VOCÊ FAZER NADA!
    echo.
) else (
    echo.
    echo ❌ Erro ao fazer push
    echo.
    echo Tente manualmente:
    echo   git push -u origin main
    echo.
)

pause
