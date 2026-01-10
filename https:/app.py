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

st.set_page_config(page_title="CIO Cockpit 8.0 - OPEX Edition", layout="wide", page_icon="🏢")

# --- HELPER: DEUTSCHE ZAHLENFORMATIERUNG ---
def fmt_de(value, decimals=0, suffix="€"):
    if value is None: return ""
    try:
        s = f"{value:,.{decimals}f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{s} {suffix}".strip()
    except: return str(value)

# --- INITIALISIERUNG SESSION STATE ---
if 'wizard_step' not in st.session_state:
    st.session_state.wizard_step = 1
if 'wiz_data' not in st.session_state:
    st.session_state.wiz_data = {}

# --- SIDEBAR & THEME TOGGLE ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3094/3094851.png", width=50)
    st.markdown("### Digital Strategy Board")
    
    # DARK MODE TOGGLE
    dark_mode = st.toggle("🌙 Dark Mode", value=False)
    
    if dark_mode:
        plotly_template = "plotly_dark"
        main_bg = "#0e1117" # Tiefes Schwarz/Grau für Hintergrund
        card_bg = "#262730" 
        text_color = "#ffffff"
        delta_color = "#bdc3c7"
    else:
        plotly_template = "plotly_white"
        main_bg = "#ffffff"
        card_bg = "#f0f2f6" # Ein sehr helles Grau hebt sich besser ab als Weiß
        text_color = "#31333F"
        delta_color = "black"

    selected = option_menu(
        "Navigation",
        [
            "Management Dashboard", 
            "Basis-Budget 2026 (OPEX)", # <-- NEU & WICHTIG
            "Manuelle Projekt-Planung",
            "Szenario-Simulator (Gesamt)", 
            "Szenario-Vergleich", 
            "Kosten & OPEX Analyse", 
            "Portfolio & Risiko", 
            "Daten-Manager"
        ],
        icons=["speedometer2", "bank", "pencil-square", "calculator", "diagram-3", "pie-chart", "bullseye", "database-gear"],
        default_index=0,
    )

