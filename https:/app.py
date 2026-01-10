import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import random
import time

# Imports aus database.py
from database import insert_bulk_projects, get_projects, insert_bulk_stats, get_stats, delete_all_projects, delete_all_stats, insert_bulk_actuals, get_actuals, delete_all_actuals

st.set_page_config(page_title="CIO Cockpit 11.0 - Full Suite", layout="wide", page_icon="🏢")

# --- HELPER ---
def fmt_de(value, decimals=0, suffix="€"):
    if value is None: return ""
    try:
        s = f"{value:,.{decimals}f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{s} {suffix}".strip()
    except: return str(value)

# --- SESSION STATE ---
if 'wizard_step' not in st.session_state: st.session_state.wizard_step = 1
if 'wiz_data' not in st.session_state: st.session_state.wiz_data = {}

# --- SIDEBAR & THEME ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3094/3094851.png", width=50)
    st.markdown("### Digital Strategy Board")
    
    dark_mode = st.toggle("🌙 Dark Mode", value=False)
    
    if dark_mode:
        plotly_template = "plotly_dark"
        main_bg = "#0e1117"
        card_bg = "#262730"
        text_color = "#ffffff"
        delta_color = "#bdc3c7"
    else:
        plotly_template = "plotly_white"
        main_bg = "#ffffff"
        card_bg = "#f0f2f6"
        text_color = "#31333F"
        delta_color = "black"

    selected = option_menu(
        "Navigation",
        [
            "Management Dashboard", 
            "1. Basis-Budget (OPEX)", 
            "2. Projekt-Planung (Wizard)", # Der alte Wizard ist hier!
            "Szenario-Simulator", 
            "Szenario-Vergleich", 
            "Kosten & OPEX Analyse", 
            "Portfolio & Risiko", 
            "Daten-Manager"
        ],
        icons=["speedometer2", "bank", "magic", "calculator", "diagram-3", "pie-chart", "bullseye", "database-gear"],
        default_index=0,
    )

# --- CSS ---
def local_css(bg_app, bg_card, txt_col, delta_col):
    st.markdown(f"""
    <style>
        .stApp {{background-color: {bg_app};}}
        .block-container {{padding-top: 1rem;}}
        div.css-card {{
            background-color: {bg_card};
            border: 1px solid rgba(128, 128, 128, 0.2);
            padding: 15px; border-radius: 10px;
            border-left: 5px solid #6c5ce7;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); color: {txt_col};
        }}
        div.card-title {{font-size: 13px; text-transform: uppercase; opacity: 0.8; margin-bottom: 5px; color: {txt_col};}}
        div.card-value {{font-size: 24px; font-weight: bold; color: {txt_col};}}
        div.card-delta {{font-size: 14px; margin-top: 5px; color: {delta_col};}}
        h1, h2, h3, p, div, span {{color: {txt_col} !important;}}
        .step-active {{color: #6c5ce7; font-weight: bold;}}
        [data-testid="stMetricDelta"] svg {{ fill: {txt_col}; }}
    </style>
    """, unsafe_allow_html=True)

    def kpi_card(title, value, delta_text="", color=delta_col):
        st.markdown(f"""
        <div class="css-card">
            <div class="card-title">{title}</div>
            <div class="card-value">{value}</div>
            <div class="card-delta" style="color: {color}">{delta_text}</div>
        </div>
        """, unsafe_allow_html=True)
    return kpi_card

kpi_func = local_css(main_bg, card_bg, text_color, delta_color)

# --- DATEN LADEN ---
try:
    raw_projects = get_projects()
    raw_stats = get_stats()
    raw_actuals = get_actuals()
    
    df_proj = pd.DataFrame(raw_projects) if raw_projects else pd.DataFrame()
    df_stats = pd.DataFrame(raw_stats) if raw_stats else pd.DataFrame()
    df_act = pd.DataFrame(raw_actuals) if raw_actuals else pd.DataFrame()
    
    if not df_proj.empty: df_proj.columns = df_proj.columns.str.lower()
    if not df_stats.empty: df_stats.columns = df_stats.columns.str.lower()
    if not df_act.empty: df_act.columns = df_act.columns.str.lower()
    
