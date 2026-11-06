"""
db.py — Connexion à la base de données et définition des tables.

Fonctionne avec MySQL (DB_ENGINE=mysql) ou SQLite (DB_ENGINE=sqlite).
Les tables sont créées automatiquement au premier lancement.
"""

import os
from datetime import datetime, timezone
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
    text,
)

load_dotenv()

metadata = MetaData()

# Une ligne par chaîne YouTube (créateurs des vidéos suivies)
channels = Table(
    "channels",
    metadata,
    Column("channel_id", String(64), primary_key=True),
    Column("title", String(255)),
    Column("country", String(8)),
    Column("published_at", DateTime),
    Column("subscriber_count", BigInteger),
    Column("video_count", BigInteger),
    Column("view_count", BigInteger),
    Column("updated_at", DateTime),
    mysql_charset="utf8mb4",
)

# Une ligne par vidéo (informations fixes)
videos = Table(
    "videos",
    metadata,
    Column("video_id", String(32), primary_key=True),
    Column("channel_id", String(64)),
    Column("title", Text),
    Column("description", Text),
    Column("tags", Text),
    Column("category_id", String(8)),
    Column("default_language", String(16)),
    Column("published_at", DateTime),
    Column("duration_seconds", Integer),
    Column("source", String(20)),  # trending / search / manual
    Column("tracked", Integer, default=0),  # 1 = suivie en temps réel
    Column("first_seen", DateTime),
    Column("cluster", Integer),  # rempli à l'étape 6
    mysql_charset="utf8mb4",
)

# Une ligne par relevé (c'est la table "temps réel")
video_stats = Table(
    "video_stats",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("video_id", String(32), index=True),
    Column("collected_at", DateTime, index=True),
    Column("view_count", BigInteger),
    Column("like_count", BigInteger),
    Column("comment_count", BigInteger),
    mysql_charset="utf8mb4",
)

# Une ligne par commentaire (auteur anonymisé)
comments = Table(
    "comments",
    metadata,
    Column("comment_id", String(128), primary_key=True),
    Column("video_id", String(32), index=True),
    Column("author_hash", String(64), index=True),
    Column("text", Text),
    Column("like_count", Integer),
    Column("reply_count", Integer),
    Column("published_at", DateTime),
    Column("collected_at", DateTime),
    Column("sentiment", String(10)),  # rempli à l'étape 5 / par le collecteur
    Column("sentiment_score", Float),
    Column("is_suspect", Integer),  # rempli à l'étape 8
    mysql_charset="utf8mb4",
)

# Profil PUBLIC et anonymisé des commentateurs
commenters = Table(
    "commenters",
    metadata,
    Column("author_hash", String(64), primary_key=True),
    Column("channel_created_at", DateTime),
    Column("country", String(8)),
    Column("subscriber_count", BigInteger),
    Column("video_count", BigInteger),
    Column("updated_at", DateTime),
    mysql_charset="utf8mb4",
)

# Démographie de TA chaîne (étape 8, YouTube Analytics)
demographics = Table(
    "demographics",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("dimension", String(20)),  # age_gender / country
    Column("age_group", String(20)),
    Column("gender", String(20)),
    Column("country", String(8)),
    Column("metric", String(40)),
    Column("value", Float),
    Column("start_date", String(10)),
    Column("end_date", String(10)),
    mysql_charset="utf8mb4",
)


def utcnow() -> datetime:
    """Heure actuelle en UTC (sans fuseau, comme dans la base)."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def get_url() -> str:
    engine = os.getenv("DB_ENGINE", "mysql").lower()
    if engine == "sqlite":
        return f"sqlite:///{os.getenv('SQLITE_PATH', 'datamining_youtube.db')}"
    user = os.getenv("MYSQL_USER", "root")
    pwd = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    name = os.getenv("MYSQL_DATABASE", "datamining_youtube")
    return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{name}?charset=utf8mb4"


_engine = None


def _creer_base_mysql():
    """Crée la base MySQL si elle n'existe pas encore."""
    url = get_url()
    serveur, nom = url.rsplit("/", 1)[0], os.getenv("MYSQL_DATABASE", "datamining_youtube")
    eng = create_engine(serveur + "/?charset=utf8mb4", future=True)
    with eng.begin() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{nom}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
    eng.dispose()


def get_engine():
    """Retourne le moteur SQLAlchemy et crée la base et les tables si besoin."""
    global _engine
    if _engine is None:
        if os.getenv("DB_ENGINE", "mysql").lower() != "sqlite":
            _creer_base_mysql()
        _engine = create_engine(get_url(), pool_pre_ping=True, future=True)
        metadata.create_all(_engine)
    return _engine


def upsert(conn, table, key_col: str, row: dict):
    """Insère la ligne, ou la met à jour si la clé existe déjà
    (fonctionne de la même façon sur MySQL et SQLite)."""
    key = row[key_col]
    exists = conn.execute(select(table.c[key_col]).where(table.c[key_col] == key)).first()
    if exists:
        values = {k: v for k, v in row.items() if k != key_col and v is not None}
        if values:
            conn.execute(table.update().where(table.c[key_col] == key).values(**values))
        return False
    conn.execute(table.insert().values(**row))
    return True


if __name__ == "__main__":
    eng = get_engine()
    print("Connexion OK :", eng.url.render_as_string(hide_password=True))
    print("Tables :", ", ".join(metadata.tables.keys()))
