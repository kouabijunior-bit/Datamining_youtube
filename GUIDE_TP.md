# TP Data Mining — Analyse de vidéos YouTube en temps réel

**Niveau :** Licence 3 / Master 1 · **Durée :** 4 heures · **Langage :** Python + MySQL
**Thème :** suivre en direct des vidéos populaires au Congo, analyser leur croissance, le sentiment des commentaires et l'audience.

---

## 0. Présentation

### Objectif général
Construire un pipeline complet de data mining sur de **vraies données** : collecte en temps réel via une API, stockage en base, préparation, analyse, apprentissage automatique et tableau de bord.

### Compétences visées
À la fin du TP, l'étudiant sait :
1. interroger une API REST et lire une réponse JSON ;
2. distinguer **collecte périodique** et **streaming continu** ;
3. stocker une série temporelle dans MySQL ;
4. calculer des variables dérivées (engagement, vitesse de croissance) ;
5. appliquer les grandes techniques : exploration, classification, clustering, régression, détection d'anomalies ;
6. évaluer un modèle et en discuter les limites ;
7. respecter les règles d'éthique et de protection des données personnelles.

### Prérequis
Python (fonctions, listes, dictionnaires), Pandas, SQL de base, notions de classification supervisée.

### Architecture

```
 YouTube Data API v3 ──► Collecteur Python ──► MySQL ──► Data mining (scikit-learn) ──► Dashboard Streamlit
 (ou simulateur DEMO)    (toutes les 60 s)      │        exploration, sentiment,          (actualisé
                                                │        clustering, prédiction,           toutes les 30 s)
 YouTube Analytics ─────────────────────────────┘        anomalies
 (âge, genre, pays de TA chaîne)
```

### Organisation des 4 heures

| Horaire | Étape | Résultat attendu |
|---|---|---|
| 0 h 00 – 0 h 20 | Présentation, API et JSON | Comprendre le pipeline |
| 0 h 20 – 0 h 50 | Étape 0 et 1 : installation, clé API, test | `01_test_api.py` fonctionne |
| 0 h 50 – 1 h 10 | Étapes 2 et 3 : choix des vidéos, lancement du collecteur | Les données arrivent en base |
| 1 h 10 – 1 h 40 | Étape 4 : exploration + requêtes SQL | Premiers constats |
| 1 h 40 – 2 h 20 | Étape 5 : sentiment des commentaires | Modèle entraîné et évalué |
| 2 h 20 – 2 h 50 | Étape 6 : clustering | Groupes de vidéos interprétés |
| 2 h 50 – 3 h 20 | Étapes 7 et 8 : prédiction et anomalies | Modèles et alertes |
| 3 h 20 – 3 h 45 | Étape 10 : dashboard | Tableau de bord en direct |
| 3 h 45 – 4 h 00 | Restitution, limites, éthique | Mini-compte rendu |

> **Astuce pour l'enseignant :** lancez le collecteur dès la fin de l'étape 3 et laissez-le tourner pendant tout le TP. Plus il tourne, plus les courbes et le clustering sont intéressants.

---

## 1. Les fichiers du projet

| Fichier | Rôle |
|---|---|
| `GUIDE_TP.md` | Ce guide |
| `EXERCICES_CORRIGES.md` | Exercices et corrigés |
| `requirements.txt` | Bibliothèques Python |
| `.env.example` | Modèle de configuration (à copier en `.env`) |
| `schema.sql` | Création de la base MySQL |
| `db.py` | Connexion et tables |
| `youtube_client.py` | Client de l'API YouTube |
| `simulator.py` | Simulateur hors ligne (mode DEMO) |
| `pretraitement.py` | Nettoyage des textes |
| `donnees.py` | Chargement des tables et variables calculées |
| `01_test_api.py` → `09_demographie.py` | Les étapes du TP |
| `dashboard.py` | Tableau de bord temps réel |
| `data/corpus_sentiment.csv` | 210 commentaires annotés (positif / négatif / neutre) |

---

## Étape 0 — Installation (20 min)

