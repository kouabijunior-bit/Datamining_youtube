# Exercices et corrigés — TP Data Mining YouTube

Les requêtes sont écrites pour **MySQL 8**. Les différences avec SQLite sont indiquées quand il y en a.

---

## Exercice A — Requêtes SQL (étape 4)

**A1.** Nombre de relevés et date du dernier relevé pour chaque vidéo suivie.

```sql
SELECT v.title, COUNT(*) AS nb_releves, MAX(s.collected_at) AS dernier_releve
FROM videos v
JOIN video_stats s ON s.video_id = v.video_id
WHERE v.tracked = 1
GROUP BY v.video_id, v.title
ORDER BY nb_releves DESC;
```

**A2.** Les 5 vidéos ayant le meilleur taux d'engagement, à partir du **dernier** relevé de chaque vidéo.

```sql
SELECT v.title,
       s.view_count, s.like_count, s.comment_count,
       ROUND((s.like_count + s.comment_count) / s.view_count, 4) AS engagement
FROM videos v
JOIN video_stats s ON s.video_id = v.video_id
WHERE s.collected_at = (SELECT MAX(s2.collected_at)
                        FROM video_stats s2
                        WHERE s2.video_id = v.video_id)
  AND s.view_count > 0
ORDER BY engagement DESC
LIMIT 5;
```
*SQLite : écrire `(s.like_count + s.comment_count) * 1.0 / s.view_count` pour éviter la division entière.*

**A3.** Nombre de vues gagnées par chaque vidéo suivie au cours des 10 dernières minutes.

```sql
SELECT v.title, MAX(s.view_count) - MIN(s.view_count) AS vues_gagnees_10min
FROM videos v
JOIN video_stats s ON s.video_id = v.video_id
WHERE v.tracked = 1
  AND s.collected_at >= UTC_TIMESTAMP() - INTERVAL 10 MINUTE
GROUP BY v.video_id, v.title
ORDER BY vues_gagnees_10min DESC;
```
*SQLite : remplacer la condition de date par `s.collected_at >= datetime('now', '-10 minutes')`.*
*Pourquoi `UTC_TIMESTAMP()` et pas `NOW()` ? Parce que les dates sont stockées en UTC, alors que l'horloge du serveur est à l'heure de Brazzaville (UTC+1).*

