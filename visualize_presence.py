
import json
import folium
import math
from folium.plugins import HeatMap

# Charger notre GeoJSON
with open("presence_cells.geojson", encoding="utf-8") as f:
    geojson = json.load(f)

features = geojson["features"]

# Carte centrée sur la zone maritime sénégalaise
m = folium.Map(
    location=[14.2, -17.5],
    zoom_start=6,
    tiles=None
)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Esri WorldStreetMap",
    overlay=False,
    control=True
).add_to(m)
# Couche 1 : densité de présence maritime
heat_data = []

for feature in features:
    lon, lat = feature["geometry"]["coordinates"]
    hours = feature["properties"]["presence_hours"]

    heat_data.append([
        lat,
        lon,
        math.log1p(hours)
    ])

HeatMap(
    heat_data,
    name="Densité de présence AIS",
    radius=18,
    blur=15,
    min_opacity=0.3
).add_to(m)

# Couche 2 : cellules individuelles
for feature in features:
    lon, lat = feature["geometry"]["coordinates"]
    props = feature["properties"]

    hours = props["presence_hours"]

    folium.CircleMarker(
        location=[lat, lon],
        radius=max(3, min(12, 3 + math.log1p(hours))),
        color="#ff6b00",
        fill=True,
        fill_opacity=0.65,
        popup=folium.Popup(
            f"""
            <b>Cellule maritime</b><br>
            Latitude : {lat}<br>
            Longitude : {lon}<br>
            Présence : {hours:.0f} heures<br>
            Pavillons : {props['flags_count']}<br>
            Observations : {props['records_count']}
            """,
            max_width=300
        )
    ).add_to(m)

folium.LayerControl().add_to(m)

# Ajustement automatique de l'emprise
bounds = [
    [feature["geometry"]["coordinates"][1],
     feature["geometry"]["coordinates"][0]]
    for feature in features
]

m.fit_bounds(bounds)

m.save("senegal_maritime_analysis.html")

print("Carte générée : senegal_maritime_analysis.html")
print("Nombre de cellules affichées :", len(features))
