import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import random
import time

# --- DATABASE IMPORTS ---
# Wir gehen davon aus, dass database.py unverändert ist und funktioniert
from database import insert_bulk_projects, get_projects, insert_bulk_stats, get_stats, delete_all_projects, delete_all_stats, insert_bulk_actuals, get_actuals, delete_all_actuals

st.set_page_config(page_title="CIO Cockpit 12.0 - Stable", layout="wide", page_icon="🏢")

# --- HELPER ---
def fmt_de(value, decimals=0, suffix="€"):
    if value is None or pd.isna(value): return "0 " + suffix
    try:
        s = f"{value:,.{decimals}f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{s} {suffix}".strip()
    except: return str(value)

# --- SESSION STATE ---
if 'wizard_step' not in st.session_state: st.session_state.wizard_step = 1
if 'wiz_data' not in st.session_state: st.session_state.wiz_data = {}

# --- DATEN LADEN & BEREINIGEN (ROBUST) ---
@st.cache_data(ttl=5) # Cache für 5 Sekunden, damit es snappy bleibt
def load_all_data():
    try:
        # 1. Projekte laden
        p = get_projects()
        df_p = pd.DataFrame(p) if p else pd.DataFrame()
        if not df_p.empty: 
            df_p.columns = df_p.columns.str.lower() # Alles klein schreiben
            # Sicherstellen, dass numeric Spalten auch numeric sind
            df_p['cost_planned'] = pd.to_numeric(df_p['cost_planned'], errors='coerce').fillna(0)
            df_p['year'] = pd.to_numeric(df_p['year'], errors='coerce').fillna(0).astype(int)

        # 2. Stats laden
        s = get_stats()
        df_s = pd.DataFrame(s) if s else pd.DataFrame()
        if not df_s.empty: 
            df_s.columns = df_s.columns.str.lower()
        
        # 3. Actuals laden
        a = get_actuals()
        df_a = pd.DataFrame(a) if a else pd.DataFrame()
        if not df_a.empty: 
            df_a.columns = df_a.columns.str.lower()
            df_a['cost_actual'] = pd.to_numeric(df_a['cost_actual'], errors='coerce').fillna(0)
            
        return df_p, df_s, df_a
    except Exception as e:
        st.error(f"Kritischer Fehler beim Laden: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_proj, df_stats, df_act = load_all_data()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3094/3094851.png", width=50)
    st.markdown("### Digital Strategy Board")
    
    # Dark Mode Logik
    dark_mode = st.toggle("🌙 Dark Mode", value=False)
    template = "plotly_dark" if dark_mode else "plotly_white"
    bg_color = "#0e1117" if dark_mode else "#ffffff"
    card_bg = "#262730" if dark_mode else "#f0f2f6"
    text_col = "#ffffff" if dark_mode else "#31333F"

    selected = option_menu(
        "Hauptmenü",
        ["Dashboard", "1. OPEX Basis 2026", "2. Projekt-Planung", "Analyse & Portfolio", "Daten-Manager"],
        icons=["speedometer2", "bank", "pencil-square", "pie-chart", "database-gear"],
        default_index=0,
    )
    
    st.divider()
    if st.checkbox("🔧 Rohdaten prüfen"):
        st.write("Projekte:", len(df_proj), "Zeilen")
        st.write("Actuals:", len(df_act), "Zeilen")
        if not df_proj.empty: st.dataframe(df_proj.head(3))

