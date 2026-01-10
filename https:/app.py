import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import random
import time

# Imports aus database.py
from database import insert_bulk_projects, get_projects, insert_bulk_stats, get_stats, delete_all_projects, delete_all_stats

st.set_page_config(page_title="CIO Cockpit 9.0 - Integrated Planning", layout="wide", page_icon="🏢")

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
    df_proj = pd.DataFrame(raw_projects) if raw_projects else pd.DataFrame()
    df_stats = pd.DataFrame(raw_stats) if raw_stats else pd.DataFrame()
    
    if not df_proj.empty: df_proj.columns = df_proj.columns.str.lower()
    if not df_stats.empty: df_stats.columns = df_stats.columns.str.lower()
    
except Exception as e:
    st.error(f"Datenbank Fehler: {e}")
    df_proj, df_stats = pd.DataFrame(), pd.DataFrame()

# ------------------------------------------------------------------
# TAB 1: MANAGEMENT DASHBOARD (IST + PLAN)
# ------------------------------------------------------------------
if selected == "Management Dashboard":
    st.title("🏛️ Management Übersicht")
    
    if df_proj.empty:
        st.warning("Keine Daten. Bitte zum 'Daten-Manager'!")
    else:
        # LOGIK: Wir zeigen Actuals (2023-2025) UND den Plan für 2026 (Fixed OPEX + Planned Projects)
        
        # 1. Datenbasis Actuals
        df_actual = df_proj[df_proj['scenario'] == 'Actual'].copy()
        df_actual['Type'] = 'Ist (Actual)'
        
        # 2. Datenbasis Plan 2026 (Zusammengesetzt aus Basis + Projekten)
        # Wir suchen nach "Budget 2026 (Fixed)" ODER manuell geplanten Projekten ("Planned")
        # Wir definieren alles als "Plan 2026", was im Jahr 2026 liegt und nicht 'Actual' ist
        # (Um Dopplungen zu vermeiden, filtern wir auf bestimmte Szenarien oder Status)
        
        # Annahme: Plan 2026 besteht aus:
        # a) Szenario "Budget 2026 (Fixed)" -> Das ist der OPEX Sockel
        # b) Status "Planned" -> Das sind die manuell hinzugefügten Projekte
        
        df_plan = df_proj[
            (df_proj['year'] == 2026) & 
            ( (df_proj['scenario'] == 'Budget 2026 (Fixed)') | (df_proj['status'] == 'Planned') )
        ].copy()
        df_plan['Type'] = 'Plan 2026'
        
        # Kombinieren für Charts
        df_dashboard = pd.concat([df_actual, df_plan])
        
        # KPIs für das aktuellste abgeschlossene Jahr (meist 2025) vs Plan 2026
        last_actual_year = df_actual['year'].max() if not df_actual.empty else 2025
        
        budget_last_actual = df_actual[df_actual['year'] == last_actual_year]['cost_planned'].sum()
        budget_plan_2026 = df_plan['cost_planned'].sum()
        
        # KPIs Anzeigen
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_func(f"Budget Ist ({last_actual_year})", fmt_de(budget_last_actual/1000000, 2, 'M€'), "Abgeschlossen", delta_color)
        with c2: kpi_func("Budget Plan (2026)", fmt_de(budget_plan_2026/1000000, 2, 'M€'), 
                          f"{fmt_de((budget_plan_2026-budget_last_actual)/budget_last_actual*100, 1, '%')} vs Vj.", 
                          "orange" if budget_plan_2026 > budget_last_actual else "green")
        
        # OPEX vs CAPEX im Plan 2026
        opex_plan = df_plan[df_plan['budget_type'] == 'OPEX']['cost_planned'].sum()
        capex_plan = df_plan[df_plan['budget_type'] == 'CAPEX']['cost_planned'].sum()
        
        with c3: kpi_func("Plan 2026: Betrieb", fmt_de(opex_plan/1000000, 2, 'M€'), "OPEX Basis", "#0984e3")
        with c4: kpi_func("Plan 2026: Projekte", fmt_de(capex_plan/1000000, 2, 'M€'), "Neue Investitionen", "#00b894")
        
        st.markdown("---")
        
        col_chart1, col_chart2 = st.columns([2, 1])
        with col_chart1:
            st.subheader("Budget-Entwicklung: Ist vs. Plan")
            # Wir gruppieren nach Jahr und Typ
            df_trend = df_dashboard.groupby(['year', 'Type'])['cost_planned'].sum().reset_index()
            
            fig = px.bar(df_trend, x='year', y='cost_planned', color='Type', text_auto='.2s', 
                         title="Gesamtbudget Verlauf",
                         color_discrete_map={'Ist (Actual)': '#636e72', 'Plan 2026': '#6c5ce7'})
            fig.update_layout(yaxis_title="Budget (€)", separators=",.", template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
        with col_chart2:
            st.subheader("Plan 2026 Struktur")
            if budget_plan_2026 > 0:
                fig_pie = px.pie(df_plan, values='cost_planned', names='budget_type', 
                                 color='budget_type', hole=0.6,
                                 color_discrete_map={'CAPEX':'#00b894', 'OPEX':'#0984e3'})
                fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0), separators=",.", template=plotly_template, paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Noch kein Budget für 2026 definiert.")

