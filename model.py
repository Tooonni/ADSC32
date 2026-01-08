import mesa
import pandas as pd
import numpy as np
from pyproj import Transformer 

# --- HILFSFUNKTIONEN ---
def get_species_counts(model):
    """
    Zählt für das Bar-Chart in der App:
    Wie viele Bäume pro Art sind lebend, tot oder neu gepflanzt?
    """
    counts = {}
    for agent in model.schedule.agents:
        # Art-Name vereinfachen (nur erstes Wort, z.B. "Linde")
        species_simple = str(agent.art).split(' ')[0]
        
        # Status bestimmen
        state = "Lebend"
        if agent.status == "dead":
            state = "Tot"
        elif agent.is_new_planting:
            state = "Neu"
            species_simple = "Neu (Zürgelbaum)" 
        
        # Key bauen: "Linde_Lebend", "Eiche_Tot" etc.
        key = f"{species_simple}_{state}"
        counts[key] = counts.get(key, 0) + 1
    return counts

# --- SCHEDULER ---
class SimpleScheduler:
    def __init__(self, model):
        self.model = model
        self.agents = []

    def add(self, agent):
        self.agents.append(agent)

    def step(self):
        np.random.shuffle(self.agents)
        for agent in self.agents:
            agent.step()

# --- AGENT ---
class TreeAgent(mesa.Agent):
    def __init__(self, unique_id, model, lat_lon, art, alter, krone):
        super().__init__(model)
        self.unique_id = unique_id
        
        self.pos = None 
        self.folium_pos = lat_lon  
        
        self.art = art
        self.alter = float(alter) if pd.notna(alter) else 15.0
        self.krone = float(krone) if pd.notna(krone) else 4.0
        
        # Start-Gesundheit (90-100)
        self.health = np.random.randint(90, 101)
        self.status = "alive"
        self.is_new_planting = False
        
        # Resilienz-Faktoren
        self.resilience_map = {
            "Linde": 1.3,      
            "Kastanie": 1.2,   
            "Ahorn": 1.1,
            "Eiche": 1.0,
            "Platane": 0.9,
            "Robinie": 0.7,
            "Gleditschie": 0.6,
            "Zürgelbaum": 0.5,
            "Ailanthus": 0.6
        }
        
        self.water_demand_factor = 1.1
        for key, factor in self.resilience_map.items():
            if key in str(self.art):
                self.water_demand_factor = factor
                break

    def step(self):
        if self.status == "dead": return 

        precip = self.model.current_precipitation
        temp = self.model.current_temp 

        # --- 1. WASSERANGEBOT ---
        # 70% des Regens sind nutzbar
        effective_water = precip * 0.7 
        
        # --- 2. TEMPERATUR-EFFEKT ---
        # Stress beginnt ab 11°C Jahresmittel
        threshold = 11.0
        if temp > threshold:
            temp_factor = 1.0 + (temp - threshold) * 0.10
        else:
            temp_factor = 1.0 
            
        # --- 3. WASSERBEDARF ---
        base_need = 250 
        size_need = self.krone * 20 
        
        total_demand = (base_need + size_need) * self.water_demand_factor * temp_factor
        
        # --- 4. BILANZ & ALTERSEFFEKT ---
        water_balance = effective_water - total_demand
        
        if water_balance < 0:
            # Basis-Schaden
            damage = abs(water_balance) / 20.0
            
            # Alterseffekte einrechnen
            if self.alter < 10:
                # Jungbäume: Wurzeln kurz -> 50% mehr Schaden
                damage *= 1.5
            elif self.alter > 80:
                # Altbäume: Vitalität gering -> 30% mehr Schaden
                damage *= 1.3
            
            self.health -= damage
        else:
            # Erholung
            recovery = 5 
            if temp > 13.0: recovery = 2 
            
            # Junge Bäume erholen sich schneller (Wachstum)
            if self.alter < 20:
                recovery += 2

            self.health += recovery
            if self.health > 100:
                self.health = 100
            
        self.alter += 1 
        
        if self.health <= 0:
            self.status = "dead"
            self.model.dead_trees_count += 1
        elif self.health < 40:
            self.status = "critical"
        elif self.health < 70:
            self.status = "stressed"
        else:
            self.status = "alive"

# --- MODELL ---
class BerlinCityModel(mesa.Model):
    def __init__(self, data_path):
        super().__init__()
        self.schedule = SimpleScheduler(self)
        
        # Startwerte
        self.current_precipitation = 570 
        self.current_temp = 10.5 
        
        self.year = 2025
        self.dead_trees_count = 0
        self.total_planted = 0
        
        print("Lade Daten...")
        try:
            df = pd.read_parquet(data_path)
        except Exception as e:
            print(f"FEHLER: {e}")
            return

        df = df[df['bezirk'] == 'Friedrichshain-Kreuzberg']
        print(f"Gefunden: {len(df)} Bäume in FK.")
        
        transformer = Transformer.from_crs("epsg:25833", "epsg:4326", always_xy=True)
        self.space = mesa.space.ContinuousSpace(x_max=14.0, y_max=53.0, torus=False, x_min=13.0, y_min=52.0)

        count = 0
        for i, row in df.iterrows():
            try:
                lat_raw = row['latitude']; lon_raw = row['longitude']
                if pd.isna(lat_raw) or pd.isna(lon_raw): continue

                if lat_raw > 360 or lon_raw > 360:
                    lon_gps, lat_gps = transformer.transform(lon_raw, lat_raw)
                else:
                    lat_gps, lon_gps = lat_raw, lon_raw

                agent = TreeAgent(
                    unique_id=i, model=self, lat_lon=(lat_gps, lon_gps), 
                    art=row['art_dtsch'], alter=row['standalter'], krone=row['kronedurch']
                )
                self.schedule.add(agent); self.space.place_agent(agent, (lon_gps, lat_gps)) 
                count += 1
            except: continue
        
        print(f"Erfolgreich initialisiert: {count} Bäume.")

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Alive Trees": lambda m: sum([1 for a in m.schedule.agents if a.status != "dead"]),
                "Avg Temp (Jahr)": "current_temp",
                "Precipitation": "current_precipitation",
                "Total Planted": "total_planted",
                "Species_Data": get_species_counts
            }
        )
        self.datacollector.collect(self)

    def step(self):
        self.schedule.step()
        self.manage_forest()
        self.datacollector.collect(self)
        self.year += 1
        print(f"Jahr {self.year}: {self.current_temp}°C / {self.current_precipitation}mm")

    def manage_forest(self):
        # Gärtner pflanzt nach (10% Chance bei toten Bäumen)
        for agent in self.schedule.agents:
            if agent.status == "dead" and np.random.random() < 0.1:
                agent.status = "alive"
                agent.health = 100
                agent.alter = 1 # Neuer Baum ist 1 Jahr alt -> also JUNG und empfindlich!
                agent.krone = 1.0 # Kleine Krone
                agent.art = "Zürgelbaum (Neu)"
                agent.water_demand_factor = 0.5 
                agent.is_new_planting = True
                self.total_planted += 1