
from pathlib import Path
from datetime import datetime
import json
import shutil
import pandas as pd

ROOT = Path(__file__).resolve().parent

MANIFEST = ROOT / "data" / "metadata" / "gfw_acquisition_manifest.csv"
AIS_DIR = ROOT / "data" / "raw" / "gfw" / "ais"
SAR_DIR = ROOT / "data" / "raw" / "gfw" / "sar_matching"

DATASET_AIS = "public-global-presence:v5.0"
DATASET_SAR = "public-global-sar-presence:v5.0"


def extract_observations(path, dataset):
    """Extrait les observations depuis la structure imbriquée GFW."""

    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    entries = payload.get("entries", [])

    observations = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        dataset_rows = entry.get(dataset, [])

        if isinstance(dataset_rows, list):
            observations.extend(dataset_rows)

    if not observations:
        raise ValueError(
            f"Aucune observation trouvée pour {dataset} dans {path}"
        )

    return observations


def build_record(period, source, category, dataset, path):

    observations = extract_observations(path, dataset)

    dates = {
        str(row.get("date"))
        for row in observations
    }

    if dates != {period}:
        raise ValueError(
            f"Dates incorrectes dans {path}: {dates}"
        )

    # Contrôle des coordonnées et des valeurs
    for row in observations:
        lat = float(row["lat"])
        lon = float(row["lon"])

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(f"Coordonnées invalides : {row}")

    rows = len(observations)

    sum_hours = None
    sum_detections = None

    if source == "ais":
        sum_hours = sum(
            float(row.get("hours", 0) or 0)
            for row in observations
        )

    elif source == "sar":
        sum_detections = sum(
            int(row.get("detections", 0) or 0)
            for row in observations
        )

    return {
        "period": period,
        "source": source,
        "category": category,
        "dataset": dataset,
        "status": "success",
        "rows": rows,
        "sum_hours": sum_hours,
        "sum_detections": sum_detections,
        "http_status": 200,
        "file": str(path.relative_to(ROOT)).replace("/", "\\"),
        "acquired_at": datetime.fromtimestamp(
            path.stat().st_mtime
        ).strftime("%Y-%m-%d %H:%M:%S"),
    }


def main():

    if not MANIFEST.exists():
        raise FileNotFoundError(MANIFEST)

    df = pd.read_csv(
        MANIFEST,
        dtype={"period": str}
    )

    required_columns = [
        "period", "source", "category", "dataset",
        "status", "rows", "sum_hours", "sum_detections",
        "http_status", "file", "acquired_at"
    ]

    if list(df.columns) != required_columns:
        raise ValueError(
            f"Structure inattendue du manifeste : {list(df.columns)}"
        )

    missing_records = []

    targets = [
        ("ais", "all_flags", DATASET_AIS),
        ("sar", "matched", DATASET_SAR),
        ("sar", "unmatched", DATASET_SAR),
    ]

    for period in ["2024-01", "2026-10"]:

        print(f"\nPériode : {period}")

        for source, category, dataset in targets:

            already_registered = (
                (df["period"] == period)
                & (df["source"] == source)
                & (df["category"] == category)
                & (df["status"] == "success")
            ).any()

            if already_registered:
                print(f"[SKIP] {source} / {category}")
                continue

            if source == "ais":
                path = AIS_DIR / f"ais_{period}.json"
            else:
                path = SAR_DIR / f"sar_{period}_{category}.json"

            if not path.exists():
                raise FileNotFoundError(path)

            record = build_record(
                period,
                source,
                category,
                dataset,
                path
            )

            missing_records.append(record)

            print(
                f"[ADD] {source} / {category} "
                f"| {record['rows']} lignes "
                f"| heures={record['sum_hours']} "
                f"| détections={record['sum_detections']}"
            )

    if not missing_records:
        print("\nAucune entrée manquante.")
        return

    # Sauvegarde de sécurité avant modification
    backup = MANIFEST.with_name(
        "gfw_acquisition_manifest_backup.csv"
    )

    shutil.copy2(MANIFEST, backup)
    print(f"\nSauvegarde créée : {backup}")

    # Ajout des nouvelles lignes
    updated = pd.concat(
        [df, pd.DataFrame(missing_records)],
        ignore_index=True
    )

    updated.to_csv(
        MANIFEST,
        index=False,
        encoding="utf-8"
    )

    # Relecture et validation indépendante
    result = pd.read_csv(
        MANIFEST,
        dtype={"period": str}
    )

    successful = result[result["status"] == "success"]

    duplicates = successful.duplicated(
        ["period", "source", "category"]
    ).sum()

    expected = pd.period_range(
        "2024-01", "2026-10", freq="M"
    ).astype(str)

    print("\n========== VALIDATION FINALE ==========")

    print(
        successful.groupby(
            ["source", "category"]
        ).size()
    )

    print(f"\nTotal des rapports : {len(successful)}")
    print(f"Doublons : {duplicates}")

    for source, category, _ in targets:

        periods = set(
            successful.loc[
                (successful["source"] == source)
                & (successful["category"] == category),
                "period"
            ]
        )

        missing = sorted(set(expected) - periods)

        print(
            f"{source}/{category} : "
            f"{len(periods)}/34 | manquants : {missing}"
        )

        assert not missing, (
            f"Périodes manquantes pour {source}/{category}"
        )

    assert len(successful) == 102
    assert duplicates == 0

    print("\nSUCCÈS : MANIFESTE COMPLET, 102/102 RAPPORTS.")


if __name__ == "__main__":
    main()
