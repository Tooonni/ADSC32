import mesa
import pandas as pd
import numpy as np
from pyproj import Transformer 

# --- Scheduler ---
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

# --- Agent ---
class TreeAgent(mesa.Agent):
    def __init__(self, unique_id, model, lat_lon, art, alter, krone):
        super().__init__(model)
        self.unique_id = unique_id
        
        # Positionen
        self.pos = None 
        self.folium_pos = lat_lon  
        
        # Eigenschaften
        self.art = art
        self.alter = float(alter) if pd.notna(alter) else 15.0
        self.krone = float(krone) if pd.notna(krone) else 4.0
        
        # Start-Gesundheit: Alte Bäume sind oft schon vorbelastet
        # Wir geben etwas Varianz rein (80-100)
        self.health = np.random.randint(80, 101)
        self.status = "alive"
        self.is_new_planting = False
        
        # --- 1. RESILIENZ-FAKTOREN (Verschärft) ---
        # Faktor 1.0 = Durchschnitt
        # Faktor > 1.0 = Braucht VIEL Wasser (Stirbt schnell)
        # Faktor < 1.0 = Braucht WENIG Wasser (Überlebt Dürre)
        self.resilience_map = {
            "Linde": 1.4,      # Sehr empfindlich (typisch Berlin)
            "Kastanie": 1.3,   # Empfindlich
            "Ahorn": 1.1,      # Durchschnitt
            "Eiche": 1.0,      # Robust
            "Platane": 0.9,    # Sehr Robust
            "Robinie": 0.7,    # Trockenkünstler
            "Gleditschie": 0.6,# Zukunftsbaum
            "Zürgelbaum": 0.5, # Zukunftsbaum
            "Ailanthus": 0.6   # Götterbaum (sehr robust)
        }
        
        # Standardwert 1.1 (leicht empfindlich), falls Art unbekannt
        self.water_demand_factor = 1.1
        for key, factor in self.resilience_map.items():
            if key in str(self.art):
                self.water_demand_factor = factor
                break

    def step(self):
        if self.status == "dead": return 

        # --- 2. DIE NEUE STRESS-MATHE ---
        
        # A. Das Wasserangebot (Der "Stadt-Effekt")
        # In der Stadt landen von 600mm Regen nur ca. 50% im Boden (Versiegelung!)
        # Wir simulieren: Je weniger Regen, desto schlimmer die Verdunstung.
        precip_total = self.model.current_precipitation
        effective_water = precip_total * 0.5  # Nur 50% erreichen die Wurzel
        
        # B. Der Wasserbedarf (Realistischer skaliert)
        # Ein Baum braucht eine Basis-Menge (z.B. 300mm äquivalent) PLUS Größe
        # Formel: (Basis + (Größe * Faktor)) * Art-Faktor
        base_need = 300 
        size_need = self.krone * 40 # Pro Meter Krone viel mehr Bedarf
        
        total_demand = (base_need + size_need) * self.water_demand_factor
        
        # C. Die Bilanz
        water_balance = effective_water - total_demand
        
        # --- 3. GESUNDHEITS-UPDATE ---
        
        if water_balance < 0:
            # Dürrestress!
            # Je größer das Defizit, desto härter der Schaden.
            # Wir teilen durch einen Dämpfer, damit sie nicht sofort tot umfallen (z.B. 10)
            damage = abs(water_balance) / 8.0 
            
            # Alterseffekt: Bäume über 80 Jahre regenerieren schlechter / leiden mehr
            if self.alter > 80:
                damage *= 1.2
            
            self.health -= damage
        else:
            # Erholung (Langsam!)
            # Bäume erholen sich langsamer als sie krank werden.
            recovery = 3 
            # Robuste Arten erholen sich schneller
            if self.water_demand_factor < 0.9:
                recovery = 5
                
            self.health += recovery
            if self.health > 100: self.health = 100
            
        # --- 4. ALTERUNG & TOD ---
        self.alter += 1 
        
        # Status setzen
        if self.health <= 0:
            self.status = "dead"
            self.model.dead_trees_count += 1
        elif self.health < 40:
            self.status = "critical" # Orange
        elif self.health < 70:
            self.status = "stressed" # Gelb
        else:
            self.status = "alive"    # Grün

# --- Model ---
class BerlinCityModel(mesa.Model):
    def __init__(self, data_path, initial_precip=600, precip_decline=5):
        super().__init__()
        self.schedule = SimpleScheduler(self)
        self.current_precipitation = initial_precip
        self.precip_decline = precip_decline 
        self.year = 2025
        self.dead_trees_count = 0
        
        print("Lade Daten...")
        try:
            df = pd.read_parquet(data_path)
        except Exception as e:
            print(f"FEHLER: {e}")
            return

        df = df[df['bezirk'] == 'Friedrichshain-Kreuzberg']
        print(f"Gefunden: {len(df)} Bäume in FK.")
        
        # Koordinaten-Umrechner (UTM -> GPS)
        transformer = Transformer.from_crs("epsg:25833", "epsg:4326", always_xy=True)

        self.space = mesa.space.ContinuousSpace(x_max=14.0, y_max=53.0, torus=False, x_min=13.0, y_min=52.0)

        count = 0
        for i, row in df.iterrows():
            try:
                lat_raw = row['latitude']
                lon_raw = row['longitude']
                
                if pd.isna(lat_raw) or pd.isna(lon_raw): continue

                # Umrechnung falls nötig
                if lat_raw > 360 or lon_raw > 360:
                    lon_gps, lat_gps = transformer.transform(lon_raw, lat_raw)
                else:
                    lat_gps, lon_gps = lat_raw, lon_raw

                # Agent erstellen: Wir übergeben (Lat, Lon) als 'lat_lon' Argument
                agent = TreeAgent(
                    unique_id=i, 
                    model=self, 
                    lat_lon=(lat_gps, lon_gps), # Das geht in self.folium_pos
                    art=row['art_dtsch'], 
                    alter=row['standalter'], 
                    krone=row['kronedurch']
                )
                
                self.schedule.add(agent)
                # Für Mesa nutzen wir (Lon, Lat) als (x, y) - das erzeugt keine Warnung mehr
                self.space.place_agent(agent, (lon_gps, lat_gps)) 
                count += 1
                
            except Exception as e:
                continue
        
        print(f"Erfolgreich initialisiert: {count} Bäume.")

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Alive Trees": lambda m: sum([1 for a in m.schedule.agents if a.status != "dead"]),
                "Precipitation": "current_precipitation"
            }
        )
        self.datacollector.collect(self)

    def step(self):
        self.current_precipitation -= self.precip_decline
        if self.current_precipitation < 0: self.current_precipitation = 0
        self.schedule.step()
        self.manage_forest()
        self.datacollector.collect(self)
        self.year += 1
        print(f"Jahr {self.year} berechnet.")

    def manage_forest(self):
        for agent in self.schedule.agents:
            if agent.status == "dead" and np.random.random() < 0.1:
                agent.status = "alive"
                agent.health = 100
                agent.art = "Zürgelbaum (Neu)"
                agent.water_demand_factor = 0.5 
                agent.is_new_planting = True