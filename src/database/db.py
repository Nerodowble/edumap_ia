"""
Database manager for EduMap IA.
Auto-selects PostgreSQL (DATABASE_URL env var) in production, SQLite locally.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Dict, List, Optional

_DATABASE_URL = os.getenv("DATABASE_URL")
_BACKEND: str = "postgres" if _DATABASE_URL else "sqlite"

if _BACKEND == "postgres":
    import psycopg2
    import psycopg2.extras  # noqa: F401 — RealDictCursor

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "edumap.db")

# ── Schema ────────────────────────────────────────────────────────────────────

_PG_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS usuarios (
        id          BIGSERIAL PRIMARY KEY,
        nome        TEXT NOT NULL,
        email       TEXT NOT NULL UNIQUE,
        senha_hash  TEXT NOT NULL,
        role        TEXT NOT NULL DEFAULT 'professor',
        escola      TEXT,
        criado_em   TIMESTAMPTZ DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS turmas (
        id         BIGSERIAL PRIMARY KEY,
        nome       TEXT NOT NULL,
        escola     TEXT,
        disciplina TEXT,
        usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
        criado_em  TIMESTAMPTZ DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS alunos (
        id        BIGSERIAL PRIMARY KEY,
        nome      TEXT NOT NULL,
        turma_id  BIGINT REFERENCES turmas(id) ON DELETE CASCADE,
        criado_em TIMESTAMPTZ DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS provas (
        id             BIGSERIAL PRIMARY KEY,
        titulo         TEXT,
        turma_id       BIGINT REFERENCES turmas(id) ON DELETE SET NULL,
        disciplina     TEXT,
        serie          TEXT,
        arquivo_nome   TEXT,
        ocr_method     TEXT,
        total_questoes INTEGER,
        criado_em      TIMESTAMPTZ DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS questoes (
        id            BIGSERIAL PRIMARY KEY,
        prova_id      BIGINT NOT NULL REFERENCES provas(id) ON DELETE CASCADE,
        numero        INTEGER,
        texto         TEXT,
        stem          TEXT,
        area_key      TEXT,
        area_display  TEXT,
        subarea_key   TEXT,
        subarea_label TEXT,
        bloom_nivel   INTEGER,
        bloom_nome    TEXT,
        bloom_verbo   TEXT,
        bncc_codigos  TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS respostas (
        id         BIGSERIAL PRIMARY KEY,
        aluno_id   BIGINT NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
        questao_id BIGINT NOT NULL REFERENCES questoes(id) ON DELETE CASCADE,
        resposta   TEXT,
        gabarito   TEXT,
        correta    INTEGER DEFAULT 0,
        criado_em  TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE (aluno_id, questao_id)
    )""",
    """CREATE TABLE IF NOT EXISTS gabarito (
        prova_id       BIGINT NOT NULL REFERENCES provas(id) ON DELETE CASCADE,
        numero_questao INTEGER NOT NULL,
        alternativa    TEXT NOT NULL,
        PRIMARY KEY (prova_id, numero_questao)
    )""",
]

