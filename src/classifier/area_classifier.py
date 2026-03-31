import json
import os
import re
import unicodedata
from typing import Dict, List, Tuple

_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "vocabulario_areas.json")

_DISPLAY = {
    "matematica": "Matemática",
    "portugues": "Português",
    "historia": "História",
    "geografia": "Geografia",
    "ciencias": "Ciências",
    "biologia": "Biologia",
    "quimica": "Química",
    "fisica": "Física",
    "ingles": "Inglês",
    "artes": "Artes",
    "ed_fisica": "Ed. Física",
}

_vocab: Dict = {}


def _load():
    global _vocab
    if not _vocab:
        with open(_DATA_FILE, encoding="utf-8") as f:
            _vocab = json.load(f)


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def classify_area(text: str) -> Tuple[str, float, List[Tuple[str, float]]]:
    """
    Returns (best_area_key, confidence_0_to_1, top3_scores).
    confidence is the fraction of total score held by best_area.
    """
    _load()
    norm = _normalize(text)

    scores: Dict[str, int] = {}
    for area, groups in _vocab.items():
        score = 0
        for w in groups.get("alta", []):
            if _normalize(w) in norm:
                score += 2
        for w in groups.get("media", []):
            if _normalize(w) in norm:
                score += 1
        scores[area] = score

    total = sum(scores.values()) or 1
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best, best_score = ranked[0]

    if best_score == 0:
        return "indefinida", 0.0, []

    confidence = best_score / total
    top3 = [(a, s / total) for a, s in ranked[:3]]
    return best, confidence, top3


def get_area_display_name(key: str) -> str:
    return _DISPLAY.get(key, key.capitalize())
