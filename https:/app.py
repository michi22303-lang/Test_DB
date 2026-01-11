import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import random
import time

# Nur für kurzzeitiges Debuggen einfügen:
if st.sidebar.button("🧹 Cache leeren"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

# Imports aus database.py
from database import (
    insert_bulk_projects, 
    get_projects, 
    insert_bulk_stats,
    get_stats,
    insert_bulk_actuals,
    delete_all_projects,
    delete_all_stats,
    delete_all_actuals,
    get_categories,
    insert_category,
    delete_category,
    get_actuals
)

st.set_page_config(page_title="CIO Cockpit Final", layout="wide", page_icon="🏢")

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
            "Administration"
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

# --- DATEN LADEN ---
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
    st.title("🏛️ Management Dashboard (2026)")
    
    if df_proj.empty:
        st.warning("Datenbank leer. Bitte Daten-Manager nutzen.")
    else:
        # PLAN 2026
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
        
        # FTE aus 2025
        if not df_stats.empty:
            stats_curr = df_stats[df_stats['year'] == 2025]
            fte = stats_curr.iloc[0]['fte_count'] if not stats_curr.empty else 0
        else: fte = 0
        
        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_func("Gesamt-Budget 2026", fmt_de(plan_total/1000000, 2, 'M€'), "Plan", delta_color)
        with c2: kpi_func("Ist-Kosten (YTD)", fmt_de(actual_total/1000000, 2, 'M€'), "Gebucht", "orange")
        with c3: kpi_func("Mitarbeiter Basis", fmt_de(fte, 0, ""), "Köpfe (2025)", delta_color)
        with c4: kpi_func("Ausschöpfung", f"{consumption:.1f}%", "Status", "red" if consumption > 100 else "green")
        
        st.markdown("---")
        
        col_main, col_side = st.columns([2, 1])
        with col_main:
            st.subheader("Plan vs. Ist (Kategorie)")
            pg = df_plan.groupby('category')['cost_planned'].sum().reset_index()
            pg['Type'] = 'Plan'; pg.rename(columns={'cost_planned':'Value'}, inplace=True)
            if not df_act_2026.empty:
                m = pd.merge(df_act_2026, df_proj[['id', 'category']], left_on='project_id', right_on='id', how='left')
                ag = m.groupby('category')['cost_actual'].sum().reset_index()
                ag['Type'] = 'Ist'; ag.rename(columns={'cost_actual':'Value'}, inplace=True)
                chart_df = pd.concat([pg, ag])
            else: chart_df = pg
            
            fig = px.bar(chart_df, x='category', y='Value', color='Type', barmode='group', 
                         color_discrete_map={'Plan': '#6c5ce7', 'Ist': '#00b894'}, text_auto='.2s')
            fig.update_layout(yaxis_title="€", template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
        with col_side:
            st.subheader("Budget Auslastung")
            max_val = plan_total if plan_total > 0 else 100
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = actual_total,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Ist vs. Plan", 'font': {'size': 20, 'color': text_color}},
                gauge = {
                    'axis': {'range': [None, max_val], 'tickwidth': 1, 'tickcolor': text_color},
                    'bar': {'color': "#6c5ce7"},
                    'bgcolor': "rgba(0,0,0,0)",
                    'steps': [
                        {'range': [0, max_val*0.75], 'color': "rgba(0, 184, 148, 0.3)"},
                        {'range': [max_val*0.75, max_val*0.95], 'color': "rgba(253, 203, 110, 0.3)"},
                        {'range': [max_val*0.95, max_val*1.5], 'color': "rgba(214, 48, 49, 0.3)"}
                    ],
                    'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': max_val}
                }
            ))
            fig_gauge.update_layout(height=350, margin=dict(t=30,b=10,l=10,r=10), paper_bgcolor='rgba(0,0,0,0)', font={'color': text_color})
            st.plotly_chart(fig_gauge, use_container_width=True)

