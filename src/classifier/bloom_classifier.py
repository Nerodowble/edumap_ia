import json
import os
import re
import unicodedata
from typing import Dict, Optional, Tuple

_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "verbos_bloom.json")

_bloom_data: Dict = {}


def _load():
    global _bloom_data
    if not _bloom_data:
        with open(_DATA_FILE, encoding="utf-8") as f:
            _bloom_data = json.load(f)


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def classify_bloom(text: str) -> Tuple[int, str, Optional[str]]:
    """
    Detect the highest Bloom level verb present in text.
    Returns (level_1_to_6, level_name, matched_verb_or_None).
    Defaults to (2, "Compreender", None) when no verb is found.
    """
    _load()
    norm = _normalize(text)

    for level in range(6, 0, -1):
        entry = _bloom_data.get(str(level), {})
        for verb in entry.get("verbos", []):
            v_norm = _normalize(verb)
            # Word-boundary safe match (handles multi-word phrases too)
            pattern = r"(?<!\w)" + re.escape(v_norm) + r"(?!\w)"
            if re.search(pattern, norm):
                return level, entry["nivel"], verb

    # Structural heuristics
    if re.search(r"(?<!\w)(marque|assinale|indique a alternativa)(?!\w)", norm):
        return 1, "Lembrar", None

    return 2, "Compreender", None


def get_bloom_display(level: int) -> Dict:
    _load()
    entry = _bloom_data.get(str(level), {})
    return {
        "nivel": entry.get("nivel", "Indefinido"),
        "cor": entry.get("cor", "#95A5A6"),
        "descricao": entry.get("descricao", ""),
    }
