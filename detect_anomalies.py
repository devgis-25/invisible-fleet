
import pandas as pd
import numpy as np

import matplotlib.pyplot as plt

from sklearn.ensemble import IsolationForest

# =====================================================
# 1. CHARGEMENT DES DONNEES
# =====================================================

df = pd.read_csv("maritime_cells_eda.csv")

print("Nombre de cellules :", len(df))

# =====================================================
# 2. PREPARATION DES VARIABLES
# =====================================================

features = [
    "presence_hours",
    "vessel_ids_sum",
    "records",
    "flags_count"
]

X = df[features].copy()

# Vérification des valeurs manquantes
print("\nValeurs manquantes :")
print(X.isnull().sum())

X = X.fillna(0)

# =====================================================
# 3. TRANSFORMATION LOGARITHMIQUE
# =====================================================

# Nos variables sont fortement asymétriques.
# log1p réduit l'influence des valeurs extrêmes.

X_log = np.log1p(X)

# =====================================================
# 4. ENTRAINEMENT ISOLATION FOREST
# =====================================================

model = IsolationForest(
    n_estimators=300,
    contamination=0.02,
    random_state=42,
    n_jobs=-1
)

model.fit(X_log)

# =====================================================
# 5. DETECTION DES ANOMALIES
# =====================================================

df["anomaly_prediction"] = model.predict(X_log)

# -1 = anomalie
#  1 = observation normale

df["anomaly_score"] = model.decision_function(X_log)

df["is_anomaly"] = (
    df["anomaly_prediction"] == -1
)

# =====================================================
# 6. STATISTIQUES
# =====================================================

anomalies = df[df["is_anomaly"]].copy()

normal = df[~df["is_anomaly"]]

print("\n========== RESULTATS ISOLATION FOREST ==========")

print("Cellules totales :", len(df))
print("Cellules normales :", len(normal))
print("Cellules atypiques :", len(anomalies))

print(
    "Pourcentage atypique :",
    round(len(anomalies) / len(df) * 100, 2),
    "%"
)

# =====================================================
# 7. TOP CELLULES ATYPIQUES
# =====================================================

anomalies = anomalies.sort_values(
    "anomaly_score",
    ascending=True
)

print("\n========== TOP 20 CELLULES ATYPIQUES ==========")

print(
    anomalies[
        [
            "lat",
            "lon",
            "presence_hours",
            "vessel_ids_sum",
            "records",
            "flags_count",
            "anomaly_score"
        ]
    ].head(20).to_string(index=False)
)

# =====================================================
# 8. VISUALISATION GEOGRAPHIQUE
# =====================================================

plt.figure(figsize=(13, 9))

plt.scatter(
    normal["lon"],
    normal["lat"],
    c="lightgray",
    s=15,
    alpha=0.5,
    label="Cellules normales"
)

plt.scatter(
    anomalies["lon"],
    anomalies["lat"],
    c=anomalies["anomaly_score"],
    cmap="Reds_r",
    s=30 + np.log1p(
        anomalies["presence_hours"]
    ) * 8,
    edgecolors="black",
    linewidths=0.3,
    label="Cellules atypiques"
)

plt.colorbar(
    label="Score Isolation Forest"
)

plt.title(
    "THE INVISIBLE FLEET - Spatial Anomaly Detection"
)

plt.xlabel("Longitude")
plt.ylabel("Latitude")

plt.legend()
plt.grid(alpha=0.2)

plt.tight_layout()

plt.savefig(
    "maritime_anomalies.png",
    dpi=250
)

plt.show()

# =====================================================
# 9. EXPORT
# =====================================================

df.to_csv(
    "maritime_cells_anomalies.csv",
    index=False
)

print("\nAnalyse terminée.")
print("Fichiers générés :")
print("- maritime_cells_anomalies.csv")
print("- maritime_anomalies.png")
