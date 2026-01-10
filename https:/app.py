import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import random
import time  # Wichtig für time.sleep()

# Imports aus database.py
from database import insert_bulk_projects, get_projects, insert_bulk_stats, get_stats, delete_all_projects, delete_all_stats

st.set_page_config(page_title="CIO Cockpit 3.0", layout="wide", page_icon="🏢")

# --- DESIGN ---
def local_css():
    st.markdown("""
    <style>
        .block-container {padding-top: 1rem;}
        div.css-card {
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.2);
            padding: 15px;
            border-radius: 10px;
            border-left: 5px solid #6c5ce7; /* Lila Akzent */
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        div.card-title {font-size: 13px; text-transform: uppercase; opacity: 0.7; margin-bottom: 5px;}
        div.card-value {font-size: 24px; font-weight: bold;}
        div.card-delta {font-size: 14px; margin-top: 5px;}
    </style>
    """, unsafe_allow_html=True)

    # Funktion für KPI Cards
    def kpi_card(title, value, delta_text="", color="black"):
        st.markdown(f"""
        <div class="css-card">
            <div class="card-title">{title}</div>
            <div class="card-value">{value}</div>
            <div class="card-delta" style="color: {color}">{delta_text}</div>
        </div>
        """, unsafe_allow_html=True)
    
    return kpi_card

kpi_func = local_css() # Funktion initialisieren

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3094/3094851.png", width=50)
    st.markdown("### Digital Strategy Board")
    selected = option_menu(
        "Navigation",
        ["Executive Dashboard", "Cost & OPEX Deep-Dive", "Portfolio & Risk", "Data Generator"],
        icons=["columns-gap", "wallet2", "bullseye", "database-add"],
        default_index=0,
    )

# DATEN LADEN (Zentral)
try:
    raw_projects = get_projects()
    raw_stats = get_stats()
    df_proj = pd.DataFrame(raw_projects) if raw_projects else pd.DataFrame()
    df_stats = pd.DataFrame(raw_stats) if raw_stats else pd.DataFrame()
    
    # Bereinigen
    if not df_proj.empty: df_proj.columns = df_proj.columns.str.lower()
    if not df_stats.empty: df_stats.columns = df_stats.columns.str.lower()
    
except Exception as e:
    st.error(f"DB Connection Error: {e}")
    df_proj, df_stats = pd.DataFrame(), pd.DataFrame()

