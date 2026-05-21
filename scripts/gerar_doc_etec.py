"""
Gera apresentacao tecnica resumida do EduMap em PDF, para envio a docente/
coordenacao da ETEC Juscelino Kubitschek (Centro Paula Souza), solicitando
oportunidade de validacao presencial.

Uso:
  py -3.12 scripts/gerar_doc_etec.py
"""
from datetime import date
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "EduMap_Apresentacao_ETEC.pdf"

AZUL = (29, 78, 216)
CINZA = (90, 90, 90)
PRETO = (30, 30, 30)


def _safe(text: str) -> str:
    """Substitui apenas caracteres fora de latin-1 (Helvetica nao suporta)."""
    return (
        text.replace("—", "-")   # em dash
            .replace("–", "-")   # en dash
            .replace("‘", "'").replace("’", "'")
            .replace("“", '"').replace("”", '"')
            .replace("•", "-")
            .replace("…", "...")
    )


class Doc(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(left=20, top=18, right=20)
        self.alias_nb_pages()

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*CINZA)
        self.cell(0, 6, _safe("EduMap - Plataforma de Diagnóstico Pedagógico"),
                  new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_draw_color(220, 220, 220)
        self.line(20, 26, 190, 26)
        self.ln(6)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*CINZA)
        self.cell(0, 6, _safe(f"Página {self.page_no()} / {{nb}}"),
                  align="C")

    # ── blocos reutilizaveis ────────────────────────────────────────────
    def h1(self, txt: str):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*AZUL)
        self.cell(0, 9, _safe(txt), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*AZUL)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y(), self.l_margin + 30,
                  self.get_y())
        self.ln(4)
        self.set_text_color(*PRETO)
        self.set_line_width(0.2)

    def h2(self, txt: str):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*AZUL)
        self.ln(2)
        self.cell(0, 7, _safe(txt), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*PRETO)
        self.ln(1)

    def p(self, txt: str, size: int = 10):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*PRETO)
        self.multi_cell(0, 5.2, _safe(txt),
                        new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def bullet(self, txt: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*PRETO)
        self.cell(5, 5.2, _safe("-"), new_x="RIGHT", new_y="TOP")
        self.multi_cell(0, 5.2, _safe(txt),
                        new_x="LMARGIN", new_y="NEXT")

    def kv(self, key: str, value: str):
        self.set_font("Helvetica", "B", 10)
        self.cell(38, 6, _safe(key + ":"), new_x="RIGHT", new_y="TOP")
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, _safe(value),
                        new_x="LMARGIN", new_y="NEXT")

    def box(self, titulo: str, linhas: list[str]):
        x0 = self.l_margin
        y0 = self.get_y()
        w = self.w - self.l_margin - self.r_margin
        pad_x, pad_y = 4, 3
        inner_w = w - 2 * pad_x
        line_h_title = 6
        line_h_body = 5.2

        self.set_font("Helvetica", "", 9.5)
        body_h = 0.0
        for ln in linhas:
            out = self.multi_cell(
                inner_w, line_h_body, _safe(ln),
                dry_run=True, output="LINES",
            )
            body_h += line_h_body * max(1, len(out))

        altura = pad_y + line_h_title + 1 + body_h + pad_y

        self.set_fill_color(240, 246, 255)
        self.set_draw_color(*AZUL)
        self.set_line_width(0.3)
        self.rect(x0, y0, w, altura, style="DF")

        self.set_xy(x0 + pad_x, y0 + pad_y)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*AZUL)
        self.cell(inner_w, line_h_title, _safe(titulo),
                  new_x="LMARGIN", new_y="NEXT")

        self.set_text_color(*PRETO)
        self.set_font("Helvetica", "", 9.5)
        for ln in linhas:
            self.set_x(x0 + pad_x)
            self.multi_cell(inner_w, line_h_body, _safe(ln),
                            new_x="LMARGIN", new_y="NEXT")

        self.set_y(y0 + altura + 3)