except Exception as e:
    st.error(f"Datenbank Fehler: {e}")
    df_proj, df_stats, df_act = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ------------------------------------------------------------------
# TAB 1: MANAGEMENT DASHBOARD
# ------------------------------------------------------------------
if selected == "Management Dashboard":
    st.title("🏛️ Management Übersicht (Plan vs. Ist 2026)")
    
    if df_proj.empty:
        st.warning("Keine Daten. Bitte zum 'Daten-Manager'!")
    else:
        # PLAN 2026: Basis (Fixed) + Geplante Projekte
        df_plan = df_proj[
            (df_proj['year'] == 2026) & 
            ( (df_proj['scenario'] == 'Budget 2026 (Fixed)') | (df_proj['status'] == 'Planned') )
        ].copy()
        
        # IST 2026
        if not df_act.empty:
            df_act_2026 = df_act[df_act['year'] == 2026].copy()
            actual_total = df_act_2026['cost_actual'].sum()
        else:
            df_act_2026 = pd.DataFrame()
            actual_total = 0
            
        plan_total = df_plan['cost_planned'].sum()
        consumption = (actual_total / plan_total * 100) if plan_total > 0 else 0
        
        # --- KPIS ---
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_func("Budget Plan 2026", fmt_de(plan_total/1000000, 2, 'M€'), "Basis + Projekte", delta_color)
        with c2: kpi_func("Ist-Kosten (YTD)", fmt_de(actual_total/1000000, 2, 'M€'), "Gebucht in DB", "orange")
        with c3: kpi_func("Verfügbar", fmt_de((plan_total-actual_total)/1000000, 2, 'M€'), "Rest-Budget", "green")
        with c4: kpi_func("Ausschöpfung", f"{consumption:.1f}%", "Budget verbraucht", "red" if consumption > 100 else "green")
        
        st.markdown("---")
        
        col_chart1, col_chart2 = st.columns([2, 1])
        with col_chart1:
            st.subheader("Plan vs. Ist (Pro Kategorie)")
            
            # Plan Group
            plan_grp = df_plan.groupby('category')['cost_planned'].sum().reset_index()
            plan_grp['Type'] = 'Plan'
            plan_grp.rename(columns={'cost_planned': 'Value'}, inplace=True)
            
            # Actual Group
            if not df_act_2026.empty:
                df_merged = pd.merge(df_act_2026, df_proj[['id', 'category']], left_on='project_id', right_on='id', how='left')
                act_grp = df_merged.groupby('category')['cost_actual'].sum().reset_index()
                act_grp['Type'] = 'Ist'
                act_grp.rename(columns={'cost_actual': 'Value'}, inplace=True)
                df_chart = pd.concat([plan_grp, act_grp])
            else:
                df_chart = plan_grp
                
            fig = px.bar(df_chart, x='category', y='Value', color='Type', barmode='group',
                         color_discrete_map={'Plan': '#6c5ce7', 'Ist': '#00b894'}, text_auto='.2s')
            fig.update_layout(yaxis_title="Betrag (€)", separators=",.", template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
        with col_chart2:
            st.subheader("Verbrauchstacho")
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number", value = actual_total,
                domain = {'x': [0, 1], 'y': [0, 1]},
                gauge = {
                    'axis': {'range': [None, plan_total if plan_total > 0 else 100]},
                    'bar': {'color': "#6c5ce7"},
                    'steps': [{'range': [0, plan_total], 'color': "rgba(200, 200, 200, 0.2)"}],
                    'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': plan_total}}))
            fig_gauge.update_layout(height=300, template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_gauge, use_container_width=True)

