# EduMap IA — Documentação Técnica

**Versão:** 0.1 MVP
**Contexto:** Projeto de extensão universitária
**Tecnologia principal:** Python + Streamlit
**Banco de dados:** SQLite (local, sem servidor)
**IA paga:** nenhuma — classificação 100% por regras e vocabulário

---

## 1. Visão Geral

O **EduMap IA** é uma plataforma web local que permite a professores:

1. Fazer upload de uma prova em PDF ou foto (JPG/PNG)
2. Extrair o texto das questões via OCR
3. Classificar automaticamente cada questão por **área do conhecimento**, **subárea curricular**, **nível da Taxonomia de Bloom** e **habilidade BNCC** provável
4. Registrar as respostas dos alunos e gerar um **relatório diagnóstico** com drill-down hierárquico: Turma → Área → Subárea → Bloom → aluno com dificuldade

O projeto foi pensado para ser usado por professores sem acesso a ferramentas pagas, rodando localmente no próprio computador ou implantado gratuitamente no Streamlit Community Cloud.

---

## 2. Estrutura de Arquivos

```
edumap_ia/
├── app.py                          # Aplicação principal Streamlit (ponto de entrada)
├── requirements.txt                # Dependências Python
├── .streamlit/
│   └── config.toml                 # Configuração do tema visual
├── data/
│   └── edumap.db                   # Banco de dados SQLite (gerado automaticamente)
├── docs/
│   └── documentacao_tecnica.md     # Este arquivo
├── provas_exemplo/
│   └── prova_exemplo_8ano.pdf      # PDF de exemplo gerado pelo script
├── scripts/
│   ├── popular_dados_ficticios.py  # Popula o banco com 4 turmas, 40 alunos e 4 provas
│   └── gerar_prova_exemplo.py      # Gera o PDF de prova de exemplo
└── src/
    ├── classifier/
    │   ├── area_classifier.py      # Classifica a área do conhecimento
    │   ├── bloom_classifier.py     # Classifica o nível de Bloom
    │   ├── bncc_mapper.py          # Mapeia para código BNCC provável
    │   ├── segmenter.py            # Segmenta o texto OCR em questões individuais
    │   └── subarea_classifier.py   # Classifica a subárea curricular
    ├── data/
    │   ├── vocabulario_areas.json  # Vocabulário de palavras-chave por área
    │   ├── verbos_bloom.json       # Verbos cognitivos por nível de Bloom
    │   ├── subareas.json           # Palavras-chave por subárea por área
    │   └── bncc_habilidades.json   # Códigos e descrições BNCC de exemplo
    ├── database/
    │   └── db.py                   # Gerenciador SQLite (CRUD + relatórios)
    ├── ocr/
    │   └── extractor.py            # Pipeline OCR: pdfplumber → PyMuPDF → Tesseract
    └── report/
        ├── charts.py               # Gráficos Plotly (Bloom, Área, Heatmap)
        ├── pdf_exporter.py         # Exportação do relatório em PDF (fpdf2)
        └── recommender.py          # Gerador de recomendações pedagógicas
```

---

## 3. Como Instalar e Executar

### Pré-requisitos

| Dependência | Versão mínima | Observação |
|---|---|---|
| Python | 3.10+ | Anaconda recomendado |
| Tesseract OCR | 5.x | Necessário para fotos/PDFs escaneados |
| Pacotes Python | ver `requirements.txt` | |

### Instalação do Tesseract (Windows)

1. Baixar o instalador em: https://github.com/UB-Mannheim/tesseract/wiki
2. Instalar em `C:\Program Files\Tesseract-OCR\`
3. O `extractor.py` já aponta para esse caminho automaticamente

### Instalação das dependências Python

```bash
pip install -r requirements.txt
```

### Executar a aplicação

```bash
# Com Anaconda
C:\Users\<usuario>\anaconda3\python.exe -m streamlit run app.py

# Ou simplesmente
streamlit run app.py
```

A aplicação abre no navegador em `http://localhost:8501`.

### Popular dados fictícios para demonstração

```bash
C:\Users\<usuario>\anaconda3\python.exe -X utf8 scripts/popular_dados_ficticios.py
```

Cria 4 turmas, 40 alunos e 4 provas com respostas variadas (perfis: excelente, bom, regular, com dificuldade), prontas para demonstrar os relatórios.

---

## 4. Pipeline de Processamento

Ao fazer upload de uma prova, o sistema executa a seguinte sequência:

