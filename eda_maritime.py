
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ============================================================
# 1. CHARGEMENT DES DONNEES
# ============================================================

df = pd.read_csv("presence_senegal_2024_01.csv")

print("\n========== STRUCTURE DES DONNEES ==========")
print(df.head())
print("\nDimensions :", df.shape)
print("\nColonnes :", df.columns.tolist())

# ============================================================
# 2. NETTOYAGE
# ============================================================

df.columns = df.columns.str.strip()

df["hours"] = pd.to_numeric(df["hours"], errors="coerce")
df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
df["vesselIDs"] = pd.to_numeric(df["vesselIDs"], errors="coerce")

df = df.dropna(subset=["lat", "lon", "hours"])

# ============================================================
# 3. STATISTIQUES GENERALES
# ============================================================

print("\n========== STATISTIQUES ==========")

print("Nombre d'observations :", len(df))
print("Nombre de cellules :", df[["lat", "lon"]].drop_duplicates().shape[0])
print("Nombre de pavillons :", df["flag"].nunique())
print("Heures totales :", df["hours"].sum())

print("\nDistribution des heures :")
print(df["hours"].describe(percentiles=[0.25, 0.50, 0.75, 0.90, 0.95, 0.99]))

# ============================================================
# 4. TOP PAVILLONS
# ============================================================

flags = (
    df.groupby("flag", dropna=False)["hours"]
    .sum()
    .sort_values(ascending=False)
    .head(15)
)

print("\n========== TOP 15 PAVILLONS ==========")
print(flags)

plt.figure(figsize=(12, 6))
flags.sort_values().plot(kind="barh")
plt.title("THE INVISIBLE FLEET - Presence maritime par pavillon")
plt.xlabel("Heures de présence")
plt.tight_layout()
plt.savefig("top_flags.png", dpi=200)
plt.show()

# ============================================================
# 5. ANALYSE DES HOTSPOTS
# ============================================================

cells = (
    df.groupby(["lat", "lon"], as_index=False)
    .agg(
        presence_hours=("hours", "sum"),
        vessel_ids_sum=("vesselIDs", "sum"),
        records=("hours", "count"),
        flags_count=("flag", "nunique")
    )
)

print("\n========== TOP 20 HOTSPOTS ==========")
print(
    cells.sort_values("presence_hours", ascending=False)
    .head(20)
)

# ============================================================
# 6. DISTRIBUTION SPATIALE
# ============================================================

plt.figure(figsize=(12, 8))

scatter = plt.scatter(
    cells["lon"],
    cells["lat"],
    c=np.log1p(cells["presence_hours"]),
    s=10 + np.log1p(cells["presence_hours"]) * 10,
    cmap="inferno",
    alpha=0.8
)

plt.colorbar(scatter, label="Log(heures de présence + 1)")
plt.title("THE INVISIBLE FLEET - Distribution spatiale des hotspots")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.grid(alpha=0.2)

plt.tight_layout()
plt.savefig("maritime_hotspots.png", dpi=250)
plt.show()

# ============================================================
# 7. EXPORT DES CELLULES
# ============================================================

cells.to_csv("maritime_cells_eda.csv", index=False)

print("\nAnalyse terminée.")
print("Fichiers générés :")
print("- top_flags.png")
print("- maritime_hotspots.png")
print("- maritime_cells_eda.csv")