# --- CSS STYLING (DYNAMISCH MIT HINTERGRUND) ---
def local_css(bg_app, bg_card, txt_col, delta_col):
    st.markdown(f"""
    <style>
        /* App Hintergrund */
        .stApp {{
            background-color: {bg_app};
        }}
        
        .block-container {{padding-top: 1rem;}}
        
        /* Karten Design */
        div.css-card {{
            background-color: {bg_card};
            border: 1px solid rgba(128, 128, 128, 0.2);
            padding: 15px;
            border-radius: 10px;
            border-left: 5px solid #6c5ce7;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            color: {txt_col};
        }}
        div.card-title {{font-size: 13px; text-transform: uppercase; opacity: 0.8; margin-bottom: 5px; color: {txt_col};}}
        div.card-value {{font-size: 24px; font-weight: bold; color: {txt_col};}}
        div.card-delta {{font-size: 14px; margin-top: 5px; color: {delta_col};}}
        
        /* Text Farben global erzwingen falls nötig */
        h1, h2, h3, p, div, span {{
            color: {txt_col} !important;
        }}
        /* Ausnahme für Metriken Delta Farben von Streamlit */
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
# TAB 1: MANAGEMENT DASHBOARD
# ------------------------------------------------------------------
if selected == "Management Dashboard":
    st.title("🏛️ Management Übersicht")
    
    if df_proj.empty:
        st.warning("Keine Daten. Bitte zum 'Daten-Manager'!")
    else:
        # Hier zeigen wir NUR Actuals
        actual_years = sorted(df_proj[df_proj['scenario'] == 'Actual']['year'].unique())
        current_year = actual_years[-1] if actual_years else 2025
        
        df_curr = df_proj[(df_proj['year'] == current_year) & (df_proj['scenario'] == 'Actual')]
        df_prev = df_proj[(df_proj['year'] == current_year - 1) & (df_proj['scenario'] == 'Actual')]
        
        total_budget = df_curr['cost_planned'].sum()
        prev_budget = df_prev['cost_planned'].sum() if not df_prev.empty else total_budget
        
        opex_val = df_curr[df_curr['budget_type'] == 'OPEX']['cost_planned'].sum()
        capex_val = df_curr[df_curr['budget_type'] == 'CAPEX']['cost_planned'].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_func("IT-Budget (Ist)", f"{fmt_de(total_budget/1000000, 2, 'M€')}", f"Jahr {current_year}", delta_color)
        with c2: kpi_func("Betrieb (OPEX)", f"{fmt_de(opex_val/1000000, 2, 'M€')}", f"{opex_val/total_budget*100:.0f}% Anteil", "#0984e3")
        with c3: kpi_func("Projekte (CAPEX)", f"{fmt_de(capex_val/1000000, 2, 'M€')}", f"{capex_val/total_budget*100:.0f}% Anteil", "#00b894")
        with c4: kpi_func("Projekte Anzahl", f"{len(df_curr)}", "Laufend", delta_color)
        
        st.markdown("---")
        
        col_chart1, col_chart2 = st.columns([2, 1])
        with col_chart1:
            st.subheader("Budget-Verlauf (Nur Ist-Daten)")
            df_trend = df_proj[df_proj['scenario'] == 'Actual'].groupby('year')['cost_planned'].sum().reset_index()
            fig = px.bar(df_trend, x='year', y='cost_planned', text_auto='.2s', title="Entwicklung")
            fig.update_traces(marker_color='#6c5ce7')
            fig.update_layout(yaxis_title="Budget (€)", separators=",.", template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
        with col_chart2:
            st.subheader("Kostenarten Split")
            fig_pie = px.pie(df_curr, values='cost_planned', names='budget_type', 
                             color='budget_type', hole=0.6,
                             color_discrete_map={'CAPEX':'#00b894', 'OPEX':'#0984e3'})
            fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0), separators=",.", template=plotly_template, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)

# ------------------------------------------------------------------
# TAB 2: BASIS-BUDGET 2026 (OPEX) - DER NEUE WIZARD
# ------------------------------------------------------------------
elif selected == "Basis-Budget 2026 (OPEX)":
    st.title("🧱 Festlegung Basis-Budget 2026 (Nur Betrieb)")
    
    if df_proj.empty:
        st.error("Bitte erst Daten generieren.")
    else:
        # 1. PRÜFEN: GIBT ES SCHON EIN FESTGELEGTES BUDGET?
        fixed_scenario_name = "Budget 2026 (Fixed)"
        df_fixed = df_proj[df_proj['scenario'] == fixed_scenario_name]
        
        if not df_fixed.empty:
            # --- ZUSTAND: BEREITS FESTGELEGT ---
            st.success(f"✅ Das Basis-Budget für die Betriebskosten 2026 ist bereits festgelegt.")
            
            total_fixed = df_fixed['cost_planned'].sum()
            
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Fixiertes OPEX Budget 2026", fmt_de(total_fixed, 2, '€'))
            with c2:
                st.info("Um die Planung neu zu starten, musst du dieses Szenario löschen.")
                if st.button("🔓 Planung entsperren (Löschen)", type="primary"):
                    # Wir löschen alle Einträge dieses Szenarios
                    # Da wir keine direkte SQL delete-by-name Funktion haben, machen wir einen Workaround:
                    # Wir filtern die IDs und löschen einzeln oder wir brauchen eine delete_by_scenario Funktion in database.py
                    # Hier der einfache Weg über ID (etwas langsam bei vielen Daten, aber sicher)
                    ids_to_del = df_fixed['id'].tolist()
                    # Wir brauchen hier eine bessere Löschfunktion, aber für Demo:
                    # (In Realität würde man eine SQL Funktion delete_scenario(name) bauen)
                    st.warning("Funktion: Bitte Datenbank Reset nutzen oder Löschfunktion erweitern.")
                    # Für Demo-Zwecke: Wir tun so als ob, oder nutzen den Reset im Data Manager.
            
            st.subheader("Details des fixierten Budgets:")
            st.dataframe(df_fixed[['project_name', 'category', 'cost_planned']], use_container_width=True)

        else:
            # --- ZUSTAND: WIZARD AKTIV ---
            st.markdown("""
            Hier definieren wir den **Sockelbetrag für die Betriebskosten (OPEX)** für 2026. 
            Projektkosten (Investitionen) werden separat geplant.
            """)
            
            # Datenbasis holen (2023-2025, NUR OPEX)
            df_hist = df_proj[
                (df_proj['scenario'] == 'Actual') & 
                (df_proj['budget_type'] == 'OPEX') & 
                (df_proj['year'].isin([2023, 2024, 2025]))
            ].copy()
            
            if df_hist.empty:
                st.warning("Keine historischen OPEX-Daten (2023-2025) gefunden.")
            else:
                # Berechnungen für die 3 Optionen
                # 1. Durchschnitt
                avg_val = df_hist.groupby('year')['cost_planned'].sum().mean()
                
                # 2. Letztes Jahr (2025)
                last_year_val = df_hist[df_hist['year'] == 2025]['cost_planned'].sum()
                
                # 3. Trend (Linearer Anstieg basierend auf Wachstum 24->25)
                val_24 = df_hist[df_hist['year'] == 2024]['cost_planned'].sum()
                growth = (last_year_val / val_24) if val_24 > 0 else 1.0
                trend_val = last_year_val * growth
                
                st.subheader("Wähle deine Basis für 2026:")
                
                col_opt1, col_opt2, col_opt3 = st.columns(3)
                
                # Option 1: Durchschnitt
                with col_opt1:
                    st.markdown(f"""
                    <div class="css-card" style="text-align: center;">
                        <div class="card-title">Option A: Durchschnitt</div>
                        <div class="card-title">(Ø 2023-2025)</div>
                        <div class="card-value">{fmt_de(avg_val, 0)}</div>
                        <p style="font-size: 12px; margin-top: 10px;">Konservativer Ansatz. Glättet Spitzen.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("A wählen", key="btn_a", use_container_width=True):
                        # Wir müssen die Projekte von 2025 nehmen und deren Kosten anteilig anpassen, 
                        # damit die Summe stimmt.
                        factor = avg_val / last_year_val if last_year_val > 0 else 1
                        # Daten vorbereiten
                        df_new = df_hist[df_hist['year'] == 2025].copy()
                        df_new['cost_planned'] = df_new['cost_planned'] * factor
                        df_new['year'] = 2026
                        df_new['scenario'] = fixed_scenario_name
                        df_new['status'] = 'Planned Base'
                        # IDs entfernen
                        if 'id' in df_new.columns: del df_new['id']
                        if 'created_at' in df_new.columns: del df_new['created_at']
                        
                        insert_bulk_projects(df_new.to_dict('records'))
                        st.rerun()

                # Option 2: Status Quo
                with col_opt2:
                    st.markdown(f"""
                    <div class="css-card" style="text-align: center; border-left: 5px solid #00b894;">
                        <div class="card-title">Option B: Status Quo</div>
                        <div class="card-title">(Wert 2025)</div>
                        <div class="card-value">{fmt_de(last_year_val, 0)}</div>
                        <p style="font-size: 12px; margin-top: 10px;">Basis: Wir geben exakt so viel aus wie letztes Jahr.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("B wählen", key="btn_b", use_container_width=True):
                        df_new = df_hist[df_hist['year'] == 2025].copy()
                        # Kosten bleiben gleich
                        df_new['year'] = 2026
                        df_new['scenario'] = fixed_scenario_name
                        df_new['status'] = 'Planned Base'
                        if 'id' in df_new.columns: del df_new['id']
                        if 'created_at' in df_new.columns: del df_new['created_at']
                        insert_bulk_projects(df_new.to_dict('records'))
                        st.rerun()

                # Option 3: Trend
                with col_opt3:
                    st.markdown(f"""
                    <div class="css-card" style="text-align: center; border-left: 5px solid #ff7675;">
                        <div class="card-title">Option C: Trend</div>
                        <div class="card-title">(Fortschreibung)</div>
                        <div class="card-value">{fmt_de(trend_val, 0)}</div>
                        <p style="font-size: 12px; margin-top: 10px;">Basis: Das Wachstum setzt sich ungebremst fort.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("C wählen", key="btn_c", use_container_width=True):
                        factor = trend_val / last_year_val if last_year_val > 0 else 1
                        df_new = df_hist[df_hist['year'] == 2025].copy()
                        df_new['cost_planned'] = df_new['cost_planned'] * factor
                        df_new['year'] = 2026
                        df_new['scenario'] = fixed_scenario_name
                        df_new['status'] = 'Planned Base'
                        if 'id' in df_new.columns: del df_new['id']
                        if 'created_at' in df_new.columns: del df_new['created_at']
                        insert_bulk_projects(df_new.to_dict('records'))
                        st.rerun()

# ------------------------------------------------------------------
# TAB 3: MANUELLE PROJEKT PLANUNG (WIZARD)
# ------------------------------------------------------------------
elif selected == "Manuelle Projekt-Planung":
    st.title("📝 Projekt-Planung 2026")
    st.info("Hier planst du neue Investitionen (CAPEX) oder zusätzliche OPEX-Themen.")
    
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
            w_year = st.number_input("Budgetjahr", value=2026, step=1)
            if st.form_submit_button("Weiter ➡️"):
                if w_name:
                    st.session_state.wiz_data.update({'project_name': w_name, 'category': w_cat, 'year': w_year})
                    st.session_state.wizard_step = 2
                    st.rerun()
                else: st.error("Name fehlt.")

    elif step == 2:
        st.subheader("2. Finanzen")
        with st.form("wiz_step2"):
            c1, c2 = st.columns(2)
            with c1: w_btype = st.radio("Typ", ["OPEX", "CAPEX"])
            with c2: w_otype = st.selectbox("OPEX Art", ["-", "Lizenzen (SaaS)", "Cloud Infra", "Beratung", "Wartung"])
            w_cost = st.number_input("Kosten (€)", min_value=0.0, step=1000.0, value=10000.0)
            
            c_b1, c_b2 = st.columns(2)
            if c_b1.form_submit_button("⬅️ Zurück"):
                st.session_state.wizard_step = 1
                st.rerun()
            if c_b2.form_submit_button("Weiter ➡️"):
                st.session_state.wiz_data.update({'budget_type': w_btype, 'opex_type': w_otype if w_btype=="OPEX" else "", 'cost_planned': w_cost, 'savings_planned': 0})
                st.session_state.wizard_step = 3
                st.rerun()

    elif step == 3:
        st.subheader("3. Strategie")
        with st.form("wiz_step3"):
            w_risk = st.slider("Risiko", 1, 5, 2)
            w_score = st.slider("Strategie-Wert", 1, 10, 5)
            # Default Szenario ist "Budget 2026 (Fixed)" falls vorhanden, sonst manuell
            w_scen = st.text_input("Ziel-Szenario", value="Budget 2026 (Fixed)")
            
            c_b1, c_b2 = st.columns(2)
            if c_b1.form_submit_button("⬅️ Zurück"):
                st.session_state.wizard_step = 2
                st.rerun()
            if c_b2.form_submit_button("💾 Speichern", type="primary"):
                final = st.session_state.wiz_data.copy()
                final.update({'risk_factor': w_risk, 'strategic_score': w_score, 'scenario': w_scen, 'status': 'Planned'})
                try:
                    insert_bulk_projects([final])
                    st.success("Gespeichert!")
                    st.session_state.wiz_data = {}
                    st.session_state.wizard_step = 1
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"Fehler: {e}")

# ------------------------------------------------------------------
# TAB 4: SZENARIO SIMULATOR (GESAMT)
# ------------------------------------------------------------------
elif selected == "Szenario-Simulator (Gesamt)":
    st.title("🔮 Szenario-Simulator 2026")
    
    if df_proj.empty:
        st.warning("Keine Datenbasis.")
    else:
        # Basis ist das letzte Actual Jahr
        last_actual_year = df_proj[df_proj['scenario'] == 'Actual']['year'].max()
        df_base = df_proj[(df_proj['year'] == last_actual_year) & (df_proj['scenario'] == 'Actual')].copy()
        
        st.markdown(f"### 1. Treiber einstellen (Basisjahr: {last_actual_year})")
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
# TAB 5: SZENARIO VERGLEICH (FILTER + DARK MODE + SANKEY FIX)
# ------------------------------------------------------------------
elif selected == "Szenario-Vergleich":
    st.title("⚖️ Vergleich & Geldfluss")
    
    if df_proj.empty:
        st.warning("Keine Daten.")
    else:
        all_scens = list(df_proj['scenario'].unique())
        # Filtern: Wir wollen Actuals UND Simulationen sehen
        sim_scens = [s for s in all_scens if s != "Actual"]
        
        st.subheader("1. Szenario-Vergleich (Planungsjahre ab 2026)")
        
        c_sel, c_chart = st.columns([1, 3])
        with c_sel:
            st.info("Actuals werden nur zum Vergleich angezeigt.")
            comp_sel = st.multiselect("Szenarien:", sim_scens, default=sim_scens[:2] if sim_scens else [])
        
        with c_chart:
            # Wir nehmen Actual (als Referenz) und die gewählten
            fin_sel = ["Actual"] + comp_sel
            
            df_comp = df_proj[df_proj['scenario'].isin(fin_sel)].copy()
            # FILTER: Nur Zukunft (ab 2026) für Simulationen, aber vielleicht das letzte Actual Jahr als Referenz?
            # User wünschte: "nicht die Jahre 2023 bis 2025 darstellen" -> also >= 2026
            df_comp = df_comp[df_comp['year'] >= 2026] 
            
            if df_comp.empty:
                st.warning("Keine Daten ab 2026 gefunden.")
            else:
                df_grp = df_comp.groupby(['scenario', 'year'])['cost_planned'].sum().reset_index()
                
                fig_comp = px.bar(df_grp, x='scenario', y='cost_planned', color='scenario', 
                                  text_auto='.2s', title="Budget Vergleich (2026+)",
                                  color_discrete_map={"Actual": "#636e72"}, 
                                  color_discrete_sequence=px.colors.qualitative.Prism)
                fig_comp.update_layout(yaxis_title="Budget (€)", separators=",.", template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_comp, use_container_width=True)
        
        st.divider()
        
        st.subheader("2. Geldfluss (Sankey)")
        sel_scen = st.selectbox("Szenario:", fin_sel, index=0)
        
        df_flow = df_proj[df_proj['scenario'] == sel_scen].copy()
        if not df_flow.empty:
            top_p = df_flow.sort_values('cost_planned', ascending=False).head(15)
            
            labels = list(top_p['budget_type'].unique()) + list(top_p['category'].unique()) + list(top_p['project_name'].unique())
            def g_idx(n): return labels.index(n)
            
            src, tgt, val = [], [], []
            
            g1 = top_p.groupby(['budget_type', 'category'])['cost_planned'].sum().reset_index()
            for _, r in g1.iterrows():
                src.append(g_idx(r['budget_type'])); tgt.append(g_idx(r['category'])); val.append(r['cost_planned'])
            
            for _, r in top_p.iterrows():
                src.append(g_idx(r['category'])); tgt.append(g_idx(r['project_name'])); val.append(r['cost_planned'])
            
            cols = ["#6c5ce7"]*len(top_p['budget_type'].unique()) + ["#00b894"]*len(top_p['category'].unique()) + ["#a29bfe"]*len(top_p['project_name'].unique())
            
            fig_san = go.Figure(data=[go.Sankey(
                node = dict(
                    pad = 20, thickness = 30, 
                    line = dict(color = "black", width = 0.5), 
                    label = labels, 
                    color = cols,
                ),
                link = dict(source = src, target = tgt, value = val, color = "rgba(100, 100, 100, 0.3)"),
                textfont=dict(size=15, color=text_color, family="Arial Black")
            )])
            fig_san.update_layout(height=600, title_text=f"Flow: {sel_scen}", template=plotly_template, font=dict(size=14), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_san, use_container_width=True)

# ------------------------------------------------------------------
# TAB 6: KOSTEN & OPEX ANALYSE
# ------------------------------------------------------------------
elif selected == "Kosten & OPEX Analyse":
    st.title("💸 Kostenstruktur Detail-Analyse")
    
    if df_proj.empty: st.warning("Keine Daten.")
    else:
        yf = st.selectbox("Jahr", sorted(df_proj['year'].unique(), reverse=True))
        df_y = df_proj[(df_proj['year'] == yf) & (df_proj['scenario'] == 'Actual')]
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
        cy = df_proj[df_proj['scenario'] == 'Actual']['year'].max()
        df_c = df_proj[(df_proj['year'] == cy) & (df_proj['scenario'] == 'Actual')]
        
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
            insert_bulk_projects(projs)
            st.success("Erledigt!"); time.sleep(1); st.rerun()

    with t2:
        st.markdown("CSV Import"); up = st.file_uploader("CSV", type=['csv'])
        if up and st.button("Import"):
            insert_bulk_projects(pd.read_csv(up).to_dict('records'))
            st.success("Importiert!"); time.sleep(1); st.rerun()

    with t3:
        if st.button("🗑️ Löschen"): delete_all_projects(); delete_all_stats(); st.rerun()