# ------------------------------------------------------------------
# TAB 2: OPEX BASIS
# ------------------------------------------------------------------
elif selected == "1. Basis-Budget (OPEX)":
    st.title("🧱 Schritt 1: Betriebskosten-Basis 2026")
    
    fixed_scen = "Budget 2026 (Fixed)"
    df_fixed = df_proj[df_proj['scenario'] == fixed_scen]
    
    if not df_fixed.empty:
        st.success("✅ Basis steht.")
        st.metric("Sockelbetrag", fmt_de(df_fixed['cost_planned'].sum()))
        with st.expander("Details"): st.dataframe(df_fixed)
    else:
        st.markdown("Berechnungsmethode für den OPEX-Sockel wählen:")
        hist = df_proj[(df_proj['scenario']=='Actual') & (df_proj['budget_type']=='OPEX') & (df_proj['year'].isin([2023,2024,2025]))].copy()
        
        if hist.empty: st.warning("Keine Historie gefunden.")
        else:
            val_25 = hist[hist['year']==2025]['cost_planned'].sum()
            val_23 = hist[hist['year']==2023]['cost_planned'].sum()
            avg_val = hist.groupby('year')['cost_planned'].sum().mean()
            trend_factor = (val_25 / val_23) ** 0.5 if val_23 > 0 else 1.0 
            trend_val = val_25 * trend_factor
            
            c1, c2, c3, c4 = st.columns(4)
            def save_opex(factor, name):
                d = hist[hist['year']==2025].copy()
                d['cost_planned'] *= factor
                d['year'] = 2026; d['scenario'] = fixed_scen; d['status'] = 'Planned Base'
                if 'id' in d: del d['id']
                if 'created_at' in d: del d['created_at']
                insert_bulk_projects(d.to_dict('records')); st.rerun()

            with c1:
                st.markdown(f'<div class="css-card"><h4>Flat</h4><h3>{fmt_de(val_25,0)}</h3></div>', unsafe_allow_html=True)
                if st.button("Wähle Flat"): save_opex(1.0, "Flat")
            with c2:
                st.markdown(f'<div class="css-card"><h4>Ø 3 Jahre</h4><h3>{fmt_de(avg_val,0)}</h3></div>', unsafe_allow_html=True)
                if st.button("Wähle Ø"): save_opex(avg_val/val_25 if val_25>0 else 1, "Avg")
            with c3:
                st.markdown(f'<div class="css-card"><h4>Trend</h4><h3>{fmt_de(trend_val,0)}</h3><small>Wachstum fortschreiben</small></div>', unsafe_allow_html=True)
                if st.button("Wähle Trend"): save_opex(trend_factor, "Trend")
            with c4:
                manual_pct = st.number_input("Manuell %", value=5.0, step=1.0)
                man_val = val_25 * (1 + manual_pct/100)
                st.markdown(f'<div class="css-card"><h4>Manuell</h4><h3>{fmt_de(man_val,0)}</h3></div>', unsafe_allow_html=True)
                if st.button("Wähle Manuell"): save_opex(1 + manual_pct/100, "Manual")

# ------------------------------------------------------------------
# TAB 3: PROJEKT WIZARD (3 SCHRITTE)
# ------------------------------------------------------------------
elif selected == "2. Projekt-Planung":
    st.title("🚀 Schritt 2: Neue Projekte")
    st.info("Füge Investitionen oder neue Themen hinzu.")
    
    step = st.session_state.wizard_step
    
    # Fortschrittsanzeige
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.markdown(f"**1. Stammdaten** {'✅' if step > 1 else '🔵'}")
    col_s2.markdown(f"**2. Finanzen** {'✅' if step > 2 else '🔵'}")
    col_s3.markdown(f"**3. Strategie** {'✅' if step > 3 else '🔵'}")
    st.progress(step/3)
    st.divider()
    
    # ... (Vorheriger Code) ...

