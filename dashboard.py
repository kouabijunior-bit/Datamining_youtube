"""
DASHBOARD YOUTUBE DATA MINING — version refondue
================================================
Interface Streamlit organisée en onglets, compatible avec les modules du TP :
    - db.py
    - donnees.py : table_videos, releves, croissance, table_commentaires, lire

Lancement depuis la racine du projet (environnement .venv activé) :
    streamlit run dashboard.py

Le collecteur 03_collecteur_temps_reel.py peut continuer à tourner dans un
premier terminal. Le tableau de bord relit les données périodiquement.

Sécurité / intégrité : ce fichier ne modifie aucune donnée MySQL. Les filtres
sont appliqués en mémoire et les exports portent uniquement sur les résultats
visibles après filtrage.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from donnees import croissance, lire, releves, table_commentaires, table_videos


# -----------------------------------------------------------------------------
# 1. Configuration générale et style
# -----------------------------------------------------------------------------
load_dotenv()

st.set_page_config(
    page_title="YouTube Data Intelligence",
    page_icon=":material/query_stats:",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "YouTube Data Intelligence"
REFRESH_DEFAULT = 20
PALETTE = {
    "positif": "#10B981",
    "neutre": "#94A3B8",
    "negatif": "#EF4444",
    "suspect": "#F97316",
    "normal": "#10B981",
    "non_evalue": "#94A3B8",
    "accent": "#38BDF8",
    "accent_2": "#818CF8",
}

try:
    THEME_BASE = st.get_option("theme.base") or "dark"
except Exception:
    THEME_BASE = "dark"
PLOTLY_TEMPLATE = "plotly_dark" if THEME_BASE == "dark" else "plotly_white"

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.35rem; padding-bottom: 2.5rem; max-width: 1800px;}
      [data-testid="stSidebar"] {border-right: 1px solid rgba(128,128,128,.20);}
      [data-testid="stMetric"] {
        background: rgba(128,128,128,.075);
        border: 1px solid rgba(128,128,128,.16);
        padding: 13px 15px; border-radius: 12px;
      }
      [data-testid="stMetricLabel"] p {font-size: .82rem;}
      [data-testid="stMetricValue"] {font-size: 1.55rem;}
      .sr-eyebrow {font-size:.76rem; letter-spacing:.09em; text-transform:uppercase;
                    opacity:.68; font-weight:700; margin-bottom:.25rem;}
      .sr-subtitle {opacity:.70; font-size:.91rem; margin-top:-.5rem;}
      .sr-status {display:inline-block; padding:.25rem .60rem; border-radius:999px;
                  font-size:.75rem; font-weight:700; border:1px solid rgba(128,128,128,.25);}
      .sr-divider {height:1px; background:rgba(128,128,128,.20); margin:.5rem 0 1rem 0;}
      div[data-testid="stTabs"] button[role="tab"] {
        display: inline-flex; align-items: center; gap: .48rem;
        font-weight: 650; padding-left: .85rem; padding-right: .85rem;
      }
      div[data-testid="stTabs"] button[role="tab"]::before {
        content: ""; display: inline-block; flex: 0 0 18px;
        width: 18px; height: 18px; background-repeat: no-repeat;
        background-position: center; background-size: contain;
        opacity: .95; transition: transform .18s ease, opacity .18s ease;
      }
      div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1)::before {
        background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%2338BDF8%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Crect%20x%3D%223%22%20y%3D%223%22%20width%3D%228%22%20height%3D%228%22%20rx%3D%221.5%22%2F%3E%3Crect%20x%3D%2213%22%20y%3D%223%22%20width%3D%228%22%20height%3D%225%22%20rx%3D%221.5%22%2F%3E%3Crect%20x%3D%2213%22%20y%3D%2210%22%20width%3D%228%22%20height%3D%2211%22%20rx%3D%221.5%22%2F%3E%3Crect%20x%3D%223%22%20y%3D%2213%22%20width%3D%228%22%20height%3D%228%22%20rx%3D%221.5%22%2F%3E%3C%2Fsvg%3E");
      }
      div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2)::before {
        background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%2360A5FA%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M3%203v18h18%22%2F%3E%3Cpath%20d%3D%22m6%2015%204-5%204%203%206-8%22%2F%3E%3Cpath%20d%3D%22M17%205h3v3%22%2F%3E%3C%2Fsvg%3E");
      }
      div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3)::before {
        background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%23F472B6%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M20.8%208.7c0%205.3-8.8%2011-8.8%2011s-8.8-5.7-8.8-11A4.7%204.7%200%200%201%2012%206.2a4.7%204.7%200%200%201%208.8%202.5Z%22%2F%3E%3Cpath%20d%3D%22M3%2012h4l2-3%203.5%206%202-3H21%22%2F%3E%3C%2Fsvg%3E");
      }
      div[data-testid="stTabs"] button[role="tab"]:nth-of-type(4)::before {
        background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%2334D399%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M20%2011.5a7.5%207.5%200%200%201-7.5%207.5H6l-3%202v-6.5A7.5%207.5%200%201%201%2020%2011.5Z%22%2F%3E%3Cpath%20d%3D%22M8%2011h.01M12%2011h.01M16%2011h.01%22%20stroke-width%3D%222.5%22%2F%3E%3C%2Fsvg%3E");
      }
      div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5)::before {
        background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%23A78BFA%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Ccircle%20cx%3D%2212%22%20cy%3D%225%22%20r%3D%222.3%22%2F%3E%3Ccircle%20cx%3D%225%22%20cy%3D%2218%22%20r%3D%222.3%22%2F%3E%3Ccircle%20cx%3D%2219%22%20cy%3D%2218%22%20r%3D%222.3%22%2F%3E%3Cpath%20d%3D%22m10.8%207-4.5%208.8M13.2%207l4.5%208.8M7.3%2018h9.4%22%2F%3E%3C%2Fsvg%3E");
      }
      div[data-testid="stTabs"] button[role="tab"]:nth-of-type(6)::before {
        background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%23F59E0B%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M12%203%2021%207v5c0%205-3.8%208-9%209-5.2-1-9-4-9-9V7l9-4Z%22%2F%3E%3Cpath%20d%3D%22M12%208v5M12%2016.5h.01%22%20stroke-width%3D%222.2%22%2F%3E%3C%2Fsvg%3E");
      }
      div[data-testid="stTabs"] button[role="tab"]:nth-of-type(7)::before {
        background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%2322D3EE%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Ccircle%20cx%3D%229%22%20cy%3D%228%22%20r%3D%223.2%22%2F%3E%3Cpath%20d%3D%22M2.8%2020a6.2%206.2%200%200%201%2012.4%200M16%205.2a3.1%203.1%200%200%201%200%206M17%2014.2a5.4%205.4%200%200%201%204.2%205.3%22%2F%3E%3C%2Fsvg%3E");
      }
      div[data-testid="stTabs"] button[role="tab"]:nth-of-type(8)::before {
        background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%2394A3B8%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M20%2011.5a7.5%207.5%200%200%201-7.5%207.5H6l-3%202v-6.5A7.5%207.5%200%201%201%2020%2011.5Z%22%2F%3E%3Cpath%20d%3D%22M8%209h8M8%2013h5%22%2F%3E%3C%2Fsvg%3E");
      }
      div[data-testid="stTabs"] button[role="tab"][aria-selected="true"]::before {
        transform: scale(1.08); opacity: 1;
      }
      div[data-testid="stTabs"] button[role="tab"]:hover::before {
        transform: translateY(-1px); opacity: 1;
      }
      .sr-note {font-size:.83rem; opacity:.72;}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# 2. Fonctions utilitaires : données, formats et graphiques
# -----------------------------------------------------------------------------
def _is_demo_mode() -> bool:
    """Détermine le mode à partir de la configuration locale, sans exposer la clé."""
    key = (os.getenv("YT_API_KEY") or "DEMO").strip()
    return not key or key.upper() == "DEMO"


def _number(value: object, decimals: int = 0) -> str:
    """Formate proprement un nombre pour les indicateurs."""
    try:
        number = float(value)
        if not np.isfinite(number):
            return "—"
        if decimals:
            return f"{number:,.{decimals}f}".replace(",", " ").replace(".", ",")
        return f"{int(round(number)):,}".replace(",", " ")
    except (TypeError, ValueError, OverflowError):
        return "—"


def _percent(value: object, decimals: int = 1) -> str:
    try:
        number = float(value)
        if not np.isfinite(number):
            return "—"
        return f"{number:.{decimals}f} %".replace(".", ",")
    except (TypeError, ValueError):
        return "—"


def _safe_datetime(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if not df.empty and column in df.columns:
        df = df.copy()
        df[column] = pd.to_datetime(df[column], errors="coerce")
    return df


def _plot(zone, fig: go.Figure, height: int | None = None) -> None:
    """Affiche un graphique avec compatibilité entre versions Streamlit."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        margin=dict(l=20, r=20, t=65, b=25),
        hoverlabel=dict(namelength=-1),
        legend_title_text="",
    )
    if height:
        fig.update_layout(height=height)
    try:
        zone.plotly_chart(fig, width="stretch", config={"displaylogo": False})
    except TypeError:
        zone.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def _table(zone, df: pd.DataFrame, **kwargs) -> None:
    try:
        zone.dataframe(df, width="stretch", **kwargs)
    except TypeError:
        zone.dataframe(df, use_container_width=True, **kwargs)


