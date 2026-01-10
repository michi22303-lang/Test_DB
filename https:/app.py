import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px
import pandas as pd
import time

# Importiere unsere Datenbank-Funktionen
# (Stelle sicher, dass die Datei database.py im selben Ordner liegt)
from database import insert_messwert, get_all_messwerte

# --- PAGE CONFIG ---
st.set_page_config(page_title="Cloud Dashboard", layout="wide")

# --- HEADER ---
st.title("☁️ Unser Live-Dashboard")
st.markdown("Daten werden in **Supabase** gespeichert und live visualisiert.")

# --- SIDEBAR & NAVIGATION ---
with st.sidebar:
    selected = option_menu(
        menu_title="Menü",
        options=["Eingabe", "Visualisierung"],
        icons=["pencil-square", "bar-chart-fill"],
        default_index=0,
    )

# --- SEITE 1: EINGABE ---
if selected == "Eingabe":
    st.subheader("Neuen Datensatz erfassen")
    
    # Wir nutzen ein Formular, damit die Seite nicht bei jedem Tastendruck neu lädt
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            kategorie = st.selectbox("Kategorie", ["Umsatz", "Kosten", "Gewinn", "Marketing"])
        with col2:
            wert = st.number_input("Wert (€)", min_value=0, value=100, step=10)
            
        kommentar = st.text_area("Kommentar (optional)")
        
        submitted = st.form_submit_button("Speichern 💾")
        
        if submitted:
            # Hier rufen wir die Funktion aus database.py auf
            try:
                insert_messwert(kategorie, wert, kommentar)
                st.success("Daten erfolgreich in die Cloud gesendet!")
                time.sleep(1) # Kurze Pause für den Effekt
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")

# --- SEITE 2: VISUALISIERUNG ---
elif selected == "Visualisierung":
    st.subheader("Live-Analyse aus der Datenbank")
    
    # Daten laden
    raw_data = get_all_messwerte()
    
    if not raw_data:
        st.warning("Noch keine Daten in der Datenbank vorhanden.")
    else:
        # Daten in ein Pandas DataFrame umwandeln
        df = pd.DataFrame(raw_data)
        
        # Metriken anzeigen
        total_sum = df['wert'].sum()
        count = len(df)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Gesamtwert", f"{total_sum} €")
        m2.metric("Anzahl Einträge", count)
        m3.metric("Neuester Eintrag", df['created_at'].iloc[-1][:10]) # Datum abschneiden

        st.divider()

        # Coole Visualisierung mit Plotly
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("### Verteilung nach Kategorie")
            # Ein Donut-Chart sieht oft moderner aus als ein Pie-Chart
            fig_pie = px.pie(df, names='kategorie', values='wert', hole=0.4, 
                             color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c2:
            st.markdown("### Werte über Zeit")
            # Wir sortieren nach Zeit, damit der Graph stimmt
            df = df.sort_values(by="created_at")
            fig_line = px.bar(df, x='created_at', y='wert', color='kategorie',
                              title="Chronologischer Verlauf")
            st.plotly_chart(fig_line, use_container_width=True)

        # Datentabelle anzeigen (optional)
        with st.expander("Rohdaten anzeigen"):
            st.dataframe(df)
