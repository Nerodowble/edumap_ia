"""
Classificação respeita a etapa da turma e aceita o label da disciplina (checklist A9).
"""
import uuid

import pytest

import api as _api
from database.db import _conn
from tests.test_isolamento import _professor

LABEL = "Ética Teste A9"


@pytest.fixture(scope="module")
def taxonomia_duplicada():
    """Mesma matéria (slug e label) em dois cursos, com a mesma palavra-chave."""
    sufixo = uuid.uuid4().hex[:6]
    with _conn() as con:
        for etapa in (f"curso_a_{sufixo}", f"curso_b_{sufixo}"):
            raiz = con.insert(
                "INSERT INTO taxonomia (etapa, materia, codigo, label, nivel, parent_id, palavras_chave) "
                "VALUES (?,?,?,?,?,?,?)",
                (etapa, "etica_a9", f"{etapa}.etica_a9", LABEL, 1, None, ""),
            )
            con.insert(
                "INSERT INTO taxonomia (etapa, materia, codigo, label, nivel, parent_id, palavras_chave) "
                "VALUES (?,?,?,?,?,?,?)",
                (etapa, "etica_a9", f"{etapa}.etica_a9.sigilo", "Sigilo", 2, raiz, "sigilo,confidencialidade"),
            )
    return f"curso_a_{sufixo}", f"curso_b_{sufixo}"


@pytest.fixture(autouse=True)
def auth_real(monkeypatch):
    monkeypatch.setattr(_api, "SKIP_AUTH", False)


@pytest.mark.parametrize("qual", [0, 1])
def test_classifica_na_arvore_da_etapa_da_turma(client, taxonomia_duplicada, qual):
    etapa = taxonomia_duplicada[qual]
    h = _professor(client, "Escola A9")
    turma = client.post("/turmas", headers=h, json={"nome": "T", "escola": "Escola A9", "etapa": etapa}).json()
    prova = client.post("/provas/manual", headers=h,
                        json={"titulo": "P", "turma_id": turma["id"], "disciplina": LABEL}).json()
    r = client.post(f"/provas/{prova['id']}/questoes", headers=h, json={
        "stem": "Explique por que o sigilo profissional é importante.",
        "alternativas": ["a", "b"], "gabarito": "A",
    })
    assert r.status_code == 201, r.text
    q = client.get(f"/provas/{prova['id']}/questoes", headers=h).json()[0]
    # Label da disciplina (que não está no SUBJECT_TO_KEY) foi reconhecido,
    # e o nó escolhido é o da etapa da turma — não o do outro curso
    assert q["taxonomia_codigo"] == f"{etapa}.etica_a9.sigilo"
