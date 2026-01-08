 # 🌳 Berlin Tree Lab: Simulation Friedrichshain-Kreuzberg

**Eine agentenbasierte Simulation (ABM) zur Analyse von Hitzestress und Waldwandel im urbanen Raum.**

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Framework](https://img.shields.io/badge/Mesa-Agent_Based_Modeling-green)
![Frontend](https://img.shields.io/badge/Streamlit-Dashboard-red)

Dieses Projekt simuliert die Auswirkungen des Klimawandels auf den realen Straßenbaumbestand des Berliner Bezirks **Friedrichshain-Kreuzberg**. Es nutzt echte Geodaten, um zu visualisieren, wie unterschiedliche Baumarten auf Temperaturanstieg und Dürre reagieren und wie Anpassungsstrategien (z.B. die Pflanzung resistenter Arten wie des Zürgelbaums) den urbanen Wald verändern.

<br>

## 📋 Projektübersicht

Friedrichshain-Kreuzberg dient als "Reallabor" für diese Simulation. Der Bezirk ist geprägt durch hohe Versiegelung, starken Parkdruck und ausgeprägte Hitzeinsel-Effekte (*Urban Heat Island*).

**Die Simulation:**
* Modelliert **~41.000 echte Bäume** als individuelle Agenten.
* Simuliert physiologischen Stress durch Hitze & Wassermangel.
* Zeigt den langfristigen Wandel der Artenzusammensetzung (von der Linde hin zu klima-resilienten Arten).

<br>

## 💾 Datengrundlage

Die Simulation basiert auf offiziellen Open Data des Landes Berlin:

* **Quelle:** [Geoportal Berlin / FIS Broker](https://daten.berlin.de/datensaetze/baumbestand-berlin-wfs-48ad3a23)
* **Dienst:** WFS Baumbestand Berlin
* **Datenstand:** 24.02.2025
* **Koordinatensystem:** Transformiert von EPSG:25833 (ETRS89 / UTM Zone 33N) auf WGS84 (Lat/Lon) für die Visualisierung.
* **Genutzte Attribute:** Baumart (`art_dtsch`), Pflanzjahr (`standalter`), Kronendurchmesser (`kronedurch`), Geometrie.

<br>

## ⚙️ Funktionsweise & Logik

Das Modell basiert auf dem **Mesa** Framework für Agentenbasierte Modellierung (ABM).

### 1. Die Agenten (`TreeAgent`)
Jeder Baum ist ein Agent mit individueller Resilienz:
* **Sensible Arten:** z.B. *Linde* (Faktor 1.3), *Kastanie*. Sie leiden bei Trockenheit überproportional.
* **Resiliente Arten:** z.B. *Robinie*, *Gleditschie*, *Zürgelbaum* (Faktor 0.5 - 0.7).
* **Alters-Effekt:** Jungbäume (<10 Jahre) und Altbäume (>80 Jahre) sind anfälliger für Stressschäden als mittelalte Bäume.

### 2. Die Stress-Physik
Pro Jahr (Step) wird der Gesundheitszustand (`Health 0-100`) berechnet:

```python
# 1. Wasserangebot (Versiegelungseffekt)
Verfügbares_Wasser = Jahresniederschlag * 0.7 

# 2. Wasserbedarf (Exponentieller Anstieg bei Hitze)
Hitze_Faktor = 1.0 + (Jahrestemperatur - 11°C) * 0.10
Bedarf = (Basisbedarf + (Kronengröße * 20)) * ArtFaktor * Hitze_Faktor


# 3. Bilanz
Stress = Verfügbares_Wasser - Bedarf
#Ist die Bilanz negativ, verliert der Baum Gesundheit.
#Erholt er sich nicht über mehrere Jahre, stirbt er (Health <= 0).
```

### 3. Der Gärtner (Adaption)

- Ein integrierter Management-Algorithmus erkennt tote Bäume.
- Aktion: Mit 10% Wahrscheinlichkeit pro Jahr wird nachgepflanzt.
- Strategie: Es wird automatisch ein Zürgelbaum (Klimawandel-Gewinner) gepflanzt, um die Anpassung des Bestandes zu simulieren

<br>

## 📂 Ordnerstruktur
Das Projekt trennt sauber zwischen Daten, Logik (Backend) und Visualisierung (Frontend).

```bash
ADSC32/
├── data/
│   ├── baumbestand_berlin.parquet          # Der initiale Datensatz aus der API
│   └── clean_baumbestand_berlin.parquet    # Der bereinigte Datensatz (FK)
├── docs/
│    └── Datenformatbeschreibung_Baeume.pdf # Offizile Beschreibung des Datensatzes
├── notebooks/
│   ├── 01_GetData.ipynb                    # Notebook wie die Daten gezogen wurden
│   └── 02_CleanData.ipynb                  # Notebook wie die Datenverarbeiten wurden
├── .python-version                         
├── app.py                                  # Frontend (Streamlit Dashboard & Folium Map)
├── model.py                                # Backend (Mesa Simulation, Agenten & Physik)
├── pyproject.toml                          # Genutze Python Pakete
├── uv.lock                                 # Python-Abhängigkeiten
└── README.md                               # Projektdokumentation
```

<br>

## 🚀 Installation & Nutzung
### **Voraussetzungen**
- Python 3.13+
- Empfohlen: uv für Pakte und virtuelle Umgebung

### 1. Installation

- Klone das Repo
```bash
git clone <dein-repo-link>
cd ADSC32
curl -LsSf https://astral.sh/uv/install.sh | sh # UV installieren 
uv venv                                         # virutelle Umgebung erstellen
uv sync                                         # alle Paket-Abhängigkeiten installieren
```

### 2. Starten der Simulation

Wechsle in den Source-Ordner und starte Streamlit:
```bash
cd ADSC32
streamlit run app.py
```

### 3. Bedienung des Labors

- Die App öffnet sich im Browser (http://localhost:8501).
- Klicke in der Sidebar auf "Simulation Starten".
- Experimentieren: Stelle für jedes Jahr neue Bedingungen ein:
- Niederschlag: Trockenheit (<450mm) vs. Normal (570mm).
- Temperatur: Berlin Normal (10.5°C) vs. Klimawandel (>12°C).
- Analysieren: Beobachte im Bar-Chart, wie Linden absterben und Zürgelbäume den Bestand übernehmen.

<br>

## 🛠 Tech Stack
Backend: Python, Mesa (ABM Logic), Pandas (Data Handling), PyProj (Geo-Transformation).

Frontend: Streamlit (UI), Folium (Maps), Altair (Charts).

Datenformat: Parquet (High-Performance I/O).