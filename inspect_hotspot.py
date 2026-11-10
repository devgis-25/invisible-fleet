
import pandas as pd

df = pd.read_csv("presence_senegal_2024_01.csv")

# Cellule dominante : coordonnées arrondies à 0,1 degré
hotspot = df[
    (df["lat"].round(1) == 14.7) &
    (df["lon"].round(1) == -17.4)
].copy()

print("\n========== CELLULE DOMINANTE ==========")
print("Nombre d'enregistrements :", len(hotspot))
print("Heures cumulées :", hotspot["hours"].sum())
print("Pavillons :", hotspot["flag"].nunique())

print("\nDétail des enregistrements :")
print(
    hotspot.sort_values("hours", ascending=False)
    .to_string(index=False)
)

print("\n========== CONTRIBUTION PAR PAVILLON ==========")
print(
    hotspot.groupby("flag", dropna=False)["hours"]
    .sum()
    .sort_values(ascending=False)
    .to_string()
)

print("\n========== OBSERVATION INDIVIDUELLE MAXIMALE ==========")
print(df.loc[df["hours"].idxmax()].to_string())
