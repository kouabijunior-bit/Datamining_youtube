"""
ÉTAPE 6 — Clustering des vidéos selon leur profil de croissance (K-Means).

Variables (calculées à partir des relevés en temps réel) :
  - vitesse   : vues par minute sur la dernière période
  - accel     : la vitesse augmente-t-elle ou diminue-t-elle ?
  - engagement, likes/vues, commentaires/vues
  - age       : âge de la vidéo (log)

Lancement :  python 06_clustering.py --k 3
"""

import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy import update

from db import get_engine, videos
from donnees import croissance, table_videos

parser = argparse.ArgumentParser()
parser.add_argument(
    "--k",
    type=int,
    default=3,
    help="nombre de groupes (0 = choix automatique par la silhouette)",
)
args = parser.parse_args()
os.makedirs("figures", exist_ok=True)

g = croissance().dropna(subset=["vues_par_minute"])
v = table_videos()
v = v[v["tracked"] == 1]
if g.empty or g.groupby("video_id").size().max() < 3:
    raise SystemExit(
        "Il faut au moins 4 relevés par vidéo : laisse tourner le collecteur un peu plus."
    )


def profil(d: pd.DataFrame) -> pd.Series:
    d = d.sort_values("collected_at")
    # YouTube retire parfois des vues (fraude) : une vitesse négative est ramenée à 0
    d = d.assign(vues_par_minute=d["vues_par_minute"].clip(lower=0))
    moitie = max(1, len(d) // 2)
    debut, fin = (
        d["vues_par_minute"].iloc[:moitie].mean(),
        d["vues_par_minute"].iloc[moitie:].mean(),
    )
    return pd.Series({"vitesse": fin, "accel": (fin - debut) / (debut + 1)})


feat = g.groupby("video_id").apply(profil, include_groups=False).reset_index()
feat = feat.merge(
    v[
        [
            "video_id",
            "title",
            "taux_engagement",
            "like_count",
            "comment_count",
            "view_count",
            "age_heures",
        ]
    ],
    on="video_id",
)
feat["likes_par_vue"] = feat["like_count"] / feat["view_count"]
feat["coms_par_vue"] = feat["comment_count"] / feat["view_count"]
feat["log_vitesse"] = np.log1p(feat["vitesse"].clip(lower=0))
feat["log_age"] = np.log1p(feat["age_heures"])
cols = ["log_vitesse", "accel", "taux_engagement", "likes_par_vue", "coms_par_vue", "log_age"]
feat = feat.dropna(subset=cols)
if len(feat) < 4:
    raise SystemExit("Pas assez de vidéos exploitables pour le clustering (minimum 4).")

Xs = StandardScaler().fit_transform(feat[cols])

# ---------- choix de k : méthode du coude + silhouette ----------
print("k | inertie | silhouette")
res = {}
for k in range(2, min(7, len(feat) // 2 + 1)):
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(Xs)
    res[k] = silhouette_score(Xs, km.labels_)
    print(f"{k} | {km.inertia_:8.1f} | {res[k]:.3f}")
k = args.k or max(res, key=res.get)
print(
    f"\n→ k retenu : {k}  (avec peu de vidéos, la silhouette favorise les grands k : "
    "préférer un k interprétable)"
)

km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(Xs)
feat["cluster"] = km.labels_

# ---------- interprétation ----------
resume = feat.groupby("cluster")[["vitesse", "accel", "taux_engagement", "age_heures"]].mean()
resume["nb_videos"] = feat.groupby("cluster").size()


def nommer(r):
    vmax = resume["vitesse"].max()
    if r["vitesse"] < 0.02 * vmax:
        return "stable / saturée"
    if r["accel"] > 0.2:
        return "en accélération"
    if r["vitesse"] == vmax:
        return "explosive"
    return "croissance modérée"


resume["interpretation"] = resume.apply(nommer, axis=1)
print("\nProfil moyen de chaque groupe :")
print(resume.round(3).to_string())
for c, d in feat.groupby("cluster"):
    print(f"\nGroupe {c} ({resume.loc[c, 'interpretation']}) :")
    for t in d["title"].head(6):
        print("   -", t[:70])

with get_engine().begin() as conn:
    for vid, c in zip(feat["video_id"], feat["cluster"]):
        conn.execute(update(videos).where(videos.c.video_id == vid).values(cluster=int(c)))

# ---------- visualisation en 2D (ACP) ----------
xy = PCA(n_components=2).fit_transform(Xs)
fig, ax = plt.subplots(figsize=(8, 6))
for c in sorted(feat["cluster"].unique()):
    m = feat["cluster"] == c
    ax.scatter(xy[m, 0], xy[m, 1], s=60, label=f"{c} : {resume.loc[c, 'interpretation']}")
ax.set_title("Clusters de vidéos (projection ACP)")
ax.legend()
plt.tight_layout()
plt.savefig("figures/clusters.png", dpi=120)
print("\nGraphique : figures/clusters.png — clusters enregistrés dans la table videos")
