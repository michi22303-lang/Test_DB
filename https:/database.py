import streamlit as st
from supabase import create_client, Client

# Verbindung aufbauen (nutzt den Cache, damit es schnell bleibt)
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# Funktion 1: Daten speichern
def insert_messwert(kategorie, wert, kommentar):
    supabase = init_connection()
    # Hier bauen wir das Dictionary für deine Spalten
    # Deine Spalte heißt "wert", also muss der Key hier auch "wert" heißen!
    data = {
        "Kategorie": kategorie, 
        "wert": wert,          # Deine Spalte in Supabase
        "kommentar": kommentar
    }
    
    # ACHTUNG: Tabellenname muss exakt stimmen. 
    # Bei "Michis Test" muss er in Anführungszeichen stehen.
    response = supabase.table("Michis Test").insert(data).execute()
    return response

# Funktion 2: Daten laden
def get_all_messwerte():
    supabase = init_connection()
    # Auch hier den richtigen Tabellennamen nutzen
    response = supabase.table("Michis Test").select("*").execute()
    return response.data

# --- Funktion 3: LÖSCHEN ---
def delete_messwert(id):
    """Löscht einen Eintrag anhand seiner ID."""
    supabase = init_connection()
    # Wir sagen: Lösche aus Tabelle "Michis Test", wo die Spalte "id" gleich dem übergebenen Wert ist.
    response = supabase.table("Michis Test").delete().eq("id", id).execute()
    return response
