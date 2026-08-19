import streamlit as st
import pandas as pd
import json
import os
import base64
import requests

def generate_photo_variants(nome):
    nome_up = nome.upper()
    variants = [
        nome_up.replace(" ", "%20"),
        nome_up.replace(" ", "-").replace(".", ""),
        nome_up.replace(" ", "").replace(".", ""),
        nome_up.split(" ")[0].replace(".", ""),
        nome_up.replace("'", ""),
        nome_up.replace(" ", "%20").replace(".", "")
    ]
    return list(set(variants))

def sincronizza_foto_listone(df):
    os.makedirs("foto", exist_ok=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.fantacalcio.it/"
    }
    
    missing_players = []
    for idx, row in df.iterrows():
        id_str = str(row.get('Id', '')).strip()
        nome = str(row.get('Nome', 'Sconosciuto')).strip()
        
        if not id_str or id_str == 'nan': continue
        try: clean_id = int(float(id_str))
        except: continue
        
        # Saltiamo se c'è l'immagine o se sappiamo già che Fantacalcio non la possiede (.missing)
        if not (os.path.exists(f"foto/{clean_id}.png") or os.path.exists(f"foto/{clean_id}.jpg") or os.path.exists(f"foto/{clean_id}.missing") or os.path.exists(f"foto/{nome}.jpg") or os.path.exists(f"foto/{nome}.png")):
            missing_players.append((clean_id, nome))
            
    if not missing_players:
        return
        
    bar = st.progress(0, text=f"Controllo e recupero {len(missing_players)} giocatori mancanti...")
    
    for i, (clean_id, nome) in enumerate(missing_players):
        variants = generate_photo_variants(nome)
        scaricato = False
        for var in variants:
            url = f"https://content.fantacalcio.it/web/campioncini/medium/{var}.png"
            try:
                r = requests.get(url, headers=headers, timeout=2)
                if r.status_code == 200:
                    with open(f"foto/{clean_id}.png", 'wb') as f:
                        f.write(r.content)
                    scaricato = True
                    break
            except:
                pass
                
        # Se dopo tutti i tentativi la foto non esiste sui server, creiamo un file marcatore .missing
        if not scaricato:
            with open(f"foto/{clean_id}.missing", 'w') as f:
                f.write('')
                
        bar.progress((i + 1) / len(missing_players), text=f"Verificato: {nome}")
        
    bar.empty()

try:
    from st_keyup import st_keyup
except ImportError:
    st_keyup = None

st.set_page_config(page_title="Asta Live Fantacalcio", layout="wide", page_icon="⚽")

# Custom CSS per minimizzare e compattare
st.markdown("""
<style>
.badge-P { background-color: #f59e0b; color: white; padding: 2px 4px; border-radius: 3px; font-weight: bold; font-size: 0.65rem; margin-right: 2px; }
.badge-D { background-color: #10b981; color: white; padding: 2px 4px; border-radius: 3px; font-weight: bold; font-size: 0.65rem; margin-right: 2px; }
.badge-C { background-color: #3b82f6; color: white; padding: 2px 4px; border-radius: 3px; font-weight: bold; font-size: 0.65rem; margin-right: 2px; }
.badge-A { background-color: #ef4444; color: white; padding: 2px 4px; border-radius: 3px; font-weight: bold; font-size: 0.65rem; margin-right: 2px; }
.player-name-compact { font-weight: 700; font-size: 0.75rem; line-height: 1; }
.player-cost-compact { color: #10b981; font-weight: bold; font-size: 0.75rem; }
.filter-container { padding: 8px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 10px; }
/* Rende i bottoni super compatti e centra l'ingranaggio (Isolato ai bottoni tertiary) */
button[kind="tertiary"] { padding: 0 !important; font-size: 0.7rem !important; height: 22px !important; min-height: 22px !important; width: 24px !important; margin-top:-2px !important; margin-bottom:-2px !important; display: inline-flex !important; align-items: center !important; justify-content: center !important; }
button[kind="tertiary"] div { display: flex !important; align-items: center !important; justify-content: center !important; margin: 0 !important; padding: 0 !important; }
button[kind="tertiary"] p { margin: 0 !important; padding: 0 !important; line-height: 0 !important; }
div[data-testid="column"] { padding: 0 1px !important; }
div[data-testid="stVerticalBlock"] > div { padding-bottom: 0px !important; padding-top: 0px !important; }
</style>
""", unsafe_allow_html=True)

