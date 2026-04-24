"""
EduMap IA — FastAPI Backend
Inicie com: uvicorn api:app --reload
Documentação: http://localhost:8000/docs
"""
import os
import re
import sys
import tempfile
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
from database import db
from database import taxonomia as db_taxonomia
from database import usuarios as db_usuarios
from ocr.extractor import extract_text_from_file
from report.relatorio_pdf import gerar_pdf_relatorio

JSON_TAXONOMIA = Path(__file__).parent / "data" / "taxonomia.json"
JSON_TEMPLATE = Path(__file__).parent / "data" / "taxonomia_template.json"

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="EduMap IA API",
    version="0.1.0",
    description="Backend da plataforma EduMap IA — diagnóstico taxonômico de aprendizagem.",
)

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
_SECRET = os.getenv("SECRET_KEY", "edumap-dev-secret-change-in-prod")
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
    "Matemática": "matematica", "Português": "portugues",
    "Ciências": "ciencias",    "História": "historia",
    "Geografia": "geografia",  "Biologia": "biologia",
    "Física": "fisica",        "Química": "quimica",
    "Inglês": "ingles",        "Artes": "artes",
    "Ed. Física": "ed_fisica",
    "Psicologia, Saúde Mental e SUS": "psicologia_saude_mental_sus",
}

# ── Schemas ───────────────────────────────────────────────────────────────────
class TurmaCreate(BaseModel):
    nome: str
    escola: str = ""
    disciplina: str = ""


class AlunoCreate(BaseModel):
    nome: str


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


# ── Auth endpoints ────────────────────────────────────────────────────────────
@app.post("/auth/register", status_code=201, summary="Registra novo usuário")
def auth_register(body: RegisterBody):
    if db_usuarios.get_usuario_por_email(body.email):
        raise HTTPException(400, "Email já cadastrado.")
    count = db_usuarios.contar_usuarios()
    role = "admin_geral" if count == 0 else "professor"
    uid = db_usuarios.criar_usuario(body.nome, body.email, _hash(body.senha), role, body.escola)
    return {"token": _create_token(uid), "role": role, "nome": body.nome}


@app.post("/auth/login", summary="Autentica usuário e retorna JWT")
def auth_login(body: LoginBody):
    user = db_usuarios.get_usuario_por_email(body.email)
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


@app.get("/admin/escolas", summary="Lista escolas agregadas (admin_geral)")
def admin_list_escolas(user=Depends(get_current_user)):
    _require_admin_geral(user)
    return db_usuarios.listar_escolas()


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
    tid = db.criar_turma(body.nome, body.escola, body.disciplina, uid)
    turma = db.get_turma(tid)
    return turma


@app.delete("/turmas/{turma_id}", status_code=204, summary="Remove uma turma")
def delete_turma(turma_id: int, user=Depends(get_current_user)):
    if not db.get_turma(turma_id):
        raise HTTPException(404, "Turma não encontrada.")
    db.delete_turma(turma_id)


# ── Alunos ────────────────────────────────────────────────────────────────────
@app.get("/turmas/{turma_id}/alunos", summary="Lista alunos de uma turma")
def list_alunos(turma_id: int, user=Depends(get_current_user)):
    return db.listar_alunos(turma_id)


@app.post("/turmas/{turma_id}/alunos", status_code=201, summary="Adiciona aluno à turma")
def create_aluno(turma_id: int, body: AlunoCreate, user=Depends(get_current_user)):
    if not db.get_turma(turma_id):
        raise HTTPException(404, "Turma não encontrada.")
    aid = db.criar_aluno(body.nome, turma_id)
    return {"id": aid, "nome": body.nome, "turma_id": turma_id}


# ── Provas ────────────────────────────────────────────────────────────────────
@app.get("/turmas/{turma_id}/provas", summary="Lista provas de uma turma")
def list_provas(turma_id: int, user=Depends(get_current_user)):
    return db.listar_provas(turma_id)


