
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "processed"

AIS_FILE = DATA_DIR / "ais_presence_2024-01_2026-10.csv"
SAR_FILE = DATA_DIR / "sar_detections_2024-01_2026-10.csv"

def main():
    print("Chargement des datasets...")
    ais = pd.read_csv(AIS_FILE)
    sar = pd.read_csv(SAR_FILE)

    ais["hours"] = pd.to_numeric(ais["hours"])
    ais["vesselIDs"] = pd.to_numeric(ais["vesselIDs"])
    sar["detections"] = pd.to_numeric(sar["detections"])

    # --------------------------------------------------
    # 1. INDICATEURS MENSUELS AIS
    # --------------------------------------------------

    ais_monthly = ais.groupby("date").agg(
        ais_observations=("date", "size"),
        ais_presence_hours=("hours", "sum"),
        ais_vessel_id_counts_sum=("vesselIDs", "sum"),
        active_flags=("flag", "nunique"),
        unknown_flag_rows=(
            "flag",
            lambda s: int(s.isna().sum() + s.eq("").sum())
        )
    )

    # --------------------------------------------------
    # 2. INDICATEURS MENSUELS SAR
    # --------------------------------------------------

    sar_monthly = sar.pivot_table(
        index="date",
        columns="category",
        values="detections",
        aggfunc="sum",
        fill_value=0
    )

    sar_rows = sar.pivot_table(
        index="date",
        columns="category",
        values="detections",
        aggfunc="count",
        fill_value=0
    )

    sar_monthly = sar_monthly.rename(columns={
        "matched": "sar_matched_detections",
        "unmatched": "sar_unmatched_detections"
    })

    sar_rows = sar_rows.rename(columns={
        "matched": "sar_matched_rows",
        "unmatched": "sar_unmatched_rows"
    })

    monthly = ais_monthly.join(
        sar_monthly, how="outer"
    ).join(sar_rows, how="outer").fillna(0)

    monthly["sar_total_detections"] = (
        monthly["sar_matched_detections"]
        + monthly["sar_unmatched_detections"]
    )

    monthly["sar_unmatched_rate_pct"] = (
        monthly["sar_unmatched_detections"]
        / monthly["sar_total_detections"].replace(0, pd.NA)
        * 100
    )

    monthly = monthly.reset_index().sort_values("date")

    monthly.to_csv(
        DATA_DIR / "monthly_indicators.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------
    # 3. ANALYSE DES PAVILLONS
    # --------------------------------------------------

    flag_analysis = (
        ais[ais["flag"].notna() & ais["flag"].ne("")]
        .groupby("flag")
        .agg(
            observations=("flag", "size"),
            presence_hours=("hours", "sum"),
            spatial_cells=("lat", lambda x: len(
                set(zip(x, ais.loc[x.index, "lon"]))
            )),
            vessel_id_counts_sum=("vesselIDs", "sum")
        )
        .sort_values("presence_hours", ascending=False)
        .reset_index()
    )

    flag_analysis.to_csv(
        DATA_DIR / "flag_analysis.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------
    # 4. HOTSPOTS SPATIAUX AIS
    # --------------------------------------------------

    ais_hotspots = (
        ais.groupby(["lat", "lon"])
        .agg(
            observations=("date", "size"),
            presence_hours=("hours", "sum"),
            active_flags=("flag", "nunique"),
            vessel_id_counts_sum=("vesselIDs", "sum")
        )
        .sort_values("presence_hours", ascending=False)
        .reset_index()
    )

    ais_hotspots.to_csv(
        DATA_DIR / "ais_spatial_hotspots.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------
    # 5. HOTSPOTS SPATIAUX SAR
    # --------------------------------------------------

    sar_hotspots = (
        sar.groupby(["lat", "lon", "category"])
        .agg(
            observations=("date", "size"),
            detections=("detections", "sum"),
            months_observed=("date", "nunique")
        )
        .sort_values("detections", ascending=False)
        .reset_index()
    )

    sar_hotspots.to_csv(
        DATA_DIR / "sar_spatial_hotspots.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------
    # 6. RAPPORT SYNTHÉTIQUE
    # --------------------------------------------------

    print("\n========== INDICATEURS GLOBAUX ==========")

    print(f"AIS observations : {len(ais):,}")
    print(f"AIS presence hours : {ais['hours'].sum():,.0f}")
    print(f"Pavillons distincts : {ais['flag'].nunique()}")

    print(f"\nSAR observations : {len(sar):,}")
    print(f"SAR detections : {sar['detections'].sum():,.0f}")

    print("\nRépartition SAR :")
    print(
        sar.groupby("category")["detections"]
        .sum()
        .to_string()
    )

    print("\n========== TOP 10 PAVILLONS ==========")
    print(
        flag_analysis.head(10)[
            ["flag", "presence_hours", "observations"]
        ].to_string(index=False)
    )

    print("\n========== TOP 10 CELLULES AIS ==========")
    print(
        ais_hotspots.head(10)[
            ["lat", "lon", "presence_hours", "active_flags"]
        ].to_string(index=False)
    )

    print("\n========== TOP 10 CELLULES SAR ==========")
    print(
        sar_hotspots.head(10)[
            ["lat", "lon", "category", "detections"]
        ].to_string(index=False)
    )

    print("\n========== ÉVOLUTION MENSUELLE ==========")
    print(
        monthly[
            [
                "date",
                "ais_presence_hours",
                "sar_total_detections",
                "sar_unmatched_rate_pct"
            ]
        ].to_string(index=False)
    )

    print("\nAnalyse terminée. Fichiers enregistrés dans data/processed/.")


if __name__ == "__main__":
    main()
