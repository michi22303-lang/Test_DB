import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px
import pandas as pd
import time

# --- IMPORTS AUS DEINER DATEI ---
# Falls er hier meckert, liegt database.py nicht im selben Ordner
from database import insert_messwert, get_all_messwerte

# --- 1. CONFIG (MUSS GANZ OBEN STEHEN) ---
st.set_page_config(
    page_title="Cloud Dashboard",
    page_icon="🚀",
    layout="wide"
)

# --- 2. CSS STYLING (OPTIONAL FÜR DEN LOOK) ---
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
            # Achte darauf, dass diese Begriffe Sinn ergeben für deine Charts
            kategorie = st.selectbox("Kategorie", ["Umsatz", "Kosten", "Gewinn", "Marketing", "Sonstiges"])
        with col2:
            wert = st.number_input("Wert (€)", min_value=0.0, value=100.0, step=10.0)
            
        kommentar = st.text_area("Kommentar (optional)")
        
        submitted = st.form_submit_button("In Cloud speichern ☁️")
        
        if submitted:
            try:
                # Aufruf der Funktion aus database.py
                insert_messwert(kategorie, wert, kommentar)
                st.success("Erfolgreich gespeichert! Geh zum Tab 'Visualisierung' um es zu sehen.")
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")

# --- 5. SEITE: VISUALISIERUNG ---
elif selected == "Visualisierung":
    st.title("📊 Live-Analyse")
    
    # Daten aus Supabase holen
    try:
        raw_data = get_all_messwerte()
    except Exception as e:
        st.error(f"Verbindungsfehler zur Datenbank: {e}")
        raw_data = []

    if not raw_data:
        st.info("Die Datenbank ist noch leer. Geh zum Tab 'Eingabe' und speichere etwas!")
    else:
        # DataFrame erstellen
        df = pd.DataFrame(raw_data)

        # --- WICHTIGER FIX: SPALTEN BEREINIGEN ---
        # Wir machen alle Spaltennamen klein, damit 'Kategorie' zu 'kategorie' wird.
        df.columns = df.columns.str.lower()
        
        # --- DEBUG-HELFER (Kannst du später entfernen) ---
        with st.expander("Technik-Check: Geladene Rohdaten ansehen"):
            st.write("Gefundene Spaltennamen:", df.columns.tolist())
            st.dataframe(df)

        # --- PRÜFUNG: Haben wir die nötigen Spalten? ---
        if 'wert' not in df.columns or 'kategorie' not in df.columns:
            st.error(f"Achtung: Die Spalten 'wert' oder 'kategorie' fehlen in den Daten. Gefunden wurde: {df.columns.tolist()}")
        else:
            # METRIKEN
            total = df['wert'].sum()
            anzahl = len(df)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Gesamtsumme", f"{total:,.2f} €")
            m2.metric("Anzahl Datensätze", anzahl)
            if 'created_at' in df.columns:
                # Letztes Datum formatieren (die ersten 10 Zeichen YYYY-MM-DD)
                last_date = str(df['created_at'].iloc[-1])[:10]
                m3.metric("Letztes Update", last_date)

            st.markdown("---")

            # CHARTS
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("Verteilung")
                fig_pie = px.pie(df, names='kategorie', values='wert', hole=0.4,
                                 color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with c2:
                st.subheader("Werte-Vergleich")
                # Falls created_at existiert, nutzen wir es als X-Achse, sonst einfach den Index
                x_axis = 'created_at' if 'created_at' in df.columns else df.index
                
                fig_bar = px.bar(df, x=x_axis, y='wert', color='kategorie',
                                 title="Balkendiagramm")
                st.plotly_chart(fig_bar, use_container_width=True)
st.divider()

        # --- DER NEUE LÖSCH-BEREICH ---
        with st.expander("🗑️ Datensätze verwalten / löschen"):
            st.warning("Achtung: Gelöschte Daten können nicht wiederhergestellt werden.")
            
            # Wir erstellen eine Liste für die Auswahlbox, die ID und Infos kombiniert
            # Beispiel-Format: "ID 12 | Umsatz | 100€"
            options = [f"ID {row['id']} | {row['kategorie']} | {row['wert']}€ | {row.get('kommentar', '')}" for row in raw_data]
            
            if options:
                selected_option = st.selectbox("Wähle einen Eintrag zum Löschen:", options)
                
                # Wir müssen die ID aus dem String wieder herausfischen (die Zahl nach "ID ")
                # Wir splitten den String beim ersten Leerzeichen und nehmen das zweite Element
                selected_id = selected_option.split(" |")[0].replace("ID ", "")
                
                if st.button("Eintrag endgültig löschen 🚨"):
                    from database import delete_messwert # Import hier oder ganz oben
                    try:
                        delete_messwert(selected_id)
                        st.success(f"Eintrag {selected_id} wurde gelöscht!")
                        time.sleep(1)
                        st.rerun() # Lädt die App neu, damit der Eintrag sofort verschwindet
                    except Exception as e:
                        st.error(f"Fehler beim Löschen: {e}")
            else:
                st.write("Keine Daten zum Löschen vorhanden.")