**A4.** Répartition des sentiments par vidéo (après l'étape 5).

```sql
SELECT v.title, c.sentiment, COUNT(*) AS nb
FROM comments c
JOIN videos v ON v.video_id = c.video_id
WHERE c.sentiment IS NOT NULL
GROUP BY v.title, c.sentiment
ORDER BY v.title, nb DESC;
```

**A5.** Nombre moyen de vues par catégorie, uniquement pour les catégories d'au moins 3 vidéos.

```sql
SELECT v.category_id, COUNT(*) AS nb_videos, ROUND(AVG(s.view_count)) AS vues_moyennes
FROM videos v
JOIN video_stats s ON s.video_id = v.video_id
WHERE s.collected_at = (SELECT MAX(collected_at) FROM video_stats s2 WHERE s2.video_id = v.video_id)
GROUP BY v.category_id
HAVING COUNT(*) >= 3
ORDER BY vues_moyennes DESC;
```
*Rappel des codes : 10 = Musique, 17 = Sport, 23 = Humour, 24 = Divertissement, 25 = Actualités, 27 = Éducation.*

---

## Exercice B — Une nouvelle variable : l'heure de Brazzaville

Les heures de publication sont en UTC. Ajoutez dans `donnees.py` (fonction `table_videos`) une variable `heure_brazzaville`, puis affichez la médiane des vues par heure locale.

**Corrigé** — dans `table_videos()`, après la ligne `v["heure_publication"] = ...` :
```python
v["heure_brazzaville"] = (v["published_at"] + pd.Timedelta(hours=1)).dt.hour
```
Puis dans un script ou une console Python :
```python
from donnees import table_videos
v = table_videos()
print(v.groupby("heure_brazzaville")["view_count"].median().sort_values(ascending=False))
```
**À discuter :** avec 50 vidéos, chaque heure ne contient que 1 à 5 vidéos. La conclusion « il faut publier à 18 h » n'est pas statistiquement solide. Il faudrait collecter plusieurs jours de tendances.

---

## Exercice C — Améliorer le modèle de sentiment

1. Lancer `python 05_sentiment.py` et noter le F1 macro (`macro avg`).
2. Remplir 50 lignes de `data/a_annoter.csv` (colonne `sentiment`).
3. Relancer le script et comparer.
4. Remplacer `LogisticRegression` par `LinearSVC` ou `MultinomialNB` et comparer.

**Corrigé (étape 4)** — dans `05_sentiment.py` :
```python
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
...
("clf", LinearSVC(C=0.5, class_weight="balanced")),
```
Attention : `LinearSVC` n'a pas de `predict_proba`. Pour l'utiliser aussi dans le collecteur, il faut l'envelopper :
```python
from sklearn.calibration import CalibratedClassifierCV
("clf", CalibratedClassifierCV(LinearSVC(C=0.5, class_weight="balanced"))),
```

**Éléments de réponse attendus :**
- Les commentaires annotés venant des **vraies vidéos** améliorent surtout la reconnaissance des expressions locales et de l'argot.
- La classe **neutre** est souvent la mieux reconnue (questions, salutations) ; **positif** et **négatif** se confondent quand il y a de l'ironie (« Bravo, encore une vidéo inutile »).
- Avec un petit corpus, les différences entre algorithmes sont faibles : **la quantité et la qualité des annotations comptent plus que le choix du modèle.**

---

## Exercice D — Ajouter un graphique au dashboard

Ajouter un graphique « Engagement moyen par sentiment dominant » : pour chaque vidéo, trouver le sentiment le plus fréquent, puis afficher le taux d'engagement moyen par sentiment dominant.

**Corrigé** — dans `dashboard.py`, à la fin du bloc `# ---------- sentiment ----------` (à l'intérieur du `if`) :
```python
        dominant = (c.dropna(subset=["sentiment"])
                    .groupby("video_id")["sentiment"]
                    .agg(lambda x: x.value_counts().idxmax())
                    .rename("sentiment_dominant").reset_index())
        eng = (v.merge(dominant, on="video_id")
                .groupby("sentiment_dominant")["taux_engagement"].mean().reset_index())
        graphique(st, px.bar(eng, x="sentiment_dominant", y="taux_engagement",
                             title="Engagement moyen selon le sentiment dominant"))
```
**À discuter :** une différence d'engagement entre groupes n'est pas une relation de cause à effet. Les vidéos polémiques peuvent avoir des commentaires négatifs **et** beaucoup d'engagement.

---

## Exercice E — Clustering : comparer k = 2, 3, 4

Lancer `06_clustering.py --k 2`, puis `--k 3`, puis `--k 4`. Pour chaque k, nommer les groupes.

**Éléments de réponse :**
- **k = 2** sépare généralement les vidéos « encore en croissance » des vidéos « saturées ».
- **k = 3** fait apparaître les vidéos **explosives** (récentes, très rapides).
- **k = 4** isole parfois une seule vidéo atypique : le groupe n'a plus de sens général.
- La silhouette n'est qu'une aide : on choisit le k que l'on sait **interpréter et expliquer**.
- **Sans standardisation**, la vitesse (des milliers de vues par minute) écraserait les taux d'engagement (de l'ordre de 0,05) : K-Means ne regarderait presque qu'une seule variable.

---

## Exercice F — Démontrer la fuite de données

Dans `07_prediction.py`, ajouter `like_count` aux variables explicatives et relancer.

**Corrigé :**
```python
X["log_likes"] = np.log1p(v["like_count"].fillna(0))
```
Le R² bondit au-dessus de **0,9** (contre environ 0,3 à 0,4 sans les likes). Le modèle paraît excellent, mais il est **inutilisable** : pour prédire les vues d'une vidéo qui vient d'être publiée, on ne connaît pas encore ses likes, qui augmentent **en même temps** que les vues. C'est une fuite de données (*data leakage*).

---

## Réponses aux questions du guide (sélection)

**Étape 1**
- Les vues sont sous `statistics.viewCount`, de type **texte** (`"1791513"`) : il faut les convertir en entier.
- `PT4M13S` = 4 min 13 s = **253 secondes**.
- On stocke en UTC pour pouvoir comparer des dates venant de pays et de serveurs différents sans ambiguïté.

**Étape 3**
- Le **sel** empêche de retrouver l'auteur en calculant le hash de tous les identifiants YouTube connus (attaque par dictionnaire).
- Les commentaires coûtent 1 unité **par vidéo** ; les compteurs, 1 unité pour **50 vidéos**. Les relever moins souvent économise le quota.

**Étape 4**
- Les vues suivent une distribution très asymétrique (quelques vidéos à des millions, beaucoup à quelques milliers). Spearman travaille sur les **rangs** et n'est pas dominé par ces valeurs extrêmes.

**Étape 6**
- Le logarithme réduit l'écart entre une vidéo à 10 vues/min et une à 5 000 vues/min ; sans lui, K-Means séparerait surtout une ou deux vidéos extrêmes.

**Étape 7**
- Un **R² négatif** signifie que le modèle prédit moins bien que la simple moyenne.
- On prédit `log10(vues)` car l'erreur relative compte plus que l'erreur absolue : se tromper de 10 000 vues est grave pour une vidéo à 5 000 vues, négligeable pour une vidéo à 2 millions.

**Étape 8**
- La moyenne est elle-même tirée vers le haut par le pic qu'on cherche à détecter ; la **médiane** n'est presque pas influencée.
- Un utilisateur très actif et passionné peut être signalé comme suspect : c'est un **faux positif**. Une alerte doit toujours être vérifiée par un humain.
- Plus de la moitié des commentateurs ne déclarent pas de pays : cette variable est **très incomplète et biaisée** (seuls certains profils la remplissent). On ne peut pas en tirer la répartition géographique réelle du public.
