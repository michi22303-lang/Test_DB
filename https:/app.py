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

st.set_page_config(page_title="CIO Cockpit Ultimate - The Real Deal", layout="wide", page_icon="🏢")

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
            "2. Projekt-Planung",
            "Szenario-Simulator", 
            "Szenario-Vergleich", 
            "Kosten & OPEX Analyse", 
            "Portfolio & Risiko", 
            "Daten-Manager"
        ],
        icons=["speedometer2", "bank", "pencil-square", "calculator", "diagram-3", "pie-chart", "bullseye", "database-gear"],
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

# --- DATEN LADEN (ROBUST) ---
try:
    raw_projects = get_projects()
    raw_stats = get_stats()
    raw_actuals = get_actuals()
    
    df_proj = pd.DataFrame(raw_projects) if raw_projects else pd.DataFrame()
    df_stats = pd.DataFrame(raw_stats) if raw_stats else pd.DataFrame()
    df_act = pd.DataFrame(raw_actuals) if raw_actuals else pd.DataFrame()
    
    if not df_proj.empty: 
        df_proj.columns = df_proj.columns.str.lower()
        df_proj['cost_planned'] = pd.to_numeric(df_proj['cost_planned'], errors='coerce').fillna(0)
    if not df_stats.empty: df_stats.columns = df_stats.columns.str.lower()
    if not df_act.empty: 
        df_act.columns = df_act.columns.str.lower()
        df_act['cost_actual'] = pd.to_numeric(df_act['cost_actual'], errors='coerce').fillna(0)
    
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
        with c1: kpi_func("Gesamt-Budget 2026", fmt_de(plan_total/1000000, 2, 'M€'), "Basis + Projekte", delta_color)
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
                # Merge um den Kategorienamen zu bekommen (Actuals haben nur project_id)
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
            st.subheader("Budget Status")
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
# TAB 2: BASIS-BUDGET 2026 (OPEX WIZARD)
# ------------------------------------------------------------------
elif selected == "1. Basis-Budget (OPEX)":
    st.title("🧱 Schritt 1: Betriebskosten-Basis 2026")
    
    fixed_scen = "Budget 2026 (Fixed)"
    df_fixed = df_proj[df_proj['scenario'] == fixed_scen]
    
    if not df_fixed.empty:
        st.success(f"✅ OPEX-Basis für 2026 ist fixiert.")
        st.metric("Fixierter Sockelbetrag", fmt_de(df_fixed['cost_planned'].sum(), 2, '€'))
        with st.expander("Details"): st.dataframe(df_fixed[['category', 'project_name', 'cost_planned']])
    else:
        st.markdown("Definiere den Sockelbetrag (Run the Business) für 2026.")
        # Historie 2023-2025
        df_hist_opex = df_proj[(df_proj['scenario']=='Actual') & (df_proj['budget_type']=='OPEX') & (df_proj['year'].isin([2023,2024,2025]))].copy()
        
        if df_hist_opex.empty: st.warning("Keine Historie (2023-2025) gefunden. Bitte Daten-Manager nutzen.")
        else:
            last_val = df_hist_opex[df_hist_opex['year'] == 2025]['cost_planned'].sum()
            avg_val = df_hist_opex.groupby('year')['cost_planned'].sum().mean()
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="css-card"><h4>Durchschnitt</h4><h2>{fmt_de(avg_val,0)}</h2><p>Ø 2023-2025</p></div>', unsafe_allow_html=True)
                if st.button("Übernehmen (Ø)"):
                    factor = avg_val / last_val if last_val > 0 else 1
                    df_new = df_hist_opex[df_hist_opex['year'] == 2025].copy()
                    df_new['cost_planned'] *= factor
                    df_new['year'] = 2026; df_new['scenario'] = fixed_scen; df_new['status'] = 'Planned Base'
                    if 'id' in df_new.columns: del df_new['id']
                    if 'created_at' in df_new.columns: del df_new['created_at']
                    insert_bulk_projects(df_new.to_dict('records')); st.rerun()

            with c2:
                st.markdown(f'<div class="css-card"><h4>Flat (Wie 2025)</h4><h2>{fmt_de(last_val,0)}</h2><p>Status Quo</p></div>', unsafe_allow_html=True)
                if st.button("Übernehmen (Flat)"):
                    df_new = df_hist_opex[df_hist_opex['year'] == 2025].copy()
                    df_new['year'] = 2026; df_new['scenario'] = fixed_scen; df_new['status'] = 'Planned Base'
                    if 'id' in df_new.columns: del df_new['id']
                    if 'created_at' in df_new.columns: del df_new['created_at']
                    insert_bulk_projects(df_new.to_dict('records')); st.rerun()
            with c3:
                infl = last_val * 1.04
                st.markdown(f'<div class="css-card"><h4>Inflation (+4%)</h4><h2>{fmt_de(infl,0)}</h2><p>Teuerung</p></div>', unsafe_allow_html=True)
                if st.button("Übernehmen (+4%)"):
                    df_new = df_hist_opex[df_hist_opex['year'] == 2025].copy()
                    df_new['cost_planned'] *= 1.04
                    df_new['year'] = 2026; df_new['scenario'] = fixed_scen; df_new['status'] = 'Planned Base'
                    if 'id' in df_new.columns: del df_new['id']
                    if 'created_at' in df_new.columns: del df_new['created_at']
                    insert_bulk_projects(df_new.to_dict('records')); st.rerun()

