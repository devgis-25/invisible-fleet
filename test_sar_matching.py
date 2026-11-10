
import os
import json
import time
from pathlib import Path

import requests


TOKEN = os.getenv("GFW_API_TOKEN")

BASE_URL = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"

REGION = {
    "dataset": "public-eez-areas",
    "id": 8371,
}

DATASET = "public-global-sar-presence:v5.0"

PERIODS = {
    "2024-01": ("2024-01-01", "2024-02-01"),
    "2026-10": ("2026-10-01", "2026-11-01"),
}

OUTPUT_DIR = Path("data/raw/gfw/sar_matching")


def extract_observations(data):
    observations = []

    for entry in data.get("entries", []):
        if isinstance(entry, dict):
            for key, values in entry.items():
                if key.startswith("public-global-sar-presence"):
                    if isinstance(values, list):
                        observations.extend(values)

    return observations


def test_matching(period, start, end, matched):
    status = "matched" if matched else "unmatched"

    params = {
        "spatial-resolution": "LOW",
        "temporal-resolution": "MONTHLY",
        "datasets[0]": DATASET,
        "filters[0]": f"matched='{str(matched).lower()}'",
        "date-range": f"{start},{end}",
        "format": "JSON",
    }

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    print(f"\nSAR {period} | {status}")

    response = requests.post(
        BASE_URL,
        params=params,
        json={"region": REGION},
        headers=headers,
        timeout=150,
    )

    print("HTTP :", response.status_code)

    if response.status_code != 200:
        print(response.text[:1500])
        response.raise_for_status()

    data = response.json()
    observations = extract_observations(data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / f"sar_{period}_{status}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_detections = sum(
        row.get("detections", 0)
        for row in observations
    )

    result = {
        "period": period,
        "matching": status,
        "dataset": DATASET,
        "http_status": response.status_code,
        "rows": len(observations),
        "total_detections": total_detections,
        "total_api": data.get("total"),
        "example": observations[0] if observations else None,
    }

    print("Lignes :", result["rows"])
    print("Détections :", result["total_detections"])
    print("Exemple :", result["example"])
    print("Fichier :", output_file)

    return result


def main():
    if not TOKEN:
        raise RuntimeError("GFW_API_TOKEN absent.")

    results = []

    for period, (start, end) in PERIODS.items():
        for matched in (True, False):
            result = test_matching(
                period,
                start,
                end,
                matched,
            )

            results.append(result)
            time.sleep(3)

    print("\n========== COMPARAISON SAR ==========")

    for result in results:
        print(
            result["period"],
            result["matching"],
            "| lignes =", result["rows"],
            "| détections =", result["total_detections"],
        )

    print("\nTests terminés.")


if __name__ == "__main__":
    main()
