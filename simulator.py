"""
simulator.py — Simulateur de l'API YouTube (mode DEMO, hors ligne).

Il renvoie des réponses JSON au MÊME FORMAT que la vraie API, avec des
compteurs qui augmentent réellement avec le temps. Idéal pour :
  - les salles sans Internet,
  - tester le pipeline avant d'avoir une clé API.

Les vidéos ont des profils de croissance différents (explosive, lente,
démarrage tardif, déjà stable) et une vidéo contient une anomalie
(hausse brutale de vues) pour l'exercice de détection d'anomalies.
"""

import hashlib
import json
import math
import os
import random
import time
from datetime import datetime, timedelta, timezone

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".demo_state.json")
N_VIDEOS = 40
N_CHANNELS = 12
N_USERS = 400
N_SPAMMERS = 10

TITRES = [
    "Rumba congolaise — nouveau clip officiel",
    "Ndombolo 2026 : la danse qui enflamme Brazzaville",
    "Diables Rouges : résumé du match",
    "Sketch : quand ta maman découvre ton bulletin",
    "Pointe-Noire by night",
    "Recette du saka-saka de grand-mère",
    "Comment réussir son bac en 3 mois",
    "Débat : la jeunesse et le chômage",
    "Freestyle rap kongo",
    "Micro-trottoir au marché Total",
    "Les meilleurs buts de la semaine",
    "Mariage coutumier à Brazzaville",
    "Comédie : le taxi-bus",
    "Tutoriel : créer son entreprise au Congo",
    "Concert live au Palais des congrès",
    "Top 10 des plats congolais",
    "Actualité : ce qui a changé cette semaine",
    "Prank au quartier Bacongo",
    "Interview exclusive d'un artiste",
    "Vlog : une journée à Oyo",
]
CATS = ["10", "10", "10", "23", "23", "24", "24", "17", "25", "27", "22", "26"]
TAGS = [
    "congo",
    "brazzaville",
    "rumba",
    "ndombolo",
    "humour",
    "musique",
    "football",
    "afrique",
    "kinshasa",
    "pointe-noire",
    "clip",
    "buzz",
    "2026",
    "lingala",
    "comédie",
]

POSITIFS = [
    "Trop fort mon frère, continue comme ça !",
    "Merci mingi pour cette vidéo",
    "Ezali malamu, j'adore",
    "Le clip est magnifique, bravo à toute l'équipe",
    "Je regarde ça en boucle depuis ce matin",
    "Fierté congolaise !",
    "Super contenu, très instructif",
    "Tu m'as fait trop rire hahaha",
    "Quelle voix, c'est incroyable",
    "Meilleure vidéo de la semaine",
    "Bravo, vous représentez bien le pays",
    "J'aime beaucoup, abonné direct",
    "C'est du lourd ça !",
    "Merci pour les conseils, ça aide vraiment",
    "La danse est trop belle",
    "Respect à toi l'artiste",
    "Excellent travail, très professionnel",
]
NEGATIFS = [
    "C'est nul, je ne comprends pas le buzz",
    "Ezali mabe, déçu",
    "Vidéo trop longue et ennuyeuse",
    "Le son est mauvais, on n'entend rien",
    "Arrêtez de copier les autres artistes",
    "Pas terrible cette fois-ci",
    "Quelle perte de temps",
    "Je n'aime pas du tout ce style",
    "Le titre est trompeur",
    "Trop de publicités, c'est fatigant",
    "Franchement c'est raté",
    "Mauvaise qualité d'image",
    "Ce n'est pas drôle du tout",
    "Encore la même chose, aucune créativité",
]
NEUTRES = [
    "Mbote na bino",
    "Qui regarde en 2026 ?",
    "C'est tourné où exactement ?",
    "Première fois que je vois ça",
    "Le titre de la musique à 2:15 svp ?",
    "Je suis de Pointe-Noire",
    "Quelqu'un de Kinshasa ici ?",
    "On attend la suite",
    "C'est sorti quand ?",
    "Je partage avec mes amis",
    "Présent depuis Dolisie",
    "Quel est le nom du danseur ?",
    "Vu à la télé hier soir",
]
SPAMS = [
    "Abonnez-vous à ma chaîne !!! http://bit.ly/gagner-argent",
    "GAGNEZ 500 000 FCFA PAR JOUR, contactez-moi WhatsApp",
    "Cliquez ici pour des vues gratuites http://vues-gratuites.xyz",
    "Abonne-toi à moi je m'abonne à toi !!!",
    "Promo crypto : doublez votre argent maintenant http://crypto-promo.top",
]


