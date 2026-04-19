# EduMap IA — Fluxo de Uso do Professor

Guia passo a passo de como um professor utiliza a plataforma do início ao fim.

---

## Visão Geral do Fluxo

```
PASSO 1          PASSO 2          PASSO 3          PASSO 4
Analisar    →    Turmas      →    Lançar      →    Relatório
Prova            e Alunos         Respostas         Diagnóstico
/analisar        /turmas          /lancar           /relatorio
```

O **FlowBanner** no topo de cada página indica em qual passo o professor está e permite navegar entre eles.

---

## Passo 1 — Analisar Prova

**Objetivo:** fazer o upload da prova e obter a classificação automática das questões.

### O que fazer:

1. Acesse **Analisar Prova** (`/analisar`)
2. Clique em **Selecionar arquivo** e escolha o PDF ou imagem da prova
3. Preencha a **Série/Ano** (ex: "8º ano EF")
4. Opcionalmente, selecione a **Disciplina** — se deixar em "Detectar automaticamente", o sistema tenta identificar por área de vocabulário
5. Opcionalmente, vincule a prova a uma **Turma** já cadastrada
6. Clique em **Analisar Prova**

### O que acontece por baixo:
- O arquivo é enviado para o backend
- O backend extrai o texto (direto do PDF se for digital, ou OCR se for scan/imagem)
- O texto é segmentado em questões individuais
- Cada questão é classificada por: área, subárea, nível de Bloom e habilidade BNCC

### O que aparece na tela:

**Tabela de questões** com:
- Número da questão
- Enunciado (primeiros caracteres)
- Área do conhecimento detectada
- Subárea curricular
- Nível de Bloom (badge colorido)
- Habilidades BNCC prováveis

**Sidebar** com:
- Distribuição das questões por nível de Bloom (gráfico de barras)
- Painel com códigos BNCC mapeados

**GabaritoCard** (logo abaixo da tabela):
- Grade de inputs onde o professor digita a alternativa correta de cada questão (A–E)
- O cursor avança automaticamente para a próxima questão a cada digitação
- Ao terminar, clicar **Salvar Gabarito** — o gabarito fica salvo no banco e será usado para calcular acertos

> **Dica:** o gabarito pode ser definido ou atualizado a qualquer momento, inclusive depois de lançar as respostas. Ao relançar as respostas, os acertos são recalculados automaticamente com o novo gabarito.

---

## Passo 2 — Turmas e Alunos

**Objetivo:** cadastrar a turma e a lista de alunos.

### O que fazer:

1. Acesse **Turmas e Alunos** (`/turmas`)
2. Clique em **Nova Turma** e preencha: nome, escola (opcional), disciplina (opcional)
3. Selecione a turma criada na lista
4. Adicione os alunos um a um (campo de nome + botão Adicionar)
5. Repita para outras turmas se necessário

### Observações:
- Ao **deletar uma turma**, todos os alunos vinculados são removidos automaticamente
- Alunos podem ser removidos individualmente
- A mesma turma pode ter provas de disciplinas diferentes

---

## Passo 3 — Lançamento de Respostas

**Objetivo:** registrar o que cada aluno respondeu na prova.

### O que fazer:

1. Acesse **Lançamento** (`/lancar`)
2. Selecione a **Turma** e a **Prova**
3. A grade aparece: linhas = alunos, colunas = questões
4. A primeira linha (verde) mostra o gabarito definido no Passo 1

**Opção A — Digitação manual:**
- Clique no campo do aluno/questão e digite a alternativa (A–E)
- O cursor avança automaticamente para a próxima questão na linha
- Ao terminar a linha de um aluno, passar para o próximo

**Opção B — OCR (folha de respostas físicas):**
- Clique no botão 📷 ao lado do nome do aluno
- Selecione a foto ou scan da folha de respostas do aluno
- O sistema aplica OCR e preenche automaticamente as respostas detectadas (em azul)
- Revise e corrija manualmente qualquer erro de reconhecimento

5. Ao terminar todos os alunos, clique **Salvar Lançamento**

### Como o sistema calcula os acertos:
- Compara cada resposta do aluno com o gabarito (case-insensitive)
- `resposta.upper() == gabarito.upper()` → acerto
- Questões sem gabarito definido são contadas como 0 acerto

---

## Passo 4 — Relatório Diagnóstico

**Objetivo:** analisar o desempenho da turma de forma completa.

### O que fazer:

1. Acesse **Relatório do Professor** (`/relatorio`)
2. Selecione a **Turma** e a **Prova**
3. Leia os **KPIs no topo:** total de questões, série, alunos avaliados, média da turma
4. Explore as três abas de análise

---

### Aba 1: Diagnóstico por Conteúdo

Drilldown hierárquico: **Área → Subárea → Nível de Bloom → Aluno**

**Como interpretar:**
- Expanda uma área (ex: Matemática) para ver as subáreas (Álgebra, Geometria…)
- Dentro de cada subárea, veja o percentual da turma por nível cognitivo
- A lista de alunos aparece ordenada do pior para o melhor desempenho
- **Vermelho** = dificuldade significativa → priorizar este conteúdo

**Uso prático:**
> "A turma tem 40% de acerto em *Geometria* no nível *Aplicar*. Os alunos Carlos e Ana são os que mais precisam de atenção neste conteúdo."

---

### Aba 2: Por Aluno

Ranking individual do mais para o menos aproveitamento.

**Ao clicar em um aluno, abre-se:**

1. **Por nível cognitivo** — percentual em cada nível de Bloom
2. **Pontos críticos** — subáreas onde o aluno teve < 60%
3. **Detalhamento por questão** — grade visual com ✓ (verde) e ✗ (vermelho)
   - Cada célula mostra: número da questão e a letra respondida
   - Passe o mouse para ver: área, nível de Bloom, resposta e gabarito
4. **Questões erradas** — lista com: número, área, nível de Bloom, "Respondeu X | Gabarito Y"
5. **Recomendações pedagógicas** — sugestões por nível de Bloom com baixo desempenho

**Uso prático:**
> "O aluno Bruno errou Q3, Q7 e Q11 (todas de Álgebra — Aplicar). Sugestão: exercícios contextualizados do cotidiano."

---

### Aba 3: Visão Geral

Visão consolidada da turma:
- Média e distribuição de desempenho
- Lista de alunos que precisam de atenção (< 50%)
- Distribuição de questões por área e por Bloom

---

## Interpretando os Percentuais

| Faixa | Cor | Interpretação |
|---|---|---|
| ≥ 70% | Verde | Desempenho satisfatório |
| 50 – 69% | Âmbar | Reforço recomendado |
| < 50% | Vermelho | Dificuldade significativa — priorizar |

---

## Perguntas Frequentes

**Posso relançar as respostas depois de alterar o gabarito?**  
Sim. Basta salvar o novo gabarito no Passo 1 (ou pela API `POST /provas/{id}/gabarito`) e relançar (`POST /provas/{id}/lancar`). Os acertos serão recalculados automaticamente.

**Posso usar a mesma prova para turmas diferentes?**  
A prova é vinculada a uma turma no upload. Para aplicar a mesma prova a outra turma, faça um novo upload vinculando à segunda turma.

**O OCR de folha de respostas é preciso?**  
Depende da qualidade da foto e da clareza da escrita. Recomenda-se sempre revisar os valores preenchidos automaticamente antes de salvar.

**Posso ter alunos sem respostas registradas?**  
Sim. O relatório exibe apenas os alunos que têm ao menos uma resposta registrada. Alunos sem respostas não aparecem no relatório.
