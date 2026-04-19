# EduMap IA — Documentação do Frontend

**Stack:** Next.js 14 (App Router) · React · TypeScript · Tailwind CSS  
**Diretório:** `edumap_frontend/`  
**Porta padrão:** `http://localhost:3000`

---

## 1. Configuração

**Variável de ambiente** (`edumap_frontend/.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Iniciar em desenvolvimento:**
```bash
cd edumap_frontend
npm install
npm run dev
```

**Build de produção:**
```bash
npm run build
npm start
```

---

## 2. Estrutura de Diretórios

```
src/
├── app/
│   ├── layout.tsx              # Layout raiz — Sidebar + área de conteúdo
│   ├── page.tsx                # Página inicial — redireciona para /analisar
│   ├── globals.css             # Estilos globais + classes utilitárias (card, input, label, tab-btn)
│   ├── analisar/
│   │   └── page.tsx            # Passo 1 — Upload e análise da prova
│   ├── turmas/
│   │   └── page.tsx            # Passo 2 — Turmas e alunos
│   ├── lancar/
│   │   └── page.tsx            # Passo 3 — Lançamento de respostas
│   └── relatorio/
│       ├── page.tsx            # Passo 4 — Seletor de turma/prova + KPIs + abas
│       ├── DrilldownTab.tsx    # Aba: Diagnóstico por Conteúdo
│       ├── AlunoTab.tsx        # Aba: Por Aluno (com detalhamento por questão)
│       └── TurmaTab.tsx        # Aba: Visão Geral da Turma
├── components/
│   ├── Sidebar.tsx             # Navegação lateral
│   ├── FlowBanner.tsx          # Indicador de progresso (4 passos)
│   ├── InfoBox.tsx             # Caixas de ajuda contextual
│   ├── BloomBadge.tsx          # Badge do nível de Bloom
│   └── PctBadge.tsx            # Badge de percentual colorido
└── lib/
    ├── api.ts                  # Funções de chamada à API REST
    ├── types.ts                # Interfaces TypeScript
    └── constants.ts            # Cores de Bloom, pctColor()
```

---

## 3. Páginas

### `/analisar` — Passo 1: Analisar Prova

**Arquivo:** `app/analisar/page.tsx`

**Funcionalidades:**
- Formulário de upload: seleciona arquivo PDF/imagem, série, disciplina e turma
- Exibe barra de progresso durante processamento
- Após upload: mostra tabela de questões com área, subárea e nível de Bloom
- **GabaritoCard:** grade de inputs para definir a alternativa correta de cada questão com auto-avanço (tecla seguinte automática)
- Salva o gabarito via `POST /provas/{id}/gabarito`
- Banner "Próximo passo" ao final

**Componentes locais:**
- `ResultsView` — exibe tabela de questões + sidebar com distribuição de Bloom + card BNCC
- `GabaritoCard` — grade de inputs do gabarito com auto-avanço

---

### `/turmas` — Passo 2: Turmas e Alunos

**Arquivo:** `app/turmas/page.tsx`

**Funcionalidades:**
- Criar nova turma (nome, escola, disciplina)
- Listar turmas existentes
- Deletar turma (com confirmação)
- Ao selecionar uma turma: listar alunos e adicionar novos
- Deletar aluno individualmente

---

### `/lancar` — Passo 3: Lançamento de Respostas

**Arquivo:** `app/lancar/page.tsx`

**Funcionalidades:**
- Seletores de turma e prova (carregamento em cascata)
- **Grade de lançamento:** tabela onde linhas=alunos e colunas=questões
  - Linha de gabarito (em verde) no topo — apenas visual, não editável
  - Inputs de resposta por aluno com auto-avanço na linha
- **Lançamento via OCR:** botão 📷 por aluno
  - Abre seletor de arquivo (foto da folha de respostas)
  - Chama `POST /provas/{id}/ocr-aluno`
  - Preenche automaticamente os inputs do aluno com os valores detectados
  - Células preenchidas por OCR destacadas em azul
- Botão "Salvar" chama `POST /provas/{id}/lancar` com todas as respostas de uma vez

---

### `/relatorio` — Passo 4: Relatório

**Arquivo:** `app/relatorio/page.tsx`

**Funcionalidades:**
- Seletores de turma e prova
- **KPIs no topo:** total de questões, série, alunos avaliados, média da turma
- **Três abas de análise:**
  - **Diagnóstico por Conteúdo** (`DrilldownTab`)
  - **Por Aluno** (`AlunoTab`)
  - **Visão Geral** (`TurmaTab`)

#### Aba: Diagnóstico por Conteúdo (`DrilldownTab`)

Drilldown hierárquico: **Área → Subárea → Nível de Bloom → Aluno**

- Accordion por área de conhecimento
- Dentro de cada área: cards por subárea com percentual da turma
- Dentro de cada subárea: breakdown por nível de Bloom
- Lista de alunos com pior desempenho primeiro

#### Aba: Por Aluno (`AlunoTab`)

Ranking individual dos alunos ordenado por percentual.

Ao expandir um aluno, mostra:
1. **Por nível cognitivo:** cards com percentual em cada nível de Bloom
2. **Pontos críticos:** conteúdos onde o aluno teve < 60%
3. **Detalhamento por questão:** grade visual com Q1…Q12 em verde (✓) ou vermelho (✗), mostrando a alternativa respondida
4. **Questões erradas:** lista detalhada — número, área, nível Bloom, "Respondeu X | Gabarito Y"
5. **Recomendações:** sugestões pedagógicas por nível de Bloom com baixo desempenho

#### Aba: Visão Geral (`TurmaTab`)

- Estatísticas gerais da turma
- Lista de alunos que precisam de atenção (percentual < 50%)
- Distribuição de questões por área e Bloom

---

## 4. Componentes

### `Sidebar`
Navegação lateral fixa com os 4 passos numerados. O link ativo é destacado em azul.

```tsx
const NAV = [
  { href: "/analisar",  label: "Analisar Prova",        icon: "📤" },
  { href: "/turmas",    label: "Turmas e Alunos",        icon: "👥" },
  { href: "/lancar",    label: "Lançamento",             icon: "📝" },
  { href: "/relatorio", label: "Relatório do Professor", icon: "📊" },
];
```

### `FlowBanner`
Exibe os 4 passos do fluxo com o passo atual destacado em azul e os anteriores com ✓ verde.

```tsx
<FlowBanner step={3} />  // exibe "passo 3 de 4"
```

**Props:** `step: 1 | 2 | 3 | 4`

### `InfoBox`
Caixa de ajuda contextual com 4 variantes visuais.

```tsx
<InfoBox variant="info" title="Como usar?">
  <p>Texto explicativo...</p>
</InfoBox>
```

**Variantes:**

| Variant | Cor | Ícone | Uso |
|---|---|---|---|
| `info` | Azul | ℹ️ | Instruções gerais |
| `tip` | Âmbar | 💡 | Dicas de interpretação |
| `glossary` | Roxo | 📖 | Definições e glossário |
| `warning` | Vermelho | ⚠️ | Alertas importantes |

**Props:** `variant?`, `title?`, `children`, `className?`

### `BloomBadge`
Badge colorido com o nível e nome de Bloom.

```tsx
<BloomBadge level={3} name="Aplicar" color="#F59E0B" />
```

### `PctBadge`
Badge de percentual com cor semântica.

```tsx
<PctBadge pct={75} />  // verde: ≥70%, âmbar: 50-69%, vermelho: <50%
```

---

## 5. Lib

### `lib/api.ts`

Todas as chamadas HTTP à API backend. Usa `fetch` nativo com `NEXT_PUBLIC_API_URL`.

**Funções principais:**

| Função | Endpoint | Descrição |
|---|---|---|
| `getTurmas()` | GET /turmas | Lista turmas |
| `createTurma(body)` | POST /turmas | Cria turma |
| `deleteTurma(id)` | DELETE /turmas/{id} | Remove turma |
| `getAlunos(turmaId)` | GET /turmas/{id}/alunos | Lista alunos |
| `createAluno(turmaId, body)` | POST /turmas/{id}/alunos | Cria aluno |
| `getProvas(turmaId)` | GET /turmas/{id}/provas | Lista provas |
| `uploadProva(formData)` | POST /provas/upload | Upload + análise |
| `getQuestoes(provaId)` | GET /provas/{id}/questoes | Lista questões |
| `getGabarito(provaId)` | GET /provas/{id}/gabarito | Recupera gabarito |
| `saveGabarito(provaId, gabarito)` | POST /provas/{id}/gabarito | Salva gabarito |
| `lancarRespostas(provaId, respostas)` | POST /provas/{id}/lancar | Lança respostas bulk |
| `ocrGabaritoAluno(provaId, file)` | POST /provas/{id}/ocr-aluno | OCR de folha física |
| `getRelatorioTurma(provaId)` | GET /provas/{id}/relatorio/turma | Relatório por aluno |
| `getRelatorioDrilldown(provaId)` | GET /provas/{id}/relatorio/drilldown | Drilldown |

### `lib/types.ts`

Principais interfaces TypeScript:

```typescript
interface Turma { id, nome, escola, disciplina, criado_em }
interface Aluno { id, nome, turma_id, criado_em }
interface Prova { id, titulo, serie, total_questoes, criado_em, ... }
interface Question { number, stem, area_key, bloom_level, bloom_name, ... }

interface DetalheQuestao {
  numero, area_display, bloom_nivel, bloom_nome,
  correta, resposta, gabarito
}

interface AlunoReport {
  aluno: { id, nome }
  acertos, total, percentual
  por_bloom: Record<string, { acertos, total }>
  detalhes?: DetalheQuestao[]
}

type DrilldownData = Record<string, Record<string, SubareaData>>
```

### `lib/constants.ts`

```typescript
// Cores dos níveis de Bloom
const BLOOM_COLORS: Record<number, string> = {
  1: "#3B82F6", 2: "#10B981", 3: "#F59E0B",
  4: "#F97316", 5: "#EF4444", 6: "#8B5CF6", 0: "#9CA3AF"
}

// Cor semântica para percentuais
function pctColor(pct: number): string
// ≥70% → verde | 50-69% → âmbar | <50% → vermelho
```

---

## 6. Estilos Globais (`globals.css`)

Classes utilitárias definidas via `@layer components`:

| Classe | Uso |
|---|---|
| `.card` | Caixa branca com sombra e borda arredondada |
| `.input` | Input/select estilizado |
| `.label` | Label de formulário |
| `.btn-primary` | Botão azul principal |
| `.btn-danger` | Botão vermelho de exclusão |
| `.tab-btn` | Botão de aba |
| `.tab-btn-active` | Aba ativa (azul) |
| `.tab-btn-inactive` | Aba inativa (cinza) |
