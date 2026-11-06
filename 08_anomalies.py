"""
ÉTAPE 8 — Détection d'anomalies.

  A. Hausses de vues anormales (z-score robuste sur la vitesse de croissance)
     -> vues achetées ? partage massif soudain ?
  B. Commentateurs suspects (Isolation Forest sur des profils ANONYMISÉS)
     -> comptes récents, sans vidéos, qui postent beaucoup, avec des liens...

Lancement :  python 08_anomalies.py
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import bindparam, update

from db import comments, get_engine, utcnow
from donnees import croissance, lire, table_commentaires, table_videos

# ---------- A. pics de vues ----------
print("A. HAUSSES DE VUES ANORMALES\n")
g = croissance().dropna(subset=["vues_par_minute"])
if g.empty:
    print("Pas assez de relevés.")
else:

    def zrobuste(x):
        """z-score robuste : (x - médiane) / MAD. Le plancher évite de diviser
        par ~0 pour les vidéos saturées qui ne gagnent presque plus de vues."""
        med = x.median()
        mad = max((x - med).abs().median() * 1.4826, 0.5 * abs(med), 10)
        return (x - med) / mad

    g["z"] = g.groupby("video_id")["vues_par_minute"].transform(zrobuste)
    # anomalie = vitesse très au-dessus de l'habitude de LA vidéo
    # ET au moins 500 vues d'un coup
    pics = g[(g["z"] > 5) & (g["nouvelles_vues"] >= 500)].merge(
        table_videos()[["video_id", "title"]], on="video_id"
    )
    if pics.empty:
        print("Aucune hausse anormale détectée.")
    else:
        aff = pics.sort_values("z", ascending=False).head(10)
        aff = aff.assign(vues_par_minute=aff["vues_par_minute"].round(0), z=aff["z"].round(1))
        print(
            aff[["collected_at", "title", "nouvelles_vues", "vues_par_minute", "z"]].to_string(
                index=False
            )
        )

# ---------- B. commentateurs suspects ----------
print("\nB. COMMENTATEURS SUSPECTS\n")
c = table_commentaires()
p = lire("commenters")
if c.empty or p.empty:
    raise SystemExit("Pas encore de commentaires / profils : laisse tourner le collecteur.")

c["a_un_lien"] = c["text"].str.contains(r"http|www\.|\.com|\.xyz", case=False, regex=True)
c["majuscules"] = c["text"].apply(lambda t: sum(ch.isupper() for ch in t) / max(len(t), 1))
c["longueur"] = c["text"].str.len()
auteurs = (
    c.groupby("author_hash")
    .agg(
        nb_commentaires=("comment_id", "count"),
        nb_videos_commentees=("video_id", "nunique"),
        part_liens=("a_un_lien", "mean"),
        part_majuscules=("majuscules", "mean"),
        longueur_moy=("longueur", "mean"),
        textes_differents=("text", "nunique"),
    )
    .reset_index()
)
auteurs["taux_repetition"] = 1 - auteurs["textes_differents"] / auteurs["nb_commentaires"]
auteurs = auteurs.merge(p, on="author_hash", how="left")
auteurs["anciennete_jours"] = (
    pd.Timestamp(utcnow()) - pd.to_datetime(auteurs["channel_created_at"])
).dt.days
auteurs["log_abonnes"] = np.log1p(auteurs["subscriber_count"].fillna(0))
auteurs["log_videos"] = np.log1p(auteurs["video_count"].fillna(0))
auteurs["log_anciennete"] = np.log1p(
    auteurs["anciennete_jours"].fillna(auteurs["anciennete_jours"].median())
)

cols = [
    "nb_commentaires",
    "nb_videos_commentees",
    "part_liens",
    "part_majuscules",
    "taux_repetition",
    "log_abonnes",
    "log_videos",
    "log_anciennete",
]
iso = IsolationForest(n_estimators=300, contamination=0.03, random_state=0)
auteurs["suspect"] = iso.fit_predict(auteurs[cols].fillna(0)) == -1
auteurs["score_anomalie"] = -iso.score_samples(auteurs[cols].fillna(0))

print(f"{len(auteurs)} commentateurs analysés, {auteurs['suspect'].sum()} suspects")
print("\nProfil moyen : suspects vs normaux")
print(
    auteurs.groupby("suspect")[
        [
            "nb_commentaires",
            "part_liens",
            "taux_repetition",
            "anciennete_jours",
            "subscriber_count",
            "video_count",
        ]
    ]
    .mean()
    .round(2)
    .to_string()
)

susp = auteurs[auteurs["suspect"]].sort_values("score_anomalie", ascending=False)
exemples = (
    c[c["author_hash"].isin(susp["author_hash"])].drop_duplicates("text")["text"].head(8)
)
print("\nExemples de commentaires d'auteurs suspects :")
for t in exemples:
    print("  -", t[:90])

ids_suspects = set(susp["author_hash"])
with get_engine().begin() as conn:
    conn.execute(
        update(comments)
        .where(comments.c.comment_id == bindparam("cid"))
        .values(is_suspect=bindparam("s")),
        [
            {"cid": cid, "s": int(a in ids_suspects)}
            for cid, a in zip(c["comment_id"], c["author_hash"])
        ],
    )

print("\nPays DÉCLARÉS par les commentateurs (beaucoup ne déclarent rien) :")
print(
    p["country"]
    .fillna("non déclaré")
    .value_counts(normalize=True)
    .mul(100)
    .round(1)
    .head(8)
    .to_string()
)
print("\nRésultats enregistrés (colonne comments.is_suspect).")