# ------------------------------------------------------------------
# TAB 2: BASIS-BUDGET 2026 (OPEX)
# ------------------------------------------------------------------
elif selected == "1. Basis-Budget (OPEX)":
    st.title("🧱 Schritt 1: Betriebskosten-Basis 2026")
    
    if df_proj.empty:
        st.error("Bitte erst Daten generieren.")
    else:
        fixed_scen = "Budget 2026 (Fixed)"
        df_fixed = df_proj[df_proj['scenario'] == fixed_scen]
        
        if not df_fixed.empty:
            st.success(f"✅ OPEX-Basis für 2026 ist fixiert.")
            st.metric("Fixierter Sockelbetrag", fmt_de(df_fixed['cost_planned'].sum(), 2, '€'))
            
            if st.button("🔓 Basis löschen & neu planen"):
                # Workaround Löschen
                st.warning("Bitte im Daten-Manager Reset durchführen (da wir keine Delete-by-Name Funktion haben).")
                
            with st.expander("Details ansehen"):
                st.dataframe(df_fixed, use_container_width=True)
        else:
            st.markdown("Definiere hier, wie viel der reine **Betrieb (Run the Business)** in 2026 kosten wird, basierend auf den Vorjahren.")
            
            # Historische OPEX Daten (2023-2025)
            df_hist_opex = df_proj[
                (df_proj['scenario'] == 'Actual') & 
                (df_proj['budget_type'] == 'OPEX') &
                (df_proj['year'].isin([2023, 2024, 2025]))
            ].copy()
            
            if df_hist_opex.empty:
                st.warning("Keine historischen OPEX Daten gefunden.")
            else:
                # Chart zur Entscheidungshilfe
                fig_hist = px.bar(df_hist_opex.groupby('year')['cost_planned'].sum().reset_index(), 
                                  x='year', y='cost_planned', title="OPEX Entwicklung (Ist)", text_auto='.2s')
                fig_hist.update_traces(marker_color='#0984e3')
                fig_hist.update_layout(height=250, separators=",.", template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_hist, use_container_width=True)
                
                # Optionen berechnen
                avg_val = df_hist_opex.groupby('year')['cost_planned'].sum().mean()
                last_val = df_hist_opex[df_hist_opex['year'] == 2025]['cost_planned'].sum()
                
                c1, c2, c3 = st.columns(3)
                
                # Option A: Durchschnitt
                with c1:
                    st.markdown(f'<div class="css-card" style="text-align:center"><h4>Durchschnitt</h4><h2>{fmt_de(avg_val, 0)}</h2><p>Ø 2023-2025</p></div>', unsafe_allow_html=True)
                    if st.button("Übernehmen (Ø)"):
                        factor = avg_val / last_val if last_val > 0 else 1
                        df_new = df_hist_opex[df_hist_opex['year'] == 2025].copy()
                        df_new['cost_planned'] *= factor
                        df_new['year'] = 2026; df_new['scenario'] = fixed_scen; df_new['status'] = 'Planned Base'
                        if 'id' in df_new.columns: del df_new['id']
                        if 'created_at' in df_new.columns: del df_new['created_at']
                        insert_bulk_projects(df_new.to_dict('records'))
                        st.rerun()
                        
                # Option B: Vorjahr (Flat)
                with c2:
                    st.markdown(f'<div class="css-card" style="text-align:center"><h4>Flat Budget</h4><h2>{fmt_de(last_val, 0)}</h2><p>Wie 2025</p></div>', unsafe_allow_html=True)
                    if st.button("Übernehmen (Flat)"):
                        df_new = df_hist_opex[df_hist_opex['year'] == 2025].copy()
                        df_new['year'] = 2026; df_new['scenario'] = fixed_scen; df_new['status'] = 'Planned Base'
                        if 'id' in df_new.columns: del df_new['id']
                        if 'created_at' in df_new.columns: del df_new['created_at']
                        insert_bulk_projects(df_new.to_dict('records'))
                        st.rerun()

                # Option C: Inflation (+4%)
                with c3:
                    infl_val = last_val * 1.04
                    st.markdown(f'<div class="css-card" style="text-align:center"><h4>Inflation (+4%)</h4><h2>{fmt_de(infl_val, 0)}</h2><p>Teuerungsausgleich</p></div>', unsafe_allow_html=True)
                    if st.button("Übernehmen (+4%)"):
                        df_new = df_hist_opex[df_hist_opex['year'] == 2025].copy()
                        df_new['cost_planned'] *= 1.04
                        df_new['year'] = 2026; df_new['scenario'] = fixed_scen; df_new['status'] = 'Planned Base'
                        if 'id' in df_new.columns: del df_new['id']
                        if 'created_at' in df_new.columns: del df_new['created_at']
                        insert_bulk_projects(df_new.to_dict('records'))
                        st.rerun()

