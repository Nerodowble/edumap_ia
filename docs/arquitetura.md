# EduMap IA — Arquitetura do Sistema

---

## 1. Visão Geral

O EduMap IA é composto por dois serviços independentes que se comunicam via HTTP:

```
┌─────────────────────────────────────────────────────┐
│                  Navegador do Professor              │
│              http://localhost:3000                   │
│                                                     │
│   ┌──────────────────────────────────────────────┐  │
│   │          Frontend (Next.js 14 + React)        │  │
│   │  /analisar  /turmas  /lancar  /relatorio      │  │
│   └────────────────────┬─────────────────────────┘  │
└────────────────────────│────────────────────────────┘
                         │ HTTP REST (JSON)
                         ▼
┌────────────────────────────────────────────────────┐
│           Backend (FastAPI — Python 3.x)            │
│              http://localhost:8000                   │
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │   OCR /      │  │ Classificação│  │  Banco    │  │
│  │  Extração    │  │  (regras)    │  │  SQLite   │  │
│  │  de Texto    │  │              │  │           │  │
│  └─────────────┘  └──────────────┘  └───────────┘  │
└────────────────────────────────────────────────────┘
```

**Princípio:** nenhuma chamada a API externa ou modelo de linguagem pago. Todo processamento (OCR, classificação) é local.

---

## 2. Backend (FastAPI)

### 2.1 Entrypoint

**Arquivo:** `api.py`  
**Inicia com:** `uvicorn api:app --reload`

O arquivo `api.py` define todos os endpoints REST e orquestra a chamada aos módulos em `src/`.

### 2.2 Módulo OCR (`src/ocr/extractor.py`)

Responsável por extrair texto bruto de arquivos PDF ou imagem.

**Estratégia em cascata:**
1. Tenta extração direta (texto embutido no PDF via `pdfplumber`)
2. Se o texto extraído for curto (< 50 caracteres), considera PDF digitalizado e aplica OCR via `PyMuPDF` + `Tesseract`
3. Para imagens (JPG, PNG), aplica OCR diretamente via `Pillow` + `Tesseract`

**Retorna:** `(texto: str, método: str)` — método pode ser `"digital"` ou `"ocr"`

**Dependência do sistema:** Tesseract OCR instalado em `C:\Program Files\Tesseract-OCR\tesseract.exe`

### 2.3 Módulo Segmentação (`src/classifier/segmenter.py`)

Divide o texto bruto em questões individuais.

**Padrões reconhecidos:**
```
1. Texto da questão       → número seguido de ponto
1) Texto                  → número seguido de parêntese
Questão 1                 → padrão por extenso
Q1. Texto                 → abreviado
(1) Texto                 → número entre parênteses
```

**Processo:**
1. Varre o texto linha a linha
2. Ao detectar um marcador de questão, fecha o bloco anterior e abre um novo
3. Separa o enunciado (stem) das alternativas (A–E)
4. Re-numera questões com número inválido sequencialmente
5. Remove blocos vazios

**Retorna:** lista de dicts `{number, text, stem, alternatives}`

### 2.4 Classificação de Área (`src/classifier/area_classifier.py`)

Identifica a disciplina de cada questão usando vocabulário ponderado.

**Áreas suportadas:**  
`matematica`, `portugues`, `historia`, `geografia`, `ciencias`, `biologia`, `quimica`, `fisica`, `ingles`, `artes`, `ed_fisica`

**Algoritmo:**
- Carrega `src/data/vocabulario_areas.json` (palavras de alta/média relevância por área)
- Palavras de alta relevância: +2 pontos | média: +1 ponto
- Área vencedora: maior pontuação total
- Confiança: `score_vencedor / score_total`

### 2.5 Classificação de Bloom (`src/classifier/bloom_classifier.py`)

Detecta o nível cognitivo da Taxonomia de Bloom revisada.

