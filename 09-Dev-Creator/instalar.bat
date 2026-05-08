@echo off
echo Criando ambiente virtual...
python -m venv venv

echo Instalando dependencias...
.\venv\Scripts\pip install -r requirements.txt

echo.
echo Instalacao concluida! Para rodar: iniciar.bat
pause
