"""
Gerador de relatório pedagógico em PDF.

Recebe os dados já processados (relatório por aluno + árvore taxonômica +
pontos críticos) e monta um PDF multi-página com linguagem acessível ao
professor.

Seções:
  1. Capa e resumo executivo
  2. Classificação dos alunos (pódio + tabela)
  3. Grupos de desempenho (faixas)
  4. Desempenho por conteúdo (árvore + barras)
  5. Pontos críticos por aluno
  6. Recomendações pedagógicas
"""
from datetime import datetime
from typing import Dict, List, Optional

from fpdf import FPDF


# ── Cores ─────────────────────────────────────────────────────────────────────
COR_BOM = (5, 150, 105)
COR_ATENCAO = (217, 119, 6)
COR_CRITICO = (220, 38, 38)
COR_AZUL = (29, 78, 216)
COR_AZUL_CLARO = (239, 246, 255)
COR_CINZA_ESCURO = (55, 65, 81)
COR_CINZA = (107, 114, 128)
COR_CINZA_CLARO = (229, 231, 235)
COR_TITULO = (17, 24, 39)


def _cor_pct(pct):
    if pct >= 70:
        return COR_BOM
    if pct >= 50:
        return COR_ATENCAO
    return COR_CRITICO


def _situacao(pct: int) -> str:
    if pct >= 85:
        return "Excelente"
    if pct >= 70:
        return "Bom"
    if pct >= 50:
        return "Atencao"
    return "Reforco urgente"


_SANITIZE = {
    "—": "-", "–": "-", "→": "->", "←": "<-", "…": "...",
    "🎯": "*", "🥇": "1.", "🥈": "2.", "🥉": "3.",
    "🟢": "[OK]", "🟡": "[!!]", "🔴": "[XX]",
    "✓": "OK", "✅": "OK", "⚠": "!!", "⚠️": "!!",
    "📊": "", "📄": "", "📚": "", "🗺️": "", "👥": "", "🏫": "",
    "​": "", " ": " ",
}


def _safe(text) -> str:
    """Substitui caracteres não-latin-1 por equivalentes ASCII."""
    if text is None:
        return ""
    s = str(text)
    for old, new in _SANITIZE.items():
        s = s.replace(old, new)
    # Remove qualquer char fora do latin-1 que restar
    return s.encode("latin-1", errors="replace").decode("latin-1")


# ── PDF Class ─────────────────────────────────────────────────────────────────
class RelatorioPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.alias_nb_pages()
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(left=15, top=15, right=15)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*COR_CINZA)
        self.cell(
            0, 8,
            f"EduMap  -  Pagina {self.page_no()} de {{nb}}",
            0, 0, "C",
        )

    def titulo(self, text, size=16, cor=None):
        self.set_font("Helvetica", "B", size)
        self.set_text_color(*(cor or COR_TITULO))
        self.multi_cell(0, 8, _safe(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def subtitulo(self, text):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*COR_CINZA)
        self.multi_cell(0, 5, _safe(text).upper(), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def paragrafo(self, text, size=10, bold=False):
        self.set_font("Helvetica", "B" if bold else "", size)
        self.set_text_color(*COR_CINZA_ESCURO)
        self.multi_cell(0, 5, _safe(text), new_x="LMARGIN", new_y="NEXT")

    def barra_progresso(self, pct: int, largura=80, altura=4):
        x, y = self.get_x(), self.get_y()
        # fundo
        self.set_fill_color(*COR_CINZA_CLARO)
        self.rect(x, y, largura, altura, "F")
        # progresso
        self.set_fill_color(*_cor_pct(pct))
        progress_w = max(0.5, largura * (pct / 100))
        self.rect(x, y, progress_w, altura, "F")
        self.set_xy(x + largura + 3, y - 1)

    def caixa_info(self, titulo: str, valor: str, descricao: str = "", cor=None):
        cor = cor or COR_AZUL
        y_inicio = self.get_y()
        self.set_fill_color(*COR_AZUL_CLARO)
        self.set_draw_color(*cor)
        self.rect(15, y_inicio, 180, 22, "DF")
        self.set_xy(20, y_inicio + 3)
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(*cor)
        self.cell(50, 12, _safe(valor), 0, 0)
        self.set_xy(75, y_inicio + 4)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*COR_TITULO)
        self.cell(115, 6, _safe(titulo), 0, 2)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*COR_CINZA)
        if descricao:
            self.set_x(75)
            self.cell(115, 5, _safe(descricao), 0, 0)
        self.set_y(y_inicio + 26)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _flatten_nodes_leaf(arvore: List[Dict]) -> List[Dict]:
    """Retorna só os nós-folha (sem filhos)."""
    out = []
    def walk(nos):
        for n in nos:
            if n.get("filhos"):
                walk(n["filhos"])
            else:
                out.append(n)
    walk(arvore)
    return out


