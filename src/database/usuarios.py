"""User CRUD for EduMap IA."""
from typing import Dict, List, Optional

from .db import _conn


def criar_usuario(nome: str, email: str, senha_hash: str, role: str, escola: str = "") -> int:
    with _conn() as con:
        return con.insert(
            "INSERT INTO usuarios (nome, email, senha_hash, role, escola) VALUES (?,?,?,?,?)",
            (nome, email, senha_hash, role, escola),
        )


def get_usuario_por_email(email: str) -> Optional[Dict]:
    with _conn() as con:
        return con.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()


def get_usuario(usuario_id: int) -> Optional[Dict]:
    with _conn() as con:
        return con.execute("SELECT * FROM usuarios WHERE id=?", (usuario_id,)).fetchone()


def contar_usuarios() -> int:
    with _conn() as con:
        row = con.execute("SELECT COUNT(*) AS cnt FROM usuarios").fetchone()
        return int(row["cnt"]) if row else 0


def listar_usuarios() -> List[Dict]:
    with _conn() as con:
        return con.execute(
            "SELECT id, nome, email, role, escola, criado_em FROM usuarios ORDER BY nome"
        ).fetchall()


def listar_escolas() -> List[Dict]:
    """Agrega escolas a partir dos campos em usuarios e turmas."""
    with _conn() as con:
        usuarios_rows = con.execute(
            """SELECT escola, COUNT(*) AS total
               FROM usuarios
               WHERE escola IS NOT NULL AND escola != ''
               GROUP BY escola"""
        ).fetchall()
        turmas_rows = con.execute(
            """SELECT escola, COUNT(*) AS total
               FROM turmas
               WHERE escola IS NOT NULL AND escola != ''
               GROUP BY escola"""
        ).fetchall()

    merged: Dict[str, Dict] = {}
    for r in usuarios_rows:
        merged[r["escola"]] = {"escola": r["escola"], "usuarios": int(r["total"]), "turmas": 0}
    for r in turmas_rows:
        if r["escola"] in merged:
            merged[r["escola"]]["turmas"] = int(r["total"])
        else:
            merged[r["escola"]] = {"escola": r["escola"], "usuarios": 0, "turmas": int(r["total"])}

    return sorted(merged.values(), key=lambda x: x["escola"])
