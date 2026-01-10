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

st.set_page_config(page_title="CIO Cockpit 5.0 - Ultimate Edition", layout="wide", page_icon="🚀")

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
    
    # JETZT MIT 6 TABS - ALLES DABEI
    selected = option_menu(
        "Navigation",
        [
            "Management Dashboard", 
            "Planung & Simulation", 
            "Szenario-Vergleich & Flow", 
            "Kosten & OPEX Analyse", 
            "Portfolio & Risiko", 
            "Daten-Generator"
        ],
        icons=["speedometer2", "calculator", "diagram-3", "pie-chart", "bullseye", "database-gear"],
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
            
            # Green IT Score Berechnung
            opex_share = df_p_curr[df_p_curr['budget_type'] == 'OPEX']['cost_planned'].sum() / total_budget if total_budget > 0 else 0
            green_score = int(opex_share * 100) 
            
            # KPIs
            c1, c2, c3, c4 = st.columns(4)
            with c1: kpi_func("IT-Budget (Ist)", f"{fmt_de(total_budget/1000000, 2, 'M€')}", f"{fmt_de((total_budget-prev_budget)/prev_budget*100, 1, '%')} Wachstum", "grey")
            with c2: kpi_func("Mitarbeiter (FTE)", f"{fmt_de(fte, 0, '')}", "Köpfe", "grey")
            with c3: kpi_func("Green IT Score", f"{green_score}/100", "Cloud Efficiency Index", "green")
            with c4: kpi_func("IT-Quote", f"{fmt_de(total_budget/revenue*100, 2, '%')}", "Ziel: < 5%", "orange")
            
            st.markdown("---")
            
            col_chart1, col_chart2 = st.columns([2, 1])
            with col_chart1:
                st.subheader("Budget-Historie")
                df_trend = df_proj[df_proj['scenario'] == 'Actual'].groupby('year')['cost_planned'].sum().reset_index()
                fig = px.bar(df_trend, x='year', y='cost_planned', text_auto='.2s', title="Budget Verlauf (Actual)")
                fig.update_traces(marker_color='#6c5ce7')
                fig.update_layout(yaxis_title="Budget (€)", separators=",.")
                st.plotly_chart(fig, use_container_width=True)
                
            with col_chart2:
                st.subheader("Invest (CAPEX) vs. Betrieb (OPEX)")
                fig_pie = px.pie(df_p_curr, values='cost_planned', names='budget_type', 
                                 color='budget_type', hole=0.6,
                                 color_discrete_map={'CAPEX':'#00b894', 'OPEX':'#0984e3'})
                fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0), separators=",.")
                st.plotly_chart(fig_pie, use_container_width=True)

# ------------------------------------------------------------------
# TAB 2: PLANUNG & SIMULATION
# ------------------------------------------------------------------
elif selected == "Planung & Simulation":
    st.title("🔮 Szenario-Simulator 2026")
    
    if df_proj.empty:
        st.warning("Keine Datenbasis.")
    else:
        # Wir nehmen das letzte "Actual" Jahr als Basis (meist 2025)
        last_actual_year = df_proj[df_proj['scenario'] == 'Actual']['year'].max()
        df_base = df_proj[(df_proj['year'] == last_actual_year) & (df_proj['scenario'] == 'Actual')].copy()
        
        st.markdown(f"### 1. Annahmen definieren (Basisjahr: {last_actual_year})")
        c1, c2, c3, c4 = st.columns(4)
        with c1: sim_inf = st.slider("Inflation", 0.0, 10.0, 3.0, format="%f%%") / 100
        with c2: sim_fte = st.slider("FTE Wachstum", -5.0, 20.0, 5.0, format="%f%%") / 100
        with c3: sim_lic = st.slider("Lizenzpreiserhöhung", 0.0, 20.0, 10.0, format="%f%%") / 100
        with c4: sim_eff = st.slider("Effizienz (Savings)", 0.0, 10.0, 2.0, format="%f%%") / 100

        # Simulation
        df_sim = df_base.copy()
        target_year = last_actual_year + 1
        df_sim['year'] = target_year
        
        def calc_sim(row):
            cost = row['cost_planned']
            opex = str(row.get('opex_type', ''))
            if "Lizenzen" in opex or "Licenses" in opex:
                return cost * (1 + sim_lic) * (1 + sim_fte)
            elif row['budget_type'] == 'OPEX':
                return cost * (1 + sim_inf)
            else: 
                return cost * (1 + sim_inf)
        
        df_sim['cost_planned'] = df_sim.apply(calc_sim, axis=1)
        
        # Ergebnis
        sim_sum = df_sim['cost_planned'].sum()
        base_sum = df_base['cost_planned'].sum()
        
        st.divider()
        c_res1, c_res2 = st.columns([2, 1])
        
        with c_res1:
            st.subheader(f"Ergebnis Prognose {target_year}")
            st.metric("Budget Bedarf", fmt_de(sim_sum, 0, "€"), delta=fmt_de(sim_sum-base_sum, 0, "€"), delta_color="inverse")
            
            # --- SPEICHERN ---
            st.markdown("### 💾 Szenario speichern")
            with st.form("save_scenario"):
                scenario_name = st.text_input("Name des Szenarios (z.B. 'Best Case')", value="Szenario A")
                submitted = st.form_submit_button("Szenario in Datenbank schreiben", type="primary")
                
                if submitted:
                    df_upload = df_sim.copy()
                    df_upload['scenario'] = scenario_name
                    if 'id' in df_upload.columns: del df_upload['id']
                    if 'created_at' in df_upload.columns: del df_upload['created_at']
                    
                    records = df_upload.to_dict('records')
                    try:
                        insert_bulk_projects(records)
                        st.success(f"Szenario '{scenario_name}' erfolgreich gespeichert!")
                    except Exception as e:
                        st.error(f"Fehler: {e}")

