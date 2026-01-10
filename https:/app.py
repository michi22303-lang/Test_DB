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

st.set_page_config(page_title="CIO Cockpit 4.0 - Enterprise Edition", layout="wide", page_icon="🚀")

# --- HELPER: DEUTSCHE ZAHLENFORMATIERUNG ---
def fmt_de(value, decimals=0, suffix="€"):
    if value is None: return ""
    try:
        s = f"{value:,.{decimals}f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{s} {suffix}".strip()
    except: return str(value)

# --- DESIGN & STYLE ---
def local_css():
    st.markdown("""
    <style>
        .block-container {padding-top: 1rem;}
        div.css-card {
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.2);
            padding: 15px;
            border-radius: 10px;
            border-left: 5px solid #6c5ce7;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        div.card-title {font-size: 13px; text-transform: uppercase; opacity: 0.7; margin-bottom: 5px;}
        div.card-value {font-size: 24px; font-weight: bold;}
        div.card-delta {font-size: 14px; margin-top: 5px;}
    </style>
    """, unsafe_allow_html=True)

    def kpi_card(title, value, delta_text="", color="black"):
        st.markdown(f"""
        <div class="css-card">
            <div class="card-title">{title}</div>
            <div class="card-value">{value}</div>
            <div class="card-delta" style="color: {color}">{delta_text}</div>
        </div>
        """, unsafe_allow_html=True)
    return kpi_card

kpi_func = local_css()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3094/3094851.png", width=50)
    st.markdown("### Digital Strategy Board")
    
    selected = option_menu(
        "Navigation",
        ["Management Dashboard", "Planung & Simulation", "Szenario-Vergleich & Flow", "Daten-Generator"],
        icons=["columns-gap", "calculator", "diagram-3", "database-add"],
        default_index=0,
    )

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
        st.warning("Keine Daten. Bitte zum 'Daten-Generator'!")
    else:
        # Wir zeigen immer das aktuellste "Actual" Jahr
        actual_years = sorted(df_proj[df_proj['scenario'] == 'Actual']['year'].unique())
        current_year = actual_years[-1] if actual_years else 2025
        
        df_p_curr = df_proj[(df_proj['year'] == current_year) & (df_proj['scenario'] == 'Actual')]
        df_s_curr = df_stats[(df_stats['year'] == current_year) & (df_stats['scenario'] == 'Actual')]
        df_p_prev = df_proj[(df_proj['year'] == current_year - 1) & (df_proj['scenario'] == 'Actual')]
        
        if not df_s_curr.empty:
            fte = df_s_curr.iloc[0]['fte_count']
            revenue = df_s_curr.iloc[0]['revenue']
            total_budget = df_p_curr['cost_planned'].sum()
            prev_budget = df_p_prev['cost_planned'].sum() if not df_p_prev.empty else total_budget
            
            # Neue KPI: Green IT Score (Simuliert)
            # Annahme: Je mehr OPEX (Cloud), desto höher der Score (weil effizienter als eigene Server)
            opex_share = df_p_curr[df_p_curr['budget_type'] == 'OPEX']['cost_planned'].sum() / total_budget
            green_score = int(opex_share * 100) 
            
            c1, c2, c3, c4 = st.columns(4)
            with c1: kpi_func("IT-Budget (Ist)", f"{fmt_de(total_budget/1000000, 2, 'M€')}", f"{fmt_de((total_budget-prev_budget)/prev_budget*100, 1, '%')} Wachstum", "grey")
            with c2: kpi_func("Mitarbeiter (FTE)", f"{fmt_de(fte, 0, '')}", "Köpfe", "grey")
            with c3: kpi_func("Green IT Score", f"{green_score}/100", "Cloud Efficiency Index", "green")
            with c4: kpi_func("IT-Quote", f"{fmt_de(total_budget/revenue*100, 2, '%')}", "Ziel: < 5%", "orange")
            
            st.markdown("---")
            
            col_chart1, col_chart2 = st.columns([2, 1])
            with col_chart1:
                st.subheader("Budget-Historie (Ist-Werte)")
                df_trend = df_proj[df_proj['scenario'] == 'Actual'].groupby('year')['cost_planned'].sum().reset_index()
                fig = px.bar(df_trend, x='year', y='cost_planned', text_auto='.2s', title="Budget Verlauf")
                fig.update_traces(marker_color='#6c5ce7', textfont_size=14)
                fig.update_layout(yaxis_title="Budget (€)", separators=",.")
                st.plotly_chart(fig, use_container_width=True)
                
            with col_chart2:
                st.subheader("Portfolio Risiko Matrix")
                fig_bub = px.scatter(df_p_curr, x="strategic_score", y="risk_factor", size="cost_planned", color="category",
                                     size_max=40, title=f"Portfolio {current_year}")
                fig_bub.update_layout(separators=",.")
                st.plotly_chart(fig_bub, use_container_width=True)

