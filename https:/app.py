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

st.set_page_config(page_title="CIO Cockpit 3.0", layout="wide", page_icon="🏢")

# --- DESIGN & STYLE ---
def local_css():
    st.markdown("""
    <style>
        .block-container {padding-top: 1rem;}
        
        /* Karten Design */
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
        ["Management Dashboard", "Planung & Simulation 2026", "Kosten & OPEX Analyse", "Portfolio & Risiko", "Daten-Generator"],
        icons=["columns-gap", "calculator", "wallet2", "bullseye", "database-add"],
        default_index=0,
    )

# --- DATEN LADEN ---
try:
    raw_projects = get_projects()
    raw_stats = get_stats()
    df_proj = pd.DataFrame(raw_projects) if raw_projects else pd.DataFrame()
    df_stats = pd.DataFrame(raw_stats) if raw_stats else pd.DataFrame()
    
    # Alles in Kleinbuchstaben für stabilen Zugriff
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
        st.warning("Keine Daten gefunden. Bitte gehe zuerst zum Reiter 'Daten-Generator'!")
    else:
        current_year = 2025
        # Filter auf aktuelles Jahr
        df_p_curr = df_proj[(df_proj['year'] == current_year) & (df_proj['scenario'] == 'Actual')]
        df_s_curr = df_stats[(df_stats['year'] == current_year) & (df_stats['scenario'] == 'Actual')]
        
        # Vorjahr
        df_p_prev = df_proj[(df_proj['year'] == current_year - 1) & (df_proj['scenario'] == 'Actual')]
        
        if not df_s_curr.empty:
            fte = df_s_curr.iloc[0]['fte_count']
            revenue = df_s_curr.iloc[0]['revenue']
            
            total_budget = df_p_curr['cost_planned'].sum()
            prev_budget = df_p_prev['cost_planned'].sum() if not df_p_prev.empty else total_budget
            
            capex = df_p_curr[df_p_curr['budget_type'] == 'CAPEX']['cost_planned'].sum()
            opex = df_p_curr[df_p_curr['budget_type'] == 'OPEX']['cost_planned'].sum()
            
            spend_per_fte = total_budget / fte if fte > 0 else 0
            it_revenue_ratio = (total_budget / revenue * 100) if revenue > 0 else 0
            
            # KPI CARDS
            c1, c2, c3, c4 = st.columns(4)
            with c1: kpi_func("Gesamt IT-Budget", f"{total_budget/1000000:,.1f} M€", f"{(total_budget-prev_budget)/prev_budget*100:+.1f}% vs Vj.", "grey")
            with c2: kpi_func("Mitarbeiter (FTE)", f"{fte:,.0f}", "Köpfe", "grey")
            with c3: kpi_func("IT-Kosten pro Kopf", f"{spend_per_fte:,.0f} €", "Ø Benchmark: 8.500 €", "#6c5ce7")
            with c4: kpi_func("IT-Quote (v. Umsatz)", f"{it_revenue_ratio:.1f} %", "Ziel: < 5%", "green" if it_revenue_ratio < 5 else "orange")
            
            st.markdown("---")
            
            col_chart1, col_chart2 = st.columns([2, 1])
            with col_chart1:
                st.subheader("Entwicklung: Budget vs. Mitarbeiter")
                # Daten aggregieren
                df_trend_p = df_proj[df_proj['scenario'] == 'Actual'].groupby('year')['cost_planned'].sum().reset_index()
                df_trend_s = df_stats[df_stats['scenario'] == 'Actual'].groupby('year')['fte_count'].mean().reset_index()
                df_merge = pd.merge(df_trend_p, df_trend_s, on='year')
                
                fig = go.Figure()
                fig.add_trace(go.Bar(x=df_merge['year'], y=df_merge['cost_planned'], name="IT Budget (€)", marker_color='#6c5ce7'))
                fig.add_trace(go.Scatter(x=df_merge['year'], y=df_merge['fte_count'], name="Mitarbeiter (FTE)", yaxis='y2', line=dict(color='orange', width=3)))
                
                fig.update_layout(
                    yaxis=dict(title="Budget in €"), 
                    yaxis2=dict(title="Anzahl FTE", overlaying='y', side='right'), 
                    legend=dict(orientation="h", y=1.1)
                )
                st.plotly_chart(fig, use_container_width=True)
                
            with col_chart2:
                st.subheader("Verteilung: Invest (CAPEX) vs. Betrieb (OPEX)")
                fig_pie = px.pie(df_p_curr, values='cost_planned', names='budget_type', 
                                   color='budget_type', 
                                   # Wir nutzen hier Englisch im Code (Keys), aber Mapping bleibt gleich
                                   color_discrete_map={'CAPEX':'#00b894', 'OPEX':'#0984e3'}, hole=0.6)
                fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
                fig_pie.add_annotation(text=f"{opex/total_budget*100:.0f}%<br>OPEX", showarrow=False, font_size=20)
                st.plotly_chart(fig_pie, use_container_width=True)

# ------------------------------------------------------------------
# TAB 2: PLANUNG & SIMULATION 2026
# ------------------------------------------------------------------
elif selected == "Planung & Simulation 2026":
    st.title("🔮 Szenario-Planer 2026")
    
    if df_proj.empty:
        st.warning("Keine Datenbasis für Simulation vorhanden.")
    else:
        # Basis 2025 laden
        df_base = df_proj[(df_proj['year'] == 2025) & (df_proj['scenario'] == 'Actual')].copy()
        stats_base = df_stats[(df_stats['year'] == 2025) & (df_stats['scenario'] == 'Actual')]
        
        base_fte = stats_base.iloc[0]['fte_count'] if not stats_base.empty else 500
        base_rev = stats_base.iloc[0]['revenue'] if not stats_base.empty else 80000000

        # --- REGLER ---
        st.markdown("### 1. Annahmen definieren")
        st.info("Verändere die Parameter, um das Budget für 2026 zu simulieren.")
        
        c_in1, c_in2, c_in3, c_in4 = st.columns(4)
        
        with c_in1:
            sim_inflation = st.slider("📈 Inflation / Dienstleister", 0.0, 15.0, 4.0, format="%f%%") / 100
        with c_in2:
            sim_fte_growth = st.slider("👥 FTE Wachstum (Mitarbeiter)", -10.0, 30.0, 5.0, format="%f%%") / 100
        with c_in3:
            sim_rev_growth = st.slider("💰 Erwarteter Umsatz", -5.0, 20.0, 8.0, format="%f%%") / 100
        with c_in4:
            sim_efficiency = st.slider("✂️ Effizienz-Ziel (Savings)", 0.0, 20.0, 2.0, format="%f%%") / 100

        st.divider()

        # --- BERECHNUNG ---
        new_fte = int(base_fte * (1 + sim_fte_growth))
        new_rev = base_rev * (1 + sim_rev_growth)
        
        df_sim = df_base.copy()
        df_sim['year'] = 2026
        df_sim['scenario'] = 'Forecast'

        def calculate_forecast(row):
            cost = row['cost_planned']
            opex_type = row.get('opex_type', '')
            
            # Logik: Lizenzen hängen an FTEs
            if opex_type == "Lizenzen (SaaS)" or opex_type == "Licenses (SaaS)": # Support DE/EN
                return cost * (1 + sim_inflation) * (1 + sim_fte_growth)
            # Personal / Consulting hängt an Inflation
            elif row['budget_type'] == 'OPEX':
                return cost * (1 + sim_inflation)
            # Hardware (CAPEX) hängt an Inflation
            else:
                return cost * (1 + sim_inflation)

        df_sim['cost_planned'] = df_sim.apply(calculate_forecast, axis=1)
        df_sim['savings_planned'] = df_sim['savings_planned'] * (1 + sim_efficiency)

        # --- ERGEBNIS ---
        st.markdown("### 2. Simulations-Ergebnis")
        
        sim_budget = df_sim['cost_planned'].sum()
        base_budget = df_base['cost_planned'].sum()
        delta = sim_budget - base_budget
        
        sim_spend_per_fte = sim_budget / new_fte
        sim_it_ratio = (sim_budget / new_rev * 100)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Budget 2026 (Prognose)", f"{sim_budget/1000000:,.2f} M€", f"{delta/1000000:+.2f} M€", delta_color="inverse")
        k2.metric("Mitarbeiter 2026", f"{new_fte}", f"{new_fte - base_fte} Köpfe")
        k3.metric("IT-Kosten / Kopf", f"{sim_spend_per_fte:,.0f} €", f"{sim_spend_per_fte - (base_budget/base_fte):+.0f} €", delta_color="inverse")
        k4.metric("IT-Quote", f"{sim_it_ratio:.2f}%", f"{sim_it_ratio - (base_budget/base_rev*100):+.2f}%", delta_color="inverse")

        st.markdown("")
        col_v1, col_v2 = st.columns([2, 1])
        
        with col_v1:
            st.subheader("Wasserfall: Treiber-Analyse")
            inflation_effect = base_budget * sim_inflation
            growth_effect = (sim_budget - base_budget) - inflation_effect
            
            fig_water = go.Figure(go.Waterfall(
                name = "2026 Bridge", orientation = "v",
                measure = ["relative", "relative", "relative", "total"],
                x = ["2025 Basis", "Effekt Inflation", "Effekt Wachstum", "2026 Prognose"],
                textposition = "outside",
                text = [f"{base_budget/1000000:.1f}M", f"+{inflation_effect/1000000:.1f}M", f"+{growth_effect/1000000:.1f}M", f"{sim_budget/1000000:.1f}M"],
                y = [base_budget, inflation_effect, growth_effect, sim_budget],
                connector = {"line":{"color":"rgb(63, 63, 63)"}},
            ))
            fig_water.update_layout(title="Wie setzt sich das neue Budget zusammen?")
            st.plotly_chart(fig_water, use_container_width=True)

        with col_v2:
            st.subheader("Top Kostentreiber 2026")
            top_costs = df_sim.sort_values(by='cost_planned', ascending=False).head(5)
            # Spaltennamen für Anzeige umbenennen
            display_df = top_costs[['project_name', 'cost_planned']].rename(columns={'project_name': 'Projekt', 'cost_planned': 'Kosten (€)'})
            st.dataframe(display_df, hide_index=True)

# ------------------------------------------------------------------
# TAB 3: KOSTEN & OPEX ANALYSE
# ------------------------------------------------------------------
elif selected == "Kosten & OPEX Analyse":
    st.title("💸 Kostenstruktur Detail-Analyse")
    
    if df_proj.empty:
        st.warning("Keine Daten.")
    else:
        year_filter = st.selectbox("Geschäftsjahr wählen", sorted(df_proj['year'].unique(), reverse=True))
        df_yr = df_proj[(df_proj['year'] == year_filter) & (df_proj['scenario'] == 'Actual')]
        
        st.subheader(f"Drill-Down: Wohin fließt das Geld in {year_filter}?")
        df_yr['opex_type'] = df_yr['opex_type'].fillna("Investition")
        
        # Sunburst Chart
        fig_sun = px.sunburst(df_yr, path=['budget_type', 'category', 'opex_type', 'project_name'], values='cost_planned',
                              color='category', color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_sun.update_layout(height=700)
        st.plotly_chart(fig_sun, use_container_width=True)
        
        st.markdown("### Top Einzelpositionen")
        st.dataframe(df_yr.sort_values(by='cost_planned', ascending=False)[['project_name', 'category', 'cost_planned', 'status']].head(10))

# ------------------------------------------------------------------
# TAB 4: PORTFOLIO & RISIKO
# ------------------------------------------------------------------
elif selected == "Portfolio & Risiko":
    st.title("🎯 Strategisches Portfolio")
    
    if df_proj.empty:
        st.warning("Keine Daten.")
    else:
        current_year = 2025
        df_curr = df_proj[df_proj['year'] == current_year]
        
        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader("Matrix: Risiko vs. Strategischer Wert")
            fig_bub = px.scatter(df_curr, x="strategic_score", y="risk_factor",
                                 size="cost_planned", color="category",
                                 hover_name="project_name", size_max=60,
                                 labels={"strategic_score": "Strategischer Wert (Business Impact)", "risk_factor": "Implementierungs-Risiko"},
                                 title=f"Projekt-Landschaft {current_year}")
            
            # Quadranten
            fig_bub.add_hrect(y0=2.5, y1=5, line_width=0, fillcolor="red", opacity=0.1, annotation_text="Hohes Risiko")
            fig_bub.add_vrect(x0=5, x1=10, line_width=0, fillcolor="green", opacity=0.1, annotation_text="Hoher Wert")
            fig_bub.update_layout(xaxis=dict(range=[0, 11]), yaxis=dict(range=[0, 6]))
            st.plotly_chart(fig_bub, use_container_width=True)
            
        with c2:
            st.markdown("### Top Strategische Wetten")
            top_strats = df_curr[df_curr['strategic_score'] >= 8].sort_values(by='strategic_score', ascending=False)
            for index, row in top_strats.head(5).iterrows():
                st.info(f"**{row['project_name']}**\n\nScore: {row['strategic_score']}/10\n\nInvest: {row['cost_planned']/1000:.0f}k€")

# ------------------------------------------------------------------
# TAB 5: DATEN GENERATOR
# ------------------------------------------------------------------
elif selected == "Daten-Generator":
    st.title("⚙️ Simulations-Engine")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Generiert ein konsistentes Datenmodell (DEUTSCH):**
        1. Generiert FTE & Umsatz Historie (2023-2025)
        2. Berechnet Basiskosten (Lizenzen = Mitarbeiter * Preis)
        3. Erzeugt Projekt-Portfolio mit Abhängigkeiten
        """)
        
        if st.button("🚨 Alles löschen & Neu Generieren", type="primary"):
            with st.spinner("Bereinige Datenbank..."):
                delete_all_projects()
                delete_all_stats()
            
            with st.spinner("Generiere Szenarien..."):
                years = [2023, 2024, 2025] 
                base_fte = 500
                base_revenue = 80000000
                
                stats_data = []
                for y in years:
                    base_fte = int(base_fte * 1.05)
                    base_revenue = base_revenue * 1.07
                    stats_data.append({"year": y, "fte_count": base_fte, "revenue": base_revenue, "scenario": "Actual"})
                insert_bulk_stats(stats_data)
                
                projects_data = []
                # Deutsche Kategorien
                categories = ["Digitaler Arbeitsplatz", "Cloud Plattform", "Cyber Security", "ERP & Business Apps", "Data & KI"]
                
                for stat in stats_data:
                    year = stat['year']
                    fte = stat['fte_count']
                    
                    # A) Variable Kosten (FTE abhängig)
                    projects_data.append({
                        "project_name": "Globale Software Lizenzen (M365)",
                        "category": "Digitaler Arbeitsplatz",
                        "opex_type": "Lizenzen (SaaS)",
                        "budget_type": "OPEX",
                        "year": year,
                        "cost_planned": fte * 1200, 
                        "savings_planned": 0,
                        "risk_factor": 1, "strategic_score": 10, "status": "Live", "scenario": "Actual"
                    })
                    
                    # B) Zufallsprojekte
                    for i in range(8):
                        cat = random.choice(categories)
                        cost = random.randint(20000, 500000)
                        
                        # Typen Zuweisung (Deutsch)
                        if "Cloud" in cat or "Lizenzen" in str(cat):
                            b_type, o_type = "OPEX", "Cloud Infra"
                        else:
                            b_type, o_type = ("CAPEX", None) if random.random() > 0.5 else ("OPEX", "Beratung")

                        projects_data.append({
                            "project_name": f"{cat} Initiative {random.choice(['Alpha', 'Phoenix', 'Nexus'])} {i}",
                            "category": cat,
                            "opex_type": o_type,
                            "budget_type": b_type,
                            "year": year,
                            "cost_planned": cost,
                            "savings_planned": cost * random.uniform(0, 2.0),
                            "risk_factor": random.randint(1, 5),
                            "strategic_score": random.randint(1, 10),
                            "status": "Live",
                            "scenario": "Actual"
                        })

                insert_bulk_projects(projects_data)
                
            st.success("✅ Deutsche Datensätze erfolgreich generiert!")
            time.sleep(1)
            st.rerun()

    with col2:
        st.info("Datenstruktur:")
        st.markdown("- **Company Stats:** FTE, Umsatz pro Jahr")
        st.markdown("- **Projekte:** Verknüpft mit FTE (z.B. Lizenzkosten steigen automatisch).")
