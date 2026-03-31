import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ocr.extractor import extract_text_from_file
from classifier.segmenter import segment_questions
from classifier.area_classifier import classify_area, get_area_display_name
from classifier.bloom_classifier import classify_bloom, get_bloom_display
from classifier.subarea_classifier import classify_subarea
from classifier.bncc_mapper import map_to_bncc
from report.charts import create_bloom_chart, create_area_chart, create_heatmap
from report.recommender import generate_recommendations
from report.pdf_exporter import export_pdf
from database import db

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="EduMap IA", page_icon="🗺️", layout="wide")
st.markdown("""
<style>
  .main-title { font-size:2.3rem; font-weight:700; color:#111827; }
  .main-sub   { color:#6B7280; font-size:1rem; margin-top:2px; }
  .rec-box    { border-radius:8px; padding:10px 14px; margin:6px 0; }
  .card       { background:#F3F4F6; border-radius:8px; padding:16px; margin:8px 0; border-left:4px solid #1D4ED8; }
  /* keep badge text legible on any pct background */
  .edu-badge  { color:#fff; padding:2px 10px; border-radius:12px; font-size:.82rem; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
YEAR_OPTIONS = [
    "1º ano EF","2º ano EF","3º ano EF","4º ano EF","5º ano EF",
    "6º ano EF","7º ano EF","8º ano EF","9º ano EF",
    "1º ano EM","2º ano EM","3º ano EM",
]
SUBJECT_OPTIONS = [
    "Detectar automaticamente",
    "Matemática","Português","Ciências","História","Geografia",
    "Biologia","Física","Química","Inglês","Artes","Ed. Física",
]
SUBJECT_TO_KEY = {
    "Matemática":"matematica","Português":"portugues","Ciências":"ciencias",
    "História":"historia","Geografia":"geografia","Biologia":"biologia",
    "Física":"fisica","Química":"quimica","Inglês":"ingles",
    "Artes":"artes","Ed. Física":"ed_fisica",
}
BLOOM_COLORS = {1:"#3B82F6",2:"#10B981",3:"#F59E0B",4:"#F97316",5:"#EF4444",6:"#8B5CF6",0:"#9CA3AF"}
BLOOM_NAMES  = {1:"Lembrar",2:"Compreender",3:"Aplicar",4:"Analisar",5:"Avaliar",6:"Criar",0:"—"}


# ── Pipeline ──────────────────────────────────────────────────────────────────
def run_pipeline(uploaded_file, year_level: str, forced_subject: str):
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    try:
        bar = st.progress(0, text="Iniciando…")
        def prog(pct, msg): bar.progress(min(pct, 0.95), text=msg)

        prog(0.05, "Extraindo texto…")
        text, method = extract_text_from_file(tmp_path, prog)

        prog(0.45, "Identificando questões…")
        questions = segment_questions(text)

        prog(0.60, f"Classificando {len(questions)} questões…")
        for q in questions:
            stem = q.get("stem") or q.get("text", "")
            if forced_subject and forced_subject != "Detectar automaticamente":
                area_key  = SUBJECT_TO_KEY.get(forced_subject, "indefinida")
                area_conf = 1.0
            else:
                area_key, area_conf, _ = classify_area(stem)

            bloom_level, bloom_name, bloom_verb = classify_bloom(stem)
            subarea_key, subarea_label = classify_subarea(stem, area_key)
            bncc = map_to_bncc(area_key, year_level, bloom_level)
            q.update({
                "area_key": area_key,
                "area_display": get_area_display_name(area_key),
                "area_confidence": area_conf,
                "subarea_key": subarea_key,
                "subarea_label": subarea_label,
                "bloom_level": bloom_level,
                "bloom_name": bloom_name,
                "bloom_verb": bloom_verb,
                "bloom_color": BLOOM_COLORS.get(bloom_level, "#9CA3AF"),
                "bncc_skills": bncc,
            })

        bar.progress(1.0, text="Concluído!")
    finally:
        os.unlink(tmp_path)

    return {
        "questions": questions,
        "raw_text": text,
        "ocr_method": method,
        "file_name": uploaded_file.name,
        "year_level": year_level,
        "subject": forced_subject,
        "metadata": {
            "Arquivo": uploaded_file.name,
            "Série / Ano": year_level,
            "Extração": "OCR (imagem)" if method == "ocr" else "Texto digital",
            "Questões": str(len(questions)),
        },
    }


# ── Sidebar navigation ────────────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.markdown("### 🗺️ EduMap IA")
        st.caption("v0.1 MVP — Extensão Universitária")
        st.divider()
        page = st.radio(
            "Navegação",
            ["📤 Analisar Prova", "👥 Turmas e Alunos", "📊 Relatório do Professor"],
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("100% local · sem IA paga · código aberto")
    return page.split(" ", 1)[1]  # strip emoji prefix


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Analisar Prova
# ─────────────────────────────────────────────────────────────────────────────
def page_analisar():
    if "results" in st.session_state:
        _results_view()
    else:
        _upload_view()


def _upload_view():
    st.markdown('<p class="main-title">🗺️ EduMap IA</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-sub">Diagnóstico taxonomico inteligente de aprendizagem</p>', unsafe_allow_html=True)
    st.divider()

    col_form, col_info = st.columns([2, 1])
    with col_form:
        with st.form("upload"):
            ca, cb = st.columns(2)
            year = ca.selectbox("Série / Ano", YEAR_OPTIONS, index=5)
            subj = cb.selectbox("Disciplina", SUBJECT_OPTIONS)

            # Optional: link to turma
            turmas = db.listar_turmas()
            turma_opts = ["(sem turma)"] + [f"{t['nome']} — {t['escola']}" for t in turmas]
            turma_sel = st.selectbox("Vincular a turma (opcional)", turma_opts)

            uploaded = st.file_uploader("📎 Upload da prova (PDF, JPG, PNG)", type=["pdf","jpg","jpeg","png"])
            submitted = st.form_submit_button("🔍 Analisar Prova", use_container_width=True, type="primary")

        if submitted:
            if not uploaded:
                st.error("Selecione um arquivo.")
            else:
                try:
                    with st.spinner():
                        res = run_pipeline(uploaded, year, subj)

                    # Save to DB
                    turma_id = None
                    if turma_sel != "(sem turma)":
                        idx = turma_opts.index(turma_sel) - 1
                        turma_id = turmas[idx]["id"]

                    disc_key = SUBJECT_TO_KEY.get(subj, "")
                    prova_id = db.salvar_prova(
                        titulo=uploaded.name,
                        serie=year,
                        disciplina=disc_key,
                        arquivo_nome=uploaded.name,
                        ocr_method=res["ocr_method"],
                        questoes=res["questions"],
                        turma_id=turma_id,
                    )
                    res["prova_id"] = prova_id
                    st.session_state["results"] = res
                    st.rerun()
                except Exception as exc:
                    st.error(f"Erro: {exc}")
                    st.exception(exc)

    with col_info:
        st.markdown("#### Como funciona")
        st.markdown("""
1. Faça **upload da prova** (foto ou PDF)
2. Selecione **série** e **disciplina**
3. O sistema faz OCR e identifica questões
4. Classifica por **área** e **Bloom**
5. Gera **relatório diagnóstico**
        """)
        st.info("💡 Boa iluminação na foto = melhor precisão do OCR.")


def _results_view():
    res       = st.session_state["results"]
    questions = res["questions"]
    prova_id  = res.get("prova_id")

    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        if st.button("← Nova prova"):
            del st.session_state["results"]
            st.rerun()
    with c2:
        st.markdown(f"### 🗺️ EduMap IA — {res['metadata'].get('Arquivo','')}")
        if prova_id:
            st.caption(f"Prova salva no banco de dados (ID #{prova_id})")
    with c3:
        recs = generate_recommendations(questions)
        pdf  = export_pdf(questions, recs, res["metadata"])
        if pdf:
            st.download_button("⬇️ Baixar PDF", data=pdf,
                               file_name="relatorio_edumap.pdf", mime="application/pdf",
                               use_container_width=True)

    # Metrics
    area_counts: dict = {}
    for q in questions:
        a = q.get("area_display","—"); area_counts[a] = area_counts.get(a,0)+1
    bloom_counts: dict = {}
    for q in questions:
        l = q.get("bloom_level",0); bloom_counts[l] = bloom_counts.get(l,0)+1

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Questões", len(questions))
    m2.metric("Extração", res["ocr_method"].upper())
    m3.metric("Área predominante", max(area_counts, key=area_counts.get) if area_counts else "—")
    m4.metric("Bloom predominante", BLOOM_NAMES.get(max(bloom_counts, key=bloom_counts.get) if bloom_counts else 0,"—"))
    st.divider()

    tab1,tab2,tab3,tab4 = st.tabs(["📊 Visão Geral","📋 Por Questão","👥 Por Aluno","💡 Recomendações"])
    with tab1: _tab_overview(questions)
    with tab2: _tab_questions(questions)
    with tab3: _tab_students(questions, prova_id)
    with tab4: _tab_recommendations(questions, res)


def _tab_overview(questions):
    ca,cb = st.columns(2)
    with ca: st.plotly_chart(create_bloom_chart(questions), use_container_width=True)
    with cb: st.plotly_chart(create_area_chart(questions), use_container_width=True)
    st.markdown("#### Contagem por nível")
    cols = st.columns(6); total = len(questions) or 1
    for i in range(1,7):
        cnt = sum(1 for q in questions if q.get("bloom_level")==i)
        c = BLOOM_COLORS[i]
        cols[i-1].markdown(
            f"<div style='text-align:center;background:{c}18;border:1px solid {c}44;border-radius:10px;padding:10px 4px'>"
            f"<div style='font-size:1.6rem;font-weight:800;color:{c}'>{cnt}</div>"
            f"<div style='font-size:.75rem;color:#374151;font-weight:600'>{BLOOM_NAMES[i]}</div>"
            f"<div style='font-size:.82rem;color:#6B7280'>{cnt*100//total}%</div></div>",
            unsafe_allow_html=True)


def _tab_questions(questions):
    st.caption(f"{len(questions)} questões identificadas")
    for q in questions:
        lvl = q.get("bloom_level",0); color = BLOOM_COLORS.get(lvl,"#9CA3AF")
        with st.expander(f"Q{q['number']} — {q.get('area_display','?')} | {q.get('bloom_name','?')}"):
            ca,cb = st.columns([3,1])
            with ca:
                stem = q.get("stem") or q.get("text","")
                st.markdown("**Enunciado:**"); st.text(stem[:400]+("…" if len(stem)>400 else ""))
                alts = q.get("alternatives",[])
                if alts: st.markdown("**Alternativas:**"); [st.text(a) for a in alts[:5]]
            with cb:
                st.markdown(
                    f"<div style='background:{color}22;border:1px solid {color};border-radius:8px;padding:10px;text-align:center'>"
                    f"<div style='font-size:.72rem;color:#6B7280'>Bloom</div>"
                    f"<div style='font-weight:700;color:{color}'>{q.get('bloom_name','—')}</div>"
                    +(f"<div style='font-size:.7rem;color:#9CA3AF'>verbo: {q['bloom_verb']}</div>" if q.get("bloom_verb") else "")
                    +"</div>", unsafe_allow_html=True)
                st.markdown(f"**Área:** {q.get('area_display','—')}")
                conf = q.get("area_confidence",0)
                st.progress(conf, text=f"Confiança: {conf*100:.0f}%")
                for sk in q.get("bncc_skills",[])[:2]:
                    st.caption(f"`{sk['codigo']}` {sk.get('descricao','')[:55]}…")


def _tab_students(questions, prova_id):
    st.markdown("#### Registrar respostas dos alunos")

    alunos_db: list = []
    turmas = db.listar_turmas()
    if turmas:
        turma_names = [f"{t['nome']} — {t['escola']}" for t in turmas]
        sel = st.selectbox("Selecionar turma para buscar alunos", ["—"] + turma_names)
        if sel != "—":
            idx = turma_names.index(sel)
            alunos_db = db.listar_alunos(turmas[idx]["id"])

    if "students" not in st.session_state:
        st.session_state["students"] = []

    with st.expander("➕ Adicionar aluno e respostas"):
        with st.form("add_student"):
            if alunos_db:
                nome_opts = ["(digitar nome)"] + [a["nome"] for a in alunos_db]
                nome_sel = st.selectbox("Aluno (da turma)", nome_opts)
                nome_manual = st.text_input("Ou digite o nome")
                nome = nome_manual if nome_sel == "(digitar nome)" else nome_sel
            else:
                nome = st.text_input("Nome do aluno")

            col1, col2 = st.columns(2)
            respostas_str = col1.text_input("Respostas do aluno (A,B,C,A…)")
            gabarito_str  = col2.text_input("Gabarito correto (A,B,C,A…)")

            if st.form_submit_button("Adicionar"):
                if nome and respostas_str and gabarito_str:
                    ans = [x.strip().upper() for x in respostas_str.split(",")]
                    gab = [x.strip().upper() for x in gabarito_str.split(",")]
                    ans_map = {
                        q["number"]: "correct" if i<len(ans) and i<len(gab) and ans[i]==gab[i] else "wrong"
                        for i,q in enumerate(questions)
                    }
                    # Save to DB if prova_id exists
                    if prova_id:
                        # Find or create aluno
                        aluno_match = next((a for a in alunos_db if a["nome"]==nome), None)
                        if aluno_match:
                            aluno_id = aluno_match["id"]
                        else:
                            turma_id = turmas[turma_names.index(sel)]["id"] if alunos_db and sel!="—" else None
                            aluno_id = db.criar_aluno(nome, turma_id) if turma_id else None
                        if aluno_id:
                            respostas_db = {
                                q["number"]: {
                                    "resposta": ans[i] if i<len(ans) else "",
                                    "gabarito": gab[i] if i<len(gab) else "",
                                    "correta": i<len(ans) and i<len(gab) and ans[i]==gab[i],
                                }
                                for i,q in enumerate(questions)
                            }
                            db.salvar_respostas(aluno_id, prova_id, respostas_db)

                    st.session_state["students"].append({"name": nome, "answers": ans_map})
                    st.success(f"'{nome}' adicionado!")
                    st.rerun()

    students = st.session_state.get("students", [])
    if students:
        if st.button("🗑️ Limpar sessão"):
            st.session_state["students"] = []; st.rerun()
        fig = create_heatmap(students, questions)
        if fig: st.plotly_chart(fig, use_container_width=True)
        st.markdown("#### Resumo")
        for s in students:
            tot = len(s["answers"]); ok = sum(1 for v in s["answers"].values() if v=="correct")
            pct = f"{ok*100//tot}%" if tot else "—"
            st.markdown(f"**{s['name']}:** {ok}/{tot} ({pct})")
    else:
        st.info("Nenhum aluno adicionado ainda.")


def _tab_recommendations(questions, res):
    students = st.session_state.get("students", [])
    recs = generate_recommendations(questions, students)
    if not recs:
        st.info("Classifique as questões e adicione alunos para receber recomendações.")
        return
    styles = {
        "success": ("#ECFDF5","#065F46","🟢"),
        "warning": ("#FFFBEB","#92400E","🟡"),
        "critical":("#FEF2F2","#991B1B","🔴"),
        "info":    ("#EFF6FF","#1E40AF","🔵"),
    }
    for rec in recs:
        bg,fg,icon = styles.get(rec.get("type","info"), styles["info"])
        st.markdown(
            f"<div style='background:{bg};border-radius:6px;padding:10px 14px;margin:6px 0'>"
            f"<strong style='color:{fg}'>{icon} {rec['title']}</strong><br>"
            f"<span style='color:{fg};font-size:.9rem'>{rec['detail']}</span></div>",
            unsafe_allow_html=True)
    with st.expander("🔍 Texto bruto (OCR)"):
        raw = res.get("raw_text","")
        st.text_area("", raw[:3000], height=200, disabled=True)
        if len(raw)>3000: st.caption(f"Mostrando 3 000 de {len(raw)} caracteres.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Turmas e Alunos
# ─────────────────────────────────────────────────────────────────────────────
def page_turmas():
    st.markdown("## 👥 Turmas e Alunos")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Criar nova turma")
        with st.form("nova_turma"):
            nome = st.text_input("Nome da turma (ex: 8º ano B)")
            escola = st.text_input("Escola (ex: E.E. João da Silva)")
            disc = st.text_input("Disciplina principal (opcional)")
            if st.form_submit_button("Criar turma", use_container_width=True):
                if nome:
                    db.criar_turma(nome, escola, disc)
                    st.success(f"Turma '{nome}' criada!")
                    st.rerun()

    with col2:
        st.markdown("#### Adicionar aluno")
        turmas = db.listar_turmas()
        if turmas:
            with st.form("novo_aluno"):
                turma_names = [f"{t['nome']} — {t['escola']}" for t in turmas]
                turma_sel = st.selectbox("Turma", turma_names)
                nome_aluno = st.text_input("Nome do aluno")
                if st.form_submit_button("Adicionar aluno", use_container_width=True):
                    if nome_aluno:
                        idx = turma_names.index(turma_sel)
                        db.criar_aluno(nome_aluno, turmas[idx]["id"])
                        st.success(f"Aluno '{nome_aluno}' adicionado!")
                        st.rerun()
        else:
            st.info("Crie uma turma primeiro.")

    st.divider()
    st.markdown("#### Turmas cadastradas")
    turmas = db.listar_turmas()
    if not turmas:
        st.info("Nenhuma turma cadastrada ainda.")
        return

    for t in turmas:
        alunos = db.listar_alunos(t["id"])
        provas = db.listar_provas(t["id"])
        with st.expander(f"**{t['nome']}** — {t['escola']}  |  {len(alunos)} alunos  |  {len(provas)} provas"):
            if alunos:
                st.markdown("**Alunos:**")
                for a in alunos:
                    st.text(f"  • {a['nome']}")
            else:
                st.caption("Nenhum aluno cadastrado.")
            if provas:
                st.markdown("**Provas analisadas:**")
                for p in provas:
                    st.text(f"  📄 {p['arquivo_nome']} — {p['serie']} — {p['total_questoes']} questões — {p['criado_em'][:10]}")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Relatório do Professor  (drill-down: turma → área → subárea → bloom → aluno)
# ─────────────────────────────────────────────────────────────────────────────
def page_relatorio():
    st.markdown("## 📊 Relatório do Professor")
    st.divider()

    turmas = db.listar_turmas()
    if not turmas:
        st.info("Nenhuma turma cadastrada. Vá em 'Turmas e Alunos' para começar.")
        return

    turma_names = [f"{t['nome']} — {t['escola']}" for t in turmas]
    c1, c2 = st.columns(2)
    sel_turma = c1.selectbox("Turma", turma_names)
    turma = turmas[turma_names.index(sel_turma)]

    provas = db.listar_provas(turma["id"])
    if not provas:
        st.info("Esta turma ainda não tem provas analisadas.")
        return

    prova_opts = [f"{p['titulo']} — {p['criado_em'][:10]}" for p in provas]
    sel_prova  = c2.selectbox("Prova", prova_opts)
    prova      = provas[prova_opts.index(sel_prova)]
    prova_id   = prova["id"]

    questoes   = db.get_questoes_prova(prova_id)
    rel_turma  = db.relatorio_turma(prova_id)
    drilldown  = db.relatorio_drilldown(prova_id)

    if not questoes:
        st.warning("Prova sem questões registradas.")
        return

    st.divider()

    # ── KPIs ─────────────────────────────────────────────────────────────────
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Questões", prova["total_questoes"])
    m2.metric("Série",    prova["serie"])
    m3.metric("Alunos avaliados", len(rel_turma))
    if rel_turma:
        media = round(sum(r["percentual"] for r in rel_turma) / len(rel_turma))
        cor_media = "normal" if media >= 70 else "inverse"
        m4.metric("Média da turma", f"{media}%", delta_color=cor_media)
    st.divider()

    tab1, tab2, tab3 = st.tabs([
        "🔍 Diagnóstico por Conteúdo",
        "👤 Por Aluno",
        "🏫 Visão Geral da Turma",
    ])
    with tab1: _tab_drilldown(drilldown, turma, prova)
    with tab2: _tab_por_aluno(rel_turma, drilldown)
    with tab3: _tab_visao_turma(rel_turma, questoes)


# ── Tab 1: drill-down área → subárea → bloom → alunos ────────────────────────
def _pct_color(pct: int) -> str:
    if pct >= 70: return "#059669"
    if pct >= 50: return "#D97706"
    return "#DC2626"


def _badge(pct: int) -> str:
    cor = _pct_color(pct)
    return (f"<span style='background:{cor};color:white;padding:2px 8px;"
            f"border-radius:10px;font-size:.85rem;font-weight:600'>{pct}%</span>")


def _tab_drilldown(drilldown: dict, turma: dict, prova: dict):
    st.markdown(
        f"Diagnóstico para **{turma['nome']}** — _{prova['titulo']}_\n\n"
        "Clique em cada nível para abrir o detalhamento. "
        "🔴 = abaixo de 50% · 🟡 = 50–69% · 🟢 = 70%+"
    )
    st.divider()

    if not drilldown:
        st.info("Nenhuma resposta registrada para esta prova ainda.")
        return

    for area, subareas in sorted(drilldown.items()):
        # Calc overall area pct
        area_ok = area_tot = 0
        for sub in subareas.values():
            for bdata in sub["bloom"].values():
                for al in bdata["alunos"]:
                    area_ok  += al["ok"]
                    area_tot += al["total"]
        area_pct = round(area_ok*100/area_tot) if area_tot else 0

        # Area header
        area_icon = "🔴" if area_pct < 50 else ("🟡" if area_pct < 70 else "🟢")
        st.markdown(
            f"<h3 style='margin-bottom:4px'>{area} &nbsp;"
            f"<span style='background:{_pct_color(area_pct)};color:white;padding:3px 10px;"
            f"border-radius:10px;font-size:.85rem;font-weight:600'>{area_pct}%</span></h3>",
            unsafe_allow_html=True,
        )

        for sub_key, sub_data in sorted(subareas.items(), key=lambda x: x[1]["label"]):
            sub_ok = sub_tot = 0
            for bdata in sub_data["bloom"].values():
                for al in bdata["alunos"]:
                    sub_ok  += al["ok"]
                    sub_tot += al["total"]
            sub_pct = round(sub_ok*100/sub_tot) if sub_tot else 0

            icon = "🔴" if sub_pct < 50 else ("🟡" if sub_pct < 70 else "🟢")
            with st.expander(
                f"{icon} {sub_data['label']}  —  {sub_ok}/{sub_tot} acertos ({sub_pct}%)",
                expanded=(sub_pct < 60),
            ):
                st.markdown(_badge(sub_pct), unsafe_allow_html=True)
                for bloom_lvl, bdata in sorted(sub_data["bloom"].items()):
                    bloom_nome = bdata["nome"]
                    bloom_pct  = bdata["pct_turma"]
                    alunos     = bdata["alunos"]
                    b_cor      = BLOOM_COLORS.get(bloom_lvl, "#9CA3AF")

                    st.markdown(
                        f"<div style='border-left:4px solid {b_cor};padding:6px 12px;"
                        f"background:{b_cor}11;border-radius:0 6px 6px 0;margin:6px 0'>"
                        f"<strong style='color:{b_cor}'>Bloom: {bloom_nome}</strong>"
                        f" &nbsp;→&nbsp; média da turma: {_badge(bloom_pct)}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    # Alunos com dificuldade (pct < 60)
                    com_dificuldade = [a for a in alunos if a["pct"] < 60]
                    bem             = [a for a in alunos if a["pct"] >= 70]

                    if com_dificuldade:
                        st.markdown(
                            f"<div style='background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:8px 14px;margin:4px 0'>"
                            f"<b style='color:#991B1B'>🔴 Precisam de atenção — {sub_data['label']} / {bloom_nome}:</b><br>"
                            + "  ".join(
                                f"<span style='color:#B91C1C;font-weight:600'>{a['nome']}</span>"
                                f"<span style='color:#6B7280;font-size:.85rem'> ({a['ok']}/{a['total']})</span>"
                                for a in com_dificuldade
                            )
                            + "</div>",
                            unsafe_allow_html=True,
                        )

                    if bem:
                        st.markdown(
                            f"<div style='background:#ECFDF5;border:1px solid #A7F3D0;border-radius:8px;padding:8px 14px;margin:4px 0'>"
                            f"<b style='color:#065F46'>🟢 Dominam — {sub_data['label']} / {bloom_nome}:</b><br>"
                            + "  ".join(
                                f"<span style='color:#047857;font-weight:600'>{a['nome']}</span>"
                                f"<span style='color:#6B7280;font-size:.85rem'> ({a['ok']}/{a['total']})</span>"
                                for a in bem
                            )
                            + "</div>",
                            unsafe_allow_html=True,
                        )

                    st.markdown("")

        st.divider()


# ── Tab 2: por aluno ──────────────────────────────────────────────────────────
def _tab_por_aluno(rel_turma: list, drilldown: dict):
    if not rel_turma:
        st.info("Nenhum aluno com respostas registradas.")
        return

    ranking = sorted(rel_turma, key=lambda r: r["percentual"], reverse=True)

    for rel in ranking:
        nome = rel["aluno"].get("nome", "Aluno")
        pct  = rel["percentual"]
        cor  = _pct_color(pct)

        with st.expander(
            f"**{nome}** — {rel['acertos']}/{rel['total']} acertos ({pct}%)",
            expanded=False,
        ):
            # Bloom breakdown
            st.markdown("#### Por nível cognitivo")
            cols = st.columns(len(rel["por_bloom"]) or 1)
            for i, (bn, stat) in enumerate(rel["por_bloom"].items()):
                p = round(stat["acertos"]*100/stat["total"]) if stat["total"] else 0
                c = _pct_color(p)
                with cols[i]:
                    st.markdown(
                        f"<div style='text-align:center;background:{c}18;border:1px solid {c}44;"
                        f"border-radius:10px;padding:10px 4px'>"
                        f"<div style='font-size:1.3rem;font-weight:800;color:{c}'>{p}%</div>"
                        f"<div style='font-size:.75rem;color:#374151;font-weight:600'>{bn}</div>"
                        f"<div style='font-size:.75rem;color:#6B7280'>{stat['acertos']}/{stat['total']}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            # Find this aluno's weak spots from drilldown
            st.markdown("#### Pontos críticos por conteúdo")
            encontrou = False
            for area, subareas in drilldown.items():
                for sub_key, sub_data in subareas.items():
                    for bloom_lvl, bdata in sub_data["bloom"].items():
                        for al in bdata["alunos"]:
                            if al["nome"] == nome and al["pct"] < 60 and al["total"] > 0:
                                encontrou = True
                                bloom_cor = BLOOM_COLORS.get(bloom_lvl, "#9CA3AF")
                                st.markdown(
                                    f"<div style='background:#FEF2F2;border-left:4px solid #DC2626;"
                                    f"padding:7px 12px;margin:3px 0;border-radius:0 6px 6px 0'>"
                                    f"🔴 <b style='color:#111827'>{area}</b>"
                                    f"<span style='color:#6B7280'> → {sub_data['label']} → </span>"
                                    f"<span style='color:{bloom_cor};font-weight:600'>{bdata['nome']}</span>"
                                    f"<span style='color:#6B7280;font-size:.85rem'>"
                                    f" &nbsp;({al['ok']}/{al['total']} acertos)</span>"
                                    f"</div>",
                                    unsafe_allow_html=True,
                                )

            if not encontrou:
                st.success("Nenhum ponto crítico identificado nesta prova. Bom desempenho!")

            # Recommendations
            st.markdown("#### Recomendações")
            SUGS = {
                "Lembrar":     "Revisar o conteúdo teórico — flashcards, listas de resumo.",
                "Compreender": "Trabalhar interpretação com leituras variadas e exemplos.",
                "Aplicar":     "Praticar com exercícios contextualizados do cotidiano.",
                "Analisar":    "Propor atividades de comparação e debate estruturado.",
                "Avaliar":     "Estimular argumentação escrita com critérios explícitos.",
                "Criar":       "Criar projetos, produções originais ou resolução aberta.",
            }
            for bn, stat in rel["por_bloom"].items():
                if stat["total"] and stat["acertos"]*100/stat["total"] < 50:
                    st.warning(f"**{bn}:** {SUGS.get(bn,'Reforçar este nível.')}")


# ── Tab 3: visão geral da turma ───────────────────────────────────────────────
def _tab_visao_turma(rel_turma: list, questoes: list):
    if not rel_turma:
        st.info("Sem dados de alunos para esta prova.")
        return

    qs = [{"bloom_level": q["bloom_nivel"], "area_display": q["area_display"]} for q in questoes]
    ca, cb = st.columns(2)
    with ca: st.plotly_chart(create_bloom_chart(qs), use_container_width=True)
    with cb: st.plotly_chart(create_area_chart(qs), use_container_width=True)

    st.markdown("#### Desempenho médio por nível de Bloom")
    bloom_agg: dict = {}
    for rel in rel_turma:
        for bn, stat in rel["por_bloom"].items():
            if bn not in bloom_agg: bloom_agg[bn] = {"ok":0,"total":0}
            bloom_agg[bn]["ok"]    += stat["acertos"]
            bloom_agg[bn]["total"] += stat["total"]

    cols = st.columns(len(bloom_agg) or 1)
    for i,(bn,stat) in enumerate(bloom_agg.items()):
        pct = round(stat["ok"]*100/stat["total"]) if stat["total"] else 0
        cor = _pct_color(pct)
        with cols[i]:
            st.markdown(
                f"<div style='text-align:center;background:{cor}18;border:1px solid {cor}44;"
                f"border-radius:10px;padding:12px 4px'>"
                f"<div style='font-size:1.5rem;font-weight:800;color:{cor}'>{pct}%</div>"
                f"<div style='font-size:.8rem;color:#374151;font-weight:600'>{bn}</div></div>",
                unsafe_allow_html=True)

    st.divider()
    st.markdown("#### Ranking")
    ranking = sorted(rel_turma, key=lambda r: r["percentual"], reverse=True)
    for i, rel in enumerate(ranking):
        nome = rel["aluno"].get("nome","—"); pct = rel["percentual"]
        cor  = _pct_color(pct)
        medal = ["🥇","🥈","🥉"][i] if i < 3 else f"{i+1}."
        st.markdown(
            f"{medal} **{nome}** — "
            f"<span style='color:{cor};font-weight:700'>{pct}%</span> "
            f"({rel['acertos']}/{rel['total']} acertos)",
            unsafe_allow_html=True)


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    page = sidebar()
    if page == "Analisar Prova":
        page_analisar()
    elif page == "Turmas e Alunos":
        page_turmas()
    else:
        page_relatorio()


if __name__ == "__main__":
    main()
