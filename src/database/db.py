"""
SQLite database manager for EduMap IA.
Stores: turmas, alunos, provas, questoes, respostas.
DB file: edumap_ia/data/edumap.db
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "edumap.db")


def _ensure_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def _conn():
    _ensure_dir()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS turmas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT NOT NULL,
            escola      TEXT,
            disciplina  TEXT,
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
        """)


# ── Turmas ────────────────────────────────────────────────────────────────────

def criar_turma(nome: str, escola: str = "", disciplina: str = "") -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO turmas (nome, escola, disciplina) VALUES (?,?,?)",
            (nome, escola, disciplina),
        )
        return cur.lastrowid


def listar_turmas() -> List[Dict]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM turmas ORDER BY nome").fetchall()
        return [dict(r) for r in rows]


def get_turma(turma_id: int) -> Optional[Dict]:
    with _conn() as con:
        row = con.execute("SELECT * FROM turmas WHERE id=?", (turma_id,)).fetchone()
        return dict(row) if row else None


# ── Alunos ────────────────────────────────────────────────────────────────────

def criar_aluno(nome: str, turma_id: int) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO alunos (nome, turma_id) VALUES (?,?)", (nome, turma_id)
        )
        return cur.lastrowid


def listar_alunos(turma_id: int) -> List[Dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM alunos WHERE turma_id=? ORDER BY nome", (turma_id,)
        ).fetchall()
        return [dict(r) for r in rows]


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
        cur = con.execute(
            """INSERT INTO provas
               (titulo, turma_id, disciplina, serie, arquivo_nome, ocr_method, total_questoes)
               VALUES (?,?,?,?,?,?,?)""",
            (titulo, turma_id, disciplina, serie, arquivo_nome, ocr_method, len(questoes)),
        )
        prova_id = cur.lastrowid

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
            rows = con.execute(
                "SELECT * FROM provas WHERE turma_id=? ORDER BY criado_em DESC", (turma_id,)
            ).fetchall()
        else:
            rows = con.execute("SELECT * FROM provas ORDER BY criado_em DESC").fetchall()
        return [dict(r) for r in rows]


def get_questoes_prova(prova_id: int) -> List[Dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM questoes WHERE prova_id=? ORDER BY numero", (prova_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["bncc_skills"] = [{"codigo": c} for c in json.loads(d.get("bncc_codigos") or "[]")]
            result.append(d)
        return result


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

        by_bloom: Dict[str, Dict] = {}
        by_area: Dict[str, Dict] = {}
        total, acertos = 0, 0

        for r in rows:
            total += 1
            ok = bool(r["correta"])
            if ok:
                acertos += 1

            bn = r["bloom_nome"] or "Indefinido"
            if bn not in by_bloom:
                by_bloom[bn] = {"total": 0, "acertos": 0}
            by_bloom[bn]["total"] += 1
            if ok:
                by_bloom[bn]["acertos"] += 1

            area = r["area_display"] or "Indefinida"
            if area not in by_area:
                by_area[area] = {"total": 0, "acertos": 0}
            by_area[area]["total"] += 1
            if ok:
                by_area[area]["acertos"] += 1

        return {
            "aluno": dict(aluno) if aluno else {},
            "total": total,
            "acertos": acertos,
            "percentual": round(acertos * 100 / total) if total else 0,
            "por_bloom": by_bloom,
            "por_area": by_area,
            "detalhes": [dict(r) for r in rows],
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
    """
    Returns a nested dict for the drill-down report:
    area -> subarea -> bloom_level -> list of {aluno, acertos, total, pct}
    Also includes per-question breakdown.
    """
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

    # Build nested structure: area -> subarea -> bloom -> [aluno stats]
    tree: Dict = {}
    aluno_sub_bloom: Dict = {}  # (aluno_id, subarea_key, bloom_nivel) -> {ok, total, nome}

    for r in rows:
        area   = r["area_display"] or "Geral"
        sub_k  = r["subarea_key"]  or "geral"
        sub_l  = r["subarea_label"] or "Geral"
        bloom  = r["bloom_nivel"]  or 0
        bloom_n= r["bloom_nome"]   or "—"
        aluno  = r["aluno_id"]
        nome   = r["aluno_nome"]
        ok     = bool(r["correta"])

        if area not in tree:
            tree[area] = {}
        if sub_k not in tree[area]:
            tree[area][sub_k] = {"label": sub_l, "bloom": {}}
        if bloom not in tree[area][sub_k]["bloom"]:
            tree[area][sub_k]["bloom"][bloom] = {"nome": bloom_n, "alunos": {}}

        aluno_stats = tree[area][sub_k]["bloom"][bloom]["alunos"]
        if aluno not in aluno_stats:
            aluno_stats[aluno] = {"nome": nome, "ok": 0, "total": 0}
        aluno_stats[aluno]["total"] += 1
        if ok:
            aluno_stats[aluno]["ok"] += 1

    # Convert aluno dicts to sorted lists with pct
    for area in tree:
        for sub in tree[area]:
            for bloom in tree[area][sub]["bloom"]:
                alunos = tree[area][sub]["bloom"][bloom]["alunos"]
                lst = []
                for aid, stat in alunos.items():
                    pct = round(stat["ok"] * 100 / stat["total"]) if stat["total"] else 0
                    lst.append({"aluno_id": aid, "nome": stat["nome"],
                                "ok": stat["ok"], "total": stat["total"], "pct": pct})
                lst.sort(key=lambda x: x["pct"])
                tree[area][sub]["bloom"][bloom]["alunos"] = lst

                # Aggregate for subarea+bloom level
                t_ok    = sum(s["ok"]    for s in lst)
                t_total = sum(s["total"] for s in lst)
                tree[area][sub]["bloom"][bloom]["pct_turma"] = (
                    round(t_ok * 100 / t_total) if t_total else 0
                )

    return tree


# Auto-init on import
init_db()
