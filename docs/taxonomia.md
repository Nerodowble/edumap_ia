# Taxonomia Educacional — EduMap IA

> Sistema de classificação taxonômica profunda de questões. Cada questão é
> enquadrada no nó mais específico possível da árvore de conteúdo, permitindo
> que o relatório aponte exatamente onde o aluno tem dificuldade.

---

## 1. Motivação

### Limitação anterior
Antes, cada questão recebia 3 classificações rasas:
- **Área** (matemática, português, etc.)
- **Subárea** (geometria, álgebra, etc.) — genérica demais
- **Nível de Bloom** (lembrar → criar)

Isso permitia dizer *"Bruno errou muito em Geometria"*, mas **não apontava onde exatamente**.

### O que temos hoje
Árvore taxonômica hierárquica (até 6 níveis) por matéria, onde cada questão é
classificada no **nó mais específico possível**:

```
Matemática → Geometria → Figuras Planas → Polígonos → Triângulos → Equilátero
```

E o relatório aponta exatamente esse ponto: *"Bruno errou 3 questões em
**Triângulo Equilátero**"* — o professor vai direto na raiz do problema.

---

## 2. Arquitetura

### 2.1 Estrutura hierárquica
Cada nó tem:
- `codigo` — identificador único (ex: `ef2.matematica.geometria.figuras_planas.poligonos.triangulos.equilatero`)
- `label` — texto legível
- `nivel` — profundidade (1 = matéria, até 6 = conceito específico)
- `parent_id` — pai na árvore
- `palavras_chave` — termos que o classificador usa para bater com o enunciado da questão

### 2.2 Fontes de dados

| Fonte | Papel |
|-------|-------|
| `data/taxonomia.json` | Seed inicial + formato de import/export. Versionável no git |
| Tabela `taxonomia` no PostgreSQL | **Fonte da verdade em runtime** — editável via UI admin |
| Script `seed_taxonomia.py` | Bootstrap inicial (roda uma vez) |
| Endpoint `POST /admin/taxonomia/import-json` | Import em massa (opcional) |

### 2.3 Schema do banco

```sql
CREATE TABLE taxonomia (
    id              BIGSERIAL PRIMARY KEY,
    etapa           TEXT NOT NULL DEFAULT 'ef2',   -- ef1, ef2, em, superior, curso_*
    materia         TEXT NOT NULL,                 -- matematica, portugues, ...
    codigo          TEXT NOT NULL UNIQUE,          -- path completo separado por ponto
    label           TEXT NOT NULL,                 -- nome legível
    nivel           INTEGER NOT NULL,              -- profundidade (1..6)
    parent_id       BIGINT REFERENCES taxonomia(id) ON DELETE CASCADE,
    palavras_chave  TEXT,                          -- CSV de termos para matching
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.4 Enriquecimento da tabela `questoes`
Coluna que armazena o nó classificado:

```sql
ALTER TABLE questoes ADD COLUMN taxonomia_codigo TEXT;
```

---

## 3. Algoritmo de Classificação

Implementado em `src/classifier/taxonomia_classifier.py`.

### Passos
```
1. Normaliza o enunciado (lowercase + remove acentos via NFD)
2. Carrega todos os nós da matéria selecionada do banco
3. Para cada nó, conta quantas palavras-chave aparecem no enunciado
4. Calcula score: matches × 2 + nivel × 3
   → Matches ganham peso; nível (profundidade) ganha peso maior,
     preferindo leaves quando há empate entre pai e filho
5. Retorna o nó com maior score (ou None se nada bateu)
6. Monta o caminho completo do raiz até o nó escolhido
```

### Detalhes do matching
- **Word boundary** (`\b...\b` com regex) — evita falsos-positivos como "corda" dentro de "acordar"
- **Plural opcional** — padrão `\bkeyword s?\b` aceita singular e plural
- **Mínimo de 3 caracteres** — keywords muito curtas (como "à") são ignoradas para não gerar ruído
- **Normalização** — `Triângulo` e `triangulo` são tratados como iguais

### Exemplo real
Enunciado: *"Calcule a área de um triângulo equilátero com lado 6 cm."*

Palavras-chave detectadas:
- `triangulo` (nó Triângulos) → +1 match
- `equilatero` (nó Equilátero) → +1 match

Resultado: `ef2.matematica.geometria.figuras_planas.poligonos.triangulos.equilatero` (nível 6).

### Tuning
Se a classificação estiver errada para um tipo de questão, a solução é
**ajustar palavras-chave** — via UI admin (botão ✏️) ou editando o JSON e
reimportando.

---

## 4. CRUD de Nós (Fase 5)

Toda operação é feita direto no banco via API, em tempo real.

| Método | Endpoint | Quem | O que faz |
|--------|----------|------|-----------|
| `GET` | `/admin/taxonomia/stats` | autenticado | totais por matéria e nível |
| `GET` | `/admin/taxonomia/materias` | autenticado | lista matérias |
| `GET` | `/admin/taxonomia/nos?materia=X` | autenticado | lista nós (flat) de uma matéria |
| `POST` | `/admin/taxonomia/classificar` | autenticado | **testa** classificação em um texto |
| `POST` | `/admin/seed-taxonomia` | admin_geral | roda seed do JSON em disco (bootstrap) |
| `POST` | `/admin/taxonomia/import-json` | admin_geral | import em massa (body: JSON completo) |
| `POST` | `/admin/taxonomia/no` | admin_geral | cria nó filho |
| `PUT` | `/admin/taxonomia/no/{id}` | admin_geral | edita label + palavras-chave |
| `DELETE` | `/admin/taxonomia/no/{id}` | admin_geral | remove nó e descendentes (cascade) |

### UI de edição
Acesse `/admin` → aba **Taxonomia** → passe o mouse sobre qualquer nó. Aparecem 3 botões:
- **✏️ Editar** — formulário inline com label e palavras-chave
- **➕ Adicionar filho** — cria sub-nó imediatamente (herda matéria/etapa do pai)
- **🗑️ Deletar** — remove com confirmação (cascade nos filhos)

---

## 5. Fluxo de Classificação (`/provas/upload`)

```
1. Professor faz upload da prova e SELECIONA a matéria
2. OCR extrai texto de cada questão (segmenter.py)
3. Classificador:
   a. Carrega a árvore taxonômica da matéria selecionada (do banco)
   b. Para cada nó, conta matches de palavras-chave no enunciado
   c. Escolhe o nó com maior score
