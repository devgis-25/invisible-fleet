
import os
import json
import time
from pathlib import Path

import requests


# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.getenv("GFW_API_TOKEN")

BASE_URL = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"

REGION = {
    "dataset": "public-eez-areas",
    "id": 8371,
}

OUTPUT_DIR = Path("data/raw/gfw")

PERIODS = [
    ("2024-01", "2024-01-01", "2024-02-01"),
    ("2026-10", "2026-10-01", "2026-11-01"),
]

DATASETS = {
    "ais": "public-global-presence:v5.0",
    "sar": "public-global-sar-presence:latest",
}


def extract_observations(data):
    """Extrait les observations du format de réponse GFW."""
    observations = []

    for entry in data.get("entries", []):
        if isinstance(entry, dict):
            for key, values in entry.items():
                if key.startswith("public-global"):
                    if isinstance(values, list):
                        observations.extend(values)

        elif isinstance(entry, list):
            observations.extend(entry)

    return observations


def request_report(source, dataset, period, start, end):
    params = {
        "spatial-resolution": "LOW",
        "temporal-resolution": "MONTHLY",
        "datasets[0]": dataset,
        "date-range": f"{start},{end}",
        "format": "JSON",
    }

    # Pour AIS, ventilation par pavillon.
    if source == "ais":
        params["group-by"] = "FLAG"

    payload = {
        "region": REGION
    }

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    print(f"\nAcquisition : {source.upper()} | {period}")

    response = requests.post(
        BASE_URL,
        params=params,
        json=payload,
        headers=headers,
        timeout=150,
    )

    print("HTTP :", response.status_code)

    if response.status_code != 200:
        print("Réponse API :", response.text[:1500])
        response.raise_for_status()

    data = response.json()

    observations = extract_observations(data)

    # Sauvegarde de la réponse brute.
    folder = OUTPUT_DIR / source
    folder.mkdir(parents=True, exist_ok=True)

    output_file = folder / f"{source}_{period}.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    # Métadonnées de provenance.
    metadata = {
        "source": source,
        "dataset_requested": dataset,
        "period": period,
        "start_date": start,
        "end_date_exclusive": end,
        "region": REGION,
        "spatial_resolution": "LOW",
        "temporal_resolution": "MONTHLY",
        "http_status": response.status_code,
        "total_api": data.get("total"),
        "observation_count": len(observations),
        "dataset_keys": list({
            key
            for entry in data.get("entries", [])
            if isinstance(entry, dict)
            for key in entry.keys()
        }),
    }

    metadata_file = folder / f"{source}_{period}_metadata.json"

    with open(metadata_file, "w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    print("Observations :", len(observations))
    print("Total API :", data.get("total"))
    print("Fichier :", output_file)

    if observations:
        print("Exemple :", observations[0])
    else:
        print("ATTENTION : aucune observation retournée.")

    return metadata


def main():
    if not TOKEN:
        raise RuntimeError(
            "GFW_API_TOKEN absent des variables d'environnement."
        )

    results = []

    # Exécution séquentielle : GFW limite les rapports concurrents.
    for source, dataset in DATASETS.items():
        for period, start, end in PERIODS:
            result = request_report(
                source,
                dataset,
                period,
                start,
                end,
            )
            results.append(result)
            time.sleep(3)

    print("\n========== BILAN DES TESTS ==========")

    for result in results:
        print(
            result["source"],
            result["period"],
            "=>",
            result["observation_count"],
            "observations",
        )

    print("\nTests terminés.")


if __name__ == "__main__":
    main()
