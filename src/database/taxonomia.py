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


def seed_from_data(data: Dict) -> Dict:
    """Popular o banco a partir de um dict já parseado (upload via API)."""
    if not isinstance(data, dict) or "materias" not in data:
        raise ValueError("JSON inválido: esperado dict com chave 'materias'.")

    etapa = data.get("etapa", "ef2")
    materias = data.get("materias", [])
    if not isinstance(materias, list):
        raise ValueError("JSON inválido: 'materias' deve ser lista.")
    materias_processadas: List[str] = []

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


def seed_from_json(json_path: Path) -> Dict:
    """Popular a partir de arquivo JSON em disco."""
    if not json_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return seed_from_data(data)


# ── Consulta ──────────────────────────────────────────────────────────────────

def listar_etapas() -> List[Dict]:
    """Retorna etapas distintas com contagem de nós."""
    with _conn() as con:
        return con.execute(
            """SELECT etapa, COUNT(*) AS total_nos,
                      COUNT(DISTINCT materia) AS total_materias
               FROM taxonomia
               GROUP BY etapa
               ORDER BY etapa""",
        ).fetchall()


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


def get_no(no_id: int) -> Optional[Dict]:
    with _conn() as con:
        return con.execute("SELECT * FROM taxonomia WHERE id=?", (no_id,)).fetchone()


def atualizar_no(
    no_id: int,
    label: Optional[str] = None,
    palavras_chave: Optional[List[str]] = None,
) -> bool:
    with _conn() as con:
        existing = con.execute("SELECT id FROM taxonomia WHERE id=?", (no_id,)).fetchone()
        if not existing:
            return False
        updates: List[str] = []
        params: List = []
        if label is not None:
            updates.append("label=?")
            params.append(label)
        if palavras_chave is not None:
            updates.append("palavras_chave=?")
            params.append(",".join(palavras_chave))
        if not updates:
            return True
        params.append(no_id)
        con.execute(f"UPDATE taxonomia SET {','.join(updates)} WHERE id=?", tuple(params))
        return True


def criar_no(
    parent_id: int,
    codigo_slug: str,
    label: str,
    palavras_chave: List[str],
) -> Optional[Dict]:
    """Cria novo nó filho. Herda etapa e materia do pai."""
    if not codigo_slug or not codigo_slug.replace("_", "").isalnum():
        raise ValueError("codigo_slug deve ser alfanumérico (use _ como separador).")
    with _conn() as con:
        parent = con.execute(
            "SELECT * FROM taxonomia WHERE id=?", (parent_id,)
        ).fetchone()
        if not parent:
            return None
        novo_codigo = f"{parent['codigo']}.{codigo_slug}"
        exists = con.execute(
            "SELECT id FROM taxonomia WHERE codigo=?", (novo_codigo,)
        ).fetchone()
        if exists:
            raise ValueError(f"Código já existe: {novo_codigo}")
        kw = ",".join(palavras_chave) if palavras_chave else ""
        novo_id = con.insert(
            """INSERT INTO taxonomia
               (etapa, materia, codigo, label, nivel, parent_id, palavras_chave)
               VALUES (?,?,?,?,?,?,?)""",
            (
                parent["etapa"],
                parent["materia"],
                novo_codigo,
                label,
                parent["nivel"] + 1,
                parent_id,
                kw,
            ),
        )
        return {
            "id": novo_id,
            "codigo": novo_codigo,
            "label": label,
            "nivel": parent["nivel"] + 1,
            "parent_id": parent_id,
            "materia": parent["materia"],
            "palavras_chave": kw,
        }


def deletar_no(no_id: int) -> bool:
    """Deleta o nó e seus descendentes (FK ON DELETE CASCADE)."""
    with _conn() as con:
        existing = con.execute("SELECT id FROM taxonomia WHERE id=?", (no_id,)).fetchone()
        if not existing:
            return False
        con.execute("DELETE FROM taxonomia WHERE id=?", (no_id,))
        return True


def remover_materia(etapa: str, materia: str) -> int:
    """Remove matéria e todos os descendentes (FK cascade). Retorna qtd removida."""
    with _conn() as con:
        row = con.execute(
            "SELECT COUNT(*) AS c FROM taxonomia WHERE etapa=? AND materia=?",
            (etapa, materia),
        ).fetchone()
        count = int(row["c"]) if row else 0
        if count == 0:
            return 0
        con.execute("DELETE FROM taxonomia WHERE etapa=? AND materia=?", (etapa, materia))
        return count


def cleanup_legacy_if_new_exists(
    etapa: str,
    legacy_materia: str,
    required_new_materias: List[str],
) -> int:
    """Remove materia legada se TODAS as novas existem no banco. Útil para
    migrações idempotentes no startup. Retorna qtd de nós removidos."""
    with _conn() as con:
        placeholders = ",".join(["?"] * len(required_new_materias))
        row = con.execute(
            f"SELECT COUNT(DISTINCT materia) AS c FROM taxonomia "
            f"WHERE etapa=? AND materia IN ({placeholders})",
            (etapa, *required_new_materias),
        ).fetchone()
        if not row or int(row["c"]) < len(required_new_materias):
            return 0
    return remover_materia(etapa, legacy_materia)


def exportar_json(etapa: str = "ef2") -> Dict:
    """Exporta toda a taxonomia de uma etapa em formato compatível com import.
    Permite download, edição offline, re-upload (round-trip completo)."""
    with _conn() as con:
        rows = con.execute(
            """SELECT id, codigo, label, nivel, parent_id, palavras_chave, materia
               FROM taxonomia
               WHERE etapa=?
               ORDER BY nivel, codigo""",
            (etapa,),
        ).fetchall()

    by_id: Dict[int, Dict] = {}
    for r in rows:
        slug = r["codigo"].split(".")[-1]
        kws_csv = r.get("palavras_chave") or ""
        kws = [k.strip() for k in kws_csv.split(",") if k.strip()]
        node = {"codigo": slug, "label": r["label"]}
        if kws:
            node["palavras_chave"] = kws
        node["_parent_id"] = r["parent_id"]
        node["_materia"] = r["materia"]
        node["filhos"] = []
        by_id[r["id"]] = node

    # Vincula filhos aos pais
    roots_by_materia: Dict[str, Dict] = {}
    for r in rows:
        nd = by_id[r["id"]]
        pid = r["parent_id"]
        if pid and pid in by_id:
            by_id[pid]["filhos"].append(nd)
        else:
            roots_by_materia[r["materia"]] = nd

    # Limpa metadados auxiliares e chaves vazias
    def _clean(node: Dict):
        node.pop("_parent_id", None)
        node.pop("_materia", None)
        if not node.get("filhos"):
            node.pop("filhos", None)
        else:
            for f in node["filhos"]:
                _clean(f)

    materias = list(roots_by_materia.values())
    for m in materias:
        _clean(m)

    return {
        "versao": "exportado",
        "etapa": etapa,
        "descricao": f"Taxonomia exportada do banco em tempo real (etapa: {etapa}).",
        "materias": materias,
    }


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
