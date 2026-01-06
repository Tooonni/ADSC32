https://daten.berlin.de/datensaetze/baumbestand-berlin-wfs-48ad3a23
Datenstand = 24.02.2025

https://gdi.berlin.de/services/wfs/baumbestand?request=GetCapabilities&service=WFS
-->
    <Abstract>Anlagenbäumen mit Angaben zur Baumart, Adresse, Pflanzjahr, Höhe, etc. sowie Anlagenbäume ohne Sachdaten.</Abstract>
    <DefaultCRS>urn:ogc:def:crs:EPSG::25833</DefaultCRS>

1. Das Konzept

Agent (TreeAgent): Jeder Baum aus deinem Datensatz wird ein Agent. Er hat Attribute wie Alter, Art und eine "Gesundheit" (Vigor).

Modell (BerlinUrbanForest): Das Modell verwaltet den Raum, die Zeit (Steps = Jahre) und externe Faktoren wie Niederschlag.

Entscheidungslogik: Wenn ein Baum ein kritisches Alter erreicht oder die Umweltbedingungen (Hitze/Trockenheit) zu schlecht sind, stirbt der Agent und markiert die Stelle für eine Neupflanzung.

Das ist eine hervorragende Entscheidung. Friedrichshain-Kreuzberg (FK) ist das perfekte "Labor" für diese Simulation:

Hohe Versiegelung: Viel Asphalt, wenig Grünflächen – hier ist der Hitzestress am größten.

Hoher Parkdruck: Jeder Quadratmeter ist umkämpft, was die Frage "Wo pflanzen?" politisch und räumlich spannend macht.

Datenmenge: ~41.000 Agenten sind rechentechnisch genau an der Grenze dessen, was noch flüssig läuft (in Python/Mesa), aber groß genug, um komplexe Muster zu zeigen.

Stress Baum = (Basisbedarf×Größenfaktor×Artenfaktor)−Niederschlag

Hier ist der komplette Code für die model.py.

Ich habe ihn so strukturiert, dass er robust, aber verständlich ist. Er enthält:

Den TreeAgent: Mit der Logik für Stress, Alterung und dem "Arten-Faktor" (Linde leidet mehr als Robinie).

Das BerlinCityModel: Lädt deine Daten, erstellt die Umwelt und managt den Ablauf (Ticks).

Die "Gärtner-Logik": Ein einfacher Mechanismus, der tote Bäume erkennt und (optional) neu bepflanzt.