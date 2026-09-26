"""
Isolamento de dados entre professores e entre provas (checklist C2, C3, C4).
Desliga SKIP_AUTH para usar usuários e tokens reais.
"""
import uuid

import pytest

import api as _api
from database import usuarios as db_usuarios

SENHA = "senha-forte-123"


@pytest.fixture(autouse=True)
def auth_real(monkeypatch):
    monkeypatch.setattr(_api, "SKIP_AUTH", False)


def _professor(client, escola):
    email = f"prof.{uuid.uuid4().hex[:8]}@teste.com"
    db_usuarios.criar_usuario("Prof", email, _api._hash(SENHA), "professor", escola)
    tok = client.post("/auth/login", json={"email": email, "senha": SENHA}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def _cenario(client, escola):
    """Professor com turma, aluno (com R.A.) e prova manual publicada de 2 questões."""
    h = _professor(client, escola)
    turma = client.post("/turmas", json={"nome": f"Turma {escola}", "escola": escola}, headers=h).json()
    ra = uuid.uuid4().hex[:6]
    nome_aluno = f"Aluno {uuid.uuid4().hex[:6]}"
    aluno = client.post(f"/turmas/{turma['id']}/alunos",
                        json={"nome": nome_aluno, "ra": ra}, headers=h).json()
    prova = client.post("/provas/manual", json={"titulo": "P", "turma_id": turma["id"]}, headers=h).json()
    for stem in ("Quanto é 2+2?", "Quanto é 3+3?"):
        r = client.post(f"/provas/{prova['id']}/questoes", headers=h, json={
            "stem": stem, "alternativas": ["4", "6", "8"], "gabarito": "A",
        })
        assert r.status_code == 201, r.text
    questoes = client.get(f"/provas/{prova['id']}/questoes", headers=h).json()
    return {"h": h, "turma": turma, "aluno": aluno, "nome_aluno": nome_aluno, "ra": ra,
            "prova": prova, "questoes": questoes}


@pytest.fixture
def a(client):
    return _cenario(client, "Escola A")


@pytest.fixture
def b(client):
    return _cenario(client, "Escola B")


# ── C2: questões ─────────────────────────────────────────────────────────────

class TestIsolamentoQuestoes:
    def test_nao_edita_questao_de_outra_prova(self, client, a, b):
        qb = b["questoes"][0]
        r = client.put(f"/provas/{a['prova']['id']}/questoes/{qb['id']}", headers=a["h"], json={
            "stem": "HACKEADO", "alternativas": ["x", "y"], "gabarito": "B",
        })
        assert r.status_code == 404
        stem = client.get(f"/provas/{b['prova']['id']}/questoes", headers=b["h"]).json()[0]["stem"]
        assert stem != "HACKEADO"

    def test_nao_apaga_questao_de_outra_prova(self, client, a, b):
        qb = b["questoes"][0]
        r = client.delete(f"/provas/{a['prova']['id']}/questoes/{qb['id']}", headers=a["h"])
        assert r.status_code == 404
        assert len(client.get(f"/provas/{b['prova']['id']}/questoes", headers=b["h"]).json()) == 2

    def test_nao_muda_tipo_de_questao_de_outra_prova(self, client, a, b):
        qb = b["questoes"][0]
        r = client.put(f"/provas/{a['prova']['id']}/questoes/{qb['id']}/tipo",
                       headers=a["h"], json={"tipo": "verdadeiro_falso"})
        assert r.status_code == 404

    def test_nao_acessa_prova_alheia(self, client, a, b):
        r = client.get(f"/provas/{b['prova']['id']}/questoes", headers=a["h"])
        assert r.status_code == 403

    def test_dono_ainda_edita_a_propria_questao(self, client, a):
        qa = a["questoes"][0]
        r = client.put(f"/provas/{a['prova']['id']}/questoes/{qa['id']}", headers=a["h"], json={
            "stem": "Quanto é 5+5?", "alternativas": ["10", "11"], "gabarito": "A",
        })
        assert r.status_code == 200


# ── C3: respostas lançadas pelo professor ────────────────────────────────────

class TestIsolamentoRespostas:
    def test_respostas_para_aluno_de_outra_turma_403(self, client, a, b):
        r = client.post(f"/provas/{a['prova']['id']}/respostas", headers=a["h"], json={
            "aluno_id": b["aluno"]["id"], "respostas": {"1": {"resposta": "A"}},
        })
        assert r.status_code == 403
        rel = client.get(f"/provas/{a['prova']['id']}/relatorio/turma", headers=a["h"]).json()
        assert all(x["aluno"]["id"] != b["aluno"]["id"] for x in rel)

    def test_lancar_com_aluno_de_outra_turma_403_nada_gravado(self, client, a, b):
        r = client.post(f"/provas/{a['prova']['id']}/lancar", headers=a["h"], json={"respostas": {
            str(a["aluno"]["id"]): {"1": "A"},
            str(b["aluno"]["id"]): {"1": "A"},
        }})
        assert r.status_code == 403
        rel = client.get(f"/provas/{a['prova']['id']}/relatorio/turma", headers=a["h"]).json()
        assert rel == []  # validação acontece antes de gravar qualquer aluno

    def test_correta_do_cliente_e_ignorada(self, client, a):
        """Gabarito da prova é A; cliente diz que 'B' está correta — servidor recalcula."""
        client.post(f"/provas/{a['prova']['id']}/gabarito", headers=a["h"],
                    json={"gabarito": {"1": "A", "2": "A"}})
        r = client.post(f"/provas/{a['prova']['id']}/respostas", headers=a["h"], json={
            "aluno_id": a["aluno"]["id"],
            "respostas": {"1": {"resposta": "B", "gabarito": "B", "correta": True}},
        })
        assert r.status_code == 201
        rel = client.get(f"/provas/{a['prova']['id']}/relatorio/turma", headers=a["h"]).json()
        linha = next(x for x in rel if x["aluno"]["id"] == a["aluno"]["id"])
        assert linha["acertos"] == 0

    def test_lancar_proprio_aluno_funciona(self, client, a):
        r = client.post(f"/provas/{a['prova']['id']}/lancar", headers=a["h"],
                        json={"respostas": {str(a["aluno"]["id"]): {"1": "A"}}})
        assert r.status_code == 201


# ── C4: aluno respondendo questão de outra prova ─────────────────────────────

def _aluno_na_prova(client, c):
    pub = client.post(f"/provas/{c['prova']['id']}/publicar", headers=c["h"], json={})
    assert pub.status_code == 200, pub.text
    tok = client.post("/aluno/auth", json={"nome": c["nome_aluno"], "ra": c["ra"]}).json()["token"]
    ha = {"Authorization": f"Bearer {tok}"}
    r = client.post(f"/aluno/provas/{c['prova']['id']}/iniciar", headers=ha, json={"pin": pub.json()["pin"]})
    assert r.status_code == 200, r.text
    return ha


class TestIsolamentoAluno:
    def test_aluno_nao_responde_questao_de_outra_prova(self, client, a, b):
        ha = _aluno_na_prova(client, a)
        qb = b["questoes"][0]
        r = client.post(f"/aluno/provas/{a['prova']['id']}/responder", headers=ha,
                        json={"questao_id": qb["id"], "resposta": "A"})
        assert r.status_code == 400
        rel = client.get(f"/provas/{b['prova']['id']}/relatorio/turma", headers=b["h"]).json()
        assert all(x["aluno"]["id"] != a["aluno"]["id"] for x in rel)

    def test_aluno_responde_questao_da_propria_prova(self, client, a):
        ha = _aluno_na_prova(client, a)
        qa = a["questoes"][0]
        r = client.post(f"/aluno/provas/{a['prova']['id']}/responder", headers=ha,
                        json={"questao_id": qa["id"], "resposta": "A"})
        assert r.status_code == 200


class TestIsolamentoUpload:
    def test_upload_para_turma_alheia_403_sem_rodar_ocr(self, client, a, b, monkeypatch):
        chamou = []
        monkeypatch.setattr(_api, "extract_text_from_file", lambda *x, **k: chamou.append(1) or ("", "digital"))
        r = client.post("/provas/upload", headers=a["h"],
                        data={"year_level": "8º ano EF", "turma_id": str(b["turma"]["id"])},
                        files={"file": ("p.pdf", b"%PDF-1.4", "application/pdf")})
        assert r.status_code == 403  # antes: 500 "Erro ao processar prova: 403", depois do OCR
        assert chamou == []


class TestListaProvasOnline:
    def test_professor_ve_so_as_proprias(self, client, a, b):
        ids = [p["id"] for p in client.get("/provas/online", headers=a["h"]).json()]
        assert a["prova"]["id"] in ids
        assert b["prova"]["id"] not in ids

    def test_traz_nome_da_turma_e_status(self, client, a):
        p = next(x for x in client.get("/provas/online", headers=a["h"]).json() if x["id"] == a["prova"]["id"])
        assert p["turma_nome"] == a["turma"]["nome"]
        assert p["status"] == "rascunho"
        assert p["total_questoes"] == 2
