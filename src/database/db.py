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
        ra        TEXT,
        cpf       TEXT,
        data_nascimento TEXT,
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
        usuario_id     BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
        origem         TEXT DEFAULT 'ocr',
        status         TEXT DEFAULT 'rascunho',
        pin            TEXT,
        publicada_em   TIMESTAMPTZ,
        encerrada_em   TIMESTAMPTZ,
        tempo_limite_min INTEGER,
        criado_em      TIMESTAMPTZ DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS prova_acessos (
        id              BIGSERIAL PRIMARY KEY,
        prova_id        BIGINT NOT NULL REFERENCES provas(id) ON DELETE CASCADE,
        aluno_id        BIGINT NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
        started_at      TIMESTAMPTZ DEFAULT NOW(),
        finished_at     TIMESTAMPTZ,
        fingerprint     TEXT,
        ip              TEXT,
        user_agent      TEXT,
        liberado_em     TIMESTAMPTZ,
        UNIQUE (prova_id, aluno_id)
    )""",
    """CREATE TABLE IF NOT EXISTS questoes (
        id               BIGSERIAL PRIMARY KEY,
        prova_id         BIGINT NOT NULL REFERENCES provas(id) ON DELETE CASCADE,
        numero           INTEGER,
        texto            TEXT,
        stem             TEXT,
        alternativas     TEXT,
        tipo             TEXT DEFAULT 'multipla_escolha',
        area_key         TEXT,
        area_display     TEXT,
        subarea_key      TEXT,
        subarea_label    TEXT,
        bloom_nivel      INTEGER,
        bloom_nome       TEXT,
        bloom_verbo      TEXT,
        taxonomia_codigo TEXT,
        bncc_codigos     TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS respostas (
        id              BIGSERIAL PRIMARY KEY,
        aluno_id        BIGINT NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
        questao_id      BIGINT NOT NULL REFERENCES questoes(id) ON DELETE CASCADE,
        resposta        TEXT,
        gabarito        TEXT,
        correta         INTEGER DEFAULT 0,
        tempo_segundos  INTEGER,
        criado_em       TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE (aluno_id, questao_id)
    )""",
    """CREATE TABLE IF NOT EXISTS gabarito (
        prova_id       BIGINT NOT NULL REFERENCES provas(id) ON DELETE CASCADE,
        numero_questao INTEGER NOT NULL,
        alternativa    TEXT NOT NULL,
        PRIMARY KEY (prova_id, numero_questao)
    )""",
    """CREATE TABLE IF NOT EXISTS taxonomia (
        id              BIGSERIAL PRIMARY KEY,
        etapa           TEXT NOT NULL DEFAULT 'ef2',
        materia         TEXT NOT NULL,
        codigo          TEXT NOT NULL UNIQUE,
        label           TEXT NOT NULL,
        nivel           INTEGER NOT NULL,
        parent_id       BIGINT REFERENCES taxonomia(id) ON DELETE CASCADE,
        palavras_chave  TEXT,
        criado_em       TIMESTAMPTZ DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_taxonomia_materia ON taxonomia(materia)",
    "CREATE INDEX IF NOT EXISTS idx_taxonomia_parent  ON taxonomia(parent_id)",
    "CREATE INDEX IF NOT EXISTS idx_taxonomia_etapa   ON taxonomia(etapa)",
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
    ra        TEXT,
    cpf       TEXT,
    data_nascimento TEXT,
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
    usuario_id     INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    origem         TEXT DEFAULT 'ocr',
    status         TEXT DEFAULT 'rascunho',
    pin            TEXT,
    publicada_em   TEXT,
    encerrada_em   TEXT,
    tempo_limite_min INTEGER,
    criado_em      TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS prova_acessos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    prova_id        INTEGER NOT NULL REFERENCES provas(id) ON DELETE CASCADE,
    aluno_id        INTEGER NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    started_at      TEXT DEFAULT (datetime('now','localtime')),
    finished_at     TEXT,
    fingerprint     TEXT,
    ip              TEXT,
    user_agent      TEXT,
    liberado_em     TEXT,
    UNIQUE(prova_id, aluno_id)
);
CREATE TABLE IF NOT EXISTS questoes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    prova_id         INTEGER NOT NULL REFERENCES provas(id) ON DELETE CASCADE,
    numero           INTEGER,
    texto            TEXT,
    stem             TEXT,
    alternativas     TEXT,
    tipo             TEXT DEFAULT 'multipla_escolha',
    area_key         TEXT,
    area_display     TEXT,
    subarea_key      TEXT,
    subarea_label    TEXT,
    bloom_nivel      INTEGER,
    bloom_nome       TEXT,
    bloom_verbo      TEXT,
    taxonomia_codigo TEXT,
    bncc_codigos     TEXT
);
CREATE TABLE IF NOT EXISTS respostas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id        INTEGER NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    questao_id      INTEGER NOT NULL REFERENCES questoes(id) ON DELETE CASCADE,
    resposta        TEXT,
    gabarito        TEXT,
    correta         INTEGER DEFAULT 0,
    tempo_segundos  INTEGER,
    criado_em       TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(aluno_id, questao_id)
);
CREATE TABLE IF NOT EXISTS gabarito (
    prova_id        INTEGER NOT NULL REFERENCES provas(id) ON DELETE CASCADE,
    numero_questao  INTEGER NOT NULL,
    alternativa     TEXT NOT NULL,
    PRIMARY KEY(prova_id, numero_questao)
);
CREATE TABLE IF NOT EXISTS taxonomia (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    etapa           TEXT NOT NULL DEFAULT 'ef2',
    materia         TEXT NOT NULL,
    codigo          TEXT NOT NULL UNIQUE,
    label           TEXT NOT NULL,
    nivel           INTEGER NOT NULL,
    parent_id       INTEGER REFERENCES taxonomia(id) ON DELETE CASCADE,
    palavras_chave  TEXT,
    criado_em       TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_taxonomia_materia ON taxonomia(materia);
CREATE INDEX IF NOT EXISTS idx_taxonomia_parent  ON taxonomia(parent_id);
CREATE INDEX IF NOT EXISTS idx_taxonomia_etapa   ON taxonomia(etapa);
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
            # Migrações
            for alter in [
                "ALTER TABLE turmas ADD COLUMN IF NOT EXISTS usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL",
                "ALTER TABLE questoes ADD COLUMN IF NOT EXISTS taxonomia_codigo TEXT",
                "ALTER TABLE provas ADD COLUMN IF NOT EXISTS usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL",
                "ALTER TABLE questoes ADD COLUMN IF NOT EXISTS tipo TEXT DEFAULT 'multipla_escolha'",
                "ALTER TABLE alunos ADD COLUMN IF NOT EXISTS ra TEXT",
                "ALTER TABLE alunos ADD COLUMN IF NOT EXISTS cpf TEXT",
                "ALTER TABLE alunos ADD COLUMN IF NOT EXISTS data_nascimento TEXT",
                "ALTER TABLE provas ADD COLUMN IF NOT EXISTS origem TEXT DEFAULT 'ocr'",
                "ALTER TABLE provas ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'rascunho'",
                "ALTER TABLE provas ADD COLUMN IF NOT EXISTS pin TEXT",
                "ALTER TABLE provas ADD COLUMN IF NOT EXISTS publicada_em TIMESTAMPTZ",
                "ALTER TABLE provas ADD COLUMN IF NOT EXISTS encerrada_em TIMESTAMPTZ",
                "ALTER TABLE provas ADD COLUMN IF NOT EXISTS tempo_limite_min INTEGER",
                "ALTER TABLE questoes ADD COLUMN IF NOT EXISTS alternativas TEXT",
                "ALTER TABLE respostas ADD COLUMN IF NOT EXISTS tempo_segundos INTEGER",
            ]:
                try:
                    self._cur.execute(alter)
                except Exception:
                    self._con.rollback()
            self._con.commit()
        else:
            self._con.executescript(_SQ_SCHEMA)
            # SQLite não tem IF NOT EXISTS em ALTER TABLE — try/except
            for alter in [
                "ALTER TABLE turmas ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL",
                "ALTER TABLE questoes ADD COLUMN taxonomia_codigo TEXT",
                "ALTER TABLE provas ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL",
                "ALTER TABLE questoes ADD COLUMN tipo TEXT DEFAULT 'multipla_escolha'",
                "ALTER TABLE alunos ADD COLUMN ra TEXT",
                "ALTER TABLE alunos ADD COLUMN cpf TEXT",
                "ALTER TABLE alunos ADD COLUMN data_nascimento TEXT",
                "ALTER TABLE provas ADD COLUMN origem TEXT DEFAULT 'ocr'",
                "ALTER TABLE provas ADD COLUMN status TEXT DEFAULT 'rascunho'",
                "ALTER TABLE provas ADD COLUMN pin TEXT",
                "ALTER TABLE provas ADD COLUMN publicada_em TEXT",
                "ALTER TABLE provas ADD COLUMN encerrada_em TEXT",
                "ALTER TABLE provas ADD COLUMN tempo_limite_min INTEGER",
                "ALTER TABLE questoes ADD COLUMN alternativas TEXT",
                "ALTER TABLE respostas ADD COLUMN tempo_segundos INTEGER",
            ]:
                try:
                    self._con.execute(alter)
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

def criar_aluno(
    nome: str,
    turma_id: int,
    ra: str = "",
    cpf: str = "",
    data_nascimento: str = "",
) -> int:
    with _conn() as con:
        return con.insert(
            "INSERT INTO alunos (nome, turma_id, ra, cpf, data_nascimento) VALUES (?,?,?,?,?)",
            (nome, turma_id, ra or "", cpf or "", data_nascimento or ""),
        )


def buscar_aluno_por_nome_ra(nome: str, ra: str) -> Optional[Dict]:
    """Busca aluno por (nome+RA) case-insensitive. Usado no login do aluno."""
    if not nome or not ra:
        return None
    nome_norm = nome.strip().lower()
    ra_norm = ra.strip()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM alunos WHERE LOWER(TRIM(nome))=? AND TRIM(ra)=?",
            (nome_norm, ra_norm),
        ).fetchall()
        return rows[0] if rows else None


