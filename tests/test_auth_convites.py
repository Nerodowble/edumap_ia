"""
Testes de autenticação real + convites de cadastro (checklist C1/T1).
Desliga SKIP_AUTH só neste módulo para exercitar JWT e permissões.
"""
import re
import uuid

import pytest

import api as _api
from database import convites as db_convites
from database import usuarios as db_usuarios
from database.db import _conn

SENHA = "senha-forte-123"
CODIGO_RE = re.compile(r"^EDU-[2-9A-HJ-NP-Z]{4}-[2-9A-HJ-NP-Z]{4}$")


@pytest.fixture(autouse=True)
def auth_real(monkeypatch):
    monkeypatch.setattr(_api, "SKIP_AUTH", False)


def _email(prefixo="u"):
    return f"{prefixo}.{uuid.uuid4().hex[:8]}@teste.com"


def _criar_usuario(role, escola=""):
    email = _email(role)
    db_usuarios.criar_usuario(f"User {role}", email, _api._hash(SENHA), role, escola)
    return email


def _token(client, email, senha=SENHA):
    r = client.post("/auth/login", json={"email": email, "senha": senha})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _registrar(client, codigo, email=None, escola="", senha=SENHA):
    return client.post("/auth/register", json={
        "nome": "Novo Professor", "email": email or _email("novo"),
        "senha": senha, "escola": escola, "codigo_convite": codigo,
    })


@pytest.fixture
def admin(client):
    return _token(client, _criar_usuario("admin_geral"))


def _convite(client, headers, **kw):
    body = {"role": "professor", "escola": "Escola X", "usos_max": 1, "validade_dias": 7}
    body.update(kw)
    r = client.post("/admin/convites", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ── Autenticação básica ──────────────────────────────────────────────────────

class TestAutenticacao:
    def test_rota_protegida_sem_token_401(self, client):
        assert client.get("/turmas").status_code == 401

    def test_token_invalido_401(self, client):
        r = client.get("/turmas", headers={"Authorization": "Bearer lixo"})
        assert r.status_code == 401

    def test_login_senha_errada_401(self, client):
        email = _criar_usuario("professor")
        r = client.post("/auth/login", json={"email": email, "senha": "errada"})
        assert r.status_code == 401

    def test_login_email_case_insensitive(self, client):
        email = _criar_usuario("professor")
        _token(client, email.upper())


# ── Cadastro ─────────────────────────────────────────────────────────────────

class TestCadastro:
    def test_sem_codigo_403(self, client, admin):
        r = _registrar(client, "")
        assert r.status_code == 403
        assert "convite" in r.json()["detail"].lower()

    def test_codigo_inexistente_403(self, client, admin):
        assert _registrar(client, "EDU-ZZZZ-ZZZZ").status_code == 403

    def test_bootstrap_primeiro_usuario_vira_admin_sem_convite(self, client, monkeypatch):
        monkeypatch.setattr(db_usuarios, "contar_usuarios", lambda: 0)
        r = _registrar(client, "")
        assert r.status_code == 201
        assert r.json()["role"] == "admin_geral"

    def test_senha_curta_422(self, client, admin):
        c = _convite(client, admin)
        assert _registrar(client, c["codigo"], senha="123").status_code == 422

    def test_email_invalido_422(self, client, admin):
        c = _convite(client, admin)
        assert _registrar(client, c["codigo"], email="sem-arroba").status_code == 422

    def test_email_duplicado_ignora_maiusculas(self, client, admin):
        email = _criar_usuario("professor")
        c = _convite(client, admin)
        assert _registrar(client, c["codigo"], email=email.upper()).status_code == 400
        # O uso do convite não foi gasto pela tentativa recusada
        assert db_convites.get_convite(c["id"])["usos"] == 0


# ── Convites ─────────────────────────────────────────────────────────────────

class TestConvites:
    def test_fluxo_completo_convite_uso_unico(self, client, admin):
        c = _convite(client, admin, escola="Escola X")
        assert CODIGO_RE.match(c["codigo"])
        assert c["status"] == "ativo"

        v = client.get(f"/convites/{c['codigo'].lower()}").json()
        assert v == {"valido": True, "role": "professor", "escola": "Escola X"}

        # Código digitado em minúsculas; escola do formulário é ignorada
        r = _registrar(client, c["codigo"].lower(), escola="Outra Escola")
        assert r.status_code == 201
        assert r.json()["role"] == "professor"
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['token']}"}).json()
        assert me["escola"] == "Escola X"

        # Segundo uso recusado
        assert _registrar(client, c["codigo"]).status_code == 403
        assert client.get(f"/convites/{c['codigo']}").json() == {"valido": False}

    def test_convite_multiplos_usos(self, client, admin):
        c = _convite(client, admin, usos_max=2)
        assert _registrar(client, c["codigo"]).status_code == 201
        assert _registrar(client, c["codigo"]).status_code == 201
        assert _registrar(client, c["codigo"]).status_code == 403
        assert db_convites.get_convite(c["id"])["status"] == "esgotado"

    def test_convite_expirado(self, client, admin):
        c = _convite(client, admin)
        with _conn() as con:
            con.execute("UPDATE convites SET expira_em=? WHERE id=?", ("2000-01-01T00:00:00Z", c["id"]))
        assert _registrar(client, c["codigo"]).status_code == 403
        assert db_convites.get_convite(c["id"])["status"] == "expirado"

    def test_convite_desativado(self, client, admin):
        c = _convite(client, admin)
        r = client.delete(f"/admin/convites/{c['id']}", headers=admin)
        assert r.status_code == 200
        assert r.json()["status"] == "desativado"
        assert _registrar(client, c["codigo"]).status_code == 403

    def test_convite_admin_escolar_cria_admin_escolar(self, client, admin):
        c = _convite(client, admin, role="admin_escolar", escola="Escola Y")
        r = _registrar(client, c["codigo"])
        assert r.json()["role"] == "admin_escolar"

    @pytest.mark.parametrize("body", [
        {"role": "admin_geral"},
        {"usos_max": 0},
        {"usos_max": 501},
        {"validade_dias": 0},
        {"validade_dias": 91},
    ])
    def test_validacao_criacao_422(self, client, admin, body):
        r = client.post("/admin/convites", json=body, headers=admin)
        assert r.status_code == 422


