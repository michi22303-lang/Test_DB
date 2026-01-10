import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px
import pandas as pd
import time

# --- IMPORTS ---
from database import insert_messwert, get_all_messwerte, delete_messwert

# --- 1. CONFIG ---
st.set_page_config(
    page_title="Cloud Dashboard",
    page_icon="🚀",
    layout="wide"
)

# --- 2. CSS & DESIGN (ADAPTIV: DARK & LIGHT MODE) ---
def local_css():
    st.markdown("""
    <style>
        /* Container Abstände */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* CARD DESIGN: Nutzt Streamlit-Variablen für Auto-Dark-Mode */
        div.css-card {
            background-color: var(--secondary-background-color); /* Passt sich an */
            border: 1px solid rgba(128, 128, 128, 0.2); /* Dezenter grauer Rand */
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); /* Sehr weicher Schatten */
            transition: transform 0.2s, box-shadow 0.2s;
            border-left: 6px solid #3498db; /* Unser Blau-Ton als Akzent */
            text-align: center;
            margin-bottom: 20px;
        }
        
        /* Hover-Effekt */
        div.css-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.15);
            border-left: 6px solid #85c1e9; /* Helleres Blau beim Hover */
        }

        /* Titel der Karte (Grau-Ton) */
        div.card-title {
            color: var(--text-color); /* Passt sich an */
            opacity: 0.7; /* Leicht ausgegraut für Eleganz */
            font-size: 14px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 5px;
        }
        
        /* Der Wert (Fett & Groß) */
        div.card-value {
            color: var(--text-color); /* Passt sich an */
            font-size: 36px;
            font-weight: 700;
            font-family: 'Segoe UI', sans-serif;
        }
        
        /* Das Icon (Blau) */
        div.card-icon {
            color: #3498db;
            font-size: 28px;
            margin-bottom: 15px;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 3. SIDEBAR (Blau/Grau Style) ---
with st.sidebar:
    # Hier können wir leider die Farben nicht per CSS ändern, das macht die Library.
    # Aber wir wählen Icons, die seriös wirken.
    selected = option_menu(
        menu_title="Navigation",
        options=["Eingabe", "Visualisierung"],
        icons=["pencil-square", "graph-up"], # Modernere Icons
        default_index=0,
        styles={
            "nav-link-selected": {"background-color": "#3498db"}, # Unser Blau
        }
    )

# --- 4. SEITE: EINGABE ---
if selected == "Eingabe":
    st.title("📝 Datenerfassung")
    st.caption("Füge neue Messwerte zur Datenbank hinzu.")
    
    with st.container():
        st.write("---")
        with st.form("entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                kategorie = st.selectbox("Kategorie", ["Umsatz", "Kosten", "Gewinn", "Marketing", "Sonstiges"])
            with col2:
                wert = st.number_input("Wert (€)", min_value=0, value=100, step=10)
                
            kommentar = st.text_area("Kommentar (optional)")
            
            # Button in Primary Color (Streamlit Standard oder User Config)
            submitted = st.form_submit_button("💾 Speichern", use_container_width=True)
            
            if submitted:
                try:
                    insert_messwert(kategorie, wert, kommentar)
                    st.success("Daten erfolgreich übermittelt!")
                except Exception as e:
                    st.error(f"Fehler: {e}")

# --- 5. SEITE: VISUALISIERUNG ---
elif selected == "Visualisierung":
    st.title("📊 Dashboard")
    
    try:
        raw_data = get_all_messwerte()
    except Exception as e:
        st.error(f"Datenbank nicht erreichbar: {e}")
        raw_data = []

    if not raw_data:
        st.info("Keine Daten vorhanden.")
    else:
        df = pd.DataFrame(raw_data)
        df.columns = df.columns.str.lower()
        
        # --- METRIKEN (KARTEN) ---
        if 'wert' in df.columns:
            total = df['wert'].sum()
            anzahl = len(df)
            last_date = str(df['created_at'].iloc[-1])[:10] if 'created_at' in df.columns else "-"
            
            # 3-Spalten Layout für die Karten
            m1, m2, m3 = st.columns(3)
            
            # Helper Funktion für sauberen HTML Code
            def card_html(icon, title, value):
                return f"""
                <div class="css-card">
                    <div class="card-icon">{icon}</div>
                    <div class="card-title">{title}</div>
                    <div class="card-value">{value}</div>
                </div>
                """

            with m1:
                st.markdown(card_html("💶", "Gesamtvolumen", f"{total:,.0f} €"), unsafe_allow_html=True)
            with m2:
                st.markdown(card_html("📂", "Datensätze", anzahl), unsafe_allow_html=True)
            with m3:
                st.markdown(card_html("🕒", "Letztes Update", last_date), unsafe_allow_html=True)
            
            st.markdown("---")

            # --- CHARTS (Blau/Grau Palette) ---
            c1, c2 = st.columns(2)
            
            # Wir definieren eine Blau-Grau Farbpalette für Plotly
            # (Dunkelblau, Mittelblau, Grau, Hellblau, Sehr helles Grau)
            custom_colors = ['#21618C', '#3498DB', '#85C1E9', '#BDC3C7', '#7F8C8D']
            
            with c1:
                st.subheader("Anteile nach Kategorie")
                if 'kategorie' in df.columns:
                    fig_pie = px.pie(df, names='kategorie', values='wert', hole=0.6,
                                     color_discrete_sequence=custom_colors) # Unsere Farben
                    fig_pie.update_traces(textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)
            
            with c2:
                st.subheader("Trendverlauf")
                if 'created_at' in df.columns:
                    # Balkendiagramm in Blau
                    fig_bar = px.bar(df, x='created_at', y='wert', color='kategorie',
                                     color_discrete_sequence=custom_colors)
                    fig_bar.update_layout(showlegend=False)
                    st.plotly_chart(fig_bar, use_container_width=True)

        # --- LÖSCHEN ---
        st.divider()
        with st.expander("🔧 Datenverwaltung"):
            if 'id' in df.columns:
                options = [f"ID {row['id']} | {row['kategorie']} | {row['wert']}€" for index, row in df.iterrows()]
                selected_option = st.selectbox("Eintrag entfernen:", options)
                
                if st.button("Löschen", type="primary"):
                    id_to_delete = selected_option.split(" |")[0].replace("ID ", "")
                    try:
                        delete_messwert(id_to_delete)
                        st.success("Gelöscht!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler: {e}")