# ------------------------------------------------------------------
# TAB 3: PROJEKT PLANUNG (DER GROSSE WIZARD)
# ------------------------------------------------------------------
elif selected == "2. Projekt-Planung":
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
                final.update({'risk_factor': w_risk, 'strategic_score': w_score, 'scenario': 'Budget 2026 (Project)', 'status': 'Planned'})
                try:
                    insert_bulk_projects([final])
                    st.success(f"Projekt '{final['project_name']}' gespeichert!")
                    st.session_state.wiz_data = {}; st.session_state.wizard_step = 1; time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Fehler: {e}")

# ------------------------------------------------------------------
# TAB 4: SZENARIO SIMULATOR (Global)
# ------------------------------------------------------------------
elif selected == "Szenario-Simulator":
    st.title("🔮 Szenario-Simulator (Global 2026)")
    if df_proj.empty: st.warning("Keine Daten.")
    else:
        # Basis: Letztes Actual Jahr
        last_act = df_proj[df_proj['scenario']=='Actual']['year'].max()
        df_base = df_proj[(df_proj['year']==last_act) & (df_proj['scenario']=='Actual')].copy()
        
        st.write(f"Basis: {last_act}")
        c1, c2 = st.columns(2)
        sim_inf = c1.slider("Inflation", 0.0, 10.0, 3.0)/100
        sim_growth = c2.slider("Wachstum", 0.0, 20.0, 5.0)/100
        
        df_sim = df_base.copy(); df_sim['year'] = 2026
        df_sim['cost_planned'] *= (1 + sim_inf + sim_growth)
        
        st.metric("Simuliertes Budget", fmt_de(df_sim['cost_planned'].sum()))
        
        if st.button("Szenario speichern"):
            df_sim['scenario'] = f"Sim {int(sim_inf*100)}%Inf"
            if 'id' in df_sim: del df_sim['id']
            if 'created_at' in df_sim: del df_sim['created_at']
            insert_bulk_projects(df_sim.to_dict('records'))
            st.success("Gespeichert!")

