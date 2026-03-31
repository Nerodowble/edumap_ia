import json
import os
from typing import Dict, List

_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "bncc_habilidades.json")

_bncc: Dict = {}

_YEAR_CODE = {
    "1º ano EF": "EF01", "2º ano EF": "EF02", "3º ano EF": "EF03",
    "4º ano EF": "EF04", "5º ano EF": "EF05", "6º ano EF": "EF06",
    "7º ano EF": "EF07", "8º ano EF": "EF08", "9º ano EF": "EF09",
    "1º ano EM": "EM", "2º ano EM": "EM", "3º ano EM": "EM",
}

_AREA_CODE = {
    "portugues": "LP", "matematica": "MA", "historia": "HI",
    "geografia": "GE", "ciencias": "CI", "biologia": "BI",
    "quimica": "QU", "fisica": "FI", "ingles": "LI",
    "artes": "AR", "ed_fisica": "EF",
}


def _load():
    global _bncc
    if not _bncc:
        with open(_DATA_FILE, encoding="utf-8") as f:
            _bncc = json.load(f)


def map_to_bncc(area: str, year_level: str, bloom_level: int) -> List[Dict]:
    """Return up to 3 probable BNCC skill codes for the given area/year/bloom."""
    _load()
    year_code = _YEAR_CODE.get(year_level, "")
    area_code = _AREA_CODE.get(area, "")

    if not year_code or not area_code:
        return []

    matches = [
        {"codigo": code, "descricao": info["descricao"], "bloom_nivel": info.get("bloom", 0)}
        for code, info in _bncc.items()
        if code.startswith(year_code) and area_code in code
    ]

    matches.sort(key=lambda x: abs(x["bloom_nivel"] - bloom_level))
    return matches[:3]
