"""
Gera uma prova de Língua Portuguesa para testar a classificação taxonômica.

Cada questão é desenhada para bater em um nó ESPECÍFICO da taxonomia.
O nó esperado está comentado ao lado de cada questão.

Uso:
  python scripts/gerar_prova_portugues.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "provas_exemplo" / "prova_portugues.pdf"

try:
    from fpdf import FPDF
except ImportError:
    print("[ERRO] instale fpdf2:  pip install fpdf2")
    sys.exit(1)


QUESTOES = [
    (
        "Na frase \"O menino correu rapidamente pelo parque\", a palavra "
        "\"rapidamente\" é classificada como:",
        ["Substantivo", "Adjetivo", "Verbo", "Advérbio", "Preposição"],
        "D",
        "ef2.portugues.gramatica.morfologia.adverbio",
    ),
    (
        "A palavra \"feliz\" na frase \"A criança feliz brincava\" é um:",
        ["Substantivo", "Adjetivo", "Verbo", "Advérbio", "Pronome"],
        "B",
        "ef2.portugues.gramatica.morfologia.adjetivo",
    ),
    (
        "Qual das frases abaixo apresenta ERRO de concordância verbal?",
        [
            "Os alunos estudaram muito.",
            "As meninas chegaram cedo.",
            "Faz dois anos que nos conhecemos.",
            "Houveram muitas reclamações.",
            "Ele e eu somos amigos.",
        ],
        "D",
        "ef2.portugues.gramatica.concordancia_verbal",
    ),
    (
        "Na frase \"Seus olhos são duas estrelas que brilham\", há um exemplo de:",
        ["Comparação", "Metáfora", "Metonímia", "Hipérbole", "Antítese"],
        "B",
        "ef2.portugues.semantica.figuras_linguagem",
    ),
    (
        "A palavra \"café\" recebe acento agudo porque é:",
        [
            "Oxítona terminada em A, E ou O",
            "Paroxítona terminada em A, E ou O",
            "Proparoxítona",
            "Monossílabo átono",
            "Palavra terminada em ditongo",
        ],
        "A",
        "ef2.portugues.gramatica.acentuacao",
    ),
    (
        "Na oração \"O professor explicou a matéria aos alunos\", o termo "
        "\"aos alunos\" funciona como:",
        ["Sujeito", "Objeto direto", "Objeto indireto", "Adjunto adnominal", "Predicativo"],
        "C",
        "ef2.portugues.gramatica.sintaxe.complementos",
    ),
    (
        "Qual o antônimo da palavra \"generoso\"?",
        ["Bondoso", "Sovina", "Gentil", "Amigável", "Caridoso"],
        "B",
        "ef2.portugues.semantica.sinonimos_antonimos",
    ),
    (
        "Qual das palavras abaixo está escrita CORRETAMENTE?",
        ["Exceção", "Excessão", "Esseção", "Escessão", "Esseção"],
        "A",
        "ef2.portugues.gramatica.ortografia",
    ),
    (
        "Leia: \"Cheguei cansado; porém, feliz.\" A vírgula e o ponto e vírgula "
        "foram usados corretamente para marcar:",
        [
            "A separação entre orações contraditórias",
            "Uma enumeração",
            "O vocativo",
            "O aposto",
            "A interjeição",
        ],
        "A",
        "ef2.portugues.gramatica.pontuacao",
    ),
    (
        "O texto que apresenta fatos em sequência temporal, com personagens, "
        "narrador e enredo, é chamado de:",
        ["Descritivo", "Dissertativo", "Narrativo", "Instrucional", "Injuntivo"],
        "C",
        "ef2.portugues.producao_textual.narracao",
    ),
    (
        "Leia o trecho: \"O sol nasceu forte naquela manhã. As crianças correram para "
        "o pátio e começaram a brincar.\" A ideia principal do trecho é:",
        [
            "O dia começou ensolarado e as crianças foram brincar.",
            "As crianças não gostavam do sol.",
            "O sol sempre nasce forte.",
            "As crianças moravam perto do pátio.",
            "Não se pode brincar no sol.",
        ],
        "A",
        "ef2.portugues.leitura_interpretacao.ideia_principal",
    ),
    (
        "Na frase \"Espero por você há duas horas\", o verbo \"esperar\" exige "
        "preposição. Esse fenômeno é chamado de:",
        ["Concordância nominal", "Regência verbal", "Concordância verbal", "Crase", "Colocação pronominal"],
        "B",
        "ef2.portugues.gramatica.regencia_verbal",
    ),
]


def gerar_prova():
    OUT.parent.mkdir(exist_ok=True)

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Avaliação de Língua Portuguesa - 8º ano", ln=True, align="C")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 5, "Escola Municipal EduMap - Disciplina: Português", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, "Nome do aluno: _______________________________________   Turma: _______", ln=True)
    pdf.cell(0, 6, "Data: ___/___/______   Nota: _______", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5,
        "Instrucoes: leia cada questao com atencao e marque a alternativa correta.",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", size=11)
    for i, (enunciado, alts, _gab, _no) in enumerate(QUESTOES, 1):
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 5.5, f"{i}. {enunciado}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=11)
        alts_text = "\n".join(f"     ({letra}) {alt}" for letra, alt in zip("ABCDE", alts))
        pdf.multi_cell(0, 5, alts_text, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    pdf.output(str(OUT))

    gab_path = OUT.with_suffix(".gabarito.txt")
    with open(gab_path, "w", encoding="utf-8") as f:
        f.write("Gabarito + nó esperado da taxonomia\n")
        f.write("=" * 60 + "\n")
        for i, (_e, _a, gab, no) in enumerate(QUESTOES, 1):
            f.write(f"{i:2d}. {gab}  →  {no}\n")

    print(f"[OK] Prova salva:    {OUT}")
    print(f"[OK] Gabarito salvo: {gab_path}")


if __name__ == "__main__":
    gerar_prova()