def _empty(zone, message: str) -> None:
    zone.info(message)


def _csv_download(zone, df: pd.DataFrame, label: str, filename: str) -> None:
    if df.empty:
        return
    data = df.to_csv(index=False).encode("utf-8-sig")
    zone.download_button(
        label=label,
        data=data,
        file_name=filename,
        mime="text/csv",
        key=f"download_{filename}",
    )


def _apply_period(
    df: pd.DataFrame,
    column: str,
    period: str,
    custom_range: tuple[date, date] | None,
) -> pd.DataFrame:
    """Filtre un DataFrame selon les dates de collecte, en UTC sans conversion locale."""
    if df.empty or column not in df.columns:
        return df
    out = _safe_datetime(df, column)
    out = out.dropna(subset=[column])
    if out.empty or period == "Tout":
        return out
    latest = out[column].max()
    windows = {
        "30 dernières minutes": timedelta(minutes=30),
        "2 dernières heures": timedelta(hours=2),
        "12 dernières heures": timedelta(hours=12),
        "24 dernières heures": timedelta(hours=24),
        "7 derniers jours": timedelta(days=7),
    }
    if period in windows:
        return out[out[column] >= latest - windows[period]]
    if period == "Personnalisée" and custom_range:
        start, end = custom_range
        start_ts = pd.Timestamp(datetime.combine(start, datetime.min.time()))
        end_ts = pd.Timestamp(datetime.combine(end + timedelta(days=1), datetime.min.time()))
        return out[(out[column] >= start_ts) & (out[column] < end_ts)]
    return out