# ----------------------------------------------------
    # SCHRITT 1
    # ----------------------------------------------------
    if step == 1:  # <--- Achte darauf, dass dies bündig mit 'elif step == 2' ist
        with st.form("s1"):
            st.subheader("1. Stammdaten")
            
            # Funktionsaufruf (Import muss in app.py vorhanden sein!)
            cat_options = get_categories() 

            n = st.text_input("Projektname", value=st.session_state.wiz_data.get('project_name',''))
            
            # Selectbox mit Daten aus DB
            c = st.selectbox("Kategorie", cat_options)
            
            # Form Button Logik
            if st.form_submit_button("Weiter ➡️"):
                if n: 
                    st.session_state.wiz_data.update({'project_name':n, 'category':c, 'year':2026})
                    st.session_state.wizard_step = 2
                    st.rerun()
                else: 
                    st.error("Name fehlt")

    # ----------------------------------------------------
    # SCHRITT 2
    # ----------------------------------------------------
    elif step == 2: # <--- Dies verursachte den Fehler
        with st.form("s2"):
            st.subheader("2. Finanzen")
            c1, c2 = st.columns(2)
            with c1: t = st.radio("Typ", ["CAPEX", "OPEX"])
            with c2: o_type = st.selectbox("Art (bei OPEX)", ["-", "Lizenzen (SaaS)", "Cloud Infra", "Beratung"])
            cost = st.number_input("Kosten (€)", value=10000.0, step=1000.0)
            
            c_b1, c_b2 = st.columns(2)
            if c_b1.form_submit_button("⬅️ Zurück"):
                st.session_state.wizard_step = 1; st.rerun()
            if c_b2.form_submit_button("Weiter ➡️"):
                st.session_state.wiz_data.update({'budget_type':t, 'cost_planned':cost, 'opex_type': o_type if t=="OPEX" else ""})
                st.session_state.wizard_step=3; st.rerun()

    # SCHRITT 3
    elif step == 3:
        with st.form("s3"):
            st.subheader("3. Strategie")
            r = st.slider("Risiko", 1,5,2)
            s = st.slider("Wert", 1,10,5)
            
            c_b1, c_b2 = st.columns(2)
            if c_b1.form_submit_button("⬅️ Zurück"):
                st.session_state.wizard_step = 2; st.rerun()
            if c_b2.form_submit_button("💾 Speichern", type="primary"):
                d = st.session_state.wiz_data.copy()
                d.update({'risk_factor':r, 'strategic_score':s, 'scenario':'Planned Project', 'status':'Planned'})
                insert_bulk_projects([d])
                st.success("Gespeichert!")
                st.session_state.wiz_data={}; st.session_state.wizard_step=1; time.sleep(1); st.rerun()

# ------------------------------------------------------------------
# TAB 4: SZENARIO SIMULATOR
# ------------------------------------------------------------------
elif selected == "Szenario-Simulator":
    st.title("🔮 Tiefen-Simulation 2026")
    if df_proj.empty: st.warning("Keine Daten.")
    else:
        basis_2026 = df_proj[(df_proj['year']==2026) & (df_proj['scenario'].isin(['Budget 2026 (Fixed)', 'Planned Project']))].copy()
        if basis_2026.empty:
            st.info("Simuliere auf Basis 2025 Ist.")
            basis_2026 = df_proj[(df_proj['year']==2025) & (df_proj['scenario']=='Actual')].copy()
            basis_2026['year'] = 2026

        base_val = basis_2026['cost_planned'].sum()
        st.markdown(f"**Basis-Volumen:** {fmt_de(base_val)}")
        
        c1, c2, c3 = st.columns(3)
        sim_inf = c1.slider("Inflation", 0.0, 10.0, 3.0)/100
        sim_fte = c2.slider("Mitarbeiter-Wachstum", -10.0, 30.0, 5.0)/100
        sim_eff = c3.slider("Effizienz-Ziel", 0.0, 10.0, 2.0)/100
        
        df_sim = basis_2026.copy()
        def smart_calc(row):
            cost = row['cost_planned']
            cat = str(row.get('category', ''))
            otype = str(row.get('opex_type', ''))
            if "Lizenzen" in otype or "Workplace" in cat: return cost * (1 + sim_inf) * (1 + sim_fte)
            else: return cost * (1 + sim_inf)

        df_sim['cost_planned'] = df_sim.apply(smart_calc, axis=1) * (1 - sim_eff)
        sim_val = df_sim['cost_planned'].sum()
        
        st.divider()
        c_r1, c_r2 = st.columns(2)
        c_r1.metric("Simuliertes Budget", fmt_de(sim_val), delta=fmt_de(sim_val - base_val), delta_color="inverse")
        with c_r2:
            with st.form("save_sim"):
                n = st.text_input("Szenario Name", value=f"Sim FTE+{int(sim_fte*100)}%")
                if st.form_submit_button("Speichern"):
                    df_sim['scenario'] = n
                    if 'id' in df_sim: del df_sim['id']
                    if 'created_at' in df_sim: del df_sim['created_at']
                    insert_bulk_projects(df_sim.to_dict('records')); st.success("Gespeichert!")

