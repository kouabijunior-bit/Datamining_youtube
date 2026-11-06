"""
pretraitement.py — Nettoyage des textes de commentaires (utilisé par
l'étape 5 pour entraîner le modèle et par le collecteur pour prédire
le sentiment en temps réel).
"""

import os
import re
import unicodedata

import joblib

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "models", "sentiment.joblib"
)


def nettoyer(texte: str) -> str:
    """minuscules, sans accents, sans liens, sans ponctuation inutile."""
    if not isinstance(texte, str):
        return ""
    t = texte.lower()
    t = re.sub(r"https?://\S+|www\.\S+", " lien ", t)  # les liens deviennent le mot "lien"
    t = re.sub(r"\d+", " ", t)
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")  # retire les accents
    t = re.sub(r"[^a-z!? ]+", " ", t)  # garde ! et ? (utiles au sentiment)
    t = re.sub(r"(!|\?)", r" \1 ", t)
    return re.sub(r"\s+", " ", t).strip()


def charger_modele():
    """Retourne le modèle entraîné, ou None s'il n'existe pas encore."""
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None


def predire(modele, textes: list[str]):
    """Retourne (étiquettes, score de confiance)."""
    propres = [nettoyer(t) for t in textes]
    labels = modele.predict(propres)
    scores = modele.predict_proba(propres).max(axis=1)
    return list(labels), [float(s) for s in scores]
