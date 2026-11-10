
# from pathlib import Path
# import geopandas as gpd
# import pyogrio

# FILES = [
#     Path("data/raw/boundaries/eez_v12.gpkg"),
#     Path("data/raw/boundaries/eez_boundaries_v12.gpkg"),
# ]

# for file in FILES:
#     print("\n" + "=" * 65)
#     print(f"FICHIER : {file}")
#     print("=" * 65)

#     if not file.exists():
#         print("FICHIER INTROUVABLE")
#         continue

#     layers = pyogrio.list_layers(file)
#     print("\nCouches disponibles :")
#     print(layers)

#     for layer_info in layers:
#         layer_name = layer_info[0]

#         print(f"\n--- COUCHE : {layer_name} ---")

#         gdf = gpd.read_file(file, layer=layer_name)

#         print("Nombre d'entités :", len(gdf))
#         print("CRS :", gdf.crs)
#         print("Géométrie :", gdf.geom_type.value_counts().to_dict())
#         print("Colonnes :", list(gdf.columns))

#         print("\nAperçu des données :")
#         print(gdf.drop(columns="geometry").head(3).to_string())

#         print("\nGéométries nulles :", gdf.geometry.isna().sum())
#         print("Géométries invalides :", (~gdf.geometry.is_valid).sum())



import geopandas as gpd

path = "data/raw/boundaries/eez_v12.gpkg"

gdf = gpd.read_file(path, layer="eez_v12")

# Recherche selon plusieurs attributs possibles
mask = (
    gdf["GEONAME"].str.contains("Senegal", case=False, na=False)
    | gdf["TERRITORY1"].str.contains("Senegal", case=False, na=False)
    | gdf["SOVEREIGN1"].str.contains("Senegal", case=False, na=False)
    | gdf["ISO_TER1"].eq("SEN")
    | gdf["ISO_SOV1"].eq("SEN")
    | gdf["MRGID"].eq(8371)
)

candidates = gdf.loc[mask].copy()

columns = [
    "MRGID",
    "GEONAME",
    "TERRITORY1",
    "SOVEREIGN1",
    "ISO_TER1",
    "ISO_SOV1",
    "POL_TYPE",
    "AREA_KM2",
]

print("\n========== CANDIDATS ZEE SENEGAL ==========")
print(candidates[columns].to_string(index=False))

print("\n========== INFORMATIONS GEOGRAPHIQUES ==========")

for _, row in candidates.iterrows():
    geom = row.geometry

    print(f"\nMRGID : {row['MRGID']}")
    print(f"Nom : {row['GEONAME']}")
    print(f"Superficie déclarée : {row['AREA_KM2']} km²")
    print(f"Type : {geom.geom_type}")
    print(f"Valide : {geom.is_valid}")
    print(f"Emprise : {geom.bounds}")
