"""
ÉTAPE 2 — Choisir les vidéos à étudier et les enregistrer en base.

Exemples :
  python 02_choisir_videos.py                         # tendances du pays (REGION_CODE)
  python 02_choisir_videos.py --region FR             # tendances d'un autre pays
  python 02_choisir_videos.py --search "rumba congolaise"   # recherche (coûte 100 unités)
  python 02_choisir_videos.py --ids abc123,def456     # vidéos précises (ID de l'URL)

Toutes les vidéos trouvées sont enregistrées (utiles pour l'étape 7),
mais seules les TRACK_TOP premières sont suivies en temps réel.
"""

import argparse
import os
from sqlalchemy import update

from db import channels, get_engine, upsert, utcnow, video_stats, videos
from youtube_client import YouTubeClient

parser = argparse.ArgumentParser()
parser.add_argument("--region", default=os.getenv("REGION_CODE", "CG"))
parser.add_argument("--search", help="mots-clés à rechercher")
parser.add_argument("--ids", help="identifiants de vidéos séparés par des virgules")
parser.add_argument(
    "--track",
    type=int,
    default=int(os.getenv("TRACK_TOP", 15)),
    help="nombre de vidéos à suivre en temps réel",
)
args = parser.parse_args()

client = YouTubeClient()
now = utcnow()

if args.ids:
    source = "manual"
    found = client.videos([x.strip() for x in args.ids.split(",") if x.strip()])
elif args.search:
    source = "search"
    found = client.videos(client.search(args.search, region=args.region, max_results=50))
else:
    source = "trending"
    found = client.trending(args.region, 50)

if not found:
    print(f"Aucune vidéo trouvée (région {args.region}). Essaie --region FR ou --search.")
    raise SystemExit(1)

# Les plus vues d'abord
found.sort(key=lambda v: -(v["view_count"] or 0))
chan_info = {c["channel_id"]: c for c in client.channels([v["channel_id"] for v in found])}

eng = get_engine()
with eng.begin() as conn:
    # la nouvelle sélection remplace l'ancienne pour le suivi temps réel
    conn.execute(update(videos).values(tracked=0))
    for rank, v in enumerate(found):
        stats = {k: v.pop(k) for k in ("view_count", "like_count", "comment_count")}
        v.update(source=source, first_seen=now, tracked=1 if rank < args.track else 0)
        upsert(conn, videos, "video_id", v)
        # premier relevé
        conn.execute(
            video_stats.insert().values(video_id=v["video_id"], collected_at=now, **stats)
        )
    for c in chan_info.values():
        upsert(conn, channels, "channel_id", dict(c, updated_at=now))

print(
    f"{len(found)} vidéos enregistrées ({source}), "
    f"{min(args.track, len(found))} suivies en temps réel :\n"
)
for v in found[: args.track]:
    print(f"  - {v['video_id']}  {v['title'][:70]}")
print(
    f"\nQuota utilisé : {client.quota_used} unité(s). "
    "Étape suivante : python 03_collecteur_temps_reel.py"
)