```
Upload (PDF/JPG/PNG)
        │
        ▼
┌─────────────────────────────────┐
│  OCR — extractor.py             │
│                                 │
│  1. pdfplumber (texto digital)  │
│  2. PyMuPDF   (fallback PDF)    │
│  3. Tesseract (imagem/scan)     │
└─────────────┬───────────────────┘
              │ texto bruto
              ▼
┌─────────────────────────────────┐
│  Segmentação — segmenter.py     │
│  Detecta padrões: "1.", "Q1",   │
│  "Questão 1", etc.              │
│  Separa enunciado e alternativas│
└─────────────┬───────────────────┘
              │ lista de questões
              ▼
┌─────────────────────────────────┐
│  Classificação (por questão)    │
│                                 │
│  area_classifier.py             │
│   → bag-of-words no vocabulário │
│   → retorna área + confiança    │
│                                 │
│  subarea_classifier.py          │
│   → bag-of-words em subareas.json│
│   → retorna subárea da área     │
│                                 │
│  bloom_classifier.py            │
│   → busca verbos cognitivos     │
│   → retorna nível 1-6 + verbo   │
│                                 │
│  bncc_mapper.py                 │
│   → filtra por área + série     │
│   → retorna código(s) BNCC      │
└─────────────┬───────────────────┘
              │ questões classificadas
              ▼
┌─────────────────────────────────┐
│  Banco de Dados — db.py         │
│  Salva: prova + questões        │
│  Vincula à turma selecionada    │
└─────────────────────────────────┘
```

---

## 5. Sistema de Classificação

### 5.1 Áreas do Conhecimento

Cada questão é comparada contra um vocabulário de palavras-chave por área (`vocabulario_areas.json`). O sistema faz pontuação simples: cada palavra encontrada no texto da questão soma pontos (alta frequência = 2 pts, média = 1 pt). A área com maior pontuação é selecionada.

Áreas suportadas: Matemática, Português, Ciências, História, Geografia, Biologia, Física, Química.

### 5.2 Subáreas Curriculares

Dentro de cada área, o texto é comparado contra palavras-chave de subáreas (`subareas.json`). Exemplo para Matemática:

| Subárea | Exemplos de palavras-chave |
|---|---|
| Álgebra | equação, incógnita, polinômio, fatoração |
| Geometria | triângulo, ângulo, área, volume, círculo |
| Estatística e Probabilidade | média, moda, probabilidade, gráfico |
| Aritmética e Números | fração, porcentagem, potência, mmc |
| Trigonometria | seno, cosseno, tangente, radiano |
| Funções e Gráficos | função, domínio, imagem, parábola |

### 5.3 Taxonomia de Bloom (Revisada)

O nível cognitivo é detectado pelos **verbos presentes no enunciado** da questão, usando o dicionário `verbos_bloom.json`.

| Nível | Nome | Cor | Exemplos de verbos |
|---|---|---|---|
| 1 | Lembrar | Azul | identificar, citar, listar, reconhecer, nomear |
| 2 | Compreender | Verde-esmeralda | explicar, descrever, resumir, interpretar, classificar |
| 3 | Aplicar | Âmbar | calcular, resolver, usar, aplicar, demonstrar |
| 4 | Analisar | Laranja | comparar, diferenciar, examinar, investigar, decompor |
| 5 | Avaliar | Vermelho | julgar, criticar, argumentar, justificar, defender |
| 6 | Criar | Violeta | criar, propor, elaborar, formular, projetar |

**O que o Bloom indica:** o *tipo de dificuldade cognitiva*. Se um aluno erra questões de nível 3 (Aplicar) mas acerta as de nível 1 (Lembrar), ele memoriza o conteúdo mas tem dificuldade em aplicá-lo em contexto.

### 5.4 Habilidades BNCC

A BNCC (Base Nacional Comum Curricular) define habilidades codificadas como `EF07MA17` (Ensino Fundamental, 7º ano, Matemática, habilidade 17). O sistema filtra as habilidades por área e série e retorna os códigos mais prováveis. Esta é uma aproximação — o mapeamento preciso requer análise semântica mais profunda.

---

## 6. Banco de Dados

Arquivo SQLite em `data/edumap.db`, criado automaticamente na primeira execução.

### Schema

