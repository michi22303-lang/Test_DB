import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px
import pandas as pd
import numpy as np
import random
import time

# Imports
from database import insert_bulk_projects, get_projects, delete_project

st.set_page_config(page_title="Digi-Planer 2.0", layout="wide", page_icon="📈")

# --- DESIGN (CSS) ---
def local_css():
    st.markdown("""
    <style>
        .block-container {padding-top: 2rem;}
        
        /* KPI Cards Style */
        div.css-card {
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.2);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            border-left: 5px solid #3498db;
            text-align: center;
        }
        div.card-value {
            font-size: 28px; font-weight: bold; color: var(--text-color);
        }
        div.card-title {
            font-size: 14px; text-transform: uppercase; opacity: 0.8;
        }
    </style>
    """, unsafe_allow_html=True)
local_css()

# --- SIDEBAR ---
with st.sidebar:
    selected = option_menu(
        "Digi-Suite",
        ["Dashboard", "Planung & Simulation", "Admin / Generator"],
        icons=["speedometer2", "calculator", "database-gear"],
        default_index=0,
    )

# ------------------------------------------------------------------
# TAB 1: DASHBOARD (HISTORIE)
# ------------------------------------------------------------------
if selected == "Dashboard":
    st.title("📊 Digitalisierungs-Historie")
    
    raw = get_projects()
    if not raw:
        st.info("Keine Daten. Geh zu 'Admin / Generator' und erstelle Testdaten!")
    else:
        df = pd.DataFrame(raw)
        
        # Nur "Actual" Daten zeigen (keine Simulationen)
        df_act = df[df['scenario'] == 'Actual']
        
        # KPI Berechnung
        capex = df_act[df_act['budget_type'] == 'CAPEX']['cost_planned'].sum()
        opex = df_act[df_act['budget_type'] == 'OPEX']['cost_planned'].sum()
        savings = df_act['savings_planned'].sum()
        
        # ROI Berechnung (Simpel: Einsparung / Kosten)
        total_cost = capex + opex
        roi_percent = ((savings - total_cost) / total_cost * 100) if total_cost > 0 else 0
        
        # KPIs anzeigen
        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(f'<div class="css-card"><div class="card-title">CAPEX Invest</div><div class="card-value">{capex:,.0f} €</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="css-card"><div class="card-title">OPEX Laufend</div><div class="card-value">{opex:,.0f} €</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="css-card"><div class="card-title">Einsparungen</div><div class="card-value">{savings:,.0f} €</div></div>', unsafe_allow_html=True)
        k4.markdown(f'<div class="css-card"><div class="card-title">Gesamt ROI</div><div class="card-value" style="color: {"green" if roi_percent > 0 else "red"}">{roi_percent:.1f}%</div></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Kosten nach Kategorie")
            fig = px.bar(df_act, x='year', y='cost_planned', color='category', title="Budget-Verteilung", barmode='group')
            st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            st.subheader("Invest vs. Savings (ROI Analyse)")
            # Scatter Plot: Wo liegen die Projekte?
            fig2 = px.scatter(df_act, x='cost_planned', y='savings_planned', color='category', 
                             size='cost_planned', hover_name='project_name',
                             title="Bubble Chart: Kosten (X) vs Einsparung (Y)")
            # Referenzlinie für Break-Even
            fig2.add_shape(type="line", x0=0, y0=0, x1=max(df_act['cost_planned']), y1=max(df_act['cost_planned']),
                           line=dict(color="Red", width=1, dash="dot"))
            st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------------
# TAB 2: PLANUNG & SIMULATION
# ------------------------------------------------------------------
elif selected == "Planung & Simulation":
    st.title("🔮 Planung 2026: Varianten-Simulator")
    
    raw = get_projects()
    if raw:
        df = pd.DataFrame(raw)
        # Wir nehmen 2025 als Basis
        df_base = df[(df['year'] == 2025) & (df['scenario'] == 'Actual')].copy()
        
        st.markdown("### 1. Annahmen definieren")
        col_input1, col_input2, col_input3 = st.columns(3)
        
        with col_input1:
            inflation = st.slider("Preisanstieg (Inflation/Vendor)", 0, 20, 5) / 100
        with col_input2:
            growth = st.slider("Unternehmenswachstum (Mitarbeiter)", 0, 30, 10) / 100
        with col_input3:
            efficiency = st.slider("Tech-Effizienzsteigerung (Savings)", 0, 50, 10) / 100
            
        st.divider()
        
        # SIMULATION BERECHNEN
        # Wir erstellen eine Kopie für 2026 Forecast
        df_sim = df_base.copy()
        df_sim['year'] = 2026
        df_sim['scenario'] = 'Forecast 2026'
        
        # Logik: 
        # - OPEX steigt mit Wachstum (mehr User) UND Inflation
        # - CAPEX steigt nur mit Inflation (Hardware wird teurer)
        # - Savings steigen durch Effizienz
        
        def calculate_new_cost(row):
            base_cost = row['cost_planned']
            if row['budget_type'] == 'OPEX':
                # OPEX wächst mit Inflation UND Mitarbeiterzahl
                return base_cost * (1 + inflation + growth)
            else:
                # CAPEX wächst nur mit Inflation
                return base_cost * (1 + inflation)

        df_sim['cost_planned'] = df_sim.apply(calculate_new_cost, axis=1)
        df_sim['savings_planned'] = df_sim['savings_planned'] * (1 + efficiency)
        
        # Ergebnis Darstellung
        st.markdown("### 2. Simulations-Ergebnis (2026)")
        
        total_cost_25 = df_base['cost_planned'].sum()
        total_cost_26 = df_sim['cost_planned'].sum()
        delta = total_cost_26 - total_cost_25
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Budget Bedarf 2026", f"{total_cost_26:,.0f} €", f"{delta:,.0f} €", delta_color="inverse")
        m2.metric("Erwartete Savings 2026", f"{df_sim['savings_planned'].sum():,.0f} €", f"{efficiency*100:.0f}% Boost")
        
        # Vergleichs-Chart
        df_combined = pd.concat([df_base.assign(Jahr="2025 Basis"), df_sim.assign(Jahr="2026 Sim")])
        
        fig_sim = px.bar(df_combined, x='category', y='cost_planned', color='Jahr', barmode='group',
                         title="Vergleich: Budget pro Kategorie 2025 vs 2026")
        st.plotly_chart(fig_sim, use_container_width=True)
        
        with st.expander("Detaillierte Projektdaten anzeigen"):
            st.dataframe(df_sim)

# ------------------------------------------------------------------
# TAB 3: ADMIN / GENERATOR
# ------------------------------------------------------------------
elif selected == "Admin / Generator":
    st.title("🛠️ Admin Tools")
    st.warning("Hier kannst du Testdaten generieren.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Testdaten erzeugen")
        st.markdown("Klicke den Button, um 50 zufällige Projekte für 2024/2025 in die Datenbank zu schreiben.")
        
        if st.button("🚀 Daten generieren & hochladen"):
            # DATEN GENERIERUNG (Python läuft in der Cloud!)
            years = [2024, 2025]
            categories = ["RPA Automation", "Cloud Migration", "Cyber Security", "SAP Upgrade", "AI Analytics", "Paperless Office"]
            budget_types = ["CAPEX", "OPEX"]
            
            fake_data = []
            for i in range(50):
                cat = random.choice(categories)
                b_type = "OPEX" if "Cloud" in cat or "AI" in cat else random.choice(budget_types)
                
                # Kosten würfeln
                cost = random.randint(10000, 150000)
                
                # Savings Logik: Automation bringt viel, Security wenig direktes Geld
                if "RPA" in cat: savings = cost * random.uniform(1.5, 4.0)
                elif "Security" in cat: savings = 0
                else: savings = cost * random.uniform(0.5, 1.5)
                
                row = {
                    "project_name": f"{cat} - Projekt {i}",
                    "category": cat,
                    "budget_type": b_type,
                    "year": random.choice(years),
                    "cost_planned": round(cost, 2),
                    "savings_planned": round(savings, 2),
                    "status": "Live",
                    "scenario": "Actual"
                }
                fake_data.append(row)
            
            # Hochladen
            try:
                insert_bulk_projects(fake_data)
                st.success(f"✅ 50 Projekte erfolgreich in 'digital_projects' gespeichert!")
            except Exception as e:
                st.error(f"Fehler beim Upload: {e}")
                
    with col2:
        st.subheader("Datenbank bereinigen")
        if st.button("🗑️ Alle Daten löschen (Vorsicht!)"):
            st.error("Feature zur Sicherheit deaktiviert. Lösche bitte über Supabase Dashboard.")
