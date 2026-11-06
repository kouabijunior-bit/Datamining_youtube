"""
youtube_client.py — Petit client pour la YouTube Data API v3.

- Avec une vraie clé : interroge https://www.googleapis.com/youtube/v3
- Avec YT_API_KEY=DEMO : utilise simulator.py (données simulées, hors ligne)

Coût en quota (10 000 unités gratuites par jour) :
  videos.list ......... 1 unité pour 50 vidéos
  channels.list ....... 1 unité pour 50 chaînes
  commentThreads.list . 1 unité pour 100 commentaires
  search.list ......... 100 unités (à utiliser avec modération !)
"""

import hashlib
import os
import re
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://www.googleapis.com/youtube/v3"

# Catégories standard de YouTube
CATEGORIES = {
    "1": "Film & Animation",
    "2": "Autos",
    "10": "Musique",
    "15": "Animaux",
    "17": "Sport",
    "19": "Voyages",
    "20": "Jeux vidéo",
    "22": "Blogs & Personnes",
    "23": "Humour",
    "24": "Divertissement",
    "25": "Actualités & Politique",
    "26": "Vie pratique & Style",
    "27": "Éducation",
    "28": "Science & Technologie",
}


class YouTubeError(Exception):
    pass


class YouTubeClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("YT_API_KEY", "DEMO")
        self.demo = self.api_key.strip().upper() == "DEMO"
        self.quota_used = 0
        if self.demo:
            import simulator

            self._sim = simulator

    # ---------- appel générique ----------
    def _get(self, endpoint: str, params: dict, cost: int = 1) -> dict:
        self.quota_used += cost
        if self.demo:
            return self._sim.handle(endpoint, dict(params))
        params = dict(params, key=self.api_key)
        r = requests.get(f"{API_URL}/{endpoint}", params=params, timeout=30)
        if r.status_code != 200:
            try:
                err = r.json()["error"]
                reason = err.get("errors", [{}])[0].get("reason", "")
                msg = err.get("message", "")
            except Exception:
                reason, msg = "", r.text[:200]
            raise YouTubeError(f"{r.status_code} {reason} : {msg}")
        return r.json()

    # ---------- vidéos ----------
    def videos(self, video_ids: list[str]) -> list[dict]:
        out = []
        for i in range(0, len(video_ids), 50):
            data = self._get(
                "videos",
                {
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids[i : i + 50]),
                    "maxResults": 50,
                },
            )
            out += [parse_video(it) for it in data.get("items", [])]
        return out

    def trending(self, region: str = "CG", max_results: int = 50) -> list[dict]:
        data = self._get(
            "videos",
            {
                "part": "snippet,statistics,contentDetails",
                "chart": "mostPopular",
                "regionCode": region,
                "maxResults": min(max_results, 50),
            },
        )
        return [parse_video(it) for it in data.get("items", [])]

    def search(
        self,
        query: str,
        region: str | None = None,
        max_results: int = 25,
        order: str = "viewCount",
    ) -> list[str]:
        """Retourne des identifiants de vidéos. ATTENTION : 100 unités !"""
        params = {
            "part": "id",
            "q": query,
            "type": "video",
            "maxResults": min(max_results, 50),
            "order": order,
        }
        if region:
            params["regionCode"] = region
        data = self._get("search", params, cost=100)
        return [
            it["id"]["videoId"]
            for it in data.get("items", [])
            if it.get("id", {}).get("videoId")
        ]

    # ---------- chaînes ----------
    def channels(self, channel_ids: list[str]) -> list[dict]:
        out = []
        ids = list(dict.fromkeys(c for c in channel_ids if c))
        for i in range(0, len(ids), 50):
            data = self._get(
                "channels",
                {
                    "part": "snippet,statistics",
                    "id": ",".join(ids[i : i + 50]),
                    "maxResults": 50,
                },
            )
            out += [parse_channel(it) for it in data.get("items", [])]
        return out

    # ---------- commentaires ----------
    def comments(
        self, video_id: str, max_results: int = 100, order: str = "time"
    ) -> list[dict]:
        try:
            data = self._get(
                "commentThreads",
                {
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": min(max_results, 100),
                    "order": order,
                    "textFormat": "plainText",
                },
            )
        except YouTubeError as e:
            if "commentsDisabled" in str(e) or "403" in str(e):
                return []  # commentaires désactivés sur cette vidéo
            raise
        return [parse_comment(it, video_id) for it in data.get("items", [])]


# ================== Transformation JSON -> dictionnaires ==================


def parse_dt(s: str | None):
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return None


def parse_duration(iso: str | None) -> int | None:
    """'PT1H2M30S' -> 3750 secondes"""
    if not iso:
        return None
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return None
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def _int(x):
    return int(x) if x not in (None, "") else None


def parse_video(item: dict) -> dict:
    sn, st, cd = (
        item.get("snippet", {}),
        item.get("statistics", {}),
        item.get("contentDetails", {}),
    )
    return {
        "video_id": item["id"],
        "channel_id": sn.get("channelId"),
        "title": sn.get("title"),
        "description": (sn.get("description") or "")[:5000],
        "tags": "|".join(sn.get("tags", [])),
        "category_id": sn.get("categoryId"),
        "default_language": sn.get("defaultAudioLanguage") or sn.get("defaultLanguage"),
        "published_at": parse_dt(sn.get("publishedAt")),
        "duration_seconds": parse_duration(cd.get("duration")),
        # compteurs (likes peuvent être masqués -> None)
        "view_count": _int(st.get("viewCount")),
        "like_count": _int(st.get("likeCount")),
        "comment_count": _int(st.get("commentCount")),
    }


def parse_channel(item: dict) -> dict:
    sn, st = item.get("snippet", {}), item.get("statistics", {})
    return {
        "channel_id": item["id"],
        "title": sn.get("title"),
        "country": sn.get("country"),
        "published_at": parse_dt(sn.get("publishedAt")),
        "subscriber_count": (
            None if st.get("hiddenSubscriberCount") else _int(st.get("subscriberCount"))
        ),
        "video_count": _int(st.get("videoCount")),
        "view_count": _int(st.get("viewCount")),
    }


def anonymize(author_channel_id: str | None) -> str | None:
    """Remplace l'identifiant de l'auteur par un hash irréversible."""
    if not author_channel_id:
        return None
    salt = os.getenv("ANON_SALT", "tp-datamining")
    return hashlib.sha256((salt + author_channel_id).encode()).hexdigest()[:32]


def parse_comment(item: dict, video_id: str) -> dict:
    top = item["snippet"]["topLevelComment"]
    sn = top["snippet"]
    author_id = (sn.get("authorChannelId") or {}).get("value")
    return {
        "comment_id": top["id"],
        "video_id": video_id,
        "author_channel_id": author_id,  # utilisé UNIQUEMENT en mémoire, jamais stocké
        "author_hash": anonymize(author_id),
        "text": sn.get("textOriginal") or sn.get("textDisplay") or "",
        "like_count": _int(sn.get("likeCount")) or 0,
        "reply_count": _int(item["snippet"].get("totalReplyCount")) or 0,
        "published_at": parse_dt(sn.get("publishedAt")),
    }
