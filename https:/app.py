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

# --- 2. CSS & DESIGN-FUNKTIONEN (Der "Angular Material" Teil) ---
def local_css():
    st.markdown("""
    <style>
        /* Hintergrund etwas heller machen */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Überschriften stylen */
        h1, h2, h3 {
            font-family: 'Roboto', sans-serif;
            color: #2c3e50;
        }

        /* CARD STYLE: Das hier erzeugt den "Angular Material"-Look */
        div.css-card {
            background-color: #FFFFFF;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); /* Der Schatten */
            transition: transform 0.2s; /* Für Hover-Effekt */
            border-left: 5px solid #2E86C1; /* Der blaue Balken links */
            text-align: center;
            margin-bottom: 20px;
        }
        
        /* Hover-Effekt: Karte hebt sich beim Drüberfahren */
        div.css-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 15px rgba(0, 0, 0, 0.2);
        }

        /* Text in der Karte */
        div.card-title {
            color: #6c757d;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        div.card-value {
            color: #2c3e50;
            font-size: 32px;
            font-weight: bold;
            margin-top: 10px;
        }
        
        div.card-icon {
            font-size: 24px;
            margin-bottom: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

# CSS laden
local_css()

# --- 3. SIDEBAR ---
with st.sidebar:
    selected = option_menu(
        menu_title="Menü",
        options=["Eingabe", "Visualisierung"],
        icons=["pencil-square", "bar-chart-fill"],
        default_index=0,
    )

# --- 4. SEITE: EINGABE ---
if selected == "Eingabe":
    st.title("📝 Neuen Datensatz erfassen")
    st.markdown("Füge hier neue Daten hinzu. Sie landen sofort in der **Supabase Cloud**.")
    
    # Ein Container, damit es aufgeräumter aussieht
    with st.container():
        st.write("---")
        with st.form("entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                kategorie = st.selectbox("Kategorie", ["Umsatz", "Kosten", "Gewinn", "Marketing", "Sonstiges"])
            with col2:
                wert = st.number_input("Wert (€)", min_value=0, value=100, step=10)
                
            kommentar = st.text_area("Kommentar (optional)")
            
            # Button etwas breiter machen
            submitted = st.form_submit_button("💾 In Cloud speichern", use_container_width=True)
            
            if submitted:
                try:
                    insert_messwert(kategorie, wert, kommentar)
                    st.success("Erfolgreich gespeichert! Geh zum Tab 'Visualisierung'.")
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")

# --- 5. SEITE: VISUALISIERUNG ---
elif selected == "Visualisierung":
    st.title("📊 Dashboard & Analyse")
    
    try:
        raw_data = get_all_messwerte()
    except Exception as e:
        st.error(f"Verbindungsfehler: {e}")
        raw_data = []

    if not raw_data:
        st.info("Noch keine Daten vorhanden.")
    else:
        # Daten vorbereiten
        df = pd.DataFrame(raw_data)
        df.columns = df.columns.str.lower()
        
        # --- METRIKEN BERECHNEN ---
        if 'wert' in df.columns:
            total = df['wert'].sum()
            anzahl = len(df)
            last_date = str(df['created_at'].iloc[-1])[:10] if 'created_at' in df.columns else "-"
            
            st.markdown("### Kennzahlen")
            
            # --- HIER SIND DIE NEUEN "ANGULAR CARDS" ---
            m1, m2, m3 = st.columns(3)
            
            # Karte 1: Gesamtsumme
            with m1:
                st.markdown(f"""
                <div class="css-card">
                    <div class="card-icon">💰</div>
                    <div class="card-title">Gesamtsumme</div>
                    <div class="card-value">{total:,.0f} €</div>
                </div>
                """, unsafe_allow_html=True)
                
            # Karte 2: Anzahl
            with m2:
                st.markdown(f"""
                <div class="css-card">
                    <div class="card-icon">📦</div>
                    <div class="card-title">Datensätze</div>
                    <div class="card-value">{anzahl}</div>
                </div>
                """, unsafe_allow_html=True)

            # Karte 3: Datum
            with m3:
                st.markdown(f"""
                <div class="css-card">
                    <div class="card-icon">📅</div>
                    <div class="card-title">Letztes Update</div>
                    <div class="card-value">{last_date}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # --- CHARTS ---
            st.markdown("---")
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("Verteilung nach Kategorie")
                if 'kategorie' in df.columns:
                    # Donut Chart sieht moderner aus
                    fig_pie = px.pie(df, names='kategorie', values='wert', hole=0.5,
                                     color_discrete_sequence=px.colors.sequential.RdBu)
                    fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie, use_container_width=True)
            
            with c2:
                st.subheader("Verlauf über Zeit")
                if 'created_at' in df.columns:
                    fig_bar = px.bar(df, x='created_at', y='wert', color='kategorie')
                    # Chart etwas aufräumen
                    fig_bar.update_layout(xaxis_title="", yaxis_title="Wert (€)", showlegend=False)
                    st.plotly_chart(fig_bar, use_container_width=True)

        # --- DELETE BEREICH ---
        st.divider()
        with st.expander("🗑️ Datensätze verwalten"):
            if 'id' in df.columns:
                options = [f"ID {row['id']} | {row['kategorie']} | {row['wert']}€" for index, row in df.iterrows()]
                selected_option = st.selectbox("Eintrag wählen:", options)
                
                if st.button("Löschen 🚨", type="primary"):
                    id_to_delete = selected_option.split(" |")[0].replace("ID ", "")
                    try:
                        delete_messwert(id_to_delete)
                        st.success(f"ID {id_to_delete} gelöscht!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler: {e}")