**Níveis (1–6):**
| Nível | Nome | Exemplo de verbos |
|---|---|---|
| 1 | Lembrar | memorize, liste, identifique |
| 2 | Compreender | explique, descreva, interprete |
| 3 | Aplicar | calcule, resolva, use |
| 4 | Analisar | compare, diferencie, examine |
| 5 | Avaliar | julgue, argumente, critique |
| 6 | Criar | elabore, proponha, crie |

**Algoritmo:** percorre os níveis de 6 a 1 (prioriza os mais complexos), procura verbos do `verbos_bloom.json` no texto. Se nenhum verbo for encontrado, retorna nível 2 (Compreender) como padrão.

### 2.6 Classificação de Subárea (`src/classifier/subarea_classifier.py`)

Refina a área em subáreas curriculares específicas.

Exemplos: dentro de `matematica` → `algebra`, `geometria`, `estatistica`, `aritmetica`.  
Usa `src/data/subareas.json` com palavras-chave por subárea.

### 2.7 Mapeamento BNCC (`src/classifier/bncc_mapper.py`)

Sugere habilidades BNCC prováveis com base em área + série + nível de Bloom.

Dados em `src/data/bncc_habilidades.json`. O mapeamento é aproximado (heurístico), não usa o texto da questão.

---

## 3. Banco de Dados (SQLite)

**Arquivo:** `data/edumap.db` (criado automaticamente ao iniciar a API)

### Esquema

```sql
-- Turmas de alunos
CREATE TABLE turmas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    escola      TEXT,
    disciplina  TEXT,
    criado_em   TEXT DEFAULT (datetime('now','localtime'))
);

-- Alunos vinculados a uma turma
CREATE TABLE alunos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT NOT NULL,
    turma_id  INTEGER REFERENCES turmas(id) ON DELETE CASCADE,
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);

-- Provas analisadas
CREATE TABLE provas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo         TEXT,
    turma_id       INTEGER REFERENCES turmas(id) ON DELETE SET NULL,
    disciplina     TEXT,
    serie          TEXT,
    arquivo_nome   TEXT,
    ocr_method     TEXT,          -- "digital" ou "ocr"
    total_questoes INTEGER,
    criado_em      TEXT DEFAULT (datetime('now','localtime'))
);

-- Questões de cada prova (com classificações)
CREATE TABLE questoes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    prova_id      INTEGER NOT NULL REFERENCES provas(id) ON DELETE CASCADE,
    numero        INTEGER,
    texto         TEXT,
    stem          TEXT,
    area_key      TEXT,           -- ex: "matematica"
    area_display  TEXT,           -- ex: "Matemática"
    subarea_key   TEXT,
    subarea_label TEXT,
    bloom_nivel   INTEGER,        -- 1 a 6
    bloom_nome    TEXT,
    bloom_verbo   TEXT,
    bncc_codigos  TEXT            -- JSON array de strings
);

-- Gabarito da prova (alternativa correta por número de questão)
CREATE TABLE gabarito (
    prova_id        INTEGER NOT NULL REFERENCES provas(id) ON DELETE CASCADE,
    numero_questao  INTEGER NOT NULL,
    alternativa     TEXT NOT NULL,
    PRIMARY KEY(prova_id, numero_questao)
);

-- Respostas dos alunos
CREATE TABLE respostas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id    INTEGER NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    questao_id  INTEGER NOT NULL REFERENCES questoes(id) ON DELETE CASCADE,
    resposta    TEXT,             -- alternativa escolhida pelo aluno
    gabarito    TEXT,             -- gabarito no momento do lançamento
    correta     INTEGER DEFAULT 0, -- 0 ou 1
    criado_em   TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(aluno_id, questao_id)  -- ON CONFLICT DO UPDATE (idempotente)
);
```

### Relacionamentos

