"""
Fluxo da prova online e cálculo de nota (checklist C7, A1, A2, A4, A5, A6).
"""
import pytest

import api as _api
from database.db import _conn
from tests.test_isolamento import _cenario


@pytest.fixture(autouse=True)
def auth_real(monkeypatch):
    monkeypatch.setattr(_api, "SKIP_AUTH", False)


@pytest.fixture
def c(client):
    return _cenario(client, "Escola Online")


def _publicar(client, c, tempo=None):
    r = client.post(f"/provas/{c['prova']['id']}/publicar", headers=c["h"],
                    json={"tempo_limite_min": tempo} if tempo else {})
    assert r.status_code == 200, r.text
    return r.json()["pin"]


def _login_aluno(client, c):
    r = client.post("/aluno/auth", json={"nome": c["nome_aluno"], "ra": c["ra"]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _iniciar(client, c, tempo=None):
    pin = _publicar(client, c, tempo)
    ha = _login_aluno(client, c)
    r = client.post(f"/aluno/provas/{c['prova']['id']}/iniciar", headers=ha, json={"pin": pin})
    assert r.status_code == 200, r.text
    return ha


def _relatorio_do_aluno(client, c):
    rel = client.get(f"/provas/{c['prova']['id']}/relatorio/turma", headers=c["h"]).json()
    return next(x for x in rel if x["aluno"]["id"] == c["aluno"]["id"])


# ── C7: PIN / login errado não é "sessão expirada" ───────────────────────────

class TestErrosDeCredencial:
    def test_pin_errado_422_e_token_continua_valido(self, client, c):
        _publicar(client, c)
        ha = _login_aluno(client, c)
        r = client.post(f"/aluno/provas/{c['prova']['id']}/iniciar", headers=ha, json={"pin": "000000"})
        assert r.status_code == 422
        assert "PIN" in r.json()["detail"]
        assert client.get("/aluno/me", headers=ha).status_code == 200

    def test_aluno_de_outra_turma_recebe_403_antes_de_testar_pin(self, client, c):
        outro = _cenario(client, "Escola Outra")
        _publicar(client, c)
        ha = _login_aluno(client, outro)
        r = client.post(f"/aluno/provas/{c['prova']['id']}/iniciar", headers=ha, json={"pin": "000000"})
        assert r.status_code == 403

    def test_login_aluno_nome_ra_errado_401(self, client, c):
        r = client.post("/aluno/auth", json={"nome": c["nome_aluno"], "ra": "nao-existe"})
        assert r.status_code == 401


# ── A6: RA em branco ─────────────────────────────────────────────────────────

class TestLoginSemRA:
    def test_ra_so_espacos_nao_loga_aluno_sem_ra(self, client, c):
        nome = "Aluno Sem RA Teste"
        client.post(f"/turmas/{c['turma']['id']}/alunos", json={"nome": nome}, headers=c["h"])
        r = client.post("/aluno/auth", json={"nome": nome, "ra": "   "})
        assert r.status_code == 401


# ── A4: respostas salvas voltam do servidor ──────────────────────────────────

class TestRespostasDoServidor:
    def test_questoes_trazem_respostas_salvas_e_segundos(self, client, c):
        ha = _iniciar(client, c)
        q1 = c["questoes"][0]
        client.post(f"/aluno/provas/{c['prova']['id']}/responder", headers=ha,
                    json={"questao_id": q1["id"], "resposta": "b"})
        d = client.get(f"/aluno/provas/{c['prova']['id']}/questoes", headers=ha).json()
        assert d["respostas"] == {str(q1["id"]): "B"}
        assert isinstance(d["segundos_decorridos"], int) and d["segundos_decorridos"] >= 0
        # O gabarito nunca vai para o aluno
        assert all("gabarito" not in q for q in d["questoes"])


# ── A5: tempo limite aplicado no servidor ────────────────────────────────────

class TestTempoLimite:
    def test_resposta_recusada_apos_tempo_esgotado(self, client, c):
        ha = _iniciar(client, c, tempo=1)
        with _conn() as con:
            con.execute("UPDATE prova_acessos SET started_at=? WHERE prova_id=? AND aluno_id=?",
                        ("2000-01-01 00:00:00", c["prova"]["id"], c["aluno"]["id"]))
        r = client.post(f"/aluno/provas/{c['prova']['id']}/responder", headers=ha,
                        json={"questao_id": c["questoes"][0]["id"], "resposta": "A"})
        assert r.status_code == 403
        assert "tempo" in r.json()["detail"].lower()
        # Finalizar continua permitido
        assert client.post(f"/aluno/provas/{c['prova']['id']}/finalizar", headers=ha).status_code == 200

    def test_dentro_do_tempo_aceita(self, client, c):
        ha = _iniciar(client, c, tempo=30)
        r = client.post(f"/aluno/provas/{c['prova']['id']}/responder", headers=ha,
                        json={"questao_id": c["questoes"][0]["id"], "resposta": "A"})
        assert r.status_code == 200


# ── A1 / A2: nota ────────────────────────────────────────────────────────────

class TestNota:
    def test_questao_em_branco_conta_como_erro(self, client, c):
        """Responder 1 de 2 corretamente = 50%, não 100%."""
        ha = _iniciar(client, c)
        client.post(f"/aluno/provas/{c['prova']['id']}/responder", headers=ha,
                    json={"questao_id": c["questoes"][0]["id"], "resposta": "A"})
        client.post(f"/aluno/provas/{c['prova']['id']}/finalizar", headers=ha)
        rel = _relatorio_do_aluno(client, c)
        assert rel["total"] == 2
        assert rel["respondidas"] == 1
        assert rel["acertos"] == 1
        assert rel["percentual"] == 50

    def test_trocar_gabarito_recalcula_sem_relancar(self, client, c):
        pid = c["prova"]["id"]
        client.post(f"/provas/{pid}/gabarito", headers=c["h"], json={"gabarito": {"1": "A", "2": "A"}})
        client.post(f"/provas/{pid}/lancar", headers=c["h"],
                    json={"respostas": {str(c["aluno"]["id"]): {"1": "B", "2": "B"}}})
        assert _relatorio_do_aluno(client, c)["acertos"] == 0

        client.post(f"/provas/{pid}/gabarito", headers=c["h"], json={"gabarito": {"1": "B", "2": "B"}})
        assert _relatorio_do_aluno(client, c)["acertos"] == 2

    def test_editar_gabarito_da_questao_recalcula(self, client, c):
        pid = c["prova"]["id"]
        q1 = c["questoes"][0]
        client.post(f"/provas/{pid}/lancar", headers=c["h"],
                    json={"respostas": {str(c["aluno"]["id"]): {"1": "B"}}})
        assert _relatorio_do_aluno(client, c)["acertos"] == 0
        client.put(f"/provas/{pid}/questoes/{q1['id']}", headers=c["h"], json={
            "stem": q1["stem"], "alternativas": ["4", "6", "8"], "gabarito": "B",
        })
        assert _relatorio_do_aluno(client, c)["acertos"] == 1
