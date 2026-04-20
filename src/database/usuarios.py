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
