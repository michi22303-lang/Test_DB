import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# --- PROJEKTE (PLAN) ---
def insert_bulk_projects(data_list):
    supabase = init_connection()
    return supabase.table("digital_projects").insert(data_list).execute()

def get_projects():
    supabase = init_connection()
    return supabase.table("digital_projects").select("*").execute().data

def delete_all_projects():
    supabase = init_connection()
    return supabase.table("digital_projects").delete().neq("id", 0).execute()

# --- STATS (FTE/Umsatz) ---
def insert_bulk_stats(data_list):
    supabase = init_connection()
    return supabase.table("company_stats").insert(data_list).execute()

def get_stats():
    supabase = init_connection()
    return supabase.table("company_stats").select("*").execute().data

def delete_all_stats():
    supabase = init_connection()
    return supabase.table("company_stats").delete().neq("id", 0).execute()

# --- NEU: ACTUALS (IST-KOSTEN) ---
def insert_bulk_actuals(data_list):
    supabase = init_connection()
    return supabase.table("project_actuals").insert(data_list).execute()

def get_actuals():
    supabase = init_connection()
    return supabase.table("project_actuals").select("*").execute().data

def delete_all_actuals():
    supabase = init_connection()
    return supabase.table("project_actuals").delete().neq("id", 0).execute()
