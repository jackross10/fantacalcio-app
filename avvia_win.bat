@echo off
cd /d "%~dp0"

echo Installazione delle dipendenze...
pip install -r requirements.txt -q

echo Avvio applicazione...
python -m streamlit run app.py --server.headless=true
pause
