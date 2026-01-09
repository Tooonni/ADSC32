import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import random 
from model import BerlinCityModel

# --- 1. Config ---
st.set_page_config(page_title="Berlin Tree Simulation", page_icon="🌳", layout="wide")
st.title("🌳 Labor: Bäume in Friedrichshain-Kreuzberg")

st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 24px; }
</style>
""", unsafe_allow_html=True)

# --- 2. State ---
if 'model' not in st.session_state:
    st.session_state.model = None
if 'simulation_started' not in st.session_state:
    st.session_state.simulation_started = False

# --- 3. Sidebar: Initialisierung ---
st.sidebar.header("1. Setup")

if st.sidebar.button("🌱 Simulation Starten / Reset"):
    with st.spinner('Lade Baumdaten...'):
        data_path = 'data/clean_baumbestand_berlin.parquet'
        st.session_state.model = BerlinCityModel(data_path)
        st.session_state.simulation_started = True
    st.sidebar.success("Modell geladen!")

# --- 4. Sidebar: Steuerung ---
if st.session_state.simulation_started:
    st.sidebar.markdown("---")
    st.sidebar.header(f"2. Wetter für Jahr {st.session_state.model.year + 1}")
    
    # --- REGLER ---    
    next_precip = st.sidebar.slider(
        "Ø Jahres-Niederschlag (mm)", 
        min_value=200, max_value=800, value=570, step=10,
        help="Berlin Normal: ca. 570mm. Dürre: < 450mm."
    )
    
    next_temp = st.sidebar.slider(
        "Ø Jahres-Temperatur (°C)", 
        min_value=8.0, max_value=16.0, value=10.5, step=0.1,
        help="Berlin Normal: ~10°C. Klimawandel-Szenario: > 12°C. (Achtung: 1°C Unterschied im Jahresmittel ist enorm!)"
    )
    
    # Simulations-Button
    if st.sidebar.button("⏩ Dieses Jahr simulieren", type="primary"):
        model = st.session_state.model
        
        # Werte übertragen
        model.current_precipitation = next_precip
        model.current_temp = next_temp
        
        with st.spinner(f'Simuliere Jahr {model.year + 1}...'):
            model.step()

# --- 5. Hauptbereich ---
if st.session_state.model is None:
    st.info("👈 Bitte starte das Labor in der Sidebar.")
else:
    model = st.session_state.model

    # --- KPIs ---
    col1, col2, col3, col4, col5 = st.columns(5)
    
    alive_trees = sum([1 for a in model.schedule.agents if a.status != "dead"])
    
    col1.metric("Jahr", model.year)
    col2.metric("Lebende Bäume", f"{alive_trees:,}")
    col3.metric("Tote Bäume", model.dead_trees_count, delta_color="inverse")
    col4.metric("Neu gepflanzt", model.total_planted, delta_color="normal")
    col5.metric("Klima (letztes Jahr)", f"{model.current_temp}°C / {model.current_precipitation}mm")

    # --- Karte ---
    st.subheader("🗺️ Zustand der Bäume")
    m = folium.Map(location=[52.50, 13.43], zoom_start=13, tiles="CartoDB Voyager") #"CartoDB dark_matter"

    all_agents = model.schedule.agents
    max_view = 3000
    
    if len(all_agents) > max_view:
        random.seed(model.year) 
        display_agents = random.sample(all_agents, max_view)
        st.caption(f"Zeige {max_view} zufällige Bäume.")
    else:
        display_agents = all_agents

    for agent in display_agents:
        if agent.folium_pos is None: continue

        color = '#2ecc71' 
        radius = 2; fill_opacity = 0.6
        
        if agent.status == 'dead':
            color = '#e74c3c'; radius = 3; fill_opacity = 0.8
        elif agent.status == 'critical':
            color = '#e67e22' 
        elif agent.status == 'stressed':
            color = '#f1c40f' 
        
        if agent.is_new_planting:
            color = '#3498db'; radius = 3.5; fill_opacity = 0.9
            
        folium.CircleMarker(
            location=agent.folium_pos, radius=radius, color=color, 
            fill=True, fill_color=color, fill_opacity=fill_opacity, popup=None 
        ).add_to(m)

    # --- Legende für die Karte ---
    st.markdown("""
    <div style="background-color: #1e1e1e; padding: 10px; border-radius: 5px; border: 1px solid #333; margin-bottom: 10px;">
        <span> Legende:</span>
        <span style="color: #2ecc71; margin-right: 15px;">● <b>Vital:</b> Gesund (Health > 70)</span>
        <span style="color: #f1c40f; margin-right: 15px;">● <b>Gestresst:</b> Trockenstress (40-70)</span>
        <span style="color: #e67e22; margin-right: 15px;">● <b>Kritisch:</b> Stark geschädigt (< 40)</span>
        <span style="color: #e74c3c; margin-right: 15px;">● <b>Tot:</b> Abgestorben (0)</span>
        <span style="color: #3498db;">● <b>Neu:</b> Nachgepflanzt (Zürgelbaum)</span>
    </div>
    """, unsafe_allow_html=True)

    st_folium(m, width="100%", height=500, returned_objects=[])

# --- Charts ---
    st.subheader("📊 Analyse & Verlauf")
    
    # Daten holen
    stats_df = model.datacollector.get_model_vars_dataframe()
    
    if not stats_df.empty:
        # --- ZEILE 1: Temperatur & Niederschlag ---
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("##### 🌡️ Temperatur-Verlauf (°C)")
            st.line_chart(stats_df["Avg Temp (Jahr)"], color="#e74c3c") # Rot
            
        with c2:
            st.markdown("##### 🌧️ Niederschlag-Verlauf (mm)")
            st.line_chart(stats_df["Precipitation"], color="#3498db") # Blau

        st.markdown("---")

        st.markdown("##### 💀 Verlauf der Baumsterblichkeit (Kumuliert)")

        # Wir nutzen die neue Variable aus dem DataCollector
        if "Dead Trees Total" in stats_df.columns:
            st.line_chart(stats_df["Dead Trees Total"], color="#e74c3c")
        else:
        # Fallback, falls der DataCollector noch nicht angepasst wurde
            st.warning("Bitte ergänze 'Dead Trees Total' im DataCollector der model.py, um diesen Graph zu sehen.")

        st.markdown("---")

# --- ZEILE 2: Baumarten Analyse (Top 5) ---
        st.markdown("##### 🌳 Top 5 Baumarten (Status aktuell)")
        
        latest_species_data = stats_df["Species_Data"].iloc[-1]
        
        if latest_species_data:
            data_for_chart = {}
            
            # Alle Arten sammeln
            all_species = set([k.split('_')[0] for k in latest_species_data.keys()])
            
            for spec in all_species:
                # 1. Lebend und Tot zählen
                count_lebend = latest_species_data.get(f"{spec}_Lebend", 0)
                count_tot = latest_species_data.get(f"{spec}_Tot", 0)
                
                # 2. Neue Bäume zählen
                count_neu = 0
                if spec == "Neu (Zürgelbaum)":
                    count_neu = latest_species_data.get(f"Neu (Zürgelbaum)_Neu", 0)
                
                data_for_chart[spec] = {
                    "Lebend": count_lebend,
                    "Neu": count_neu,
                    "Tot": count_tot
                }
            
            # DataFrame erstellen
            chart_df = pd.DataFrame.from_dict(data_for_chart, orient='index')
            
            # NaN durch 0 ersetzen (wichtig für die Summe)
            chart_df = chart_df.fillna(0)
            
            # Top 5 berechnen (Inklusive der neuen Bäume)
            chart_df['Total'] = chart_df.sum(axis=1)
            chart_df = chart_df.sort_values('Total', ascending=False).head(5)
            chart_df = chart_df.drop(columns=['Total'])
            
            # Spalten sortieren für die Farben
            # Wenn "Neu" im DF fehlt (weil noch nichts gepflanzt), fügen wir es hinzu, damit Farben stimmen
            if "Neu" not in chart_df.columns:
                chart_df["Neu"] = 0
            
            chart_df = chart_df[["Lebend", "Neu", "Tot"]]
            
            # Zeichnen
            st.bar_chart(
                chart_df, 
                color=["#2ecc71", "#3498db", "#e74c3c"], # Grün, Blau, Rot
                stack=True
            )
            
        else:
            st.info("Noch keine Daten.")