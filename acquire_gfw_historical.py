
import os
import csv
import json
import time
import calendar
from pathlib import Path
from datetime import date

import requests


# ============================================================
# CONFIGURATION GENERALE
# ============================================================

TOKEN = os.getenv("GFW_API_TOKEN")

BASE_URL = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"

REGION = {
    "dataset": "public-eez-areas",
    "id": 8371,
}

START_YEAR = 2024
START_MONTH = 1

END_YEAR = 2026
END_MONTH = 10

SPATIAL_RESOLUTION = "LOW"
TEMPORAL_RESOLUTION = "MONTHLY"

DATASETS = {
    "ais": "public-global-presence:v5.0",
    "sar": "public-global-sar-presence:v5.0",
}

OUTPUT = Path("data/raw/gfw")
MANIFEST = Path("data/metadata/gfw_acquisition_manifest.csv")

REQUEST_DELAY = 3
MAX_RETRIES = 4

# Emprise large de contrôle, pas une frontière officielle de ZEE.
MIN_LAT, MAX_LAT = 8.0, 20.0
MIN_LON, MAX_LON = -25.0, -12.0

REQUIRED_COMMON = {"date", "lat", "lon", "vesselIDs"}


# ============================================================
# GENERATION DES MOIS
# ============================================================

def generate_months():
    months = []

    year = START_YEAR
    month = START_MONTH

    while (year, month) <= (END_YEAR, END_MONTH):
        period = f"{year:04d}-{month:02d}"

        start = date(year, month, 1)

        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)

        months.append({
            "period": period,
            "start": start.isoformat(),
            "end": end.isoformat(),
        })

        month += 1

        if month > 12:
            month = 1
            year += 1

    return months


# ============================================================
# EXTRACTION DES OBSERVATIONS
# ============================================================

def extract_observations(data):
    observations = []

    for entry in data.get("entries", []):
        if not isinstance(entry, dict):
            continue

        for key, values in entry.items():
            if key.startswith("public-global"):
                if isinstance(values, list):
                    observations.extend(values)

    return observations


# ============================================================
# VALIDATION DES DONNEES
# ============================================================

def validate_observations(rows, source, period):
    if not rows:
        raise ValueError(
            f"Aucune observation retournée pour {source} {period}"
        )

    expected_fields = set(REQUIRED_COMMON)

    if source == "ais":
        expected_fields.add("hours")
    else:
        expected_fields.add("detections")

    errors = []

    for index, row in enumerate(rows):
        missing = expected_fields - set(row.keys())

        if missing:
            errors.append(
                f"Ligne {index}: champs absents {missing}"
            )
            continue

        if row["date"] != period:
            errors.append(
                f"Ligne {index}: date inattendue {row['date']}"
            )

        try:
            lat = float(row["lat"])
            lon = float(row["lon"])
            vessel_ids = int(row["vesselIDs"])

            if source == "ais":
                value = float(row["hours"])
            else:
                value = int(row["detections"])

            if not MIN_LAT <= lat <= MAX_LAT:
                errors.append(
                    f"Ligne {index}: latitude hors emprise {lat}"
                )

            if not MIN_LON <= lon <= MAX_LON:
                errors.append(
                    f"Ligne {index}: longitude hors emprise {lon}"
                )

            if vessel_ids < 0 or value < 0:
                errors.append(
                    f"Ligne {index}: valeur négative"
                )

        except (TypeError, ValueError):
            errors.append(
                f"Ligne {index}: valeur numérique invalide"
            )

    if errors:
        raise ValueError(
            "\n".join(errors[:10])
        )

    return {
        "rows": len(rows),
        "sum_hours": (
            sum(float(r["hours"]) for r in rows)
            if source == "ais" else None
        ),
        "sum_detections": (
            sum(int(r["detections"]) for r in rows)
            if source == "sar" else None
        ),
    }


# ============================================================
# MANIFESTE
# ============================================================

