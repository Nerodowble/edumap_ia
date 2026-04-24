"""
Gera 3 provas SEPARADAS, uma por matéria: Psicologia, Saúde Mental e SUS.
Cada questão é desenhada para bater em um nó específico da taxonomia.

Uso:
  python scripts/gerar_prova_psicologia.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "provas_exemplo"

try:
    from fpdf import FPDF
except ImportError:
    print("[ERRO] instale fpdf2:  pip install fpdf2")
    sys.exit(1)


# ═══ PROVA 1: PSICOLOGIA ═══════════════════════════════════════════════════════
QUESTOES_PSICOLOGIA = [
    (
        "De acordo com a teoria psicanalitica de Sigmund Freud, o inconsciente:",
        ["E identico ao pre-consciente.", "Contem conteudos recalcados que escapam ao controle da consciencia.",
         "E uma invencao pos-freudiana.", "Opera pelas leis da logica formal.", "So existe em pacientes graves."],
        "B", "superior.psicologia.escolas_abordagens.psicanalise.freud",
    ),
    (
        "Na teoria psicanalitica, atribuir a outra pessoa sentimentos ou desejos proprios inaceitaveis e um mecanismo de defesa chamado:",
        ["Recalque", "Negacao", "Projecao", "Racionalizacao", "Sublimacao"],
        "C", "superior.psicologia.escolas_abordagens.psicanalise.mecanismos_defesa",
    ),
    (
        "Segundo Skinner, no condicionamento operante, o reforco positivo ocorre quando:",
        ["Um estimulo aversivo e removido apos o comportamento.",
         "Um estimulo agradavel e adicionado apos o comportamento, aumentando sua frequencia.",
         "O comportamento e ignorado ate se extinguir.", "Uma punicao e aplicada.", "Ha reflexo condicionado."],
        "B", "superior.psicologia.escolas_abordagens.behaviorismo.skinner",
    ),
    (
        "A Abordagem Centrada na Pessoa, de Carl Rogers, destaca tres atitudes fundamentais do terapeuta:",
        ["Interpretacao, neutralidade e abstinencia.",
         "Empatia, aceitacao incondicional e congruencia.",
         "Diretividade, analise e confrontacao.", "Observacao, medicao e modelagem.",
         "Hipnose, sugestao e catarse."],
        "B", "superior.psicologia.escolas_abordagens.humanismo.rogers",
    ),
    (
        "Qual necessidade ocupa o topo da piramide de Maslow?",
        ["Fisiologicas", "Seguranca", "Pertencimento", "Estima", "Autorrealizacao"],
        "E", "superior.psicologia.escolas_abordagens.humanismo.maslow",
    ),
    (
        "Na teoria de Piaget, a crianca conquista a nocao de conservacao (de quantidade, peso, volume) no estagio:",
        ["Sensorio-motor", "Pre-operatorio", "Operatorio concreto", "Operatorio formal", "Pos-formal"],
        "C", "superior.psicologia.desenvolvimento_humano.piaget.operatorio_concreto",
    ),
    (
        "O conceito de Zona de Desenvolvimento Proximal (ZDP) foi proposto por:",
        ["Piaget", "Freud", "Skinner", "Vigotski", "Watson"],
        "D", "superior.psicologia.escolas_abordagens.sociohistorica.vigotski",
    ),
    (
        "A teoria da aprendizagem social de Albert Bandura destaca:",
        ["Apenas o reforco positivo.", "O papel da modelacao e da autoeficacia na aprendizagem observacional.",
         "O condicionamento classico.", "Os arquetipos do inconsciente coletivo.", "As fases psicossexuais."],
        "B", "superior.psicologia.escolas_abordagens.behaviorismo.bandura",
    ),
    (
        "A psicologia escolar atua principalmente:",
        ["Realizando cirurgias cerebrais.", "Na saude mental de atletas.",
         "Em processos de ensino-aprendizagem, queixas escolares e mediacao pedagogica.",
         "Apenas em perícias judiciais.", "No transito."],
        "C", "superior.psicologia.areas_atuacao.escolar",
    ),
    (
        "Sobre o sigilo profissional do psicologo (Codigo de Etica), e correto afirmar:",
        ["E absoluto e nunca pode ser quebrado.",
         "Deve ser preservado, podendo ser limitado para proteger a vida e a saude proprias ou de terceiros.",
         "Pode ser quebrado sempre que o psicologo julgar conveniente.",
         "Nao se aplica a atendimentos em grupo.", "So vale para psicologos clinicos."],
        "B", "superior.psicologia.etica_profissional.sigilo",
    ),
]

# ═══ PROVA 2: SAÚDE MENTAL ═════════════════════════════════════════════════════
QUESTOES_SAUDE_MENTAL = [
    (
        "O DSM-5 e o Manual Diagnostico e Estatistico de Transtornos Mentais publicado pela:",
        ["OMS", "Ministerio da Saude", "APA - Associacao Psiquiatrica Americana",
         "CFP", "Federacao Brasileira de Psiquiatria"],
        "C", "superior.saude_mental.classificacao.dsm5",
    ),
    (
        "O TDAH caracteriza-se por:",
        ["So pode ser diagnosticado em adultos.",
         "Padrao persistente de desatencao e/ou hiperatividade/impulsividade que interfere no funcionamento.",
         "E sempre causado por ma educacao familiar.", "Nao tem tratamento farmacologico.",
         "E um transtorno psicotico."],
        "B", "superior.saude_mental.neurodesenvolvimento.tdah",
    ),
    (
        "Um dos criterios centrais do Transtorno Depressivo Maior, segundo o DSM-5, e:",
        ["Alucinacoes auditivas persistentes.",
         "Humor deprimido e/ou anedonia, com duracao minima de duas semanas.",
         "Episodios de mania.", "Ansiedade excessiva.", "Dificuldade em relacionamentos."],
        "B", "superior.saude_mental.humor.depressao",
    ),
    (
        "O Transtorno Obsessivo-Compulsivo (TOC) caracteriza-se por obsessoes e/ou compulsoes. As compulsoes sao:",
        ["Pensamentos intrusivos e indesejados.",
         "Comportamentos ou atos mentais repetitivos que o individuo se sente compelido a realizar para aliviar ansiedade.",
         "Episodios de desrealizacao.", "Memorias traumaticas.", "Sintomas somaticos."],
        "B", "superior.saude_mental.ansiedade.toc",
    ),
    (
        "Na esquizofrenia, e um exemplo de sintoma NEGATIVO:",
        ["Delirios persecutorios.", "Alucinacoes auditivas.",
         "Embotamento afetivo e avolicao.", "Pensamento desorganizado.", "Agitacao psicomotora."],
        "C", "superior.saude_mental.psicoticos.esquizofrenia",
    ),
    (
        "O Transtorno de Personalidade Borderline (TPB) tem como caracteristica central:",
        ["Padrao invariavel de estabilidade emocional.",
         "Padrao de instabilidade em relacoes, autoimagem e afetos, com impulsividade marcante.",
         "Total ausencia de empatia.", "Autoconfianca excessiva e grandiosidade.",
         "Alucinacoes visuais."],
        "B", "superior.saude_mental.personalidade.cluster_b.borderline",
    ),
    (
        "O TEA (Transtorno do Espectro Autista) e classificado pelo DSM-5 em tres niveis. O Nivel 3 indica:",
        ["Ausencia de prejuizo funcional.", "Suporte leve.", "Suporte substancial.",
         "Suporte muito substancial (prejuizo grave).", "Autismo suprimido."],
        "D", "superior.saude_mental.neurodesenvolvimento.tea.tea_nivel3",
    ),
    (
        "Sobre os fatores de risco para suicidio, e correto afirmar:",
        ["Sao irrelevantes para a prevencao.",
         "Incluem historia previa de tentativas, transtornos mentais, isolamento social e desesperanca.",
         "So se aplicam a adolescentes.", "Nao envolvem questoes sociais.", "Sao identicos para todos."],
        "B", "superior.saude_mental.suicidio_autolesao.fatores_risco_protecao",
    ),
    (
        "Os antidepressivos da classe dos ISRS (inibidores seletivos da recaptacao de serotonina), como a fluoxetina e a sertralina, atuam principalmente:",
        ["Bloqueando receptores dopaminergicos.",
         "Aumentando a disponibilidade de serotonina na fenda sinaptica.",
         "Reduzindo a acao da acetilcolina.", "Como ansioliticos imediatos.",
         "Como estabilizadores de humor primarios."],
        "B", "superior.saude_mental.psicofarmacologia.antidepressivos",
    ),
    (
        "A entrevista clinica em saude mental tem como objetivo:",
        ["Apenas preencher formularios administrativos.",
         "Coletar historia, observar estado mental e construir vinculo terapeutico para formulacao de caso.",
         "Aplicar exclusivamente testes projetivos.", "Substituir o atendimento em grupo.",
         "Indicar apenas medicacao."],
        "B", "superior.saude_mental.clinica_avaliacao.entrevista_clinica",
    ),
]

# ═══ PROVA 3: SUS ══════════════════════════════════════════════════════════════
QUESTOES_SUS = [
    (
        "A Lei 8.080/1990, conhecida como Lei Organica da Saude:",
        ["Cria o plano de saude suplementar.",
         "Regulamenta, em todo o territorio nacional, as acoes e servicos de saude do SUS.",
         "Extingue o SUS.", "So se aplica a hospitais privados.",
         "Substitui a Constituicao Federal em materia de saude."],
        "B", "superior.sus.historia_sus.lei_8080",
    ),
    (
        "O principio do SUS que garante acesso a saude para TODOS os cidadaos, independentemente de condicao social, e a:",
        ["Descentralizacao", "Hierarquizacao", "Universalidade", "Regionalizacao", "Privatizacao"],
        "C", "superior.sus.principios_sus.universalidade",
    ),
    (
        "A Lei 10.216/2001, tambem conhecida como Lei Paulo Delgado:",
        ["Determina o fechamento imediato de todos os hospitais psiquiatricos.",
         "Dispoe sobre a protecao e os direitos das pessoas com transtornos mentais e redireciona o modelo assistencial.",
         "Cria o SUS.", "Regulamenta medicamentos controlados.",
         "So se aplica a internacao voluntaria."],
        "B", "superior.sus.reforma_psiquiatrica.lei_10216",
    ),
    (
        "Franco Basaglia, referencia mundial na luta antimanicomial, defendia:",
        ["A expansao dos manicomios.",
         "A desinstitucionalizacao e a criacao de servicos comunitarios em substituicao ao manicomio.",
         "O uso exclusivo de eletroconvulsoterapia.", "A reclusao permanente de pacientes.",
         "A proibicao de medicacao psiquiatrica."],
        "B", "superior.sus.reforma_psiquiatrica.basaglia",
    ),
    (
        "O CAPS III diferencia-se dos demais por:",
        ["Atender apenas criancas.", "Atender apenas alcool e drogas.",
         "Funcionar 24 horas por dia, com leitos de acolhimento noturno.",
         "Ser voltado apenas para pequenos municipios.", "Ser um hospital psiquiatrico tradicional."],
        "C", "superior.sus.raps.caps.caps3",
    ),
    (
        "Uma das diretrizes fundamentais do CAPS AD (Alcool e Drogas) e:",
        ["A abstinencia total e imediata como unica meta.",
         "A estrategia de reducao de danos, que nao exige abstinencia como condicao para o cuidado.",
         "O encaminhamento obrigatorio a comunidades terapeuticas.",
         "A internacao compulsoria em todos os casos.", "Atender apenas drogas ilicitas."],
        "B", "superior.sus.raps.caps.caps_ad",
    ),
    (
        "A Rede de Atencao Psicossocial (RAPS), instituida pela Portaria 3.088/2011:",
        ["Substitui o SUS.",
         "Organiza os servicos de saude mental em rede, com pontos de atencao articulados e base territorial.",
         "E composta apenas por CAPS e hospitais psiquiatricos.",
         "Privatizou a saude mental no Brasil.", "So atende internacao integral."],
        "B", "superior.sus.raps",
    ),
    (
        "A Estrategia Saude da Familia (ESF) atua em saude mental principalmente:",
        ["Realizando internacoes de longa duracao.", "Apenas em casos graves.",
         "Atraves de acoes de promocao, prevencao e cuidado no territorio, com apoio matricial dos CAPS.",
         "Atendendo exclusivamente criancas.", "Substituindo o atendimento especializado."],
        "C", "superior.sus.atencao_primaria.esf",
    ),
    (
        "A Politica Nacional de Humanizacao (PNH/HumanizaSUS) tem como um de seus principios:",
        ["Padronizacao rigida dos atendimentos.",
         "Transversalidade, acolhimento, clinica ampliada e gestao participativa.",
         "Hierarquia militarizada.", "Privatizacao das UBS.", "Substituicao do SUS."],
        "B", "superior.sus.humanizacao.pnh",
    ),
    (
        "A estrategia de reducao de danos na politica para alcool e outras drogas:",
        ["Exige abstinencia imediata como pre-requisito para o cuidado.",
         "Prioriza minimizar danos associados ao uso, respeitando o usuario em sua singularidade, sem impor abstinencia.",
         "Proibe qualquer uso medicamentoso.", "E sinonimo de internacao compulsoria.",
         "So se aplica a drogas licitas."],
        "B", "superior.sus.politicas_programas.politica_ad",
    ),
]


def _gerar_pdf(titulo: str, subtitulo: str, questoes: list, out_path: Path):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, titulo, ln=True, align="C")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 5, subtitulo, ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, "Nome do aluno: _______________________________________   Turma: _______", ln=True)
    pdf.cell(0, 6, "Data: ___/___/______   Nota: _______", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5, "Instrucoes: leia cada questao com atencao e marque a alternativa correta.",
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", size=11)
    for i, (enunciado, alts, _gab, _no) in enumerate(questoes, 1):
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 5.5, f"{i}. {enunciado}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=11)
        alts_text = "\n".join(f"     ({letra}) {alt}" for letra, alt in zip("ABCDE", alts))
        pdf.multi_cell(0, 5, alts_text, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    pdf.output(str(out_path))

    gab_path = out_path.with_suffix(".gabarito.txt")
    with open(gab_path, "w", encoding="utf-8") as f:
        f.write(f"Gabarito: {titulo}\n")
        f.write("=" * 80 + "\n")
        for i, (_e, _a, gab, no) in enumerate(questoes, 1):
            f.write(f"{i:2d}. {gab}  ->  {no}\n")

    print(f"[OK] {out_path.name}  +  {gab_path.name}")


def main():
    OUT_DIR.mkdir(exist_ok=True)

    _gerar_pdf(
        "Avaliacao de Psicologia",
        "Faculdade EduMap - Disciplina: Psicologia Geral",
        QUESTOES_PSICOLOGIA,
        OUT_DIR / "prova_psicologia.pdf",
    )
    _gerar_pdf(
        "Avaliacao de Saude Mental",
        "Faculdade EduMap - Disciplina: Psicopatologia e Saude Mental",
        QUESTOES_SAUDE_MENTAL,
        OUT_DIR / "prova_saude_mental.pdf",
    )
    _gerar_pdf(
        "Avaliacao de SUS e Saude Publica",
        "Faculdade EduMap - Disciplina: Politicas Publicas em Saude",
        QUESTOES_SUS,
        OUT_DIR / "prova_sus.pdf",
    )


# Export para o classificador testar
QUESTOES_ALL = {
    "psicologia": QUESTOES_PSICOLOGIA,
    "saude_mental": QUESTOES_SAUDE_MENTAL,
    "sus": QUESTOES_SUS,
}


if __name__ == "__main__":
    main()