def atualizar_aluno_completo(
    aluno_id: int,
    nome: str,
    ra: str = "",
    cpf: str = "",
    data_nascimento: str = "",
) -> bool:
    if not nome or not nome.strip():
        return False
    with _conn() as con:
        existing = con.execute("SELECT id FROM alunos WHERE id=?", (aluno_id,)).fetchone()
        if not existing:
            return False
        con.execute(
            "UPDATE alunos SET nome=?, ra=?, cpf=?, data_nascimento=? WHERE id=?",
            (nome.strip(), ra or "", cpf or "", data_nascimento or "", aluno_id),
        )
        return True


def listar_alunos(turma_id: int) -> List[Dict]:
    with _conn() as con:
        return con.execute(
            "SELECT * FROM alunos WHERE turma_id=? ORDER BY nome", (turma_id,)
        ).fetchall()


def get_aluno(aluno_id: int) -> Optional[Dict]:
    with _conn() as con:
        return con.execute("SELECT * FROM alunos WHERE id=?", (aluno_id,)).fetchone()


def atualizar_aluno(aluno_id: int, nome: str) -> bool:
    if not nome or not nome.strip():
        return False
    with _conn() as con:
        existing = con.execute("SELECT id FROM alunos WHERE id=?", (aluno_id,)).fetchone()
        if not existing:
            return False
        con.execute("UPDATE alunos SET nome=? WHERE id=?", (nome.strip(), aluno_id))
        return True