4. Classificador também faz Bloom (nível cognitivo) — independente
5. Salva: questão + taxonomia_codigo + caminho + nível Bloom
```

Se a classificação falhar (nenhum match), o campo `taxonomia_codigo` fica vazio
e a questão aparece no relatório só no drilldown legado (área/subárea/Bloom).

---

## 6. Relatórios

### 6.1 Árvore de Conteúdo
Endpoint: `GET /provas/{id}/relatorio/taxonomia`

Retorna a árvore com stats agregados por nó:
- Cada nó mostra: `total`, `acertos`, `percentual`
- Stats fazem **roll-up**: uma questão classificada em `Equilátero` conta para
  todos os nós ancestrais (Triângulos, Polígonos, Figuras Planas, Geometria,
  Matemática)
- Filhos ordenados por pior desempenho primeiro

Exemplo de output no frontend:
```
Matemática (45% acerto geral)
├── Aritmética ................. 78% 🟢
├── Álgebra .................... 62% 🟡
└── Geometria .................. 23% 🔴
    ├── Figuras Planas ......... 18% 🔴
    │   └── Polígonos .......... 15% 🔴
    │       └── Triângulos ..... 10% 🔴
    │           ├── Equilátero . 0%  🔴
    │           └── Isósceles .. 20% 🔴
    └── Sólidos Geométricos .... 40% 🔴
```

### 6.2 Pontos Críticos por Aluno
Endpoint: `GET /provas/{id}/relatorio/pontos-criticos?top_n=3`

Para cada aluno, retorna os top N nós taxonômicos com pior desempenho (< 70%):
```
Bruno Silva (percentual geral: 58%)
Pontos críticos:
  🎯 Triângulo Equilátero ............ 0% (0/1)
  🎯 Quadriláteros .................... 33% (1/3)
  🎯 Tipos de Ângulos ................. 50% (1/2)
```

Aparece automaticamente na aba "Por Aluno" do relatório.

---

## 7. Roadmap

| Fase | O que | Status |
|------|-------|--------|
| **1** | Trust na matéria informada pelo professor | ✅ (já funcionava) |
| **2** | Estrutura de dados: JSON + tabela + seed | ✅ |
| **3** | Classificador profundo que navega a árvore | ✅ |
| **4** | Relatório drilldown navegável pela taxonomia | ✅ |
| **5** | Interface admin_geral para editar a taxonomia | ✅ |
| **6** | Expandir para Ensino Médio e Superior | 🔲 futuro |

---

## 8. Extensibilidade

### 8.1 Novas etapas
Campo `etapa` permite crescer sem tocar em dados existentes:
- `ef1` — Ensino Fundamental I (1º–5º)
- `ef2` — Ensino Fundamental II (6º–9º) — **foco atual**
- `em` — Ensino Médio
- `superior` — Graduação
- `curso_*` — Cursos técnicos/livres

### 8.2 Multiplas matérias na mesma questão (futuro)
Uma questão pode tocar em várias áreas (ex: Geometria + Álgebra). Modelagem futura:
tabela N:M entre `questoes` e `taxonomia` com peso por associação.

---

## 9. Provas de Exemplo para Testes

Na pasta `scripts/` estão geradores de PDFs sintéticos com questões desenhadas
para bater em nós específicos da taxonomia:

| Script | Matéria | Foco |
|--------|---------|------|
| `gerar_prova_matematica.py` | Matemática | Geometria (polígonos, ângulos, áreas, volumes) |
| `gerar_prova_portugues.py` | Português | Gramática + interpretação |
| `gerar_prova_geografia.py` | Geografia | Física, humana, cartografia |
| `gerar_prova_exemplo.py` | Múltiplas | Prova genérica de 8º ano (legado) |

### Como gerar
```bash
cd edumap_ia
python scripts/gerar_prova_matematica.py
python scripts/gerar_prova_portugues.py
python scripts/gerar_prova_geografia.py
```

Os PDFs são salvos em `provas_exemplo/`. Cada script também gera um arquivo
`.gabarito.txt` ao lado do PDF listando a resposta correta + o nó esperado da
taxonomia para cada questão — útil para validar o classificador.

---

## 10. Arquivos Relevantes

| Arquivo | Papel |
|---------|-------|
| `edumap_ia/data/taxonomia.json` | Seed inicial (versionado no git) |
| `edumap_ia/src/database/db.py` | Schema da tabela `taxonomia` |
| `edumap_ia/src/database/taxonomia.py` | Seed + CRUD + consultas |
| `edumap_ia/src/classifier/taxonomia_classifier.py` | Classificador profundo |
| `edumap_ia/scripts/seed_taxonomia.py` | Script de bootstrap inicial |
| `edumap_ia/scripts/gerar_prova_*.py` | Geradores de PDF de teste |
| `edumap_ia/api.py` | Endpoints REST |
| `edumap_frontend/src/app/relatorio/TaxonomiaTab.tsx` | UI da árvore no relatório |
| `edumap_frontend/src/app/admin/page.tsx` | UI de CRUD da taxonomia |
