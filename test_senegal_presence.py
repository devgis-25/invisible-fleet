
import os
import json
import requests

import csv
from collections import defaultdict

TOKEN = os.getenv("GFW_API_TOKEN")

if not TOKEN:
    raise RuntimeError("Token GFW introuvable.")

URL = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"

params = {
    "spatial-resolution": "LOW",
    "temporal-resolution": "MONTHLY",
    "group-by": "FLAG",
    "datasets[0]": "public-global-presence:latest",
    "date-range": "2024-01-01,2024-02-01",
    "format": "JSON",
}

# Zone maritime : ZEE du Sénégal
payload = {
    "region": {
        "dataset": "public-eez-areas",
        "id": 8371
    }
}

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

print("Interrogation de la ZEE du Sénégal...")

response = requests.post(
    URL,
    params=params,
    headers=headers,
    json=payload,
    timeout=120
)

print("HTTP Status:", response.status_code)

response.raise_for_status()

data = response.json()


# Récupération des observations depuis la structure réelle de GFW
entries = data.get("entries", [])

dataset_key = "public-global-presence:v5.0"

observations = []


for entry in entries:
    dataset_observations = entry.get(dataset_key, [])
    observations.extend(dataset_observations)



# ==========================================
# CONTROLE QUALITE DES OBSERVATIONS
# ==========================================

print("\n===== CONTROLE QUALITE =====")

# 1. Étendue géographique des observations
latitudes = [
    obs["lat"] for obs in observations
    if obs.get("lat") is not None
]

longitudes = [
    obs["lon"] for obs in observations
    if obs.get("lon") is not None
]

if latitudes and longitudes:
    print("Latitude minimale :", min(latitudes))
    print("Latitude maximale :", max(latitudes))
    print("Longitude minimale :", min(longitudes))
    print("Longitude maximale :", max(longitudes))

# 2. Pavillons manquants
missing_flags = [
    obs for obs in observations
    if not str(obs.get("flag", "")).strip()
]

print("Observations sans pavillon :", len(missing_flags))

# 3. Observations par pavillon
from collections import Counter

flag_counts = Counter(
    str(obs.get("flag", "")).strip() or "UNKNOWN"
    for obs in observations
)

print("\nTop 10 des pavillons par nombre d'observations :")

for flag, count in flag_counts.most_common(10):
    print(f"{flag} : {count}")

# 4. Vérification des coordonnées manquantes
invalid_coordinates = [
    obs for obs in observations
    if obs.get("lat") is None or obs.get("lon") is None
]

print("\nObservations sans coordonnées :", len(invalid_coordinates))
print("Total des observations :", len(observations))

print("\n===== BILAN MARITIME DU SENEGAL =====")

print("Nombre d'observations :", len(observations))

# Agrégation par pavillon
from collections import defaultdict

stats_flags = defaultdict(lambda: {
    "hours": 0,
    "cells": 0,
    "vessel_ids_sum": 0
})

for observation in observations:
    flag = observation.get("flag", "UNKNOWN")

    stats_flags[flag]["hours"] += observation.get("hours", 0)
    stats_flags[flag]["cells"] += 1
    stats_flags[flag]["vessel_ids_sum"] += observation.get("vesselIDs", 0)

total_hours = sum(obs.get("hours", 0) for obs in observations)

print("Nombre de cellules :", len(observations))
print("Nombre de pavillons :", len(stats_flags))
print("Total des heures de présence par cellule :", total_hours)

print("\n===== REPARTITION PAR PAVILLON =====")

for flag, stats in sorted(
    stats_flags.items(),
    key=lambda item: item[1]["hours"],
    reverse=True
):
    print(
        f"{flag} | "
        f"Heures : {stats['hours']} | "
        f"Cellules : {stats['cells']} | "
        f"Somme vesselIDs : {stats['vessel_ids_sum']}"
    )

# Export CSV
import csv

with open(
    "presence_senegal_2024_01.csv",
    "w",
    newline="",
    encoding="utf-8"
) as csvfile:

    fieldnames = [
        "date",
        "flag",
        "hours",
        "lat",
        "lon",
        "vesselIDs"
    ]

    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(observations)

print("\nExport CSV terminé.")