# ------------------------------------------------------------------
# TAB 5: SZENARIO VERGLEICH & SANKEY
# ------------------------------------------------------------------
elif selected == "Szenario-Vergleich":
    st.title("⚖️ Szenario-Vergleich & Flow")
    
    if df_proj.empty: st.warning("Keine Daten.")
    else:
        # 1. VERGLEICH
        st.subheader("Vergleich")
        all_scens = [s for s in df_proj['scenario'].unique() if s != "Actual"]
        sel_scens = st.multiselect("Szenarien wählen:", all_scens, default=all_scens[:2] if all_scens else [])
        
        # Actuals zum Vergleich
        fin_sel = ["Actual"] + sel_scens
        df_comp = df_proj[df_proj['scenario'].isin(fin_sel)].copy()
        
        # User wollte keine alten Jahre in der Grafik -> Filter auf 2026 für Simulationen, aber wir brauchen Actuals für Kontext?
        # Wir zeigen Budgetsumme pro Szenario (für 2026 bei Sims, Max Year bei Actuals)
        
        df_grp = df_comp.groupby(['scenario', 'year'])['cost_planned'].sum().reset_index()
        fig = px.bar(df_grp, x='scenario', y='cost_planned', color='scenario', title="Gesamtbudget Vergleich", text_auto='.2s')
        fig.update_layout(template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # 2. SANKEY
        st.subheader("Geldfluss (Sankey)")
        s_flow = st.selectbox("Szenario für Flow:", fin_sel)
        df_flow = df_proj[df_proj['scenario'] == s_flow]
        
        if not df_flow.empty:
            top = df_flow.sort_values('cost_planned', ascending=False).head(15)
            labels = list(top['budget_type'].unique()) + list(top['category'].unique()) + list(top['project_name'].unique())
            def g_i(n): return labels.index(n)
            
            src, tgt, val = [], [], []
            g1 = top.groupby(['budget_type', 'category'])['cost_planned'].sum().reset_index()
            for _, r in g1.iterrows(): src.append(g_i(r['budget_type'])); tgt.append(g_i(r['category'])); val.append(r['cost_planned'])
            for _, r in top.iterrows(): src.append(g_i(r['category'])); tgt.append(g_i(r['project_name'])); val.append(r['cost_planned'])
            
            cols = ["#6c5ce7"]*len(top['budget_type'].unique()) + ["#00b894"]*len(top['category'].unique()) + ["#a29bfe"]*len(top['project_name'].unique())
            
            fig_san = go.Figure(data=[go.Sankey(
                node = dict(pad = 20, thickness = 30, line = dict(color = "black", width = 0.5), label = labels, color = cols),
                link = dict(source = src, target = tgt, value = val, color = "rgba(100, 100, 100, 0.3)"),
                textfont=dict(size=14, color=text_color)
            )])
            fig_san.update_layout(height=600, template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_san, use_container_width=True)

# ------------------------------------------------------------------
# TAB 6 & 7: ANALYSE & PORTFOLIO
# ------------------------------------------------------------------
elif selected == "Kosten & OPEX Analyse":
    st.title("💸 Analyse")
    if not df_proj.empty:
        y = st.selectbox("Jahr", sorted(df_proj['year'].unique(), reverse=True))
        df_y = df_proj[df_proj['year']==y].copy()
        fig = px.sunburst(df_y, path=['budget_type', 'category', 'project_name'], values='cost_planned')
        fig.update_layout(height=700, template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

elif selected == "Portfolio & Risiko":
    st.title("🎯 Portfolio")
    if not df_proj.empty:
        # Nur Planned Projects zeigen oder Actuals?
        df_p = df_proj[df_proj['year'] == 2026]
        if not df_p.empty:
            fig = px.scatter(df_p, x='strategic_score', y='risk_factor', size='cost_planned', color='category', hover_name='project_name', size_max=50, title="Portfolio 2026")
            fig.update_layout(template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------
# TAB 8: DATEN MANAGER
# ------------------------------------------------------------------
elif selected == "Daten-Manager":
    st.title("💾 Daten Management")
    t1, t2, t3, t4 = st.tabs(["🎲 Historie (2022-2025)", "📅 Ist-Werte (2026)", "📂 CSV Import", "⚠️ Reset"])
    
    with t1:
        st.markdown("**Erzeugt Historie 2022-2025**")
        if st.button("🚀 Historie generieren"):
            delete_all_projects(); delete_all_stats(); delete_all_actuals()
            years = [2022, 2023, 2024, 2025]
            projs = []
            for y in years:
                # OPEX Basis
                projs.append({"project_name": "M365 Lizenzen", "category": "Digitaler Arbeitsplatz", "budget_type": "OPEX", "year": y, "cost_planned": 500000 * (1.05**(y-2022)), "scenario": "Actual", "status": "Live"})
                projs.append({"project_name": "SAP Wartung", "category": "ERP", "budget_type": "OPEX", "year": y, "cost_planned": 200000, "scenario": "Actual", "status": "Live"})
                # Random Projekte
                for i in range(4):
                    projs.append({"project_name": f"Projekt {y}-{i}", "category": "Cloud", "budget_type": "OPEX", "year": y, "cost_planned": random.randint(50000, 250000), "scenario": "Actual"})
            insert_bulk_projects(projs)
            st.success("Historie 2022-2025 erstellt!"); time.sleep(1); st.rerun()

    with t2:
        st.subheader("Ist-Buchungen für 2026 simulieren")
        m = st.selectbox("Monat", range(1, 13))
        if st.button("💸 Ist-Kosten buchen"):
            # Hole Plan-Projekte 2026
            plan_26 = df_proj[(df_proj['year'] == 2026) & (df_proj['scenario'].isin(['Budget 2026 (Fixed)', 'Planned Project', 'Budget 2026 (Project)']))]
            
            if plan_26.empty:
                st.error("Kein Budget 2026 gefunden (Weder Basis noch Projekte).")
            else:
                acts = []
                for _, row in plan_26.iterrows():
                    val = (row['cost_planned'] / 12) * random.uniform(0.8, 1.2)
                    acts.append({"project_id": row['id'], "year": 2026, "month": m, "cost_actual": val})
                insert_bulk_actuals(acts)
                st.success(f"Ist-Kosten für Monat {m} gebucht!"); time.sleep(1); st.rerun()
                
    with t3:
        st.write("CSV Import für Actuals möglich.")
        
    with t4:
        if st.button("🗑️ ALLES LÖSCHEN"):
            delete_all_projects(); delete_all_stats(); delete_all_actuals(); st.rerun()
