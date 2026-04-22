"""
Gera uma prova de Geografia para testar a classificação taxonômica.

Cada questão é desenhada para bater em um nó ESPECÍFICO da taxonomia.
O nó esperado está comentado ao lado de cada questão.

Uso:
  python scripts/gerar_prova_geografia.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "provas_exemplo" / "prova_geografia.pdf"

try:
    from fpdf import FPDF
except ImportError:
    print("[ERRO] instale fpdf2:  pip install fpdf2")
    sys.exit(1)


QUESTOES = [
    (
        "O relevo caracterizado por grandes elevações de topo plano, formadas "
        "por rochas antigas e desgastadas pela erosão, é chamado de:",
        ["Planície", "Planalto", "Depressão", "Serra", "Montanha"],
        "B",
        "ef2.geografia.geografia_fisica.relevo",
    ),
    (
        "O bioma brasileiro conhecido pela vegetação de árvores baixas, "
        "troncos retorcidos e adaptação à seca, típico do sertão nordestino, é:",
        ["Mata Atlântica", "Pantanal", "Cerrado", "Caatinga", "Pampas"],
        "D",
        "ef2.geografia.geografia_fisica.vegetacao",
    ),
    (
        "Qual é o clima predominante na região equatorial do Brasil, marcado "
        "por altas temperaturas e muita umidade?",
        ["Tropical", "Equatorial", "Semiárido", "Subtropical", "Temperado"],
        "B",
        "ef2.geografia.geografia_fisica.clima",
    ),
    (
        "O movimento da população do campo para as cidades, intensificado no "
        "Brasil a partir dos anos 1960, é conhecido como:",
        ["Imigração", "Emigração", "Êxodo rural", "Nomadismo", "Urbanização"],
        "C",
        "ef2.geografia.geografia_humana.migracao",
    ),
    (
        "A linha imaginária horizontal que divide a Terra em hemisfério norte "
        "e hemisfério sul é chamada de:",
        ["Meridiano de Greenwich", "Linha do Equador", "Trópico de Câncer", "Trópico de Capricórnio", "Círculo Polar"],
        "B",
        "ef2.geografia.cartografia.coordenadas",
    ),
    (
        "Em um mapa, a relação entre a distância real e a distância representada "
        "no papel é chamada de:",
        ["Legenda", "Rosa dos ventos", "Escala", "Projeção", "Coordenada"],
        "C",
        "ef2.geografia.cartografia.escala",
    ),
    (
        "Quais são os estados que compõem a região Sul do Brasil?",
        [
            "Paraná, Santa Catarina e Rio Grande do Sul",
            "São Paulo, Paraná e Santa Catarina",
            "Minas Gerais, Paraná e Rio Grande do Sul",
            "Santa Catarina, Mato Grosso e Paraná",
            "Rio Grande do Sul, Goiás e Paraná",
        ],
        "A",
        "ef2.geografia.brasil.regioes_brasil",
    ),
    (
        "O setor da economia que engloba a indústria e a construção civil é chamado de:",
        ["Setor primário", "Setor secundário", "Setor terciário", "Setor quaternário", "Setor informal"],
        "B",
        "ef2.geografia.geografia_economica.setores_economicos",
    ),
    (
        "O continente que possui o maior número de países e abriga a cordilheira "
        "do Himalaia é:",
        ["Europa", "África", "Ásia", "América", "Oceania"],
        "C",
        "ef2.geografia.mundo.continentes",
    ),
    (
        "A concentração excessiva de pessoas em grandes centros urbanos, "
        "resultando em problemas como trânsito, poluição e falta de moradia, "
        "é consequência direta da:",
        ["Migração interna", "Globalização", "Urbanização acelerada", "Industrialização", "Êxodo rural"],
        "C",
        "ef2.geografia.geografia_humana.urbanizacao",
    ),
    (
        "A bacia hidrográfica formada pelos maiores rios da região Norte do Brasil, "
        "com destaque para o rio Amazonas, é a bacia:",
        ["Do Prata", "Amazônica", "Do São Francisco", "Do Tocantins-Araguaia", "Do Paraná"],
        "B",
        "ef2.geografia.geografia_fisica.hidrografia",
    ),
    (
        "A atividade econômica que ocupa grandes áreas no centro-oeste brasileiro, "
        "com produção de soja, milho e criação de gado, é chamada de:",
        ["Agricultura familiar", "Agronegócio", "Pesca", "Extrativismo", "Indústria pesada"],
        "B",
        "ef2.geografia.geografia_economica.agricultura",
    ),
]


def gerar_prova():
    OUT.parent.mkdir(exist_ok=True)

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Avaliação de Geografia - 8º ano", ln=True, align="C")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 5, "Escola Municipal EduMap - Disciplina: Geografia", ln=True, align="C")
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
