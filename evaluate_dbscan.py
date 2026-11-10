
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors

# =====================================================
# 1. CHARGEMENT
# =====================================================

df = pd.read_csv("maritime_cells_eda.csv")

coordinates = np.radians(
    df[["lat", "lon"]].to_numpy()
)

EARTH_RADIUS_KM = 6371.0088

# =====================================================
# 2. COURBE DES DISTANCES K-PLUS-PROCHES
# =====================================================

MIN_SAMPLES = 4

neighbors = NearestNeighbors(
    n_neighbors=MIN_SAMPLES,
    metric="haversine",
    algorithm="ball_tree"
)

neighbors.fit(coordinates)

distances, _ = neighbors.kneighbors()

k_distances = np.sort(
    distances[:, -1] * EARTH_RADIUS_KM
)

plt.figure(figsize=(12, 6))
plt.plot(k_distances)

plt.title("DBSCAN - Courbe des distances aux 4e voisins")
plt.xlabel("Cellules classées par distance")
plt.ylabel("Distance au 4e voisin (km)")
plt.grid(alpha=0.3)

plt.tight_layout()
plt.savefig("dbscan_k_distance.png", dpi=250)
plt.show()

# =====================================================
# 3. COMPARAISON DES PARAMETRES
# =====================================================

results = []

for eps_km in [8, 10, 12, 14, 16]:

    for min_samples in [4, 5]:

        model = DBSCAN(
            eps=EPS_KM / EARTH_RADIUS_KM,
            min_samples=MIN_SAMPLES,
            metric="haversine",
            algorithm="ball_tree"
        )

        labels = model.fit_predict(coordinates)

        clusters = set(labels) - {-1}

        noise_count = np.sum(labels == -1)

        results.append({
            "eps_km": eps_km,
            "min_samples": min_samples,
            "clusters": len(clusters),
            "noise_cells": int(noise_count),
            "noise_percent": round(
                noise_count / len(df) * 100, 2
            )
        })

results_df = pd.DataFrame(results)

print("\n========== COMPARAISON DBSCAN ==========")
print(results_df.to_string(index=False))

results_df.to_csv(
    "dbscan_parameter_comparison.csv",
    index=False
)

print("\nAnalyse terminée.")
print("Fichiers :")
print("- dbscan_k_distance.png")
print("- dbscan_parameter_comparison.csv")