# ── Permissões ───────────────────────────────────────────────────────────────

class TestPermissoesConvites:
    def test_professor_nao_gerencia_convites(self, client):
        prof = _token(client, _criar_usuario("professor", "Escola X"))
        assert client.post("/admin/convites", json={}, headers=prof).status_code == 403
        assert client.get("/admin/convites", headers=prof).status_code == 403

    def test_sem_token_401(self, client):
        assert client.post("/admin/convites", json={}).status_code == 401

    def test_admin_escolar_so_convida_professor_da_propria_escola(self, client):
        esc = _token(client, _criar_usuario("admin_escolar", "Escola Z"))
        r = client.post("/admin/convites", json={"role": "admin_escolar"}, headers=esc)
        assert r.status_code == 403
        c = _convite(client, esc, escola="Tentativa Outra Escola")
        assert c["escola"] == "Escola Z"

    def test_admin_escolar_lista_so_propria_escola(self, client, admin):
        _convite(client, admin, escola="Escola Alheia")
        esc = _token(client, _criar_usuario("admin_escolar", "Escola W"))
        _convite(client, esc)
        lista = client.get("/admin/convites", headers=esc).json()
        assert lista and all(c["escola"] == "Escola W" for c in lista)

    def test_admin_escolar_nao_desativa_convite_alheio(self, client, admin):
        alheio = _convite(client, admin, escola="Escola Alheia")
        esc = _token(client, _criar_usuario("admin_escolar", "Escola V"))
        assert client.delete(f"/admin/convites/{alheio['id']}", headers=esc).status_code == 404

    def test_admin_escolar_sem_escola_403(self, client):
        esc = _token(client, _criar_usuario("admin_escolar", ""))
        assert client.get("/admin/convites", headers=esc).status_code == 403

    def test_admin_geral_lista_todos(self, client, admin):
        c = _convite(client, admin, escola="Escola Q")
        ids = [x["id"] for x in client.get("/admin/convites", headers=admin).json()]
        assert c["id"] in ids
