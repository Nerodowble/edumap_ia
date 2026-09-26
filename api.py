"""
EduMap IA — FastAPI Backend
Inicie com: uvicorn api:app --reload
Documentação: http://localhost:8000/docs
"""
import os
import re
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional

from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from classifier.area_classifier import classify_area, get_area_display_name
from classifier.bloom_classifier import classify_bloom
from classifier.bncc_mapper import map_to_bncc
from classifier.segmenter import segment_questions
from classifier.subarea_classifier import classify_subarea
from classifier.taxonomia_classifier import classify as classify_taxonomia
from classifier.taxonomia_classifier import classify_across_all as classify_taxonomia_auto
from database import convites as db_convites
from database import db
from database import taxonomia as db_taxonomia
from database import usuarios as db_usuarios
from ocr.extractor import extract_text_from_file
from report.relatorio_pdf import gerar_pdf_relatorio

JSON_TAXONOMIA = Path(__file__).parent / "data" / "taxonomia.json"
JSON_TEMPLATE = Path(__file__).parent / "data" / "taxonomia_template.json"


def _auto_seed_taxonomias():
    """Auto-importa todos os arquivos data/taxonomia_*.json ou taxonomia.json
    no startup do servidor. So reimporta arquivos cujo conteudo mudou desde o
    ultimo seed (hash). Pula o template. Silencia erros para não impedir o boot."""
    data_dir = Path(__file__).parent / "data"
    if not data_dir.exists():
        return
    for jf in sorted(data_dir.glob("taxonomia*.json")):
        if jf.name == "taxonomia_template.json":
            continue
        try:
            stats = db_taxonomia.seed_from_json_if_changed(jf)
            if stats is None:
                print(f"[auto-seed] {jf.name}: sem alterações, pulado")
                continue
            print(
                f"[auto-seed] {jf.name}: etapa={stats['etapa']} "
                f"total={stats['total_depois']} adicionados={stats['adicionados']}"
            )
        except Exception as exc:
            print(f"[auto-seed] {jf.name}: FALHOU ({exc})")


def _startup_seed():
    try:
        _auto_seed_taxonomias()
        # Migração: remover matéria legada unificada se as 3 novas existem
        removed = db_taxonomia.cleanup_legacy_if_new_exists(
            "superior", "psicologia_saude_mental_sus",
            ["psicologia", "saude_mental", "sus"],
        )
        if removed:
            print(f"[migration] matéria legada 'psicologia_saude_mental_sus' removida: {removed} nós")
    except Exception as _exc:
        print(f"[auto-seed] erro geral: {_exc}")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="EduMap IA API",
    version="0.1.0",
    description="Backend da plataforma EduMap IA — diagnóstico taxonômico de aprendizagem.",
)


@app.on_event("startup")
def _iniciar_seed_em_background():
    # Roda fora do caminho de boot: o servidor abre a porta imediatamente
    # (importante no Render free, que reinicia a cada cold start).
    if os.getenv("SKIP_AUTO_SEED", "").lower() in ("1", "true", "yes"):
        return
    threading.Thread(target=_startup_seed, name="auto-seed", daemon=True).start()

_extra = os.getenv("ALLOWED_ORIGINS", "")
_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
] + [o.strip() for o in _extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth ──────────────────────────────────────────────────────────────────────
_SECRET = os.getenv("SECRET_KEY", "")
if not _SECRET:
    if os.getenv("DATABASE_URL"):
        # Produção (Postgres): sem chave própria, qualquer um forjaria tokens
        raise RuntimeError("SECRET_KEY não definida. Configure a variável de ambiente no servidor.")
    _SECRET = "edumap-dev-secret-change-in-prod"
    print("[auth] AVISO: SECRET_KEY ausente — usando chave de desenvolvimento (só para uso local).")
_ALGO = "HS256"
_TTL = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days
SKIP_AUTH = os.getenv("SKIP_AUTH", "").lower() in ("1", "true", "yes")

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)
_FAKE_USER = {"id": 0, "nome": "Dev Admin", "email": "dev@local", "role": "admin_geral", "escola": ""}


def _hash(pwd: str) -> str:
    return _pwd.hash(pwd)


