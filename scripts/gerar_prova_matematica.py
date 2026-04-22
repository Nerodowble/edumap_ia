"""
Gera uma prova de Matemática (foco em Geometria) para testar a classificação taxonômica.

Cada questão é desenhada para bater em um nó ESPECÍFICO da taxonomia.
O nó esperado está comentado ao lado de cada questão - útil para validar
o classificador na Fase 3.

Uso:
  python scripts/gerar_prova_matematica.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "provas_exemplo" / "prova_matematica_geometria.pdf"

try:
    from fpdf import FPDF
except ImportError:
    print("[ERRO] instale fpdf2:  pip install fpdf2")
    sys.exit(1)


# (enunciado, [alternativas A-E], gabarito, nó esperado da taxonomia)
QUESTOES = [
    (
        "Um triângulo possui três lados com medidas iguais a 6 cm cada. "
        "Como se classifica esse triângulo quanto aos lados?",
        ["Escaleno", "Isósceles", "Equilátero", "Retângulo", "Obtusângulo"],
        "C",
        "ef2.matematica.geometria.figuras_planas.poligonos.triangulos.equilatero",
    ),
    (
        "Um ângulo mede exatamente 90 graus. Esse ângulo é classificado como:",
        ["Agudo", "Reto", "Obtuso", "Raso", "Côncavo"],
        "B",
        "ef2.matematica.geometria.figuras_planas.angulos.tipos_angulos.reto",
    ),
    (
        "Qual é o perímetro de um quadrado cujo lado mede 7 cm?",
        ["14 cm", "21 cm", "28 cm", "49 cm", "56 cm"],
        "C",
        "ef2.matematica.geometria.perimetro_area.perimetro",
    ),
    (
        "Calcule a área de um retângulo com base 8 cm e altura 5 cm.",
        ["13 cm²", "26 cm²", "40 cm²", "45 cm²", "50 cm²"],
        "C",
        "ef2.matematica.geometria.perimetro_area.area.area_retangulo",
    ),
    (
        "Qual é o volume de um cubo com aresta de 4 cm?",
        ["16 cm³", "32 cm³", "48 cm³", "64 cm³", "128 cm³"],
        "D",
        "ef2.matematica.geometria.volume.volume_cubo",
    ),
    (
        "Um quadrilátero possui os quatro lados de mesma medida, mas seus ângulos "
        "não são retos. Que figura é essa?",
        ["Quadrado", "Retângulo", "Losango", "Trapézio", "Paralelogramo"],
        "C",
        "ef2.matematica.geometria.figuras_planas.poligonos.quadrilateros.losango",
    ),
    (
        "Uma pirâmide possui base quadrada e 4 faces laterais triangulares. "
        "Quantas arestas ela possui?",
        ["4", "6", "8", "10", "12"],
        "C",
        "ef2.matematica.geometria.solidos_geometricos.poliedros.piramides",
    ),
    (
        "Qual sólido geométrico tem duas bases circulares paralelas e uma "
        "superfície lateral curva?",
        ["Esfera", "Cone", "Cilindro", "Prisma", "Pirâmide"],
        "C",
        "ef2.matematica.geometria.solidos_geometricos.corpos_redondos.cilindro",
    ),
    (
        "Em um triângulo retângulo, os catetos medem 3 cm e 4 cm. "
        "Aplicando o Teorema de Pitágoras, qual é a medida da hipotenusa?",
        ["5 cm", "6 cm", "7 cm", "8 cm", "9 cm"],
        "A",
        "ef2.matematica.geometria.figuras_planas.poligonos.triangulos.teorema_pitagoras",
    ),
    (
        "Em uma circunferência, o segmento que liga o centro a qualquer ponto "
        "da circunferência é chamado de:",
        ["Diâmetro", "Corda", "Raio", "Arco", "Setor"],
        "C",
        "ef2.matematica.geometria.figuras_planas.circunferencia_circulo.raio",
    ),
    (
        "Maria comprou um produto que custava R$ 80,00 com 25% de desconto. "
        "Quanto ela pagou?",
        ["R$ 55,00", "R$ 60,00", "R$ 65,00", "R$ 70,00", "R$ 75,00"],
        "B",
        "ef2.matematica.aritmetica.porcentagem",
    ),
    (
        "Resolva a equação do 1º grau: 2x + 6 = 14. Qual é o valor de x?",
        ["2", "3", "4", "5", "6"],
        "C",
        "ef2.matematica.algebra.equacoes_primeiro_grau",
    ),
]


def gerar_prova():
    OUT.parent.mkdir(exist_ok=True)

    pdf = FPDF()
    pdf.add_page()

    # Cabeçalho
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Avaliação de Matemática - 8º ano", ln=True, align="C")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 5, "Escola Municipal EduMap - Disciplina: Matemática - Foco: Geometria", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, "Nome do aluno: _______________________________________   Turma: _______", ln=True)
    pdf.cell(0, 6, "Data: ___/___/______   Nota: _______", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5,
        "Instrucoes: leia cada questao com atencao e marque a alternativa correta. "
        "Sao permitidas consultas apenas ao caderno pessoal. Boa prova!",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(4)

    # Questões
    pdf.set_font("Helvetica", size=11)
    for i, (enunciado, alts, _gab, _no) in enumerate(QUESTOES, 1):
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 5.5, f"{i}. {enunciado}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=11)
        alts_text = "\n".join(f"     ({letra}) {alt}" for letra, alt in zip("ABCDE", alts))
        pdf.multi_cell(0, 5, alts_text, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    pdf.output(str(OUT))

    # Gerar arquivo de gabarito também
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
