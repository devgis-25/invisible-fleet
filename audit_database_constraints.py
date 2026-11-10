
import csv
from collections import Counter
from pathlib import Path


FILES = {
    "AIS": {
        "path": Path(
            "data/processed/ais_presence_2024-01_2026-10.csv"
        ),
        "keys": ["date", "flag", "lat", "lon", "category"],
    },
    "SAR": {
        "path": Path(
            "data/processed/sar_detections_2024-01_2026-10.csv"
        ),
        "keys": ["date", "lat", "lon", "category"],
    },
}


for name, config in FILES.items():
    path = config["path"]
    keys = config["keys"]

    print("\n" + "=" * 65)
    print(f"AUDIT DES CONTRAINTES : {name}")
    print("=" * 65)

    counts = Counter()

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            key = tuple(row[column] for column in keys)
            counts[key] += 1

    duplicates = {
        key: count
        for key, count in counts.items()
        if count > 1
    }

    print("Nombre de combinaisons :", len(counts))
    print("Combinaisons dupliquées :", len(duplicates))
    print(
        "Lignes concernées :",
        sum(count - 1 for count in duplicates.values())
    )

    if duplicates:
        print("\nExemples de doublons :")
        for key, count in list(duplicates.items())[:10]:
            print(f"{key} -> {count} occurrences")
    else:
        print("Aucun doublon sur les clés prévues.")
