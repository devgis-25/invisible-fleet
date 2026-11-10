
import json
from pathlib import Path

FILES = [
    Path("data/raw/gfw/ais/ais_2024-01.json"),
    Path("data/raw/gfw/ais/ais_2026-10.json"),
    Path("data/raw/gfw/sar/sar_2024-01.json"),
    Path("data/raw/gfw/sar/sar_2026-10.json"),
    Path("data/raw/gfw/sar_matching/sar_2024-01_matched.json"),
    Path("data/raw/gfw/sar_matching/sar_2024-01_unmatched.json"),
    Path("data/raw/gfw/sar_matching/sar_2026-10_matched.json"),
    Path("data/raw/gfw/sar_matching/sar_2026-10_unmatched.json"),
]


def extract_rows(data):
    rows = []

    for entry in data.get("entries", []):
        if isinstance(entry, dict):
            for key, values in entry.items():
                if key.startswith("public-global"):
                    if isinstance(values, list):
                        rows.extend(values)

    return rows


def inspect_file(path):
    print("\n" + "=" * 70)
    print(path)

    if not path.exists():
        print("FICHIER ABSENT")
        return None

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    rows = extract_rows(data)

    print("Clés racine :", list(data.keys()))
    print("Total API :", data.get("total"))
    print("Limit :", data.get("limit"))
    print("Offset :", data.get("offset"))
    print("Next offset :", data.get("nextOffset"))
    print("Metadata :", data.get("metadata"))
    print("Nombre de lignes :", len(rows))

    if not rows:
        return {
            "path": path,
            "rows": 0,
            "detections": 0,
        }

    lats = [r["lat"] for r in rows if r.get("lat") is not None]
    lons = [r["lon"] for r in rows if r.get("lon") is not None]

    dates = sorted(set(r.get("date") for r in rows))

    detections = sum(r.get("detections", 0) for r in rows)
    hours = sum(r.get("hours", 0) for r in rows)

    print("Dates :", dates)
    print("Latitude :", min(lats), "à", max(lats))
    print("Longitude :", min(lons), "à", max(lons))
    print("Somme detections :", detections)
    print("Somme hours :", hours)
    print("Exemple :", rows[0])

    return {
        "path": path,
        "rows": len(rows),
        "detections": detections,
        "hours": hours,
    }


def main():
    results = {}

    for path in FILES:
        result = inspect_file(path)

        if result:
            results[path.name] = result

    print("\n" + "=" * 70)
    print("CONTROLE DE COHERENCE SAR")

    for period in ("2024-01", "2026-10"):
        raw = results.get(f"sar_{period}.json", {})
        matched = results.get(f"sar_{period}_matched.json", {})
        unmatched = results.get(f"sar_{period}_unmatched.json", {})

        raw_total = raw.get("detections", 0)
        matched_total = matched.get("detections", 0)
        unmatched_total = unmatched.get("detections", 0)

        print(f"\n{period}")
        print("SAR total :", raw_total)
        print("SAR matched :", matched_total)
        print("SAR unmatched :", unmatched_total)
        print("Somme des catégories :", matched_total + unmatched_total)
        print(
            "Différence :",
            raw_total - matched_total - unmatched_total
        )


if __name__ == "__main__":
    main()
