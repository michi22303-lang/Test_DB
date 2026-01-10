import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# --- ALTE FUNKTIONEN (für Michis Test) ---
def insert_messwert(kategorie, wert, kommentar):
    supabase = init_connection()
    data = {"kategorie": kategorie, "wert": wert, "kommentar": kommentar}
    return supabase.table("Michis Test").insert(data).execute() # Ggf. tabellenname anpassen

def get_all_messwerte():
    supabase = init_connection()
    return supabase.table("Michis Test").select("*").execute().data

# --- NEUE FUNKTIONEN (für Digital Projects) ---
def insert_bulk_projects(data_list):
    """Speichert viele Projekte auf einmal (für den Generator)"""
    supabase = init_connection()
    # Supabase erlaubt Bulk-Inserts, wenn man eine Liste von Dictionaries übergibt
    response = supabase.table("digital_projects").insert(data_list).execute()
    return response

def get_projects():
    """Lädt die Projektdaten"""
    supabase = init_connection()
    return supabase.table("digital_projects").select("*").execute().data

def delete_project(id):
    supabase = init_connection()
    return supabase.table("digital_projects").delete().eq("id", id).execute()