def _flatten_nodes_level(arvore: List[Dict], max_level: int) -> List[Dict]:
    """Retorna nós até um certo nível de profundidade."""
    out = []
    def walk(nos):
        for n in nos:
            if n["nivel"] <= max_level:
                out.append(n)
                if n.get("filhos"):
                    walk(n["filhos"])
    walk(arvore)
    return out


def _gerar_recomendacoes(
    media_geral: int,
    bons: int,
    atencao: int,
    criticos: int,
    total: int,
    piores_nos: List[Dict],
    melhores_nos: List[Dict],
    alunos_criticos: List[Dict],
) -> List[str]:
    recs: List[str] = []

    if total == 0:
        return ["Ainda nao ha dados suficientes para gerar recomendacoes."]

    # Desempenho geral
    if media_geral >= 70:
        recs.append(
            f"A turma esta com bom desempenho geral ({media_geral}%). "
            "Voce pode avancar para o proximo conteudo do plano, mas reforce "
            "os topicos especificos listados abaixo."
        )
    elif media_geral >= 50:
        recs.append(
            f"A turma esta na faixa de atencao ({media_geral}%). "
            "Recomendamos uma aula de revisao antes de avancar, com foco nos "
            "topicos criticos."
        )
    else:
        recs.append(
            f"A turma teve desempenho abaixo do esperado ({media_geral}%). "
            "Sugerimos reforcar o conteudo base antes de seguir — considere "
            "revisar pre-requisitos e aplicar exercicios guiados."
        )

    # Alunos em reforço
    if criticos > 0:
        recs.append(
            f"{criticos} aluno(s) precisa(m) de atencao individual urgente. "
            "Considere monitoria, listas extras ou conversa com os responsaveis."
        )
    if atencao > 0 and criticos == 0:
        recs.append(
            f"{atencao} aluno(s) esta(o) na faixa intermediaria. "
            "Trabalhos em dupla com os alunos de melhor desempenho podem ajudar."
        )

    # Top pontos críticos da turma
    if piores_nos:
        nomes_piores = ", ".join(_safe(p["label"]) for p in piores_nos[:3])
        recs.append(
            f"Dedique uma ou duas aulas extras a estes conteudos: {nomes_piores}. "
            "Sao os topicos onde mais alunos erraram."
        )

    # Pontos fortes (avançar)
    if melhores_nos and media_geral >= 60:
        nomes_bons = ", ".join(_safe(p["label"]) for p in melhores_nos[:2])
        recs.append(
            f"A turma demonstra boa compreensao em: {nomes_bons}. "
            "Esses conteudos podem servir de ponte para os proximos topicos."
        )

    # Alunos com pontos críticos específicos
    destaque = [a for a in alunos_criticos if len(a.get("criticos", [])) >= 2]
    if destaque:
        top_nomes = ", ".join(_safe(a["nome"]) for a in destaque[:3])
        recs.append(
            f"Atencao individual para {top_nomes}: esses alunos tem multiplos "
            "pontos criticos e podem se beneficiar de suporte personalizado."
        )

    return recs


