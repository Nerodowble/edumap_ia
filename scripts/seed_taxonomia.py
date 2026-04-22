"""
Popular a tabela `taxonomia` a partir do arquivo data/taxonomia.json.

Idempotente: pode rodar múltiplas vezes sem duplicar registros.

Uso:
  python scripts/seed_taxonomia.py
  DATABASE_URL=postgresql://... python scripts/seed_taxonomia.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from database.db import _conn, _BACKEND  # noqa: E402


JSON_PATH = ROOT / "data" / "taxonomia.json"


def _existe_codigo(con, codigo: str) -> bool:
    row = con.execute("SELECT id FROM taxonomia WHERE codigo=?", (codigo,)).fetchone()
    return row is not None


def _get_id(con, codigo: str):
    row = con.execute("SELECT id FROM taxonomia WHERE codigo=?", (codigo,)).fetchone()
    return row["id"] if row else None


def _inserir_no(con, etapa, materia, codigo, label, nivel, parent_id, palavras):
    if _existe_codigo(con, codigo):
        return _get_id(con, codigo)
    kw = ",".join(palavras) if palavras else ""
    return con.insert(
        """INSERT INTO taxonomia
           (etapa, materia, codigo, label, nivel, parent_id, palavras_chave)
           VALUES (?,?,?,?,?,?,?)""",
        (etapa, materia, codigo, label, nivel, parent_id, kw),
    )


def _walk(con, no: dict, etapa: str, materia: str, codigo_pai: str, nivel: int, parent_id):
    codigo_atual = f"{codigo_pai}.{no['codigo']}" if codigo_pai else no["codigo"]
    codigo_full = f"{etapa}.{codigo_atual}"
    novo_id = _inserir_no(
        con, etapa, materia, codigo_full, no["label"], nivel, parent_id,
        no.get("palavras_chave", []),
    )
    for filho in no.get("filhos", []):
        _walk(con, filho, etapa, materia, codigo_atual, nivel + 1, novo_id)


def seed():
    if not JSON_PATH.exists():
        print(f"[ERRO] Arquivo não encontrado: {JSON_PATH}")
        sys.exit(1)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    etapa = data.get("etapa", "ef2")
    materias = data.get("materias", [])

    print(f"[seed] Backend: {_BACKEND}")
    print(f"[seed] Etapa:   {etapa}")
    print(f"[seed] Materias encontradas: {len(materias)}")

    total_antes = total_depois = 0
    with _conn() as con:
        row = con.execute("SELECT COUNT(*) AS c FROM taxonomia WHERE etapa=?", (etapa,)).fetchone()
        total_antes = int(row["c"]) if row else 0

        for materia in materias:
            cod = materia["codigo"]
            _walk(con, materia, etapa, cod, "", nivel=1, parent_id=None)
            print(f"  - {materia['label']} processada")

        row = con.execute("SELECT COUNT(*) AS c FROM taxonomia WHERE etapa=?", (etapa,)).fetchone()
        total_depois = int(row["c"]) if row else 0

    novos = total_depois - total_antes
    print(f"\n[seed] OK — {total_depois} nós na etapa '{etapa}' (adicionados: {novos})")


if __name__ == "__main__":
    seed()