def _verify(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def _create_token(uid: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=_TTL)
    return jwt.encode({"sub": str(uid), "exp": exp}, _SECRET, algorithm=_ALGO)


def _require_turma_access(turma_id: int, user: Dict):
    """404 se turma não existe, 403 se existe mas não é do user."""
    if not db.get_turma(turma_id):
        raise HTTPException(404, "Turma não encontrada.")
    if not db.user_pode_ver_turma(turma_id, user):
        raise HTTPException(403, "Você não tem permissão para acessar esta turma.")


def _require_prova_access(prova_id: int, user: Dict):
    """404 se prova não existe, 403 se existe mas não é do user."""
    if not db.get_prova(prova_id):
        raise HTTPException(404, "Prova não encontrada.")
    if not db.user_pode_ver_prova(prova_id, user):
        raise HTTPException(403, "Você não tem permissão para acessar esta prova.")


def _require_questao_da_prova(questao_id: int, prova_id: int):
    """404 se a questão não existe ou pertence a outra prova (evita IDOR)."""
    q = db.get_questao(questao_id)
    if not q or q["prova_id"] != prova_id:
        raise HTTPException(404, "Questão não encontrada.")


def _require_aluno_da_prova(aluno_id: int, prova_id: int, user: Dict):
    """O aluno precisa ser da turma da prova (ou, se a prova não tem turma,
    de uma turma que o usuário pode ver). Evita lançar/ler dados de alunos
    de outros professores."""
    aluno = db.get_aluno(aluno_id)
    prova = db.get_prova(prova_id)
    if not aluno or not prova:
        raise HTTPException(404, "Aluno não encontrado.")
    if prova.get("turma_id"):
        ok = aluno.get("turma_id") == prova["turma_id"]
    else:
        ok = bool(aluno.get("turma_id")) and db.user_pode_ver_turma(aluno["turma_id"], user)
    if not ok:
        raise HTTPException(403, f"O aluno {aluno_id} não pertence à turma desta prova.")


def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)):
    if SKIP_AUTH:
        return _FAKE_USER
    if not creds:
        raise HTTPException(status_code=401, detail="Token não fornecido.")
    try:
        payload = jwt.decode(creds.credentials, _SECRET, algorithms=[_ALGO])
        uid = payload.get("sub")
        if uid is None:
            raise HTTPException(status_code=401, detail="Token inválido.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    user = db_usuarios.get_usuario(int(uid))
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")
    return user


# ── Constants ─────────────────────────────────────────────────────────────────
BLOOM_COLORS: Dict[int, str] = {
    1: "#3B82F6", 2: "#10B981", 3: "#F59E0B",
    4: "#F97316", 5: "#EF4444", 6: "#8B5CF6", 0: "#9CA3AF",
}
SUBJECT_TO_KEY: Dict[str, str] = {
    # Educação básica
    "Matemática": "matematica",
    "Português": "portugues",
    "Ciências": "ciencias",
    "História": "historia",
    "Geografia": "geografia",
    "Biologia": "biologia",
    "Física": "fisica",
    "Química": "quimica",
    "Inglês": "ingles",
    "Artes": "artes",
    "Ed. Física": "ed_fisica",
    # Ensino superior
    "Psicologia": "psicologia",
    "Saúde Mental": "saude_mental",
    "SUS": "sus",
    # Téc. Desenvolvimento de Sistemas (DSE)
    "Análise e Projeto de Sistemas": "analise_projeto_sistemas",
    "Design Digital": "design_digital",
    "Fundamentos da Informática": "fundamentos_informatica",
    "Linguagem, Trabalho e Tecnologia (DSE)": "linguagem_trabalho_tecnologia",
    "Técnicas de Programação e Algoritmos": "tecnicas_programacao_algoritmos",
    "Banco de Dados I": "banco_dados_1",
    "Desenvolvimento de Sistemas": "desenvolvimento_sistemas",
    "Estrutura de Dados": "estrutura_dados",
    "Ética e Cidadania Organizacional (DSE)": "etica_cidadania",
    "Programação de Computadores I": "programacao_computadores_1",
    "Sistemas Embarcados": "sistemas_embarcados",
    "Banco de Dados II": "banco_dados_2",
    "Desenvolvimento para Dispositivos Móveis": "dispositivos_moveis",
    "Internet, Protocolos e Segurança de Sistemas": "internet_protocolos_seguranca",
    "Qualidade e Teste de Software": "qualidade_teste_software",
    "Programação de Computadores II": "programacao_computadores_2",
    "TCC em Desenvolvimento de Sistemas": "tcc",
    # Téc. Administração
    "Administração de Marketing": "administracao_marketing",
    "Aplicativos Informáticos": "aplicativos_informaticos",
    "Gestão Empreendedora e Inovação": "gestao_empreendedora",
    "Introdução à Administração e aos Negócios": "introducao_administracao",
    "Linguagem, Trabalho e Tecnologia (Admin)": "linguagem_trabalho_tecnologia",
    "Técnicas Organizacionais": "tecnicas_organizacionais",
    "Administração da Produção e Serviços": "administracao_producao",
    "Administração Financeira e Orçamentária": "administracao_financeira",
    "Cálculo Financeiro e Estatístico": "calculo_financeiro_estatistico",
    "Ética e Cidadania Organizacional (Admin)": "etica_cidadania",
    "Gestão de Pessoas I": "gestao_pessoas_1",
    "Legislação Empresarial": "legislacao_empresarial",
    "Administração de Recursos Humanos (Gestão de Pessoas II)": "administracao_rh",
    "Gestão de Custos e Preços": "gestao_custos_precos",
    "Logística Empresarial e Negociações Internacionais": "logistica_negociacoes",
    "Planejamento Empresarial e Estratégico": "planejamento_estrategico",
    "TCC em Administração": "tcc",
    # Téc. Logística
    "Administração da Produção e Operações": "administracao_producao_operacoes",
    "Aplicativos Informáticos Aplicados à Logística": "aplicativos_informaticos",
    "Fundamentos de Logística": "fundamentos_logistica",
    "Linguagem, Trabalho e Tecnologia (Log)": "linguagem_trabalho_tecnologia",
    "Movimentação, Expedição e Distribuição": "movimentacao_expedicao_distribuicao",
    "Custos Logísticos": "custos_logisticos",
    "Ética e Cidadania Organizacional (Log)": "etica_cidadania",
    "Gestão do Transporte de Cargas": "gestao_transporte_cargas",
    "Planejamento, Programação e Controle da Produção (PPCP)": "ppcp",
    "Suprimentos e Gestão de Estoques": "suprimentos_estoques",
    "Logística Internacional e Economia": "logistica_internacional",
    "Comércio Exterior": "comercio_exterior",
    "Logística Reversa e Sustentabilidade": "logistica_reversa_sustentabilidade",
    "Planejamento Estratégico e Logístico": "planejamento_estrategico",
    "Sistemas de Informação Logística": "sistemas_informacao_logistica",
    "TCC em Logística": "tcc_logistica",
    # Téc. Informática para Internet (IW)
    "Criação de Sites (HTML/CSS)": "criacao_sites",
    "Design Digital Aplicado à Web": "design_digital",
    "Fundamentos de Informática e Redes": "fundamentos_inf_redes",
    "Linguagem, Trabalho e Tecnologia (IW)": "linguagem_trabalho_tecnologia",
    "Lógica de Programação": "logica_programacao",
    "Banco de Dados Orientado a Ambientes Web": "banco_dados_web",
    "Desenvolvimento de Softwares para Web I": "desenvolvimento_web_i",
    "Ética e Cidadania Organizacional (IW)": "etica_cidadania",
    "Interface Humano-Computador (IHC)": "ihc",
    "Programação Script para Web": "programacao_script_web",
    "Desenvolvimento de Softwares para Web II": "desenvolvimento_web_ii",
    "Marketing Digital e E-commerce": "marketing_digital_ecommerce",
    "Segurança de Aplicações Web": "seguranca_aplicacoes_web",
    "Sistemas de Gerenciamento de Conteúdo (CMS)": "cms",
    "TCC em Informática para Internet": "tcc",
    # Téc. Finanças
    "Contabilidade Geral": "contabilidade_geral",
    "Fundamentos de Economia e Mercados": "fundamentos_economia",
    "Informática Aplicada às Finanças": "informatica_aplicada",
    "Introdução às Atividades Financeiras": "intro_atividades_financeiras",
    "Linguagem, Trabalho e Tecnologia (Fin)": "linguagem_trabalho_tecnologia",
    "Matemática Financeira": "matematica_financeira",
    "Análise de Demonstrações Financeiras": "analise_demonstracoes",
    "Análise de Investimentos e Riscos": "analise_investimentos_riscos",
    "Ética e Cidadania Organizacional (Fin)": "etica_cidadania",
    "Gestão de Custos e Formação de Preços": "gestao_custos_precos",
    "Planejamento Financeiro e Orçamentário": "planejamento_orcamentario",
    "Auditoria e Controladoria": "auditoria_controladoria",
    "Finanças Corporativas e Internacionais": "financas_corporativas_internacionais",
    "Legislação Tributária e Fiscal": "legislacao_tributaria",
    "Mercado de Capitais e Operações Financeiras": "mercado_capitais",
    "TCC em Finanças": "tcc_financas",
}

# ── Schemas ───────────────────────────────────────────────────────────────────
class TurmaCreate(BaseModel):
    nome: str
    escola: str = ""
    disciplina: str = ""
    etapa: str = ""  # slug da etapa (ex: curso_logistica, ef2, superior)


class AlunoCreate(BaseModel):
    nome: str
    ra: str = ""
    cpf: str = ""
    data_nascimento: str = ""


class AlunoUpdate(BaseModel):
    nome: str
    # None = manter o valor atual (antes o front enviava só nome/ra e apagava CPF e nascimento)
    ra: Optional[str] = None
    cpf: Optional[str] = None
    data_nascimento: Optional[str] = None


class TurmaUpdate(BaseModel):
    nome: str
    escola: str = ""
    disciplina: str = ""
    etapa: Optional[str] = None  # None = nao alterar; "" = limpar; outra string = atualizar


class RespostaItem(BaseModel):
    resposta: str = ""
    gabarito: str = ""
    correta: bool = False


class RespostasPayload(BaseModel):
    aluno_id: int
    respostas: Dict[str, RespostaItem]


class GabaritoPayload(BaseModel):
    gabarito: Dict[str, str]


class LancarBulkPayload(BaseModel):
    respostas: Dict[str, Dict[str, str]]


class RegisterBody(BaseModel):
    nome: str
    email: str
    senha: str
    escola: str = ""
    codigo_convite: str = ""


class ConviteBody(BaseModel):
    role: str = "professor"
    escola: str = ""
    usos_max: int = 1
    validade_dias: int = 7


class LoginBody(BaseModel):
    email: str
    senha: str


class ClassificarBody(BaseModel):
    stem: str
    materia: str
    etapa: str = "ef2"


class AtualizarNoBody(BaseModel):
    label: Optional[str] = None
    palavras_chave: Optional[list] = None


class CriarNoBody(BaseModel):
    parent_id: int
    codigo_slug: str
    label: str
    palavras_chave: list = []


class TipoQuestaoBody(BaseModel):
    tipo: str  # "multipla_escolha" | "verdadeiro_falso"


# ── Auth endpoints ────────────────────────────────────────────────────────────
@app.post("/auth/register", status_code=201, summary="Registra novo usuário")
def auth_register(body: RegisterBody):
    nome = body.nome.strip()
    email = body.email.strip().lower()
    if not nome:
        raise HTTPException(422, "Informe o nome.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(422, "Email inválido.")
    if len(body.senha) < 6:
        raise HTTPException(422, "A senha deve ter pelo menos 6 caracteres.")
    if db_usuarios.get_usuario_por_email(email):
        raise HTTPException(400, "Email já cadastrado.")

    # Bootstrap: banco sem usuários — o primeiro vira admin_geral sem convite
    if db_usuarios.contar_usuarios() == 0:
        uid = db_usuarios.criar_usuario(nome, email, _hash(body.senha), "admin_geral", body.escola.strip())
        return {"token": _create_token(uid), "role": "admin_geral", "nome": nome}

    if not body.codigo_convite.strip():
        raise HTTPException(403, "O cadastro exige um código de convite.")
    novo = db_convites.registrar_com_convite(
        body.codigo_convite, nome, email, _hash(body.senha), body.escola.strip()
    )
    if not novo:
        raise HTTPException(403, "Código de convite inválido, expirado ou já utilizado.")
    return {"token": _create_token(novo["id"]), "role": novo["role"], "nome": nome}


@app.get("/convites/{codigo}", summary="Valida um código de convite (público)")
def validar_convite(codigo: str):
    conv = db_convites.get_convite_por_codigo(codigo)
    if not conv or conv["status"] != "ativo":
        return {"valido": False}
    return {"valido": True, "role": conv["role"], "escola": conv["escola"] or ""}


@app.post("/auth/login", summary="Autentica usuário e retorna JWT")
def auth_login(body: LoginBody):
    user = db_usuarios.get_usuario_por_email(body.email.strip().lower())
    if not user or not _verify(body.senha, user["senha_hash"]):
        raise HTTPException(401, "Email ou senha incorretos.")
    return {"token": _create_token(user["id"]), "role": user["role"], "nome": user["nome"]}


@app.get("/auth/me", summary="Retorna dados do usuário autenticado")
def auth_me(user=Depends(get_current_user)):
    return {
        "id": user["id"],
        "nome": user["nome"],
        "email": user.get("email", ""),
        "role": user["role"],
        "escola": user.get("escola", ""),
    }


# ── Admin: Taxonomia ──────────────────────────────────────────────────────────
def _require_admin_geral(user):
    if user["role"] != "admin_geral":
        raise HTTPException(403, "Apenas admin_geral pode executar esta ação.")


@app.post("/admin/seed-taxonomia", summary="Popular tabela de taxonomia a partir do JSON (admin_geral)")
def admin_seed_taxonomia(user=Depends(get_current_user)):
    _require_admin_geral(user)
    try:
        stats = db_taxonomia.seed_from_json(JSON_TAXONOMIA)
        return {"ok": True, **stats}
    except FileNotFoundError as exc:
        raise HTTPException(500, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"Erro no seed: {exc}")


@app.get("/admin/taxonomia/etapas", summary="Lista etapas distintas com contagem")
def admin_taxonomia_etapas(user=Depends(get_current_user)):
    return db_taxonomia.listar_etapas()


@app.get("/etapas", summary="Lista etapas disponiveis (para professor escolher ao criar turma)")
def listar_etapas_publicas(user=Depends(get_current_user)):
    """Mesma lista do /admin/taxonomia/etapas, mas acessivel a qualquer
    usuario autenticado. Util para o select de etapa ao criar/editar turma."""
    return db_taxonomia.listar_etapas()


@app.get("/admin/taxonomia/template", summary="Baixa template JSON de exemplo")
def admin_taxonomia_template(user=Depends(get_current_user)):
    _require_admin_geral(user)
    if not JSON_TEMPLATE.exists():
        raise HTTPException(404, "Template não encontrado no servidor.")
    with open(JSON_TEMPLATE, "r", encoding="utf-8") as f:
        content = f.read()
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="taxonomia_template.json"'
        },
    )