def get_save_file():
    stanza = st.session_state.get('stanza', 'pubblica').strip()
    if not stanza: stanza = 'pubblica'
    # Sanitize room name
    stanza = "".join([c for c in stanza if c.isalnum() or c in ('-', '_')])
    return f'asta_salvata_{stanza}.json'

def init_state():
    if 'fase' not in st.session_state:
        st.session_state.fase = 0
    if 'squadre' not in st.session_state:
        st.session_state.squadre = []
    if 'assegnazioni' not in st.session_state:
        st.session_state.assegnazioni = []
    if 'budget_iniziale' not in st.session_state:
        st.session_state.budget_iniziale = 500
    if 'config_ruoli' not in st.session_state:
        st.session_state.config_ruoli = {'P': 3, 'D': 8, 'C': 8, 'A': 6}
    if 'df_listone' not in st.session_state:
        st.session_state.df_listone = pd.DataFrame()
    if 'squadra_input' not in st.session_state:
        st.session_state.squadra_input = ""
    if 'stanza' not in st.session_state:
        st.session_state.stanza = ""
    if 'password' not in st.session_state:
        st.session_state.password = ""
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = True
    if 'giocatore_in_asta' not in st.session_state:
        st.session_state.giocatore_in_asta = ""

init_state()

def save_state():
    listone_data = []
    if not st.session_state.df_listone.empty:
        listone_data = st.session_state.df_listone.to_dict('records')
        
    state = {
        'squadre': st.session_state.squadre,
        'assegnazioni': st.session_state.assegnazioni,
        'budget_iniziale': st.session_state.budget_iniziale,
        'config_ruoli': st.session_state.config_ruoli,
        'listone': listone_data,
        'password': st.session_state.get('password', ''),
        'giocatore_in_asta': st.session_state.get('giocatore_in_asta', ''),
        'costo_in_asta': st.session_state.get('costo_in_asta', 1),
        'squadra_in_asta': st.session_state.get('squadra_in_asta', '')
    }
    with open(get_save_file(), 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_state():
    if os.path.exists(get_save_file()):
        try:
            with open(get_save_file(), 'r', encoding='utf-8') as f:
                state = json.load(f)
                st.session_state.squadre = state.get('squadre', [])
                st.session_state.assegnazioni = state.get('assegnazioni', [])
                st.session_state.budget_iniziale = state.get('budget_iniziale', 500)
                st.session_state.config_ruoli = state.get('config_ruoli', {'P': 3, 'D': 8, 'C': 8, 'A': 6})
                st.session_state.giocatore_in_asta = state.get('giocatore_in_asta', '')
                st.session_state.costo_in_asta = state.get('costo_in_asta', 1)
                st.session_state.squadra_in_asta = state.get('squadra_in_asta', '')
                
                list_data = state.get('listone', [])
                if list_data:
                    st.session_state.df_listone = pd.DataFrame(list_data)
                return True
        except:
            pass
    return False

def add_squadra():
    sq = st.session_state.squadra_input.strip()
    if sq and sq not in st.session_state.squadre:
        st.session_state.squadre.append(sq)
        save_state()
    st.session_state.squadra_input = ""

def remove_squadra(sq):
    if sq in st.session_state.squadre:
        st.session_state.squadre.remove(sq)
        st.session_state.assegnazioni = [a for a in st.session_state.assegnazioni if a['squadra'] != sq]
        save_state()

def get_stats_squadra(nome_squadra):
    assegnati = [a for a in st.session_state.assegnazioni if a['squadra'] == nome_squadra]
    spesa = sum(a['costo'] for a in assegnati)
    rimanente = st.session_state.budget_iniziale - spesa
    
    conteggio_ruoli = {'P': 0, 'D': 0, 'C': 0, 'A': 0}
    for a in assegnati:
        ruolo_norm = a['ruolo'].upper()
        if ruolo_norm in conteggio_ruoli:
            conteggio_ruoli[ruolo_norm] += 1
            
    totale_giocatori = sum(conteggio_ruoli.values())
    totale_richiesti = sum(st.session_state.config_ruoli.values())
    slot_liberi = totale_richiesti - totale_giocatori
    
    max_spendibile = rimanente - (slot_liberi - 1) if slot_liberi > 0 else rimanente
    
    return {
        'spesa': spesa,
        'rimanente': rimanente,
        'ruoli': conteggio_ruoli,
        'max_spendibile': max_spendibile,
        'slot_liberi': slot_liberi,
        'totale_richiesti': totale_richiesti,
        'totale_giocatori': totale_giocatori,
        'assegnati': assegnati
    }

def get_ruolo_colore(r):
    if r == 'P': return "#f59e0b"
    if r == 'D': return "#10b981"
    if r == 'C': return "#3b82f6"
    if r == 'A': return "#ef4444"
    return "#888888"

@st.dialog("Modifica Giocatore")
def modal_modifica_giocatore(nome_giocatore, costo_attuale, squadra_attuale):
    st.write(f"Stai gestendo: **{nome_giocatore}**")
    new_cost = st.number_input("Nuovo Costo", value=costo_attuale, min_value=1, step=1)
    new_sq = st.selectbox("Cambia Squadra", st.session_state.squadre, index=st.session_state.squadre.index(squadra_attuale))
    
    c_sv, c_rm = st.columns(2)
    if c_sv.button("💾 Salva Modifiche", type="primary", use_container_width=True):
        for a in st.session_state.assegnazioni:
            if a['giocatore'] == nome_giocatore:
                a['costo'] = new_cost
                a['squadra'] = new_sq
        save_state()
        st.rerun()
        
    if c_rm.button("🗑️ Svincola", type="secondary", use_container_width=True):
        st.session_state.assegnazioni = [a for a in st.session_state.assegnazioni if a['giocatore'] != nome_giocatore]
        save_state()
        st.rerun()

# ==========================================
# FASE 0: LOBBY & ACCESSO
# ==========================================
if st.session_state.fase == 0:
    st.title("⚽ Asta Fantacalcio")
    
    st.info("""
    **Benvenuto nell'Asta Live!**
    - 👑 **Banditore (Admin):** Inventa un Nome Stanza e una Password per creare la tua asta protetta.
    - 👀 **Spettatori:** Inserite il Nome Stanza del vostro Banditore e lasciate VUOTA la Password.
    """)
    
    col_s, col_p = st.columns(2)
    stanza = col_s.text_input("🔑 Nome Stanza", value=st.session_state.get('stanza', ''), placeholder="es. LegaAmici2026")
    password = col_p.text_input("🔒 Password Admin", type="password", help="Obbligatoria per creare una nuova stanza o per gestirla come Admin.")
    
    if not stanza:
        st.warning("👈 Inserisci un Nome Stanza per continuare!")
    else:
        st.session_state.stanza = stanza
        file_esiste = os.path.exists(get_save_file())
        
        is_admin = False
        can_spectate = False
        
        if file_esiste:
            try:
                with open(get_save_file(), 'r', encoding='utf-8') as f:
                    state_tmp = json.load(f)
                    saved_pw = state_tmp.get('password', '')
                    if saved_pw and password != saved_pw:
                        st.error("Password errata. Se sei uno spettatore, puoi comunque guardare l'asta!")
                        can_spectate = True
                    else:
                        is_admin = True
                        can_spectate = True
            except:
                is_admin = True
        else:
            # La stanza non esiste. Deve esserci per forza una password.
            if not password:
                st.warning("⚠️ Per creare una nuova stanza devi obbligatoriamente inserire una Password!")
                is_admin = False
            else:
                is_admin = True
            
        col_b1, col_b2 = st.columns(2)
        
        if is_admin:
            if file_esiste:
                if col_b1.button("▶️ Entra nell'Asta (Admin)", type="primary", use_container_width=True):
                    st.session_state.is_admin = True
                    st.session_state.password = password
                    load_state()
                    st.session_state.fase = 2
                    st.rerun()
            else:
                if col_b1.button("✨ Crea Nuova Stanza", type="primary", use_container_width=True):
                    st.session_state.is_admin = True
                    st.session_state.password = password
                    st.session_state.fase = 1
                    st.rerun()
                    
        if can_spectate and file_esiste:
            if col_b2.button("👀 Entra come Spettatore", use_container_width=True):
                st.session_state.is_admin = False
                st.session_state.password = ""
                load_state()
                st.session_state.fase = 2
                st.rerun()

    st.divider()
    import glob
    stanze_files = glob.glob("asta_salvata_*.json")
    if stanze_files:
        stanze_names = [f.replace("asta_salvata_", "").replace(".json", "") for f in stanze_files]
        st.caption("🟢 **Stanze attualmente attive sul server:**")
        st.caption(", ".join(stanze_names))
    else:
        st.caption("Nessuna stanza attiva al momento.")

# ==========================================
# FASE 1: SETUP
# ==========================================
elif st.session_state.fase == 1:
    col_back, _ = st.columns([1, 4])
    if col_back.button("🚪 Torna alla Hall", use_container_width=True):
        st.session_state.fase = 0
        st.rerun()
        
    st.title("⚙️ Setup & Configurazione")
    
    col_load, col_empty = st.columns([1, 2])
    with col_load:
        if not st.session_state.df_listone.empty:
            if st.button("🗑️ Elimina Listone Attuale", use_container_width=True):
                st.session_state.df_listone = pd.DataFrame()
                save_state()
                st.rerun()
                
    st.header("1. Configurazione Regole")
    c1, c2, c3, c4, c5 = st.columns(5)
    st.session_state.budget_iniziale = c1.number_input("Budget", min_value=1, value=st.session_state.budget_iniziale)
    st.session_state.config_ruoli['P'] = c2.number_input("Portieri (P)", min_value=1, value=st.session_state.config_ruoli['P'])
    st.session_state.config_ruoli['D'] = c3.number_input("Difensori (D)", min_value=1, value=st.session_state.config_ruoli['D'])
    st.session_state.config_ruoli['C'] = c4.number_input("Centrocampisti (C)", min_value=1, value=st.session_state.config_ruoli['C'])
    st.session_state.config_ruoli['A'] = c5.number_input("Attaccanti (A)", min_value=1, value=st.session_state.config_ruoli['A'])

    st.header("2. Squadre Partecipanti")
    st.text_input("Aggiungi Nome Squadra e premi Invio", placeholder="Es. Real Madrid", key="squadra_input", on_change=add_squadra)
            
    if st.session_state.squadre:
        st.write("**Squadre aggiunte:**")
        cols = st.columns(4)
        for i, sq in enumerate(st.session_state.squadre):
            with cols[i % 4]:
                c_name, c_btn = st.columns([4, 1])
                c_name.markdown(f"✅ **{sq}**")
                if c_btn.button("❌", key=f"del_{sq}", help="Rimuovi squadra", type="tertiary"):
                    remove_squadra(sq)
                    st.rerun()

    st.header("3. Carica Listone CSV")
    if not st.session_state.df_listone.empty:
        st.success(f"✔️ Listone già caricato in memoria ({len(st.session_state.df_listone)} giocatori).")
        st.dataframe(st.session_state.df_listone.head(3), height=150)
    else:
        uploaded_file = st.file_uploader("Seleziona il CSV (Formato Ufficiale o Custom)", type=["csv"])
        if uploaded_file is not None:
            try:
                df_temp = pd.read_csv(uploaded_file, sep=None, engine='python', header=None)
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
                    if c_upper in ['R', 'RUOLO']: col_mapping[col] = 'Ruolo'
                    elif c_upper in ['NOME', 'GIOCATORE']: col_mapping[col] = 'Nome'
                    elif c_upper in ['SQUADRA', 'TEAM']: col_mapping[col] = 'Squadra'
                    elif c_upper in ['ID']: col_mapping[col] = 'Id'
                    elif c_upper in ['QT.A', 'QT', 'QUOTAZIONE', 'FVM'] and 'Quotazione' not in col_mapping.values():
                        col_mapping[col] = 'Quotazione'
                
                df_list.rename(columns=col_mapping, inplace=True)
                if all(c in df_list.columns for c in ['Ruolo', 'Nome', 'Squadra']):
                    st.session_state.df_listone = df_list
                    save_state()
                    st.success(f"Listone caricato con successo e salvato in memoria! {len(df_list)} giocatori trovati.")
                    st.rerun()
                else:
                    st.error("Errore: colonne obbligatorie non trovate (Ruolo, Nome, Squadra).")
            except Exception as e:
                st.error(f"Errore durante la lettura del CSV: {e}")

    st.divider()
    can_start = len(st.session_state.squadre) >= 2 and not st.session_state.df_listone.empty
    if st.button("🚀 Avvia Asta", disabled=not can_start, use_container_width=True, type="primary"):
        sincronizza_foto_listone(st.session_state.df_listone)
        st.session_state.fase = 2
        save_state()
        st.rerun()

# ==========================================
# FASE 2: ASTA LIVE
# ==========================================
elif st.session_state.fase == 2:
    
    c_b1, c_b2, _ = st.columns([1, 1, 3])
    if c_b1.button("🚪 Torna alla Hall", use_container_width=True):
        st.session_state.fase = 0
        st.rerun()
        
    is_admin = st.session_state.get('is_admin', True)
    if is_admin:
        if c_b2.button("⚙️ Torna al Setup", use_container_width=True):
            st.session_state.fase = 1
            st.rerun()

    col_t, col_toggle = st.columns([3, 1])
    with col_t:
        stanza_corrente = st.session_state.get('stanza', 'Stanza')
        st.title(f"🔴 Asta Live - {stanza_corrente}")
    with col_toggle:
        st.write("")
        if is_admin:
            spettatore_mode = st.toggle("👀 Modalità Spettatore", help="Nasconde i comandi per fare spazio ai tabelloni.")
        else:
            spettatore_mode = True
            st.error("👀 **SEI IN MODALITÀ SPETTATORE**")
            
        try:
            from streamlit_autorefresh import st_autorefresh
            if spettatore_mode:
                load_state()
                st_autorefresh(interval=3000, key="spettatore_refresh")
        except:
            pass

    def colorize_role(val):
        color = ''
        if val == 'P': color = 'color: #f59e0b; font-weight: bold;'
        elif val == 'D': color = 'color: #10b981; font-weight: bold;'
        elif val == 'C': color = 'color: #3b82f6; font-weight: bold;'
        elif val == 'A': color = 'color: #ef4444; font-weight: bold;'
        return color

    st.markdown("### 🔍 Ricerca e Chiamata")
    
    df_listone = st.session_state.df_listone
    assegnati_nomi = [a['giocatore'] for a in st.session_state.assegnazioni]
    df_disponibili = df_listone[~df_listone['Nome'].isin(assegnati_nomi)].copy()
    
    if df_disponibili.empty:
        st.warning("Tutti i giocatori sono stati assegnati!")
    else:
        import streamlit.components.v1 as components
        import os
        
        # Inizializza il componente custom
        parent_dir = os.path.dirname(os.path.abspath(__file__))
        custom_table2_dir = os.path.join(parent_dir, "custom_table2")
        custom_table2 = components.declare_component("custom_table2", path=custom_table2_dir)
        
        players_json = df_disponibili.fillna("").to_dict('records')
        c_tab, c_assegna = st.columns([2, 1])
        
        with c_tab:
            st.write("**Usa la barra di ricerca o i filtri per trovare il giocatore**")
            # Il componente restituisce il nome del giocatore quando viene cliccato "Chiama"
            clicked_player = custom_table2(
                players_json=players_json, 
                is_spectator=spettatore_mode or not is_admin,
                key=f"table_{len(assegnati_nomi)}" # Forza re-render quando cambiano gli assegnati
            )
        
        if is_admin and not spettatore_mode:
            if clicked_player:
                if st.session_state.get('giocatore_in_asta') != clicked_player:
                    st.session_state.giocatore_in_asta = clicked_player
                    save_state()
            else:
                if st.session_state.get('giocatore_in_asta', '') != '':
                    st.session_state.giocatore_in_asta = ''
                    save_state()
        
        giocatore_selezionato = st.session_state.get('giocatore_in_asta', '')
                
        with c_assegna:
            st.markdown("#### Modulo Rilancio")
            if not giocatore_selezionato:
                if is_admin:
                    st.info("👈 Clicca su un calciatore in tabella per metterlo all'asta!")
                else:
                    st.info("⏳ In attesa che il Banditore chiami un giocatore...")
            
            if giocatore_selezionato:
                # In caso il giocatore sia stato filtrato via dallo schermo spettatore, cerchiamolo nel df totale
                riga_match = df_disponibili[df_disponibili['Nome'] == giocatore_selezionato]
                if not riga_match.empty:
                    riga_g = riga_match.iloc[0]
                    ruolo_g = str(riga_g.get('Ruolo', '')).upper()
                    squadra_reale = riga_g.get('Squadra', '')
                    quotazione = riga_g.get('Quotazione', '-')
                    id_g = riga_g.get('Id', None)
                    iniziali = giocatore_selezionato[:2].upper()
                else:
                    ruolo_g, squadra_reale, quotazione, id_g, iniziali = "", "", "-", None, "XX"
                
                foto_url = ""
                # Logica per l'immagine:
                # 1. Cerca una foto locale nella cartella 'foto'
                foto_png_id = f"foto/{id_g}.png"
                foto_jpg_id = f"foto/{id_g}.jpg"
                foto_png_nome = f"foto/{giocatore_selezionato}.png"
                foto_jpg_nome = f"foto/{giocatore_selezionato}.jpg"
                
                if os.path.exists(foto_png_id):
                    with open(foto_png_id, "rb") as f:
                        foto_url = f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
                elif os.path.exists(foto_jpg_id):
                    with open(foto_jpg_id, "rb") as f:
                        foto_url = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
                elif os.path.exists(foto_png_nome):
                    with open(foto_png_nome, "rb") as f:
                        foto_url = f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
                elif os.path.exists(foto_jpg_nome):
                    with open(foto_jpg_nome, "rb") as f:
                        foto_url = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
                
                if foto_url:
                    avatar_html = f"<img src='{foto_url}' style='width:100px; height:100px; object-fit:contain; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.6));'>"
                else:
                    avatar_html = f"<div style='width:90px; height:90px; border-radius:12px; background:#2a2a2a; border: 1px solid rgba(255,255,255,0.1); display:flex; justify-content:center; align-items:center; font-size:2.5rem; font-weight:900; color:#777; box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);'>{iniziali}</div>"
                
                html_figurina = f"""
                <div style='display:flex; align-items:center; padding:15px; border:1px solid rgba(255,255,255,0.1); border-radius:12px; margin-bottom:15px; background: linear-gradient(145deg, rgba(30,30,30,0.9), rgba(15,15,15,0.9)); box-shadow: 0 8px 20px rgba(0,0,0,0.4);'>
                    <div style='margin-right:20px;'>{avatar_html}</div>
                    <div style='flex-grow:1;'>
                        <div style='font-size:1.8rem; font-weight:900; line-height:1; color:#ffffff; text-transform:uppercase; letter-spacing:-0.5px; margin-bottom:8px;'>
                            {giocatore_selezionato}
                        </div>
                        <div style='display:flex; align-items:center; gap:10px;'>
                            <span class='badge-{ruolo_g}' style='font-size:0.9rem; padding:4px 8px;'>{ruolo_g}</span>
                            <span style='font-size:1.1rem; color:#bbb; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;'>{squadra_reale}</span>
                        </div>
                    </div>
                    <div style='text-align:right; border-left: 1px solid rgba(255,255,255,0.15); padding-left: 20px;'>
                        <div style='font-size:0.75rem; color:#888; text-transform:uppercase; font-weight:800; letter-spacing:1px; margin-bottom:2px;'>Quotazione</div>
                        <div style='font-size:2.2rem; font-weight:900; color:#10b981; line-height:1;'>{quotazione}</div>
                    </div>
                </div>
                """
                st.markdown(html_figurina, unsafe_allow_html=True)
                
                if is_admin and not spettatore_mode:
                    def on_asta_change():
                        st.session_state.costo_in_asta = st.session_state.get('costo_input', 1)
                        st.session_state.squadra_in_asta = st.session_state.get('squadra_input', '')
                        save_state()

                    cc1, cc2 = st.columns(2)
                    default_sq = st.session_state.get('squadra_in_asta') if st.session_state.get('squadra_in_asta') in st.session_state.squadre else (st.session_state.squadre[0] if st.session_state.squadre else None)
                    squadra_index = st.session_state.squadre.index(default_sq) if default_sq else 0
                    
                    squadra_acquirente = cc1.selectbox("Acquirente", st.session_state.squadre, index=squadra_index, key="squadra_input", on_change=on_asta_change)
                    costo = cc2.number_input("Prezzo", min_value=1, value=st.session_state.get('costo_in_asta', 1), step=1, key="costo_input", on_change=on_asta_change)
                    
                    if st.button("🔨 Assegna", type="primary", use_container_width=True):
                        stats = get_stats_squadra(squadra_acquirente)
                        limite_ruolo = st.session_state.config_ruoli.get(ruolo_g, 0)
                        
                        if costo > stats['max_spendibile']:
                            st.error(f"⚠️ {squadra_acquirente} max spendibile: {stats['max_spendibile']} cr.")
                        elif stats['ruoli'].get(ruolo_g, 0) >= limite_ruolo:
                            st.error(f"⚠️ Slot completati per {ruolo_g}.")
                        else:
                            st.session_state.assegnazioni.append({
                                'squadra': squadra_acquirente,
                                'giocatore': giocatore_selezionato,
                                'ruolo': ruolo_g,
                                'costo': costo
                            })
                            st.session_state.giocatore_in_asta = ""
                            st.session_state.costo_in_asta = 1
                            st.session_state.squadra_in_asta = ""
                            save_state()
                            st.rerun()
                else:
                    st.info("👀 Stai guardando. Solo il Banditore può assegnare il giocatore.")
                    curr_costo = st.session_state.get('costo_in_asta', 1)
                    st.markdown(f"""
                    <div style='background-color:#1e1e1e; padding:15px; border-radius:10px; border:2px solid #333; text-align:center;'>
                        <div style='font-size:1.1rem; color:#aaa; margin-bottom:5px;'>Puntata Attuale</div>
                        <div style='font-size:3rem; font-weight:900; color:#10b981; line-height:1;'>{curr_costo}</div>
                    </div>
                    """, unsafe_allow_html=True)

    st.divider()
    
    # --- SEZIONE INFERIORE (TABELLONE A COLONNE COMPATTO E MINIMIZZATO) ---
    st.markdown("### 📊 Tabellone Rose")
    
    num_squadre = len(st.session_state.squadre)
    # Impostiamo max 5 colonne per riga. 10 squadre = 2 righe da 5 (perfettamente leggibile).
    cols_per_row = 5 if num_squadre > 5 else max(1, num_squadre)
    
    for i in range(0, num_squadre, cols_per_row):
        row_squadre = st.session_state.squadre[i:i+cols_per_row]
        cols = st.columns(len(row_squadre))
        
        for j, sq in enumerate(row_squadre):
            stats = get_stats_squadra(sq)
            with cols[j]:
                with st.container(border=True):
                        # Intestazione molto compatta, rimossi i colori forzati bianchi per compatibilità Light/Dark mode
                        st.markdown(f"<div style='font-size:1.3rem; font-weight:900; border-bottom:1px solid #555; padding-bottom:3px;'>{sq}</div>", unsafe_allow_html=True)
                        
                        # Statistiche ingrandite e conteggio Ruoli esplicito
                        st.markdown(f"""
                        <div style='font-size:0.95rem; line-height:1.4; padding:5px 0;'>
                            Crediti: <b>{stats['rimanente']}</b> | Rilancio: <b style='color:#10b981'>{stats['max_spendibile']}</b><br>
                            <span style='color:#f59e0b; font-weight:bold;'>P: {stats['ruoli']['P']}/{st.session_state.config_ruoli['P']}</span> &nbsp;
                            <span style='color:#10b981; font-weight:bold;'>D: {stats['ruoli']['D']}/{st.session_state.config_ruoli['D']}</span> &nbsp;
                            <span style='color:#3b82f6; font-weight:bold;'>C: {stats['ruoli']['C']}/{st.session_state.config_ruoli['C']}</span> &nbsp;
                            <span style='color:#ef4444; font-weight:bold;'>A: {stats['ruoli']['A']}/{st.session_state.config_ruoli['A']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if not stats['assegnati']:
                            st.caption("Nessun giocatore")
                        else:
                            ruoli_ordinati = ['P', 'D', 'C', 'A']
                            first_role = True
                            for r in ruoli_ordinati:
                                giocatori_r = [g for g in stats['assegnati'] if g['ruolo'] == r]
                                if giocatori_r:
                                    col_hex = get_ruolo_colore(r)
                                    m_top = "2px" if first_role else "-8px"
                                    m_bottom = "14px" if spettatore_mode else "4px"
                                    st.markdown(f"<div style='border-bottom:1px solid {col_hex}; margin-top:{m_top}; margin-bottom:{m_bottom}; font-weight:800; color:{col_hex}; font-size:0.8rem;'>{r}</div>", unsafe_allow_html=True)
                                    first_role = False
                                    
                                    # Giocatori super compatti con bottone Modal (Tasto senza freccia)
                                    for g in giocatori_r:
                                        g_m_bottom = "10px" if spettatore_mode else "-2px"
                                        html_g = f"<div style='margin-top:-2px; margin-bottom:{g_m_bottom}; display:flex; align-items:center; white-space:nowrap; overflow:hidden; min-height: 24px;'><span class='badge-{r}'>{r}</span> <span class='player-name-compact' style='margin-left:4px; margin-right:4px;'>{g['giocatore']}</span> <span class='player-cost-compact'>({g['costo']})</span></div>"
                                        c1, c2 = st.columns([6, 1])
                                        c1.markdown(html_g, unsafe_allow_html=True)
                                        with c2:
                                            if not spettatore_mode:
                                                if st.button("⚙️", key=f"edit_{sq}_{g['giocatore']}", help="Modifica", type="tertiary"):
                                                    modal_modifica_giocatore(g['giocatore'], g['costo'], sq)
