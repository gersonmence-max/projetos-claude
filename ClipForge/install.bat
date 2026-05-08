@echo off
REM install.bat — Instalação do ClipForge no Windows
REM Execute como Administrador se necessário

echo.
echo =============================================
echo     ClipForge — Instalacao (Windows)
echo =============================================
echo.

REM Verifica Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ERRO: Python nao encontrado.
    echo Instale em: https://python.org/downloads
    echo Marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)
echo [1/4] Python encontrado.

REM pip install
echo.
echo [2/4] Instalando dependencias Python...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo ERRO ao instalar dependencias.
    pause
    exit /b 1
)
echo     OK

REM Playwright
echo.
echo [3/4] Instalando Chromium para Kwai...
playwright install chromium
echo     OK (opcional para Kwai)

REM Verifica FFmpeg
echo.
echo [4/4] Verificando FFmpeg...
ffmpeg -version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ATENCAO: FFmpeg nao encontrado.
    echo Baixe em: https://ffmpeg.org/download.html
    echo Extraia e adicione a pasta bin/ ao PATH do Windows.
    echo.
) ELSE (
    echo     FFmpeg encontrado.
)

REM Cria pasta de clips
if not exist clips mkdir clips

echo.
echo =============================================
echo     Instalacao concluida!
echo =============================================
echo.
echo Para iniciar:
echo.
echo     python app.py
echo.
echo Depois abra no navegador:
echo.
echo     http://localhost:5000
echo.
pause
