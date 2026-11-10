
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.cluster import DBSCAN

# ============================================================
# 1. CHARGEMENT
# ============================================================

df = pd.read_csv("maritime_cells_eda.csv")

print("Nombre de cellules :", len(df))

# ============================================================
# 2. PREPARATION DES COORDONNEES
# ============================================================

coordinates = np.radians(
    df[["lat", "lon"]].to_numpy()
)

# Rayon moyen de la Terre en kilomètres
EARTH_RADIUS_KM = 6371.0088

# Rayon de recherche : 16 km
EPS_KM = 12

# Conversion kilomètres -> radians
eps_radians = EPS_KM / EARTH_RADIUS_KM

# ============================================================
# 3. MODELE DBSCAN
# ============================================================

model = DBSCAN(
    eps=eps_radians,
    min_samples=4,
    metric="haversine",
    algorithm="ball_tree"
)

df["cluster"] = model.fit_predict(coordinates)


# =====================================================
# DIAGNOSTIC INTERNE DBSCAN
# =====================================================

print("\n========== DIAGNOSTIC INTERNE ==========")

print("Version scikit-learn :", __import__("sklearn").__version__)
print("Min samples réel :", model.min_samples)
print("EPS réel (km) :", EPS_KM)

# Nombre de points centraux par cluster
core_indices = model.core_sample_indices_

core_df = df.iloc[core_indices]

print("\nPoints centraux par cluster :")
print(
    core_df.groupby("cluster").size()
)

# Vérification détaillée du cluster 2
cluster_2_indices = df.index[df["cluster"] == 2].tolist()

print("\nIndices du cluster 2 :", cluster_2_indices)

print("\nPoints centraux appartenant au cluster 2 :")

print(
    core_df[core_df["cluster"] == 2][
        ["lat", "lon"]
    ].to_string(index=True)
)

# Nombre de voisins dans le rayon pour chaque cellule
from sklearn.neighbors import NearestNeighbors

neighborhood = NearestNeighbors(
    radius=EPS_KM / EARTH_RADIUS_KM,
    metric="haversine",
    algorithm="ball_tree"
)

neighborhood.fit(coordinates)

neighbor_indices = neighborhood.radius_neighbors(
    coordinates,
    return_distance=False
)

print("\nNombre de voisins dans le rayon :")

for index in cluster_2_indices:
    print(
        f"Index {index} | "
        f"Coordonnées : {df.loc[index, 'lat']}, "
        f"{df.loc[index, 'lon']} | "
        f"Voisins : {len(neighbor_indices[index])}"
    )

# =====================================================
# VALIDATION DE LA COHERENCE DBSCAN
# =====================================================

print("\n========== VALIDATION DBSCAN ==========")

print("EPS :", EPS_KM, "km")
print("MIN_SAMPLES :", 4)

print("\nNombre de cellules par cluster :")
print(df["cluster"].value_counts().sort_index())

# Vérification de l'unicité des coordonnées
duplicates = df.duplicated(
    subset=["lat", "lon"]
).sum()

print("\nCoordonnées dupliquées :", duplicates)

# Vérification du groupe suspect
print("\nCellules du cluster 2 :")

print(
    df[df["cluster"] == 2][
        ["lat", "lon", "presence_hours"]
    ].to_string(index=False)
)
# ============================================================
# 4. EVALUATION DES CLUSTERS
# ============================================================

clustered = df[df["cluster"] != -1]
noise = df[df["cluster"] == -1]

number_clusters = clustered["cluster"].nunique()

print("\n========== RESULTATS DBSCAN ==========")
print("Nombre de clusters :", number_clusters)
print("Cellules regroupées :", len(clustered))
print("Cellules isolées (bruit) :", len(noise))

if len(df) > 0:
    print(
        "Pourcentage de cellules isolées :",
        round(len(noise) / len(df) * 100, 2),
        "%"
    )

# ============================================================
# 5. CARACTERISATION DES CLUSTERS
# ============================================================

if number_clusters > 0:

    summary = (
        clustered.groupby("cluster")
        .agg(
            cells=("lat", "count"),
            total_presence_hours=("presence_hours", "sum"),
            total_vessel_id_counts=("vessel_ids_sum", "sum"),
            mean_presence_hours=("presence_hours", "mean"),
            max_presence_hours=("presence_hours", "max"),
            mean_flags=("flags_count", "mean"),
            center_lat=("lat", "mean"),
            center_lon=("lon", "mean")
        )
        .sort_values(
            "total_presence_hours",
            ascending=False
        )
    )

    print("\n========== CLUSTERS ==========")
    print(summary.to_string())

    summary.to_csv("maritime_clusters_summary.csv")

# ============================================================
# 6. VISUALISATION
# ============================================================

plt.figure(figsize=(13, 9))

# Bruit : cellules non affectées à un cluster
plt.scatter(
    noise["lon"],
    noise["lat"],
    c="lightgray",
    s=12,
    label="Cellules isolées",
    alpha=0.6
)

# Clusters
if number_clusters > 0:

    scatter = plt.scatter(
        clustered["lon"],
        clustered["lat"],
        c=clustered["cluster"],
        cmap="turbo",
        s=15 + np.log1p(
            clustered["presence_hours"]
        ) * 8,
        alpha=0.85,
        edgecolors="black",
        linewidths=0.2,
        label="Clusters"
    )

    plt.colorbar(scatter, label="Identifiant du cluster")

plt.title("THE INVISIBLE FLEET - DBSCAN maritime clustering")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.legend()
plt.grid(alpha=0.2)

plt.tight_layout()
plt.savefig("maritime_dbscan_clusters.png", dpi=250)
plt.show()

# ============================================================
# 7. EXPORT
# ============================================================

df.to_csv("maritime_cells_clustered.csv", index=False)

print("\nAnalyse DBSCAN terminée.")
print("Fichiers générés :")
print("- maritime_cells_clustered.csv")
print("- maritime_clusters_summary.csv")
print("- maritime_dbscan_clusters.png")