@app.get("/admin/taxonomia/export", summary="Exporta taxonomia de uma etapa como JSON (admin_geral)")
def admin_taxonomia_export(etapa: str = "ef2", user=Depends(get_current_user)):
    _require_admin_geral(user)
    import json as _json
    data = db_taxonomia.exportar_json(etapa)
    content = _json.dumps(data, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="taxonomia_{etapa}_export.json"'
        },
    )


@app.get("/admin/taxonomia/stats", summary="Estatísticas da taxonomia carregada")
def admin_taxonomia_stats(etapa: str = "ef2", user=Depends(get_current_user)):
    return db_taxonomia.stats(etapa)


@app.get("/admin/taxonomia/materias", summary="Lista matérias da taxonomia")
def admin_taxonomia_materias(etapa: str = "ef2", user=Depends(get_current_user)):
    return db_taxonomia.listar_materias(etapa)


@app.get("/admin/taxonomia/nos", summary="Lista nós da taxonomia (filtro opcional por matéria)")
def admin_taxonomia_nos(
    materia: Optional[str] = None,
    etapa: str = "ef2",
    user=Depends(get_current_user),
):
    return db_taxonomia.listar_nos(materia, etapa)


@app.post("/admin/taxonomia/classificar", summary="Testa o classificador em um texto (sem salvar)")
def admin_taxonomia_classificar(body: ClassificarBody, user=Depends(get_current_user)):
    """
    Útil para depurar o classificador. Passe um enunciado e a matéria,
    veja qual nó da árvore ele bate.
    """
    tax = classify_taxonomia(body.stem, body.materia, body.etapa)
    if not tax:
        return {"encontrado": False, "stem": body.stem, "materia": body.materia}
    return {"encontrado": True, **tax}


@app.post("/admin/taxonomia/import-json", summary="Importa taxonomia de um JSON no body (admin_geral)")
def admin_taxonomia_import(body: Dict = Body(...), user=Depends(get_current_user)):
    _require_admin_geral(user)
    try:
        stats = db_taxonomia.seed_from_data(body)
        return {"ok": True, **stats}
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, f"JSON inválido: {exc}")
    except Exception as exc:
        raise HTTPException(500, f"Erro ao importar: {exc}")


@app.put("/admin/taxonomia/no/{no_id}", summary="Atualiza label e palavras-chave de um nó (admin_geral)")
def admin_atualizar_no(no_id: int, body: AtualizarNoBody, user=Depends(get_current_user)):
    _require_admin_geral(user)
    ok = db_taxonomia.atualizar_no(no_id, body.label, body.palavras_chave)
    if not ok:
        raise HTTPException(404, "Nó não encontrado.")
    return {"ok": True, **(db_taxonomia.get_no(no_id) or {})}


@app.post("/admin/taxonomia/no", status_code=201, summary="Cria novo nó filho (admin_geral)")
def admin_criar_no(body: CriarNoBody, user=Depends(get_current_user)):
    _require_admin_geral(user)
    try:
        result = db_taxonomia.criar_no(
            body.parent_id, body.codigo_slug, body.label, body.palavras_chave or []
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if result is None:
        raise HTTPException(404, "Nó pai não encontrado.")
    return result


@app.delete("/admin/taxonomia/no/{no_id}", status_code=204, summary="Deleta nó e descendentes (admin_geral)")
def admin_deletar_no(no_id: int, user=Depends(get_current_user)):
    _require_admin_geral(user)
    if not db_taxonomia.deletar_no(no_id):
        raise HTTPException(404, "Nó não encontrado.")


# ── Admin: Usuários e Escolas ─────────────────────────────────────────────────
@app.get("/admin/usuarios", summary="Lista todos os usuários (admin_geral)")
def admin_list_usuarios(user=Depends(get_current_user)):
    _require_admin_geral(user)
    return db_usuarios.listar_usuarios()


# ── Admin: Convites de cadastro ───────────────────────────────────────────────
def _require_pode_convidar(user):
    if user["role"] not in ("admin_geral", "admin_escolar"):
        raise HTTPException(403, "Apenas administradores podem gerenciar convites.")
    if user["role"] == "admin_escolar" and not (user.get("escola") or "").strip():
        raise HTTPException(403, "Seu usuário não está vinculado a uma escola.")


@app.post("/admin/convites", status_code=201, summary="Gera um código de convite de cadastro")
def admin_criar_convite(body: ConviteBody, user=Depends(get_current_user)):
    _require_pode_convidar(user)
    if body.role not in db_convites.ROLES_CONVIDAVEIS:
        raise HTTPException(422, "Role inválido. Use professor ou admin_escolar.")
    if not 1 <= body.usos_max <= 500:
        raise HTTPException(422, "usos_max deve estar entre 1 e 500.")
    if not 1 <= body.validade_dias <= 90:
        raise HTTPException(422, "validade_dias deve estar entre 1 e 90.")
    escola = body.escola.strip()
    if user["role"] == "admin_escolar":
        if body.role != "professor":
            raise HTTPException(403, "admin_escolar só pode convidar professores.")
        escola = user["escola"]
    return db_convites.criar_convite(body.role, escola, body.usos_max, body.validade_dias, user["id"])


@app.get("/admin/convites", summary="Lista convites (admin_escolar vê só os da própria escola)")
def admin_listar_convites(user=Depends(get_current_user)):
    _require_pode_convidar(user)
    escola = user["escola"] if user["role"] == "admin_escolar" else None
    return db_convites.listar_convites(escola)


@app.delete("/admin/convites/{convite_id}", summary="Desativa um convite")
def admin_desativar_convite(convite_id: int, user=Depends(get_current_user)):
    _require_pode_convidar(user)
    conv = db_convites.get_convite(convite_id)
    if not conv or (user["role"] == "admin_escolar" and conv["escola"] != user["escola"]):
        raise HTTPException(404, "Convite não encontrado.")
    db_convites.desativar_convite(convite_id)
    return db_convites.get_convite(convite_id)


# Health/version endpoint para conferir qual commit esta deployado.
# Sem autenticacao para facilitar debug em producao.
@app.get("/admin/version", summary="Versão atual da API e endpoints admin disponíveis")
def admin_version():
    routes_admin = sorted(
        f"{list(r.methods - {'HEAD', 'OPTIONS'})[0]} {r.path}"
        for r in app.routes
        if hasattr(r, "methods") and hasattr(r, "path") and "/admin/" in r.path
    )
    return {"version": "0.1.0", "admin_routes_count": len(routes_admin), "admin_routes": routes_admin}


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    role: Optional[str] = None
    escola: Optional[str] = None


@app.put("/admin/usuarios/{usuario_id}", summary="Atualiza usuário (admin_geral)")
def admin_update_usuario(usuario_id: int, body: UsuarioUpdate, user=Depends(get_current_user)):
    _require_admin_geral(user)
    if body.role and body.role not in ("admin_geral", "admin_escolar", "professor"):
        raise HTTPException(400, "Role inválido. Use admin_geral, admin_escolar ou professor.")
    if not db_usuarios.atualizar_usuario(
        usuario_id, nome=body.nome, role=body.role, escola=body.escola,
    ):
        raise HTTPException(404, "Usuário não encontrado ou nenhum campo válido foi enviado.")
    return db_usuarios.get_usuario(usuario_id)


@app.delete("/admin/usuarios/{usuario_id}", status_code=204, summary="Deleta usuário (admin_geral)")
def admin_delete_usuario(usuario_id: int, user=Depends(get_current_user)):
    _require_admin_geral(user)
    # Impede auto-deleção
    if user.get("id") == usuario_id:
        raise HTTPException(400, "Você não pode deletar sua própria conta.")
    if not db_usuarios.deletar_usuario(usuario_id):
        raise HTTPException(404, "Usuário não encontrado.")


@app.get("/admin/escolas", summary="Lista escolas agregadas (admin_geral)")
def admin_list_escolas(user=Depends(get_current_user)):
    _require_admin_geral(user)
    return db_usuarios.listar_escolas()


class EscolaRenameIn(BaseModel):
    nome_novo: str


@app.put("/admin/escolas/{nome_antigo}", summary="Renomeia uma escola (admin_geral)")
def admin_rename_escola(nome_antigo: str, body: EscolaRenameIn, user=Depends(get_current_user)):
    _require_admin_geral(user)
    try:
        res = db_usuarios.renomear_escola(nome_antigo, body.nome_novo)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, **res}


