
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

BASE = Path("data/processed/eez_validation")
OUTPUT = BASE / "boundary_cells"

OUTPUT.mkdir(parents=True, exist_ok=True)

HALF = 0.05


def export_cells(filename, output_name):

    df = pd.read_csv(OUTPUT / filename)

    geometries = [
        box(
            row.lon - HALF,
            row.lat - HALF,
            row.lon + HALF,
            row.lat + HALF,
        )
        for row in df.itertuples()
    ]

    cells = gpd.GeoDataFrame(
        df,
        geometry=geometries,
        crs="EPSG:4326",
    )

    destination = OUTPUT / output_name

    cells.to_file(destination, driver="GeoJSON")

    print(f"{output_name}: {len(cells)} cellules exportées")


export_cells(
    "ais_outside_centers.csv",
    "ais_outside_cells.geojson",
)

export_cells(
    "sar_outside_centers.csv",
    "sar_outside_cells.geojson",
)

print("\nExport terminé.")
