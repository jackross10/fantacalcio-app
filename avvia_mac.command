#!/bin/bash
cd "$(dirname "$0")"

if ! command -v pip3 &> /dev/null
then
    echo "pip3 non trovato. Assicurati di avere Python 3 installato."
    exit 1
fi

echo "Installazione delle dipendenze..."
pip3 install -r requirements.txt -q

echo "Avvio applicazione..."
python3 -m streamlit run app.py --server.headless=true