def _rng(*keys) -> random.Random:
    h = hashlib.md5("|".join(map(str, keys)).encode()).hexdigest()
    return random.Random(int(h, 16))


def _start_time() -> float:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)["start"]
    start = time.time()
    with open(STATE_FILE, "w") as f:
        json.dump({"start": start}, f)
    return start


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _video_params(i: int) -> dict:
    r = _rng("video", i)
    profil = r.choices(["explosive", "lente", "tardive", "stable"], [3, 3, 2, 2])[0]
    p = {
        "id": f"demoVid{i:03d}",
        "channel": f"demoChan{r.randrange(N_CHANNELS):02d}",
        "title": f"{r.choice(TITRES)} #{i}",
        "category": r.choice(CATS),
        "tags": r.sample(TAGS, r.randint(0, 8)),
        "duration": r.choice([45, 90, 180, 240, 300, 420, 600, 900, 1500]) + r.randint(0, 59),
        "profil": profil,
        "like_rate": r.uniform(0.02, 0.09),
        "comment_rate": r.uniform(0.002, 0.012),
        "humeur": r.uniform(-0.4, 0.6),  # tendance des commentaires (négatif -> positif)
    }
    if profil == "explosive":
        p.update(
            offset_min=r.uniform(5, 40), cap=r.uniform(80_000, 400_000), tau=r.uniform(20, 60)
        )
    elif profil == "lente":
        p.update(
            offset_min=r.uniform(10, 120),
            cap=r.uniform(10_000, 60_000),
            tau=r.uniform(200, 600),
        )
    elif profil == "tardive":
        p.update(
            offset_min=r.uniform(5, 30),
            cap=r.uniform(50_000, 250_000),
            t0=r.uniform(40, 120),
            s=r.uniform(8, 20),
        )
    else:  # stable : publiée il y a plusieurs jours, déjà saturée
        p.update(
            offset_min=r.uniform(2 * 1440, 10 * 1440),
            cap=r.uniform(100_000, 2_000_000),
            tau=r.uniform(300, 900),
        )
    p["anomalie"] = i == 7  # cette vidéo reçoit des "vues achetées"
    if p["anomalie"]:  # vidéo très vue (donc toujours suivie) mais stable
        p.update(profil="stable", offset_min=4 * 1440, cap=1_500_000, tau=600)
    return p


def _counts(p: dict, now: float) -> tuple[int, int, int, float]:
    start = _start_time()
    published = start - p["offset_min"] * 60
    age_min = max(0.0, (now - published) / 60)
    if p["profil"] == "tardive":
        v = p["cap"] / (1 + math.exp(-(age_min - p["t0"]) / p["s"]))
    else:
        v = p["cap"] * (1 - math.exp(-age_min / p["tau"]))
    if p["anomalie"] and now - start > 15 * 60:
        v += 60_000  # saut brutal après 15 minutes de collecte
    v = int(v) + 50
    return v, int(v * p["like_rate"]), int(v * p["comment_rate"]), published


def _video_item(i: int, now: float) -> dict:
    p = _video_params(i)
    views, likes, ncom, published = _counts(p, now)
    return {
        "kind": "youtube#video",
        "id": p["id"],
        "snippet": {
            "publishedAt": _iso(published),
            "channelId": p["channel"],
            "title": p["title"],
            "description": f"Vidéo de démonstration ({p['profil']}).",
            "tags": p["tags"],
            "categoryId": p["category"],
            "defaultAudioLanguage": "fr",
        },
        "contentDetails": {"duration": f"PT{p['duration'] // 60}M{p['duration'] % 60}S"},
        "statistics": {
            "viewCount": str(views),
            "likeCount": str(likes),
            "commentCount": str(ncom),
        },
    }


