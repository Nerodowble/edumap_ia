"""
Seed e consulta da taxonomia educacional.
A lógica de seed é idempotente e pode ser chamada via script ou via API.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

from .db import _conn


# ── Seed ──────────────────────────────────────────────────────────────────────

def _existe_codigo(con, codigo: str) -> bool:
    row = con.execute("SELECT id FROM taxonomia WHERE codigo=?", (codigo,)).fetchone()
    return row is not None


def _get_id(con, codigo: str) -> Optional[int]:
    row = con.execute("SELECT id FROM taxonomia WHERE codigo=?", (codigo,)).fetchone()
    return row["id"] if row else None


def _inserir_no(con, etapa, materia, codigo, label, nivel, parent_id, palavras):
    """UPSERT: insere novo nó ou atualiza label/palavras-chave se já existir.
    Isso permite iterar na taxonomia JSON e re-rodar o seed para aplicar."""
    kw = ",".join(palavras) if palavras else ""
    existing = _get_id(con, codigo)
    if existing is not None:
        con.execute(
            "UPDATE taxonomia SET label=?, palavras_chave=?, nivel=?, parent_id=? WHERE id=?",
            (label, kw, nivel, parent_id, existing),
        )
        return existing
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


def seed_from_json(json_path: Path) -> Dict:
    """Popular o banco a partir do JSON da taxonomia. Idempotente."""
    if not json_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    etapa = data.get("etapa", "ef2")
    materias = data.get("materias", [])
    materias_processadas = []

    atualizados = 0
    with _conn() as con:
        row = con.execute(
            "SELECT COUNT(*) AS c FROM taxonomia WHERE etapa=?", (etapa,)
        ).fetchone()
        total_antes = int(row["c"]) if row else 0

        for materia in materias:
            cod = materia["codigo"]
            _walk(con, materia, etapa, cod, "", nivel=1, parent_id=None)
            materias_processadas.append(materia["label"])

        row = con.execute(
            "SELECT COUNT(*) AS c FROM taxonomia WHERE etapa=?", (etapa,)
        ).fetchone()
        total_depois = int(row["c"]) if row else 0
        atualizados = total_antes  # todos os nós existentes são atualizados

    adicionados = total_depois - total_antes
    return {
        "etapa": etapa,
        "materias_processadas": materias_processadas,
        "total_antes": total_antes,
        "total_depois": total_depois,
        "adicionados": adicionados,
        "atualizados": atualizados,
    }


# ── Consulta ──────────────────────────────────────────────────────────────────

def listar_materias(etapa: str = "ef2") -> List[Dict]:
    with _conn() as con:
        return con.execute(
            """SELECT materia, COUNT(*) AS total_nos
               FROM taxonomia
               WHERE etapa=?
               GROUP BY materia
               ORDER BY materia""",
            (etapa,),
        ).fetchall()


def listar_nos(materia: Optional[str] = None, etapa: str = "ef2") -> List[Dict]:
    with _conn() as con:
        if materia:
            return con.execute(
                """SELECT id, codigo, label, nivel, parent_id, palavras_chave
                   FROM taxonomia
                   WHERE etapa=? AND materia=?
                   ORDER BY codigo""",
                (etapa, materia),
            ).fetchall()
        return con.execute(
            """SELECT id, codigo, label, nivel, parent_id, palavras_chave, materia
               FROM taxonomia
               WHERE etapa=?
               ORDER BY materia, codigo""",
            (etapa,),
        ).fetchall()


def stats(etapa: str = "ef2") -> Dict:
    with _conn() as con:
        total = con.execute(
            "SELECT COUNT(*) AS c FROM taxonomia WHERE etapa=?", (etapa,)
        ).fetchone()
        por_materia = con.execute(
            """SELECT materia, COUNT(*) AS total
               FROM taxonomia
               WHERE etapa=?
               GROUP BY materia
               ORDER BY materia""",
            (etapa,),
        ).fetchall()
        por_nivel = con.execute(
            """SELECT nivel, COUNT(*) AS total
               FROM taxonomia
               WHERE etapa=?
               GROUP BY nivel
               ORDER BY nivel""",
            (etapa,),
        ).fetchall()

    return {
        "etapa": etapa,
        "total_nos": int(total["c"]) if total else 0,
        "por_materia": por_materia,
        "por_nivel": por_nivel,
    }
