import os
import pandas as pd
import requests
import glob
from sys import stdout
import urllib.parse
import time

def generate_variants(nome):
    nome_up = nome.upper()
    variants = [
        nome_up.replace(" ", "%20"), # ORIGINALE con spazi
        nome_up.replace(" ", "-").replace(".", ""), # ES: MARTINEZ-L
        nome_up.replace(" ", "").replace(".", ""), # ES: MARTINEZL
        nome_up.split(" ")[0].replace(".", ""), # ES: MARTINEZ
        nome_up.replace("'", ""), # ES: NDICKA
        nome_up.replace(" ", "%20").replace(".", "") # ES: MARTINEZ L (senza punto)
    ]
    return list(set(variants))

def main():
    print("Cerco file CSV del listone...")
    csv_files = glob.glob("*.csv")
    if not csv_files:
        print("Errore: Nessun file CSV trovato.")
        return
    
    csv_file = csv_files[0]
    print(f"File trovato: {csv_file}")
    
    try:
        df_temp = pd.read_csv(csv_file, sep=None, engine='python', header=None)
        header_idx = 0
        for i in range(min(5, len(df_temp))):
            row_vals = df_temp.iloc[i].astype(str).str.upper().values
            if 'NOME' in row_vals and ('R' in row_vals or 'RUOLO' in row_vals):
                header_idx = i
                break
        
        df_list = df_temp.copy()
        df_list.columns = df_temp.iloc[header_idx].astype(str)
        df_list = df_list.iloc[header_idx+1:].reset_index(drop=True)
        
        col_mapping = {}
        for col in df_list.columns:
            c_upper = str(col).upper()
            if c_upper in ['ID']: col_mapping[col] = 'Id'
            elif c_upper in ['NOME', 'GIOCATORE']: col_mapping[col] = 'Nome'
            
        df_list.rename(columns=col_mapping, inplace=True)
            
    except Exception as e:
        print(f"Errore durante l'analisi: {e}")
        return
        
    os.makedirs("foto", exist_ok=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.fantacalcio.it/"
    }
    
    total = len(df_list)
    count = 0
    
    print(f"Inizio download CAMPIONCINI ANIMATI per {total} calciatori...\n")
    
    for idx, row in df_list.iterrows():
        count += 1
        id_str = str(row.get('Id', '')).strip()
        nome = str(row.get('Nome', 'Sconosciuto')).strip()
        
        if not id_str or id_str == 'nan': continue
            
        try: clean_id = int(float(id_str))
        except: continue
            
        file_path_png = f"foto/{clean_id}.png"
        file_path_jpg = f"foto/{clean_id}.jpg"
        
        if os.path.exists(file_path_png) or os.path.exists(file_path_jpg):
            stdout.write(f"\rSaltato (già esiste): {nome} - {count}/{total}       ")
            stdout.flush()
            continue
            
        variants = generate_variants(nome)
        scaricato = False
        
        for var in variants:
            url = f"https://content.fantacalcio.it/web/campioncini/medium/{var}.png"
            try:
                r = requests.get(url, headers=headers, timeout=5)
                if r.status_code == 200:
                    with open(file_path_png, 'wb') as f:
                        f.write(r.content)
                    stdout.write(f"\rScaricato: {nome} - {count}/{total}       ")
                    scaricato = True
                    break
            except:
                pass
                
        if not scaricato:
            stdout.write(f"\rNon trovato: {nome} - {count}/{total}       ")
        stdout.flush()
            
    print("\n\nDownload completato!")

if __name__ == "__main__":
    main()