def _channel_item(cid: str) -> dict:
    r = _rng("chan", cid)
    if cid.startswith("demoUser"):
        k = int(cid.replace("demoUser", ""))
        spam = k < N_SPAMMERS
        created = time.time() - (r.uniform(1, 20) if spam else r.uniform(60, 4000)) * 86400
        country = (
            None
            if spam
            else r.choices(["CG", "CD", "FR", "CI", "CM", None], [3, 2, 1, 1, 1, 8])[0]
        )
        subs = 0 if spam else int(r.paretovariate(1.2) * 3) - 3
        vids = 0 if spam else max(0, int(r.paretovariate(1.5)) - 1)
        title = f"Utilisateur {k}"
    else:
        created = time.time() - r.uniform(300, 3000) * 86400
        country = r.choice(["CG", "CG", "CD", "FR", None])
        subs = int(r.uniform(2_000, 900_000))
        vids = r.randint(20, 800)
        title = f"Chaîne Démo {cid[-2:]}"
    return {
        "kind": "youtube#channel",
        "id": cid,
        "snippet": {
            "title": title,
            "publishedAt": _iso(created),
            **({"country": country} if country else {}),
        },
        "statistics": {
            "subscriberCount": str(max(0, subs)),
            "videoCount": str(vids),
            "viewCount": str(max(0, subs) * 40),
            "hiddenSubscriberCount": False,
        },
    }


def _comment_item(p: dict, idx: int, ncom: int, published: float, now: float) -> dict:
    r = _rng("com", p["id"], idx)
    if r.random() < 0.06:
        author = f"demoUser{r.randrange(N_SPAMMERS)}"
        text = r.choice(SPAMS)
    else:
        author = f"demoUser{r.randrange(N_SPAMMERS, N_USERS)}"
        x = r.random() + p["humeur"] * 0.4
        text = r.choice(NEGATIFS if x < 0.3 else NEUTRES if x < 0.55 else POSITIFS)
    t = published + (now - published) * (idx + 1) / max(ncom, 1)
    return {
        "kind": "youtube#commentThread",
        "id": f"{p['id']}-c{idx}",
        "snippet": {
            "videoId": p["id"],
            "totalReplyCount": r.choice([0, 0, 0, 1, 2, 5]),
            "topLevelComment": {
                "id": f"{p['id']}-c{idx}",
                "snippet": {
                    "textOriginal": text,
                    "authorChannelId": {"value": author},
                    "likeCount": int(r.paretovariate(1.3)) - 1,
                    "publishedAt": _iso(t),
                },
            },
        },
    }


def handle(endpoint: str, params: dict) -> dict:
    now = time.time()
    if endpoint == "videos":
        if params.get("chart") == "mostPopular":
            items = [_video_item(i, now) for i in range(N_VIDEOS)]
            items.sort(key=lambda it: -int(it["statistics"]["viewCount"]))
            return {"items": items[: int(params.get("maxResults", 50))]}
        ids = params.get("id", "").split(",")
        idx = [int(x.replace("demoVid", "")) for x in ids if x.startswith("demoVid")]
        return {"items": [_video_item(i, now) for i in idx if i < N_VIDEOS]}
    if endpoint == "search":
        q = params.get("q", "").lower()
        hits = [
            i
            for i in range(N_VIDEOS)
            if any(w in _video_params(i)["title"].lower() for w in q.split())
        ]
        hits = hits or list(range(N_VIDEOS))
        return {
            "items": [
                {"id": {"videoId": f"demoVid{i:03d}"}}
                for i in hits[: int(params.get("maxResults", 25))]
            ]
        }
    if endpoint == "channels":
        return {"items": [_channel_item(c) for c in params.get("id", "").split(",") if c]}
    if endpoint == "commentThreads":
        vid = params["videoId"]
        i = int(vid.replace("demoVid", ""))
        p = _video_params(i)
        _, _, ncom, published = _counts(p, now)
        n = min(int(params.get("maxResults", 100)), ncom)
        return {
            "items": [
                _comment_item(p, k, ncom, published, now)
                for k in range(ncom - 1, ncom - 1 - n, -1)
            ]
        }
    raise ValueError(f"Endpoint non simulé : {endpoint}")