# ------------------------------------------------------------------
# TAB 2: PLANUNG & SIMULATION
# ------------------------------------------------------------------
elif selected == "Planung & Simulation":
    st.title("🔮 Szenario-Simulator 2026")
    
    if df_proj.empty:
        st.warning("Keine Datenbasis.")
    else:
        df_base = df_proj[(df_proj['year'] == 2025) & (df_proj['scenario'] == 'Actual')].copy()
        
        st.markdown("### 1. Treiber einstellen")
        c1, c2, c3, c4 = st.columns(4)
        with c1: sim_inf = st.slider("Inflation", 0.0, 10.0, 3.0, format="%f%%") / 100
        with c2: sim_fte = st.slider("FTE Wachstum", -5.0, 20.0, 5.0, format="%f%%") / 100
        with c3: sim_lic = st.slider("Lizenzpreiserhöhung", 0.0, 20.0, 10.0, format="%f%%") / 100
        with c4: sim_eff = st.slider("Effizienz (Savings)", 0.0, 10.0, 2.0, format="%f%%") / 100

        # --- LOGIK ---
        df_sim = df_base.copy()
        df_sim['year'] = 2026
        
        def calc_sim(row):
            cost = row['cost_planned']
            if "Lizenzen" in str(row.get('opex_type', '')):
                # Lizenzen = Preis * Menge (FTE)
                return cost * (1 + sim_lic) * (1 + sim_fte)
            elif row['budget_type'] == 'OPEX':
                return cost * (1 + sim_inf)
            else: 
                return cost * (1 + sim_inf) # Hardware
        
        df_sim['cost_planned'] = df_sim.apply(calc_sim, axis=1)
        
        # --- ERGEBNIS & SPEICHERN ---
        sim_sum = df_sim['cost_planned'].sum()
        base_sum = df_base['cost_planned'].sum()
        
        st.divider()
        c_res1, c_res2 = st.columns([2, 1])
        
        with c_res1:
            st.subheader("Simulations-Ergebnis")
            st.metric("Budget 2026 Prognose", fmt_de(sim_sum, 0, "€"), delta=fmt_de(sim_sum-base_sum, 0, "€"), delta_color="inverse")
            
            # --- DER NEUE SAVE BUTTON ---
            st.markdown("### 💾 Szenario speichern")
            with st.form("save_scenario"):
                scenario_name = st.text_input("Name des Szenarios (z.B. 'Best Case', 'Aggressives Wachstum')", value="Szenario A")
                submitted = st.form_submit_button("Szenario in Datenbank schreiben", type="primary")
                
                if submitted:
                    # Daten vorbereiten für Upload
                    # Wir müssen das DataFrame in eine Liste von dicts umwandeln
                    # Und wichtig: Das Szenario-Feld setzen!
                    df_upload = df_sim.copy()
                    df_upload['scenario'] = scenario_name
                    # ID muss weg, da neu generiert wird
                    if 'id' in df_upload.columns: del df_upload['id']
                    if 'created_at' in df_upload.columns: del df_upload['created_at']
                    
                    # Umwandeln und senden
                    records = df_upload.to_dict('records')
                    try:
                        # Vorher altes Szenario gleichen Namens löschen, um Duplikate zu vermeiden? 
                        # Fürs erste lassen wir es einfach hinzufügen (Versionierung)
                        insert_bulk_projects(records)
                        st.success(f"Szenario '{scenario_name}' erfolgreich gespeichert! Wechsel zum Tab 'Szenario-Vergleich'.")
                    except Exception as e:
                        st.error(f"Fehler: {e}")