# ------------------------------------------------------------------
# TAB 3: SZENARIO VERGLEICH & FLOW
# ------------------------------------------------------------------
elif selected == "Szenario-Vergleich & Flow":
    st.title("⚖️ Vergleich & Geldfluss")
    
    if df_proj.empty:
        st.warning("Keine Daten.")
    else:
        available_scenarios = df_proj['scenario'].unique()
        
        st.subheader("1. Szenario-Vergleich")
        scenarios_to_compare = st.multiselect("Szenarien wählen:", available_scenarios, default=available_scenarios)
        
        if scenarios_to_compare:
            df_comp = df_proj[df_proj['scenario'].isin(scenarios_to_compare)].groupby(['scenario', 'year'])['cost_planned'].sum().reset_index()
            fig_comp = px.bar(df_comp, x='scenario', y='cost_planned', color='scenario', 
                              text_auto='.2s', title="Gesamtbudget Vergleich",
                              color_discrete_sequence=px.colors.qualitative.Prism)
            fig_comp.update_layout(yaxis_title="Budget (€)", separators=",.")
            st.plotly_chart(fig_comp, use_container_width=True)
        
        st.divider()
        st.subheader("2. Geldfluss (Sankey)")
        selected_scen = st.selectbox("Szenario für Flow:", available_scenarios, index=0)
        
        # Sankey Logic
        df_flow = df_proj[df_proj['scenario'] == selected_scen].copy()
        top_projects = df_flow.sort_values('cost_planned', ascending=False).head(15)
        
        labels = []
        source = []
        target = []
        value = []
        
        budget_types = list(top_projects['budget_type'].unique())
        categories = list(top_projects['category'].unique())
        projects = list(top_projects['project_name'].unique())
        
        labels = budget_types + categories + projects
        def get_idx(name): return labels.index(name)
        
        grp1 = top_projects.groupby(['budget_type', 'category'])['cost_planned'].sum().reset_index()
        for _, row in grp1.iterrows():
            source.append(get_idx(row['budget_type']))
            target.append(get_idx(row['category']))
            value.append(row['cost_planned'])
            
        for _, row in top_projects.iterrows():
            source.append(get_idx(row['category']))
            target.append(get_idx(row['project_name']))
            value.append(row['cost_planned'])
            
        node_colors = ["#6c5ce7"] * len(budget_types) + ["#00b894"] * len(categories) + ["#a29bfe"] * len(projects)
        
        fig_sankey = go.Figure(data=[go.Sankey(
            node = dict(pad = 15, thickness = 20, line = dict(color = "black", width = 0.5), label = labels, color = node_colors),
            link = dict(source = source, target = target, value = value, color = "rgba(100, 100, 100, 0.2)")
        )])
        fig_sankey.update_layout(height=600, title_text=f"Flow: {selected_scen}")
        st.plotly_chart(fig_sankey, use_container_width=True)

