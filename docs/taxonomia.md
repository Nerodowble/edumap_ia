# Taxonomia Educacional — EduMap IA

> Estruturação do novo sistema de classificação taxonômica profunda de questões.

---

## 1. Motivação

### Limitação atual
Hoje, cada questão recebe 3 classificações rasas:
- **Área** (matemática, português, etc.)
- **Subárea** (geometria, álgebra, etc.) — genérica demais
- **Nível de Bloom** (lembrar → criar)

Isso permite dizer "Bruno errou muito em Geometria", mas **não diz onde exatamente** — se é em triângulos, polígonos, ângulos, volume... O professor ainda precisa investigar manualmente.

### O que queremos
Uma árvore taxonômica profunda (5 níveis) por matéria, onde cada questão é classificada no **nó mais específico possível**:

```
Matemática → Geometria → Figuras Planas → Polígonos → Triângulos → Equilátero
```

E o relatório aponta exatamente esse ponto: *"Bruno errou 3 questões em **Triângulos › classificação por ângulos**"* — o professor vai direto na raiz do problema.

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
| `data/taxonomia.json` | **Fonte da verdade**, versionável no git |
| Tabela `taxonomia` no PostgreSQL | Acesso rápido em runtime |
| Script `seed_taxonomia.py` | Carrega JSON → DB (idempotente) |

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
Nova coluna para armazenar o nó classificado:

```sql
ALTER TABLE questoes ADD COLUMN taxonomia_codigo TEXT;
```

---

## 3. Fluxo de Classificação

```
1. Professor faz upload da prova e SELECIONA a matéria (obrigatório)
2. OCR extrai texto de cada questão
3. Classificador:
   a. Carrega a árvore taxonômica da matéria selecionada
   b. Para cada nó, conta matches de palavras-chave no enunciado
   c. Escolhe o nó mais profundo com pelo menos N matches
   d. Fallback: sobe um nível se confiança < threshold
4. Classificador ainda faz Bloom (nível cognitivo) — independente
5. Salva: questão + taxonomia_codigo + nível Bloom
```

### Exemplo real
Enunciado: *"Calcule a área de um triângulo equilátero com lado 6 cm."*

Palavras-chave detectadas: `área`, `triângulo`, `equilátero`, `lado`
Resultado: `ef2.matematica.geometria.figuras_planas.poligonos.triangulos.equilatero`

---

## 4. Fluxo do Relatório

### 4.1 Drilldown hierárquico
```
Matemática (45% acerto geral)
├── Aritmética ................. 78%
├── Álgebra .................... 62%
└── Geometria .................. 23% ⚠️
    ├── Figuras Planas ......... 18% ⚠️
    │   └── Polígonos .......... 15% ⚠️
    │       └── Triângulos ..... 10% ⚠️
    │           ├── Equilátero . 0%  ⚠️⚠️
    │           └── Isósceles .. 20% ⚠️
    └── Sólidos Geométricos .... 40%
```

### 4.2 Recomendação ao professor
```
Bruno Silva (percentual geral: 58%)
Pontos críticos:
  • Triângulos › Equilátero ............ 0% (1 questão)
  • Polígonos › Quadriláteros .......... 33% (3 questões)
  • Ângulos › Tipos de ângulos ......... 50% (2 questões)
```

---

## 5. Roadmap

| Fase | O que | Status |
|------|-------|--------|
| **1** | Tornar matéria obrigatória no upload | 🔲 pendente |
| **2** | Estrutura de dados: JSON + tabela + seed | ✅ implementado |
| **3** | Novo classificador profundo | 🔲 pendente |
| **4** | Relatório drilldown navegável | 🔲 pendente |
| **5** | Interface admin_geral para editar taxonomia | 🔲 futuro |
| **6** | Expandir para Ensino Médio e Superior | 🔲 futuro |

---

## 6. Extensibilidade

### 6.1 Novas etapas
Campo `etapa` permite crescer sem tocar em dados existentes:
- `ef1` — Ensino Fundamental I (1º–5º)
- `ef2` — Ensino Fundamental II (6º–9º) — **foco atual**
- `em` — Ensino Médio
- `superior` — Graduação
- `curso_*` — Cursos técnicos/livres

### 6.2 Adição de nós por admin
Futuro: tela onde `admin_geral` pode adicionar/editar nós + palavras-chave (melhora classificador).

---

## 7. Provas de Exemplo para Testes

Na pasta `scripts/` estão geradores de PDFs sintéticos com questões desenhadas para bater em nós específicos da taxonomia:

| Script | Matéria | Foco |
|--------|---------|------|
| `gerar_prova_matematica.py` | Matemática | Geometria (polígonos, ângulos, áreas, volumes) |
| `gerar_prova_portugues.py` | Português | Gramática + interpretação |
| `gerar_prova_geografia.py` | Geografia | Física, humana, cartografia |
| `gerar_prova_exemplo.py` (já existia) | Múltiplas | Prova genérica de 8º ano |

### Como gerar
```bash
cd edumap_ia
python scripts/gerar_prova_matematica.py
python scripts/gerar_prova_portugues.py
python scripts/gerar_prova_geografia.py
```

Os PDFs são salvos em `provas_exemplo/` e podem ser enviados diretamente pelo frontend da aplicação. Cada questão tem o nó esperado da taxonomia comentado no script, então na Fase 3 dá pra comparar o resultado do classificador com o gabarito.

---

## 8. Onde cada coisa mora

| Arquivo | Papel |
|---------|-------|
| `edumap_ia/data/taxonomia.json` | Taxonomia canônica (versionada) |
| `edumap_ia/src/database/db.py` | Schema da tabela `taxonomia` |
| `edumap_ia/scripts/seed_taxonomia.py` | Popular DB a partir do JSON |
| `edumap_ia/scripts/gerar_prova_*.py` | Gerar PDFs de prova para testes |
| `edumap_ia/src/classifier/taxonomia_classifier.py` | (Fase 3) Classificador profundo |
| `edumap_frontend/src/app/relatorio/` | (Fase 4) Nova UI do drilldown taxonômico |

---

## 9. Para rodar o seed manualmente

```bash
# Local (SQLite)
cd edumap_ia
python scripts/seed_taxonomia.py

# Produção (PostgreSQL via Render) — uma vez após deploy
DATABASE_URL="postgresql://..." python scripts/seed_taxonomia.py
```

O script é idempotente: pode rodar múltiplas vezes sem duplicar registros.