# ------------------------------------------------------------------
# TAB 3: SZENARIO VERGLEICH & FLOW (NEU!)
# ------------------------------------------------------------------
elif selected == "Szenario-Vergleich & Flow":
    st.title("⚖️ Strategischer Vergleich & Geldfluss")
    
    if df_proj.empty:
        st.warning("Keine Daten.")
    else:
        # Welche Szenarien gibt es? (Actual + die gespeicherten)
        available_scenarios = df_proj['scenario'].unique()
        
        # 1. VERGLEICH
        st.subheader("1. Szenario-Vergleich (Budget 2026)")
        
        # Wir filtern auf 2026 (oder das Simulationsjahr)
        # Wenn wir nur Actual haben, macht Vergleich keinen Sinn, daher prüfen
        scenarios_to_compare = st.multiselect("Wähle Szenarien zum Vergleich:", available_scenarios, default=available_scenarios)
        
        if scenarios_to_compare:
            df_comp = df_proj[df_proj['scenario'].isin(scenarios_to_compare)].groupby(['scenario', 'year'])['cost_planned'].sum().reset_index()
            
            fig_comp = px.bar(df_comp, x='scenario', y='cost_planned', color='scenario', 
                              text_auto='.2s', title="Budget-Vergleich Total",
                              color_discrete_sequence=px.colors.qualitative.Prism)
            fig_comp.update_layout(yaxis_title="Budget (€)", separators=",.")
            st.plotly_chart(fig_comp, use_container_width=True)
        
        st.divider()
        
        # 2. SANKEY DIAGRAMM (Das "Spacige")
        st.subheader("2. Geldfluss-Analyse (Sankey Flow)")
        st.info("Visualisiert den Fluss: Budget-Art -> Kategorie -> Top Projekte")
        
        # Welches Szenario wollen wir visualisieren?
        selected_scen = st.selectbox("Szenario für Flow wählen:", available_scenarios, index=0)
        df_flow = df_proj[df_proj['scenario'] == selected_scen].copy()
        
        # Wir müssen die Daten aggregieren für das Sankey
        # Level 1: Budget Type (CAPEX/OPEX) -> Category
        # Level 2: Category -> Project (Top 10)
        
        # Sankey braucht: Source (Index), Target (Index), Value
        # Wir bauen eine Liste aller Labels
        
        # Wir nehmen nur die Top 15 teuersten Projekte, sonst wird die Grafik zu voll
        top_projects = df_flow.sort_values('cost_planned', ascending=False).head(15)
        
        # Alle Knoten sammeln
        labels = []
        source = []
        target = []
        value = []
        
        # Knoten definieren
        budget_types = list(top_projects['budget_type'].unique())
        categories = list(top_projects['category'].unique())
        projects = list(top_projects['project_name'].unique())
        
        labels = budget_types + categories + projects
        
        # Helper um Index zu finden
        def get_idx(name): return labels.index(name)
        
        # Link 1: Budget Type -> Category
        grp1 = top_projects.groupby(['budget_type', 'category'])['cost_planned'].sum().reset_index()
        for _, row in grp1.iterrows():
            source.append(get_idx(row['budget_type']))
            target.append(get_idx(row['category']))
            value.append(row['cost_planned'])
            
        # Link 2: Category -> Project
        for _, row in top_projects.iterrows():
            source.append(get_idx(row['category']))
            target.append(get_idx(row['project_name']))
            value.append(row['cost_planned'])
            
        # Farben generieren (Spacey Theme)
        node_colors = ["#6c5ce7"] * len(budget_types) + ["#00b894"] * len(categories) + ["#a29bfe"] * len(projects)
        
         

        fig_sankey = go.Figure(data=[go.Sankey(
            node = dict(
              pad = 15,
              thickness = 20,
              line = dict(color = "black", width = 0.5),
              label = labels,
              color = node_colors
            ),
            link = dict(
              source = source,
              target = target,
              value = value,
              color = "rgba(100, 100, 100, 0.2)" # Halb-transparente Verbindungen
          ))])
        
        fig_sankey.update_layout(title_text=f"Budget Flussdiagramm ({selected_scen})", font_size=12, height=600)
        st.plotly_chart(fig_sankey, use_container_width=True)

# ------------------------------------------------------------------
# TAB 4: DATEN GENERATOR
# ------------------------------------------------------------------
elif selected == "Daten-Generator":
    st.title("⚙️ System-Reset & Daten")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Reset:** Löscht alles und erstellt Basis-Daten für 2023-2025.")
        if st.button("🚨 System zurücksetzen & Neu Generieren", type="primary"):
            with st.spinner("Arbeite..."):
                delete_all_projects()
                delete_all_stats()
                
                # Stats
                stats = []
                base_fte, base_rev = 500, 80000000
                for y in [2023, 2024, 2025]:
                    base_fte = int(base_fte * 1.05)
                    base_rev *= 1.07
                    stats.append({"year": y, "fte_count": base_fte, "revenue": base_rev, "scenario": "Actual"})
                insert_bulk_stats(stats)
                
                # Projekte
                projs = []
                cats = ["Digital Workplace", "Cloud Platform", "Cyber Security", "ERP Core", "Data Analytics"]
                
                for s in stats:
                    # Fixkosten
                    projs.append({
                        "project_name": "M365 Lizenzen Global", "category": "Digital Workplace",
                        "opex_type": "Lizenzen", "budget_type": "OPEX", "year": s['year'],
                        "cost_planned": s['fte_count'] * 1200, "savings_planned": 0,
                        "risk_factor": 1, "strategic_score": 10, "status": "Live", "scenario": "Actual"
                    })
                    # Variable Projekte
                    for i in range(10):
                        cat = random.choice(cats)
                        cost = random.randint(50000, 800000)
                        b_type = "OPEX" if "Cloud" in cat else ("CAPEX" if random.random() > 0.6 else "OPEX")
                        projs.append({
                            "project_name": f"{cat} Initative {i+1}", "category": cat,
                            "opex_type": "Cloud" if b_type=="OPEX" else "", "budget_type": b_type,
                            "year": s['year'], "cost_planned": cost, "savings_planned": cost * 0.5,
                            "risk_factor": random.randint(1,5), "strategic_score": random.randint(1,10),
                            "status": "Live", "scenario": "Actual"
                        })
                insert_bulk_projects(projs)
                
            st.success("System erfolgreich resettet!")
            time.sleep(1)
            st.rerun()
