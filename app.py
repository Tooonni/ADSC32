import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import random 
from model import BerlinCityModel

# --- 1. Konfiguration der Seite ---
st.set_page_config(
    page_title="Berlin Tree Simulation",
    page_icon="🌳",
    layout="wide"
)

st.title("🌳 Simulation: Straßenbäume in Friedrichshain-Kreuzberg")

# CSS für schönere Metrik-Boxen
st.markdown("""
<style>
    div[data-testid="stMetricValue"] {
        font-size: 24px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Session State initialisieren ---
# Damit das Modell nicht gelöscht wird, wenn du einen Button klickst
if 'model' not in st.session_state:
    st.session_state.model = None
if 'simulation_started' not in st.session_state:
    st.session_state.simulation_started = False

# --- 3. Sidebar: Einstellungen ---
st.sidebar.header("⚙️ Einstellungen")

# Schieberegler für das Klima
precip_start = st.sidebar.slider("Start-Niederschlag (mm)", 300, 800, 550, help="Durchschnitt Berlin: ca. 570mm")
precip_decline = st.sidebar.slider("Trockenheit-Trend (mm/Jahr)", 0, 20, 5, help="Wie viel weniger Regen pro Jahr?")

# Start-Button
if st.sidebar.button("🌱 Simulation Starten / Reset"):
    with st.spinner('Lade Baumdaten und initialisiere Welt...'):
        data_path = 'clean_baumbestand_berlin.parquet'
        # Modell neu erstellen
        st.session_state.model = BerlinCityModel(data_path, precip_start, precip_decline)
        st.session_state.simulation_started = True
    st.sidebar.success(f"Modell geladen! {len(st.session_state.model.schedule.agents)} Bäume bereit.")

# Schritt-Button (nur sichtbar, wenn Simulation läuft)
if st.session_state.simulation_started:
    st.sidebar.markdown("---")
    if st.sidebar.button("⏩ Ein Jahr simulieren", type="primary"):
        with st.spinner(f'Simuliere Jahr {st.session_state.model.year + 1}...'):
            st.session_state.model.step()

# --- 4. Hauptbereich ---

if st.session_state.model is None:
    st.info("👈 Bitte starte die Simulation über den Button in der Sidebar.")
    st.markdown("### Über diese App")
    st.markdown("""
    Diese Simulation zeigt die Auswirkung von zunehmender Trockenheit auf den Baumbestand in Friedrichshain-Kreuzberg.
    - **Grüne Punkte:** Gesunde Bäume.
    - **Gelbe/Orangen Punkte:** Bäume unter Wasserstress.
    - **Rote Punkte:** Abgestorbene Bäume.
    - **Blaue Punkte:** Neu gepflanzte, resistente Arten (Zürgelbaum).
    """)
else:
    model = st.session_state.model

    # --- A. KPIs (Metriken) ---
    col1, col2, col3, col4 = st.columns(4)
    
    # Live-Daten aus dem Modell holen
    alive_trees = sum([1 for a in model.schedule.agents if a.status != "dead"])
    dead_trees = model.dead_trees_count
    current_year = model.year
    precip = model.current_precipitation
    
    col1.metric("Jahr", current_year)
    col2.metric("Lebende Bäume", f"{alive_trees:,}")
    col3.metric("Abgestorben", dead_trees, delta_color="inverse")
    col4.metric("Niederschlag", f"{precip} mm")

    # --- B. Karte (Folium) ---
    st.subheader("🗺️ Zustand der Bäume (Live-Karte)")
    
    # Basiskarte erstellen (Zentrum auf FK)
    m = folium.Map(location=[52.50, 13.43], zoom_start=13, tiles="CartoDB dark_matter")

    # --- SAMPLING LOGIK (WICHTIG!) ---
    all_agents = model.schedule.agents
    total_agents = len(all_agents)
    max_view = 3000 # Limit für den Browser
    
    if total_agents > max_view:
        # WICHTIG: random.seed nutzen, damit die Punkte beim Neuladen nicht "springen"
        random.seed(model.year) 
        display_agents = random.sample(all_agents, max_view)
        st.caption(f"ℹ️ Performance-Modus: Zeige eine zufällige Auswahl von **{max_view}** aus **{total_agents}** Bäumen.")
    else:
        display_agents = all_agents

    # Punkte zeichnen
    for agent in display_agents:
        # Standard: Grün
        color = '#2ecc71' 
        radius = 2
        fill_opacity = 0.6
        
        # Status-Farben
        if agent.status == 'dead':
            color = '#e74c3c' # Rot
            radius = 3
            fill_opacity = 0.8
        elif agent.status == 'critical':
            color = '#e67e22' # Orange
        elif agent.status == 'stressed':
            color = '#f1c40f' # Gelb
        
        # Neupflanzungen überschreiben alles
        if agent.is_new_planting:
            color = '#3498db' # Blau
            radius = 3.5
            fill_opacity = 0.9
            
        # Sicherheits-Check: Hat der Agent Koordinaten?
        if agent.folium_pos is None:
            continue

        folium.CircleMarker(
            # HIER ÄNDERN: agent.folium_pos nutzen!
            location=[agent.folium_pos[0], agent.folium_pos[1]], 
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=fill_opacity,
            popup=None 
        ).add_to(m)

    st_folium(m, width="100%", height=500, returned_objects=[])

    # --- C. Statistiken (Graphen) ---
    st.subheader("📊 Langzeit-Analyse")
    
    # Datenverlauf holen
    stats_df = model.datacollector.get_model_vars_dataframe()
    
    if not stats_df.empty:
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown("**Anzahl lebender Bäume**")
            st.line_chart(stats_df["Alive Trees"], color="#2ecc71")
            
        with chart_col2:
            st.markdown("**Niederschlag (Klimawandel)**")
            st.line_chart(stats_df["Precipitation"], color="#3498db")