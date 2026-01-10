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

st.set_page_config(page_title="CIO Cockpit 6.0", layout="wide", page_icon="🏢")

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
        
        /* Wizard Steps */
        .step-active {color: #6c5ce7; font-weight: bold;}
        .step-inactive {color: gray;}
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

# --- INITIALISIERUNG SESSION STATE (FÜR WIZARD) ---
if 'wizard_step' not in st.session_state:
    st.session_state.wizard_step = 1
if 'wiz_data' not in st.session_state:
    st.session_state.wiz_data = {}

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3094/3094851.png", width=50)
    st.markdown("### Digital Strategy Board")
    
    selected = option_menu(
        "Navigation",
        [
            "Management Dashboard", 
            "Manuelle Planung (Wizard)",  # <-- NEU
            "Planung & Simulation", 
            "Szenario-Vergleich", 
            "Kosten & OPEX Analyse", 
            "Portfolio & Risiko", 
            "Daten-Manager"
        ],
        icons=["speedometer2", "pencil-square", "calculator", "diagram-3", "pie-chart", "bullseye", "database-gear"],
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
        st.warning("Keine Daten. Bitte zum 'Daten-Manager'!")
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
            
            opex_share = df_p_curr[df_p_curr['budget_type'] == 'OPEX']['cost_planned'].sum() / total_budget if total_budget > 0 else 0
            green_score = int(opex_share * 100) 
            
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
# TAB 2: MANUELLE PLANUNG (WIZARD) - NEU!
# ------------------------------------------------------------------
elif selected == "Manuelle Planung (Wizard)":
    st.title("📝 Projekt-Planung 2026")
    st.info("Dieser Assistent hilft dir, ein neues Budget manuell anzulegen.")
    
    # Fortschrittsanzeige
    step = st.session_state.wizard_step
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.markdown(f"**Schritt 1: Stammdaten** {'✅' if step > 1 else '🔵'}")
    col_s2.markdown(f"**Schritt 2: Finanzen** {'✅' if step > 2 else '🔵'}")
    col_s3.markdown(f"**Schritt 3: Strategie** {'✅' if step > 3 else '🔵'}")
    st.progress(step / 3)
    
    st.divider()

    # SCHRITT 1: STAMMDATEN
    if step == 1:
        st.subheader("1. Um welches Projekt geht es?")
        with st.form("wiz_step1"):
            w_name = st.text_input("Projektname", value=st.session_state.wiz_data.get('project_name', ''))
            w_cat = st.selectbox("Kategorie", ["Digitaler Arbeitsplatz", "Cloud Plattform", "Cyber Security", "ERP & Apps", "Data & KI", "Infrastruktur"], 
                                 index=0)
            w_year = st.number_input("Budgetjahr", value=2026, step=1)
            
            submitted_1 = st.form_submit_button("Weiter zu Finanzen ➡️")
            if submitted_1:
                if w_name:
                    st.session_state.wiz_data.update({'project_name': w_name, 'category': w_cat, 'year': w_year})
                    st.session_state.wizard_step = 2
                    st.rerun()
                else:
                    st.error("Bitte Projektnamen eingeben.")

    # SCHRITT 2: FINANZEN
    elif step == 2:
        st.subheader("2. Was wird es kosten?")
        with st.form("wiz_step2"):
            c1, c2 = st.columns(2)
            with c1:
                w_btype = st.radio("Budget Typ", ["OPEX", "CAPEX"])
            with c2:
                w_otype = st.selectbox("OPEX Art (nur falls OPEX)", ["-", "Lizenzen (SaaS)", "Cloud Infra", "Beratung", "Wartung"])
            
            w_cost = st.number_input("Geplante Kosten (€)", min_value=0.0, step=1000.0, value=10000.0)
            w_save = st.number_input("Erwartete Einsparung (€)", min_value=0.0, step=1000.0, value=0.0)
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                back_2 = st.form_submit_button("⬅️ Zurück")
            with col_b2:
                submitted_2 = st.form_submit_button("Weiter zu Strategie ➡️")
            
            if back_2:
                st.session_state.wizard_step = 1
                st.rerun()
            
            if submitted_2:
                st.session_state.wiz_data.update({
                    'budget_type': w_btype, 
                    'opex_type': w_otype if w_btype == "OPEX" else "", 
                    'cost_planned': w_cost, 
                    'savings_planned': w_save
                })
                st.session_state.wizard_step = 3
                st.rerun()

    # SCHRITT 3: STRATEGIE & SAVE
    elif step == 3:
        st.subheader("3. Strategische Einordnung")
        with st.form("wiz_step3"):
            w_risk = st.slider("Risiko-Faktor (1=Gering, 5=Hoch)", 1, 5, 2)
            w_score = st.slider("Strategischer Wert (1=Nett, 10=Gamechanger)", 1, 10, 5)
            w_scen = st.text_input("Szenario Name (z.B. 'Budget 2026 V1')", value="Budget 2026 Manuell")
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                back_3 = st.form_submit_button("⬅️ Zurück")
            with col_b2:
                final_submit = st.form_submit_button("💾 Projekt speichern", type="primary")
            
            if back_3:
                st.session_state.wizard_step = 2
                st.rerun()
                
            if final_submit:
                # Daten finalisieren
                final_data = st.session_state.wiz_data.copy()
                final_data.update({
                    'risk_factor': w_risk,
                    'strategic_score': w_score,
                    'scenario': w_scen,
                    'status': 'Planned'
                })
                
                # Speichern
                try:
                    insert_bulk_projects([final_data]) # Als Liste übergeben
                    st.success(f"Projekt '{final_data['project_name']}' erfolgreich gespeichert!")
                    
                    # Reset Wizard
                    st.session_state.wiz_data = {}
                    st.session_state.wizard_step = 1
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")

# ------------------------------------------------------------------
# TAB 3: PLANUNG & SIMULATION
# ------------------------------------------------------------------
elif selected == "Planung & Simulation":
    st.title("🔮 Szenario-Simulator 2026")
    
    if df_proj.empty:
        st.warning("Keine Datenbasis.")
    else:
        last_actual_year = df_proj[df_proj['scenario'] == 'Actual']['year'].max()
        df_base = df_proj[(df_proj['year'] == last_actual_year) & (df_proj['scenario'] == 'Actual')].copy()
        
        st.markdown(f"### 1. Treiber einstellen (Basisjahr: {last_actual_year})")
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
                scenario_name = st.text_input("Name des Szenarios (z.B. 'Best Case')", value="Szenario Auto")
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
# TAB 4: SZENARIO VERGLEICH (OPTIMIERT)
# ------------------------------------------------------------------
elif selected == "Szenario-Vergleich":
    st.title("⚖️ Vergleich & Geldfluss")
    
    if df_proj.empty:
        st.warning("Keine Daten.")
    else:
        # Alle Szenarien außer 'Actual' finden
        all_scenarios = list(df_proj['scenario'].unique())
        sim_scenarios = [s for s in all_scenarios if s != "Actual"]
        
        st.subheader("1. Szenario-Vergleich")
        
        col_sel, col_chart = st.columns([1, 3])
        
        with col_sel:
            st.markdown("**Vergleichsauswahl:**")
            # Actual ist immer dabei (fest codiert in der Logik unten)
            st.info("ℹ️ 'Actual' (Ist) wird immer angezeigt.")
            compare_selection = st.multiselect("Zusätzliche Szenarien wählen:", sim_scenarios, default=sim_scenarios[:2] if sim_scenarios else [])
        
        with col_chart:
            # Wir bauen die Liste: Actual + Auswahl
            final_selection = ["Actual"] + compare_selection
            
            # Daten filtern
            df_comp = df_proj[df_proj['scenario'].isin(final_selection)].groupby(['scenario', 'year'])['cost_planned'].sum().reset_index()
            
            # Chart
            fig_comp = px.bar(df_comp, x='scenario', y='cost_planned', color='scenario', 
                              text_auto='.2s', title="Gesamtbudget Vergleich",
                              color_discrete_map={"Actual": "#2d3436"}, # Actual immer dunkelgrau
                              color_discrete_sequence=px.colors.qualitative.Prism)
            fig_comp.update_layout(yaxis_title="Budget (€)", separators=",.")
            st.plotly_chart(fig_comp, use_container_width=True)
        
        st.divider()
        
        # SANKEY
        st.subheader("2. Geldfluss (Sankey)")
        selected_scen = st.selectbox("Szenario für Flow:", final_selection, index=0)
        
        df_flow = df_proj[df_proj['scenario'] == selected_scen].copy()
        
        if df_flow.empty:
            st.warning("Keine Daten für dieses Szenario.")
        else:
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
                try:
                    source.append(get_idx(row['budget_type']))
                    target.append(get_idx(row['category']))
                    value.append(row['cost_planned'])
                except: pass
                
            for _, row in top_projects.iterrows():
                try:
                    source.append(get_idx(row['category']))
                    target.append(get_idx(row['project_name']))
                    value.append(row['cost_planned'])
                except: pass
            
            if labels:
                node_colors = ["#6c5ce7"] * len(budget_types) + ["#00b894"] * len(categories) + ["#a29bfe"] * len(projects)
                
                

                fig_sankey = go.Figure(data=[go.Sankey(
                    node = dict(pad = 15, thickness = 20, line = dict(color = "black", width = 0.5), label = labels, color = node_colors),
                    link = dict(source = source, target = target, value = value, color = "rgba(100, 100, 100, 0.2)")
                )])
                fig_sankey.update_layout(height=600, title_text=f"Flow: {selected_scen}")
                st.plotly_chart(fig_sankey, use_container_width=True)

# ------------------------------------------------------------------
# TAB 5: KOSTEN & OPEX ANALYSE
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
# TAB 6: PORTFOLIO & RISIKO
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
# TAB 7: DATEN MANAGER
# ------------------------------------------------------------------
elif selected == "Daten-Manager":
    st.title("💾 Daten Management")
    
    tab_gen, tab_imp, tab_del = st.tabs(["🎲 Testdaten-Generator", "📂 CSV Import (Echtdaten)", "⚠️ Reset"])
    
    # --- SUB-TAB 1: GENERATOR ---
    with tab_gen:
        st.markdown("**Für Demos & Tests:** Erstellt ein konsistentes Datenmodell mit Zufallswerten.")
        if st.button("🚀 Testdaten generieren (2023-2025)", type="primary"):
            with st.spinner("Generiere..."):
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
                cats = ["Digitaler Arbeitsplatz", "Cloud Plattform", "Cyber Security", "ERP & Apps", "Data & KI"]
                for s in stats:
                    projs.append({
                        "project_name": "Globale Software Lizenzen", "category": "Digitaler Arbeitsplatz",
                        "opex_type": "Lizenzen", "budget_type": "OPEX", "year": s['year'],
                        "cost_planned": s['fte_count'] * 1200, "savings_planned": 0,
                        "risk_factor": 1, "strategic_score": 10, "status": "Live", "scenario": "Actual"
                    })
                    for i in range(8):
                        cat = random.choice(cats)
                        cost = random.randint(20000, 500000)
                        b_type = "OPEX" if "Cloud" in cat else ("CAPEX" if random.random() > 0.6 else "OPEX")
                        projs.append({
                            "project_name": f"{cat} Projekt {i+1}", "category": cat,
                            "opex_type": "Cloud" if b_type=="OPEX" else "", "budget_type": b_type,
                            "year": s['year'], "cost_planned": cost, "savings_planned": cost * 0.5,
                            "risk_factor": random.randint(1,5), "strategic_score": random.randint(1,10),
                            "status": "Live", "scenario": "Actual"
                        })
                insert_bulk_projects(projs)
            st.success("Testdaten erfolgreich erstellt!")
            time.sleep(1)
            st.rerun()

    # --- SUB-TAB 2: CSV IMPORT ---
    with tab_imp:
        st.markdown("### Echte Daten hochladen")
        
        sample_data = pd.DataFrame([{
            "project_name": "SAP Migration", "category": "ERP & Apps", "budget_type": "CAPEX", 
            "year": 2025, "cost_planned": 150000, "savings_planned": 0, "opex_type": "", 
            "risk_factor": 3, "strategic_score": 9, "status": "Live", "scenario": "Actual"
        }])
        csv_template = sample_data.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Muster-CSV herunterladen", csv_template, "vorlage.csv", "text/csv")
        
        st.markdown("---")
        uploaded_file = st.file_uploader("Deine CSV Datei wählen", type=['csv'])
        
        if uploaded_file is not None:
            try:
                df_upload = pd.read_csv(uploaded_file)
                st.write("Vorschau:", df_upload.head())
                if st.button("💾 Importieren"):
                    records = df_upload.to_dict('records')
                    insert_bulk_projects(records)
                    st.success(f"{len(records)} Zeilen importiert!")
                    time.sleep(1.5)
                    st.rerun()
            except Exception as e:
                st.error(f"Fehler: {e}")

    # --- SUB-TAB 3: RESET ---
    with tab_del:
        if st.button("🗑️ Alles löschen"):
            delete_all_projects()
            delete_all_stats()
            st.success("Datenbank leer.")
            st.rerun()