_SQ_SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    senha_hash  TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'professor',
    escola      TEXT,
    criado_em   TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS turmas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    escola      TEXT,
    disciplina  TEXT,
    usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em   TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS alunos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT NOT NULL,
    turma_id  INTEGER REFERENCES turmas(id) ON DELETE CASCADE,
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS provas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo         TEXT,
    turma_id       INTEGER REFERENCES turmas(id) ON DELETE SET NULL,
    disciplina     TEXT,
    serie          TEXT,
    arquivo_nome   TEXT,
    ocr_method     TEXT,
    total_questoes INTEGER,
    criado_em      TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS questoes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    prova_id      INTEGER NOT NULL REFERENCES provas(id) ON DELETE CASCADE,
    numero        INTEGER,
    texto         TEXT,
    stem          TEXT,
    area_key      TEXT,
    area_display  TEXT,
    subarea_key   TEXT,
    subarea_label TEXT,
    bloom_nivel   INTEGER,
    bloom_nome    TEXT,
    bloom_verbo   TEXT,
    bncc_codigos  TEXT
);
CREATE TABLE IF NOT EXISTS respostas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id    INTEGER NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    questao_id  INTEGER NOT NULL REFERENCES questoes(id) ON DELETE CASCADE,
    resposta    TEXT,
    gabarito    TEXT,
    correta     INTEGER DEFAULT 0,
    criado_em   TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(aluno_id, questao_id)
);
CREATE TABLE IF NOT EXISTS gabarito (
    prova_id        INTEGER NOT NULL REFERENCES provas(id) ON DELETE CASCADE,
    numero_questao  INTEGER NOT NULL,
    alternativa     TEXT NOT NULL,
    PRIMARY KEY(prova_id, numero_questao)
);
"""


# ── Connection adapter ────────────────────────────────────────────────────────

class _Rows:
    """Uniform result wrapper so callers use .fetchall() / .fetchone() on both backends."""
    def __init__(self, rows: list):
        self._rows = rows

    def fetchall(self) -> list:
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class _Conn:
    """Adapter that unifies sqlite3 and psycopg2 behind a single interface."""

    def __init__(self):
        if _BACKEND == "postgres":
            self._con = psycopg2.connect(
                _DATABASE_URL,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
            self._cur = self._con.cursor()
        else:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            self._con = sqlite3.connect(DB_PATH)
            self._con.row_factory = sqlite3.Row
            self._con.execute("PRAGMA foreign_keys = ON")
            self._cur = None

    def _ph(self, sql: str) -> str:
        """Replace ? placeholders with %s for PostgreSQL."""
        if _BACKEND == "postgres":
            return sql.replace("?", "%s")
        return sql

    def execute(self, sql: str, params=()) -> _Rows:
        sql = self._ph(sql)
        if _BACKEND == "postgres":
            self._cur.execute(sql, params or None)
            if self._cur.description:
                return _Rows([dict(r) for r in self._cur.fetchall()])
            return _Rows([])
        else:
            cur = self._con.execute(sql, params)
            return _Rows([dict(r) for r in cur.fetchall()])

    def insert(self, sql: str, params=()) -> int:
        """Execute INSERT and return the new row id."""
        sql = self._ph(sql)
        if _BACKEND == "postgres":
            self._cur.execute(sql + " RETURNING id", params or None)
            return self._cur.fetchone()["id"]
        else:
            cur = self._con.execute(sql, params)
            return cur.lastrowid

    def commit(self):
        self._con.commit()

    def rollback(self):
        self._con.rollback()

    def close(self):
        self._con.close()

    def init_schema(self):
        if _BACKEND == "postgres":
            for stmt in _PG_SCHEMA:
                self._cur.execute(stmt)
            try:
                self._cur.execute(
                    "ALTER TABLE turmas ADD COLUMN IF NOT EXISTS "
                    "usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL"
                )
            except Exception:
                self._con.rollback()
            self._con.commit()
        else:
            self._con.executescript(_SQ_SCHEMA)
            try:
                self._con.execute(
                    "ALTER TABLE turmas ADD COLUMN usuario_id INTEGER "
                    "REFERENCES usuarios(id) ON DELETE SET NULL"
                )
                self._con.commit()
            except Exception:
                pass


@contextmanager
def _conn():
    c = _Conn()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def init_db():
    c = _Conn()
    try:
        c.init_schema()
    finally:
        c.close()


# ── Turmas ────────────────────────────────────────────────────────────────────

def criar_turma(nome: str, escola: str = "", disciplina: str = "", usuario_id: Optional[int] = None) -> int:
    with _conn() as con:
        return con.insert(
            "INSERT INTO turmas (nome, escola, disciplina, usuario_id) VALUES (?,?,?,?)",
            (nome, escola, disciplina, usuario_id),
        )


def listar_turmas(usuario_id: Optional[int] = None, role: str = "admin_geral", escola: Optional[str] = None) -> List[Dict]:
    with _conn() as con:
        if role == "admin_geral":
            return con.execute("SELECT * FROM turmas ORDER BY nome").fetchall()
        elif role == "admin_escolar" and escola:
            return con.execute("SELECT * FROM turmas WHERE escola=? ORDER BY nome", (escola,)).fetchall()
        else:
            return con.execute("SELECT * FROM turmas WHERE usuario_id=? ORDER BY nome", (usuario_id,)).fetchall()


def get_turma(turma_id: int) -> Optional[Dict]:
    with _conn() as con:
        return con.execute("SELECT * FROM turmas WHERE id=?", (turma_id,)).fetchone()


def delete_turma(turma_id: int) -> None:
    with _conn() as con:
        con.execute("DELETE FROM turmas WHERE id=?", (turma_id,))


# ── Alunos ────────────────────────────────────────────────────────────────────

def criar_aluno(nome: str, turma_id: int) -> int:
    with _conn() as con:
        return con.insert(
            "INSERT INTO alunos (nome, turma_id) VALUES (?,?)", (nome, turma_id)
        )


def listar_alunos(turma_id: int) -> List[Dict]:
    with _conn() as con:
        return con.execute(
            "SELECT * FROM alunos WHERE turma_id=? ORDER BY nome", (turma_id,)
        ).fetchall()


# ── Provas ────────────────────────────────────────────────────────────────────

def salvar_prova(
    titulo: str,
    serie: str,
    disciplina: str,
    arquivo_nome: str,
    ocr_method: str,
    questoes: List[Dict],
    turma_id: Optional[int] = None,
) -> int:
    with _conn() as con:
        prova_id = con.insert(
            """INSERT INTO provas
               (titulo, turma_id, disciplina, serie, arquivo_nome, ocr_method, total_questoes)
               VALUES (?,?,?,?,?,?,?)""",
            (titulo, turma_id, disciplina, serie, arquivo_nome, ocr_method, len(questoes)),
        )
        for q in questoes:
            bncc = json.dumps(
                [s["codigo"] for s in q.get("bncc_skills", [])], ensure_ascii=False
            )
            con.execute(
                """INSERT INTO questoes
                   (prova_id, numero, texto, stem, area_key, area_display,
                    subarea_key, subarea_label,
                    bloom_nivel, bloom_nome, bloom_verbo, bncc_codigos)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    prova_id,
                    q.get("number"),
                    q.get("text", ""),
                    q.get("stem", ""),
                    q.get("area_key", ""),
                    q.get("area_display", ""),
                    q.get("subarea_key", "geral"),
                    q.get("subarea_label", "Geral"),
                    q.get("bloom_level", 0),
                    q.get("bloom_name", ""),
                    q.get("bloom_verb", ""),
                    bncc,
                ),
            )
        return prova_id


