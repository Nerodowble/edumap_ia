"""Convites de cadastro para EduMap IA.

Cada cadastro de professor/admin_escolar exige um codigo de convite gerado por
um admin. O convite define role e escola do novo usuario.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from .db import _conn

# Sem 0/O e 1/I para evitar confusao ao digitar
_ALFABETO = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
ROLES_CONVIDAVEIS = ("professor", "admin_escolar")


def _agora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gerar_codigo() -> str:
    bloco = lambda: "".join(secrets.choice(_ALFABETO) for _ in range(4))  # noqa: E731
    return f"EDU-{bloco()}-{bloco()}"


def normalizar_codigo(codigo: str) -> str:
    return (codigo or "").strip().upper().replace(" ", "")


def _status(c: Dict) -> str:
    if not c["ativo"]:
        return "desativado"
    if c["usos"] >= c["usos_max"]:
        return "esgotado"
    if c["expira_em"] <= _agora_iso():
        return "expirado"
    return "ativo"


def _com_status(c: Optional[Dict]) -> Optional[Dict]:
    if c is None:
        return None
    c = dict(c)
    c["status"] = _status(c)
    return c


def criar_convite(
    role: str, escola: str, usos_max: int, validade_dias: int, criado_por: Optional[int]
) -> Dict:
    expira = (datetime.now(timezone.utc) + timedelta(days=validade_dias)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    with _conn() as con:
        for _ in range(5):  # colisao e astronomicamente improvavel, mas tratada
            codigo = _gerar_codigo()
            if not con.execute("SELECT id FROM convites WHERE codigo=?", (codigo,)).fetchone():
                break
        cid = con.insert(
            """INSERT INTO convites (codigo, role, escola, usos_max, expira_em, criado_por)
               VALUES (?,?,?,?,?,?)""",
            (codigo, role, escola, usos_max, expira, criado_por),
        )
    return get_convite(cid)


def get_convite(convite_id: int) -> Optional[Dict]:
    with _conn() as con:
        return _com_status(
            con.execute("SELECT * FROM convites WHERE id=?", (convite_id,)).fetchone()
        )


def get_convite_por_codigo(codigo: str) -> Optional[Dict]:
    with _conn() as con:
        return _com_status(
            con.execute(
                "SELECT * FROM convites WHERE codigo=?", (normalizar_codigo(codigo),)
            ).fetchone()
        )


def listar_convites(escola: Optional[str] = None) -> List[Dict]:
    """Lista convites (mais recentes primeiro). Se escola for dada, filtra por ela."""
    sql = """SELECT c.*, u.nome AS criado_por_nome
             FROM convites c LEFT JOIN usuarios u ON u.id = c.criado_por"""
    params: tuple = ()
    if escola is not None:
        sql += " WHERE c.escola = ?"
        params = (escola,)
    sql += " ORDER BY c.id DESC"
    with _conn() as con:
        return [_com_status(r) for r in con.execute(sql, params).fetchall()]


def desativar_convite(convite_id: int) -> bool:
    with _conn() as con:
        return con.update("UPDATE convites SET ativo=0 WHERE id=?", (convite_id,)) > 0


def registrar_com_convite(
    codigo: str, nome: str, email: str, senha_hash: str, escola_fallback: str = ""
) -> Optional[Dict]:
    """Consome um uso do convite e cria o usuario na MESMA transacao.

    O UPDATE condicional garante atomicidade: dois cadastros simultaneos nao
    conseguem gastar o ultimo uso. Se a criacao do usuario falhar, o uso volta.
    Retorna {id, role, escola} ou None se o convite nao for utilizavel.
    """
    codigo = normalizar_codigo(codigo)
    with _conn() as con:
        consumido = con.update(
            """UPDATE convites SET usos = usos + 1
               WHERE codigo=? AND ativo=1 AND usos < usos_max AND expira_em > ?""",
            (codigo, _agora_iso()),
        )
        if consumido != 1:
            return None
        conv = con.execute(
            "SELECT role, escola FROM convites WHERE codigo=?", (codigo,)
        ).fetchone()
        escola = conv["escola"] or escola_fallback
        uid = con.insert(
            "INSERT INTO usuarios (nome, email, senha_hash, role, escola) VALUES (?,?,?,?,?)",
            (nome, email, senha_hash, conv["role"], escola),
        )
    return {"id": uid, "role": conv["role"], "escola": escola}