@app.post("/provas/upload", summary="Faz upload de prova, executa OCR e classifica questões")
async def upload_prova(
    file: UploadFile = File(...),
    year_level: str = Form(...),
    subject: str = Form("Detectar automaticamente"),
    turma_id: Optional[str] = Form(None),
    user=Depends(get_current_user),
):
    suffix = Path(file.filename or "prova.pdf").suffix or ".pdf"
    content = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        noop = lambda pct, msg: None
        text, method = extract_text_from_file(tmp_path, noop)
        questions = segment_questions(text)

        for q in questions:
            stem = q.get("stem") or q.get("text", "")

            if subject and subject != "Detectar automaticamente":
                area_key = SUBJECT_TO_KEY.get(subject, "indefinida")
                area_conf = 1.0
            else:
                area_key, area_conf, _ = classify_area(stem)

            bloom_level, bloom_name, bloom_verb = classify_bloom(stem)
            subarea_key, subarea_label = classify_subarea(stem, area_key)
            bncc = map_to_bncc(area_key, year_level, bloom_level)

            # Classificação taxonômica profunda (árvore do banco)
            tax = None
            if area_key and area_key != "indefinida":
                try:
                    tax = classify_taxonomia(stem, area_key)
                except Exception:
                    tax = None

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

        tid = int(turma_id) if turma_id and turma_id not in ("", "none") else None
        disc_key = SUBJECT_TO_KEY.get(subject, "")

        prova_id = db.salvar_prova(
            titulo=file.filename or "prova",
            serie=year_level,
            disciplina=disc_key,
            arquivo_nome=file.filename or "prova",
            ocr_method=method,
            questoes=questions,
            turma_id=tid,
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

    except Exception as exc:
        raise HTTPException(500, f"Erro ao processar prova: {exc}") from exc
    finally:
        os.unlink(tmp_path)


# ── Questoes + Relatórios ─────────────────────────────────────────────────────
@app.get("/provas/{prova_id}/questoes", summary="Lista questões de uma prova")
def get_questoes(prova_id: int, user=Depends(get_current_user)):
    return db.get_questoes_prova(prova_id)


@app.get("/provas/{prova_id}/relatorio/turma", summary="Relatório de desempenho por aluno")
def get_relatorio_turma(prova_id: int, user=Depends(get_current_user)):
    return db.relatorio_turma(prova_id)


@app.get("/provas/{prova_id}/relatorio/drilldown", summary="Relatório drill-down área→subárea→bloom→aluno")
def get_relatorio_drilldown(prova_id: int, user=Depends(get_current_user)):
    return db.relatorio_drilldown(prova_id)


@app.get("/provas/{prova_id}/relatorio/taxonomia", summary="Árvore taxonômica com stats por nó")
def get_relatorio_taxonomia(prova_id: int, user=Depends(get_current_user)):
    return db.relatorio_taxonomia(prova_id)


@app.get("/provas/{prova_id}/relatorio/pontos-criticos", summary="Pontos críticos por aluno (taxonomia)")
def get_pontos_criticos(prova_id: int, top_n: int = 3, user=Depends(get_current_user)):
    return db.alunos_pontos_criticos(prova_id, top_n)


@app.get("/provas/{prova_id}/relatorio/pdf", summary="Gera relatório pedagógico em PDF")
def get_relatorio_pdf(prova_id: int, user=Depends(get_current_user)):
    prova = db.get_prova(prova_id)
    if not prova:
        raise HTTPException(404, "Prova não encontrada.")
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
    respostas = {
        int(k): {"resposta": v.resposta, "gabarito": v.gabarito, "correta": v.correta}
        for k, v in payload.respostas.items()
    }
    db.salvar_respostas(payload.aluno_id, prova_id, respostas)
    return {"ok": True}


# ── Gabarito ──────────────────────────────────────────────────────────────────
@app.post("/provas/{prova_id}/gabarito", status_code=201, summary="Salva gabarito da prova")
def save_gabarito(prova_id: int, payload: GabaritoPayload, user=Depends(get_current_user)):
    gabarito = {int(k): v for k, v in payload.gabarito.items()}
    db.salvar_gabarito(prova_id, gabarito)
    return {"ok": True}


@app.get("/provas/{prova_id}/gabarito", summary="Retorna gabarito da prova")
def get_gabarito(prova_id: int, user=Depends(get_current_user)):
    return db.get_gabarito(prova_id)


@app.post("/provas/{prova_id}/lancar", status_code=201, summary="Lança respostas de vários alunos")
def lancar_respostas(prova_id: int, payload: LancarBulkPayload, user=Depends(get_current_user)):
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
    respostas: Dict[int, str] = {}
    patterns = [
        r'\b(\d{1,2})\s*[.)\-:]\s*([A-Ea-e])\b',
        r'\bQ\s*(\d{1,2})\s*[:\-\s]\s*([A-Ea-e])\b',
        r'\b(\d{1,2})\s+([A-Ea-e])\b',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            num = int(m.group(1))
            alt = m.group(2).upper()
            if 1 <= num <= 60 and alt in "ABCDE" and num not in respostas:
                respostas[num] = alt
    return respostas


@app.post("/provas/{prova_id}/ocr-aluno", summary="OCR do gabarito físico de um aluno")
async def ocr_gabarito_aluno(
    prova_id: int,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    suffix = Path(file.filename or "gabarito.jpg").suffix or ".jpg"
    content = await file.read()

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
