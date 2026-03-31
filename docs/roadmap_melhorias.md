# Roadmap de Evolução — EduMap IA

Este documento detalha as oportunidades de melhoria identificadas para as próximas versões do EduMap IA, visando aumentar a precisão pedagógica e a eficiência operacional para o professor.

---

## 1. Evolução da Inteligência de Classificação
### 1.1 Transição para Embeddings Locais (NLU)
Atualmente, o sistema utiliza *Bag-of-Words* (contagem de palavras). Para evitar erros de contexto, propõe-se:
* **Implementação:** Utilizar a biblioteca `sentence-transformers` com o modelo `paraphrase-multilingual-MiniLM-L12-v2`.
* **Benefício:** Classificação semântica. O sistema entenderá que uma questão sobre "crise hídrica" pode pertencer a Geografia ou Biologia pelo contexto, e não apenas por palavras isoladas.
* **Custo:** Zero (roda localmente na CPU).

### 1.2 Refinamento do Mapeamento BNCC
* **Busca Vetorial:** Cruzar o vetor da questão com o vetor das descrições oficiais da BNCC.
* **Sugestão Múltipla:** Permitir que uma questão seja vinculada a mais de uma habilidade, refletindo a realidade de questões interdisciplinares.

---

## 2. Automação Operacional (Otimização de Tempo)
### 2.1 Módulo de Correção Automática (OMR)
O maior gargalo atual é a inserção manual das respostas dos alunos.
* **Proposta:** Implementar leitura de gabaritos via câmera/foto usando `OpenCV`.
* **Fluxo:** O professor imprime um modelo padrão de folha de respostas -> Alunos preenchem -> Professor tira foto -> EduMap computa as notas instantaneamente.

### 2.2 Interface de Revisão de OCR
O OCR pode falhar em imagens de baixa qualidade.
* **Melhoria:** Criar uma etapa de "Sanity Check" no Streamlit após o upload, onde o professor pode editar o texto extraído antes da classificação final.

---

## 3. Gestão de Dados e Persistência
### 3.1 Histórico de Evolução Temporal
* **Dashboards de Progresso:** Adicionar visualizações que comparem o desempenho da mesma turma ao longo do ano (Prova 1 vs. Prova 2).
* **Filtros de Séries:** Estruturar o banco para separar dados por anos letivos e trimestres.

### 3.2 Portabilidade do Banco de Dados
* **Export/Import:** Criar botões para baixar o arquivo `edumap.db` e fazer upload dele. Isso resolve o problema de volatilidade em deploys no Streamlit Cloud.

---

## 4. Novas Funcionalidades Pedagógicas
### 4.1 Gerador de Planos de Intervenção
* **Saída:** Gerar um PDF automático para o professor com o "Top 3 pontos críticos da turma".
* **Personalização:** Sugerir materiais de estudo baseados na subárea onde a taxa de erro foi maior que 50%.

### 4.2 Gamificação e Engajamento
* **Relatório Individual:** Gerar um "mural de conquistas" para o aluno, focando no que ele já domina (ex: "Mestre em Álgebra") para incentivar a autoeficácia.

---

## 5. Interface e UX
* **Tema Escuro/Claro:** Ajuste nativo de acessibilidade.
* **Tooltips Pedagógicos:** Pequenas janelas explicativas sobre o que significa cada nível da Taxonomia de Bloom para auxiliar professores iniciantes na metodologia.
