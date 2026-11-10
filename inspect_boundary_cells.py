
from pathlib import Path

import geopandas as gpd
import pandas as pd

BASE = Path("data/processed/eez_validation")

AIS_FILE = BASE / "ais_cell_validation.csv"
SAR_FILE = BASE / "sar_cell_validation.csv"

OUTPUT = BASE / "boundary_cells"

OUTPUT.mkdir(parents=True, exist_ok=True)


def inspect(source, path):

    df = pd.read_csv(path)

    outside = df.loc[
        ~df["center_inside_eez"]
    ].copy()

    inside = df.loc[
        df["center_inside_eez"]
    ].copy()

    print("\n" + "=" * 65)
    print(f"SOURCE : {source}")
    print("=" * 65)

    print("Nombre de cellules :", len(df))
    print("Centroïdes intérieurs :", len(inside))
    print("Centroïdes extérieurs :", len(outside))

    print("\nRépartition des cellules extérieures :")

    print(
        outside.groupby("cell_relation")
        .size()
        .to_string()
    )

    if source == "AIS":
        print("\nTop 20 cellules extérieures par observations :")

        print(
            outside.sort_values(
                "observations",
                ascending=False
            )[
                ["lat", "lon", "observations"]
            ].head(20).to_string(index=False)
        )

    else:
        print("\nCellules SAR extérieures :")

        print(
            outside.sort_values(
                "observations",
                ascending=False
            )[
                ["lat", "lon", "category", "observations"]
            ].head(30).to_string(index=False)
        )

    outside.to_csv(
        OUTPUT / f"{source.lower()}_outside_centers.csv",
        index=False,
    )

    # Export des centroïdes pour inspection QGIS
    points = gpd.GeoDataFrame(
        outside,
        geometry=gpd.points_from_xy(
            outside["lon"],
            outside["lat"]
        ),
        crs="EPSG:4326",
    )

    points.to_file(
        OUTPUT / f"{source.lower()}_outside_centers.geojson",
        driver="GeoJSON",
    )

    print("\nFichiers exportés dans :", OUTPUT)


inspect("AIS", AIS_FILE)
inspect("SAR", SAR_FILE)

print("\nINSPECTION TERMINEE.")