```sql
turmas (
    id          INTEGER PK AUTOINCREMENT,
    nome        TEXT NOT NULL,
    escola      TEXT,
    disciplina  TEXT,
    criado_em   TEXT
)

alunos (
    id        INTEGER PK AUTOINCREMENT,
    nome      TEXT NOT NULL,
    turma_id  INTEGER → turmas(id) CASCADE DELETE,
    criado_em TEXT
)

provas (
    id             INTEGER PK AUTOINCREMENT,
    titulo         TEXT,
    turma_id       INTEGER → turmas(id),
    disciplina     TEXT,
    serie          TEXT,
    arquivo_nome   TEXT,
    ocr_method     TEXT,    -- 'direct', 'pymupdf' ou 'ocr'
    total_questoes INTEGER,
    criado_em      TEXT
)

questoes (
    id            INTEGER PK AUTOINCREMENT,
    prova_id      INTEGER → provas(id) CASCADE DELETE,
    numero        INTEGER,
    texto         TEXT,     -- texto completo da questão
    stem          TEXT,     -- apenas o enunciado
    area_key      TEXT,     -- ex: 'matematica'
    area_display  TEXT,     -- ex: 'Matemática'
    subarea_key   TEXT,     -- ex: 'algebra'
    subarea_label TEXT,     -- ex: 'Álgebra'
    bloom_nivel   INTEGER,  -- 1-6
    bloom_nome    TEXT,     -- ex: 'Aplicar'
    bloom_verbo   TEXT,     -- verbo detectado
    bncc_codigos  TEXT      -- JSON array: ["EF07MA17", ...]
)

respostas (
    id         INTEGER PK AUTOINCREMENT,
    aluno_id   INTEGER → alunos(id) CASCADE DELETE,
    questao_id INTEGER → questoes(id) CASCADE DELETE,
    resposta   TEXT,        -- letra escolhida pelo aluno
    gabarito   TEXT,        -- letra correta
    correta    INTEGER,     -- 0 ou 1
    criado_em  TEXT,
    UNIQUE(aluno_id, questao_id)
)
```

---

## 7. Relatório Diagnóstico

### Estrutura do Drill-Down

O relatório principal (`page_relatorio()`) apresenta 3 abas:

**Aba 1 — Diagnóstico por Conteúdo**

Hierarquia de 4 níveis, do mais geral ao mais específico:

```
Área (ex: Matemática)  →  72% turma
  └── Subárea (ex: Álgebra)  →  58% turma
        └── Bloom nível (ex: Aplicar)  →  média 55%
              ├── Alunos com dificuldade (<60%): Luizinho (2/5), Maria (1/5)
              └── Alunos que dominam (≥70%): Ana (5/5), João (4/5)
```

Código de cores dos indicadores de desempenho:
- **Verde** (`#059669`) — ≥ 70% (domínio satisfatório)
- **Âmbar** (`#D97706`) — 50–69% (em desenvolvimento)
- **Vermelho** (`#DC2626`) — < 50% (precisa de atenção)

**Aba 2 — Por Aluno**

Ranking individual + breakdown por nível de Bloom + pontos críticos por conteúdo + recomendações pedagógicas automáticas.

**Aba 3 — Visão Geral da Turma**

Gráficos de distribuição por Bloom e por Área + desempenho médio por nível cognitivo + ranking completo.

---

## 8. Tecnologias Utilizadas

| Biblioteca | Versão mínima | Uso |
|---|---|---|
| streamlit | 1.32 | Interface web |
| pdfplumber | 0.10 | Extração de texto de PDFs digitais |
| pymupdf (fitz) | 1.23 | Fallback de extração e renderização de páginas |
| pytesseract | 0.3.10 | OCR via Tesseract (para scans e fotos) |
| Pillow | 10.0 | Processamento de imagens para OCR |
| plotly | 5.18 | Gráficos interativos |
| fpdf2 | 2.7 | Exportação de relatório em PDF |
| pandas | 2.0 | Manipulação de dados nos gráficos |
| sqlite3 | stdlib | Banco de dados local |

---

## 9. Decisões de Projeto

### Por que sem IA paga?

O projeto é voltado a professores de escolas públicas e privadas sem orçamento para APIs. A classificação por vocabulário e verbos atinge precisão suficiente para fins diagnósticos em sala de aula, especialmente quando o professor conhece a prova e pode interpretar os resultados.

O sistema foi desenhado para receber o **Gemini Free API** como upgrade futuro: basta trocar a função `classify_area()` por uma chamada ao modelo, mantendo a mesma interface.

### Por que Streamlit?

- Deploy gratuito em [streamlit.io/cloud](https://streamlit.io/cloud)
- Código Python puro, sem HTML/JS obrigatório
- Ideal para protótipos de ferramentas educacionais

### Por que SQLite?

- Zero configuração — o arquivo `edumap.db` é criado automaticamente
- Portátil — pode ser copiado junto com o projeto
- Suficiente para o volume de dados esperado (dezenas de turmas, centenas de alunos)

---

## 10. Como Fazer Deploy (Streamlit Cloud)

1. Criar repositório no GitHub com todos os arquivos do projeto
2. Acessar [share.streamlit.io](https://share.streamlit.io) e fazer login com GitHub
3. Clicar em **New app** e selecionar o repositório
4. Definir `app.py` como arquivo principal
5. Em **Advanced settings**, adicionar a variável de ambiente se necessário

**Atenção:** O Tesseract OCR não está disponível no Streamlit Cloud por padrão. Para deploy com suporte a OCR de imagens, é necessário adicionar um arquivo `packages.txt` com o conteúdo:

```
tesseract-ocr
tesseract-ocr-por
```

O banco SQLite no Streamlit Cloud é **volátil** (apaga a cada redeploy). Para persistência em produção, substituir por PostgreSQL (ex: Supabase free tier).