# ------------------------------------------------------------------
# TAB 3: MANUELLE PROJEKT PLANUNG
# ------------------------------------------------------------------
elif selected == "2. Projekt-Planung":
    st.title("🚀 Schritt 2: Neue Projekte 2026")
    st.info("Füge hier Investitionen (CAPEX) oder neue OPEX-Themen hinzu, die **zusätzlich** zur Basis kommen.")
    
    # Check ob Basis existiert
    if df_proj[df_proj['scenario'] == 'Budget 2026 (Fixed)'].empty:
        st.warning("⚠️ Achtung: Du hast noch kein Basis-Budget (Schritt 1) festgelegt.")
    
    step = st.session_state.wizard_step
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.markdown(f"**1. Stammdaten** {'✅' if step > 1 else '🔵'}")
    col_s2.markdown(f"**2. Finanzen** {'✅' if step > 2 else '🔵'}")
    col_s3.markdown(f"**3. Strategie** {'✅' if step > 3 else '🔵'}")
    st.progress(step / 3)
    st.divider()

    if step == 1:
        st.subheader("1. Stammdaten")
        with st.form("wiz_step1"):
            w_name = st.text_input("Projektname", value=st.session_state.wiz_data.get('project_name', ''))
            w_cat = st.selectbox("Kategorie", ["Digitaler Arbeitsplatz", "Cloud Plattform", "Cyber Security", "ERP & Apps", "Data & KI", "Infrastruktur"])
            w_year = st.number_input("Budgetjahr", value=2026, step=1, disabled=True) # Fest auf 2026
            if st.form_submit_button("Weiter ➡️"):
                if w_name:
                    st.session_state.wiz_data.update({'project_name': w_name, 'category': w_cat, 'year': 2026})
                    st.session_state.wizard_step = 2
                    st.rerun()
                else: st.error("Name fehlt.")

    elif step == 2:
        st.subheader("2. Finanzen")
        with st.form("wiz_step2"):
            c1, c2 = st.columns(2)
            with c1: w_btype = st.radio("Typ", ["CAPEX (Invest)", "OPEX (Laufend)"])
            with c2: w_otype = st.selectbox("OPEX Art", ["-", "Lizenzen (SaaS)", "Cloud Infra", "Beratung", "Wartung"])
            w_cost = st.number_input("Kosten 2026 (€)", min_value=0.0, step=1000.0, value=50000.0)
            
            c_b1, c_b2 = st.columns(2)
            if c_b1.form_submit_button("⬅️ Zurück"):
                st.session_state.wizard_step = 1
                st.rerun()
            if c_b2.form_submit_button("Weiter ➡️"):
                b_clean = "CAPEX" if "CAPEX" in w_btype else "OPEX"
                st.session_state.wiz_data.update({'budget_type': b_clean, 'opex_type': w_otype if b_clean=="OPEX" else "", 'cost_planned': w_cost, 'savings_planned': 0})
                st.session_state.wizard_step = 3
                st.rerun()

    elif step == 3:
        st.subheader("3. Strategie")
        with st.form("wiz_step3"):
            w_risk = st.slider("Risiko", 1, 5, 2)
            w_score = st.slider("Strategie-Wert", 1, 10, 5)
            # Hier kein Szenario-Input mehr nötig, da wir es fix als "Plan 2026" behandeln via Status
            
            c_b1, c_b2 = st.columns(2)
            if c_b1.form_submit_button("⬅️ Zurück"):
                st.session_state.wizard_step = 2
                st.rerun()
            if c_b2.form_submit_button("💾 Projekt speichern", type="primary"):
                final = st.session_state.wiz_data.copy()
                final.update({'risk_factor': w_risk, 'strategic_score': w_score, 'scenario': 'Planned Project', 'status': 'Planned'})
                try:
                    insert_bulk_projects([final])
                    st.success("Gespeichert! Erscheint jetzt im Dashboard.")
                    st.session_state.wiz_data = {}
                    st.session_state.wizard_step = 1
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"Fehler: {e}")

