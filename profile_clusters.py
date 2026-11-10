
import pandas as pd

# Donnees agregees avec les identifiants DBSCAN
cells = pd.read_csv("maritime_cells_clustered.csv")

# Donnees AIS originales
raw = pd.read_csv("presence_senegal_2024_01.csv")

# =====================================================
# 1. STATISTIQUES GEOGRAPHIQUES ET MARITIMES
# =====================================================

summary = (
    cells[cells["cluster"] != -1]
    .groupby("cluster")
    .agg(
        cells=("lat", "count"),
        presence_hours=("presence_hours", "sum"),
        vessel_id_counts=("vessel_ids_sum", "sum"),
        mean_hours=("presence_hours", "mean"),
        median_hours=("presence_hours", "median"),
        max_hours=("presence_hours", "max"),
        mean_flags=("flags_count", "mean"),
        center_lat=("lat", "mean"),
        center_lon=("lon", "mean"),
        min_lat=("lat", "min"),
        max_lat=("lat", "max"),
        min_lon=("lon", "min"),
        max_lon=("lon", "max")
    )
    .sort_values("presence_hours", ascending=False)
)

print("\n========== PROFIL DES CLUSTERS ==========")
print(summary.round(2).to_string())

summary.to_csv("cluster_geographic_profiles.csv")

# =====================================================
# 2. RATTACHEMENT DES CLUSTERS AUX OBSERVATIONS AIS
# =====================================================

raw["lat"] = pd.to_numeric(raw["lat"], errors="coerce")
raw["lon"] = pd.to_numeric(raw["lon"], errors="coerce")

raw = raw.dropna(subset=["lat", "lon"])

cluster_lookup = cells[["lat", "lon", "cluster"]]

raw = raw.merge(
    cluster_lookup,
    on=["lat", "lon"],
    how="left"
)

# =====================================================
# 3. PAVILLONS DOMINANTS PAR CLUSTER
# =====================================================

flag_profiles = (
    raw[raw["cluster"] != -1]
    .groupby(["cluster", "flag"], dropna=False)
    .agg(
        presence_hours=("hours", "sum"),
        records=("hours", "count"),
        vessel_id_counts=("vesselIDs", "sum")
    )
    .reset_index()
    .sort_values(
        ["cluster", "presence_hours"],
        ascending=[True, False]
    )
)

print("\n========== TOP 10 PAVILLONS PAR CLUSTER ==========")

for cluster_id in sorted(flag_profiles["cluster"].unique()):

    print(f"\n--- CLUSTER {cluster_id} ---")

    print(
        flag_profiles[
            flag_profiles["cluster"] == cluster_id
        ]
        .head(10)
        .to_string(index=False)
    )

flag_profiles.to_csv(
    "cluster_flag_profiles.csv",
    index=False
)

# =====================================================
# 4. CELLULES ISOLEES
# =====================================================

noise = cells[cells["cluster"] == -1]

print("\n========== CELLULES ISOLEES ==========")
print("Nombre :", len(noise))
print(
    noise[
        ["lat", "lon", "presence_hours", "flags_count"]
    ].to_string(index=False)
)

# =====================================================
# 5. EXPORT
# =====================================================

raw.to_csv("maritime_observations_with_clusters.csv", index=False)

print("\nAnalyse des profils terminee.")
print("Fichiers generes :")
print("- cluster_geographic_profiles.csv")
print("- cluster_flag_profiles.csv")
print("- maritime_observations_with_clusters.csv")