def deletar_aluno(aluno_id: int) -> bool:
    with _conn() as con:
        existing = con.execute("SELECT id FROM alunos WHERE id=?", (aluno_id,)).fetchone()
        if not existing:
            return False
        con.execute("DELETE FROM alunos WHERE id=?", (aluno_id,))
        return True


def atualizar_turma(turma_id: int, nome: str, escola: str = "", disciplina: str = "") -> bool:
    if not nome or not nome.strip():
        return False
    with _conn() as con:
        existing = con.execute("SELECT id FROM turmas WHERE id=?", (turma_id,)).fetchone()
        if not existing:
            return False
        con.execute(
            "UPDATE turmas SET nome=?, escola=?, disciplina=? WHERE id=?",
            (nome.strip(), escola or "", disciplina or "", turma_id),
        )
        return True


# ── Provas ────────────────────────────────────────────────────────────────────

def salvar_prova(
    titulo: str,
    serie: str,
    disciplina: str,
    arquivo_nome: str,
    ocr_method: str,
    questoes: List[Dict],
    turma_id: Optional[int] = None,
    usuario_id: Optional[int] = None,
) -> int:
    with _conn() as con:
        prova_id = con.insert(
            """INSERT INTO provas
               (titulo, turma_id, disciplina, serie, arquivo_nome, ocr_method, total_questoes, usuario_id)
               VALUES (?,?,?,?,?,?,?,?)""",
            (titulo, turma_id, disciplina, serie, arquivo_nome, ocr_method, len(questoes), usuario_id),
        )
        for q in questoes:
            bncc = json.dumps(
                [s["codigo"] for s in q.get("bncc_skills", [])], ensure_ascii=False
            )
            con.execute(
                """INSERT INTO questoes
                   (prova_id, numero, texto, stem, tipo,
                    area_key, area_display, subarea_key, subarea_label,
                    bloom_nivel, bloom_nome, bloom_verbo, taxonomia_codigo, bncc_codigos)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    prova_id,
                    q.get("number"),
                    q.get("text", ""),
                    q.get("stem", ""),
                    q.get("tipo", "multipla_escolha"),
                    q.get("area_key", ""),
                    q.get("area_display", ""),
                    q.get("subarea_key", "geral"),
                    q.get("subarea_label", "Geral"),
                    q.get("bloom_level", 0),
                    q.get("bloom_name", ""),
                    q.get("bloom_verb", ""),
                    q.get("taxonomia_codigo", ""),
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


# ── Autorização (ownership / role) ────────────────────────────────────────────

def user_pode_ver_turma(turma_id: int, user: Dict) -> bool:
    """True se o usuário pode ver/acessar esta turma.
    - admin_geral: sempre
    - admin_escolar: se turma.escola == user.escola
    - professor: se turma.usuario_id == user.id
    """
    if not user:
        return False
    if user.get("role") == "admin_geral":
        return True
    turma = get_turma(turma_id)
    if not turma:
        return False
    if user.get("role") == "admin_escolar":
        return (turma.get("escola") or "") == (user.get("escola") or "")
    if user.get("role") == "professor":
        return turma.get("usuario_id") == user.get("id")
    return False


def user_pode_ver_prova(prova_id: int, user: Dict) -> bool:
    """True se o usuário pode ver/acessar esta prova."""
    if not user:
        return False
    if user.get("role") == "admin_geral":
        return True
    prova = get_prova(prova_id)
    if not prova:
        return False
    # Se a prova tem dono direto, verifica
    owner_id = prova.get("usuario_id")
    if user.get("role") == "professor":
        if owner_id is not None:
            return owner_id == user.get("id")
        # Sem dono direto: verifica via turma
        if prova.get("turma_id"):
            return user_pode_ver_turma(prova["turma_id"], user)
        return False
    if user.get("role") == "admin_escolar":
        if prova.get("turma_id"):
            return user_pode_ver_turma(prova["turma_id"], user)
        # Sem turma vinculada: admin_escolar não vê
        return False
    return False


def get_prova(prova_id: int) -> Optional[Dict]:
    with _conn() as con:
        return con.execute("SELECT * FROM provas WHERE id=?", (prova_id,)).fetchone()


def listar_todas_provas() -> List[Dict]:
    """Lista todas as provas com informações da turma (admin)."""
    with _conn() as con:
        return con.execute(
            """SELECT p.*, t.nome AS turma_nome, t.escola AS turma_escola
               FROM provas p
               LEFT JOIN turmas t ON t.id = p.turma_id
               ORDER BY p.criado_em DESC"""
        ).fetchall()


def delete_prova(prova_id: int) -> bool:
    """Deleta prova (cascata em questoes/respostas/gabarito via FK)."""
    with _conn() as con:
        existing = con.execute("SELECT id FROM provas WHERE id=?", (prova_id,)).fetchone()
        if not existing:
            return False
        con.execute("DELETE FROM provas WHERE id=?", (prova_id,))
        return True


def atualizar_tipo_questao(questao_id: int, tipo: str) -> bool:
    """Atualiza tipo da questão (multipla_escolha | verdadeiro_falso)."""
    if tipo not in ("multipla_escolha", "verdadeiro_falso"):
        return False
    with _conn() as con:
        existing = con.execute("SELECT id FROM questoes WHERE id=?", (questao_id,)).fetchone()
        if not existing:
            return False
        con.execute("UPDATE questoes SET tipo=? WHERE id=?", (tipo, questao_id))
        return True


def get_questao(questao_id: int) -> Optional[Dict]:
    with _conn() as con:
        return con.execute("SELECT * FROM questoes WHERE id=?", (questao_id,)).fetchone()


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


def relatorio_taxonomia(prova_id: int) -> Dict:
    """Árvore taxonômica com stats agregados por nó (roll-up dos descendentes).
    Só inclui questões com taxonomia_codigo preenchido."""
    with _conn() as con:
        rows = con.execute(
            """SELECT q.taxonomia_codigo, r.correta
               FROM respostas r
               JOIN questoes q ON q.id = r.questao_id
               WHERE q.prova_id = ?
                 AND q.taxonomia_codigo IS NOT NULL
                 AND q.taxonomia_codigo != ''""",
            (prova_id,),
        ).fetchall()

        if not rows:
            return {"arvore": []}

        all_nodes = con.execute(
            "SELECT id, codigo, label, nivel, parent_id FROM taxonomia"
        ).fetchall()

    by_codigo = {n["codigo"]: n for n in all_nodes}
    by_id = {n["id"]: n for n in all_nodes}

    stats: Dict[str, Dict] = {}
    for r in rows:
        codigo = r["taxonomia_codigo"]
        correta = bool(r["correta"])
        node = by_codigo.get(codigo)
        if not node:
            continue
        cur = node
        while cur is not None:
            c = cur["codigo"]
            if c not in stats:
                parent = by_id.get(cur["parent_id"]) if cur["parent_id"] else None
                stats[c] = {
                    "codigo": c,
                    "label": cur["label"],
                    "nivel": cur["nivel"],
                    "total": 0,
                    "acertos": 0,
                    "parent_codigo": parent["codigo"] if parent else None,
                }
            stats[c]["total"] += 1
            if correta:
                stats[c]["acertos"] += 1
            cur = by_id.get(cur["parent_id"]) if cur["parent_id"] else None

    for s in stats.values():
        s["percentual"] = round(s["acertos"] * 100 / s["total"]) if s["total"] else 0

    nodes_tree = {c: {**s, "filhos": []} for c, s in stats.items()}
    roots: List[Dict] = []
    for node in nodes_tree.values():
        pc = node["parent_codigo"]
        if pc and pc in nodes_tree:
            nodes_tree[pc]["filhos"].append(node)
        else:
            roots.append(node)

    def _sort_rec(n):
        n["filhos"].sort(key=lambda c: c["percentual"])
        for child in n["filhos"]:
            _sort_rec(child)

    for root in roots:
        _sort_rec(root)
    roots.sort(key=lambda r: r["label"])

    return {"arvore": roots}


def alunos_pontos_criticos(prova_id: int, top_n: int = 3) -> List[Dict]:
    """Para cada aluno, retorna os top_n nós taxonômicos com pior desempenho (< 70%)."""
    with _conn() as con:
        rows = con.execute(
            """SELECT a.id AS aluno_id, a.nome AS aluno_nome,
                      q.taxonomia_codigo, r.correta
               FROM respostas r
               JOIN questoes q ON q.id = r.questao_id
               JOIN alunos a ON a.id = r.aluno_id
               WHERE q.prova_id = ?
                 AND q.taxonomia_codigo IS NOT NULL
                 AND q.taxonomia_codigo != ''""",
            (prova_id,),
        ).fetchall()

        all_nodes = con.execute("SELECT codigo, label FROM taxonomia").fetchall()

    labels = {n["codigo"]: n["label"] for n in all_nodes}

    per_aluno: Dict[int, Dict] = {}
    for r in rows:
        aid = r["aluno_id"]
        codigo = r["taxonomia_codigo"]
        if aid not in per_aluno:
            per_aluno[aid] = {"aluno_id": aid, "nome": r["aluno_nome"], "por_no": {}}
        if codigo not in per_aluno[aid]["por_no"]:
            per_aluno[aid]["por_no"][codigo] = {"total": 0, "acertos": 0}
        per_aluno[aid]["por_no"][codigo]["total"] += 1
        if r["correta"]:
            per_aluno[aid]["por_no"][codigo]["acertos"] += 1

    result: List[Dict] = []
    for aluno in per_aluno.values():
        nos = []
        for codigo, s in aluno["por_no"].items():
            pct = round(s["acertos"] * 100 / s["total"]) if s["total"] else 0
            nos.append({
                "codigo": codigo,
                "label": labels.get(codigo, codigo),
                "total": s["total"],
                "acertos": s["acertos"],
                "percentual": pct,
            })
        nos.sort(key=lambda n: (n["percentual"], -n["total"]))
        criticos = [n for n in nos if n["percentual"] < 70][:top_n]
        result.append({
            "aluno_id": aluno["aluno_id"],
            "nome": aluno["nome"],
            "criticos": criticos,
        })
    result.sort(key=lambda a: (-len(a["criticos"]), a["nome"]))
    return result


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


# ── Prova manual (criada na plataforma, sem OCR) ──────────────────────────────

def criar_prova_manual(
    titulo: str,
    turma_id: Optional[int],
    disciplina: str,
    serie: str,
    usuario_id: Optional[int],
    tempo_limite_min: Optional[int] = None,
) -> int:
    """Cria prova manual no estado 'rascunho', sem questões."""
    with _conn() as con:
        return con.insert(
            """INSERT INTO provas
               (titulo, turma_id, disciplina, serie, arquivo_nome, ocr_method,
                total_questoes, usuario_id, origem, status, tempo_limite_min)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (titulo, turma_id, disciplina, serie, "", "manual", 0, usuario_id,
             "manual", "rascunho", tempo_limite_min),
        )