def _prepare_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Recharge les tables utiles. Aucun résultat n'est écrit dans la base."""
    videos_df = table_videos()
    stats_df = _safe_datetime(releves(), "collected_at")
    growth_df = _safe_datetime(croissance(), "collected_at")
    comments_df = _safe_datetime(table_commentaires(), "collected_at")
    demographics_df = lire("demographics")
    return videos_df, stats_df, growth_df, comments_df, demographics_df


def _apply_global_filters(
    videos_df: pd.DataFrame,
    stats_df: pd.DataFrame,
    growth_df: pd.DataFrame,
    comments_df: pd.DataFrame,
    only_tracked: bool,
    categories: list[str],
    period: str,
    custom_range: tuple[date, date] | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    v = videos_df.copy()
    if only_tracked and "tracked" in v.columns:
        v = v[pd.to_numeric(v["tracked"], errors="coerce").fillna(0).astype(int) == 1]
    if categories and "categorie" in v.columns:
        v = v[v["categorie"].isin(categories)]
    if not categories:
        v = v.iloc[0:0]

    ids = set(v["video_id"].astype(str)) if "video_id" in v.columns else set()
    s = stats_df[stats_df["video_id"].astype(str).isin(ids)].copy() if not stats_df.empty else stats_df.copy()
    g = growth_df[growth_df["video_id"].astype(str).isin(ids)].copy() if not growth_df.empty else growth_df.copy()
    c = comments_df[comments_df["video_id"].astype(str).isin(ids)].copy() if not comments_df.empty else comments_df.copy()

    s = _apply_period(s, "collected_at", period, custom_range)
    g = _apply_period(g, "collected_at", period, custom_range)
    # Pour les commentaires, on filtre sur leur date de collecte afin de rester cohérent
    # avec la période d'observation du collecteur.
    c = _apply_period(c, "collected_at", period, custom_range)
    return v, s, g, c


def _current_growth(growth_df: pd.DataFrame, videos_df: pd.DataFrame) -> pd.DataFrame:
    if growth_df.empty or videos_df.empty or "vues_par_minute" not in growth_df.columns:
        return pd.DataFrame()
    g = growth_df.dropna(subset=["vues_par_minute"]).copy()
    if g.empty:
        return g
    titles = videos_df[["video_id", "title"]].drop_duplicates("video_id")
    last = g.sort_values("collected_at").groupby("video_id", as_index=False).tail(1)
    return last.merge(titles, on="video_id", how="left")


def _growth_anomalies(growth_df: pd.DataFrame, videos_df: pd.DataFrame) -> pd.DataFrame:
    """Reproduit le critère exploratoire du TP sans modifier MySQL."""
    needed = {"video_id", "vues_par_minute", "nouvelles_vues", "collected_at"}
    if growth_df.empty or not needed.issubset(growth_df.columns):
        return pd.DataFrame()
    g = growth_df.dropna(subset=["vues_par_minute"]).copy()
    if g.empty:
        return g

    def robust_z(series: pd.Series) -> pd.Series:
        median = series.median()
        mad = max(float((series - median).abs().median()) * 1.4826, 0.5 * abs(float(median)), 10.0)
        return (series - median) / mad

    g["z_robuste"] = g.groupby("video_id")["vues_par_minute"].transform(robust_z)
    spikes = g[(g["z_robuste"] > 5) & (g["nouvelles_vues"] >= 500)].copy()
    if spikes.empty:
        return spikes
    cols = [c for c in ["video_id", "title"] if c in videos_df.columns]
    return spikes.merge(videos_df[cols].drop_duplicates("video_id"), on="video_id", how="left")


def _comment_status(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    status = pd.Series("Non évalué", index=series.index, dtype="object")
    status.loc[numeric == 0] = "Normal"
    status.loc[numeric == 1] = "Suspect"
    return status


# -----------------------------------------------------------------------------
# 3. Lecture initiale : nécessaire pour préparer les filtres latéraux
# -----------------------------------------------------------------------------
try:
    _initial_videos = table_videos()
except Exception as exc:  # message volontairement générique pour ne pas exposer de secrets
    st.error("Impossible de lire les données de MySQL.")
    st.caption("Vérifie que MySQL est démarré, que le fichier .env est correct et que db.py fonctionne.")
    st.caption(f"Détail technique : {type(exc).__name__}")
    st.stop()

if _initial_videos.empty:
    st.warning("La base ne contient aucune vidéo. Lance d'abord `python 02_choisir_videos.py`.")
    st.stop()

# -----------------------------------------------------------------------------
# 4. Filtres globaux dans la barre latérale
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"## :material/monitoring: {APP_TITLE}")
    st.caption("Centre de suivi et d'analyse des données YouTube")

    if _is_demo_mode():
        st.warning("SOURCE : MODE DEMO — les données sont simulées.", icon=":material/science:")
    else:
        st.success("SOURCE : YOUTUBE API — mode réel configuré.", icon=":material/play_circle:")

    st.divider()
    st.subheader("Filtres globaux")
    refresh_seconds = st.slider(
        "Actualisation automatique (secondes)",
        min_value=10,
        max_value=300,
        value=REFRESH_DEFAULT,
        step=10,
        help="Le tableau de bord relit MySQL à cet intervalle. Le collecteur doit tourner séparément.",
    )

    period_options = [
        "30 dernières minutes",
        "2 dernières heures",
        "12 dernières heures",
        "24 dernières heures",
        "7 derniers jours",
        "Tout",
        "Personnalisée",
    ]
    selected_period = st.selectbox("Période analysée", period_options, index=5)

    custom_dates: tuple[date, date] | None = None
    if selected_period == "Personnalisée":
        if "collected_at" in releves().columns and not releves().empty:
            _dates = pd.to_datetime(releves()["collected_at"], errors="coerce").dropna()
            min_day = _dates.min().date() if not _dates.empty else date.today() - timedelta(days=7)
            max_day = _dates.max().date() if not _dates.empty else date.today()
        else:
            min_day, max_day = date.today() - timedelta(days=7), date.today()
        chosen = st.date_input(
            "Du … au …",
            value=(min_day, max_day),
            min_value=min_day,
            max_value=max(max_day, date.today()),
        )
        if isinstance(chosen, tuple) and len(chosen) == 2:
            custom_dates = (chosen[0], chosen[1])
        elif isinstance(chosen, date):
            custom_dates = (chosen, chosen)

    only_tracked = st.checkbox("Afficher seulement les vidéos suivies", value=True)

    categories_available = sorted(
        _initial_videos.get("categorie", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()
    )
    selected_categories = st.multiselect(
        "Catégories",
        options=categories_available,
        default=categories_available,
        help="Décoche une catégorie pour l'exclure de tous les onglets concernés.",
    )

    st.divider()
    st.caption("Le collecteur `03_collecteur_temps_reel.py` doit rester actif dans un autre terminal.")
    st.caption("Les filtres du tableau de bord ne modifient jamais les données MySQL.")


# -----------------------------------------------------------------------------
# 5. En-tête et moteur d'affichage périodique
# -----------------------------------------------------------------------------
def afficher_dashboard() -> None:
    try:
        raw_v, raw_s, raw_g, raw_c, raw_d = _prepare_data()
        v, s, g, c = _apply_global_filters(
            raw_v,
            raw_s,
            raw_g,
            raw_c,
            only_tracked,
            selected_categories,
            selected_period,
            custom_dates,
        )
    except Exception as exc:
        st.error("Une erreur est survenue pendant le chargement du tableau de bord.")
        st.caption(f"Détail technique : {type(exc).__name__}")
        return

    mode_text = "DÉMO" if _is_demo_mode() else "YOUTUBE API"
    source_color = "#F59E0B" if _is_demo_mode() else "#10B981"
    st.markdown('<div class="sr-eyebrow">CENTRE D’ANALYSE ET DE SURVEILLANCE</div>', unsafe_allow_html=True)
    head_left, head_right = st.columns([5, 1])
    with head_left:
        st.title("YouTube Data Intelligence")
        st.markdown(
            "<div class='sr-subtitle'>Analyse des performances, des séries temporelles et des résultats de Machine Learning</div>",
            unsafe_allow_html=True,
        )
    with head_right:
        st.markdown(
            f"<div style='text-align:right;padding-top:1.2rem'><span class='sr-status' style='color:{source_color}'>{mode_text}</span></div>",
            unsafe_allow_html=True,
        )

    latest_observation = s["collected_at"].max() if not s.empty and "collected_at" in s else None
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    st.caption(
        f"Actualisation de l'interface : {now_utc} UTC  ·  "
        f"Dernier relevé visible : {latest_observation if latest_observation is not None else 'aucun'} UTC  ·  "
        f"Période : {selected_period}"
    )

    if v.empty:
        st.warning("Aucune vidéo ne correspond aux filtres. Modifie la catégorie ou désactive le filtre des vidéos suivies.")
        return

    # Indicateurs du contexte filtré : les vues sont le dernier compteur connu par vidéo.
    total_views = pd.to_numeric(v.get("view_count", 0), errors="coerce").fillna(0).sum()
    total_likes = pd.to_numeric(v.get("like_count", 0), errors="coerce").fillna(0).sum()
    total_comments_video = pd.to_numeric(v.get("comment_count", 0), errors="coerce").fillna(0).sum()
    labelled = c[c["sentiment"].notna()].copy() if not c.empty and "sentiment" in c.columns else pd.DataFrame()
    positive_share = (labelled["sentiment"].astype(str).str.lower() == "positif").mean() * 100 if not labelled.empty else np.nan
    tracked_count = int((pd.to_numeric(v.get("tracked", 0), errors="coerce").fillna(0) == 1).sum()) if "tracked" in v.columns else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Vidéos dans la sélection", _number(len(v)))
    k2.metric("Vues cumulées actuelles", _number(total_views))
    k3.metric("Relevés dans la période", _number(len(s)))
    k4.metric("Commentaires collectés", _number(len(c)))
    k5.metric("Sentiments positifs", _percent(positive_share, 1))
    st.caption(
        f"{tracked_count} vidéo(s) suivie(s) dans la sélection · "
        f"{_number(total_likes)} likes et {_number(total_comments_video)} commentaires déclarés par les compteurs YouTube."
    )

    tabs = st.tabs(
        [
            "Vue générale",
            "Temps & croissance",
            "Engagement",
            "Sentiments",
            "Clustering",
            "Anomalies",
            "Audience",
            "Commentaires",
        ]
    )

    # -------------------------------------------------------------------------
    # ONGLET 1 — Vue générale
    # -------------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Vue d'ensemble")
        left, right = st.columns([1.55, 1])

        if not s.empty:
            trend = (
                s.groupby("collected_at", as_index=False)
                .agg(vues_total=("view_count", "sum"))
                .sort_values("collected_at")
            )
            fig = px.area(
                trend,
                x="collected_at",
                y="vues_total",
                title="Évolution cumulée des vues des vidéos sélectionnées",
                labels={"collected_at": "Date de collecte (UTC)", "vues_total": "Vues cumulées"},
            )
            fig.update_traces(line_color=PALETTE["accent"], fillcolor="rgba(56,189,248,.16)")
            _plot(left, fig, 370)
        else:
            _empty(left, "Aucun relevé disponible pour la période sélectionnée.")

        category_summary = (
            v.groupby("categorie", dropna=False)
            .agg(videos=("video_id", "nunique"), vues_moyennes=("view_count", "mean"))
            .reset_index()
            .sort_values("vues_moyennes", ascending=True)
        )
        if not category_summary.empty:
            fig = px.bar(
                category_summary,
                x="vues_moyennes",
                y="categorie",
                orientation="h",
                text_auto=".3s",
                title="Vues moyennes par catégorie",
                labels={"vues_moyennes": "Vues moyennes", "categorie": "Catégorie"},
                color_discrete_sequence=[PALETTE["accent_2"]],
            )
            _plot(right, fig, 370)

        st.markdown("#### Vidéos les plus vues")
        top = v.sort_values("view_count", ascending=False).head(10).copy()
        top = top[[col for col in ["title", "categorie", "view_count", "like_count", "comment_count", "taux_engagement"] if col in top.columns]]
        top = top.rename(
            columns={
                "title": "Vidéo",
                "categorie": "Catégorie",
                "view_count": "Vues",
                "like_count": "Likes",
                "comment_count": "Commentaires",
                "taux_engagement": "Taux d'engagement",
            }
        )
        _table(st, top, hide_index=True)
        _csv_download(st, top, "Télécharger le classement CSV", "classement_videos.csv")

    # -------------------------------------------------------------------------
    # ONGLET 2 — Séries temporelles et croissance
    # -------------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Analyse temporelle")
        if s.empty:
            _empty(st, "Aucun relevé temporel dans cette période. Laisse tourner le collecteur, puis actualise.")
        else:
            video_labels = {
                str(row.video_id): f"{str(row.title)[:75]} · {row.video_id}"
                for row in v[["video_id", "title"]].itertuples(index=False)
            }
            defaults = v.sort_values("view_count", ascending=False)["video_id"].astype(str).head(5).tolist()
            chosen_ids = st.multiselect(
                "Vidéos à comparer sur la courbe",
                options=list(video_labels.keys()),
                default=defaults,
                format_func=lambda value: video_labels.get(str(value), str(value)),
                key="temporal_video_selection",
            )
            metric_options = {
                "Vues": "view_count",
                "Likes": "like_count",
                "Commentaires (compteur vidéo)": "comment_count",
            }
            selected_metric_label = st.selectbox("Indicateur temporel", list(metric_options.keys()), key="temporal_metric")
            metric_col = metric_options[selected_metric_label]
            plot_s = s[s["video_id"].astype(str).isin(chosen_ids)].copy() if chosen_ids else s.iloc[0:0].copy()
            if not plot_s.empty and metric_col in plot_s.columns:
                plot_s["video"] = plot_s["video_id"].astype(str).map(video_labels)
                use_log = metric_col == "view_count" and (pd.to_numeric(plot_s[metric_col], errors="coerce") > 0).all()
                fig = px.line(
                    plot_s.sort_values("collected_at"),
                    x="collected_at",
                    y=metric_col,
                    color="video",
                    markers=False,
                    log_y=use_log,
                    title=f"{selected_metric_label} au fil du temps",
                    labels={"collected_at": "Date de collecte (UTC)", metric_col: selected_metric_label, "video": "Vidéo"},
                    color_discrete_sequence=px.colors.qualitative.Safe,
                )
                _plot(st, fig, 490)
            else:
                _empty(st, "Sélectionne au moins une vidéo pour afficher la courbe.")

        st.markdown("#### Vitesse de croissance actuelle")
        current = _current_growth(g, v)
        if not current.empty:
            current = current.sort_values("vues_par_minute", ascending=True).tail(15)
            current["video"] = current["title"].fillna(current["video_id"]).astype(str).str.slice(0, 65)
            fig = px.bar(
                current,
                x="vues_par_minute",
                y="video",
                orientation="h",
                text_auto=".3s",
                title="Dernière vitesse calculée par vidéo",
                labels={"vues_par_minute": "Nouvelles vues / minute", "video": "Vidéo"},
                color="vues_par_minute",
                color_continuous_scale="Blues",
            )
            _plot(st, fig, 430)
            _csv_download(st, current, "Exporter les vitesses CSV", "vitesses_videos.csv")
        else:
            _empty(st, "Pas encore assez de relevés espacés pour calculer une vitesse fiable.")

    # -------------------------------------------------------------------------
    # ONGLET 3 — Engagement
    # -------------------------------------------------------------------------
    with tabs[2]:
        st.subheader("Analyse de l'engagement")
        if "taux_engagement" not in v.columns:
            _empty(st, "La variable taux_engagement n'est pas disponible.")
        else:
            engagement = v.copy()
            engagement["taux_engagement"] = pd.to_numeric(engagement["taux_engagement"], errors="coerce")
            engagement = engagement.dropna(subset=["taux_engagement"])
            left, right = st.columns(2)
            top_eng = engagement.sort_values("taux_engagement", ascending=False).head(12).copy()
            top_eng["video"] = top_eng["title"].fillna(top_eng["video_id"]).astype(str).str.slice(0, 65)
            if not top_eng.empty:
                fig = px.bar(
                    top_eng.sort_values("taux_engagement"),
                    x="taux_engagement",
                    y="video",
                    orientation="h",
                    title="Top vidéos par taux d'engagement",
                    labels={"taux_engagement": "Interactions / vues", "video": "Vidéo"},
                    color_discrete_sequence=[PALETTE["accent"]],
                )
                fig.update_xaxes(tickformat=".1%")
                _plot(left, fig, 430)

            if {"like_count", "view_count"}.issubset(engagement.columns):
                engagement["ratio_likes"] = pd.to_numeric(engagement["like_count"], errors="coerce") / pd.to_numeric(engagement["view_count"], errors="coerce").replace(0, np.nan)
                fig = px.scatter(
                    engagement,
                    x="view_count",
                    y="ratio_likes",
                    size="comment_count" if "comment_count" in engagement.columns else None,
                    color="categorie" if "categorie" in engagement.columns else None,
                    hover_name="title" if "title" in engagement.columns else None,
                    title="Relation entre vues et ratio de likes",
                    labels={"view_count": "Vues", "ratio_likes": "Likes / vues", "categorie": "Catégorie"},
                )
                fig.update_yaxes(tickformat=".1%")
                _plot(right, fig, 430)

            details = engagement.sort_values("taux_engagement", ascending=False)[
                [col for col in ["title", "categorie", "view_count", "like_count", "comment_count", "taux_engagement"] if col in engagement.columns]
            ].rename(
                columns={"title": "Vidéo", "categorie": "Catégorie", "view_count": "Vues", "like_count": "Likes", "comment_count": "Commentaires", "taux_engagement": "Taux d'engagement"}
            )
            _table(st, details, hide_index=True)
            _csv_download(st, details, "Exporter l'analyse d'engagement", "engagement.csv")

    # -------------------------------------------------------------------------
    # ONGLET 4 — Sentiments
    # -------------------------------------------------------------------------
    with tabs[3]:
        st.subheader("Analyse des sentiments")
        if c.empty or "sentiment" not in c.columns or c["sentiment"].notna().sum() == 0:
            _empty(st, "Aucun commentaire classifié pour la sélection. Vérifie l'étape 5 et le collecteur.")
        else:
            sentiment_df = c.copy()
            sentiment_df["sentiment"] = sentiment_df["sentiment"].astype(str).str.lower().str.strip()
            sentiment_df = sentiment_df[sentiment_df["sentiment"].isin(["positif", "negatif", "neutre"])]
            counts = sentiment_df["sentiment"].value_counts().reindex(["positif", "neutre", "negatif"], fill_value=0).rename_axis("sentiment").reset_index(name="commentaires")
            total_labelled = int(counts["commentaires"].sum())
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Commentaires classifiés", _number(total_labelled))
            for col, sentiment, title in [(k2, "positif", "Positifs"), (k3, "neutre", "Neutres"), (k4, "negatif", "Négatifs")]:
                count = int(counts.loc[counts["sentiment"] == sentiment, "commentaires"].iloc[0])
                col.metric(title, _number(count), _percent(100 * count / total_labelled if total_labelled else 0))

            left, right = st.columns(2)
            fig = px.pie(
                counts,
                names="sentiment",
                values="commentaires",
                hole=0.58,
                title="Répartition des sentiments",
                color="sentiment",
                color_discrete_map=PALETTE,
            )
            _plot(left, fig, 400)

            sentiment_by_video = (
                sentiment_df.merge(v[["video_id", "title"]].drop_duplicates("video_id"), on="video_id", how="left")
                .groupby(["title", "sentiment"], dropna=False)
                .size()
                .reset_index(name="commentaires")
            )
            if not sentiment_by_video.empty:
                fig = px.bar(
                    sentiment_by_video,
                    x="commentaires",
                    y="title",
                    color="sentiment",
                    orientation="h",
                    barmode="stack",
                    title="Sentiments par vidéo",
                    labels={"commentaires": "Nombre de commentaires", "title": "Vidéo"},
                    color_discrete_map=PALETTE,
                )
                _plot(right, fig, 440)

            confidence = pd.to_numeric(sentiment_df.get("sentiment_score"), errors="coerce")
            if confidence.notna().any():
                st.metric("Confiance moyenne des prédictions", _percent(confidence.mean() * 100, 1))
                st.caption("Le score de confiance est la probabilité maximale renvoyée par le classifieur, pas une certitude absolue.")
            _csv_download(st, sentiment_df, "Exporter les commentaires classifiés", "sentiments.csv")

    # -------------------------------------------------------------------------
    # ONGLET 5 — Clustering
    # -------------------------------------------------------------------------
    with tabs[4]:
        st.subheader("Segmentation des vidéos — K-Means")
        if "cluster" not in v.columns or v["cluster"].notna().sum() == 0:
            _empty(st, "Aucun cluster disponible. Exécute `python 06_clustering.py --k 3` puis actualise.")
        else:
            cluster_df = v.dropna(subset=["cluster"]).copy()
            cluster_df["cluster"] = pd.to_numeric(cluster_df["cluster"], errors="coerce")
            cluster_df = cluster_df.dropna(subset=["cluster"])
            cluster_df["Groupe K-Means"] = cluster_df["cluster"].astype(int).astype(str)
            if {"age_heures", "vues_par_heure"}.issubset(cluster_df.columns):
                scatter = cluster_df[(pd.to_numeric(cluster_df["age_heures"], errors="coerce") > 0) & (pd.to_numeric(cluster_df["vues_par_heure"], errors="coerce") > 0)]
                if not scatter.empty:
                    fig = px.scatter(
                        scatter,
                        x="age_heures",
                        y="vues_par_heure",
                        color="Groupe K-Means",
                        hover_name="title",
                        size="taux_engagement" if "taux_engagement" in scatter.columns else None,
                        log_y=True,
                        title="Profil des vidéos : âge et vues par heure",
                        labels={"age_heures": "Âge de la vidéo (heures)", "vues_par_heure": "Vues par heure"},
                    )
                    _plot(st, fig, 470)
            cluster_summary = (
                cluster_df.groupby("Groupe K-Means")
                .agg(
                    nombre_videos=("video_id", "nunique"),
                    vues_moyennes=("view_count", "mean"),
                    engagement_moyen=("taux_engagement", "mean"),
                    vitesse_moyenne=("vues_par_heure", "mean"),
                )
                .reset_index()
            )
            _table(st, cluster_summary.round(4), hide_index=True)
            _csv_download(st, cluster_df, "Exporter les vidéos et leurs clusters", "clusters_videos.csv")
            st.caption("Les numéros de cluster sont des identifiants de groupes, pas un classement de qualité ou de popularité.")

    # -------------------------------------------------------------------------
    # ONGLET 6 — Anomalies
    # -------------------------------------------------------------------------
    with tabs[5]:
        st.subheader("Surveillance des comportements inhabituels")
        spikes = _growth_anomalies(g, v)
        left, right = st.columns(2)
        if spikes.empty:
            _empty(left, "Aucun pic de croissance répondant au seuil exploratoire du TP dans cette période.")
        else:
            spikes_display = spikes.sort_values("z_robuste", ascending=False).head(30).copy()
            spikes_display["video"] = spikes_display["title"].fillna(spikes_display["video_id"])
            fig = px.scatter(
                spikes_display,
                x="collected_at",
                y="vues_par_minute",
                color="video",
                size="nouvelles_vues",
                hover_data=["nouvelles_vues", "z_robuste"],
                title="Pics de croissance détectés",
                labels={"collected_at": "Collecte (UTC)", "vues_par_minute": "Vues / minute", "video": "Vidéo"},
            )
            _plot(left, fig, 420)
            _csv_download(left, spikes_display, "Exporter les pics détectés", "pics_croissance.csv")

        if not c.empty and "is_suspect" in c.columns:
            c_status = c.copy()
            c_status["Statut"] = _comment_status(c_status["is_suspect"])
            status_counts = c_status["Statut"].value_counts().reindex(["Suspect", "Normal", "Non évalué"], fill_value=0).rename_axis("Statut").reset_index(name="Commentaires")
            fig = px.bar(
                status_counts,
                x="Statut",
                y="Commentaires",
                color="Statut",
                title="État de l'analyse des commentateurs",
                color_discrete_map={"Suspect": PALETTE["suspect"], "Normal": PALETTE["normal"], "Non évalué": PALETTE["non_evalue"]},
            )
            _plot(right, fig, 420)
            st.markdown("#### État des commentaires")
            _table(st, status_counts, hide_index=True)
            st.caption("« Non évalué » signifie que la colonne is_suspect est NULL : ce n'est ni un résultat normal ni un résultat suspect.")
        else:
            _empty(right, "La colonne is_suspect n'est pas disponible ou aucun commentaire n'a été collecté.")

        if not c.empty and "is_suspect" in c.columns:
            suspicious = c.copy()
            suspicious["Statut"] = _comment_status(suspicious["is_suspect"])
            suspicious = suspicious[suspicious["Statut"] == "Suspect"]
            if not suspicious.empty:
                st.markdown("#### Commentaires associés à un auteur signalé")
                show_cols = [x for x in ["published_at", "text", "sentiment", "like_count", "Statut"] if x in suspicious.columns]
                _table(st, suspicious.sort_values("published_at", ascending=False)[show_cols].head(50), hide_index=True)

    # -------------------------------------------------------------------------
    # ONGLET 7 — Démographie
    # -------------------------------------------------------------------------
    with tabs[6]:
        st.subheader("Audience et démographie")
        if raw_d.empty:
            _empty(st, "Aucune donnée démographique enregistrée. Exécute `python 09_demographie.py --jours 90`.")
        else:
            if _is_demo_mode():
                st.warning("Ces données démographiques sont simulées. Elles ne décrivent pas l'audience réelle d'une chaîne.", icon=":material/science:")
            else:
                st.info("Les données Analytics concernent uniquement une chaîne à laquelle le compte OAuth connecté a accès.")
            age_gender = raw_d[raw_d.get("dimension", pd.Series(index=raw_d.index, dtype=str)) == "age_gender"].copy()
            country = raw_d[(raw_d.get("dimension", pd.Series(index=raw_d.index, dtype=str)) == "country") & (raw_d.get("metric", pd.Series(index=raw_d.index, dtype=str)) == "views")].copy()
            col_a, col_b = st.columns(2)
            if not age_gender.empty:
                fig = px.bar(
                    age_gender,
                    x="age_group",
                    y="value",
                    color="gender",
                    barmode="group",
                    title="Répartition par tranche d'âge et genre (%)",
                    labels={"age_group": "Tranche d'âge", "value": "Part de l'audience (%)", "gender": "Genre"},
                    color_discrete_sequence=[PALETTE["accent"], PALETTE["accent_2"]],
                )
                _plot(col_a, fig, 420)
            else:
                _empty(col_a, "Aucune donnée âge / genre disponible.")
            if not country.empty:
                country = country.sort_values("value", ascending=True).tail(15)
                fig = px.bar(
                    country,
                    x="value",
                    y="country",
                    orientation="h",
                    title="Vues par pays",
                    labels={"value": "Vues", "country": "Pays"},
                    color_discrete_sequence=[PALETTE["accent"]],
                )
                _plot(col_b, fig, 420)
            else:
                _empty(col_b, "Aucune mesure de vues par pays disponible.")
            st.caption("L'API YouTube Analytics fournit des agrégats d'audience pour la chaîne autorisée ; elle ne révèle pas l'âge ou le genre de chaque spectateur.")
            _csv_download(st, raw_d, "Exporter les données démographiques", "demographie.csv")

    # -------------------------------------------------------------------------
    # ONGLET 8 — Commentaires
    # -------------------------------------------------------------------------
    with tabs[7]:
        st.subheader("Exploration des commentaires")
        if c.empty:
            _empty(st, "Aucun commentaire dans la sélection et la période courante.")
        else:
            comment_search = st.text_input("Rechercher dans le texte des commentaires", placeholder="Mot, expression…", key="comments_search")
            col_filter_1, col_filter_2 = st.columns(2)
            sentiment_filter = col_filter_1.selectbox("Sentiment", ["Tous", "positif", "neutre", "negatif", "Non classifié"], key="comments_sentiment_filter")
            status_filter = col_filter_2.selectbox("État anomalie", ["Tous", "Suspect", "Normal", "Non évalué"], key="comments_status_filter")
            display_c = c.copy()
            if "sentiment" in display_c.columns:
                display_c["sentiment"] = display_c["sentiment"].fillna("").astype(str).str.lower().str.strip()
                if sentiment_filter == "Non classifié":
                    display_c = display_c[display_c["sentiment"] == ""]
                elif sentiment_filter != "Tous":
                    display_c = display_c[display_c["sentiment"] == sentiment_filter]
            if "is_suspect" in display_c.columns:
                display_c["Statut anomalie"] = _comment_status(display_c["is_suspect"])
                if status_filter != "Tous":
                    display_c = display_c[display_c["Statut anomalie"] == status_filter]
            if comment_search:
                display_c = display_c[display_c["text"].fillna("").astype(str).str.contains(comment_search, case=False, regex=False)]

            st.caption(f"{_number(len(display_c))} commentaire(s) correspondent aux filtres.")
            visible_cols = [x for x in ["published_at", "text", "sentiment", "sentiment_score", "Statut anomalie", "like_count", "reply_count"] if x in display_c.columns]
            display = display_c.sort_values("published_at", ascending=False)[visible_cols].copy() if "published_at" in display_c.columns else display_c[visible_cols].copy()
            display = display.rename(
                columns={
                    "published_at": "Date de publication",
                    "text": "Commentaire",
                    "sentiment": "Sentiment",
                    "sentiment_score": "Confiance modèle",
                    "like_count": "Likes",
                    "reply_count": "Réponses",
                }
            )
            _table(st, display.head(500), hide_index=True)
            _csv_download(st, display, "Télécharger les commentaires filtrés", "commentaires_filtres.csv")
            if len(display) > 500:
                st.caption("L'aperçu est limité aux 500 premières lignes ; le téléchargement CSV contient toutes les lignes filtrées.")

    st.markdown('<div class="sr-divider"></div>', unsafe_allow_html=True)
    st.markdown(
        "<div class='sr-note'>YouTube Data Intelligence · Données issues de MySQL · Horodatages de collecte en UTC</div>",
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# 6. Actualisation automatique avec compatibilité Streamlit
# -----------------------------------------------------------------------------
if hasattr(st, "fragment"):
    st.fragment(run_every=timedelta(seconds=refresh_seconds))(afficher_dashboard)()
else:
    st.info("L'actualisation automatique nécessite Streamlit 1.37 ou supérieur. Utilise le bouton Actualiser du navigateur.")
    afficher_dashboard()
