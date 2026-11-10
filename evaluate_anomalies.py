
import pandas as pd
import numpy as np

from sklearn.ensemble import IsolationForest

# ==========================================
# 1. CHARGEMENT
# ==========================================

df = pd.read_csv("maritime_cells_eda.csv")

features = [
    "presence_hours",
    "vessel_ids_sum",
    "records",
    "flags_count"
]

X = np.log1p(df[features].fillna(0))

# ==========================================
# 2. COMPARAISON DES SEUILS
# ==========================================

contamination_values = [0.01, 0.02, 0.03, 0.05]

results = []

for contamination in contamination_values:

    model = IsolationForest(
        n_estimators=300,
        contamination=contamination,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X)

    predictions = model.predict(X)
    scores = model.decision_function(X)

    df[f"anomaly_{int(contamination * 100)}"] = (
        predictions == -1
    )

    results.append({
        "contamination": contamination,
        "anomalies": int((predictions == -1).sum()),
        "percentage": round(
            (predictions == -1).mean() * 100, 2
        )
    })

print("\n========== SENSIBILITE DU MODELE ==========")

print(pd.DataFrame(results).to_string(index=False))

# ==========================================
# 3. STABILITE DES DETECTIONS
# ==========================================

print("\n========== CELLULES DETECTEES A CHAQUE SEUIL ==========")

for col in [
    "anomaly_1",
    "anomaly_2",
    "anomaly_3",
    "anomaly_5"
]:
    print(col, ":", int(df[col].sum()))

# Cellules détectées dans toutes les configurations
df["stable_anomaly"] = df[
    ["anomaly_1", "anomaly_2", "anomaly_3", "anomaly_5"]
].all(axis=1)

stable = df[df["stable_anomaly"]].copy()

print("\nAnomalies stables :", len(stable))

print(
    stable[
        ["lat", "lon", "presence_hours",
         "vessel_ids_sum", "records", "flags_count"]
    ].to_string(index=False)
)

# ==========================================
# 4. EXPORT
# ==========================================

df.to_csv(
    "maritime_anomaly_sensitivity.csv",
    index=False
)

stable.to_csv(
    "maritime_stable_anomalies.csv",
    index=False
)

print("\nFichiers générés :")
print("- maritime_anomaly_sensitivity.csv")
print("- maritime_stable_anomalies.csv")