# ------------------------------------------------------------------
# TAB 2: BASIS-BUDGET 2026 (OPEX)
# ------------------------------------------------------------------
elif selected == "1. Basis-Budget (OPEX)":
    st.title("🧱 Schritt 1: Betriebskosten-Basis 2026")
    
    fixed_scen = "Budget 2026 (Fixed)"
    df_fixed = df_proj[df_proj['scenario'] == fixed_scen]
    
    if not df_fixed.empty:
        st.success(f"✅ OPEX-Basis für 2026 ist fixiert.")
        st.metric("Fixierter Sockelbetrag", fmt_de(df_fixed['cost_planned'].sum(), 2, '€'))
        with st.expander("Details"): st.dataframe(df_fixed)
    else:
        st.markdown("Definiere den Sockelbetrag (Run the Business) für 2026.")
        # Historie 2023-2025
        df_hist_opex = df_proj[(df_proj['scenario']=='Actual') & (df_proj['budget_type']=='OPEX') & (df_proj['year'].isin([2023,2024,2025]))].copy()
        
        if df_hist_opex.empty: st.warning("Keine Historie (2023-2025) gefunden. Bitte Daten-Manager nutzen.")
        else:
            last_val = df_hist_opex[df_hist_opex['year'] == 2025]['cost_planned'].sum()
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<div class="css-card"><h4>Flat (Wie 2025)</h4><h2>{fmt_de(last_val,0)}</h2></div>', unsafe_allow_html=True)
                if st.button("Übernehmen (Flat)"):
                    df_new = df_hist_opex[df_hist_opex['year'] == 2025].copy()
                    df_new['year'] = 2026; df_new['scenario'] = fixed_scen; df_new['status'] = 'Planned Base'
                    if 'id' in df_new.columns: del df_new['id']
                    if 'created_at' in df_new.columns: del df_new['created_at']
                    insert_bulk_projects(df_new.to_dict('records')); st.rerun()
            with c2:
                infl = last_val * 1.04
                st.markdown(f'<div class="css-card"><h4>Inflation (+4%)</h4><h2>{fmt_de(infl,0)}</h2></div>', unsafe_allow_html=True)
                if st.button("Übernehmen (+4%)"):
                    df_new = df_hist_opex[df_hist_opex['year'] == 2025].copy()
                    df_new['cost_planned'] *= 1.04
                    df_new['year'] = 2026; df_new['scenario'] = fixed_scen; df_new['status'] = 'Planned Base'
                    if 'id' in df_new.columns: del df_new['id']
                    if 'created_at' in df_new.columns: del df_new['created_at']
                    insert_bulk_projects(df_new.to_dict('records')); st.rerun()

