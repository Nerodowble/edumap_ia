"""
Configuração global de testes — EduMap IA
Isola o banco de dados real usando um DB temporário.
"""
import os
import sys
import subprocess
import tempfile

import pytest

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

# ── Isola banco de dados ANTES de qualquer import da api ─────────────────────
os.environ["SKIP_AUTH"] = "true"  # Desativa JWT nos testes

_TMP_DIR = tempfile.mkdtemp(prefix="edumap_test_")
_TEST_DB = os.path.join(_TMP_DIR, "test_edumap.db")

from database import db as _db  # noqa: E402
_db.DB_PATH = _TEST_DB
_db.init_db()

# ── Importa api depois do patch ───────────────────────────────────────────────
from starlette.testclient import TestClient  # noqa: E402
import api as _api  # noqa: E402


# ── Fixtures compartilhadas ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client():
    with TestClient(_api.app) as c:
        yield c


@pytest.fixture(scope="session")
def prova_pdf():
    path = os.path.join(ROOT, "provas_exemplo", "prova_exemplo_8ano.pdf")
    if not os.path.exists(path):
        subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "gerar_prova_exemplo.py")],
            check=True,
        )
    return path


@pytest.fixture(scope="session")
def turma_criada(client):
    r = client.post("/turmas", json={"nome": "8ºB Teste", "escola": "Escola Teste", "disciplina": "Múltiplas"})
    assert r.status_code == 201
    return r.json()


@pytest.fixture(scope="session")
def aluno_criado(client, turma_criada):
    r = client.post(f"/turmas/{turma_criada['id']}/alunos", json={"nome": "Aluno Teste"})
    assert r.status_code == 201
    return r.json()


@pytest.fixture(scope="session")
def prova_enviada(client, turma_criada, prova_pdf):
    with open(prova_pdf, "rb") as f:
        r = client.post(
            "/provas/upload",
            data={
                "year_level": "8º ano EF",
                "subject": "Detectar automaticamente",
                "turma_id": str(turma_criada["id"]),
            },
            files={"file": ("prova_8ano.pdf", f, "application/pdf")},
        )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="session")
def prova_com_gabarito(client, turma_criada, prova_pdf):
    """Segunda prova com gabarito definido — usada pelos testes de lançamento."""
    with open(prova_pdf, "rb") as f:
        r = client.post(
            "/provas/upload",
            data={"year_level": "8º ano EF", "turma_id": str(turma_criada["id"])},
            files={"file": ("prova_gabarito.pdf", f, "application/pdf")},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    prova_id = data["prova_id"]
    questions = data["questions"]

    # Gabarito alternando A/B/C/D para ter diversidade nos acertos
    alts = ["A", "B", "C", "D"]
    gabarito = {str(q["number"]): alts[i % 4] for i, q in enumerate(questions)}
    rg = client.post(f"/provas/{prova_id}/gabarito", json={"gabarito": gabarito})
    assert rg.status_code == 201

    return {"prova_id": prova_id, "questions": questions, "gabarito": gabarito}


@pytest.fixture(scope="session")
def aluno_gabarito(client, turma_criada):
    """Aluno dedicado para testes de lançamento (separado do aluno_criado)."""
    r = client.post(f"/turmas/{turma_criada['id']}/alunos", json={"nome": "Aluno Gabarito"})
    assert r.status_code == 201
    return r.json()


@pytest.fixture(scope="session")
def aluno_gabarito2(client, turma_criada):
    """Segundo aluno para testes de múltiplos alunos."""
    r = client.post(f"/turmas/{turma_criada['id']}/alunos", json={"nome": "Aluno Gabarito 2"})
    assert r.status_code == 201
    return r.json()
