
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

BASE = Path("data/processed/eez_validation")
OUTPUT = BASE / "boundary_overlap"

OUTPUT.mkdir(parents=True, exist_ok=True)

EEZ_FILE = Path("data/raw/boundaries/eez_v12.gpkg")
AIS_FILE = BASE / "ais_cell_validation.csv"
SAR_FILE = BASE / "sar_cell_validation.csv"

CELL_SIZE = 0.1
HALF = CELL_SIZE / 2
PROJECTED_CRS = "EPSG:32628"

# --------------------------------------------------
# ZEE
# --------------------------------------------------

eez_gdf = gpd.read_file(
    EEZ_FILE,
    layer="eez_v12"
)

eez_gdf = eez_gdf.loc[
    eez_gdf["MRGID"] == 8371
].to_crs(PROJECTED_CRS)

eez = eez_gdf.geometry.union_all()

# --------------------------------------------------
# ANALYSE DES CELLULES
# --------------------------------------------------

def analyze(source, file):

    df = pd.read_csv(file)

    # Une seule ligne par position géographique
    cells = df[["lat", "lon"]].drop_duplicates().copy()

    geometries = [
        box(
            lon - HALF,
            lat - HALF,
            lon + HALF,
            lat + HALF
        )
        for lat, lon in zip(cells["lat"], cells["lon"])
    ]

    grid = gpd.GeoDataFrame(
        cells,
        geometry=geometries,
        crs="EPSG:4326"
    ).to_crs(PROJECTED_CRS)

    records = []

    for _, row in grid.iterrows():

        cell = row.geometry
        center = cell.centroid

        intersection = cell.intersection(eez)

        overlap_pct = (
            intersection.area / cell.area * 100
        )

        center_inside = eez.covers(center)

        distance = (
            0 if center_inside
            else center.distance(eez)
        )

        records.append({
            "lat": row["lat"],
            "lon": row["lon"],
            "center_inside": center_inside,
            "overlap_pct": overlap_pct,
            "outside_distance_m": distance,
            "intersection_area_km2": (
                intersection.area / 1_000_000
            ),
        })

    result = pd.DataFrame(records)

    result["overlap_class"] = pd.cut(
        result["overlap_pct"],
        bins=[-0.001, 0, 25, 50, 75, 100.001],
        labels=[
            "outside",
            "marginal_0_25",
            "partial_25_50",
            "majority_50_75",
            "almost_inside_75_100",
        ]
    )

    result.to_csv(
        OUTPUT / f"{source.lower()}_overlap.csv",
        index=False
    )

    print("\n" + "=" * 60)
    print(f"SOURCE : {source}")
    print("=" * 60)

    print("\nClassification du chevauchement :")
    print(result["overlap_class"].value_counts().to_string())

    outside = result.loc[~result["center_inside"]]

    print("\nCentroïdes extérieurs :")
    print("Nombre :", len(outside))

    if len(outside):
        print(
            "\nPourcentage de recouvrement :"
        )
        print(
            outside["overlap_pct"].describe().round(2)
        )

        print(
            "\nDistance à la frontière (mètres) :"
        )
        print(
            outside["outside_distance_m"].describe().round(2)
        )

        print("\nCellules les moins couvertes :")
        print(
            outside.sort_values("overlap_pct")[
                [
                    "lat",
                    "lon",
                    "overlap_pct",
                    "outside_distance_m",
                ]
            ].head(20).to_string(index=False)
        )

    return result


ais = analyze("AIS", AIS_FILE)
sar = analyze("SAR", SAR_FILE)

print("\nAnalyse du chevauchement terminée.")
print("Résultats :", OUTPUT)