# ------------------------------------------------------------------
# TAB 1: EXECUTIVE DASHBOARD
# ------------------------------------------------------------------
if selected == "Executive Dashboard":
    st.title("🏛️ Executive Overview")
    
    if df_proj.empty or df_stats.empty:
        st.warning("Keine Daten. Bitte zuerst zum Tab 'Data Generator' gehen!")
    else:
        # Filter auf aktuelles Jahr (Beispiel 2025)
        current_year = 2025
        df_p_curr = df_proj[(df_proj['year'] == current_year) & (df_proj['scenario'] == 'Actual')]
        df_s_curr = df_stats[(df_stats['year'] == current_year) & (df_stats['scenario'] == 'Actual')]
        
        # Vorjahr für Vergleiche
        df_p_prev = df_proj[(df_proj['year'] == current_year - 1) & (df_proj['scenario'] == 'Actual')]
        
        if not df_s_curr.empty:
            fte = df_s_curr.iloc[0]['fte_count']
            revenue = df_s_curr.iloc[0]['revenue']
            
            total_budget = df_p_curr['cost_planned'].sum()
            prev_budget = df_p_prev['cost_planned'].sum() if not df_p_prev.empty else total_budget
            
            capex = df_p_curr[df_p_curr['budget_type'] == 'CAPEX']['cost_planned'].sum()
            opex = df_p_curr[df_p_curr['budget_type'] == 'OPEX']['cost_planned'].sum()
            
            # KPI: IT Spend per FTE
            spend_per_fte = total_budget / fte if fte > 0 else 0
            
            # KPI: IT Budget % vom Umsatz
            it_revenue_ratio = (total_budget / revenue * 100) if revenue > 0 else 0
            
            # LAYOUT
            c1, c2, c3, c4 = st.columns(4)
            with c1: kpi_func("Gesamt IT-Budget", f"{total_budget/1000000:,.1f} M€", f"{(total_budget-prev_budget)/prev_budget*100:+.1f}% vs Vj.", "grey")
            with c2: kpi_func("Mitarbeiter (FTE)", f"{fte:,.0f}", "Köpfe", "grey")
            with c3: kpi_func("IT-Kosten pro Kopf", f"{spend_per_fte:,.0f} €", "Ø Benchmark: 8.500 €", "#6c5ce7")
            with c4: kpi_func("IT-Quote (v. Umsatz)", f"{it_revenue_ratio:.1f} %", "Ziel: < 5%", "green" if it_revenue_ratio < 5 else "orange")
            
            st.markdown("---")
            
            # CHART: Budget Entwicklung + FTE
            col_chart1, col_chart2 = st.columns([2, 1])
            
            with col_chart1:
                st.subheader("Budget-Trend vs. FTE Wachstum")
                # Wir aggregieren Daten über alle Jahre
                df_trend_p = df_proj[df_proj['scenario'] == 'Actual'].groupby('year')['cost_planned'].sum().reset_index()
                df_trend_s = df_stats[df_stats['scenario'] == 'Actual'].groupby('year')['fte_count'].mean().reset_index()
                
                df_merge = pd.merge(df_trend_p, df_trend_s, on='year')
                
                fig = go.Figure()
                # Balken für Budget
                fig.add_trace(go.Bar(x=df_merge['year'], y=df_merge['cost_planned'], name="IT Budget (€)", marker_color='#6c5ce7'))
                # Linie für FTE
                fig.add_trace(go.Scatter(x=df_merge['year'], y=df_merge['fte_count'], name="Mitarbeiter", yaxis='y2', line=dict(color='orange', width=3)))
                
                fig.update_layout(
                    yaxis=dict(title="Budget in €"),
                    yaxis2=dict(title="Anzahl FTE", overlaying='y', side='right'),
                    legend=dict(orientation="h", y=1.1),
                    margin=dict(l=0, r=0, t=30, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
                
            with col_chart2:
                st.subheader("CAPEX vs. OPEX Split")
                # HIER WAR DER FEHLER: px.pie STATT px.donut
                fig_pie = px.pie(df_p_curr, values='cost_planned', names='budget_type', 
                                   color='budget_type', 
                                   color_discrete_map={'CAPEX':'#00b894', 'OPEX':'#0984e3'}, 
                                   hole=0.6) # hole macht es zum Donut
                fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
                # Text in die Mitte
                fig_pie.add_annotation(text=f"{opex/total_budget*100:.0f}%<br>OPEX", showarrow=False, font_size=20)
                st.plotly_chart(fig_pie, use_container_width=True)

# ------------------------------------------------------------------
# TAB 2: COST & OPEX DEEP-DIVE
# ------------------------------------------------------------------
elif selected == "Cost & OPEX Deep-Dive":
    st.title("💸 Wo fließt das Geld hin?")
    
    if df_proj.empty:
        st.warning("Keine Daten.")
    else:
        year_filter = st.selectbox("Jahr wählen", sorted(df_proj['year'].unique(), reverse=True))
        df_yr = df_proj[(df_proj['year'] == year_filter) & (df_proj['scenario'] == 'Actual')]
        
        # Sunburst Chart: Das ultimative Tool für Hierarchien
        # Wir zeigen: Budget Typ -> Kategorie -> OPEX Typ -> Projektname
        st.subheader(f"Kostenstruktur {year_filter}")
        
        # Daten vorbereiten für Sunburst (Wir füllen NaN bei CAPEX, da CAPEX oft keine 'opex_type' hat)
        df_yr['opex_type'] = df_yr['opex_type'].fillna("Investment")
        
        fig_sun = px.sunburst(df_yr, path=['budget_type', 'category', 'opex_type', 'project_name'], values='cost_planned',
                              color='category', color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_sun.update_layout(height=700)
        st.plotly_chart(fig_sun, use_container_width=True)
        
        # Tabelle für Details
        st.markdown("### Top Kostentreiber")
        st.dataframe(df_yr.sort_values(by='cost_planned', ascending=False)[['project_name', 'category', 'opex_type', 'cost_planned', 'status']].head(10))

# ------------------------------------------------------------------
# TAB 3: PORTFOLIO & RISK
# ------------------------------------------------------------------
elif selected == "Portfolio & Risk":
    st.title("🎯 Strategisches Portfolio")
    
    if df_proj.empty:
        st.warning("Keine Daten.")
    else:
        current_year = 2025
        df_curr = df_proj[df_proj['year'] == current_year]
        
        c1, c2 = st.columns([3, 1])
        
        with c1:
            st.subheader("Risk vs. Strategic Value Matrix")
            # Bubble Chart
            # X = Strategischer Wert (1-10)
            # Y = Risiko (1-5)
            # Größe = Kosten
            # Farbe = Kategorie
            
            fig_bub = px.scatter(df_curr, x="strategic_score", y="risk_factor",
                                 size="cost_planned", color="category",
                                 hover_name="project_name", size_max=60,
                                 labels={"strategic_score": "Strategischer Wert (Business Impact)", "risk_factor": "Implementierungs-Risiko"},
                                 title=f"Projekt-Landschaft {current_year}")
            
            # Quadranten einzeichnen
            fig_bub.add_hrect(y0=2.5, y1=5, line_width=0, fillcolor="red", opacity=0.1, annotation_text="High Risk")
            fig_bub.add_vrect(x0=5, x1=10, line_width=0, fillcolor="green", opacity=0.1, annotation_text="High Value")
            
            fig_bub.update_layout(xaxis=dict(range=[0, 11]), yaxis=dict(range=[0, 6]))
            st.plotly_chart(fig_bub, use_container_width=True)
            
        with c2:
            st.markdown("### Top Strategische Wetten")
            # Projekte mit Score > 8
            top_strats = df_curr[df_curr['strategic_score'] >= 8].sort_values(by='strategic_score', ascending=False)
            for index, row in top_strats.head(5).iterrows():
                st.info(f"**{row['project_name']}**\n\nScore: {row['strategic_score']}/10\n\nInvest: {row['cost_planned']/1000:.0f}k€")

# ------------------------------------------------------------------
# TAB 4: DATA GENERATOR
# ------------------------------------------------------------------
elif selected == "Data Generator":
    st.title("⚙️ Simulation Engine")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        Dieser Generator erstellt ein **konsistentes Datenmodell**:
        1. Er generiert zuerst Unternehmensdaten (FTEs, Umsatz) für 2023-2026.
        2. Darauf basierend berechnet er IT-Kosten (z.B. Lizenzen = 50€ * FTE).
        3. Er fügt zufällige Großprojekte (ERP, Migration) hinzu.
        """)
        
        if st.button("🚨 Alles löschen & Neu Generieren", type="primary"):
            with st.spinner("Lösche alte Daten..."):
                delete_all_projects()
                delete_all_stats()
            
            with st.spinner("Generiere Szenarien..."):
                # 1. Company Stats generieren (Wachstumsszenario)
                years = [2023, 2024, 2025, 2026]
                base_fte = 500
                base_revenue = 80000000 # 80 Mio
                
                stats_data = []
                # Kleines Wachstum simulieren
                for y in years:
                    base_fte = int(base_fte * 1.05) # 5% Wachstum
                    base_revenue = base_revenue * 1.07 # 7% Wachstum
                    stats_data.append({
                        "year": y, "fte_count": base_fte, "revenue": base_revenue, "scenario": "Actual"
                    })
                insert_bulk_stats(stats_data)
                
                # 2. Projekte generieren
                projects_data = []
                categories = ["Modern Workplace", "Cloud Platform", "Cyber Security", "ERP & Apps", "Data & AI"]
                opex_types = ["Licenses (SaaS)", "Cloud Infra", "Maintenance", "Consulting", "Personnel"]
                
                for stat in stats_data:
                    year = stat['year']
                    fte = stat['fte_count']
                    
                    # A) Automatische Kosten basierend auf FTE (Die "Baseload")
                    # Microsoft 365 Lizenzen etc.
                    projects_data.append({
                        "project_name": "Global Software Licenses",
                        "category": "Modern Workplace",
                        "opex_type": "Licenses (SaaS)",
                        "budget_type": "OPEX",
                        "year": year,
                        "cost_planned": fte * 1200, # 100€ pro User pro Monat
                        "savings_planned": 0,
                        "risk_factor": 1,
                        "strategic_score": 10, # Muss sein
                        "status": "Live",
                        "scenario": "Actual"
                    })
                    
                    # Hardware Leasing
                    projects_data.append({
                        "project_name": "Workplace Hardware Leasing",
                        "category": "Modern Workplace",
                        "opex_type": "Maintenance",
                        "budget_type": "OPEX",
                        "year": year,
                        "cost_planned": fte * 600, 
                        "savings_planned": 0,
                        "risk_factor": 1,
                        "strategic_score": 5,
                        "status": "Live",
                        "scenario": "Actual"
                    })

                    # B) Zufällige Projekte
                    for i in range(8): # 8 Projekte pro Jahr
                        cat = random.choice(categories)
                        
                        # Strategie Score & Risiko würfeln
                        strat = random.randint(1, 10)
                        risk = random.randint(1, 5)
                        
                        cost = random.randint(20000, 500000)
                        
                        # CAPEX oder OPEX?
                        if "Cloud" in cat or "Licenses" in str(cat):
                            b_type = "OPEX"
                            o_type = random.choice(["Cloud Infra", "Licenses (SaaS)"])
                        else:
                            # 50/50 Chance
                            if random.random() > 0.5:
                                b_type = "CAPEX"
                                o_type = None # CAPEX hat oft keine OPEX Kategorie im engeren Sinn
                            else:
                                b_type = "OPEX"
                                o_type = "Consulting"

                        projects_data.append({
                            "project_name": f"{cat} Initiative {random.choice(['Alpha', 'X', 'Prime'])}",
                            "category": cat,
                            "opex_type": o_type,
                            "budget_type": b_type,
                            "year": year,
                            "cost_planned": cost,
                            "savings_planned": cost * random.uniform(0, 2.5) if strat > 7 else 0, # Nur strategische Projekte sparen viel
                            "risk_factor": risk,
                            "strategic_score": strat,
                            "status": random.choice(["Live", "Planned", "In Progress"]),
                            "scenario": "Actual"
                        })

                insert_bulk_projects(projects_data)
                
            st.success("✅ Neue Simulations-Daten erstellt!")
            time.sleep(1)
            st.rerun()

    with col2:
        st.info("Datenstruktur:")
        st.markdown("- **Company Stats:** FTE, Umsatz pro Jahr")
        st.markdown("- **Digital Projects:** Verknüpft mit FTE (z.B. Lizenzkosten steigen automatisch).")