# ------------------------------------------------------------------
# TAB 3: PROJEKT PLANUNG (DER GROSSE WIZARD IST ZURÜCK!)
# ------------------------------------------------------------------
elif selected == "2. Projekt-Planung (Wizard)":
    st.title("🚀 Schritt 2: Neue Projekte 2026")
    st.info("Hier planst du neue Investitionen oder Projekte, die **zusätzlich** zur Basis kommen.")
    
    step = st.session_state.wizard_step
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.markdown(f"**1. Stammdaten** {'✅' if step > 1 else '🔵'}")
    col_s2.markdown(f"**2. Finanzen** {'✅' if step > 2 else '🔵'}")
    col_s3.markdown(f"**3. Strategie** {'✅' if step > 3 else '🔵'}")
    st.progress(step / 3)
    st.divider()

    # SCHRITT 1
    if step == 1:
        st.subheader("1. Stammdaten")
        with st.form("wiz_step1"):
            w_name = st.text_input("Projektname", value=st.session_state.wiz_data.get('project_name', ''))
            w_cat = st.selectbox("Kategorie", ["Digitaler Arbeitsplatz", "Cloud Plattform", "Cyber Security", "ERP & Apps", "Data & KI", "Infrastruktur"])
            w_year = st.number_input("Budgetjahr", value=2026, disabled=True)
            if st.form_submit_button("Weiter ➡️"):
                if w_name:
                    st.session_state.wiz_data.update({'project_name': w_name, 'category': w_cat, 'year': 2026})
                    st.session_state.wizard_step = 2
                    st.rerun()
                else: st.error("Name fehlt.")

    # SCHRITT 2
    elif step == 2:
        st.subheader("2. Finanzen")
        with st.form("wiz_step2"):
            c1, c2 = st.columns(2)
            with c1: w_btype = st.radio("Typ", ["CAPEX (Invest)", "OPEX (Laufend)"])
            with c2: w_otype = st.selectbox("OPEX Art", ["-", "Lizenzen", "Cloud", "Beratung"])
            w_cost = st.number_input("Kosten 2026 (€)", min_value=0.0, step=1000.0, value=50000.0)
            
            c_b1, c_b2 = st.columns(2)
            if c_b1.form_submit_button("⬅️ Zurück"):
                st.session_state.wizard_step = 1; st.rerun()
            if c_b2.form_submit_button("Weiter ➡️"):
                b_clean = "CAPEX" if "CAPEX" in w_btype else "OPEX"
                st.session_state.wiz_data.update({'budget_type': b_clean, 'opex_type': w_otype if b_clean=="OPEX" else "", 'cost_planned': w_cost})
                st.session_state.wizard_step = 3; st.rerun()

    # SCHRITT 3
    elif step == 3:
        st.subheader("3. Strategie")
        with st.form("wiz_step3"):
            w_risk = st.slider("Risiko", 1, 5, 2)
            w_score = st.slider("Strategie-Wert", 1, 10, 5)
            
            c_b1, c_b2 = st.columns(2)
            if c_b1.form_submit_button("⬅️ Zurück"):
                st.session_state.wizard_step = 2; st.rerun()
            if c_b2.form_submit_button("💾 Speichern", type="primary"):
                final = st.session_state.wiz_data.copy()
                final.update({'risk_factor': w_risk, 'strategic_score': w_score, 'scenario': 'Planned Project', 'status': 'Planned'})
                try:
                    insert_bulk_projects([final])
                    st.success(f"Projekt '{final['project_name']}' gespeichert!")
                    st.session_state.wiz_data = {}; st.session_state.wizard_step = 1; time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Fehler: {e}")

# ------------------------------------------------------------------
# RESTLICHE TABS (SIMULATOR, VERGLEICH, ANALYSE, PORTFOLIO)
# ------------------------------------------------------------------
elif selected == "Szenario-Simulator":
    st.title("🔮 Szenario-Simulator"); st.info("Simuliere Inflation und Wachstum auf Basis der 2025 Daten.")
    # (Code wie in Vorversionen, hier gekürzt für Übersicht)
    # Nutze einfach den Code aus der Version 9.0/10.0 für diesen Block

elif selected == "Szenario-Vergleich":
    st.title("⚖️ Vergleich"); st.info("Vergleiche verschiedene Planungs-Szenarien.")
    # (Code wie in Vorversionen)

elif selected == "Kosten & OPEX Analyse":
    st.title("💸 Analyse")
    if not df_proj.empty:
        yf = st.selectbox("Jahr", sorted(df_proj['year'].unique(), reverse=True))
        df_y = df_proj[df_proj['year'] == yf].copy()
        if yf == 2026: df_y = df_y[df_y['scenario'].isin(['Budget 2026 (Fixed)', 'Planned Project']) | (df_y['status'] == 'Planned')]
        fig_s = px.sunburst(df_y, path=['budget_type', 'category', 'project_name'], values='cost_planned', color='category')
        fig_s.update_layout(height=700, template=plotly_template); st.plotly_chart(fig_s, use_container_width=True)