def listar_provas(turma_id: Optional[int] = None) -> List[Dict]:
    with _conn() as con:
        if turma_id:
            return con.execute(
                "SELECT * FROM provas WHERE turma_id=? ORDER BY criado_em DESC", (turma_id,)
            ).fetchall()
        return con.execute("SELECT * FROM provas ORDER BY criado_em DESC").fetchall()


def get_questoes_prova(prova_id: int) -> List[Dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM questoes WHERE prova_id=? ORDER BY numero", (prova_id,)
        ).fetchall()
        for d in rows:
            d["bncc_skills"] = [{"codigo": c} for c in json.loads(d.get("bncc_codigos") or "[]")]
        return rows


# ── Gabarito ──────────────────────────────────────────────────────────────────

def salvar_gabarito(prova_id: int, gabarito: Dict[int, str]) -> None:
    with _conn() as con:
        con.execute("DELETE FROM gabarito WHERE prova_id=?", (prova_id,))
        for num, alt in gabarito.items():
            con.execute(
                "INSERT INTO gabarito (prova_id, numero_questao, alternativa) VALUES (?,?,?)",
                (prova_id, num, alt.upper()),
            )


def get_gabarito(prova_id: int) -> Dict[int, str]:
    with _conn() as con:
        rows = con.execute(
            "SELECT numero_questao, alternativa FROM gabarito WHERE prova_id=? ORDER BY numero_questao",
            (prova_id,),
        ).fetchall()
        return {r["numero_questao"]: r["alternativa"] for r in rows}


def lancar_respostas_aluno(aluno_id: int, prova_id: int, respostas_aluno: Dict[int, str]) -> None:
    """respostas_aluno: {numero_questao: alternativa_respondida} — compara com gabarito automaticamente."""
    gabarito = get_gabarito(prova_id)
    with _conn() as con:
        questoes = con.execute(
            "SELECT id, numero FROM questoes WHERE prova_id=?", (prova_id,)
        ).fetchall()
        num_to_id = {r["numero"]: r["id"] for r in questoes}

        for numero, resposta in respostas_aluno.items():
            qid = num_to_id.get(numero)
            if not qid:
                continue
            gab = gabarito.get(numero, "")
            correta = bool(resposta and gab and resposta.upper() == gab.upper())
            con.execute(
                """INSERT INTO respostas (aluno_id, questao_id, resposta, gabarito, correta)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(aluno_id, questao_id) DO UPDATE
                   SET resposta=excluded.resposta, gabarito=excluded.gabarito,
                       correta=excluded.correta""",
                (aluno_id, qid, resposta.upper(), gab, 1 if correta else 0),
            )


# ── Respostas ─────────────────────────────────────────────────────────────────

def salvar_respostas(aluno_id: int, prova_id: int, respostas: Dict[int, Dict]):
    """respostas: {questao_numero: {resposta, gabarito, correta}}"""
    with _conn() as con:
        questoes = con.execute(
            "SELECT id, numero FROM questoes WHERE prova_id=?", (prova_id,)
        ).fetchall()
        num_to_id = {r["numero"]: r["id"] for r in questoes}

        for numero, dados in respostas.items():
            qid = num_to_id.get(numero)
            if not qid:
                continue
            con.execute(
                """INSERT INTO respostas (aluno_id, questao_id, resposta, gabarito, correta)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(aluno_id, questao_id) DO UPDATE
                   SET resposta=excluded.resposta, gabarito=excluded.gabarito,
                       correta=excluded.correta""",
                (aluno_id, qid, dados.get("resposta", ""), dados.get("gabarito", ""),
                 1 if dados.get("correta") else 0),
            )


