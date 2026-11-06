"""
ÉTAPE 9 (optionnelle) — Démographie de l'audience : âge, genre, pays.

YouTube ne donne ces données QUE pour une chaîne dont on est propriétaire,
via la YouTube Analytics API, et uniquement en POURCENTAGES (jamais par personne).

Préparation (mode réel) :
  1. Google Cloud Console -> activer « YouTube Analytics API »
  2. Identifiants -> « ID client OAuth » -> type « Application de bureau »
  3. Télécharger le JSON et l'enregistrer sous client_secret.json dans ce dossier
  4. Écran de consentement OAuth : ajouter son adresse Gmail comme « utilisateur test »
  5. Lancer le script : un navigateur s'ouvre pour se connecter au compte de la chaîne

Lancement :  python 09_demographie.py --jours 90
Sans client_secret.json (ou avec YT_API_KEY=DEMO) : données simulées.
"""

import argparse
import os
import random
from datetime import date, timedelta

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import delete

from db import demographics, get_engine

parser = argparse.ArgumentParser()
parser.add_argument("--jours", type=int, default=90)
args = parser.parse_args()
fin = date.today() - timedelta(days=2)  # les données Analytics ont ~2 jours de retard
debut = fin - timedelta(days=args.jours)
os.makedirs("figures", exist_ok=True)

demo = os.getenv("YT_API_KEY", "DEMO").upper() == "DEMO" or not os.path.exists(
    "client_secret.json"
)

if demo:
    print(
        "Mode DÉMO : démographie simulée "
        "(ajoute client_secret.json pour tes vraies données).\n"
    )
    r = random.Random(3)
    ages = ["age13-17", "age18-24", "age25-34", "age35-44", "age45-54", "age55-64", "age65-"]
    poids = [8, 34, 30, 14, 8, 4, 2]
    rows_ag = []
    for a, w in zip(ages, poids):
        h = r.uniform(0.5, 0.65)
        rows_ag += [[a, "male", w * h], [a, "female", w * (1 - h)]]
    tot = sum(x[2] for x in rows_ag)
    rows_ag = [[a, g, round(100 * x / tot, 2)] for a, g, x in rows_ag]
    pays = {"CG": 46, "CD": 18, "FR": 12, "CI": 5, "CM": 4, "BE": 4, "US": 3, "GA": 3, "AO": 2}
    rows_c = [
        [c, n * 100, n * 100 * r.uniform(2.0, 4.5), r.uniform(80, 260)]
        for c, n in pays.items()
    ]
else:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secret.json", scopes=["https://www.googleapis.com/auth/yt-analytics.readonly"]
    )
    creds = flow.run_local_server(port=0)
    yta = build("youtubeAnalytics", "v2", credentials=creds)
    rows_ag = (
        yta.reports()
        .query(
            ids="channel==MINE",
            startDate=str(debut),
            endDate=str(fin),
            metrics="viewerPercentage",
            dimensions="ageGroup,gender",
            sort="gender,ageGroup",
        )
        .execute()
        .get("rows", [])
    )
    rows_c = (
        yta.reports()
        .query(
            ids="channel==MINE",
            startDate=str(debut),
            endDate=str(fin),
            metrics="views,estimatedMinutesWatched,averageViewDuration",
            dimensions="country",
            sort="-views",
            maxResults=25,
        )
        .execute()
        .get("rows", [])
    )
    if not rows_ag:
        print(
            "[ATTENTION] Pas de données d'âge/genre : "
            "la chaîne n'a pas encore assez de vues sur la période."
        )

ag = pd.DataFrame(rows_ag, columns=["age_group", "gender", "pourcentage"])
pc = pd.DataFrame(rows_c, columns=["country", "views", "minutes", "duree_moy_s"])

with get_engine().begin() as conn:
    conn.execute(delete(demographics))
    for _, x in ag.iterrows():
        conn.execute(
            demographics.insert().values(
                dimension="age_gender",
                age_group=x.age_group,
                gender=x.gender,
                metric="viewerPercentage",
                value=float(x.pourcentage),
                start_date=str(debut),
                end_date=str(fin),
            )
        )
    for _, x in pc.iterrows():
        for m in ("views", "minutes", "duree_moy_s"):
            conn.execute(
                demographics.insert().values(
                    dimension="country",
                    country=x.country,
                    metric=m,
                    value=float(x[m]),
                    start_date=str(debut),
                    end_date=str(fin),
                )
            )

if not ag.empty:
    tab = ag.pivot_table(
        index="age_group", columns="gender", values="pourcentage", aggfunc="sum"
    ).fillna(0)
    print(f"Audience par âge et genre (% des vues, du {debut} au {fin}) :")
    print(tab.round(1).to_string())
    print("\nTotal par genre :", ag.groupby("gender")["pourcentage"].sum().round(1).to_dict())
    tab.plot.bar(figsize=(9, 5), title="Audience par âge et genre (%)")
    plt.tight_layout()
    plt.savefig("figures/demographie_age_genre.png", dpi=120)
    plt.close()
if not pc.empty:
    pc["part_vues_%"] = 100 * pc["views"] / pc["views"].sum()
    print("\nAudience par pays :")
    print(pc.round(1).to_string(index=False))
    print(
        "\nQuestion : les pays où l'on regarde le plus longtemps "
        "sont-ils ceux qui regardent le plus ?"
    )
print("\nDonnées enregistrées dans la table demographics, graphique dans figures/")
