"""
Popular a tabela `taxonomia` a partir do arquivo data/taxonomia.json.

Idempotente: pode rodar múltiplas vezes sem duplicar registros.

Uso:
  python scripts/seed_taxonomia.py
  DATABASE_URL=postgresql://... python scripts/seed_taxonomia.py

(Em produção no Render, prefira chamar o endpoint POST /admin/seed-taxonomia.)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from database.taxonomia import seed_from_json  # noqa: E402


JSON_PATH = ROOT / "data" / "taxonomia.json"


def main():
    stats = seed_from_json(JSON_PATH)
    print(f"[seed] Etapa: {stats['etapa']}")
    print(f"[seed] Materias processadas: {len(stats['materias_processadas'])}")
    for m in stats["materias_processadas"]:
        print(f"  - {m}")
    print(f"[seed] OK  total={stats['total_depois']}  adicionados={stats['adicionados']}")


if __name__ == "__main__":
    main()
