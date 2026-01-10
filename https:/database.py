import streamlit as st
from supabase import create_client, Client

# Wir holen die Zugangsdaten sicher aus den Streamlit Secrets (nicht hardcoden!)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

def init_connection():
    return create_client(url, key)

def save_data(table_name, data_dict):
    """Speichert ein Dictionary in der Datenbank"""
    supabase = init_connection()
    data = supabase.table(table_name).insert(data_dict).execute()
    return data

def load_data(table_name):
    """Lädt alle Daten aus einer Tabelle"""
    supabase = init_connection()
    response = supabase.table(table_name).select("*").execute()
    return response.data