# ------------------------------------------------------------------
# TAB 4: SZENARIO SIMULATOR (GESAMT)
# ------------------------------------------------------------------
elif selected == "Szenario-Simulator":
    st.title("🔮 Szenario-Simulator 2026")
    
    if df_proj.empty:
        st.warning("Keine Datenbasis.")
    else:
        # Wir simulieren auf Basis des letzten Actual Jahres
        last_actual_year = df_proj[df_proj['scenario'] == 'Actual']['year'].max()
        df_base = df_proj[(df_proj['year'] == last_actual_year) & (df_proj['scenario'] == 'Actual')].copy()
        
        st.markdown(f"### Treiber einstellen (Basis: Ist {last_actual_year})")
        c1, c2, c3, c4 = st.columns(4)
        with c1: sim_inf = st.slider("Inflation", 0.0, 10.0, 3.0, format="%f%%") / 100
        with c2: sim_fte = st.slider("FTE Wachstum", -5.0, 20.0, 5.0, format="%f%%") / 100
        with c3: sim_lic = st.slider("Lizenzpreise", 0.0, 20.0, 10.0, format="%f%%") / 100
        with c4: sim_eff = st.slider("Effizienz", 0.0, 10.0, 2.0, format="%f%%") / 100

        df_sim = df_base.copy()
        df_sim['year'] = last_actual_year + 1
        
        def calc_sim(row):
            cost = row['cost_planned']
            opex = str(row.get('opex_type', ''))
            if "Lizenzen" in opex or "Licenses" in opex: return cost * (1 + sim_lic) * (1 + sim_fte)
            elif row['budget_type'] == 'OPEX': return cost * (1 + sim_inf)
            else: return cost * (1 + sim_inf)
        
        df_sim['cost_planned'] = df_sim.apply(calc_sim, axis=1)
        sim_sum = df_sim['cost_planned'].sum()
        base_sum = df_base['cost_planned'].sum()
        
        st.divider()
        st.metric("Budget Prognose", fmt_de(sim_sum, 0, "€"), delta=fmt_de(sim_sum-base_sum, 0, "€"), delta_color="inverse")
        
        with st.form("save_scenario"):
            s_name = st.text_input("Szenario Name", value="Auto-Sim 2026")
            if st.form_submit_button("Szenario speichern"):
                df_up = df_sim.copy()
                df_up['scenario'] = s_name
                if 'id' in df_up.columns: del df_up['id']
                if 'created_at' in df_up.columns: del df_up['created_at']
                insert_bulk_projects(df_up.to_dict('records'))
                st.success("Gespeichert!")

