
import csv
from pathlib import Path

FILES = [
    Path("data/processed/ais_presence_2024-01_2026-10.csv"),
    Path("data/processed/sar_detections_2024-01_2026-10.csv"),
]

for file_path in FILES:
    print("\n" + "=" * 70)
    print(f"FICHIER : {file_path}")
    print("=" * 70)

    if not file_path.exists():
        print("ERREUR : fichier introuvable")
        continue

    with file_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        print("\nCOLONNES :")
        for column in reader.fieldnames or []:
            print(f" - {column}")

        print("\nPREMIÈRE LIGNE :")
        first_row = next(reader, None)

        if first_row:
            for key, value in first_row.items():
                print(f" {key}: {value}")
        else:
            print("Fichier vide")

print("\nInspection terminée.")
