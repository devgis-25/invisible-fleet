
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent

AIS_DIR = ROOT / "data/raw/gfw/ais"
SAR_DIR = ROOT / "data/raw/gfw/sar_matching"
OUTPUT_DIR = ROOT / "data/processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

START_PERIOD = "2024-01"
END_PERIOD = "2026-10"

DATASET_AIS = "public-global-presence:v5.0"
DATASET_SAR = "public-global-sar-presence:v5.0"

EXPECTED_MONTHS = pd.period_range(
    START_PERIOD, END_PERIOD, freq="M"
).astype(str).tolist()


def extract_observations(filepath, dataset_name):
    """Extrait les observations d'un rapport GFW imbriqué."""

    with open(filepath, "r", encoding="utf-8") as f:
        payload = json.load(f)

    observations = []

    for entry in payload.get("entries", []):
        if not isinstance(entry, dict):
            continue

        records = entry.get(dataset_name, [])

        if isinstance(records, list):
            observations.extend(records)

    if not observations:
        raise ValueError(
            f"Aucune observation trouvée dans {filepath}"
        )

    return observations


def load_ais():
    frames = []

    for period in EXPECTED_MONTHS:
        filepath = AIS_DIR / f"ais_{period}.json"

        if not filepath.exists():
            raise FileNotFoundError(filepath)

        records = extract_observations(
            filepath, DATASET_AIS
        )

        df = pd.DataFrame(records)
        df["source"] = "AIS"
        df["category"] = "all_flags"

        frames.append(df)

        print(
            f"[AIS] {period}: {len(df):,} observations"
        )

    return pd.concat(frames, ignore_index=True)


def load_sar():
    frames = []

    for period in EXPECTED_MONTHS:
        for category in ["matched", "unmatched"]:

            filepath = (
                SAR_DIR /
                f"sar_{period}_{category}.json"
            )

            if not filepath.exists():
                raise FileNotFoundError(filepath)

            records = extract_observations(
                filepath, DATASET_SAR
            )

            df = pd.DataFrame(records)
            df["source"] = "SAR"
            df["category"] = category

            frames.append(df)

            print(
                f"[SAR] {period} / {category}: "
                f"{len(df):,} observations"
            )

    return pd.concat(frames, ignore_index=True)


def validate_dataset(df, source):
    """Contrôles de qualité sans supprimer de données."""

    required = (
        ["date", "lat", "lon", "hours", "vesselIDs"]
        if source == "AIS"
        else ["date", "lat", "lon", "detections"]
    )

    missing_columns = [
        col for col in required if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{source}: colonnes absentes : {missing_columns}"
        )

    df["date"] = df["date"].astype(str)

    for col in ["lat", "lon"]:
        df[col] = pd.to_numeric(
            df[col], errors="coerce"
        )

    numeric_columns = (
        ["hours", "vesselIDs"]
        if source == "AIS"
        else ["detections", "vesselIDs"]
    )

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col], errors="coerce"
            )

    invalid_dates = sorted(
        set(df["date"]) - set(EXPECTED_MONTHS)
    )

    invalid_coordinates = df[
        df["lat"].isna()
        | df["lon"].isna()
        | ~df["lat"].between(-90, 90)
        | ~df["lon"].between(-180, 180)
    ]

    # Enveloppe géographique de contrôle grossière.
    # Ce n'est PAS la frontière officielle de la ZEE.
    outside_sanity_bounds = df[
        ~df["lat"].between(8, 20)
        | ~df["lon"].between(-25, -12)
    ]

    exact_duplicates = int(df.duplicated().sum())

    report = {
        "source": source,
        "rows": int(len(df)),
        "periods": int(df["date"].nunique()),
        "invalid_dates": invalid_dates,
        "invalid_coordinates": int(len(invalid_coordinates)),
        "outside_sanity_bounds": int(
            len(outside_sanity_bounds)
        ),
        "exact_duplicate_rows": exact_duplicates,
        "missing_values": {
            col: int(df[col].isna().sum())
            for col in required
        },
        "latitude_min": float(df["lat"].min()),
        "latitude_max": float(df["lat"].max()),
        "longitude_min": float(df["lon"].min()),
        "longitude_max": float(df["lon"].max()),
    }

    return report