def write_manifest(records):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "period",
        "source",
        "category",
        "dataset",
        "status",
        "rows",
        "sum_hours",
        "sum_detections",
        "http_status",
        "file",
        "acquired_at",
    ]

    with open(
        MANIFEST,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def load_manifest():
    if not MANIFEST.exists():
        return []

    with open(
        MANIFEST,
        newline="",
        encoding="utf-8-sig",
    ) as f:
        return list(csv.DictReader(f))


# ============================================================
# CONSTRUCTION DES REQUETES
# ============================================================

def build_request(source, category, start, end):
    dataset = DATASETS[source]

    params = {
        "spatial-resolution": SPATIAL_RESOLUTION,
        "temporal-resolution": TEMPORAL_RESOLUTION,
        "datasets[0]": dataset,
        "date-range": f"{start},{end}",
        "format": "JSON",
    }

    if source == "ais":
        params["group-by"] = "FLAG"

    elif source == "sar":
        matched = category == "matched"
        params["filters[0]"] = (
            f"matched='{str(matched).lower()}'"
        )

    return params


# ============================================================
# APPEL API AVEC RETRIES
# ============================================================

def fetch_report(params, period, source, category):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        print(
            f"  Requête {source}/{category} "
            f"{period} — tentative {attempt}/{MAX_RETRIES}"
        )

        try:
            response = requests.post(
                BASE_URL,
                params=params,
                json={"region": REGION},
                headers=headers,
                timeout=150,
            )

            if response.status_code == 200:
                data = response.json()

                # Une réponse paginée ne doit jamais être
                # considérée comme complète silencieusement.
                if data.get("nextOffset") is not None:
                    raise RuntimeError(
                        "Pagination détectée : "
                        "acquisition interrompue pour éviter "
                        "une sauvegarde partielle. "
                        f"nextOffset={data.get('nextOffset')}"
                    )

                return data, response.status_code

            if response.status_code not in (429, 500, 502, 503, 504, 524):
                raise RuntimeError(
                    f"Erreur HTTP {response.status_code}: "
                    f"{response.text[:1500]}"
                )

            wait = min(15 * attempt, 90)

            print(
                f"  HTTP {response.status_code}. "
                f"Nouvel essai dans {wait}s."
            )

            time.sleep(wait)

        except requests.RequestException as exc:
            wait = min(10 * attempt, 60)

            print("  Erreur réseau :", exc)
            time.sleep(wait)

    raise RuntimeError(
        f"Échec définitif : {source} {category} {period}"
    )


# ============================================================
# SAUVEGARDE ET ACQUISITION
# ============================================================

def acquire_one(month, source, category, manifest):
    period = month["period"]

    if source == "ais":
        folder = OUTPUT / "ais"
        filename = f"ais_{period}.json"
        category_label = "all_flags"

    elif category == "matched":
        folder = OUTPUT / "sar_matching"
        filename = f"sar_{period}_matched.json"
        category_label = "matched"

    else:
        folder = OUTPUT / "sar_matching"
        filename = f"sar_{period}_unmatched.json"
        category_label = "unmatched"

    folder.mkdir(parents=True, exist_ok=True)

    output_file = folder / filename

    # Reprise : ne pas écraser un fichier déjà validé.
    if output_file.exists():
        try:
            with open(output_file, encoding="utf-8") as f:
                existing = json.load(f)

            rows = extract_observations(existing)
            metrics = validate_observations(
                rows, source, period
            )

            print(
                f"  [SKIP] {filename} déjà présent "
                f"et valide ({metrics['rows']} lignes)"
            )

            return

        except Exception as exc:
            print("  Fichier existant invalide :", exc)
            print("  Nouvelle acquisition nécessaire.")

    params = build_request(
        source,
        category,
        month["start"],
        month["end"],
    )

    data, status_code = fetch_report(
        params,
        period,
        source,
        category,
    )

    rows = extract_observations(data)

    metrics = validate_observations(
        rows,
        source,
        period,
    )

    # Vérification de la clé de dataset réellement renvoyée.
    dataset_keys = sorted({
        key
        for entry in data.get("entries", [])
        if isinstance(entry, dict)
        for key in entry
        if key.startswith("public-global")
    })

    if not dataset_keys:
        raise ValueError(
            f"Aucune clé de dataset dans {filename}"
        )

    # Sauvegarde de la réponse originale.
    temp_file = output_file.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    temp_file.replace(output_file)

    metadata = {
        "source": source,
        "category": category_label,
        "period": period,
        "start_date": month["start"],
        "end_date_exclusive": month["end"],
        "region": REGION,
        "dataset_requested": DATASETS[source],
        "dataset_returned": dataset_keys,
        "spatial_resolution": SPATIAL_RESOLUTION,
        "temporal_resolution": TEMPORAL_RESOLUTION,
        "group_by": "FLAG" if source == "ais" else None,
        "filter": (
            f"matched='{str(category == 'matched').lower()}'"
            if source == "sar" else None
        ),
        "http_status": status_code,
        "api_total": data.get("total"),
        "api_limit": data.get("limit"),
        "api_offset": data.get("offset"),
        "api_next_offset": data.get("nextOffset"),
        "metrics": metrics,
    }

    metadata_file = output_file.with_name(
        output_file.stem + "_metadata.json"
    )

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    record = {
        "period": period,
        "source": source,
        "category": category_label,
        "dataset": DATASETS[source],
        "status": "success",
        "rows": metrics["rows"],
        "sum_hours": metrics["sum_hours"],
        "sum_detections": metrics["sum_detections"],
        "http_status": status_code,
        "file": str(output_file),
        "acquired_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    manifest.append(record)
    write_manifest(manifest)

    print(
        f"  [OK] {filename} | "
        f"{metrics['rows']} lignes"
    )


# ============================================================
# CONTROLE FINAL
# ============================================================

def final_report(manifest):
    expected = 34 * 3

    successful = [
        r for r in manifest
        if r.get("status") == "success"
    ]

    print("\n" + "=" * 65)
    print("BILAN DE L'ACQUISITION HISTORIQUE")
    print("=" * 65)

    print("Rapports attendus :", expected)
    print("Rapports validés :", len(successful))
    print("Rapports restants :", expected - len(successful))

    for source in ("ais", "sar"):
        source_records = [
            r for r in successful
            if r["source"] == source
        ]

        print(
            f"{source.upper()} : "
            f"{len(source_records)} rapports"
        )

    if len(successful) == expected:
        print("\nACQUISITION TERMINEE.")
    else:
        print("\nACQUISITION INCOMPLETE.")
        print("Relance le script pour reprendre.")


# ============================================================
# MAIN
# ============================================================

def main():
    if not TOKEN:
        raise RuntimeError(
            "GFW_API_TOKEN absent des variables d'environnement."
        )

    months = generate_months()
    manifest = load_manifest()

    print("=" * 65)
    print("THE INVISIBLE FLEET — HISTORICAL ACQUISITION")
    print("=" * 65)
    print("Période :", months[0]["period"], "à", months[-1]["period"])
    print("Nombre de mois :", len(months))
    print("Rapports attendus :", len(months) * 3)
    print("Région :", REGION)
    print("Dataset AIS :", DATASETS["ais"])
    print("Dataset SAR :", DATASETS["sar"])

    for month in months:
        print("\n" + "-" * 65)
        print("PÉRIODE :", month["period"])
        print("-" * 65)

        acquire_one(
            month, "ais", "all", manifest
        )
        time.sleep(REQUEST_DELAY)

        acquire_one(
            month, "sar", "matched", manifest
        )
        time.sleep(REQUEST_DELAY)

        acquire_one(
            month, "sar", "unmatched", manifest
        )
        time.sleep(REQUEST_DELAY)

    final_report(manifest)


if __name__ == "__main__":
    main()
