# TP Data Mining — YouTube en temps réel

Le guide complet est dans **`GUIDE_TP.md`**, les exercices et corrigés dans **`EXERCICES_CORRIGES.md`**.

## Démarrage rapide (mode DEMO, sans clé ni Internet)

```powershell
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS : source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # Linux/macOS : cp .env.example .env
# dans .env : renseigner MYSQL_PASSWORD (ou mettre DB_ENGINE=sqlite)

python 01_test_api.py
python 02_choisir_videos.py
python 03_collecteur_temps_reel.py      # laisser tourner (terminal 1)

# terminal 2 :
python 04_exploration.py
python 05_sentiment.py
python 06_clustering.py
python 07_prediction.py
python 08_anomalies.py
python 09_demographie.py
streamlit run dashboard.py
```

Pour les vraies données : mettre sa clé YouTube Data API v3 dans `YT_API_KEY` (voir le guide, étape 1).
