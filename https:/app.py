import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px
import pandas as pd
import time

# --- WICHTIG: Hier habe ich 'delete_messwert' hinzugefügt ---
from database import insert_messwert, get_all_messwerte, delete_messwert

# --- 1. CONFIG ---
st.set_page_config(
    page_title="Cloud Dashboard",
    page_icon="🚀",
    layout="wide"
)

# --- 2. CSS STYLING ---
st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 0rem;}
        h1 {color: #2e86c1;}
    </style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR NAVIGATION ---
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
    
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            kategorie = st.selectbox("Kategorie", ["Umsatz", "Kosten", "Gewinn", "Marketing", "Sonstiges"])
        with col2:
            # Wir nutzen Integer (Ganzzahlen), um Datenbank-Fehler zu vermeiden
            wert = st.number_input("Wert (€)", min_value=0, value=100, step=10)
            
        kommentar = st.text_area("Kommentar (optional)")
        
        submitted = st.form_submit_button("In Cloud speichern ☁️")
        
        if submitted:
            try:
                insert_messwert(kategorie, wert, kommentar)
                st.success("Erfolgreich gespeichert! Geh zum Tab 'Visualisierung' um es zu sehen.")
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")

# --- 5. SEITE: VISUALISIERUNG ---
elif selected == "Visualisierung":
    st.title("📊 Live-Analyse")
    
    # Daten laden
    try:
        raw_data = get_all_messwerte()
    except Exception as e:
        st.error(f"Verbindungsfehler zur Datenbank: {e}")
        raw_data = []

    if not raw_data:
        st.info("Die Datenbank ist noch leer.")
    else:
        # DataFrame erstellen und Spalten bereinigen
        df = pd.DataFrame(raw_data)
        df.columns = df.columns.str.lower()
        
        # Metriken berechnen
        if 'wert' in df.columns:
            total = df['wert'].sum()
            anzahl = len(df)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Gesamtsumme", f"{total:,.2f} €")
            m2.metric("Anzahl Datensätze", anzahl)
            if 'created_at' in df.columns:
                last_date = str(df['created_at'].iloc[-1])[:10]
                m3.metric("Letztes Update", last_date)

            st.markdown("---")

            # Charts anzeigen
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("Verteilung")
                if 'kategorie' in df.columns:
                    fig_pie = px.pie(df, names='kategorie', values='wert', hole=0.4,
                                     color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig_pie, use_container_width=True)
            
            with c2:
                st.subheader("Werte-Vergleich")
                if 'created_at' in df.columns:
                    fig_bar = px.bar(df, x='created_at', y='wert', color='kategorie',
                                     title="Balkendiagramm")
                    st.plotly_chart(fig_bar, use_container_width=True)

        # ---------------------------------------------
        # HIER BEGINNT DER NEUE LÖSCH-BEREICH
        # ---------------------------------------------
        st.divider()
        
        with st.expander("🗑️ Datensätze verwalten / löschen"):
            st.warning("Achtung: Gelöschte Daten sind unwiderruflich weg.")
            
            # Wir bauen eine Liste für die Auswahlbox
            # Wir prüfen sicherheitshalber, ob 'id' vorhanden ist
            if 'id' in df.columns:
                # List Comprehension um schöne Labels zu bauen
                options = [f"ID {row['id']} | {row['kategorie']} | {row['wert']}€" for index, row in df.iterrows()]
                
                selected_option = st.selectbox("Wähle einen Eintrag:", options)
                
                if st.button("Eintrag löschen 🚨"):
                    # ID extrahieren (alles nach "ID " und vor dem ersten " |")
                    id_to_delete = selected_option.split(" |")[0].replace("ID ", "")
                    
                    try:
                        delete_messwert(id_to_delete)
                        st.success(f"Eintrag ID {id_to_delete} wurde gelöscht!")
                        time.sleep(1)
                        st.rerun() # Seite neu laden
                    except Exception as e:
                        st.error(f"Fehler beim Löschen: {e}")
            else:
                st.error("Fehler: Keine ID-Spalte in den Daten gefunden.")
