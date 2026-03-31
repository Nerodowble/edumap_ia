"""
Gera uma prova de exemplo realista em PDF para testar o EduMap IA.
Uso: C:\\Users\\willi\\anaconda3\\python.exe scripts/gerar_prova_exemplo.py
Saida: provas_exemplo/prova_exemplo_8ano.pdf
"""
import os
import sys

try:
    from fpdf import FPDF
except ImportError:
    print("fpdf2 nao encontrado. Execute: pip install fpdf2")
    sys.exit(1)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "provas_exemplo")
os.makedirs(OUTPUT_DIR, exist_ok=True)

QUESTOES = [
    {
        "secao": "MATEMATICA",
        "itens": [
            {
                "num": 1,
                "enunciado": "Defina o que e uma equacao do 1 grau e escreva um exemplo.",
                "alts": [],
                "linhas": 3,
            },
            {
                "num": 2,
                "enunciado": "Resolva a equacao abaixo e encontre o valor de x:\n   3x - 9 = 15",
                "alts": ["A) x = 6", "B) x = 7", "C) x = 8", "D) x = 9"],
                "linhas": 0,
            },
            {
                "num": 3,
                "enunciado": "Calcule a area do retangulo com base 12 cm e altura 5 cm.",
                "alts": ["A) 17 cm", "B) 34 cm", "C) 60 cm2", "D) 120 cm2"],
                "linhas": 0,
            },
            {
                "num": 4,
                "enunciado": (
                    "Analise as duas equacoes e compare os resultados:\n"
                    "   Equacao 1: 2x + 4 = 10\n"
                    "   Equacao 2: x + 2 = 5\n"
                    "O que voce observa? Explique a relacao entre elas."
                ),
                "alts": [],
                "linhas": 4,
            },
        ],
    },
    {
        "secao": "LINGUA PORTUGUESA",
        "itens": [
            {
                "num": 5,
                "enunciado": "Qual das alternativas apresenta um substantivo proprio?",
                "alts": ["A) cidade", "B) rio", "C) Brasilia", "D) montanha"],
                "linhas": 0,
            },
            {
                "num": 6,
                "enunciado": (
                    "Leia o trecho e explique, em suas proprias palavras, a ideia principal:\n\n"
                    "\"A leitura e uma das ferramentas mais poderosas para o desenvolvimento humano. "
                    "Por meio dela, o individuo amplia seu vocabulario e exercita o raciocinio critico.\""
                ),
                "alts": [],
                "linhas": 3,
            },
            {
                "num": 7,
                "enunciado": (
                    "Avalie e justifique se a frase esta correta do ponto de vista da concordancia verbal:\n\n"
                    "\"Os alunos foi ao laboratorio de ciencias ontem.\""
                ),
                "alts": [],
                "linhas": 4,
            },
        ],
    },
    {
        "secao": "CIENCIAS",
        "itens": [
            {
                "num": 8,
                "enunciado": "Assinale a alternativa que define corretamente fotossintese:",
                "alts": [
                    "A) Processo pelo qual as plantas absorvem agua pelas raizes",
                    "B) Processo pelo qual as plantas produzem energia a partir da luz solar e CO2",
                    "C) Processo de reproducao das plantas por sementes",
                    "D) Processo de decomposicao da materia organica",
                ],
                "linhas": 0,
            },
            {
                "num": 9,
                "enunciado": (
                    "Uma planta foi colocada em um armario escuro por 10 dias. "
                    "Descreva o que acontecera com a fotossintese e o desenvolvimento da planta."
                ),
                "alts": [],
                "linhas": 4,
            },
        ],
    },
    {
        "secao": "HISTORIA",
        "itens": [
            {
                "num": 10,
                "enunciado": "Em que ano foi proclamada a Republica do Brasil?",
                "alts": ["A) 1822", "B) 1850", "C) 1889", "D) 1930"],
                "linhas": 0,
            },
            {
                "num": 11,
                "enunciado": (
                    "Analise as principais causas que levaram a Proclamacao da Republica no Brasil "
                    "em 1889. Considere aspectos politicos, economicos e sociais do periodo."
                ),
                "alts": [],
                "linhas": 5,
            },
            {
                "num": 12,
                "enunciado": (
                    "Avalie a importancia da abolicao da escravatura (1888) para a Proclamacao da "
                    "Republica. Voce concorda que esses eventos estao relacionados? "
                    "Justifique com argumentos historicos."
                ),
                "alts": [],
                "linhas": 5,
            },
        ],
    },
]


def build_pdf() -> FPDF:
    class Prova(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 13)
            self.cell(0, 8, "ESCOLA ESTADUAL EXEMPLO", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "", 10)
            self.cell(0, 6, "Avaliacao Bimestral  -  8 ano do Ensino Fundamental", align="C", new_x="LMARGIN", new_y="NEXT")
            self.cell(0, 6, "Disciplinas: Matematica | Portugues | Ciencias | Historia", align="C", new_x="LMARGIN", new_y="NEXT")
            self.ln(2)
            self.set_draw_color(100, 100, 100)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(4)

        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 8, f"Pagina {self.page_no()}  |  Boa prova!", align="C")

    pdf = Prova()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Cabecalho aluno
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(110, 7, "Nome: ____________________________________________", border="B")
    pdf.cell(10, 7, "")
    pdf.cell(70, 7, "Turma: __________  Data: __________", border="B")
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 5, "Instrucoes: Leia com atencao. Nas questoes dissertativas, justifique sua resposta.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for secao in QUESTOES:
        # Section bar
        pdf.set_fill_color(44, 62, 80)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, f"  {secao['secao']}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

        for item in secao["itens"]:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(8, 6, f"{item['num']}.")
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, item["enunciado"])

            for alt in item["alts"]:
                pdf.cell(10, 6, "")
                pdf.cell(0, 6, alt, new_x="LMARGIN", new_y="NEXT")

            for _ in range(item["linhas"]):
                pdf.cell(0, 8, "", border="B", new_x="LMARGIN", new_y="NEXT")

            pdf.ln(5)

    return pdf


if __name__ == "__main__":
    pdf = build_pdf()
    out = os.path.join(OUTPUT_DIR, "prova_exemplo_8ano.pdf")
    pdf.output(out)
    print(f"Prova gerada: {out}")
