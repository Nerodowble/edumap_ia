"""
Popula o banco de dados com dados ficticios realistas para demonstracao.
Uso: C:\\Users\\willi\\anaconda3\\python.exe scripts/popular_dados_ficticios.py
"""
import json
import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "edumap.db")

# ── Dados ficticios ───────────────────────────────────────────────────────────

TURMAS = [
    {"nome": "6º ano A", "escola": "E.E. Prof. João Mendes", "disciplina": "Ciências"},
    {"nome": "7º ano B", "escola": "E.E. Prof. João Mendes", "disciplina": "História"},
    {"nome": "8º ano C", "escola": "E.M. Novo Horizonte",   "disciplina": "Matemática"},
    {"nome": "9º ano A", "escola": "E.M. Novo Horizonte",   "disciplina": "Português"},
]

ALUNOS_POR_TURMA = {
    "6º ano A": [
        "Ana Beatriz Souza", "Carlos Eduardo Lima", "Fernanda Oliveira",
        "Gabriel Santos", "Isabela Ferreira", "João Pedro Costa",
        "Larissa Alves", "Matheus Rodrigues", "Natalia Pereira", "Rafael Mendes",
    ],
    "7º ano B": [
        "Amanda Cristina Neves", "Bruno Henrique Dias", "Camila Rocha",
        "Diego Martins", "Eduarda Carvalho", "Felipe Araujo",
        "Giovanna Ribeiro", "Henrique Lopes", "Ingrid Nascimento", "Lucas Barbosa",
    ],
    "8º ano C": [
        "Aline Moreira", "Bernardo Castro", "Carolina Pinto",
        "Daniel Freitas", "Elisa Cardoso", "Fabio Vieira",
        "Gabriela Teixeira", "Heitor Monteiro", "Juliana Azevedo", "Kevin Gomes",
    ],
    "9º ano A": [
        "Leticia Borges", "Marcelo Cunha", "Nathalia Farias",
        "Otavio Macedo", "Patricia Melo", "Quirino Batista",
        "Renata Campos", "Sergio Duarte", "Tatiane Esteves", "Vitor Hugo Lima",
    ],
}