def adicionar_questao_manual(
    prova_id: int,
    numero: int,
    stem: str,
    alternativas: List[str],
    gabarito: str,
    tipo: str = "multipla_escolha",
    bloom_nivel: int = 0,
    bloom_nome: str = "",
    bloom_verbo: str = "",
    taxonomia_codigo: str = "",
    area_key: str = "",
    area_display: str = "",
    subarea_key: str = "geral",
    subarea_label: str = "Geral",
) -> int:
    """Insere questão criada manualmente. Salva alternativas como JSON e
    grava gabarito na tabela `gabarito` automaticamente."""
    alts_json = json.dumps(alternativas, ensure_ascii=False)
    with _conn() as con:
        qid = con.insert(
            """INSERT INTO questoes
               (prova_id, numero, texto, stem, alternativas, tipo,
                area_key, area_display, subarea_key, subarea_label,
                bloom_nivel, bloom_nome, bloom_verbo, taxonomia_codigo, bncc_codigos)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (prova_id, numero, stem, stem, alts_json, tipo,
             area_key, area_display, subarea_key or "geral", subarea_label or "Geral",
             bloom_nivel, bloom_nome, bloom_verbo, taxonomia_codigo, "[]"),
        )
        # Atualiza total_questoes
        con.execute(
            "UPDATE provas SET total_questoes = (SELECT COUNT(*) FROM questoes WHERE prova_id=?) WHERE id=?",
            (prova_id, prova_id),
        )
        # Grava gabarito
        if gabarito:
            con.execute("DELETE FROM gabarito WHERE prova_id=? AND numero_questao=?", (prova_id, numero))
            con.execute(
                "INSERT INTO gabarito (prova_id, numero_questao, alternativa) VALUES (?,?,?)",
                (prova_id, numero, gabarito.upper()),
            )
        return qid


def atualizar_questao_manual(
    questao_id: int,
    stem: str,
    alternativas: List[str],
    gabarito: str,
    tipo: str = "multipla_escolha",
    bloom_nivel: int = 0,
    bloom_nome: str = "",
    bloom_verbo: str = "",
    taxonomia_codigo: str = "",
    area_key: str = "",
    area_display: str = "",
    subarea_key: str = "geral",
    subarea_label: str = "Geral",
) -> bool:
    alts_json = json.dumps(alternativas, ensure_ascii=False)
    with _conn() as con:
        row = con.execute("SELECT prova_id, numero FROM questoes WHERE id=?", (questao_id,)).fetchone()
        if not row:
            return False
        con.execute(
            """UPDATE questoes SET stem=?, texto=?, alternativas=?, tipo=?,
                                   bloom_nivel=?, bloom_nome=?, bloom_verbo=?,
                                   taxonomia_codigo=?, area_key=?, area_display=?,
                                   subarea_key=?, subarea_label=?
                                   WHERE id=?""",
            (stem, stem, alts_json, tipo, bloom_nivel, bloom_nome, bloom_verbo,
             taxonomia_codigo, area_key, area_display,
             subarea_key or "geral", subarea_label or "Geral", questao_id),
        )
        if gabarito:
            con.execute("DELETE FROM gabarito WHERE prova_id=? AND numero_questao=?", (row["prova_id"], row["numero"]))
            con.execute(
                "INSERT INTO gabarito (prova_id, numero_questao, alternativa) VALUES (?,?,?)",
                (row["prova_id"], row["numero"], gabarito.upper()),
            )
        return True


def deletar_questao(questao_id: int) -> bool:
    with _conn() as con:
        row = con.execute("SELECT prova_id, numero FROM questoes WHERE id=?", (questao_id,)).fetchone()
        if not row:
            return False
        con.execute("DELETE FROM questoes WHERE id=?", (questao_id,))
        con.execute("DELETE FROM gabarito WHERE prova_id=? AND numero_questao=?", (row["prova_id"], row["numero"]))
        # Renumera questões restantes e atualiza total
        questoes = con.execute(
            "SELECT id, numero FROM questoes WHERE prova_id=? ORDER BY numero", (row["prova_id"],)
        ).fetchall()
        for novo_idx, q in enumerate(questoes, start=1):
            if q["numero"] != novo_idx:
                con.execute("UPDATE questoes SET numero=? WHERE id=?", (novo_idx, q["id"]))
                con.execute(
                    "UPDATE gabarito SET numero_questao=? WHERE prova_id=? AND numero_questao=?",
                    (novo_idx, row["prova_id"], q["numero"]),
                )
        con.execute(
            "UPDATE provas SET total_questoes = (SELECT COUNT(*) FROM questoes WHERE prova_id=?) WHERE id=?",
            (row["prova_id"], row["prova_id"]),
        )
        return True


def publicar_prova(prova_id: int, pin: str, tempo_limite_min: Optional[int] = None) -> bool:
    """Publica prova (status='publicada') com PIN ad-hoc."""
    with _conn() as con:
        existing = con.execute("SELECT id FROM provas WHERE id=?", (prova_id,)).fetchone()
        if not existing:
            return False
        if _BACKEND == "postgres":
            con.execute(
                "UPDATE provas SET status='publicada', pin=?, tempo_limite_min=?, publicada_em=NOW(), encerrada_em=NULL WHERE id=?",
                (pin, tempo_limite_min, prova_id),
            )
        else:
            con.execute(
                "UPDATE provas SET status='publicada', pin=?, tempo_limite_min=?, publicada_em=datetime('now','localtime'), encerrada_em=NULL WHERE id=?",
                (pin, tempo_limite_min, prova_id),
            )
        return True


def encerrar_prova(prova_id: int) -> bool:
    with _conn() as con:
        existing = con.execute("SELECT id FROM provas WHERE id=?", (prova_id,)).fetchone()
        if not existing:
            return False
        if _BACKEND == "postgres":
            con.execute(
                "UPDATE provas SET status='encerrada', encerrada_em=NOW() WHERE id=?",
                (prova_id,),
            )
        else:
            con.execute(
                "UPDATE provas SET status='encerrada', encerrada_em=datetime('now','localtime') WHERE id=?",
                (prova_id,),
            )
        return True


def get_questoes_para_aluno(prova_id: int) -> List[Dict]:
    """Retorna questões da prova SEM expor o gabarito ao aluno.
    Inclui o campo `alternativas` decodificado."""
    with _conn() as con:
        rows = con.execute(
            """SELECT id, numero, stem, alternativas, tipo
               FROM questoes WHERE prova_id=? ORDER BY numero""",
            (prova_id,),
        ).fetchall()
        for r in rows:
            try:
                r["alternativas"] = json.loads(r.get("alternativas") or "[]")
            except Exception:
                r["alternativas"] = []
        return rows


# ── Prova Acessos (sessão do aluno na prova) ──────────────────────────────────

def get_acesso(prova_id: int, aluno_id: int) -> Optional[Dict]:
    with _conn() as con:
        return con.execute(
            "SELECT * FROM prova_acessos WHERE prova_id=? AND aluno_id=?",
            (prova_id, aluno_id),
        ).fetchone()


def criar_ou_obter_acesso(
    prova_id: int,
    aluno_id: int,
    fingerprint: str,
    ip: str,
    user_agent: str,
) -> Dict:
    """Cria acesso ou retorna o existente.
    Bloqueio: se já existe e o fingerprint é diferente E não foi liberado, lança ValueError."""
    existing = get_acesso(prova_id, aluno_id)
    if existing:
        # Já finalizado? não pode reentrar
        if existing.get("finished_at"):
            raise ValueError("prova_ja_finalizada")
        # Mesmo dispositivo? OK, continua
        if existing.get("fingerprint") == fingerprint:
            return existing
        # Foi liberado pelo professor? OK, atualiza fingerprint e libera novamente
        if existing.get("liberado_em"):
            with _conn() as con:
                con.execute(
                    "UPDATE prova_acessos SET fingerprint=?, ip=?, user_agent=?, liberado_em=NULL WHERE id=?",
                    (fingerprint, ip, user_agent, existing["id"]),
                )
            return get_acesso(prova_id, aluno_id)  # type: ignore
        # Bloqueado
        raise ValueError("dispositivo_diferente")

    # Cria novo
    with _conn() as con:
        if _BACKEND == "postgres":
            con.execute(
                """INSERT INTO prova_acessos (prova_id, aluno_id, fingerprint, ip, user_agent, started_at)
                   VALUES (?,?,?,?,?, NOW())""",
                (prova_id, aluno_id, fingerprint, ip, user_agent),
            )
        else:
            con.execute(
                """INSERT INTO prova_acessos (prova_id, aluno_id, fingerprint, ip, user_agent, started_at)
                   VALUES (?,?,?,?,?, datetime('now','localtime'))""",
                (prova_id, aluno_id, fingerprint, ip, user_agent),
            )
    return get_acesso(prova_id, aluno_id)  # type: ignore


def finalizar_acesso(prova_id: int, aluno_id: int) -> bool:
    with _conn() as con:
        acesso = con.execute(
            "SELECT id, finished_at FROM prova_acessos WHERE prova_id=? AND aluno_id=?",
            (prova_id, aluno_id),
        ).fetchone()
        if not acesso:
            return False
        if acesso.get("finished_at"):
            return True
        if _BACKEND == "postgres":
            con.execute(
                "UPDATE prova_acessos SET finished_at=NOW() WHERE id=?", (acesso["id"],)
            )
        else:
            con.execute(
                "UPDATE prova_acessos SET finished_at=datetime('now','localtime') WHERE id=?",
                (acesso["id"],),
            )
        return True


def liberar_relogin(prova_id: int, aluno_id: int) -> bool:
    """Permite que o aluno faça login de novo (zera fingerprint).
    Não funciona se a prova já foi finalizada — nesse caso o professor precisa
    chamar reset_prova_aluno."""
    with _conn() as con:
        acesso = con.execute(
            "SELECT id, finished_at FROM prova_acessos WHERE prova_id=? AND aluno_id=?",
            (prova_id, aluno_id),
        ).fetchone()
        if not acesso:
            return False
        if acesso.get("finished_at"):
            return False
        if _BACKEND == "postgres":
            con.execute(
                "UPDATE prova_acessos SET fingerprint=NULL, liberado_em=NOW() WHERE id=?",
                (acesso["id"],),
            )
        else:
            con.execute(
                "UPDATE prova_acessos SET fingerprint=NULL, liberado_em=datetime('now','localtime') WHERE id=?",
                (acesso["id"],),
            )
        return True


def listar_acessos_prova(prova_id: int) -> List[Dict]:
    """Para o monitor do professor: lista alunos da turma da prova com status."""
    with _conn() as con:
        prova = con.execute("SELECT turma_id FROM provas WHERE id=?", (prova_id,)).fetchone()
        if not prova or not prova.get("turma_id"):
            return []
        return con.execute(
            """SELECT a.id AS aluno_id, a.nome AS aluno_nome, a.ra,
                      pa.started_at, pa.finished_at, pa.fingerprint, pa.liberado_em,
                      pa.ip, pa.user_agent
               FROM alunos a
               LEFT JOIN prova_acessos pa
                 ON pa.aluno_id = a.id AND pa.prova_id = ?
               WHERE a.turma_id = ?
               ORDER BY a.nome""",
            (prova_id, prova["turma_id"]),
        ).fetchall()


def listar_provas_em_aberto_para_aluno(aluno_id: int) -> List[Dict]:
    """Lista provas publicadas da turma do aluno, marcando quais ele já fez."""
    with _conn() as con:
        aluno = con.execute("SELECT turma_id FROM alunos WHERE id=?", (aluno_id,)).fetchone()
        if not aluno or not aluno.get("turma_id"):
            return []
        return con.execute(
            """SELECT p.id, p.titulo, p.disciplina, p.serie, p.total_questoes,
                      p.tempo_limite_min, p.publicada_em,
                      pa.started_at, pa.finished_at
               FROM provas p
               LEFT JOIN prova_acessos pa
                 ON pa.prova_id = p.id AND pa.aluno_id = ?
               WHERE p.turma_id = ? AND p.status = 'publicada'
               ORDER BY p.publicada_em DESC""",
            (aluno_id, aluno["turma_id"]),
        ).fetchall()


def get_prova_por_pin(pin: str) -> Optional[Dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM provas WHERE pin=? AND status='publicada'",
            (pin.strip(),),
        ).fetchall()
        return rows[0] if rows else None


def salvar_resposta_unica(
    aluno_id: int,
    questao_id: int,
    resposta: str,
    tempo_segundos: Optional[int] = None,
) -> Dict:
    """Salva uma resposta do aluno (online) e calcula automaticamente o gabarito/correta."""
    with _conn() as con:
        q = con.execute(
            "SELECT prova_id, numero FROM questoes WHERE id=?", (questao_id,)
        ).fetchone()
        if not q:
            return {"ok": False, "erro": "questao_nao_encontrada"}
        gab_row = con.execute(
            "SELECT alternativa FROM gabarito WHERE prova_id=? AND numero_questao=?",
            (q["prova_id"], q["numero"]),
        ).fetchone()
        gab = (gab_row["alternativa"] if gab_row else "") or ""
        resp = (resposta or "").strip().upper()
        correta = 1 if (resp and gab and resp == gab.upper()) else 0
        con.execute(
            """INSERT INTO respostas (aluno_id, questao_id, resposta, gabarito, correta, tempo_segundos)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(aluno_id, questao_id) DO UPDATE
               SET resposta=excluded.resposta, gabarito=excluded.gabarito,
                   correta=excluded.correta, tempo_segundos=excluded.tempo_segundos""",
            (aluno_id, questao_id, resp, gab, correta, tempo_segundos),
        )
        return {"ok": True, "correta": bool(correta)}


# Auto-init on import
init_db()