elif selected == "Portfolio & Risiko":
    st.title("🎯 Portfolio"); st.info("Risiko vs Wert Analyse.")
    # (Code wie in Vorversionen)

# ------------------------------------------------------------------
# TAB 8: DATEN MANAGER (MIT HISTORIE 2022-2025 & ACTUALS)
# ------------------------------------------------------------------
elif selected == "Daten-Manager":
    st.title("💾 Daten & Ist-Werte Management")
    t1, t2, t3, t4 = st.tabs(["🎲 Basis-Daten (2022-2025)", "📅 Ist-Werte Generieren", "📂 CSV Import", "⚠️ Reset"])
    
    # GENERATOR BASIS (2022 - 2025)
    with t1:
        st.markdown("Erstellt Historie von **2022 bis 2025**.")
        if st.button("🚀 Historie generieren"):
            delete_all_projects(); delete_all_stats(); delete_all_actuals()
            
            # Jahre 2022, 2023, 2024, 2025
            years = [2022, 2023, 2024, 2025]
            stats = [{"year": y, "fte_count": int(500*1.05**i), "revenue": 80000000*1.07**i, "scenario": "Actual"} for i, y in enumerate(years)]
            insert_bulk_stats(stats)
            
            projs = []
            for s in stats:
                # Fixe Kosten
                projs.append({"project_name": "M365 Lizenzen", "category": "Digitaler Arbeitsplatz", "budget_type": "OPEX", "year": s['year'], "cost_planned": s['fte_count']*1200, "scenario": "Actual"})
                projs.append({"project_name": "SAP Wartung", "category": "ERP", "budget_type": "OPEX", "year": s['year'], "cost_planned": 200000, "scenario": "Actual"})
                
                # Variable Projekte pro Jahr
                for i in range(5):
                    projs.append({"project_name": f"Projekt {i}", "category": "Cloud Plattform", "budget_type": "OPEX", "year": s['year'], "cost_planned": random.randint(20000, 300000), "scenario": "Actual"})
                    if random.random() > 0.5:
                        projs.append({"project_name": f"Invest {i}", "category": "Infrastruktur", "budget_type": "CAPEX", "year": s['year'], "cost_planned": random.randint(50000, 500000), "scenario": "Actual"})
            
            insert_bulk_projects(projs)
            st.success("Historie 2022-2025 erstellt!"); time.sleep(1); st.rerun()

    # GENERATOR ACTUALS
    with t2:
        st.subheader("Monatliche Ist-Buchungen für 2026")
        col_m, col_b = st.columns(2)
        with col_m: gen_month = st.selectbox("Monat", range(1,13))
        with col_b:
            if st.button("💸 Ist-Kosten buchen"):
                # Relevante Projekte 2026 suchen
                rel_projs = df_proj[(df_proj['year'] == 2026) & ((df_proj['scenario'] == 'Budget 2026 (Fixed)') | (df_proj['status'] == 'Planned'))]
                if rel_projs.empty: st.error("Kein Budget 2026 gefunden.")
                else:
                    acts = []
                    for _, row in rel_projs.iterrows():
                        monthly = row['cost_planned'] / 12
                        acts.append({"project_id": row['id'], "year": 2026, "month": gen_month, "cost_actual": monthly * random.uniform(0.8, 1.2)})
                    insert_bulk_actuals(acts)
                    st.success(f"Gebucht für Monat {gen_month}!"); time.sleep(1); st.rerun()

    with t3:
        st.markdown("CSV Import (Ist-Werte)"); up = st.file_uploader("CSV", type=['csv'])
        if up and st.button("Import"):
            insert_bulk_actuals(pd.read_csv(up).to_dict('records')); st.success("Importiert!"); st.rerun()

    with t4:
        if st.button("🗑️ KOMPLETT LÖSCHEN"): delete_all_projects(); delete_all_stats(); delete_all_actuals(); st.rerun()