# ── Função principal ──────────────────────────────────────────────────────────
def gerar_pdf_relatorio(
    prova: Dict,
    turma: Optional[Dict],
    alunos_report: List[Dict],
    taxonomia: Dict,
    pontos_criticos: List[Dict],
) -> bytes:
    pdf = RelatorioPDF()
    pdf.add_page()

    # ═══ CABEÇALHO ═══
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*COR_AZUL)
    pdf.cell(0, 10, _safe("EduMap - Relatorio Pedagogico"), 0, 1, "C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*COR_CINZA)
    pdf.cell(0, 5, _safe("Diagnostico de aprendizagem por conteudo"), 0, 1, "C")
    pdf.ln(4)

    # Info da prova
    turma_nome = f"{turma['nome']} - {turma.get('escola', '')}" if turma else "Sem turma"
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*COR_CINZA_ESCURO)
    infos = [
        ("Prova:", prova.get("titulo") or "-"),
        ("Turma:", turma_nome),
        ("Serie:", prova.get("serie") or "-"),
        ("Total de questoes:", str(prova.get("total_questoes") or "-")),
        ("Gerado em:", datetime.now().strftime("%d/%m/%Y %H:%M")),
    ]
    for label, valor in infos:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(35, 5, _safe(label), 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, _safe(valor), 0, 1)
    pdf.ln(4)

    # ═══ RESUMO EXECUTIVO ═══
    total = len(alunos_report)
    if total == 0:
        pdf.subtitulo("RESUMO")
        pdf.paragrafo(
            "Ainda nao ha respostas de alunos lancadas para esta prova. "
            "Lance as respostas no Lancamento para ver o diagnostico."
        )
        return bytes(pdf.output())

    medias = [a["percentual"] for a in alunos_report]
    media_geral = round(sum(medias) / total)
    bons = sum(1 for p in medias if p >= 70)
    atencao = sum(1 for p in medias if 50 <= p < 70)
    criticos_count = sum(1 for p in medias if p < 50)

    pdf.subtitulo("RESUMO EXECUTIVO")
    pdf.caixa_info(
        titulo="Media geral da turma",
        valor=f"{media_geral}%",
        descricao=f"{total} alunos avaliados em {prova.get('total_questoes', '?')} questoes",
        cor=_cor_pct(media_geral),
    )

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*COR_TITULO)
    pdf.cell(0, 6, _safe("Como os alunos se distribuem:"), 0, 1)
    pdf.ln(1)

    for label, qtd, cor in [
        ("Bom desempenho (70% ou mais)", bons, COR_BOM),
        ("Precisa de atencao (50% a 69%)", atencao, COR_ATENCAO),
        ("Reforco urgente (abaixo de 50%)", criticos_count, COR_CRITICO),
    ]:
        pct_faixa = round(qtd * 100 / total) if total else 0
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*cor)
        pdf.cell(10, 6, "|", 0, 0)
        pdf.set_text_color(*COR_CINZA_ESCURO)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(95, 6, _safe(label), 0, 0)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*cor)
        pdf.cell(20, 6, f"{qtd} alunos", 0, 0)
        pdf.set_text_color(*COR_CINZA)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, f"({pct_faixa}% da turma)", 0, 1)
    pdf.ln(4)

    # Top pontos críticos e fortes
    nos_folha = _flatten_nodes_leaf(taxonomia.get("arvore", []))
    nos_folha_validos = [n for n in nos_folha if n["total"] > 0]
    nos_folha_validos.sort(key=lambda n: n["percentual"])
    piores = nos_folha_validos[:3]
    melhores = [n for n in reversed(nos_folha_validos) if n["percentual"] >= 70][:3]

    if piores:
        pdf.subtitulo("TRES PONTOS MAIS CRITICOS")
        for n in piores:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*_cor_pct(n["percentual"]))
            pdf.cell(18, 6, f"{n['percentual']}%", 0, 0)
            pdf.set_text_color(*COR_CINZA_ESCURO)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(
                0, 6,
                _safe(f"{n['label']}  ({n['acertos']}/{n['total']} acertos)"),
                0, 1,
            )
        pdf.ln(2)

    if melhores:
        pdf.subtitulo("ONDE A TURMA VAI BEM")
        for n in melhores:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*_cor_pct(n["percentual"]))
            pdf.cell(18, 6, f"{n['percentual']}%", 0, 0)
            pdf.set_text_color(*COR_CINZA_ESCURO)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(
                0, 6,
                _safe(f"{n['label']}  ({n['acertos']}/{n['total']} acertos)"),
                0, 1,
            )

    # ═══ PÁGINA 2: CLASSIFICAÇÃO DOS ALUNOS ═══
    pdf.add_page()
    pdf.titulo("Classificacao dos alunos")

    alunos_ord = sorted(alunos_report, key=lambda a: -a["percentual"])

    if len(alunos_ord) >= 3:
        pdf.subtitulo("PODIO DA TURMA")
        medalhas = [("1o", COR_AZUL), ("2o", (100, 116, 139)), ("3o", (161, 98, 7))]
        for i, a in enumerate(alunos_ord[:3]):
            pos, cor_pos = medalhas[i]
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(*cor_pos)
            pdf.cell(15, 8, pos, 0, 0)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*COR_TITULO)
            pdf.cell(90, 8, _safe(a["aluno"]["nome"]), 0, 0)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(*_cor_pct(a["percentual"]))
            pdf.cell(25, 8, f"{a['percentual']}%", 0, 0)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*COR_CINZA)
            pdf.cell(0, 8, f"({a['acertos']}/{a['total']})", 0, 1)
        pdf.ln(3)

    pdf.subtitulo("TODOS OS ALUNOS - ORDENADOS POR DESEMPENHO")
    pdf.set_fill_color(243, 244, 246)
    pdf.set_draw_color(*COR_CINZA_CLARO)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*COR_CINZA)
    pdf.cell(10, 7, "#", 1, 0, "C", True)
    pdf.cell(80, 7, "Aluno", 1, 0, "L", True)
    pdf.cell(25, 7, "Acertos", 1, 0, "C", True)
    pdf.cell(20, 7, "%", 1, 0, "C", True)
    pdf.cell(45, 7, "Situacao", 1, 1, "L", True)

    for i, a in enumerate(alunos_ord, 1):
        pct = a["percentual"]
        sit = _situacao(pct)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*COR_CINZA_ESCURO)
        pdf.cell(10, 6, str(i), 1, 0, "C")
        pdf.cell(80, 6, _safe(a["aluno"]["nome"])[:42], 1, 0)
        pdf.cell(25, 6, f"{a['acertos']}/{a['total']}", 1, 0, "C")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_cor_pct(pct))
        pdf.cell(20, 6, f"{pct}%", 1, 0, "C")
        pdf.cell(45, 6, _safe(sit), 1, 1)

    # ═══ PÁGINA 3: GRUPOS DE DESEMPENHO ═══
    pdf.add_page()
    pdf.titulo("Grupos de desempenho")
    pdf.paragrafo(
        "Os alunos sao agrupados em tres faixas para facilitar o planejamento. "
        "Use essas listas para formar duplas, escolher monitores ou direcionar "
        "reforco individualizado.",
        size=9,
    )
    pdf.ln(3)

    grupos = [
        ("ALUNOS COM BOM DESEMPENHO (70% ou mais)",
         [a for a in alunos_ord if a["percentual"] >= 70], COR_BOM,
         "Podem atuar como monitores ou trabalhar em duplas com colegas em reforco."),
        ("ALUNOS EM ATENCAO (50% a 69%)",
         [a for a in alunos_ord if 50 <= a["percentual"] < 70], COR_ATENCAO,
         "Precisam de revisao direcionada nos conteudos criticos da turma."),
        ("ALUNOS EM REFORCO URGENTE (abaixo de 50%)",
         [a for a in alunos_ord if a["percentual"] < 50], COR_CRITICO,
         "Prioridade para acompanhamento individual. Ver detalhes na pagina de pontos criticos."),
    ]

    for titulo, lista, cor, nota in grupos:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*cor)
        pdf.cell(0, 6, _safe(titulo + f"  ({len(lista)})"), 0, 1)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*COR_CINZA)
        pdf.multi_cell(0, 4, _safe(nota), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        if not lista:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*COR_CINZA)
            pdf.cell(0, 5, "  (nenhum aluno nesta faixa)", 0, 1)
        else:
            for a in lista:
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*COR_CINZA_ESCURO)
                pdf.cell(8, 5, "", 0, 0)
                pdf.cell(0, 5, _safe(f"- {a['aluno']['nome']}  -  {a['percentual']}%  ({a['acertos']}/{a['total']})"), 0, 1)
        pdf.ln(3)

    # ═══ PÁGINA 4: DESEMPENHO POR CONTEÚDO ═══
    arvore = taxonomia.get("arvore", [])
    if arvore:
        pdf.add_page()
        pdf.titulo("Desempenho por conteudo")
        pdf.paragrafo(
            "Aqui a turma e avaliada pelos topicos que a prova cobriu. "
            "Barras vermelhas indicam pontos que precisam de reforco.",
            size=9,
        )
        pdf.ln(3)

        def _render_no(no: Dict, depth: int = 0, max_depth: int = 3):
            if depth > max_depth:
                return
            indent = depth * 6
            pdf.set_x(15 + indent)
            pdf.set_font("Helvetica", "B" if depth == 0 else "", 10 if depth <= 1 else 9)
            pdf.set_text_color(*COR_TITULO if depth == 0 else COR_CINZA_ESCURO)
            label_w = 85 - indent
            pdf.cell(label_w, 5, _safe(no["label"])[: 50 - indent * 2], 0, 0)
            pdf.barra_progresso(no["percentual"], largura=50, altura=3.5)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*_cor_pct(no["percentual"]))
            pdf.cell(15, 5, f"{no['percentual']}%", 0, 0)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*COR_CINZA)
            pdf.cell(0, 5, f"({no['acertos']}/{no['total']})", 0, 1)
            for f in no.get("filhos", []):
                _render_no(f, depth + 1, max_depth)
            if depth == 0:
                pdf.ln(2)

        for root in arvore:
            _render_no(root)

    # ═══ PÁGINA 5: PONTOS CRÍTICOS POR ALUNO ═══
    alunos_com_criticos = [a for a in pontos_criticos if a.get("criticos")]
    if alunos_com_criticos:
        pdf.add_page()
        pdf.titulo("Pontos criticos por aluno")
        pdf.paragrafo(
            "Para cada aluno abaixo, listamos os conteudos especificos onde ele "
            "teve pior desempenho. Use esta lista para montar planos de estudo "
            "individuais.",
            size=9,
        )
        pdf.ln(3)

        for a in alunos_com_criticos:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*COR_TITULO)
            pdf.cell(0, 6, _safe(a["nome"]), 0, 1)
            for c in a["criticos"]:
                pdf.set_x(20)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*_cor_pct(c["percentual"]))
                pdf.cell(8, 5, "*", 0, 0)
                pdf.set_text_color(*COR_CINZA_ESCURO)
                pdf.cell(90, 5, _safe(c["label"])[:55], 0, 0)
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(*_cor_pct(c["percentual"]))
                pdf.cell(15, 5, f"{c['percentual']}%", 0, 0)
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(*COR_CINZA)
                pdf.cell(0, 5, f"({c['acertos']}/{c['total']})", 0, 1)
            pdf.ln(2)

    # ═══ PÁGINA 6: RECOMENDAÇÕES ═══
    pdf.add_page()
    pdf.titulo("Recomendacoes pedagogicas")
    pdf.paragrafo(
        "Sugestoes automaticas baseadas nos dados desta prova. Use como ponto "
        "de partida para seu planejamento.",
        size=9,
    )
    pdf.ln(3)

    recs = _gerar_recomendacoes(
        media_geral, bons, atencao, criticos_count, total,
        piores, melhores, alunos_com_criticos,
    )
    for i, rec in enumerate(recs, 1):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*COR_AZUL)
        pdf.cell(10, 6, f"{i}.", 0, 0)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*COR_CINZA_ESCURO)
        pdf.multi_cell(0, 5, _safe(rec), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    return bytes(pdf.output())