# ------------------------------------------------------------------
# TAB 5: SZENARIO VERGLEICH
# ------------------------------------------------------------------
elif selected == "Szenario-Vergleich":
    st.title("⚖️ Vergleich & Geldfluss")
    
    if df_proj.empty:
        st.warning("Keine Daten.")
    else:
        # Wir zeigen: Actuals 2023-2025 UND den Plan 2026
        # Dazu müssen wir den "Plan 2026" erst zusammenbauen (wie im Dashboard)
        
        df_actuals = df_proj[df_proj['scenario'] == 'Actual'].copy()
        df_actuals['Label'] = 'Ist (Actual)'
        
        # Plan 2026 bauen
        df_plan = df_proj[
            (df_proj['year'] == 2026) & 
            ( (df_proj['scenario'] == 'Budget 2026 (Fixed)') | (df_proj['status'] == 'Planned') )
        ].copy()
        
        if not df_plan.empty:
            df_plan['Label'] = 'Plan 2026 (Final)'
            # Zusammenfügen
            df_comp = pd.concat([df_actuals, df_plan])
        else:
            df_comp = df_actuals
        
        st.subheader("Entwicklung Ist vs. Plan")
        
        df_grp = df_comp.groupby(['year', 'Label'])['cost_planned'].sum().reset_index()
        fig_comp = px.bar(df_grp, x='year', y='cost_planned', color='Label', 
                          text_auto='.2s', title="Budget Verlauf",
                          color_discrete_map={"Ist (Actual)": "#636e72", "Plan 2026 (Final)": "#00b894"})
        fig_comp.update_layout(yaxis_title="Budget (€)", separators=",.", template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_comp, use_container_width=True)
        
        st.divider()
        
        # SANKEY für Plan 2026
        st.subheader("Geldfluss Plan 2026")
        if not df_plan.empty:
            top_p = df_plan.sort_values('cost_planned', ascending=False).head(15)
            
            labels = list(top_p['budget_type'].unique()) + list(top_p['category'].unique()) + list(top_p['project_name'].unique())
            def g_idx(n): return labels.index(n)
            
            src, tgt, val = [], [], []
            
            # Link 1
            g1 = top_p.groupby(['budget_type', 'category'])['cost_planned'].sum().reset_index()
            for _, r in g1.iterrows():
                try: src.append(g_idx(r['budget_type'])); tgt.append(g_idx(r['category'])); val.append(r['cost_planned'])
                except: pass
            
            # Link 2
            for _, r in top_p.iterrows():
                try: src.append(g_idx(r['category'])); tgt.append(g_idx(r['project_name'])); val.append(r['cost_planned'])
                except: pass
            
            if labels:
                cols = ["#6c5ce7"]*len(top_p['budget_type'].unique()) + ["#00b894"]*len(top_p['category'].unique()) + ["#a29bfe"]*len(top_p['project_name'].unique())
                
                

                fig_san = go.Figure(data=[go.Sankey(
                    node = dict(pad = 20, thickness = 30, line = dict(color = "black", width = 0.5), label = labels, color = cols, align="left"),
                    link = dict(source = src, target = tgt, value = val, color = "rgba(100, 100, 100, 0.3)"),
                    textfont=dict(size=15, color=text_color, family="Arial Black")
                )])
                fig_san.update_layout(height=600, title_text="Flow: Plan 2026", template=plotly_template, font=dict(size=14), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_san, use_container_width=True)
        else:
            st.info("Noch kein Plan für 2026 vorhanden.")

