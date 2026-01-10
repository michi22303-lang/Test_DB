import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# --- PROJEKTE ---
def insert_bulk_projects(data_list):
    supabase = init_connection()
    return supabase.table("digital_projects").insert(data_list).execute()

def get_projects():
    supabase = init_connection()
    return supabase.table("digital_projects").select("*").execute().data

def delete_project(id):
    supabase = init_connection()
    return supabase.table("digital_projects").delete().eq("id", id).execute()

def delete_all_projects(): # Vorsicht!
    supabase = init_connection()
    # Trick um alles zu löschen: ID größer als 0
    return supabase.table("digital_projects").delete().neq("id", 0).execute()

# --- NEU: COMPANY STATS ---
def insert_bulk_stats(data_list):
    supabase = init_connection()
    return supabase.table("company_stats").insert(data_list).execute()

def get_stats():
    supabase = init_connection()
    return supabase.table("company_stats").select("*").execute().data

def delete_all_stats():
    supabase = init_connection()
    return supabase.table("company_stats").delete().neq("id", 0).execute()
