@echo off
echo.
echo  DEV CREATOR - Servidor Web
echo  Abrindo em: http://localhost:8000
echo.
start "" http://localhost:8000
.\venv\Scripts\uvicorn server:app --host 127.0.0.1 --port 8000
pause