# ------------------------------------------------------------------
# TAB 4: KOSTEN & OPEX ANALYSE (WIEDER DA!)
# ------------------------------------------------------------------
elif selected == "Kosten & OPEX Analyse":
    st.title("💸 Kostenstruktur Detail-Analyse")
    
    if df_proj.empty:
        st.warning("Keine Daten.")
    else:
        year_filter = st.selectbox("Geschäftsjahr wählen", sorted(df_proj['year'].unique(), reverse=True))
        df_yr = df_proj[(df_proj['year'] == year_filter) & (df_proj['scenario'] == 'Actual')]
        
        st.subheader(f"Drill-Down: {year_filter}")
        df_yr['opex_type'] = df_yr['opex_type'].fillna("Investition")
        
        # Sunburst Chart
        fig_sun = px.sunburst(df_yr, path=['budget_type', 'category', 'opex_type', 'project_name'], values='cost_planned',
                              color='category', color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_sun.update_layout(height=700, separators=",.")
        st.plotly_chart(fig_sun, use_container_width=True)
        
        st.markdown("### Top Positionen")
        top_list = df_yr.sort_values(by='cost_planned', ascending=False)[['project_name', 'category', 'cost_planned', 'status']].head(10)
        top_list['cost_planned'] = top_list['cost_planned'].apply(lambda x: fmt_de(x, 2, '€'))
        st.dataframe(top_list, use_container_width=True)

# ------------------------------------------------------------------
# TAB 5: PORTFOLIO & RISIKO (WIEDER DA!)
# ------------------------------------------------------------------
elif selected == "Portfolio & Risiko":
    st.title("🎯 Strategisches Portfolio")
    
    if df_proj.empty:
        st.warning("Keine Daten.")
    else:
        current_year = df_proj[df_proj['scenario'] == 'Actual']['year'].max()
        df_curr = df_proj[(df_proj['year'] == current_year) & (df_proj['scenario'] == 'Actual')]
        
        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader("Matrix: Risiko vs. Wert")
            fig_bub = px.scatter(df_curr, x="strategic_score", y="risk_factor",
                                 size="cost_planned", color="category",
                                 hover_name="project_name", size_max=60,
                                 labels={"strategic_score": "Strategischer Wert", "risk_factor": "Risiko"},
                                 title=f"Projekt-Landschaft {current_year}")
            
            fig_bub.add_hrect(y0=2.5, y1=5, line_width=0, fillcolor="red", opacity=0.1, annotation_text="Hohes Risiko")
            fig_bub.add_vrect(x0=5, x1=10, line_width=0, fillcolor="green", opacity=0.1, annotation_text="Hoher Wert")
            fig_bub.update_layout(xaxis=dict(range=[0, 11]), yaxis=dict(range=[0, 6]), separators=",.")
            st.plotly_chart(fig_bub, use_container_width=True)
            
        with c2:
            st.markdown("### Top Wetten")
            top_strats = df_curr[df_curr['strategic_score'] >= 8].sort_values(by='strategic_score', ascending=False)
            for index, row in top_strats.head(5).iterrows():
                st.info(f"**{row['project_name']}**\n\nScore: {row['strategic_score']}\nInvest: {fmt_de(row['cost_planned']/1000, 0, 'k€')}")

# ------------------------------------------------------------------
# TAB 6: DATEN GENERATOR
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
                
                stats = []
                base_fte, base_rev = 500, 80000000
                for y in [2023, 2024, 2025]:
                    base_fte = int(base_fte * 1.05)
                    base_rev *= 1.07
                    stats.append({"year": y, "fte_count": base_fte, "revenue": base_rev, "scenario": "Actual"})
                insert_bulk_stats(stats)
                
                projs = []
                cats = ["Digital Workplace", "Cloud Platform", "Cyber Security", "ERP Core", "Data Analytics"]
                
                for s in stats:
                    projs.append({
                        "project_name": "M365 Lizenzen Global", "category": "Digital Workplace",
                        "opex_type": "Lizenzen", "budget_type": "OPEX", "year": s['year'],
                        "cost_planned": s['fte_count'] * 1200, "savings_planned": 0,
                        "risk_factor": 1, "strategic_score": 10, "status": "Live", "scenario": "Actual"
                    })
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
