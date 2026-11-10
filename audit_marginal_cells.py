from pathlib import Path
import pandas as pd

BASE = Path("data/processed")

overlap_dir = BASE / "eez_validation" / "boundary_overlap"

ais = pd.read_csv(BASE / "ais_presence_2024-01_2026-10.csv")
sar = pd.read_csv(BASE / "sar_detections_2024-01_2026-10.csv")

ais_geo = pd.read_csv(overlap_dir / "ais_overlap.csv")
sar_geo = pd.read_csv(overlap_dir / "sar_overlap.csv")

# Cellules avec un recouvrement inférieur à 1 %
marginal_ais = ais_geo[ais_geo["overlap_pct"] < 1]
marginal_sar = sar_geo[sar_geo["overlap_pct"] < 1]

def audit(source, data, marginal, value_column):
    print("\n" + "=" * 65)
    print(source)
    print("=" * 65)

    for _, cell in marginal.iterrows():
        lat, lon = cell["lat"], cell["lon"]

        subset = data[
            (data["lat"] == lat) &
            (data["lon"] == lon)
        ]

        print(f"\nCellule : ({lat}, {lon})")
        print(f"Recouvrement : {cell['overlap_pct']:.4f} %")
        print(f"Observations : {len(subset)}")

        if value_column in subset.columns:
            print(
                f"Total {value_column} : "
                f"{subset[value_column].sum():,.0f}"
            )

        if "date" in subset.columns:
            print(
                "Période :",
                subset["date"].min(),
                "->",
                subset["date"].max()
            )

audit("AIS", ais, marginal_ais, "hours")
audit("SAR", sar, marginal_sar, "detections")



print("\n" + "=" * 65)
print("BILAN GLOBAL DES CELLULES MARGINALES")
print("=" * 65)

for name, data, geo, value in [
    ("AIS", ais, ais_geo, "hours"),
    ("SAR", sar, sar_geo, "detections"),
]:
    marginal = geo[geo["overlap_pct"] < 1]

    print(f"\n{name}")
    print("Cellules sous 1 % :", len(marginal))
    print("Observations concernées :")

    merged = data.merge(
        marginal[["lat", "lon"]],
        on=["lat", "lon"],
        how="inner"
    )

    print("Nombre :", len(merged))
    print("Valeur cumulée :", merged[value].sum())
    print("Pourcentage des observations :",
          round(len(merged) / len(data) * 100, 6), "%")