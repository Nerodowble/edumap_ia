"""
Gera uma prova de Psicologia / Saúde Mental / SUS para testar a classificação
taxonômica no nível Superior.

Cada questão é desenhada para bater em um nó ESPECÍFICO da taxonomia
'psicologia_saude_mental_sus' (etapa 'superior'). O nó esperado está
comentado ao lado de cada questão.

Uso:
  python scripts/gerar_prova_psicologia.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "provas_exemplo" / "prova_psicologia_sus.pdf"

try:
    from fpdf import FPDF
except ImportError:
    print("[ERRO] instale fpdf2:  pip install fpdf2")
    sys.exit(1)


QUESTOES = [
    (
        "De acordo com a teoria psicanalitica desenvolvida por Sigmund Freud, o "
        "inconsciente opera segundo processos especificos. Sobre o inconsciente, "
        "assinale a alternativa correta:",
        [
            "E identico ao pre-consciente e pode ser acessado pela simples vontade.",
            "Contem conteudos recalcados que escapam ao controle da consciencia.",
            "E uma invencao pos-freudiana, sem relevancia na psicanalise classica.",
            "Opera segundo as leis da logica formal, igual ao pensamento consciente.",
            "So existe nos pacientes com transtornos mentais graves.",
        ],
        "B",
        "superior.psicologia_saude_mental_sus.fundamentos.escolas_abordagens.psicanalise.freud",
    ),
    (
        "Na teoria psicanalitica, os mecanismos de defesa sao operacoes do ego "
        "para lidar com conflitos psiquicos. Qual dos mecanismos abaixo consiste "
        "em atribuir a outra pessoa sentimentos ou desejos proprios inaceitaveis?",
        ["Recalque", "Negacao", "Projecao", "Racionalizacao", "Sublimacao"],
        "C",
        "superior.psicologia_saude_mental_sus.fundamentos.escolas_abordagens.psicanalise.mecanismos_defesa",
    ),
    (
        "Skinner desenvolveu o conceito de condicionamento operante, no qual o "
        "comportamento e modelado por suas consequencias. Um reforco positivo "
        "ocorre quando:",
        [
            "Um estimulo aversivo e removido apos o comportamento.",
            "Um estimulo agradavel e adicionado apos o comportamento, aumentando sua frequencia.",
            "O comportamento e simplesmente ignorado ate se extinguir.",
            "Uma punicao e aplicada para reduzir o comportamento.",
            "O organismo responde automaticamente a um estimulo neutro.",
        ],
        "B",
        "superior.psicologia_saude_mental_sus.fundamentos.escolas_abordagens.behaviorismo.skinner",
    ),
    (
        "A Abordagem Centrada na Pessoa, proposta por Carl Rogers, destaca tres "
        "atitudes fundamentais do terapeuta. Quais sao elas?",
        [
            "Interpretacao, neutralidade e abstinencia.",
            "Empatia, aceitacao incondicional e congruencia.",
            "Diretividade, analise e confrontacao.",
            "Observacao, medicao e modelagem.",
            "Hipnose, sugestao e catarse.",
        ],
        "B",
        "superior.psicologia_saude_mental_sus.fundamentos.escolas_abordagens.humanismo.rogers",
    ),
    (
        "Abraham Maslow propos uma hierarquia de necessidades humanas organizada "
        "em uma piramide. Qual necessidade ocupa o topo da piramide de Maslow?",
        [
            "Necessidades fisiologicas (alimentacao, sono).",
            "Necessidades de seguranca.",
            "Necessidades de pertencimento social.",
            "Necessidades de estima.",
            "Necessidade de autorrealizacao.",
        ],
        "E",
        "superior.psicologia_saude_mental_sus.fundamentos.escolas_abordagens.humanismo.maslow",
    ),
    (
        "O DSM-5 e um dos principais manuais classificatorios de transtornos "
        "mentais. Sobre o DSM-5, assinale a alternativa correta:",
        [
            "E publicado pela Organizacao Mundial da Saude.",
            "Adota exclusivamente uma abordagem dimensional de avaliacao.",
            "E o Manual Diagnostico e Estatistico de Transtornos Mentais da Associacao Psiquiatrica Americana.",
            "Foi extinto em favor da CID-11 em 2019.",
            "So pode ser usado por psiquiatras, nao por psicologos.",
        ],
        "C",
        "superior.psicologia_saude_mental_sus.psicopatologia.classificacao.dsm5",
    ),
    (
        "O Transtorno do Deficit de Atencao e Hiperatividade (TDAH) e um "
        "transtorno do neurodesenvolvimento. Sobre o TDAH, e correto afirmar:",
        [
            "So pode ser diagnosticado em adultos.",
            "Caracteriza-se por padrao persistente de desatencao e/ou hiperatividade/impulsividade que interfere no funcionamento.",
            "E sempre causado por ma educacao familiar.",
            "Nao existe tratamento farmacologico eficaz.",
            "E considerado um transtorno psicotico pelo DSM-5.",
        ],
        "B",
        "superior.psicologia_saude_mental_sus.psicopatologia.neurodesenvolvimento.tdah",
    ),
    (
        "O Transtorno Depressivo Maior, segundo o DSM-5, tem como um dos "
        "criterios centrais a presenca de:",
        [
            "Alucinacoes auditivas persistentes.",
            "Humor deprimido e/ou anedonia, com duracao minima de duas semanas.",
            "Episodios de mania alternados com euforia.",
            "Ansiedade excessiva e preocupacao incontrolavel.",
            "Dificuldade em manter relacionamentos interpessoais.",
        ],
        "B",
        "superior.psicologia_saude_mental_sus.psicopatologia.humor.depressao",
    ),
    (
        "O Transtorno Obsessivo-Compulsivo (TOC) caracteriza-se pela presenca de "
        "obsessoes e/ou compulsoes. As compulsoes sao:",
        [
            "Pensamentos intrusivos e indesejados.",
            "Comportamentos ou atos mentais repetitivos que o individuo se sente compelido a realizar para aliviar ansiedade.",
            "Episodios de desrealizacao e despersonalizacao.",
            "Memorias traumaticas involuntarias.",
            "Sintomas somaticos sem causa organica.",
        ],
        "B",
        "superior.psicologia_saude_mental_sus.psicopatologia.ansiedade.toc",
    ),
    (
        "A esquizofrenia e um transtorno psicotico que pode apresentar sintomas "
        "positivos (como delirios e alucinacoes) e sintomas negativos. Um exemplo "
        "de sintoma negativo da esquizofrenia e:",
        [
            "Delirios persecutorios.",
            "Alucinacoes auditivas.",
            "Embotamento afetivo e avolicao.",
            "Pensamento desorganizado.",
            "Agitacao psicomotora.",
        ],
        "C",
        "superior.psicologia_saude_mental_sus.psicopatologia.psicoticos.esquizofrenia",
    ),
    (
        "A Lei 10.216, tambem conhecida como Lei Paulo Delgado, foi promulgada "
        "em 2001 e representa um marco da Reforma Psiquiatrica brasileira. "
        "Essa lei:",
        [
            "Determina o fechamento imediato de todos os hospitais psiquiatricos.",
            "Dispoe sobre a protecao e os direitos das pessoas portadoras de transtornos mentais e redireciona o modelo assistencial.",
            "Cria o Sistema Unico de Saude (SUS).",
            "Regulamenta o uso de medicamentos psiquiatricos controlados.",
            "So se aplica a pacientes em internacao voluntaria.",
        ],
        "B",
        "superior.psicologia_saude_mental_sus.sus_politicas.reforma_psiquiatrica.lei_10216",
    ),
    (
        "Franco Basaglia e considerado referencia mundial na luta antimanicomial. "
        "Sua experiencia em Trieste, na Italia, influenciou a Reforma Psiquiatrica "
        "brasileira. Basaglia defendia:",
        [
            "A expansao dos hospitais psiquiatricos tradicionais.",
            "A desinstitucionalizacao e a criacao de servicos comunitarios em substituicao ao manicomio.",
            "O uso exclusivo de eletroconvulsoterapia como tratamento.",
            "A reclusao dos pacientes psiquiatricos por toda a vida.",
            "A proibicao de qualquer tipo de medicacao psiquiatrica.",
        ],
        "B",
        "superior.psicologia_saude_mental_sus.sus_politicas.reforma_psiquiatrica.basaglia",
    ),
    (
        "Os Centros de Atencao Psicossocial (CAPS) sao organizados em diferentes "
        "modalidades. O CAPS III caracteriza-se por:",
        [
            "Atender apenas criancas e adolescentes.",
            "Funcionar exclusivamente para casos de alcool e outras drogas.",
            "Funcionar 24 horas por dia, com leitos de acolhimento noturno.",
            "Atender em municipios com ate 20 mil habitantes.",
            "Ser uma modalidade de hospital psiquiatrico tradicional.",
        ],
        "C",
        "superior.psicologia_saude_mental_sus.sus_politicas.raps.caps.caps3",
    ),
    (
        "O CAPS AD (Alcool e outras Drogas) e um servico especializado da RAPS "
        "que atende pessoas com problemas decorrentes do uso de substancias "
        "psicoativas. Uma das suas diretrizes fundamentais e:",
        [
            "A abstinencia total e imediata como unica meta possivel.",
            "A estrategia de reducao de danos, que nao exige abstinencia como condicao para o cuidado.",
            "O encaminhamento obrigatorio a comunidades terapeuticas religiosas.",
            "A internacao compulsoria em todos os casos.",
            "O atendimento apenas a usuarios de drogas ilicitas.",
        ],
        "B",
        "superior.psicologia_saude_mental_sus.sus_politicas.raps.caps.caps_ad",
    ),
    (
        "A Rede de Atencao Psicossocial (RAPS) foi instituida pela Portaria "
        "3.088/2011 do Ministerio da Saude e integra o SUS. A RAPS:",
        [
            "Substitui o SUS em questoes de saude mental.",
            "Organiza os servicos de saude mental em rede, com pontos de atencao articulados e base territorial.",
            "E composta apenas pelos CAPS e hospitais psiquiatricos.",
            "Privatizou o atendimento em saude mental no Brasil.",
            "So atende pacientes em regime de internacao integral.",
        ],
        "B",
        "superior.psicologia_saude_mental_sus.sus_politicas.raps",
    ),
    (
        "A Constituicao Federal de 1988 estabeleceu a saude como direito de "
        "todos e dever do Estado. Um dos principios doutrinarios do SUS que "
        "garante que todas as pessoas tenham acesso aos servicos de saude, "
        "independente de condicao social ou economica, e a:",
        ["Descentralizacao", "Hierarquizacao", "Universalidade", "Regionalizacao", "Privatizacao"],
        "C",
        "superior.psicologia_saude_mental_sus.sus_politicas.principios_sus.universalidade",
    ),
    (
        "A Estrategia Saude da Familia (ESF) e a principal porta de entrada "
        "do SUS. Em saude mental, a ESF atua principalmente:",
        [
            "Realizando internacoes psiquiatricas de longa duracao.",
            "Oferecendo atendimento intensivo apenas a casos graves.",
            "Atraves de acoes de promocao, prevencao e cuidado no territorio, com apoio matricial dos CAPS.",
            "Atendendo exclusivamente criancas e adolescentes.",
            "Substituindo completamente o atendimento psiquiatrico especializado.",
        ],
        "C",
        "superior.psicologia_saude_mental_sus.sus_politicas.raps.atencao_basica.esf",
    ),
    (
        "O Codigo de Etica Profissional do Psicologo (CFP) estabelece diretrizes "
        "fundamentais para a pratica. Sobre o sigilo profissional, e correto afirmar:",
        [
            "E absoluto e nunca pode ser quebrado em nenhuma hipotese.",
            "Deve ser preservado, podendo ser limitado apenas para proteger a vida e a saude do proprio ou de terceiros.",
            "Pode ser quebrado sempre que o psicologo julgar conveniente.",
            "Nao se aplica a atendimentos em grupo.",
            "So vale para psicologos clinicos.",
        ],
        "B",
        "superior.psicologia_saude_mental_sus.fundamentos.etica_profissional.sigilo",
    ),
]


def gerar_prova():
    OUT.parent.mkdir(exist_ok=True)

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Avaliacao de Psicologia, Saude Mental e SUS", ln=True, align="C")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 5, "Faculdade EduMap - Curso de Psicologia - Disciplina: Saude Mental e SUS", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, "Nome do aluno: _______________________________________   Turma: _______", ln=True)
    pdf.cell(0, 6, "Data: ___/___/______   Nota: _______", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5,
        "Instrucoes: leia cada questao com atencao e marque a alternativa correta. "
        "A prova cobre fundamentos de Psicologia, psicopatologia e politicas publicas em "
        "saude mental (SUS).",
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
        f.write("Gabarito + no esperado da taxonomia (etapa: superior)\n")
        f.write("=" * 80 + "\n")
        for i, (_e, _a, gab, no) in enumerate(QUESTOES, 1):
            f.write(f"{i:2d}. {gab}  ->  {no}\n")

    print(f"[OK] Prova salva:    {OUT}")
    print(f"[OK] Gabarito salvo: {gab_path}")


if __name__ == "__main__":
    gerar_prova()