# ── Relatório ─────────────────────────────────────────────────────────────────

def relatorio_aluno(aluno_id: int, prova_id: int) -> Dict:
    with _conn() as con:
        aluno = con.execute("SELECT * FROM alunos WHERE id=?", (aluno_id,)).fetchone()
        rows = con.execute(
            """SELECT q.numero, q.area_display, q.bloom_nivel, q.bloom_nome,
                      r.correta, r.resposta, r.gabarito
               FROM respostas r
               JOIN questoes q ON q.id = r.questao_id
               WHERE r.aluno_id=? AND q.prova_id=?
               ORDER BY q.numero""",
            (aluno_id, prova_id),
        ).fetchall()

        by_bloom: Dict = {}
        by_area: Dict = {}
        total, acertos = 0, 0

        for r in rows:
            total += 1
            ok = bool(r["correta"])
            if ok:
                acertos += 1

            bn = r["bloom_nome"] or "Indefinido"
            by_bloom.setdefault(bn, {"total": 0, "acertos": 0})
            by_bloom[bn]["total"] += 1
            if ok:
                by_bloom[bn]["acertos"] += 1

            area = r["area_display"] or "Indefinida"
            by_area.setdefault(area, {"total": 0, "acertos": 0})
            by_area[area]["total"] += 1
            if ok:
                by_area[area]["acertos"] += 1

        return {
            "aluno": aluno or {},
            "total": total,
            "acertos": acertos,
            "percentual": round(acertos * 100 / total) if total else 0,
            "por_bloom": by_bloom,
            "por_area": by_area,
            "detalhes": rows,
        }


def relatorio_turma(prova_id: int) -> List[Dict]:
    with _conn() as con:
        alunos_ids = con.execute(
            """SELECT DISTINCT r.aluno_id FROM respostas r
               JOIN questoes q ON q.id = r.questao_id
               WHERE q.prova_id=?""",
            (prova_id,),
        ).fetchall()
    return [relatorio_aluno(r["aluno_id"], prova_id) for r in alunos_ids]


def relatorio_drilldown(prova_id: int) -> Dict:
    with _conn() as con:
        rows = con.execute(
            """SELECT
                a.id AS aluno_id, a.nome AS aluno_nome,
                q.numero, q.area_display, q.subarea_key, q.subarea_label,
                q.bloom_nivel, q.bloom_nome,
                r.correta
               FROM respostas r
               JOIN questoes q ON q.id = r.questao_id
               JOIN alunos a ON a.id = r.aluno_id
               WHERE q.prova_id = ?
               ORDER BY q.area_display, q.subarea_label, q.bloom_nivel, a.nome""",
            (prova_id,),
        ).fetchall()

    tree: Dict = {}
    for r in rows:
        area   = r["area_display"]  or "Geral"
        sub_k  = r["subarea_key"]   or "geral"
        sub_l  = r["subarea_label"] or "Geral"
        bloom  = r["bloom_nivel"]   or 0
        bloom_n= r["bloom_nome"]    or "—"
        aluno  = r["aluno_id"]
        nome   = r["aluno_nome"]
        ok     = bool(r["correta"])

        tree.setdefault(area, {})
        tree[area].setdefault(sub_k, {"label": sub_l, "bloom": {}})
        tree[area][sub_k]["bloom"].setdefault(bloom, {"nome": bloom_n, "alunos": {}})

        stats = tree[area][sub_k]["bloom"][bloom]["alunos"]
        stats.setdefault(aluno, {"nome": nome, "ok": 0, "total": 0})
        stats[aluno]["total"] += 1
        if ok:
            stats[aluno]["ok"] += 1

    for area in tree:
        for sub in tree[area]:
            for bloom in tree[area][sub]["bloom"]:
                alunos = tree[area][sub]["bloom"][bloom]["alunos"]
                lst = [
                    {
                        "aluno_id": aid,
                        "nome": s["nome"],
                        "ok": s["ok"],
                        "total": s["total"],
                        "pct": round(s["ok"] * 100 / s["total"]) if s["total"] else 0,
                    }
                    for aid, s in alunos.items()
                ]
                lst.sort(key=lambda x: x["pct"])
                tree[area][sub]["bloom"][bloom]["alunos"] = lst
                t_ok    = sum(s["ok"]    for s in lst)
                t_total = sum(s["total"] for s in lst)
                tree[area][sub]["bloom"][bloom]["pct_turma"] = (
                    round(t_ok * 100 / t_total) if t_total else 0
                )

    return tree


# Auto-init on import
init_db()
