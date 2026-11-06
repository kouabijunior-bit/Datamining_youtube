"""
ÉTAPE 4 — Analyse exploratoire (EDA).

Questions :
  - Quelles catégories font le plus de vues ?
  - À quelle heure publier ?
  - Les likes suivent-ils les vues ? (corrélations)
  - Quelle vidéo grandit le plus vite en ce moment ?

Lancement :  python 04_exploration.py   (les graphiques vont dans figures/)
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from donnees import croissance, releves, table_commentaires, table_videos

os.makedirs("figures", exist_ok=True)
pd.set_option("display.width", 140)
v = table_videos()
if v.empty:
    raise SystemExit("Base vide : lance d'abord les étapes 2 et 3.")

print("=" * 70, "\n1. APERÇU DES DONNÉES\n" + "=" * 70)
nb_com = len(table_commentaires())
print(f"{len(v)} vidéos | {len(releves())} relevés | {nb_com} commentaires")
print("\nValeurs manquantes (%) :")
print(
    (
        v[
            [
                "view_count",
                "like_count",
                "comment_count",
                "subscriber_count",
                "duration_seconds",
            ]
        ]
        .isna()
        .mean()
        * 100
    )
    .round(1)
    .to_string()
)

print("\nStatistiques descriptives :")
print(
    v[
        [
            "view_count",
            "like_count",
            "comment_count",
            "duree_min",
            "taux_engagement",
            "subscriber_count",
        ]
    ]
    .describe()
    .round(3)
    .to_string()
)

print("\n" + "=" * 70, "\n2. PAR CATÉGORIE\n" + "=" * 70)
cat = (
    v.groupby("categorie")
    .agg(
        nb_videos=("video_id", "count"),
        vues_moyennes=("view_count", "mean"),
        engagement_moyen=("taux_engagement", "mean"),
    )
    .sort_values("vues_moyennes", ascending=False)
)
print(cat.round(4).to_string())
cat["vues_moyennes"].plot.barh(
    figsize=(8, 5), color="#3b6ea8", title="Vues moyennes par catégorie"
)
plt.xlabel("Vues")
plt.tight_layout()
plt.savefig("figures/vues_par_categorie.png", dpi=120)
plt.close()

print("\n" + "=" * 70, "\n3. HEURE DE PUBLICATION (UTC)\n" + "=" * 70)
h = v.groupby("heure_publication")["view_count"].median()
print(h.round(0).to_string())

print("\n" + "=" * 70, "\n4. CORRÉLATIONS\n" + "=" * 70)
cols = [
    "view_count",
    "like_count",
    "comment_count",
    "subscriber_count",
    "duree_min",
    "nb_tags",
    "age_heures",
]
corr = v[cols].corr(method="spearman").round(2)
print(corr.to_string())
fig, ax = plt.subplots(figsize=(7, 6))
im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(len(cols)), cols, rotation=45, ha="right")
ax.set_yticks(range(len(cols)), cols)
for i in range(len(cols)):
    for j in range(len(cols)):
        ax.text(j, i, corr.iloc[i, j], ha="center", va="center", fontsize=8)
fig.colorbar(im)
ax.set_title("Corrélations (Spearman)")
plt.tight_layout()
plt.savefig("figures/correlations.png", dpi=120)
plt.close()

print("\n" + "=" * 70, "\n5. TEMPS RÉEL : QUI GRANDIT LE PLUS VITE ?\n" + "=" * 70)
g = croissance().dropna(subset=["vues_par_minute"])
if g.empty:
    print("Pas encore assez de relevés : laisse tourner le collecteur quelques minutes.")
else:
    derniere = g.groupby("video_id").tail(1).merge(v[["video_id", "title"]], on="video_id")
    print(
        derniere.sort_values("vues_par_minute", ascending=False)[
            ["title", "view_count", "vues_par_minute"]
        ]
        .head(10)
        .round(1)
        .to_string(index=False)
    )
    s = releves().merge(v[["video_id", "tracked"]], on="video_id")
    s = s[s["tracked"] == 1]
    fig, ax = plt.subplots(figsize=(10, 5))
    for vid, d in s.groupby("video_id"):
        ax.plot(d["collected_at"], d["view_count"], marker=".", label=vid)
    ax.set_yscale("log")
    ax.set_title("Évolution des vues (vidéos suivies, échelle log)")
    ax.set_ylabel("Vues")
    ax.legend(fontsize=6, ncol=2)
    plt.tight_layout()
    plt.savefig("figures/evolution_vues.png", dpi=120)
    plt.close()

print("\nGraphiques enregistrés dans le dossier figures/")