def build_monthly_summary(ais, sar):
    combined = pd.concat(
        [
            ais.assign(source_type="AIS"),
            sar.assign(source_type="SAR")
        ],
        ignore_index=True,
        sort=False
    )

    rows = []

    for (period, source, category), group in combined.groupby(
        ["date", "source_type", "category"],
        dropna=False
    ):
        rows.append({
            "period": period,
            "source": source,
            "category": category,
            "rows": len(group),
            "sum_hours": (
                group["hours"].sum()
                if source == "AIS" else None
            ),
            "sum_detections": (
                group["detections"].sum()
                if source == "SAR" else None
            )
        })

    return pd.DataFrame(rows).sort_values(
        ["period", "source", "category"]
    )


def main():
    print("\n========== CHARGEMENT AIS ==========\n")
    ais = load_ais()

    print("\n========== CHARGEMENT SAR ==========\n")
    sar = load_sar()

    print("\n========== VALIDATION ==========\n")

    ais_report = validate_dataset(ais, "AIS")
    sar_report = validate_dataset(sar, "SAR")

    print(json.dumps(
        {"AIS": ais_report, "SAR": sar_report},
        indent=2,
        ensure_ascii=False
    ))

    if ais_report["periods"] != 34:
        raise ValueError("AIS : les 34 mois ne sont pas présents.")

    if sar_report["periods"] != 34:
        raise ValueError("SAR : les 34 mois ne sont pas présents.")

    if ais_report["invalid_dates"] or sar_report["invalid_dates"]:
        raise ValueError("Dates invalides détectées.")

    if ais_report["invalid_coordinates"] or sar_report["invalid_coordinates"]:
        raise ValueError("Coordonnées invalides détectées.")

    if ais_report["outside_sanity_bounds"] or sar_report["outside_sanity_bounds"]:
        raise ValueError(
            "Des coordonnées sont hors de l'enveloppe de contrôle."
        )

    # Ne jamais supprimer automatiquement les doublons :
    # ils doivent être examinés avant toute décision.

    ais_path = OUTPUT_DIR / (
        "ais_presence_2024-01_2026-10.csv"
    )
    sar_path = OUTPUT_DIR / (
        "sar_detections_2024-01_2026-10.csv"
    )
    summary_path = OUTPUT_DIR / "monthly_summary.csv"
    report_path = OUTPUT_DIR / "data_quality_report.json"

    ais.to_csv(
        ais_path, index=False, encoding="utf-8-sig"
    )
    sar.to_csv(
        sar_path, index=False, encoding="utf-8-sig"
    )

    summary = build_monthly_summary(ais, sar)
    summary.to_csv(
        summary_path, index=False, encoding="utf-8-sig"
    )

    quality_report = {
        "period": {
            "start": START_PERIOD,
            "end": END_PERIOD,
            "months": 34
        },
        "ais": ais_report,
        "sar": sar_report,
        "total_ais_observations": int(len(ais)),
        "total_sar_observations": int(len(sar)),
        "total_sar_detections": int(sar["detections"].sum()),
        "sar_categories": {
            category: int(group["detections"].sum())
            for category, group in sar.groupby("category")
        }
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            quality_report,
            f,
            indent=2,
            ensure_ascii=False
        )

    print("\n========== CONSOLIDATION TERMINÉE ==========")
    print(f"AIS : {len(ais):,} observations")
    print(f"SAR : {len(sar):,} observations")
    print(f"Détections SAR : {sar['detections'].sum():,}")
    print(f"\nFichiers créés dans : {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