# ──────────────────────────────────────────────────────────────────────────
def build():
    pdf = Doc()

    # ===== CAPA =====
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*AZUL)
    pdf.cell(0, 14, _safe("EduMap"), new_x="LMARGIN", new_y="NEXT",
             align="C")

    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(*PRETO)
    pdf.cell(0, 8, _safe(
        "Plataforma de diagnóstico pedagógico com OCR e taxonomia BNCC"
    ), new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.ln(18)
    pdf.set_draw_color(*AZUL)
    pdf.set_line_width(0.5)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, _safe("Apresentação técnica resumida"),
             new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*CINZA)
    pdf.cell(0, 6, _safe(
        "ETEC Juscelino Kubitschek - Centro Paula Souza"
    ), new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.ln(60)

    y = pdf.get_y()
    pdf.set_fill_color(245, 248, 252)
    pdf.set_draw_color(220, 230, 240)
    pdf.rect(35, y, 140, 38, style="DF")
    pdf.set_xy(40, y + 4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*PRETO)
    pdf.cell(0, 6, _safe("Identificação"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(40)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5.5, _safe("Autor: Willian Lima"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(40)
    pdf.cell(0, 5.5, _safe("Contato: willianvidallima@outlook.com"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(40)
    pdf.cell(0, 5.5, _safe(
        f"Data: {date.today().strftime('%d/%m/%Y')}"),
        new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(40)
    pdf.cell(0, 5.5, _safe("Versão: 1.0"),
             new_x="LMARGIN", new_y="NEXT")

    # ===== PAGINA 1: Resumo + Problema =====
    pdf.add_page()
    pdf.h1("1. Resumo executivo")
    pdf.p(
        "O EduMap é uma plataforma web que automatiza a correção de provas "
        "objetivas e a análise pedagógica do desempenho de alunos a partir "
        "de fotos de gabaritos tiradas com smartphone. Ele combina visão "
        "computacional (OCR), uma taxonomia hierárquica alinhada à BNCC e "
        "à Taxonomia de Bloom, e relatórios acionáveis por aluno, turma e "
        "habilidade. O objetivo não é substituir o professor, mas devolver "
        "tempo de planejamento pedagógico que hoje é consumido em tarefas "
        "operacionais de correção e tabulação."
    )

    pdf.h1("2. Problema endereçado")
    pdf.bullet(
        "Professores brasileiros aplicam provas com frequência mas raramente "
        "têm tempo de transformar o resultado em diagnóstico por habilidade."
    )
    pdf.bullet(
        "A correção manual de provas de múltipla escolha consome de 5 a 15 "
        "minutos por aluno, multiplicados por turmas de 30+ alunos."
    )
    pdf.bullet(
        "Sistemas comerciais existentes são caros, dependem de gabaritos "
        "proprietários pré-impressos e não oferecem análise por taxonomia."
    )
    pdf.bullet(
        "Faltam ferramentas gratuitas que conectem 'erro em uma questão' "
        "com 'qual habilidade BNCC ainda não foi consolidada'."
    )

    pdf.h1("3. Proposta de valor")
    pdf.box("O que o EduMap entrega", [
        "1) Upload de prova em PDF (foto ou digital) com extração automática "
        "das questões e alternativas.",
        "2) Lançamento de respostas com OCR a partir de foto do gabarito "
        "preenchido pelo aluno (pré-processamento OpenCV: deskew + Otsu + "
        "denoise).",
        "3) Classificação automática de cada questão em uma taxonomia "
        "hierárquica (etapa -> matéria -> tópico -> subtópico -> conceito).",
        "4) Relatórios por aluno (pontos críticos), por turma (mapa de "
        "calor de habilidades) e por conteúdo (drill-down).",
        "5) Exportação em PDF do relatório completo da prova.",
    ])

    # ===== PAGINA 2: Arquitetura =====
    pdf.add_page()
    pdf.h1("4. Arquitetura técnica")

    pdf.h2("4.1. Visão geral")
    pdf.p(
        "Aplicação web 3-tier com separação clara entre frontend SPA, "
        "API REST com regras de negócio e classificador, e banco de dados "
        "relacional. Autenticação por JWT e controle de acesso baseado em "
        "papéis (RBAC) com três níveis: admin_geral, admin_escolar e "
        "professor, garantindo isolamento de dados por instituição."
    )

    pdf.h2("4.2. Stack")
    pdf.kv("Frontend", "Next.js 14 (App Router) + TypeScript + Tailwind CSS")
    pdf.kv("Backend", "Python 3.12 + FastAPI + Pydantic")
    pdf.kv("Banco", "PostgreSQL (produção) / SQLite (desenvolvimento)")
    pdf.kv("OCR", "Tesseract 5 + OpenCV (pré-processamento)")
    pdf.kv("Auth", "JWT (python-jose) + bcrypt")
    pdf.kv("PDF", "fpdf2 (geração de relatórios)")
    pdf.kv("Hospedagem", "Vercel (frontend) + Render (API + DB)")

    pdf.h2("4.3. Fluxo simplificado")
    pdf.box("Pipeline da análise de prova", [
        "1) Professor faz upload do PDF da prova -> extração de texto.",
        "2) Segmentador identifica enunciado, alternativas e tipo "
        "(múltipla escolha / verdadeiro-falso).",
        "3) Classificador casa cada questão a um nó da taxonomia por "
        "matching de palavras-chave hierárquicas com tolerância a plural.",
        "4) Professor envia foto do gabarito do aluno -> OCR detecta as "
        "marcações.",
        "5) Sistema cruza respostas x gabarito x taxonomia e produz o "
        "relatório pedagógico em segundos.",
    ])

    pdf.h2("4.4. Taxonomia")
    pdf.p(
        "Estrutura hierárquica de até 6 níveis (etapa, matéria, tópico, "
        "subtópico, conceito, microconceito). Hoje cobre: Ensino "
        "Fundamental 2 (todas as matérias da BNCC), Ensino Médio e três "
        "matérias do Ensino Superior (Psicologia, Saúde Mental e SUS). "
        "Editável via interface administrativa - cada professor admin pode "
        "ajustar palavras-chave sem precisar de redeploy."
    )

    # ===== PAGINA 3: Funcionalidades + Diferenciais =====
    pdf.add_page()
    pdf.h1("5. Funcionalidades principais")

    pdf.h2("Para o professor")
    pdf.bullet("Cadastro próprio de turmas, alunos e provas.")
    pdf.bullet(
        "Upload de prova em PDF ou foto - extração automática de questões."
    )
    pdf.bullet(
        "Lançamento de respostas por digitação manual ou por foto do "
        "gabarito do aluno (OCR otimizado para fotos de celular)."
    )
    pdf.bullet(
        "Suporte a questões de múltipla escolha (A-E) e verdadeiro/falso."
    )
    pdf.bullet(
        "Relatórios visuais: ranking da turma, alunos em situação "
        "crítica, mapa de habilidades dominadas vs. fragilizadas."
    )
    pdf.bullet("Exportação do relatório completo em PDF.")
    pdf.bullet("Interface mobile-friendly com sidebar colapsável.")

    pdf.h2("Para a coordenação")
    pdf.bullet(
        "Painel administrativo com visão por escola e por professor."
    )
    pdf.bullet(
        "Edição da taxonomia (BNCC) diretamente pela interface - permite "
        "adaptar à realidade da instituição."
    )
    pdf.bullet(
        "Isolamento de dados por escola/professor (LGPD-friendly)."
    )

    pdf.h1("6. Diferenciais")
    pdf.bullet(
        "Gratuito e open-source - não depende de papel especial nem "
        "scanner profissional, basta um smartphone."
    )
    pdf.bullet(
        "Classificação por habilidade BNCC, não apenas nota - o professor "
        "vê QUAL conteúdo precisa retomar."
    )
    pdf.bullet(
        "Pré-processamento de imagem (OpenCV) com correção de inclinação "
        "e binarização Otsu garante OCR robusto mesmo com fotos tortas ou "
        "iluminação irregular."
    )
    pdf.bullet(
        "Arquitetura modular: o classificador taxonômico pode ser "
        "estendido para qualquer curso técnico do Centro Paula Souza."
    )

    pdf.h1("7. Status atual")
    pdf.kv("Maturidade", "MVP em produção, em validação com docentes")
    pdf.kv("Ambiente de demonstração",
           "https://edumap.vercel.app (acesso mediante cadastro)")
    pdf.kv("Código-fonte",
           "github.com/Nerodowble/edumap_ia (backend) e "
           "edumap_frontend (interface)")
    pdf.kv("Documentação",
           "docs/ - arquitetura, API, fluxo do professor, taxonomia")

    # ===== PAGINA 4: Solicitacao + Contato =====
    pdf.add_page()
    pdf.h1("8. Aplicação a cursos técnicos do CPS")
    pdf.p(
        "Embora a versão atual do EduMap parta da BNCC do ensino "
        "fundamental e médio, a taxonomia foi modelada de forma agnóstica "
        "e já inclui exemplos de Ensino Superior. Para cursos técnicos do "
        "Centro Paula Souza (ex.: Desenvolvimento de Sistemas, "
        "Administração, Logística, Enfermagem), basta cadastrar a "
        "estrutura curricular do PPC respectivo na área administrativa "
        "para que a classificação automática passe a operar sobre as "
        "competências do curso."
    )
    pdf.p(
        "Casos de uso imediatos identificados na ETEC: avaliações "
        "diagnósticas no início do semestre, simulados preparatórios para "
        "o Vestibulinho e para o Enem, e acompanhamento longitudinal das "
        "competências por turma ao longo do módulo."
    )

    pdf.h1("9. Solicitação")
    pdf.p(
        "Solicito a apreciação desta documentação pela coordenação "
        "pedagógica da ETEC Juscelino Kubitschek com a finalidade de "
        "avaliar a possibilidade de:"
    )
    pdf.bullet(
        "Apresentação técnica presencial (30 a 45 minutos) com demonstração "
        "ao vivo da ferramenta."
    )
    pdf.bullet(
        "Piloto controlado em uma turma e uma disciplina, sem custo, com "
        "acompanhamento de feedback estruturado."
    )
    pdf.bullet(
        "Inclusão do EduMap como objeto de estudo/extensão em uma "
        "disciplina de tecnologia, se for de interesse do curso."
    )
    pdf.p(
        "Comprometo-me com o sigilo das informações pedagógicas eventualmente "
        "utilizadas em piloto e com a aderência à Lei Geral de Proteção de "
        "Dados (LGPD) - todo dado de aluno é armazenado em base isolada "
        "por professor."
    )

    pdf.h1("10. Contato")
    pdf.kv("Responsável", "Willian Lima")
    pdf.kv("E-mail", "willianvidallima@outlook.com")
    pdf.kv("Repositório backend", "github.com/Nerodowble/edumap_ia")
    pdf.kv("Repositório frontend", "github.com/Nerodowble/edumap_frontend")
    pdf.kv("Disponibilidade", "Apresentação presencial mediante agenda")

    pdf.ln(6)
    pdf.h1("11. Aviso importante - estado do projeto")
    pdf.box("MVP em desenvolvimento ativo", [
        "O EduMap encontra-se atualmente em estágio de MVP (Minimum Viable "
        "Product), em desenvolvimento contínuo e sujeito a ajustes "
        "frequentes de funcionalidade, interface e desempenho.",
        "O propósito desta apresentação NÃO é oferecer um produto final "
        "acabado, mas sim expor o conceito, a arquitetura técnica e os "
        "resultados preliminares para fins de avaliação, feedback e "
        "validação institucional.",
        "Pequenas instabilidades, ausência de funcionalidades secundárias "
        "e refinamentos de UX/UI ainda em curso são esperados nesta fase.",
        "Eventual piloto na ETEC Juscelino Kubitschek terá caráter "
        "experimental, e qualquer feedback recebido será incorporado ao "
        "roadmap do produto antes de uma versão estabilizada.",
        "O autor compromete-se a comunicar previamente qualquer mudança "
        "significativa que afete o uso da ferramenta durante uma fase de "
        "testes acordada com a coordenação.",
    ])

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*CINZA)
    pdf.multi_cell(0, 5, _safe(
        "Documento gerado automaticamente a partir do código-fonte do "
        f"projeto EduMap em {date.today().strftime('%d/%m/%Y')}. Versão 1.0 "
        "- MVP em desenvolvimento."
    ), new_x="LMARGIN", new_y="NEXT", align="C")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    build()
