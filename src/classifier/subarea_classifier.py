import json
import os
import unicodedata
from typing import Optional, Tuple

_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "subareas.json")
_data: dict = {}


def _load():
    global _data
    if not _data:
        with open(_DATA_FILE, encoding="utf-8") as f:
            _data = json.load(f)


def _norm(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def classify_subarea(text: str, area_key: str) -> Tuple[str, str]:
    """
    Returns (subarea_key, subarea_label) for the given text within an area.
    Falls back to ("geral", area_key.capitalize()) if nothing matches.
    """
    _load()
    area_data = _data.get(area_key, {})
    if not area_data:
        return "geral", "Geral"

    norm_text = _norm(text)
    best_key, best_label, best_score = "geral", "Geral", 0

    for sub_key, sub_info in area_data.items():
        score = sum(1 for w in sub_info["palavras"] if _norm(w) in norm_text)
        if score > best_score:
            best_score = score
            best_key = sub_key
            best_label = sub_info["label"]

    return best_key, best_label


def get_all_subareas(area_key: str) -> dict:
    """Return all subarea definitions for an area."""
    _load()
    return _data.get(area_key, {})
