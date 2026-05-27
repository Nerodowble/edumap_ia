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


def atualizar_usuario(
    usuario_id: int,
    nome: Optional[str] = None,
    role: Optional[str] = None,
    escola: Optional[str] = None,
) -> bool:
    """Atualiza campos selecionados de um usuario. So passe os campos que quer mudar."""
    updates: List[str] = []
    params: list = []
    if nome is not None and nome.strip():
        updates.append("nome=?")
        params.append(nome.strip())
    if role is not None and role in ("admin_geral", "admin_escolar", "professor"):
        updates.append("role=?")
        params.append(role)
    if escola is not None:
        updates.append("escola=?")
        params.append(escola.strip())
    if not updates:
        return False
    with _conn() as con:
        existing = con.execute("SELECT id FROM usuarios WHERE id=?", (usuario_id,)).fetchone()
        if not existing:
            return False
        params.append(usuario_id)
        con.execute(f"UPDATE usuarios SET {', '.join(updates)} WHERE id=?", tuple(params))
        return True


def deletar_usuario(usuario_id: int) -> bool:
    """Apaga usuario. Turmas/provas dele ficam com usuario_id=NULL via ON DELETE SET NULL."""
    with _conn() as con:
        existing = con.execute("SELECT id FROM usuarios WHERE id=?", (usuario_id,)).fetchone()
        if not existing:
            return False
        con.execute("DELETE FROM usuarios WHERE id=?", (usuario_id,))
        return True


def renomear_escola(nome_antigo: str, nome_novo: str) -> Dict[str, int]:
    """Renomeia uma escola: atualiza usuarios.escola e turmas.escola.
    Retorna contadores de quantas linhas tem o nome novo apos a operacao."""
    nome_antigo = (nome_antigo or "").strip()
    nome_novo = (nome_novo or "").strip()
    if not nome_antigo or not nome_novo:
        raise ValueError("Nomes nao podem estar vazios")
    with _conn() as con:
        con.execute("UPDATE usuarios SET escola=? WHERE escola=?", (nome_novo, nome_antigo))
        con.execute("UPDATE turmas SET escola=? WHERE escola=?", (nome_novo, nome_antigo))
        u = con.execute("SELECT COUNT(*) AS c FROM usuarios WHERE escola=?", (nome_novo,)).fetchone()
        t = con.execute("SELECT COUNT(*) AS c FROM turmas WHERE escola=?", (nome_novo,)).fetchone()
        return {
            "usuarios_atualizados": int(u["c"]) if u else 0,
            "turmas_atualizadas": int(t["c"]) if t else 0,
        }


def deletar_escola(nome: str) -> Dict[str, int]:
    """Apaga uma escola: deleta todos os usuarios e todas as turmas dessa escola.
    Provas/alunos seguem por cascade da FK turma_id.
    Retorna contadores das exclusoes (antes do DELETE)."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Nome da escola obrigatorio")
    with _conn() as con:
        u = con.execute("SELECT COUNT(*) AS c FROM usuarios WHERE escola=?", (nome,)).fetchone()
        t = con.execute("SELECT COUNT(*) AS c FROM turmas WHERE escola=?", (nome,)).fetchone()
        usuarios_deletados = int(u["c"]) if u else 0
        turmas_deletadas = int(t["c"]) if t else 0
        con.execute("DELETE FROM usuarios WHERE escola=?", (nome,))
        con.execute("DELETE FROM turmas WHERE escola=?", (nome,))
        return {
            "usuarios_deletados": usuarios_deletados,
            "turmas_deletadas": turmas_deletadas,
        }
