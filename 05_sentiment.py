"""
ÉTAPE 5 — Classification du sentiment des commentaires (TF-IDF + régression logistique).

  1. entraîne le modèle sur data/corpus_sentiment.csv (commentaires annotés à la main)
  2. l'évalue (validation croisée + matrice de confusion)
  3. prédit le sentiment de tous les commentaires de la base
  4. exporte 100 commentaires réels dans data/a_annoter.csv (exercice d'annotation)

Une fois le modèle enregistré, le collecteur (étape 3) prédit le sentiment
des nouveaux commentaires en temps réel.

Lancement :  python 05_sentiment.py
"""

import os

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import FeatureUnion, Pipeline
from sqlalchemy import bindparam, update

from db import comments, get_engine
from donnees import table_commentaires, table_videos
from pretraitement import MODEL_PATH, nettoyer, predire

# ---------- 1. corpus d'entraînement ----------
corpus = pd.read_csv("data/corpus_sentiment.csv")
# Si les étudiants ont annoté des commentaires réels, on les ajoute
if os.path.exists("data/a_annoter.csv"):
    ann = pd.read_csv("data/a_annoter.csv").dropna(subset=["sentiment"])
    ann = ann[ann["sentiment"].isin(["positif", "negatif", "neutre"])]
    if len(ann):
        print(f"+ {len(ann)} commentaires annotés par les étudiants ajoutés au corpus")
        corpus = pd.concat([corpus, ann[["texte", "sentiment"]]], ignore_index=True)

X = corpus["texte"].map(nettoyer)
y = corpus["sentiment"]
print(f"Corpus : {len(corpus)} phrases\n{y.value_counts().to_string()}\n")

# Deux familles de variables : les mots (et paires de mots) + des morceaux de
# 2 à 5 lettres, plus robustes aux fautes d'orthographe et au lingala.
modele = Pipeline(
    [
        (
            "tfidf",
            FeatureUnion(
                [
                    ("mots", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
                    (
                        "lettres",
                        TfidfVectorizer(
                            analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True
                        ),
                    ),
                ]
            ),
        ),
        ("clf", LogisticRegression(max_iter=3000, class_weight="balanced", C=2)),
    ]
)

# ---------- 2. évaluation (validation croisée à 5 plis) ----------
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
pred = cross_val_predict(modele, X, y, cv=cv)
print("Évaluation (validation croisée) :")
print(classification_report(y, pred, zero_division=0))
labels = ["negatif", "neutre", "positif"]
print("Matrice de confusion (lignes = vrai, colonnes = prédit) :")
print(
    pd.DataFrame(
        confusion_matrix(y, pred, labels=labels), index=labels, columns=labels
    ).to_string()
)

erreurs = corpus[pred != y].assign(predit=pred[pred != y])
if len(erreurs):
    print("\nExemples d'erreurs :")
    print(erreurs.head(8).to_string(index=False))

# ---------- 3. entraînement final + prédiction sur la base ----------
modele.fit(X, y)
os.makedirs("models", exist_ok=True)
joblib.dump(modele, MODEL_PATH)
print(f"\nModèle enregistré : {MODEL_PATH}")

coefs = modele.named_steps["clf"].coef_
noms = modele.named_steps["tfidf"].get_feature_names_out()
est_mot = [n.startswith("mots__") for n in noms]
for i, classe in enumerate(modele.named_steps["clf"].classes_):
    top = [j for j in coefs[i].argsort()[::-1] if est_mot[j]][:8]
    print(f"Mots les plus liés à « {classe} » : {', '.join(noms[j][6:] for j in top)}")

c = table_commentaires()
if c.empty:
    print("\nAucun commentaire en base : lance le collecteur (étape 3).")
    raise SystemExit
labs, scores = predire(modele, c["text"].tolist())
c["sentiment"], c["sentiment_score"] = labs, scores
eng = get_engine()
with eng.begin() as conn:
    conn.execute(
        update(comments)
        .where(comments.c.comment_id == bindparam("cid"))
        .values(sentiment=bindparam("s"), sentiment_score=bindparam("sc")),
        [{"cid": a, "s": b, "sc": d} for a, b, d in zip(c["comment_id"], labs, scores)],
    )
print(f"\n{len(c)} commentaires classés :")
print(
    c["sentiment"]
    .value_counts(normalize=True)
    .mul(100)
    .round(1)
    .astype(str)
    .add(" %")
    .to_string()
)

# Sentiment moyen par vidéo (score : positif = +1, neutre = 0, négatif = -1)
c["score_num"] = c["sentiment"].map({"positif": 1, "neutre": 0, "negatif": -1})
v = table_videos()[["video_id", "title", "taux_engagement"]]
par_video = (
    c.groupby("video_id")
    .agg(nb=("comment_id", "count"), sentiment_moyen=("score_num", "mean"))
    .reset_index()
    .merge(v, on="video_id")
)
print("\nSentiment moyen par vidéo :")
print(
    par_video.sort_values("sentiment_moyen", ascending=False)[
        ["title", "nb", "sentiment_moyen", "taux_engagement"]
    ]
    .round(3)
    .to_string(index=False)
)
print(
    "\nCorrélation sentiment moyen / engagement :",
    round(
        par_video["sentiment_moyen"].corr(par_video["taux_engagement"], method="spearman"), 3
    ),
)

# ---------- 4. fichier d'annotation pour les étudiants ----------
if not os.path.exists("data/a_annoter.csv"):
    ech = c.sample(min(100, len(c)), random_state=1)[["text", "sentiment"]]
    ech = ech.rename(columns={"text": "texte", "sentiment": "prediction_modele"})
    ech["sentiment"] = ""
    ech.to_csv("data/a_annoter.csv", index=False)
    print(
        "\nFichier data/a_annoter.csv créé : remplissez la colonne 'sentiment' "
        "(positif / negatif / neutre) puis relancez ce script."
    )