# --- CSS INJECTION ---
st.markdown(f"""
<style>
    .stApp {{background-color: {bg_color};}}
    div.css-card {{
        background-color: {card_bg};
        padding: 15px; border-radius: 10px;
        border-left: 5px solid #6c5ce7;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    h1, h2, h3, p, span, div {{ color: {text_col} !important; }}
    [data-testid="stMetricValue"] {{ color: {text_col} !important; }}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# TAB 1: DASHBOARD (FLEXIBEL)
# ------------------------------------------------------------------
if selected == "Dashboard":
    st.title("📊 Management Dashboard")

    if df_proj.empty:
        st.info("⚠️ Die Datenbank ist leer. Bitte gehe zum 'Daten-Manager' und klicke 'Historie generieren'.")
    else:
        # 1. Welches ist das aktuellste Jahr mit Daten?
        max_year = int(df_proj['year'].max())
        
        # 2. Daten filtern
        # Ist-Daten (Actuals) aus der Vergangenheit
        df_hist = df_proj[df_proj['scenario'] == 'Actual'].copy()
        
        # Plan-Daten (2026) - Alles was NICHT Actual ist
        df_plan_2026 = df_proj[(df_proj['year'] == 2026) & (df_proj['scenario'] != 'Actual')].copy()
        
        # 3. Bestimmen, was wir anzeigen
        if not df_plan_2026.empty:
            display_year = 2026
            display_mode = "Planung 2026"
            total_budget = df_plan_2026['cost_planned'].sum()
            df_display = df_plan_2026
        else:
            display_year = max_year
            display_mode = f"Ist-Daten {display_year}"
            df_display = df_hist[df_hist['year'] == display_year]
            total_budget = df_display['cost_planned'].sum()

        # Ist-Kosten (Actuals aus Tabelle project_actuals)
        actuals_sum = 0
        if not df_act.empty:
            actuals_sum = df_act[df_act['year'] == display_year]['cost_actual'].sum()

        # --- KPIs ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Budget ({display_mode})", fmt_de(total_budget, 0))
        c2.metric(f"Ist-Kosten ({display_year})", fmt_de(actuals_sum, 0), delta=f"{actuals_sum/total_budget*100:.1f}%" if total_budget>0 else "")
        
        opex = df_display[df_display['budget_type'] == 'OPEX']['cost_planned'].sum()
        capex = df_display[df_display['budget_type'] == 'CAPEX']['cost_planned'].sum()
        
        c3.metric("Davon Betrieb (OPEX)", fmt_de(opex, 0))
        c4.metric("Davon Projekte (CAPEX)", fmt_de(capex, 0))

        st.divider()

        # --- CHARTS ---
        col_main, col_side = st.columns([2, 1])
        
        with col_main:
            st.subheader("Budget-Entwicklung (Historie + Plan)")
            # Wir bauen einen DataFrame für den Chart: Historie + Plan
            chart_data = df_hist.groupby(['year'])['cost_planned'].sum().reset_index()
            chart_data['Type'] = 'Ist'
            
            if not df_plan_2026.empty:
                plan_row = pd.DataFrame({'year': [2026], 'cost_planned': [total_budget], 'Type': ['Plan']})
                chart_data = pd.concat([chart_data, plan_row])
            
            fig = px.bar(chart_data, x='year', y='cost_planned', color='Type', text_auto='.2s',
                         color_discrete_map={'Ist': '#636e72', 'Plan': '#6c5ce7'})
            fig.update_layout(template=template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        with col_side:
            st.subheader(f"Split {display_year}")
            fig_pie = px.pie(df_display, values='cost_planned', names='category', hole=0.5)
            fig_pie.update_layout(template=template, showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)

# ------------------------------------------------------------------
# TAB 2: OPEX BASIS (WIZARD)
# ------------------------------------------------------------------
elif selected == "1. OPEX Basis 2026":
    st.title("🧱 OPEX Basis 2026 festlegen")
    
    # Prüfen ob schon da
    existing_opex = df_proj[(df_proj['year'] == 2026) & (df_proj['scenario'] == 'Budget 2026 (Fixed)')]
    
    if not existing_opex.empty:
        st.success("✅ OPEX-Basis für 2026 steht bereits.")
        st.metric("Fixer Betrag", fmt_de(existing_opex['cost_planned'].sum()))
        if st.button("🗑️ Löschen & Neu planen"):
            # Workaround: Wir können hier nur schwer löschen ohne spezifische SQL
            st.warning("Bitte nutze den 'Daten-Manager' -> 'Reset' für einen sauberen Neustart.")
    else:
        # Historie holen (nur OPEX)
        hist_opex = df_proj[(df_proj['budget_type'] == 'OPEX') & (df_proj['scenario'] == 'Actual')]
        
        if hist_opex.empty:
            st.warning("Keine historischen OPEX-Daten für eine Berechnung.")
        else:
            last_val = hist_opex[hist_opex['year'] == 2025]['cost_planned'].sum()
            st.write(f"OPEX Wert 2025 war: **{fmt_de(last_val)}**")
            
            c1, c2 = st.columns(2)
            if c1.button("👉 Flat übernehmen (wie 2025)"):
                new_data = hist_opex[hist_opex['year'] == 2025].copy()
                new_data['year'] = 2026
                new_data['scenario'] = 'Budget 2026 (Fixed)'
                if 'id' in new_data: del new_data['id']
                if 'created_at' in new_data: del new_data['created_at']
                insert_bulk_projects(new_data.to_dict('records'))
                st.rerun()
                
            if c2.button("👉 Inflation (+4%)"):
                new_data = hist_opex[hist_opex['year'] == 2025].copy()
                new_data['year'] = 2026
                new_data['scenario'] = 'Budget 2026 (Fixed)'
                new_data['cost_planned'] *= 1.04
                if 'id' in new_data: del new_data['id']
                if 'created_at' in new_data: del new_data['created_at']
                insert_bulk_projects(new_data.to_dict('records'))
                st.rerun()

# ------------------------------------------------------------------
# TAB 3: PROJEKT PLANUNG (WIZARD)
# ------------------------------------------------------------------
elif selected == "2. Projekt-Planung":
    st.title("🚀 Neue Projekte planen")
    
    step = st.session_state.wizard_step
    
    # Fortschritt
    c1, c2, c3 = st.columns(3)
    c1.write(f"1. Daten {'✅' if step>1 else ''}")
    c2.write(f"2. Geld {'✅' if step>2 else ''}")
    c3.write(f"3. Ende {'✅' if step>3 else ''}")
    st.progress(step/3)
    
    if step == 1:
        with st.form("s1"):
            st.subheader("Was planen wir?")
            n = st.text_input("Name", value=st.session_state.wiz_data.get('project_name',''))
            c = st.selectbox("Kategorie", ["Cloud", "Workplace", "ERP", "Security", "Infra"])
            if st.form_submit_button("Weiter"):
                if n: 
                    st.session_state.wiz_data.update({'project_name':n, 'category':c, 'year':2026})
                    st.session_state.wizard_step=2
                    st.rerun()
                else: st.error("Name fehlt")
                
    elif step == 2:
        with st.form("s2"):
            st.subheader("Kosten?")
            t = st.radio("Typ", ["CAPEX", "OPEX"])
            cost = st.number_input("Betrag (€)", value=10000.0, step=1000.0)
            if st.form_submit_button("Weiter"):
                st.session_state.wiz_data.update({'budget_type':t, 'cost_planned':cost})
                st.session_state.wizard_step=3
                st.rerun()
                
    elif step == 3:
        st.subheader("Zusammenfassung")
        st.write(st.session_state.wiz_data)
        if st.button("💾 Speichern"):
            d = st.session_state.wiz_data.copy()
            d['scenario'] = 'Planned Project' # WICHTIG: Damit wir es unterscheiden können
            d['status'] = 'Planned'
            d['opex_type'] = 'Project'
            d['risk_factor'] = 3
            d['strategic_score'] = 5
            d['savings_planned'] = 0
            
            insert_bulk_projects([d])
            st.success("Projekt angelegt!")
            st.session_state.wiz_data = {}
            st.session_state.wizard_step = 1
            time.sleep(1)
            st.rerun()

# ------------------------------------------------------------------
# TAB 4: ANALYSE
# ------------------------------------------------------------------
elif selected == "Analyse & Portfolio":
    st.title("🔍 Deep Dive")
    if not df_proj.empty:
        # Sunburst
        st.subheader("Kostenverteilung")
        fig = px.sunburst(df_proj[df_proj['year']==2026], path=['scenario', 'budget_type', 'category', 'project_name'], values='cost_planned')
        fig.update_layout(template=template)
        st.plotly_chart(fig, use_container_width=True)
        
        # Portfolio
        st.subheader("Portfolio Matrix")
        # Filtern auf alles was nicht Actual ist
        df_plan = df_proj[df_proj['scenario'] != 'Actual']
        if not df_plan.empty:
            fig2 = px.scatter(df_plan, x='strategic_score', y='risk_factor', size='cost_planned', color='category', hover_name='project_name', size_max=50)
            fig2.update_layout(template=template)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Noch keine Projekte geplant.")

# ------------------------------------------------------------------
# TAB 5: DATEN MANAGER (DER WICHTIGE TEIL)
# ------------------------------------------------------------------
elif selected == "Daten-Manager":
    st.title("💾 Daten-Zentrale")
    
    t1, t2, t3 = st.tabs(["🎲 Historie Generieren", "📅 Ist-Werte (2026)", "⚠️ Reset"])
    
    with t1:
        st.markdown("**Erzeugt Daten für 2022, 2023, 2024, 2025 (Actuals)**")
        if st.button("🚀 Historie generieren (2022-2025)"):
            delete_all_projects(); delete_all_stats(); delete_all_actuals()
            
            projs = []
            years = [2022, 2023, 2024, 2025]
            
            for y in years:
                # 1. OPEX Basis
                fte = int(500 * (1.05 ** (y-2022)))
                projs.append({"project_name": "M365 Lizenzen", "category": "Workplace", "budget_type": "OPEX", "year": y, "cost_planned": fte*1200, "scenario": "Actual", "status": "Live"})
                projs.append({"project_name": "SAP Wartung", "category": "ERP", "budget_type": "OPEX", "year": y, "cost_planned": 250000, "scenario": "Actual", "status": "Live"})
                
                # 2. CAPEX Projekte (zufällig)
                for i in range(3):
                    projs.append({
                        "project_name": f"Projekt {y}-{i}", 
                        "category": random.choice(["Cloud", "Security", "Infra"]),
                        "budget_type": "CAPEX",
                        "year": y,
                        "cost_planned": random.randint(50000, 300000),
                        "scenario": "Actual",
                        "status": "Closed"
                    })
            
            insert_bulk_projects(projs)
            st.success("Historie erfolgreich erstellt!")
            time.sleep(1)
            st.rerun()

    with t2:
        st.subheader("Ist-Buchungen für 2026 simulieren")
        m = st.selectbox("Monat wählen", range(1, 13))
        
        if st.button(f"💸 Ist-Kosten für Monat {m} buchen"):
            # Wir suchen Projekte, die für 2026 geplant sind
            plan_26 = df_proj[(df_proj['year'] == 2026) & (df_proj['scenario'] != 'Actual')]
            
            if plan_26.empty:
                st.error("Kein Budget für 2026 gefunden. Bitte erst OPEX Basis oder Projekte planen.")
            else:
                acts = []
                for _, row in plan_26.iterrows():
                    # Wir simulieren eine Buchung (ca. 1/12 vom Budget +/- 20%)
                    val = (row['cost_planned'] / 12) * random.uniform(0.8, 1.2)
                    acts.append({
                        "project_id": row['id'],
                        "year": 2026,
                        "month": m,
                        "cost_actual": val
                    })
                insert_bulk_actuals(acts)
                st.success(f"Buchungen für Monat {m} angelegt.")
                time.sleep(1)
                st.rerun()

    with t3:
        if st.button("🔥 ALLES LÖSCHEN"):
            delete_all_projects()
            delete_all_stats()
            delete_all_actuals()
            st.success("Datenbank ist leer.")
            time.sleep(1)
            st.rerun()