@app.delete("/admin/escolas/{nome}", summary="Apaga escola - deleta usuarios e turmas dessa escola (admin_geral)")
def admin_delete_escola(nome: str, user=Depends(get_current_user)):
    _require_admin_geral(user)
    if (user.get("escola") or "") == nome:
        raise HTTPException(400, "Você não pode deletar a escola onde sua conta está vinculada.")
    try:
        res = db_usuarios.deletar_escola(nome)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, **res}


# ── Admin: Provas ─────────────────────────────────────────────────────────────
@app.get("/admin/provas", summary="Lista todas as provas (admin_geral)")
def admin_list_provas(user=Depends(get_current_user)):
    _require_admin_geral(user)
    return db.listar_todas_provas()


@app.delete("/admin/provas/{prova_id}", status_code=204, summary="Deleta prova e dados relacionados (admin_geral)")
def admin_delete_prova(prova_id: int, user=Depends(get_current_user)):
    _require_admin_geral(user)
    if not db.delete_prova(prova_id):
        raise HTTPException(404, "Prova não encontrada.")


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "app": "EduMap IA API", "docs": "/docs"}


# ── Turmas ────────────────────────────────────────────────────────────────────
@app.get("/turmas", summary="Lista turmas visíveis ao usuário")
def list_turmas(user=Depends(get_current_user)):
    return db.listar_turmas(
        usuario_id=user["id"],
        role=user["role"],
        escola=user.get("escola"),
    )


@app.post("/turmas", status_code=201, summary="Cria uma nova turma")
def create_turma(body: TurmaCreate, user=Depends(get_current_user)):
    uid = user["id"] if user["id"] != 0 else None
    tid = db.criar_turma(body.nome, body.escola, body.disciplina, body.etapa, uid)
    turma = db.get_turma(tid)
    return turma


@app.put("/turmas/{turma_id}", summary="Atualiza nome/escola/disciplina/etapa de uma turma")
def update_turma(turma_id: int, body: TurmaUpdate, user=Depends(get_current_user)):
    _require_turma_access(turma_id, user)
    if not db.atualizar_turma(turma_id, body.nome, body.escola, body.disciplina, body.etapa):
        raise HTTPException(400, "Não foi possível atualizar a turma. Verifique se o nome é válido.")
    return db.get_turma(turma_id)


@app.delete("/turmas/{turma_id}", status_code=204, summary="Remove uma turma")
def delete_turma(turma_id: int, user=Depends(get_current_user)):
    _require_turma_access(turma_id, user)
    db.delete_turma(turma_id)


@app.get("/turmas/{turma_id}/contexto", summary="Retorna a etapa da turma com materias e series disponiveis")
def turma_contexto(turma_id: int, user=Depends(get_current_user)):
    """Para ancorar a UI de criar prova: dado o turma_id, devolve a etapa
    e as opcoes de disciplina/serie filtradas pra ela."""
    _require_turma_access(turma_id, user)
    turma = db.get_turma(turma_id)
    if not turma:
        raise HTTPException(404, "Turma nao encontrada.")
    etapa = turma.get("etapa") or ""
    if not etapa:
        return {
            "etapa": "",
            "etapa_label": "",
            "etapa_grupo": "",
            "materias": [],
            "tem_filtro": False,
        }
    # Procura nos metadados da etapa
    etapa_label = etapa
    etapa_grupo = ""
    for e in db_taxonomia.listar_etapas():
        if e["etapa"] == etapa:
            etapa_label = e.get("etapa_label") or etapa
            etapa_grupo = e.get("etapa_grupo") or ""
            break
    return {
        "etapa": etapa,
        "etapa_label": etapa_label,
        "etapa_grupo": etapa_grupo,
        "materias": db_taxonomia.listar_materias(etapa),
        "tem_filtro": True,
    }


# ── Alunos ────────────────────────────────────────────────────────────────────
@app.get("/turmas/{turma_id}/alunos", summary="Lista alunos de uma turma")
def list_alunos(turma_id: int, user=Depends(get_current_user)):
    _require_turma_access(turma_id, user)
    return db.listar_alunos(turma_id)


@app.post("/turmas/{turma_id}/alunos", status_code=201, summary="Adiciona aluno à turma")
def create_aluno(turma_id: int, body: AlunoCreate, user=Depends(get_current_user)):
    _require_turma_access(turma_id, user)
    aid = db.criar_aluno(body.nome, turma_id, body.ra, body.cpf, body.data_nascimento)
    return {
        "id": aid, "nome": body.nome, "turma_id": turma_id,
        "ra": body.ra, "cpf": body.cpf, "data_nascimento": body.data_nascimento,
    }


@app.put("/alunos/{aluno_id}", summary="Atualiza dados de um aluno")
def update_aluno(aluno_id: int, body: AlunoUpdate, user=Depends(get_current_user)):
    aluno = db.get_aluno(aluno_id)
    if not aluno:
        raise HTTPException(404, "Aluno não encontrado.")
    _require_turma_access(aluno["turma_id"], user)
    if not db.atualizar_aluno_completo(aluno_id, body.nome, body.ra, body.cpf, body.data_nascimento):
        raise HTTPException(400, "Nome inválido.")
    return db.get_aluno(aluno_id)


@app.delete("/alunos/{aluno_id}", status_code=204, summary="Remove um aluno")
def delete_aluno(aluno_id: int, user=Depends(get_current_user)):
    aluno = db.get_aluno(aluno_id)
    if not aluno:
        raise HTTPException(404, "Aluno não encontrado.")
    _require_turma_access(aluno["turma_id"], user)
    db.deletar_aluno(aluno_id)


# ── Provas ────────────────────────────────────────────────────────────────────
@app.get("/provas/online", summary="Lista as provas online (criadas no editor) do usuário")
def list_provas_online(user=Depends(get_current_user)):
    return db.listar_provas_online(user)


@app.get("/turmas/{turma_id}/provas", summary="Lista provas de uma turma")
def list_provas(turma_id: int, user=Depends(get_current_user)):
    _require_turma_access(turma_id, user)
    return db.listar_provas(turma_id)


_EXTENSOES_UPLOAD = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
_MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "15")) * 1024 * 1024


async def _ler_upload(file: UploadFile, padrao: str) -> tuple:
    """Valida extensão e tamanho (lendo em blocos). Retorna (sufixo, bytes)."""
    suffix = (Path(file.filename or padrao).suffix or Path(padrao).suffix).lower()
    if suffix not in _EXTENSOES_UPLOAD:
        raise HTTPException(415, "Formato não suportado. Envie PDF ou imagem (JPG, PNG, WEBP, TIFF, BMP).")
    partes, total = [], 0
    while True:
        bloco = await file.read(1024 * 1024)
        if not bloco:
            break
        total += len(bloco)
        if total > _MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"Arquivo muito grande. O limite é {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
        partes.append(bloco)
    if total == 0:
        raise HTTPException(422, "O arquivo enviado está vazio.")
    return suffix, b"".join(partes)


