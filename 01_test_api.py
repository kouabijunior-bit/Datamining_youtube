"""
ÉTAPE 1 — Tester la clé API et découvrir le format JSON.

Lancement :  python 01_test_api.py
"""

import json
import os

from youtube_client import CATEGORIES, YouTubeClient, YouTubeError

client = YouTubeClient()
region = os.getenv("REGION_CODE", "CG")
print("Mode :", "DÉMO (données simulées)" if client.demo else "RÉEL (API YouTube)")

try:
    # Réponse brute (JSON) d'une vidéo en tendance
    brut = client._get(
        "videos",
        {
            "part": "snippet,statistics,contentDetails",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": 1,
        },
    )
except YouTubeError as e:
    print("\n[ERREUR] Erreur de l'API :", e)
    print(
        "Vérifie : la clé dans .env, que 'YouTube Data API v3' est activée, "
        "et ta connexion Internet."
    )
    raise SystemExit(1)

if not brut.get("items"):
    print(f"\n[ATTENTION] Aucune tendance disponible pour REGION_CODE={region}.")
    print("Essaie une autre région dans .env (ex. FR, CD, CI, CM) puis relance.")
    raise SystemExit(1)

print("\n===== Extrait de la réponse JSON brute =====")
item = brut["items"][0]
print(
    json.dumps(
        {
            "id": item["id"],
            "snippet": {
                k: item["snippet"][k]
                for k in ("title", "channelId", "publishedAt", "categoryId")
            },
            "statistics": item["statistics"],
            "contentDetails": item["contentDetails"],
        },
        indent=2,
        ensure_ascii=False,
    )
)

v = client.trending(region, 1)[0]
print("\n===== Après transformation (dictionnaire Python) =====")
for k in (
    "video_id",
    "title",
    "published_at",
    "duration_seconds",
    "category_id",
    "view_count",
    "like_count",
    "comment_count",
):
    print(f"{k:18}: {v[k]}")
print("Catégorie         :", CATEGORIES.get(v["category_id"], "?"))
print(
    f"\n[OK] API OK — quota utilisé par ce script : {client.quota_used} unité(s) "
    "sur 10 000/jour"
)