# ------------------------------------------------------------------
# TAB 6: KOSTEN & OPEX ANALYSE
# ------------------------------------------------------------------
elif selected == "Kosten & OPEX Analyse":
    st.title("💸 Kostenstruktur Detail-Analyse")
    if df_proj.empty: st.warning("Keine Daten.")
    else:
        yf = st.selectbox("Jahr", sorted(df_proj['year'].unique(), reverse=True))
        # Hier zeigen wir ALLES für das Jahr (Actuals oder Plan)
        # Wir filtern nicht hart auf 'Actual', sondern nehmen alles für das Jahr, um auch 2026 Plan zu sehen
        df_y = df_proj[df_proj['year'] == yf].copy()
        
        # Wenn 2026, filtern wir Müll-Simulationen raus und nehmen nur Fixed + Planned
        if yf == 2026:
            df_y = df_y[df_y['scenario'].isin(['Budget 2026 (Fixed)', 'Planned Project']) | (df_y['status'] == 'Planned')]
        elif yf < 2026:
            df_y = df_y[df_y['scenario'] == 'Actual']
            
        df_y['opex_type'] = df_y['opex_type'].fillna("Invest")
        
        fig_s = px.sunburst(df_y, path=['budget_type', 'category', 'opex_type', 'project_name'], values='cost_planned',
                              color='category', color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_s.update_layout(height=700, separators=",.", template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_s, use_container_width=True)
        
        top = df_y.sort_values('cost_planned', ascending=False)[['project_name', 'category', 'cost_planned']].head(10)
        top['cost_planned'] = top['cost_planned'].apply(lambda x: fmt_de(x, 2, '€'))
        st.dataframe(top, use_container_width=True)

# ------------------------------------------------------------------
# TAB 7: PORTFOLIO & RISIKO
# ------------------------------------------------------------------
elif selected == "Portfolio & Risiko":
    st.title("🎯 Strategisches Portfolio")
    if df_proj.empty: st.warning("Keine Daten.")
    else:
        cy = df_proj['year'].max() # Wir nehmen das letzte Jahr (auch Plan)
        df_c = df_proj[df_proj['year'] == cy]
        
        c1, c2 = st.columns([3, 1])
        with c1:
            fig_b = px.scatter(df_c, x="strategic_score", y="risk_factor", size="cost_planned", color="category",
                                 hover_name="project_name", size_max=60, title=f"Portfolio {cy}")
            fig_b.add_hrect(y0=2.5, y1=5, line_width=0, fillcolor="red", opacity=0.1)
            fig_b.add_vrect(x0=5, x1=10, line_width=0, fillcolor="green", opacity=0.1)
            fig_b.update_layout(template=plotly_template, separators=",.", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_b, use_container_width=True)
        with c2:
            st.markdown("### Top Wetten")
            ts = df_c[df_c['strategic_score'] >= 8].sort_values('strategic_score', ascending=False).head(5)
            for _, r in ts.iterrows():
                st.info(f"**{r['project_name']}**\nInvest: {fmt_de(r['cost_planned']/1000, 0, 'k€')}")

# ------------------------------------------------------------------
# TAB 8: DATEN MANAGER
# ------------------------------------------------------------------
elif selected == "Daten-Manager":
    st.title("💾 Daten Management")
    t1, t2, t3 = st.tabs(["🎲 Generator", "📂 Import", "⚠️ Reset"])
    
    with t1:
        if st.button("🚀 Testdaten erzeugen"):
            delete_all_projects(); delete_all_stats()
            stats = [{"year": y, "fte_count": int(500*1.05**i), "revenue": 80000000*1.07**i, "scenario": "Actual"} for i, y in enumerate([2023, 2024, 2025])]
            insert_bulk_stats(stats)
            projs = []
            for s in stats:
                projs.append({"project_name": "M365 Lizenzen", "category": "Digitaler Arbeitsplatz", "opex_type": "Lizenzen", "budget_type": "OPEX", "year": s['year'], "cost_planned": s['fte_count']*1200, "savings_planned": 0, "risk_factor": 1, "strategic_score": 10, "status": "Live", "scenario": "Actual"})
                for i in range(8):
                    projs.append({"project_name": f"Projekt {i}", "category": "Cloud Plattform", "budget_type": "OPEX", "year": s['year'], "cost_planned": random.randint(20000, 500000), "savings_planned": 0, "risk_factor": 3, "strategic_score": 5, "status": "Live", "scenario": "Actual"})
                # Ein paar CAPEX Projekte für die Historie
                for i in range(3):
                    projs.append({"project_name": f"Invest {i}", "category": "Infrastruktur", "budget_type": "CAPEX", "year": s['year'], "cost_planned": random.randint(50000, 200000), "savings_planned": 10000, "risk_factor": 2, "strategic_score": 7, "status": "Live", "scenario": "Actual"})
            insert_bulk_projects(projs)
            st.success("Erledigt!"); time.sleep(1); st.rerun()

    with t2:
        st.markdown("CSV Import"); up = st.file_uploader("CSV", type=['csv'])
        if up and st.button("Import"):
            insert_bulk_projects(pd.read_csv(up).to_dict('records'))
            st.success("Importiert!"); time.sleep(1); st.rerun()

    with t3:
        if st.button("🗑️ Löschen"): delete_all_projects(); delete_all_stats(); st.rerun()