@app.post("/provas/upload", summary="Faz upload de prova, executa OCR e classifica questões")
async def upload_prova(
    file: UploadFile = File(...),
    year_level: str = Form(...),
    subject: str = Form("Detectar automaticamente"),
    turma_id: Optional[str] = Form(None),
    user=Depends(get_current_user),
):
    # Valida entrada e acesso ANTES do OCR (caro) e fora do try (senão vira 500)
    if turma_id and turma_id not in ("", "none"):
        if not turma_id.isdigit():
            raise HTTPException(422, "turma_id inválido.")
        tid: Optional[int] = int(turma_id)
        _require_turma_access(tid, user)
    else:
        tid = None
    suffix, content = await _ler_upload(file, "prova.pdf")
    etapa_turma = (db.get_turma(tid) or {}).get("etapa") if tid else None

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        noop = lambda pct, msg: None
        text, method = extract_text_from_file(tmp_path, noop)
        questions = segment_questions(text)

        auto_detect = not subject or subject == "Detectar automaticamente"

        for q in questions:
            stem = q.get("stem") or q.get("text", "")
            # Inclui alternativas para dar mais sinal ao classificador
            alts_list = q.get("alternatives", []) or []
            stem_full = (stem + " " + " ".join(alts_list)).strip()

            tax = None
            if not auto_detect:
                area_key, etapa_materia = _materia_da_disciplina(subject, etapa_turma)
                area_key = area_key or "indefinida"
                area_conf = 1.0
                if area_key != "indefinida":
                    try:
                        tax = classify_taxonomia(stem_full, area_key, etapa_materia or "ef2")
                    except Exception:
                        tax = None
            else:
                # Auto-detect: usa a taxonomia com pontuação por matéria
                try:
                    tax = classify_taxonomia_auto(stem_full)
                except Exception:
                    tax = None

                if tax and tax.get("materia_total_matches", tax.get("matches", 0)) >= 2:
                    area_key = tax["materia"]
                    area_conf = min(1.0, tax.get("materia_total_matches", tax["matches"]) / 6)
                else:
                    # Fallback: classificador legacy de palavras-chave
                    area_key, area_conf, _ = classify_area(stem_full)
                    if area_key and area_key != "indefinida":
                        try:
                            tax = classify_taxonomia(stem_full, area_key)
                        except Exception:
                            tax = None

            bloom_level, bloom_name, bloom_verb = classify_bloom(stem)
            subarea_key, subarea_label = classify_subarea(stem, area_key)
            bncc = map_to_bncc(area_key, year_level, bloom_level)

            q.update({
                "area_key":          area_key,
                "area_display":      get_area_display_name(area_key),
                "area_confidence":   area_conf,
                "subarea_key":       subarea_key,
                "subarea_label":     subarea_label,
                "bloom_level":       bloom_level,
                "bloom_name":        bloom_name,
                "bloom_verb":        bloom_verb,
                "bloom_color":       BLOOM_COLORS.get(bloom_level, "#9CA3AF"),
                "bncc_skills":       bncc,
                "taxonomia_codigo":  tax["codigo"]  if tax else "",
                "taxonomia_label":   tax["label"]   if tax else "",
                "taxonomia_caminho": tax["caminho"] if tax else [],
                "taxonomia_matches": tax["matches"] if tax else 0,
            })

        disc_key = SUBJECT_TO_KEY.get(subject, "")

        owner_id = user["id"] if user.get("id", 0) != 0 else None
        prova_id = db.salvar_prova(
            titulo=file.filename or "prova",
            serie=year_level,
            disciplina=disc_key,
            arquivo_nome=file.filename or "prova",
            ocr_method=method,
            questoes=questions,
            turma_id=tid,
            usuario_id=owner_id,
        )

        return {
            "prova_id":   prova_id,
            "questions":  questions,
            "ocr_method": method,
            "file_name":  file.filename,
            "year_level": year_level,
            "subject":    subject,
            "metadata": {
                "Arquivo":     file.filename,
                "Série / Ano": year_level,
                "Extração":    "OCR (imagem)" if method == "ocr" else "Texto digital",
                "Questões":    str(len(questions)),
            },
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Erro ao processar prova: {exc}") from exc
    finally:
        os.unlink(tmp_path)


# ── Questoes + Relatórios ─────────────────────────────────────────────────────
@app.get("/provas/{prova_id}/questoes", summary="Lista questões de uma prova")
def get_questoes(prova_id: int, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    return db.get_questoes_prova(prova_id)


@app.put("/provas/{prova_id}/questoes/{questao_id}/tipo",
         summary="Atualiza tipo da questão (multipla_escolha | verdadeiro_falso)")
def update_tipo_questao(
    prova_id: int,
    questao_id: int,
    body: TipoQuestaoBody,
    user=Depends(get_current_user),
):
    _require_prova_access(prova_id, user)
    _require_questao_da_prova(questao_id, prova_id)
    if body.tipo not in ("multipla_escolha", "verdadeiro_falso"):
        raise HTTPException(400, "tipo inválido. Use 'multipla_escolha' ou 'verdadeiro_falso'.")
    if not db.atualizar_tipo_questao(questao_id, body.tipo):
        raise HTTPException(404, "Questão não encontrada.")
    return {"ok": True, "tipo": body.tipo}


@app.get("/provas/{prova_id}/relatorio/turma", summary="Relatório de desempenho por aluno")
def get_relatorio_turma(prova_id: int, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    return db.relatorio_turma(prova_id)


@app.get("/provas/{prova_id}/relatorio/drilldown", summary="Relatório drill-down área→subárea→bloom→aluno")
def get_relatorio_drilldown(prova_id: int, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    return db.relatorio_drilldown(prova_id)


@app.get("/provas/{prova_id}/relatorio/taxonomia", summary="Árvore taxonômica com stats por nó")
def get_relatorio_taxonomia(prova_id: int, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    return db.relatorio_taxonomia(prova_id)


@app.get("/provas/{prova_id}/relatorio/pontos-criticos", summary="Pontos críticos por aluno (taxonomia)")
def get_pontos_criticos(prova_id: int, top_n: int = 3, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    return db.alunos_pontos_criticos(prova_id, top_n)


@app.get("/provas/{prova_id}/relatorio/pdf", summary="Gera relatório pedagógico em PDF")
def get_relatorio_pdf(prova_id: int, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    prova = db.get_prova(prova_id)
    turma = db.get_turma(prova["turma_id"]) if prova.get("turma_id") else None
    alunos = db.relatorio_turma(prova_id)
    taxonomia = db.relatorio_taxonomia(prova_id)
    pontos = db.alunos_pontos_criticos(prova_id, top_n=5)
    try:
        pdf_bytes = gerar_pdf_relatorio(prova, turma, alunos, taxonomia, pontos)
    except Exception as exc:
        raise HTTPException(500, f"Erro ao gerar PDF: {exc}")
    nome_arquivo = f"relatorio_prova_{prova_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@app.post("/provas/{prova_id}/respostas", status_code=201, summary="Salva respostas de um aluno")
def save_respostas(prova_id: int, payload: RespostasPayload, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    _require_aluno_da_prova(payload.aluno_id, prova_id, user)
    # `correta` enviado pelo cliente é ignorado: o servidor recalcula (ver db.salvar_respostas)
    respostas = {
        int(k): {"resposta": v.resposta, "gabarito": v.gabarito}
        for k, v in payload.respostas.items()
    }
    db.salvar_respostas(payload.aluno_id, prova_id, respostas)
    return {"ok": True}


# ── Gabarito ──────────────────────────────────────────────────────────────────
@app.post("/provas/{prova_id}/gabarito", status_code=201, summary="Salva gabarito da prova")
def save_gabarito(prova_id: int, payload: GabaritoPayload, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    gabarito = {int(k): v for k, v in payload.gabarito.items()}
    db.salvar_gabarito(prova_id, gabarito)
    return {"ok": True}


@app.get("/provas/{prova_id}/gabarito", summary="Retorna gabarito da prova")
def get_gabarito(prova_id: int, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    return db.get_gabarito(prova_id)


@app.post("/provas/{prova_id}/lancar", status_code=201, summary="Lança respostas de vários alunos")
def lancar_respostas(prova_id: int, payload: LancarBulkPayload, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    # Valida todos os alunos antes de gravar qualquer coisa
    for aluno_id_str in payload.respostas:
        if not aluno_id_str.isdigit():
            raise HTTPException(422, f"aluno_id inválido: {aluno_id_str}")
        _require_aluno_da_prova(int(aluno_id_str), prova_id, user)
    erros = []
    for aluno_id_str, resps in payload.respostas.items():
        try:
            respostas_int = {int(k): v for k, v in resps.items() if k.isdigit()}
            db.lancar_respostas_aluno(int(aluno_id_str), prova_id, respostas_int)
        except Exception as exc:
            erros.append({"aluno_id": aluno_id_str, "erro": str(exc)})
    return {"ok": True, "erros": erros}


# ── OCR de gabarito de aluno ──────────────────────────────────────────────────
def _parse_respostas_ocr(text: str) -> Dict[int, str]:
    """Extrai pares (número da questão, alternativa) do texto OCR.
    Aceita A-E (múltipla escolha) e V/F (verdadeiro/falso)."""
    respostas: Dict[int, str] = {}
    # Inclui V e F nos padrões — letras válidas A-F (com V/F como casos especiais)
    patterns = [
        r'\b(\d{1,2})\s*[.)\-:]\s*([A-FVa-fv])\b',
        r'\bQ\s*(\d{1,2})\s*[:\-\s]\s*([A-FVa-fv])\b',
        r'\b(\d{1,2})\s+([A-FVa-fv])\b',
    ]
    valid = "ABCDEFV"
    for pattern in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            num = int(m.group(1))
            alt = m.group(2).upper()
            if 1 <= num <= 60 and alt in valid and num not in respostas:
                respostas[num] = alt
    return respostas


@app.post("/provas/{prova_id}/ocr-aluno", summary="OCR do gabarito físico de um aluno")
async def ocr_gabarito_aluno(
    prova_id: int,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    _require_prova_access(prova_id, user)
    suffix, content = await _ler_upload(file, "gabarito.jpg")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        noop = lambda pct, msg: None
        text, method = extract_text_from_file(tmp_path, noop)
        respostas = _parse_respostas_ocr(text)
        return {
            "respostas":       respostas,
            "total_detectado": len(respostas),
            "ocr_method":      method,
            "texto_bruto":     text[:800],
        }
    except Exception as exc:
        raise HTTPException(500, f"Erro no OCR: {exc}") from exc
    finally:
        os.unlink(tmp_path)


# ═══════════════════════════════════════════════════════════════════════════════
# PROVA ONLINE — Pivô para criação manual + aplicação online
# ═══════════════════════════════════════════════════════════════════════════════
import hashlib  # noqa: E402
import secrets  # noqa: E402
from typing import List  # noqa: E402
from fastapi import Request  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────────────────────
def _fingerprint(request: Request) -> str:
    """Gera fingerprint do dispositivo (sha256 do IP + User-Agent)."""
    xff = request.headers.get("x-forwarded-for", "")
    ip = (xff.split(",")[0].strip() if xff else (request.client.host if request.client else "")) or ""
    ua = request.headers.get("user-agent", "") or ""
    raw = f"{ip}::{ua}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _request_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return (request.client.host if request.client else "") or ""


def _gerar_pin() -> str:
    """PIN de 6 dígitos. Não usa 0 e 1 pra evitar confusão visual."""
    digitos = "23456789"
    return "".join(secrets.choice(digitos) for _ in range(6))


def _create_aluno_token(aluno_id: int) -> str:
    """JWT específico de aluno (não é usuário do sistema)."""
    exp = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode({"aid": aluno_id, "kind": "aluno", "exp": exp}, _SECRET, algorithm=_ALGO)


def get_current_aluno(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> Dict:
    if not creds:
        raise HTTPException(401, "Token de aluno não fornecido.")
    try:
        payload = jwt.decode(creds.credentials, _SECRET, algorithms=[_ALGO])
        if payload.get("kind") != "aluno":
            raise HTTPException(401, "Token inválido.")
        aid = int(payload.get("aid", 0))
    except (JWTError, ValueError):
        raise HTTPException(401, "Token inválido ou expirado.")
    aluno = db.get_aluno(aid)
    if not aluno:
        raise HTTPException(401, "Aluno não encontrado.")
    return aluno


# ── Schemas ──────────────────────────────────────────────────────────────────
class ProvaManualCreate(BaseModel):
    titulo: str
    turma_id: Optional[int] = None
    disciplina: str = ""
    serie: str = ""
    tempo_limite_min: Optional[int] = None


class QuestaoCreate(BaseModel):
    stem: str
    alternativas: List[str]
    gabarito: str
    tipo: str = "multipla_escolha"
    bloom_nivel: int = 0
    bloom_nome: str = ""
    bloom_verbo: str = ""
    taxonomia_codigo: str = ""


class QuestaoUpdate(BaseModel):
    stem: str
    alternativas: List[str]
    gabarito: str
    tipo: str = "multipla_escolha"
    bloom_nivel: int = 0
    bloom_nome: str = ""
    bloom_verbo: str = ""
    taxonomia_codigo: str = ""


class PublicarProvaIn(BaseModel):
    tempo_limite_min: Optional[int] = None


class AlunoLoginIn(BaseModel):
    nome: str
    ra: str


class IniciarProvaIn(BaseModel):
    pin: str


class ResponderQuestaoIn(BaseModel):
    questao_id: int
    resposta: str
    tempo_segundos: Optional[int] = None


# ── Endpoints professor: prova manual ────────────────────────────────────────
@app.post("/provas/manual", status_code=201, summary="Cria uma prova manualmente (sem OCR), em rascunho")
def criar_prova_manual_endpoint(body: ProvaManualCreate, user=Depends(get_current_user)):
    if body.turma_id:
        _require_turma_access(body.turma_id, user)
    pid = db.criar_prova_manual(
        titulo=body.titulo or "Prova sem título",
        turma_id=body.turma_id,
        disciplina=body.disciplina,
        serie=body.serie,
        usuario_id=user["id"],
        tempo_limite_min=body.tempo_limite_min,
    )
    return db.get_prova(pid)


@app.put("/provas/{prova_id}", summary="Atualiza dados de uma prova manual em rascunho")
def atualizar_prova_manual_endpoint(prova_id: int, body: ProvaManualCreate, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    prova = db.get_prova(prova_id)
    if prova.get("status") != "rascunho":
        raise HTTPException(400, "Só é possível alterar os dados de uma prova em rascunho.")
    if body.turma_id:
        _require_turma_access(body.turma_id, user)
    if body.tempo_limite_min is not None and body.tempo_limite_min <= 0:
        raise HTTPException(422, "O tempo limite deve ser maior que zero.")
    db.atualizar_prova_manual(
        prova_id, body.titulo.strip() or "Prova sem título", body.turma_id,
        body.disciplina, body.serie, body.tempo_limite_min,
    )
    return db.get_prova(prova_id)


@app.get("/provas/{prova_id}/edicao", summary="Detalhes da prova para edição (com alternativas e gabarito)")
def get_prova_edicao(prova_id: int, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    prova = db.get_prova(prova_id)
    questoes = db.get_questoes_prova(prova_id)
    gabarito = db.get_gabarito(prova_id)
    import json as _json
    for q in questoes:
        try:
            q["alternativas"] = _json.loads(q.get("alternativas") or "[]")
        except Exception:
            q["alternativas"] = []
        q["gabarito"] = gabarito.get(q["numero"], "")
    return {"prova": prova, "questoes": questoes}


def _etapa_da_prova(prova: Dict) -> Optional[str]:
    turma = db.get_turma(prova["turma_id"]) if prova.get("turma_id") else None
    return (turma or {}).get("etapa") or None


def _materia_da_disciplina(disciplina: str, etapa: Optional[str]) -> tuple:
    """(materia, etapa) a partir do que a prova guarda em `disciplina`: slug,
    nome do mapa fixo ou label da taxonomia (o front de /criar-prova envia o label)."""
    if not disciplina:
        return "", etapa
    chave = SUBJECT_TO_KEY.get(disciplina)
    if chave:
        return chave, etapa
    achado = db_taxonomia.materia_por_label(disciplina, etapa) or db_taxonomia.materia_por_label(disciplina)
    if achado:
        return achado["materia"], etapa or achado["etapa"]
    return "", etapa


def _classificar_questao(stem: str, alternativas: list, disciplina: str, etapa: Optional[str] = None) -> Dict:
    """Roda o pipeline taxonomico sobre uma questao criada manualmente.
    Usa a disciplina da prova como hint de materia (fallback: classify_across_all).
    Retorna dict com area_key, area_display, subarea_key, subarea_label,
    bloom_nivel, bloom_nome, bloom_verbo, taxonomia_codigo.
    Resultado fica como SUGESTAO automatica — frontend pode permitir override."""
    stem_full = (stem or "") + " " + " ".join(alternativas or [])
    stem_full = stem_full.strip()

    # 1) Bloom
    try:
        bloom_level, bloom_name, bloom_verb = classify_bloom(stem)
    except Exception:
        bloom_level, bloom_name, bloom_verb = 0, "", ""

    # 2) Materia/area: usa a disciplina da prova como hint (se informada)
    area_key, etapa_materia = _materia_da_disciplina(disciplina or "", etapa)
    tem_hint = bool(area_key)
    tax = None

    if area_key:
        try:
            tax = classify_taxonomia(stem_full, area_key, etapa_materia or "ef2")
        except Exception:
            tax = None

    # Fallback automatico SO se NAO ha hint de disciplina (auto-detect puro).
    # Se o professor informou a disciplina e a classificacao falhou, melhor
    # deixar sem nó taxonomico do que classificar errado em outra materia.
    if not tax and not tem_hint:
        try:
            tax_auto = classify_taxonomia_auto(stem_full)
            # Threshold mais alto: >= 2 matches na materia para evitar
            # classificacao por palavra solta
            if tax_auto and tax_auto.get("materia_total_matches", 0) >= 2:
                tax = tax_auto
                area_key = tax_auto.get("materia") or area_key
        except Exception:
            pass

    area_display = get_area_display_name(area_key) if area_key else ""

    # 3) Subarea (baseada na area)
    try:
        subarea_key, subarea_label = classify_subarea(stem, area_key)
    except Exception:
        subarea_key, subarea_label = "geral", "Geral"

    return {
        "area_key":          area_key or "",
        "area_display":      area_display or "",
        "subarea_key":       subarea_key or "geral",
        "subarea_label":     subarea_label or "Geral",
        "bloom_nivel":       bloom_level or 0,
        "bloom_nome":        bloom_name or "",
        "bloom_verbo":       bloom_verb or "",
        "taxonomia_codigo":  (tax or {}).get("codigo", "") if tax else "",
        "taxonomia_label":   (tax or {}).get("label", "") if tax else "",
        "taxonomia_caminho": (tax or {}).get("caminho", []) if tax else [],
    }


@app.post("/provas/{prova_id}/questoes", status_code=201, summary="Adiciona questão a uma prova manual (com classificação automática)")
def add_questao_manual(prova_id: int, body: QuestaoCreate, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    prova = db.get_prova(prova_id)
    if prova.get("status") == "encerrada":
        raise HTTPException(400, "Prova já encerrada.")

    # Roda classificacao automatica (Bloom + materia + taxonomia + subarea)
    auto = _classificar_questao(body.stem, body.alternativas, prova.get("disciplina") or "", _etapa_da_prova(prova))

    # Override: se o professor passou valores nao-default, prevalece
    bloom_nivel = body.bloom_nivel if body.bloom_nivel else auto["bloom_nivel"]
    bloom_nome  = body.bloom_nome  or auto["bloom_nome"]
    bloom_verbo = body.bloom_verbo or auto["bloom_verbo"]
    taxonomia_codigo = body.taxonomia_codigo or auto["taxonomia_codigo"]

    questoes = db.get_questoes_prova(prova_id)
    proximo = (max([q["numero"] for q in questoes], default=0) or 0) + 1

    qid = db.adicionar_questao_manual(
        prova_id=prova_id,
        numero=proximo,
        stem=body.stem,
        alternativas=body.alternativas,
        gabarito=body.gabarito,
        tipo=body.tipo,
        bloom_nivel=bloom_nivel,
        bloom_nome=bloom_nome,
        bloom_verbo=bloom_verbo,
        taxonomia_codigo=taxonomia_codigo,
        area_key=auto["area_key"],
        area_display=auto["area_display"],
        subarea_key=auto["subarea_key"],
        subarea_label=auto["subarea_label"],
    )
    return {
        "id": qid, "numero": proximo,
        "classificacao_automatica": {
            "bloom_nivel": bloom_nivel,
            "bloom_nome": bloom_nome,
            "area_display": auto["area_display"],
            "taxonomia_codigo": taxonomia_codigo,
            "taxonomia_label": auto["taxonomia_label"],
            "taxonomia_caminho": auto["taxonomia_caminho"],
        },
    }


@app.put("/provas/{prova_id}/questoes/{questao_id}", summary="Atualiza questão de uma prova manual (re-classifica automaticamente)")
def update_questao_manual(prova_id: int, questao_id: int, body: QuestaoUpdate, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    _require_questao_da_prova(questao_id, prova_id)
    prova = db.get_prova(prova_id)
    auto = _classificar_questao(body.stem, body.alternativas, prova.get("disciplina") or "", _etapa_da_prova(prova))

    # Override: se o professor passou valores nao-default no body, prevalece sobre auto
    bloom_nivel = body.bloom_nivel if body.bloom_nivel else auto["bloom_nivel"]
    bloom_nome  = body.bloom_nome  or auto["bloom_nome"]
    bloom_verbo = body.bloom_verbo or auto["bloom_verbo"]
    taxonomia_codigo = body.taxonomia_codigo or auto["taxonomia_codigo"]

    if not db.atualizar_questao_manual(
        questao_id=questao_id,
        stem=body.stem,
        alternativas=body.alternativas,
        gabarito=body.gabarito,
        tipo=body.tipo,
        bloom_nivel=bloom_nivel,
        bloom_nome=bloom_nome,
        bloom_verbo=bloom_verbo,
        taxonomia_codigo=taxonomia_codigo,
        area_key=auto["area_key"],
        area_display=auto["area_display"],
        subarea_key=auto["subarea_key"],
        subarea_label=auto["subarea_label"],
    ):
        raise HTTPException(404, "Questão não encontrada.")
    return {
        "ok": True,
        "classificacao_automatica": {
            "bloom_nivel": bloom_nivel,
            "bloom_nome": bloom_nome,
            "area_display": auto["area_display"],
            "taxonomia_codigo": taxonomia_codigo,
            "taxonomia_label": auto["taxonomia_label"],
            "taxonomia_caminho": auto["taxonomia_caminho"],
        },
    }


@app.delete("/provas/{prova_id}/questoes/{questao_id}", status_code=204, summary="Remove questão")
def delete_questao(prova_id: int, questao_id: int, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    _require_questao_da_prova(questao_id, prova_id)
    if not db.deletar_questao(questao_id):
        raise HTTPException(404, "Questão não encontrada.")


@app.post("/provas/{prova_id}/publicar", summary="Publica prova e gera PIN ad-hoc")
def publicar_prova_endpoint(prova_id: int, body: PublicarProvaIn = Body(default=None), user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    prova = db.get_prova(prova_id)
    if not prova.get("turma_id"):
        raise HTTPException(400, "Vincule a prova a uma turma antes de publicar.")
    questoes = db.get_questoes_prova(prova_id)
    if not questoes:
        raise HTTPException(400, "A prova não tem questões.")
    pin = _gerar_pin()
    db.publicar_prova(prova_id, pin, body.tempo_limite_min if body else None)
    return {"ok": True, "pin": pin, "total_questoes": len(questoes)}


@app.post("/provas/{prova_id}/encerrar", summary="Encerra aplicação da prova")
def encerrar_prova_endpoint(prova_id: int, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    db.encerrar_prova(prova_id)
    return {"ok": True}


@app.get("/provas/{prova_id}/monitor", summary="Lista alunos da turma com status de aplicação")
def monitor_prova(prova_id: int, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    prova = db.get_prova(prova_id)
    acessos = db.listar_acessos_prova(prova_id)
    out = []
    for a in acessos:
        if a.get("finished_at"):
            status = "finalizado"
        elif a.get("started_at") and a.get("fingerprint"):
            status = "em_andamento"
        elif a.get("started_at"):
            status = "aguardando_relogin"
        else:
            status = "aguardando"
        out.append({**a, "status": status})
    return {
        "prova": {
            "id": prova["id"],
            "titulo": prova.get("titulo"),
            "status": prova.get("status"),
            "pin": prova.get("pin"),
            "publicada_em": prova.get("publicada_em"),
            "encerrada_em": prova.get("encerrada_em"),
            "total_questoes": prova.get("total_questoes"),
        },
        "acessos": out,
    }


@app.post("/provas/{prova_id}/alunos/{aluno_id}/liberar-relogin", summary="Libera relogin de aluno (caso celular travou)")
def liberar_relogin_endpoint(prova_id: int, aluno_id: int, user=Depends(get_current_user)):
    _require_prova_access(prova_id, user)
    ok = db.liberar_relogin(prova_id, aluno_id)
    if not ok:
        raise HTTPException(400, "Não foi possível liberar relogin (prova já finalizada ou inexistente).")
    return {"ok": True}


# ── Endpoints públicos do aluno ──────────────────────────────────────────────
@app.post("/aluno/auth", summary="Login do aluno (Nome completo + R.A.)")
def aluno_auth(body: AlunoLoginIn):
    aluno = db.buscar_aluno_por_nome_ra(body.nome, body.ra)
    if not aluno:
        raise HTTPException(401, "Nome ou R.A. não conferem. Verifique com o professor.")
    tok = _create_aluno_token(aluno["id"])
    return {"token": tok, "aluno": {"id": aluno["id"], "nome": aluno["nome"], "ra": aluno.get("ra") or ""}}


@app.get("/aluno/me", summary="Dados do aluno autenticado")
def aluno_me(aluno=Depends(get_current_aluno)):
    return {
        "id": aluno["id"],
        "nome": aluno["nome"],
        "ra": aluno.get("ra") or "",
        "turma_id": aluno.get("turma_id"),
    }


@app.get("/aluno/provas", summary="Lista provas em aberto da turma do aluno")
def aluno_listar_provas(aluno=Depends(get_current_aluno)):
    return db.listar_provas_em_aberto_para_aluno(aluno["id"])


@app.post("/aluno/provas/{prova_id}/iniciar", summary="Inicia uma prova (valida PIN, registra fingerprint)")
def aluno_iniciar_prova(prova_id: int, body: IniciarProvaIn, request: Request, aluno=Depends(get_current_aluno)):
    prova = db.get_prova(prova_id)
    if not prova:
        raise HTTPException(404, "Prova não encontrada.")
    if prova.get("status") != "publicada":
        raise HTTPException(400, "Esta prova não está aberta para resposta.")
    # Turma antes do PIN: aluno de outra turma não consegue testar PINs
    if prova.get("turma_id") != aluno.get("turma_id"):
        raise HTTPException(403, "Esta prova não pertence à sua turma.")
    # 422 (e não 401): PIN errado não é sessão expirada — o front não deve deslogar
    if (prova.get("pin") or "").strip() != (body.pin or "").strip():
        raise HTTPException(422, "PIN incorreto. Confira com o professor.")

    fp = _fingerprint(request)
    ip = _request_ip(request)
    ua = request.headers.get("user-agent", "")
    try:
        acesso = db.criar_ou_obter_acesso(prova_id, aluno["id"], fp, ip, ua)
    except ValueError as e:
        msg = str(e)
        if msg == "prova_ja_finalizada":
            raise HTTPException(403, "Você já finalizou esta prova.")
        if msg == "dispositivo_diferente":
            raise HTTPException(409, "Esta prova já foi iniciada em outro dispositivo. Peça ao professor para liberar relogin.")
        raise HTTPException(400, "Não foi possível iniciar a prova.")
    return {"ok": True, "acesso": acesso}


@app.get("/aluno/provas/{prova_id}/questoes", summary="Retorna as questões (sem o gabarito) para o aluno responder")
def aluno_questoes(prova_id: int, request: Request, aluno=Depends(get_current_aluno)):
    prova = db.get_prova(prova_id)
    if not prova:
        raise HTTPException(404, "Prova não encontrada.")
    if prova.get("status") != "publicada":
        raise HTTPException(400, "Prova não está aberta.")
    if prova.get("turma_id") != aluno.get("turma_id"):
        raise HTTPException(403, "Você não tem acesso a esta prova.")
    acesso = db.get_acesso(prova_id, aluno["id"])
    if not acesso:
        raise HTTPException(403, "Inicie a prova primeiro.")
    if acesso.get("finished_at"):
        raise HTTPException(403, "Prova já finalizada.")
    fp = _fingerprint(request)
    if acesso.get("fingerprint") and acesso["fingerprint"] != fp:
        raise HTTPException(409, "Dispositivo diferente do que iniciou a prova.")
    questoes = db.get_questoes_para_aluno(prova_id)
    return {
        "prova": {
            "id": prova["id"], "titulo": prova.get("titulo"),
            "disciplina": prova.get("disciplina"), "total_questoes": prova.get("total_questoes"),
            "tempo_limite_min": prova.get("tempo_limite_min"),
        },
        "started_at": acesso.get("started_at"),
        # Calculado no servidor: evita erro de fuso/formato de data no navegador
        "segundos_decorridos": _segundos_desde(acesso.get("started_at")),
        "questoes": questoes,
        # Respostas já salvas: o servidor é a fonte da verdade (relogin, outro aparelho)
        "respostas": {str(k): v for k, v in db.get_respostas_aluno_prova(aluno["id"], prova_id).items()},
    }


_TOLERANCIA_TEMPO_SEG = 60  # latência de rede / relógio


def _segundos_desde(ts) -> int:
    """Segundos desde `ts` (datetime do Postgres com fuso ou texto local do SQLite)."""
    if ts is None:
        return 0
    if not isinstance(ts, datetime):
        try:
            ts = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except ValueError:
            return 0
    agora = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
    return max(0, int((agora - ts).total_seconds()))


def _tempo_esgotado(prova: Dict, acesso: Dict) -> bool:
    limite = prova.get("tempo_limite_min")
    if not limite:
        return False
    return _segundos_desde(acesso.get("started_at")) > limite * 60 + _TOLERANCIA_TEMPO_SEG


@app.post("/aluno/provas/{prova_id}/responder", summary="Salva a resposta do aluno para uma questão")
def aluno_responder(prova_id: int, body: ResponderQuestaoIn, request: Request, aluno=Depends(get_current_aluno)):
    prova = db.get_prova(prova_id)
    if not prova or prova.get("status") != "publicada":
        raise HTTPException(400, "Prova indisponível.")
    if prova.get("turma_id") != aluno.get("turma_id"):
        raise HTTPException(403, "Sem acesso.")
    acesso = db.get_acesso(prova_id, aluno["id"])
    if not acesso or acesso.get("finished_at"):
        raise HTTPException(403, "Prova não iniciada ou já finalizada.")
    fp = _fingerprint(request)
    if acesso.get("fingerprint") and acesso["fingerprint"] != fp:
        raise HTTPException(409, "Dispositivo diferente.")
    if _tempo_esgotado(prova, acesso):
        raise HTTPException(403, "O tempo da prova terminou.")
    out = db.salvar_resposta_unica(
        aluno_id=aluno["id"],
        prova_id=prova_id,
        questao_id=body.questao_id,
        resposta=body.resposta,
        tempo_segundos=body.tempo_segundos,
    )
    if not out.get("ok"):
        raise HTTPException(400, out.get("erro", "Erro ao salvar resposta."))
    return {"ok": True}


class ReclassificarIn(BaseModel):
    prova_ids: Optional[list] = None
    disciplina: Optional[str] = None


@app.get("/admin/taxonomia/reclassificar/preview", summary="Conta quantas questoes serao reclassificadas")
def reclassificar_preview(disciplina: Optional[str] = None, user=Depends(get_current_user)):
    if user.get("role") != "admin_geral":
        raise HTTPException(403, "Apenas admin_geral pode reclassificar taxonomia.")
    questoes = db.listar_questoes_para_reclassificar(disciplina_filter=disciplina)
    disciplinas = db.listar_disciplinas_distintas()
    provas_unicas = len({q["prova_id"] for q in questoes})
    return {
        "total_questoes": len(questoes),
        "total_provas": provas_unicas,
        "disciplinas_disponiveis": disciplinas,
    }


@app.post("/admin/taxonomia/reclassificar", summary="Reclassifica taxonomia de provas existentes (admin_geral)")
def reclassificar_taxonomia(body: ReclassificarIn = Body(default=None), user=Depends(get_current_user)):
    if user.get("role") != "admin_geral":
        raise HTTPException(403, "Apenas admin_geral pode reclassificar taxonomia.")

    prova_ids = body.prova_ids if body and body.prova_ids else None
    disciplina = body.disciplina if body and body.disciplina else None

    questoes = db.listar_questoes_para_reclassificar(
        prova_ids=prova_ids,
        disciplina_filter=disciplina,
    )

    atualizadas = 0
    mantidas = 0
    mudancas_resumo = []  # primeiras 20 mudancas para log/feedback

    for q in questoes:
        alts = q.get("alternativas_lista") or []
        nova = _classificar_questao(q.get("stem") or "", alts, q.get("disciplina") or "", q.get("turma_etapa"))

        antes = (q.get("taxonomia_codigo") or "", q.get("bloom_nivel") or 0, q.get("area_key") or "")
        depois = (nova.get("taxonomia_codigo") or "", nova.get("bloom_nivel") or 0, nova.get("area_key") or "")

        if antes == depois:
            mantidas += 1
            continue

        db.atualizar_classificacao_questao(
            questao_id=q["id"],
            area_key=nova["area_key"],
            area_display=nova["area_display"],
            subarea_key=nova["subarea_key"],
            subarea_label=nova["subarea_label"],
            bloom_nivel=nova["bloom_nivel"],
            bloom_nome=nova["bloom_nome"],
            bloom_verbo=nova["bloom_verbo"],
            taxonomia_codigo=nova["taxonomia_codigo"],
        )
        atualizadas += 1
        if len(mudancas_resumo) < 20:
            mudancas_resumo.append({
                "prova_id": q["prova_id"],
                "prova_titulo": q.get("prova_titulo") or "",
                "numero": q["numero"],
                "antes": {"taxonomia": antes[0], "bloom": antes[1], "area": antes[2]},
                "depois": {"taxonomia": depois[0], "bloom": depois[1], "area": depois[2]},
            })

    return {
        "ok": True,
        "atualizadas": atualizadas,
        "mantidas": mantidas,
        "total_processadas": len(questoes),
        "mudancas": mudancas_resumo,
    }


@app.post("/aluno/provas/{prova_id}/finalizar", summary="Finaliza a prova do aluno (registra finished_at)")
def aluno_finalizar(prova_id: int, request: Request, aluno=Depends(get_current_aluno)):
    prova = db.get_prova(prova_id)
    if not prova:
        raise HTTPException(404, "Prova não encontrada.")
    acesso = db.get_acesso(prova_id, aluno["id"])
    if not acesso:
        raise HTTPException(403, "Prova não iniciada.")
    fp = _fingerprint(request)
    if acesso.get("fingerprint") and acesso["fingerprint"] != fp:
        raise HTTPException(409, "Dispositivo diferente.")
    db.finalizar_acesso(prova_id, aluno["id"])
    return {"ok": True}
