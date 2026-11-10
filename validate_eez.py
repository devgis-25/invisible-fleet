
from pathlib import Path
import json

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box

# ============================================================
# CONFIGURATION
# ============================================================

EEZ_FILE = Path("data/raw/boundaries/eez_v12.gpkg")
AIS_FILE = Path("data/processed/ais_presence_2024-01_2026-10.csv")
SAR_FILE = Path("data/processed/sar_detections_2024-01_2026-10.csv")

OUTPUT_DIR = Path("data/processed/eez_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EEZ_MRGID = 8371
CELL_SIZE = 0.1
HALF_CELL = CELL_SIZE / 2

# ============================================================
# 1. CHARGEMENT DE LA ZEE
# ============================================================

print("\nChargement de la géométrie de référence...")

eez_data = gpd.read_file(EEZ_FILE, layer="eez_v12")

senegal = eez_data.loc[
    eez_data["MRGID"] == EEZ_MRGID
].copy()

if len(senegal) != 1:
    raise ValueError(
        f"Une seule ZEE attendue pour MRGID {EEZ_MRGID}. "
        f"Résultat : {len(senegal)}"
    )

eez = senegal.geometry.iloc[0]

if eez.is_empty or not eez.is_valid:
    raise ValueError("La géométrie de la ZEE est invalide.")

print("ZEE :", senegal["GEONAME"].iloc[0])
print("Superficie déclarée :", senegal["AREA_KM2"].iloc[0], "km²")
print("CRS :", eez_data.crs)
print("Emprise :", eez.bounds)

# ============================================================
# 2. FONCTION DE VALIDATION DES CELLULES
# ============================================================

def validate_cells(df, source, group_columns):
    """
    Agrège les observations par cellule et vérifie :

    - si le centroïde appartient à la ZEE ;
    - si la cellule entière est couverte ;
    - si la cellule intersecte la ZEE.

    Les coordonnées GFW sont traitées comme les centres
    des cellules de 0.1 degré.
    """

    aggregated = (
        df.groupby(group_columns, dropna=False)
        .size()
        .reset_index(name="observations")
    )

    if "lat" not in aggregated.columns or "lon" not in aggregated.columns:
        raise ValueError(
            f"Colonnes lat/lon absentes pour {source}"
        )

    results = []

    for _, row in aggregated.iterrows():

        lat = float(row["lat"])
        lon = float(row["lon"])

        center = Point(lon, lat)

        # Emprise approximative de la cellule GFW
        cell = box(
            lon - HALF_CELL,
            lat - HALF_CELL,
            lon + HALF_CELL,
            lat + HALF_CELL,
        )

        center_inside = eez.covers(center)
        cell_intersects = eez.intersects(cell)
        cell_fully_inside = eez.covers(cell)

        if cell_fully_inside:
            relation = "fully_inside"
        elif cell_intersects:
            relation = "boundary_intersection"
        else:
            relation = "outside"

        results.append({
            **row.to_dict(),
            "source": source,
            "center_inside_eez": center_inside,
            "cell_relation": relation,
            "cell_intersects_eez": cell_intersects,
            "cell_fully_inside_eez": cell_fully_inside,
            "geometry": center,
        })

    return gpd.GeoDataFrame(
        results,
        geometry="geometry",
        crs="EPSG:4326",
    )


# ============================================================
# 3. CHARGEMENT DES DONNEES AIS ET SAR
# ============================================================

print("\nChargement AIS et SAR...")

ais = pd.read_csv(AIS_FILE)
sar = pd.read_csv(SAR_FILE)

print("AIS observations :", len(ais))
print("SAR observations :", len(sar))

# ============================================================
# 4. VALIDATION AIS
# ============================================================

print("\nValidation spatiale AIS...")

ais_cells = validate_cells(
    ais,
    source="AIS",
    group_columns=["lat", "lon"],
)

# ============================================================
# 5. VALIDATION SAR
# ============================================================

print("\nValidation spatiale SAR...")

sar_cells = validate_cells(
    sar,
    source="SAR",
    group_columns=["lat", "lon", "category"],
)

# ============================================================
# 6. RAPPORT STATISTIQUE
# ============================================================

def build_report(gdf, original_count, source):

    center_inside = gdf["center_inside_eez"]
    intersects = gdf["cell_intersects_eez"]
    fully_inside = gdf["cell_fully_inside_eez"]

    return {
        "source": source,
        "observations_total": int(original_count),
        "unique_cells": int(len(gdf)),

        "centers_inside": int(center_inside.sum()),
        "centers_outside": int((~center_inside).sum()),

        "cells_fully_inside": int(fully_inside.sum()),
        "cells_intersecting_eez": int(intersects.sum()),
        "cells_outside": int((~intersects).sum()),

        "observations_in_cells_with_center_inside": int(
            gdf.loc[center_inside, "observations"].sum()
        ),

        "observations_in_cells_intersecting_eez": int(
            gdf.loc[intersects, "observations"].sum()
        ),

        "observations_in_cells_outside": int(
            gdf.loc[~intersects, "observations"].sum()
        ),

        "observations_in_cells_with_center_outside_but_intersecting": int(
            gdf.loc[(~center_inside) & intersects, "observations"].sum()
        ),
    }


ais_report = build_report(ais_cells, len(ais), "AIS")
sar_report = build_report(sar_cells, len(sar), "SAR")

report = {
    "reference": {
        "dataset": "Marine Regions World EEZ v12",
        "mrid": EEZ_MRGID,
        "name": "Senegalese Exclusive Economic Zone",
        "crs": "EPSG:4326",
        "cell_size_degrees": CELL_SIZE,
    },
    "ais": ais_report,
    "sar": sar_report,
}

# ============================================================
# 7. EXPORTS
# ============================================================

print("\nExportation des résultats...")

ais_cells.drop(columns="geometry").to_csv(
    OUTPUT_DIR / "ais_cell_validation.csv",
    index=False,
)

sar_cells.drop(columns="geometry").to_csv(
    OUTPUT_DIR / "sar_cell_validation.csv",
    index=False,
)

ais_cells.to_file(
    OUTPUT_DIR / "ais_cell_validation.geojson",
    driver="GeoJSON",
)

sar_cells.to_file(
    OUTPUT_DIR / "sar_cell_validation.geojson",
    driver="GeoJSON",
)

with open(
    OUTPUT_DIR / "eez_validation_report.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(report, f, indent=4, ensure_ascii=False)

# ============================================================
# 8. AFFICHAGE
# ============================================================

for source_report in [ais_report, sar_report]:

    print("\n" + "=" * 55)
    print("SOURCE :", source_report["source"])
    print("=" * 55)

    for key, value in source_report.items():
        if key != "source":
            print(f"{key:55s}: {value}")

print("\nFichiers produits dans :", OUTPUT_DIR)
print("VALIDATION GEOGRAPHIQUE TERMINEE.")
