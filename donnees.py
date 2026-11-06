"""
donnees.py — Chargement des tables en DataFrames Pandas + variables calculées.
Utilisé par les étapes 4 à 8 et par le dashboard.
"""

import numpy as np
import pandas as pd

from db import get_engine, utcnow
from youtube_client import CATEGORIES


def lire(table: str) -> pd.DataFrame:
    return pd.read_sql_table(table, get_engine())


def releves() -> pd.DataFrame:
    """Tous les relevés (série temporelle), triés par vidéo et par date."""
    s = lire("video_stats")
    if s.empty:
        return s
    s["collected_at"] = pd.to_datetime(s["collected_at"])
    return s.sort_values(["video_id", "collected_at"])


def table_videos() -> pd.DataFrame:
    """Une ligne par vidéo : infos fixes + dernier relevé + chaîne + variables."""
    v = lire("videos")
    if v.empty:
        return v
    s = releves()
    dernier = (
        s.groupby("video_id")
        .tail(1)
        .set_index("video_id")[["view_count", "like_count", "comment_count", "collected_at"]]
    )
    v = v.join(dernier, on="video_id")
    ch = lire("channels").rename(
        columns={
            "title": "channel_title",
            "country": "channel_country",
            "published_at": "channel_created_at",
            "view_count": "channel_view_count",
            "video_count": "channel_video_count",
        }
    )
    v = v.merge(
        ch[
            [
                "channel_id",
                "channel_title",
                "channel_country",
                "subscriber_count",
                "channel_video_count",
                "channel_view_count",
            ]
        ],
        on="channel_id",
        how="left",
    )

    # ----- variables calculées -----
    v["published_at"] = pd.to_datetime(v["published_at"])
    ref = v["collected_at"].fillna(pd.Timestamp(utcnow()))
    v["age_heures"] = ((ref - v["published_at"]).dt.total_seconds() / 3600).clip(lower=0.1)
    v["categorie"] = v["category_id"].map(CATEGORIES).fillna("Autre")
    v["heure_publication"] = v["published_at"].dt.hour
    v["jour_publication"] = v["published_at"].dt.day_name()
    v["duree_min"] = v["duration_seconds"] / 60
    v["nb_tags"] = v["tags"].fillna("").apply(lambda t: len([x for x in t.split("|") if x]))
    v["longueur_titre"] = v["title"].fillna("").str.len()
    vues = v["view_count"].replace(0, np.nan)
    v["taux_engagement"] = (v["like_count"].fillna(0) + v["comment_count"].fillna(0)) / vues
    v["vues_par_heure"] = v["view_count"] / v["age_heures"]
    v["ratio_vues_abonnes"] = v["view_count"] / v["subscriber_count"].replace(0, np.nan)
    return v


def croissance() -> pd.DataFrame:
    """Vitesse de croissance entre deux relevés successifs (vues par minute)."""
    s = releves()
    if s.empty:
        return s
    s["minutes"] = s.groupby("video_id")["collected_at"].diff().dt.total_seconds() / 60
    s["nouvelles_vues"] = s.groupby("video_id")["view_count"].diff()
    # deux relevés trop rapprochés (< 6 s) ne permettent pas de mesurer une vitesse
    s["vues_par_minute"] = (s["nouvelles_vues"] / s["minutes"]).where(s["minutes"] >= 0.1)
    return s


def table_commentaires() -> pd.DataFrame:
    c = lire("comments")
    if c.empty:
        return c
    c["published_at"] = pd.to_datetime(c["published_at"])
    return c
