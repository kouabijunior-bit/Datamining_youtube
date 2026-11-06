"""
ÉTAPE 3 — Collecteur en (quasi) temps réel.

À chaque cycle (toutes les COLLECT_INTERVAL_SECONDS secondes) :
  1. relève vues / likes / commentaires des vidéos suivies  -> table video_stats
Tous les COMMENTS_EVERY_N_CYCLES cycles :
  2. récupère les nouveaux commentaires (dédoublonnés)       -> table comments
  3. prédit leur sentiment si le modèle de l'étape 5 existe
  4. récupère le profil PUBLIC des nouveaux auteurs (anonymisé) -> table commenters
  5. met à jour les statistiques des chaînes                 -> table channels

Lancement :  python 03_collecteur_temps_reel.py
Options   :  --cycles 5 (s'arrête après 5 cycles)   --interval 30
Arrêt     :  Ctrl + C
"""

import argparse
import os
import time

from sqlalchemy import select

from db import channels, commenters, comments, get_engine, upsert, utcnow, video_stats, videos
from pretraitement import charger_modele, predire
from youtube_client import YouTubeClient, YouTubeError, anonymize

parser = argparse.ArgumentParser()
parser.add_argument(
    "--interval", type=int, default=int(os.getenv("COLLECT_INTERVAL_SECONDS", 60))
)
parser.add_argument(
    "--comments-every", type=int, default=int(os.getenv("COMMENTS_EVERY_N_CYCLES", 10))
)
parser.add_argument("--cycles", type=int, default=0, help="0 = sans fin")
args = parser.parse_args()

client = YouTubeClient()
eng = get_engine()

with eng.connect() as conn:
    tracked = [
        r[0] for r in conn.execute(select(videos.c.video_id).where(videos.c.tracked == 1))
    ]
    known_authors = {r[0] for r in conn.execute(select(commenters.c.author_hash))}
if not tracked:
    print("Aucune vidéo suivie. Lance d'abord : python 02_choisir_videos.py")
    raise SystemExit(1)

# Estimation du quota journalier pour prévenir l'étudiant
cycles_jour = 86400 / args.interval
estimation = cycles_jour * (len(tracked) / 50 + 0.0001) + cycles_jour / args.comments_every * (
    len(tracked) + 2
)
print(
    f"Mode {'DÉMO' if client.demo else 'RÉEL'} — {len(tracked)} vidéos suivies, "
    f"relevé toutes les {args.interval}s"
)
print(f"Quota estimé si le collecteur tourne 24 h : ~{int(estimation)} unités / 10 000")
if estimation > 9000:
    conseil = "augmente --interval ou --comments-every."
    print("[ATTENTION] Risque de dépasser le quota :", conseil)

modele = charger_modele()
print(
    "Sentiment en temps réel :",
    "activé" if modele else "désactivé (lance l'étape 5 pour l'activer)",
)
print("Ctrl + C pour arrêter.\n")

cycle = 0
try:
    while True:
        cycle += 1
        now = utcnow()
        try:
            # ---------- 1. compteurs ----------
            items = client.videos(tracked)
            with eng.begin() as conn:
                for v in items:
                    conn.execute(
                        video_stats.insert().values(
                            video_id=v["video_id"],
                            collected_at=now,
                            view_count=v["view_count"],
                            like_count=v["like_count"],
                            comment_count=v["comment_count"],
                        )
                    )
            total_vues = sum(v["view_count"] or 0 for v in items)
            msg = (
                f"[{now:%H:%M:%S}] cycle {cycle:>4} | {len(items)} vidéos "
                f"| {total_vues:,} vues au total"
            )

            # ---------- 2 à 5. commentaires, profils, chaînes ----------
            if cycle == 1 or cycle % args.comments_every == 0:
                nouveaux, nouveaux_auteurs = [], {}
                with eng.connect() as conn:
                    for vid in tracked:
                        for c in client.comments(vid, max_results=100, order="time"):
                            if conn.execute(
                                select(comments.c.comment_id).where(
                                    comments.c.comment_id == c["comment_id"]
                                )
                            ).first():
                                continue
                            author_id = c.pop("author_channel_id")
                            if (
                                c["author_hash"]
                                and c["author_hash"] not in known_authors
                                and author_id
                            ):
                                nouveaux_auteurs[author_id] = c["author_hash"]
                            nouveaux.append(c)
                if nouveaux and modele is not None:
                    labels, scores = predire(modele, [c["text"] for c in nouveaux])
                    for c, lab, sc in zip(nouveaux, labels, scores):
                        c["sentiment"], c["sentiment_score"] = lab, sc
                # profils publics des nouveaux auteurs (on ne garde que le hash)
                profils = client.channels(list(nouveaux_auteurs)) if nouveaux_auteurs else []
                chans = client.channels(list({v["channel_id"] for v in items}))
                with eng.begin() as conn:
                    for c in nouveaux:
                        conn.execute(comments.insert().values(collected_at=now, **c))
                    for p in profils:
                        h = nouveaux_auteurs.get(p["channel_id"]) or anonymize(p["channel_id"])
                        upsert(
                            conn,
                            commenters,
                            "author_hash",
                            {
                                "author_hash": h,
                                "channel_created_at": p["published_at"],
                                "country": p["country"],
                                "subscriber_count": p["subscriber_count"],
                                "video_count": p["video_count"],
                                "updated_at": now,
                            },
                        )
                        known_authors.add(h)
                    for ch in chans:
                        upsert(conn, channels, "channel_id", dict(ch, updated_at=now))
                msg += f" | +{len(nouveaux)} commentaires | +{len(profils)} profils"
            print(msg + f" | quota utilisé : {client.quota_used}")
        except YouTubeError as e:
            print(f"[{now:%H:%M:%S}] Erreur API : {e}")
            if "quotaExceeded" in str(e):
                print(
                    "Quota journalier épuisé. "
                    "Reprise possible demain (minuit heure du Pacifique)."
                )
                break
        except Exception as e:  # coupure réseau, base indisponible...
            print(f"[{now:%H:%M:%S}] Erreur : {e} — nouvel essai au prochain cycle")

        if args.cycles and cycle >= args.cycles:
            break
        time.sleep(args.interval)
except KeyboardInterrupt:
    pass
print(
    f"\nCollecte arrêtée après {cycle} cycle(s). "
    f"Quota utilisé : {client.quota_used} unités."
)
