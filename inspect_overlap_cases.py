from pathlib import Path
import pandas as pd

BASE = Path("data/processed/eez_validation/boundary_overlap")

for source in ["ais", "sar"]:
    print("\n" + "=" * 70)
    print(f"SOURCE : {source.upper()}")
    print("=" * 70)

    df = pd.read_csv(BASE / f"{source}_overlap.csv")

    # Centroïdes extérieurs
    outside = df[df["center_inside"] == False].copy()

    print("\n1. CELLULES AVEC 0 % DE RECOUVREMENT")
    print(
        outside[outside["overlap_pct"] < 0.01][
            ["lat", "lon", "overlap_pct", "outside_distance_m"]
        ].to_string(index=False)
    )

    print("\n2. CELLULES AUTOUR DE LA LATITUDE 13.1")
    print(
        df[df["lat"].between(13.0, 13.2)][
            ["lat", "lon", "center_inside", "overlap_pct"]
        ]
        .sort_values(["lat", "lon"])
        .to_string(index=False)
    )

    print("\n3. CELLULES EXTÉRIEURES LES PLUS PROCHES DE LA ZEE")
    print(
        outside.sort_values("outside_distance_m").head(15)[
            ["lat", "lon", "overlap_pct", "outside_distance_m"]
        ].to_string(index=False)
    )