
import csv
import json
from collections import defaultdict

INPUT_FILE = "presence_senegal_2024_01.csv"
OUTPUT_GEOJSON = "presence_cells.geojson"
OUTPUT_CSV = "presence_cells_aggregated.csv"

cells = defaultdict(lambda: {
    "hours": 0,
    "flags": set(),
    "records": 0,
    "vessel_ids_sum": 0
})

# Lecture et agrégation des observations
with open(INPUT_FILE, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        lat = float(row["lat"])
        lon = float(row["lon"])
        key = (lat, lon)

        flag = (row.get("flag") or "").strip()

        cells[key]["hours"] += float(row["hours"] or 0)
        cells[key]["records"] += 1
        cells[key]["vessel_ids_sum"] += int(row["vesselIDs"] or 0)

        if flag:
            cells[key]["flags"].add(flag)

# Création des entités GeoJSON
features = []

for (lat, lon), stats in cells.items():
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat]
        },
        "properties": {
            "presence_hours": stats["hours"],
            "flags_count": len(stats["flags"]),
            "records_count": stats["records"],
            "vessel_ids_sum": stats["vessel_ids_sum"]
        }
    })

geojson = {
    "type": "FeatureCollection",
    "features": features
}

with open(OUTPUT_GEOJSON, "w", encoding="utf-8") as file:
    json.dump(geojson, file, ensure_ascii=False, indent=2)

# Export CSV agrégé
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)

    writer.writerow([
        "latitude",
        "longitude",
        "presence_hours",
        "flags_count",
        "records_count",
        "vessel_ids_sum"
    ])

    for feature in features:
        lon, lat = feature["geometry"]["coordinates"]
        props = feature["properties"]

        writer.writerow([
            lat,
            lon,
            props["presence_hours"],
            props["flags_count"],
            props["records_count"],
            props["vessel_ids_sum"]
        ])

print("\n===== ANALYSE SPATIALE =====")
print("Nombre d'observations initiales :", 11953)
print("Nombre de cellules géographiques :", len(cells))
print("Nombre de cellules avec plusieurs pavillons :",
      sum(1 for c in cells.values() if len(c["flags"]) > 1))

print("\nCellules les plus actives :")

top_cells = sorted(
    cells.items(),
    key=lambda item: item[1]["hours"],
    reverse=True
)[:10]

for (lat, lon), stats in top_cells:
    print(
        f"Lat: {lat} | Lon: {lon} | "
        f"Heures: {stats['hours']} | "
        f"Pavillons: {len(stats['flags'])}"
    )

print("\nFichiers générés :")
print(OUTPUT_GEOJSON)
print(OUTPUT_CSV)
