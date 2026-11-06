"""
ÉTAPE 7 — Prédiction : combien de vues ? virale ou non ?

  A. Régression     : prédire log(vues) — Random Forest vs régression linéaire
  B. Classification : prédire « virale » (vues > 2 × abonnés de la chaîne)

Attention : on n'utilise PAS les likes ni les commentaires comme variables,
car ils sont une conséquence des vues (ce serait de la « fuite de données »).

Lancement :  python 07_prediction.py
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import classification_report, mean_absolute_error, r2_score
from sklearn.model_selection import cross_val_predict, KFold, StratifiedKFold

from donnees import table_videos

v = table_videos().dropna(subset=["view_count", "duration_seconds"])
if len(v) < 15:
    raise SystemExit(
        f"Seulement {len(v)} vidéos : il en faut au moins 15 "
        "(étape 2 avec la tendance ou --search)."
    )

v["log_abonnes"] = np.log1p(v["subscriber_count"].fillna(v["subscriber_count"].median()))
v["log_age"] = np.log1p(v["age_heures"])
v["log_duree"] = np.log1p(v["duration_seconds"])
v["est_weekend"] = v["published_at"].dt.dayofweek >= 5
X = pd.concat(
    [
        v[
            [
                "log_abonnes",
                "log_age",
                "log_duree",
                "nb_tags",
                "longueur_titre",
                "heure_publication",
                "est_weekend",
            ]
        ],
        pd.get_dummies(v["categorie"], prefix="cat"),
    ],
    axis=1,
).astype(float)
print(f"{len(v)} vidéos, {X.shape[1]} variables explicatives\n")

# ---------- A. Régression ----------
y = np.log10(v["view_count"].clip(lower=1))
cv = KFold(5, shuffle=True, random_state=0)
print("A. RÉGRESSION — prédire log10(vues)")
for nom, m in [
    ("Régression linéaire", LinearRegression()),
    ("Random Forest", RandomForestRegressor(300, min_samples_leaf=2, random_state=0)),
]:
    p = cross_val_predict(m, X, y, cv=cv)
    print(
        f"  {nom:20} R² = {r2_score(y, p):.3f} "
        f"| erreur moyenne = ×{10 ** mean_absolute_error(y, p):.2f}"
    )
rf = RandomForestRegressor(300, min_samples_leaf=2, random_state=0).fit(X, y)
imp = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\n  Variables les plus importantes :")
print(imp.head(8).round(3).to_string())

# ---------- B. Classification ----------
v["virale"] = (v["view_count"] > 2 * v["subscriber_count"].fillna(np.inf)).astype(int)
print(
    f"\nB. CLASSIFICATION — vidéo « virale » (vues > 2 × abonnés) : "
    f"{v['virale'].sum()} virales sur {len(v)}"
)
if v["virale"].nunique() < 2 or v["virale"].value_counts().min() < 3:
    print(
        "  Pas assez d'exemples dans chaque classe ; "
        "change la définition de « virale » (ex. > abonnés)."
    )
else:
    clf = RandomForestClassifier(
        300, min_samples_leaf=2, class_weight="balanced", random_state=0
    )
    n = min(5, v["virale"].value_counts().min())
    p = cross_val_predict(
        clf, X, v["virale"], cv=StratifiedKFold(n, shuffle=True, random_state=0)
    )
    print(
        classification_report(
            v["virale"], p, target_names=["non virale", "virale"], zero_division=0
        )
    )

print(
    "Questions : quelle variable compte le plus ? "
    "Le modèle est-il meilleur qu'une simple moyenne (R² > 0) ?"
)