PROVAS = [
    {
        "turma": "6º ano A",
        "titulo": "1ª Avaliação Bimestral — Ciências",
        "serie": "6º ano EF",
        "disciplina": "ciencias",
        "arquivo": "prova_6A_ciencias_bim1.pdf",
        "questoes": [
            {"numero": 1, "stem": "Cite os estados físicos da matéria e dê um exemplo de cada.",
             "area_key": "ciencias", "area_display": "Ciências", "subarea_key": "materia_energia", "subarea_label": "Matéria e Energia", "bloom_nivel": 1, "bloom_nome": "Lembrar", "bloom_verbo": "cite"},
            {"numero": 2, "stem": "Descreva o processo de fotossíntese nas plantas verdes.",
             "area_key": "ciencias", "area_display": "Ciências", "subarea_key": "seres_vivos", "subarea_label": "Seres Vivos e Ecologia", "bloom_nivel": 2, "bloom_nome": "Compreender", "bloom_verbo": "descreva"},
            {"numero": 3, "stem": "Defina o que é célula e indique a diferença entre célula animal e vegetal.",
             "area_key": "ciencias", "area_display": "Ciências", "subarea_key": "seres_vivos", "subarea_label": "Seres Vivos e Ecologia", "bloom_nivel": 1, "bloom_nome": "Lembrar", "bloom_verbo": "defina"},
            {"numero": 4, "stem": "Uma planta foi colocada em ambiente sem luz por 7 dias. Explique o que acontece com a fotossíntese.",
             "area_key": "ciencias", "area_display": "Ciências", "subarea_key": "seres_vivos", "subarea_label": "Seres Vivos e Ecologia", "bloom_nivel": 3, "bloom_nome": "Aplicar", "bloom_verbo": "explique"},
            {"numero": 5, "stem": "Analise a cadeia alimentar: grama → coelho → raposa → decompositores.",
             "area_key": "ciencias", "area_display": "Ciências", "subarea_key": "seres_vivos", "subarea_label": "Seres Vivos e Ecologia", "bloom_nivel": 4, "bloom_nome": "Analisar", "bloom_verbo": "analise"},
            {"numero": 6, "stem": "Compare a reprodução sexuada e a reprodução assexuada.",
             "area_key": "ciencias", "area_display": "Ciências", "subarea_key": "seres_vivos", "subarea_label": "Seres Vivos e Ecologia", "bloom_nivel": 4, "bloom_nome": "Analisar", "bloom_verbo": "compare"},
        ],
        "gabarito": ["B", "D", "A", "C", "B", None],  # None = dissertativa
    },
    {
        "turma": "7º ano B",
        "titulo": "2ª Avaliação Bimestral — História",
        "serie": "7º ano EF",
        "disciplina": "historia",
        "arquivo": "prova_7B_historia_bim2.pdf",
        "questoes": [
            {"numero": 1, "stem": "Em que ano ocorreu a chegada dos portugueses ao Brasil?",
             "area_key": "historia", "area_display": "História", "subarea_key": "brasil_colonial", "subarea_label": "Brasil Colonial", "bloom_nivel": 1, "bloom_nome": "Lembrar", "bloom_verbo": "quando foi"},
            {"numero": 2, "stem": "Nomeie os três principais ciclos econômicos do Brasil Colonial.",
             "area_key": "historia", "area_display": "História", "subarea_key": "brasil_colonial", "subarea_label": "Brasil Colonial", "bloom_nivel": 1, "bloom_nome": "Lembrar", "bloom_verbo": "nomeie"},
            {"numero": 3, "stem": "Explique o significado do Pacto Colonial e seu impacto para a colônia.",
             "area_key": "historia", "area_display": "História", "subarea_key": "brasil_colonial", "subarea_label": "Brasil Colonial", "bloom_nivel": 2, "bloom_nome": "Compreender", "bloom_verbo": "explique"},
            {"numero": 4, "stem": "Analise as causas da Inconfidência Mineira e relacione com o Iluminismo.",
             "area_key": "historia", "area_display": "História", "subarea_key": "brasil_colonial", "subarea_label": "Brasil Colonial", "bloom_nivel": 4, "bloom_nome": "Analisar", "bloom_verbo": "analise"},
            {"numero": 5, "stem": "Avalie a importância da escravidão para a economia colonial e seus impactos.",
             "area_key": "historia", "area_display": "História", "subarea_key": "brasil_colonial", "subarea_label": "Brasil Colonial", "bloom_nivel": 5, "bloom_nome": "Avaliar", "bloom_verbo": "avalie"},
        ],
        "gabarito": ["C", "A", None, None, None],
    },
    {
        "turma": "8º ano C",
        "titulo": "1ª Avaliação Bimestral — Matemática",
        "serie": "8º ano EF",
        "disciplina": "matematica",
        "arquivo": "prova_8C_matematica_bim1.pdf",
        "questoes": [
            {"numero": 1, "stem": "Defina o que é uma equação do 1º grau.",
             "area_key": "matematica", "area_display": "Matemática", "subarea_key": "algebra", "subarea_label": "Álgebra", "bloom_nivel": 1, "bloom_nome": "Lembrar", "bloom_verbo": "defina"},
            {"numero": 2, "stem": "Resolva a equação: 3x + 9 = 24",
             "area_key": "matematica", "area_display": "Matemática", "subarea_key": "algebra", "subarea_label": "Álgebra", "bloom_nivel": 3, "bloom_nome": "Aplicar", "bloom_verbo": "resolva"},
            {"numero": 3, "stem": "Calcule a área de um retângulo com base 8m e altura 5m.",
             "area_key": "matematica", "area_display": "Matemática", "subarea_key": "geometria", "subarea_label": "Geometria", "bloom_nivel": 3, "bloom_nome": "Aplicar", "bloom_verbo": "calcule"},
            {"numero": 4, "stem": "Resolva o sistema de equações: x + y = 10 e x - y = 4.",
             "area_key": "matematica", "area_display": "Matemática", "subarea_key": "algebra", "subarea_label": "Álgebra", "bloom_nivel": 3, "bloom_nome": "Aplicar", "bloom_verbo": "resolva"},
            {"numero": 5, "stem": "Analise as equações 2x + 6 = 14 e x + 3 = 7. Que relação existe entre elas?",
             "area_key": "matematica", "area_display": "Matemática", "subarea_key": "algebra", "subarea_label": "Álgebra", "bloom_nivel": 4, "bloom_nome": "Analisar", "bloom_verbo": "analise"},
            {"numero": 6, "stem": "Calcule o custo total e o lucro: 50 caixas a R$12,00 vendidas a R$18,00.",
             "area_key": "matematica", "area_display": "Matemática", "subarea_key": "aritmetica", "subarea_label": "Aritmética e Números", "bloom_nivel": 3, "bloom_nome": "Aplicar", "bloom_verbo": "calcule"},
        ],
        "gabarito": ["B", "A", "C", "D", None, None],
    },
    {
        "turma": "9º ano A",
        "titulo": "3ª Avaliação Bimestral — Português",
        "serie": "9º ano EF",
        "disciplina": "portugues",
        "arquivo": "prova_9A_portugues_bim3.pdf",
        "questoes": [
            {"numero": 1, "stem": "Identifique a oração subordinada substantiva: 'Espero que você venha.'",
             "area_key": "portugues", "area_display": "Português", "subarea_key": "gramatica", "subarea_label": "Gramática", "bloom_nivel": 2, "bloom_nome": "Compreender", "bloom_verbo": "identifique"},
            {"numero": 2, "stem": "Cite três tipos de figuras de linguagem e dê um exemplo de cada.",
             "area_key": "portugues", "area_display": "Português", "subarea_key": "literatura", "subarea_label": "Literatura", "bloom_nivel": 1, "bloom_nome": "Lembrar", "bloom_verbo": "cite"},
            {"numero": 3, "stem": "Interprete o trecho poético e explique as metáforas do autor.",
             "area_key": "portugues", "area_display": "Português", "subarea_key": "interpretacao", "subarea_label": "Interpretação e Leitura", "bloom_nivel": 2, "bloom_nome": "Compreender", "bloom_verbo": "interprete"},
            {"numero": 4, "stem": "Analise o uso da ironia no texto 'O alienista' de Machado de Assis.",
             "area_key": "portugues", "area_display": "Português", "subarea_key": "literatura", "subarea_label": "Literatura", "bloom_nivel": 4, "bloom_nome": "Analisar", "bloom_verbo": "analise"},
            {"numero": 5, "stem": "Avalie a tese central do texto argumentativo e julgue se os argumentos são suficientes.",
             "area_key": "portugues", "area_display": "Português", "subarea_key": "interpretacao", "subarea_label": "Interpretação e Leitura", "bloom_nivel": 5, "bloom_nome": "Avaliar", "bloom_verbo": "avalie"},
            {"numero": 6, "stem": "Redija um parágrafo argumentativo sobre o uso consciente das redes sociais.",
             "area_key": "portugues", "area_display": "Português", "subarea_key": "producao_textual", "subarea_label": "Produção Textual", "bloom_nivel": 6, "bloom_nome": "Criar", "bloom_verbo": "redija"},
        ],
        "gabarito": ["C", "A", None, None, None, None],
    },
]