```
turmas ──< alunos
turmas ──< provas (ON DELETE SET NULL)
provas ──< questoes (ON DELETE CASCADE)
provas ──< gabarito (ON DELETE CASCADE)
alunos ──< respostas (ON DELETE CASCADE)
questoes ──< respostas (ON DELETE CASCADE)
```

### Camada de Acesso (`src/database/db.py`)

Todas as operações de banco são feitas via funções puras neste módulo. Usa `sqlite3` nativo do Python com `row_factory = sqlite3.Row` para retornar dicionários.

Funções principais:

| Função | Descrição |
|---|---|
| `criar_turma()` | Insere nova turma |
| `listar_turmas()` | Lista todas as turmas |
| `criar_aluno()` | Insere aluno em uma turma |
| `salvar_prova()` | Insere prova + questões classificadas |
| `salvar_gabarito()` | Salva/atualiza gabarito (DELETE + INSERT) |
| `get_gabarito()` | Retorna gabarito como `{numero: alternativa}` |
| `lancar_respostas_aluno()` | Registra respostas comparando com gabarito |
| `relatorio_turma()` | Retorna desempenho de todos os alunos da prova |
| `relatorio_drilldown()` | Retorna árvore área→subárea→bloom→aluno |

---

## 4. Frontend (Next.js 14)

### Estrutura de Páginas

| Rota | Arquivo | Passo |
|---|---|---|
| `/analisar` | `app/analisar/page.tsx` | 1 — Upload e análise da prova |
| `/turmas` | `app/turmas/page.tsx` | 2 — Turmas e alunos |
| `/lancar` | `app/lancar/page.tsx` | 3 — Lançamento de respostas |
| `/relatorio` | `app/relatorio/page.tsx` | 4 — Relatórios diagnósticos |

### Componentes Reutilizáveis

| Componente | Descrição |
|---|---|
| `Sidebar` | Navegação lateral com os 4 passos |
| `FlowBanner` | Indicador de progresso (passo atual) |
| `InfoBox` | Caixas de contexto (info/tip/glossary/warning) |
| `BloomBadge` | Badge colorido do nível de Bloom |
| `PctBadge` | Badge de percentual com cor semântica (verde/âmbar/vermelho) |

### Lib

| Arquivo | Descrição |
|---|---|
| `lib/api.ts` | Funções de chamada à API REST |
| `lib/types.ts` | Interfaces TypeScript (Turma, Aluno, Prova, AlunoReport…) |
| `lib/constants.ts` | Cores de Bloom, função `pctColor()` |

---

## 5. Fluxo de Dados — Upload de Prova

```
Professor envia PDF
        │
        ▼
POST /provas/upload (multipart/form-data)
        │
        ├─→ extract_text_from_file()
        │       ├─ pdfplumber (texto digital)
        │       └─ PyMuPDF + Tesseract (imagem/scan)
        │
        ├─→ segment_questions(text)
        │       └─ lista de {number, text, stem, alternatives}
        │
        ├─→ Para cada questão:
        │       ├─ classify_area(stem)
        │       ├─ classify_bloom(stem)
        │       ├─ classify_subarea(stem, area)
        │       └─ map_to_bncc(area, serie, bloom)
        │
        ├─→ db.salvar_prova(questoes_classificadas)
        │       └─ INSERT INTO provas + questoes
        │
        └─→ Resposta JSON: {prova_id, questions[], metadata}
```

## 6. Fluxo de Dados — Lançamento de Respostas

```
Professor submete respostas
        │
        ▼
POST /provas/{id}/lancar
        │
        ├─→ db.get_gabarito(prova_id)
        │       └─ {numero: alternativa}
        │
        ├─→ db.lancar_respostas_aluno(aluno_id, prova_id, respostas)
        │       ├─ Busca questoes.numero → id
        │       ├─ Compara resposta.upper() == gabarito.upper()
        │       └─ INSERT OR UPDATE respostas (correta = 0|1)
        │
        └─→ Resposta JSON: {ok, erros[]}
```