# ------------------------------------------------------------------
# TAB 5, 6, 7 (VERGLEICH, ANALYSE, PORTFOLIO)
# ------------------------------------------------------------------
elif selected == "Szenario-Vergleich":
    st.title("⚖️ Vergleich & Flow")
    if not df_proj.empty:
        scens = [s for s in df_proj['scenario'].unique() if s != 'Actual']
        sel = st.multiselect("Vergleichen:", scens, default=scens[:2] if scens else [])
        if sel:
            d = df_proj[df_proj['scenario'].isin(sel)].groupby('scenario')['cost_planned'].sum().reset_index()
            fig = px.bar(d, x='scenario', y='cost_planned', color='scenario', title="Gesamtbudget", text_auto='.2s')
            fig.update_layout(template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            s_flow = st.selectbox("Sankey für:", sel)
            df_f = df_proj[df_proj['scenario'] == s_flow]
            if not df_f.empty:
                top = df_f.sort_values('cost_planned', ascending=False).head(15)
                lbl = list(top['budget_type'].unique()) + list(top['category'].unique()) + list(top['project_name'].unique())
                src, tgt, val = [], [], []
                def idx(x): return lbl.index(x)
                g1 = top.groupby(['budget_type', 'category'])['cost_planned'].sum().reset_index()
                for _,r in g1.iterrows(): src.append(idx(r['budget_type'])); tgt.append(idx(r['category'])); val.append(r['cost_planned'])
                for _,r in top.iterrows(): src.append(idx(r['category'])); tgt.append(idx(r['project_name'])); val.append(r['cost_planned'])
                cols = ["#6c5ce7"]*10 + ["#00b894"]*10 + ["#a29bfe"]*20
                fig_s = go.Figure(data=[go.Sankey(node=dict(label=lbl, color=cols, pad=20, thickness=20, line=dict(color="black", width=0.5)),
                                                  link=dict(source=src, target=tgt, value=val, color="rgba(100,100,100,0.3)"))])
                fig_s.update_layout(height=600, template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(size=14))
                st.plotly_chart(fig_s, use_container_width=True)

elif selected == "Kosten & OPEX Analyse":
    st.title("💸 Analyse")
    if not df_proj.empty:
        y = st.selectbox("Jahr", sorted(df_proj['year'].unique(), reverse=True))
        d = df_proj[df_proj['year']==y]
        if y == 2026: d = d[d['scenario'].isin(['Budget 2026 (Fixed)', 'Planned Project']) | (d['status']=='Planned')]
        fig = px.sunburst(d, path=['budget_type', 'category', 'project_name'], values='cost_planned')
        fig.update_layout(height=700, template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

elif selected == "Portfolio & Risiko":
    st.title("🎯 Portfolio")
    if not df_proj.empty:
        d = df_proj[(df_proj['year']==2026) & (df_proj['scenario']!='Actual')]
        if not d.empty:
            fig = px.scatter(d, x='strategic_score', y='risk_factor', size='cost_planned', color='category', hover_name='project_name', size_max=60)
            fig.update_layout(template=plotly_template, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------
# TAB 8: ADMINISTRATION (Ehemals Daten Manager)
# ------------------------------------------------------------------
elif selected == "Administration":
    st.title("🛠️ Administration")
    
    # Hier wurde "🏷️ Kategorien" als 4. Tab hinzugefügt
    t1, t2, t3, t4 = st.tabs(["🎲 Historie (22-25)", "📅 Ist-Werte 26", "⚠️ Reset", "🏷️ Kategorien"])
    
    with t1:
        st.markdown("**Erzeugt Projekte UND Mitarbeiterzahlen (2022-2025)**")
        if st.button("🚀 Historie generieren"):
            delete_all_projects(); delete_all_stats(); delete_all_actuals()
            stats_list, projs_list = [], []
            for y in [2022, 2023, 2024, 2025]:
                fte = int(500 * (1.05**(y-2022)))
                rev = 80000000 * (1.07**(y-2022))
                stats_list.append({"year": y, "fte_count": fte, "revenue": rev, "scenario": "Actual"})
                projs_list.append({"project_name": "M365 Lizenzen", "category": "Digitaler Arbeitsplatz", "budget_type": "OPEX", "opex_type": "Lizenzen", "year": y, "cost_planned": fte*1200, "scenario": "Actual", "status": "Live"})
                projs_list.append({"project_name": "Rechenzentrum", "category": "Infrastruktur", "budget_type": "OPEX", "opex_type": "Cloud", "year": y, "cost_planned": 300000, "scenario": "Actual", "status": "Live"})
                for i in range(4):
                    projs_list.append({"project_name": f"Projekt {y}-{i}", "category": random.choice(["Cloud","Security"]), "budget_type": "CAPEX", "year": y, "cost_planned": random.randint(50000, 200000), "scenario": "Actual", "status": "Closed"})
            insert_bulk_stats(stats_list)
            insert_bulk_projects(projs_list)
            st.success("Erledigt!"); time.sleep(1); st.rerun()
            
    with t2:
        m = st.selectbox("Monat", range(1,13))
        if st.button("Ist-Kosten buchen"):
            # Hinweis: Stellen Sie sicher, dass df_proj hier definiert ist oder laden Sie es neu
            pl = df_proj[(df_proj['year']==2026) & (df_proj['scenario'].isin(['Budget 2026 (Fixed)', 'Planned Project']))]
            if pl.empty: st.error("Kein Plan 2026.")
            else:
                a = []
                for _,r in pl.iterrows(): a.append({"project_id": r['id'], "year": 2026, "month": m, "cost_actual": (r['cost_planned']/12)*random.uniform(0.9,1.1)})
                insert_bulk_actuals(a); st.success("Gebucht!"); time.sleep(1); st.rerun()

    with t3:
        if st.button("Alles löschen"): 
            delete_all_projects()
            delete_all_stats()
            delete_all_actuals()
            st.rerun()

   # --- TAB 4: KATEGORIEN ---
    with t4:
        st.subheader("Projekt-Kategorien verwalten")
        
        # ... (Formular Code) ...
        
        categories = get_categories() 
        
        # --- DIAGNOSE START ---
        st.write("🔍 WAS KOMMT AUS DER DB?", categories)
        # --- DIAGNOSE ENDE ---

        if categories:
        
        # 1. Formular zum Anlegen
        with st.form("new_category_form", clear_on_submit=True):
            new_cat_name = st.text_input("Neue Kategorie Name:")
            submitted = st.form_submit_button("Hinzufügen")
            if submitted and new_cat_name:
                insert_category(new_cat_name) 
                st.success(f"Kategorie '{new_cat_name}' gespeichert.")
                time.sleep(0.5)
                st.rerun()
        
        st.divider()
        st.write("**Aktuelle Kategorien:**")
        
        # 2. Daten abrufen
        categories = get_categories() 
        
        # DEBUG: Falls Fehler auftreten, zeigen wir kurz die Rohdaten (können Sie später löschen)
        # st.write("Rohdaten:", categories)

        if categories:
            # WICHTIG: Falls 'categories' kein Array (Liste) ist, machen wir eine Liste daraus.
            # Das verhindert, dass Python über die Keys eines einzelnen Objekts iteriert.
            if not isinstance(categories, list):
                categories = [categories]

            for cat in categories:
                # Sicherheitscheck: Ist 'cat' wirklich ein Dictionary?
                if isinstance(cat, dict):
                    c1, c2 = st.columns([0.8, 0.2])
                    
                    val_name = cat.get('name', 'Unbekannt')
                    val_id = cat.get('id')
                    
                    c1.text(val_name)
                    
                    if val_id and c2.button("🗑️", key=f"del_cat_{val_id}"):
                        delete_category(val_id)
                        st.rerun()
                else:
                    # Falls 'cat' ein String ist (z.B. durch falsche Struktur), überspringen oder anzeigen
                    st.warning(f"Überspringe ungültigen Eintrag: {cat}")
        else:
            st.info("Noch keine Kategorien angelegt.")