# Perfis de desempenho: (chance_acerto_bloom_1, 2, 3, 4, 5, 6)
PERFIS = {
    "excelente":  [0.95, 0.90, 0.85, 0.80, 0.75, 0.70],
    "bom":        [0.85, 0.75, 0.70, 0.60, 0.50, 0.40],
    "regular":    [0.70, 0.60, 0.50, 0.40, 0.30, 0.20],
    "dificuldade":[0.50, 0.40, 0.30, 0.20, 0.15, 0.10],
}

ALTERNATIVAS = ["A", "B", "C", "D"]


def conectar():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def limpar_dados_ficticios(con):
    # Remove tudo para começar do zero
    con.executescript("""
        DELETE FROM respostas;
        DELETE FROM questoes;
        DELETE FROM provas;
        DELETE FROM alunos;
        DELETE FROM turmas;
        UPDATE sqlite_sequence SET seq=0 WHERE name IN
            ('turmas','alunos','provas','questoes','respostas');
    """)
    con.commit()
    print("Banco limpo.")


def popular(con):
    random.seed(42)

    turma_ids = {}
    for t in TURMAS:
        cur = con.execute(
            "INSERT INTO turmas (nome, escola, disciplina) VALUES (?,?,?)",
            (t["nome"], t["escola"], t["disciplina"]),
        )
        turma_ids[t["nome"]] = cur.lastrowid
    con.commit()
    print(f"  {len(TURMAS)} turmas criadas.")

    aluno_ids = {}
    total_alunos = 0
    for nome_turma, alunos in ALUNOS_POR_TURMA.items():
        tid = turma_ids[nome_turma]
        aluno_ids[nome_turma] = {}
        perfis_disponiveis = list(PERFIS.keys())
        for i, nome_aluno in enumerate(alunos):
            # Distribui perfis variados na turma
            perfil = perfis_disponiveis[i % len(perfis_disponiveis)]
            cur = con.execute(
                "INSERT INTO alunos (nome, turma_id) VALUES (?,?)", (nome_aluno, tid)
            )
            aluno_ids[nome_turma][nome_aluno] = (cur.lastrowid, perfil)
            total_alunos += 1
    con.commit()
    print(f"  {total_alunos} alunos criados.")

    total_provas = 0
    total_respostas = 0
    for prova_def in PROVAS:
        nome_turma = prova_def["turma"]
        tid = turma_ids[nome_turma]

        # Cria datas variadas nos últimos 3 meses
        dias_atras = random.randint(10, 90)
        data_prova = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d %H:%M:%S")

        cur = con.execute(
            """INSERT INTO provas
               (titulo, turma_id, disciplina, serie, arquivo_nome, ocr_method, total_questoes, criado_em)
               VALUES (?,?,?,?,?,?,?,?)""",
            (prova_def["titulo"], tid, prova_def["disciplina"], prova_def["serie"],
             prova_def["arquivo"], "direct", len(prova_def["questoes"]), data_prova),
        )
        prova_id = cur.lastrowid
        total_provas += 1

        # Insere questões
        questao_ids = {}
        for q in prova_def["questoes"]:
            cur2 = con.execute(
                """INSERT INTO questoes
                   (prova_id, numero, texto, stem, area_key, area_display,
                    subarea_key, subarea_label,
                    bloom_nivel, bloom_nome, bloom_verbo, bncc_codigos)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (prova_id, q["numero"], q["stem"], q["stem"],
                 q["area_key"], q["area_display"],
                 q.get("subarea_key","geral"), q.get("subarea_label","Geral"),
                 q["bloom_nivel"], q["bloom_nome"], q.get("bloom_verbo",""), "[]"),
            )
            questao_ids[q["numero"]] = cur2.lastrowid

        # Gera respostas para cada aluno da turma
        gabarito = prova_def["gabarito"]
        for nome_aluno, (aluno_id, perfil) in aluno_ids[nome_turma].items():
            chances = PERFIS[perfil]
            for i, q in enumerate(prova_def["questoes"]):
                bloom = q["bloom_nivel"]
                chance = chances[bloom - 1] if bloom <= 6 else 0.5
                acertou = random.random() < chance
                gab = gabarito[i]

                if gab is None:
                    # Dissertativa: sem alternativa
                    resposta = None
                    correta = acertou
                else:
                    if acertou:
                        resposta = gab
                    else:
                        erradas = [a for a in ALTERNATIVAS if a != gab]
                        resposta = random.choice(erradas)
                    correta = (resposta == gab)

                con.execute(
                    """INSERT INTO respostas
                       (aluno_id, questao_id, resposta, gabarito, correta)
                       VALUES (?,?,?,?,?)""",
                    (aluno_id, questao_ids[q["numero"]],
                     resposta or "", gab or "", 1 if correta else 0),
                )
                total_respostas += 1

    con.commit()
    print(f"  {total_provas} provas criadas.")
    print(f"  {total_respostas} respostas geradas.")


if __name__ == "__main__":
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # Garante que as tabelas existem
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from database import db as _db  # noqa: triggers init_db()

    con = conectar()
    print("Limpando dados anteriores...")
    limpar_dados_ficticios(con)
    print("Populando dados fictícios...")
    popular(con)
    con.close()

    print("\nConcluido! Dados inseridos:")
    print(f"  4 turmas  |  40 alunos  |  4 provas  |  ~240 respostas")
    print("\nAbra o app e va em 'Relatorio do Professor' para visualizar.")