### 0.1 Installer Python et MySQL
- **Python 3.10 ou plus récent** (cocher « Add Python to PATH » à l'installation sous Windows).
- **MySQL 8** (ou XAMPP / WAMP, qui contiennent MySQL). Noter le mot de passe de l'utilisateur `root`.
- Un éditeur : **VS Code** recommandé.

> Pas de MySQL disponible ? Mettez `DB_ENGINE=sqlite` dans `.env` : tout fonctionne sans installation (la base est un simple fichier).

### 0.2 Créer l'environnement Python
Ouvrir le dossier du projet dans VS Code, puis un terminal :

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Linux / macOS**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 0.3 Créer la base MySQL
```bash
mysql -u root -p < schema.sql
```
Si la commande `mysql` n'est pas reconnue : ouvrir `schema.sql` dans MySQL Workbench (ou phpMyAdmin) et l'exécuter.
*(Les scripts Python créent aussi la base et les tables automatiquement si elles n'existent pas.)*

### 0.4 Configurer le projet
Copier `.env.example` en `.env` :
```powershell
copy .env.example .env      # Windows
cp .env.example .env        # Linux / macOS
```
Puis ouvrir `.env` et renseigner au minimum `MYSQL_PASSWORD`.

Vérifier la connexion :
```bash
python db.py
```
Résultat attendu : `Connexion OK` et la liste des 6 tables.

---

## Étape 1 — Obtenir la clé API et tester (15 min)

### 1.1 Créer la clé (gratuite, sans carte bancaire)
1. Aller sur **console.cloud.google.com** et se connecter avec un compte Gmail.
2. En haut : **Sélectionner un projet → Nouveau projet** (nom : `tp-datamining`).
3. Menu **API et services → Bibliothèque** → chercher **YouTube Data API v3** → **Activer**.
4. **API et services → Identifiants → Créer des identifiants → Clé API**.
5. Copier la clé (elle commence par `AIza...`) et la coller dans `.env` :
   ```
   YT_API_KEY=AIzaSy...
   ```

> **Pas d'Internet ou pas encore de clé ?** Laisser `YT_API_KEY=DEMO`. Le simulateur renvoie des données au **même format JSON** que YouTube, avec des compteurs qui augmentent réellement. Tout le TP fonctionne à l'identique.

### 1.2 Le quota
Chaque clé dispose de **10 000 unités gratuites par jour** :

| Requête | Coût |
|---|---|
| Statistiques de 50 vidéos (`videos.list`) | 1 unité |
| Informations de 50 chaînes (`channels.list`) | 1 unité |
| 100 commentaires (`commentThreads.list`) | 1 unité |
| Une recherche par mot-clé (`search.list`) | **100 unités** |

> **Conseil :** une clé par binôme. Avec les réglages par défaut, le collecteur consomme environ 3 000 unités en 24 h.

### 1.3 Tester
```bash
python 01_test_api.py
```
Le script affiche la **réponse JSON brute** d'une vidéo, puis la même vidéo transformée en dictionnaire Python.

**Questions :**
1. Dans le JSON, sous quelle clé se trouvent les vues ? Sont-elles de type nombre ou texte ?
2. Que signifie la durée `PT4M13S` ? Convertissez-la en secondes.
3. Pourquoi faut-il convertir les dates en UTC avant de les stocker ?

---

## Étape 2 — Choisir les vidéos (10 min)

```bash
python 02_choisir_videos.py
```
Le script récupère les **50 vidéos en tendance** du pays défini par `REGION_CODE` (CG = Congo-Brazzaville), les enregistre en base et en sélectionne **15 à suivre en temps réel**.

Autres possibilités :
```bash
python 02_choisir_videos.py --region CD                  # tendances de la RDC
python 02_choisir_videos.py --search "rumba congolaise"  # recherche (coûte 100 unités)
python 02_choisir_videos.py --ids dQw4w9WgXcQ,abc123     # vidéos précises
```
L'identifiant d'une vidéo se trouve dans son lien : `youtube.com/watch?v=`**`dQw4w9WgXcQ`**.

> Si aucune tendance n'est disponible pour votre pays, essayez `--region FR` ou utilisez `--search`.

---

## Étape 3 — Le collecteur en temps réel (10 min, puis il tourne en continu)

```bash
python 03_collecteur_temps_reel.py
```
**Laissez ce terminal ouvert** et ouvrez-en un second (avec `.venv` activé) pour la suite.

À chaque cycle (60 s par défaut), le collecteur :
1. relève les vues, likes et commentaires des vidéos suivies → table `video_stats` ;
2. tous les 10 cycles : récupère les **nouveaux commentaires** sans doublons → table `comments` ;
3. prédit leur **sentiment en direct** (dès que l'étape 5 a été faite) ;
4. récupère le profil **public** des nouveaux auteurs, **anonymisé** → table `commenters` ;
5. met à jour les statistiques des chaînes → table `channels`.

### Collecte périodique ou streaming ?
| | Collecte périodique (ce TP) | Streaming continu |
|---|---|---|
| Principe | On interroge la source à intervalle régulier | La source envoie chaque événement dès qu'il se produit |
| Latence | L'intervalle (ici 60 s) | Quelques millisecondes |
| Exemple | YouTube Data API | Chat d'un live YouTube, flux Bluesky |
| Risque | Rater des événements entre deux relevés | Volume important à absorber |

### Anonymisation
Le nom et l'identifiant des commentateurs **ne sont jamais stockés**. Ils sont remplacés par un *hash* (empreinte irréversible) calculé avec un sel secret (`ANON_SALT`). On peut ainsi compter les commentaires d'un même auteur **sans savoir qui il est**.

**Questions :**
1. Ouvrez `youtube_client.py`, fonction `anonymize`. Pourquoi ajoute-t-on un « sel » avant de calculer le hash ?
2. Dans MySQL, exécutez `SELECT video_id, collected_at, view_count FROM video_stats ORDER BY collected_at DESC LIMIT 20;`. Que constatez-vous ?
3. Pourquoi les commentaires sont-ils relevés moins souvent que les compteurs ?

---

## Étape 4 — Analyse exploratoire (30 min)

```bash
python 04_exploration.py
```
Le script affiche : un aperçu et les valeurs manquantes, les statistiques descriptives, les vues par catégorie, les vues par heure de publication, la matrice de corrélation, et **les vidéos qui grandissent le plus vite en ce moment**.
Les graphiques sont enregistrés dans `figures/`.

### Variables calculées (fichier `donnees.py`)
| Variable | Formule | Intérêt |
|---|---|---|
| `taux_engagement` | (likes + commentaires) / vues | Mesure l'implication du public |
| `vues_par_heure` | vues / âge de la vidéo | Popularité « à âge égal » |
| `vues_par_minute` | nouvelles vues / minutes entre deux relevés | Vitesse **en temps réel** |
| `ratio_vues_abonnes` | vues / abonnés de la chaîne | > 1 : la vidéo dépasse son public habituel |

**Questions :**
1. Pourquoi utilise-t-on la corrélation de **Spearman** plutôt que celle de Pearson ici ? (indice : distribution des vues)
2. Quelle catégorie a le meilleur taux d'engagement ? Est-ce la même que celle qui a le plus de vues ?
3. Relancez le script 10 minutes plus tard. Le classement des vidéos les plus rapides a-t-il changé ?

*(Requêtes SQL : voir l'exercice A dans `EXERCICES_CORRIGES.md`.)*

---

## Étape 5 — Classification du sentiment (40 min)

```bash
python 05_sentiment.py
```

### Démarche
1. **Corpus d'apprentissage** : `data/corpus_sentiment.csv`, 210 commentaires annotés à la main (70 positifs, 70 négatifs, 70 neutres), en français avec quelques expressions en lingala (*mbote*, *merci mingi*, *ezali malamu*, *ezali mabe*).
2. **Nettoyage** (`pretraitement.py`) : minuscules, suppression des accents, des chiffres, remplacement des liens par le mot `lien`.
3. **Vectorisation TF-IDF** sur deux types de variables : les **mots** (et paires de mots) et des **morceaux de 2 à 5 lettres**, plus robustes aux fautes d'orthographe.
4. **Régression logistique** pour classer en positif / négatif / neutre.
5. **Évaluation** par validation croisée à 5 plis : précision, rappel, F1, matrice de confusion.
6. **Prédiction** sur tous les commentaires collectés et calcul du sentiment moyen par vidéo.

Le modèle est enregistré dans `models/sentiment.joblib`. **Redémarrez le collecteur** (Ctrl + C puis relance) : il prédit désormais le sentiment de chaque nouveau commentaire **en temps réel**.

### Exercice d'annotation (fortement recommandé)
Le script crée `data/a_annoter.csv` avec 100 vrais commentaires. Chaque binôme remplit la colonne `sentiment` (positif / negatif / neutre), puis relance `python 05_sentiment.py` : les annotations sont ajoutées au corpus et le modèle est réévalué.

**Questions :**
1. Quelle classe est la mieux reconnue ? Laquelle est la plus confondue, et avec quoi ?
2. Regardez les erreurs affichées. Pourquoi « C'est du lourd ! » est-il difficile pour le modèle ?
3. La précision a-t-elle augmenté après l'ajout de vos annotations ?
4. Le sentiment moyen d'une vidéo est-il corrélé à son taux d'engagement ?

> **Limite importante :** avec 210 phrases, le modèle sert à **apprendre la méthode**, pas à mesurer scientifiquement l'opinion. Un vrai projet demanderait des milliers de commentaires annotés par plusieurs personnes.

---

## Étape 6 — Clustering des vidéos (30 min)

```bash
python 06_clustering.py          # k = 3 groupes
python 06_clustering.py --k 4    # pour comparer
python 06_clustering.py --k 0    # choix automatique par la silhouette
```
> Il faut au moins 4 relevés par vidéo (≈ 5 minutes de collecte).

### Variables utilisées
`log_vitesse` (vues par minute récentes), `accel` (la vitesse augmente-t-elle ?), `taux_engagement`, `likes_par_vue`, `coms_par_vue`, `log_age`.
Elles sont **standardisées** (moyenne 0, écart-type 1) avant K-Means.

Le script affiche l'inertie (méthode du coude) et le score de silhouette pour k = 2 à 6, le profil moyen de chaque groupe avec une interprétation (explosive, croissance modérée, en accélération, stable / saturée), et une projection ACP en 2D dans `figures/clusters.png`.

**Questions :**
1. Pourquoi passe-t-on la vitesse au logarithme avant le clustering ?
2. Que se passerait-il sans standardisation ?
3. Donnez un nom à chacun de vos groupes. Correspond-il à l'interprétation automatique ?
4. Pourquoi la silhouette augmente-t-elle presque toujours avec k quand on a peu de vidéos ?
5. Une vidéo forme parfois un groupe à elle seule. Laquelle ? Comparez avec les résultats de l'étape 8 : que vous apprend ce groupe ?

---

## Étape 7 — Prédiction (20 min)

```bash
python 07_prediction.py
```

**A. Régression** : prédire `log10(vues)` à partir des abonnés, de l'âge, de la durée, du nombre de tags, de la longueur du titre, de l'heure de publication, du week-end et de la catégorie. Comparaison **régression linéaire vs Random Forest** (R² et erreur moyenne).

**B. Classification** : prédire si une vidéo est « virale » (vues > 2 × abonnés de la chaîne).

> **Fuite de données :** on n'utilise **pas** les likes ni les commentaires pour prédire les vues. Ils sont une **conséquence** des vues : le modèle semblerait excellent mais serait inutilisable pour une vidéo qui vient de sortir.

**Questions :**
1. Quelle variable est la plus importante ? Est-ce surprenant ?
2. Que signifie un R² négatif ?
3. Pourquoi prédire `log10(vues)` plutôt que les vues directement ?
4. Avec seulement 50 vidéos, peut-on faire confiance à ces résultats ? Comment avoir plus de données ?

---

## Étape 8 — Détection d'anomalies (15 min)

```bash
python 08_anomalies.py
```

**A. Hausses de vues anormales** : pour chaque vidéo, on compare chaque vitesse à sa vitesse habituelle avec un **z-score robuste** (médiane et écart absolu médian). Une alerte apparaît si z > 5 et au moins 500 nouvelles vues d'un coup.
*En mode DEMO, une vidéo reçoit 60 000 vues d'un coup après 15 minutes de collecte : la retrouverez-vous ?*

**B. Commentateurs suspects** : **Isolation Forest** sur des profils anonymisés : nombre de commentaires, part de liens, part de majuscules, taux de répétition du même texte, ancienneté du compte, abonnés, vidéos publiées.

**Questions :**
1. Pourquoi utiliser la médiane plutôt que la moyenne pour détecter un pic ?
2. Les commentateurs signalés sont-ils tous des spammeurs ? Trouvez un faux positif et expliquez-le.
3. Quel est le pourcentage de commentateurs qui ne déclarent **aucun** pays ? Qu'en concluez-vous sur la variable « pays » ?

---

## Étape 9 (optionnelle) — Démographie : âge, genre, pays (15 min)

YouTube ne fournit l'âge, le genre et le pays de l'audience **que pour une chaîne dont on est propriétaire**, et **uniquement en pourcentages** (jamais personne par personne).

```bash
python 09_demographie.py --jours 90
```
- **Mode DEMO** (sans `client_secret.json`) : démographie simulée.
- **Mode réel** :
  1. Google Cloud Console → activer **YouTube Analytics API** ;
  2. **Identifiants → ID client OAuth → Application de bureau** ;
  3. télécharger le JSON et l'enregistrer sous `client_secret.json` dans le dossier du projet ;
  4. **Écran de consentement OAuth** : ajouter son adresse Gmail comme utilisateur test ;
  5. lancer le script : un navigateur s'ouvre pour se connecter au compte de la chaîne.

> **Idée pour la classe :** créer une chaîne YouTube du cours, y publier une courte vidéo et la partager. Les données démographiques apparaissent après quelques centaines de vues, avec 1 à 2 jours de retard.

**Questions :**
1. Quelle tranche d'âge et quel genre regardent le plus ?
2. Les pays qui regardent le plus sont-ils ceux qui regardent le plus longtemps ?

---

## Étape 10 — Tableau de bord en temps réel (25 min)

Dans un **nouveau terminal** (le collecteur tourne toujours dans le premier) :
```bash
streamlit run dashboard.py
```
Le navigateur s'ouvre sur `http://localhost:8501`. Le tableau de bord s'actualise tout seul et affiche :
- les indicateurs clés (vues totales, relevés, commentaires, % positifs) ;
- l'évolution des vues en direct ;
- la vitesse actuelle et le taux d'engagement par vidéo ;
- le sentiment des commentaires (global et par vidéo) ;
- les clusters (après l'étape 6) et la démographie (après l'étape 9) ;
- les 30 derniers commentaires avec leur sentiment et l'indicateur « suspect ».

**Exercice D** (voir corrigés) : ajouter un graphique.

---

## 11. Éthique et protection des données (à discuter en fin de séance)

1. **Données publiques ≠ données libres d'usage.** Un commentaire public reste une donnée personnelle.
2. **Minimisation** : on ne collecte que ce qui sert l'analyse. Pas de photos de profil, pas de noms.
3. **Anonymisation** dès la collecte (hash salé). Le sel ne doit jamais être publié.
4. **Analyses de groupe uniquement** : « 30 % des commentateurs ont un compte de moins d'un an », jamais « tel utilisateur ».
5. **Ne pas deviner** le genre, l'âge ou l'origine d'une personne à partir de son nom ou de sa photo : c'est peu fiable et contraire à la protection des données.
6. **Respect des conditions de YouTube** : utiliser l'API officielle, respecter le quota, ne pas republier les données brutes.
7. Au Congo, la protection des données personnelles est encadrée par la loi de 2019 : un projet de recherche doit en tenir compte.

---

## 12. Compte rendu attendu (par binôme)

Un document de 3 à 5 pages contenant :
1. la description des données collectées (période, nombre de vidéos, de relevés, de commentaires) ;
2. trois constats issus de l'exploration, chacun appuyé par un graphique ;
3. les résultats du modèle de sentiment (avant et après annotation) et leur interprétation ;
4. les groupes du clustering, nommés et interprétés ;
5. les résultats de la prédiction et une discussion de la fuite de données ;
6. les anomalies détectées et au moins un faux positif expliqué ;
7. les limites du travail et les questions éthiques.

### Barème indicatif

| Compétence | Points |
|---|---|
| Collecte temps réel et base de données fonctionnelles | 3 |
| Requêtes SQL et exploration | 3 |
| Classification du sentiment et annotation | 4 |
| Clustering et interprétation | 3 |
| Prédiction et anomalies | 3 |
| Dashboard | 2 |
| Éthique, limites et qualité du compte rendu | 2 |
| **Total** | **20** |

---

## 13. Problèmes fréquents

| Problème | Solution |
|---|---|
| `ModuleNotFoundError` | L'environnement n'est pas activé : `.venv\Scripts\activate` puis `pip install -r requirements.txt` |
| `Access denied for user 'root'` | Mauvais `MYSQL_PASSWORD` dans `.env` |
| `Can't connect to MySQL server` | MySQL n'est pas démarré (XAMPP : cliquer sur *Start* à côté de MySQL) |
| `400 keyInvalid` / `API key not valid` | Clé mal copiée, ou YouTube Data API v3 non activée sur le projet |
| `403 quotaExceeded` | Quota du jour épuisé : attendre le lendemain ou utiliser une autre clé / le mode DEMO |
| Aucune tendance pour `CG` | Utiliser `--region FR`, `--region CD` ou `--search` |
| « Il faut au moins 4 relevés » | Laisser tourner le collecteur quelques minutes de plus |
| Le dashboard ne bouge pas | Vérifier que le collecteur tourne dans l'autre terminal |
| Recommencer à zéro en mode DEMO | Supprimer les tables (ou le fichier `.db`) **et** le fichier `.demo_state.json` |

---

## 14. Pour aller plus loin (mini-projets)

- **Langues locales** : détecter automatiquement si un commentaire est en français, lingala, kituba ou anglais.
- **Topic modeling** : thèmes de discussion des commentaires avec LDA.
- **Règles d'association** (Apriori) : quels tags apparaissent ensemble dans les vidéos les plus vues ?
- **Séries temporelles** : prévoir les vues de l'heure suivante (moyenne mobile, ARIMA).
- **Chat des lives** : récupérer en vrai temps réel les messages du chat d'un live YouTube (Live Streaming API).
- **Comparaison de pays** : tendances du Congo vs RDC vs Côte d'Ivoire.
