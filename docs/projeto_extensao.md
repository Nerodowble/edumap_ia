# Implementação de Tecnologia Assistiva para Diagnóstico de Aprendizagem e Capacitação Docente

**Projeto de Extensão Universitária — EduMap**

---

## Identificação

| Campo | Informação |
|-------|------------|
| **Aluno extensionista** | Willian Vidal Lima |
| **Curso** | _______________________________________ |
| **Instituição** | _______________________________________ |
| **Disciplina/Componente** | Atividade de Extensão Universitária |
| **Período letivo** | _______________________________________ |
| **Data da entrega** | _______________________________________ |

---

## 1. Resumo Executivo

O **EduMap** é uma plataforma web gratuita que automatiza o diagnóstico
pedagógico a partir de provas reais aplicadas a alunos. Combinando OCR
(Reconhecimento Óptico de Caracteres) e uma taxonomia educacional
hierárquica, o sistema lê a prova, classifica cada questão por área de
conhecimento, nível cognitivo (Taxonomia de Bloom) e tópico específico,
e gera relatórios que mostram **exatamente** onde cada aluno tem
dificuldade — não apenas "errou em Geometria", mas "errou na
classificação de triângulos pelos lados".

A ferramenta foi desenvolvida no contexto desta extensão universitária
e prestada como **serviço gratuito a professores particulares,
centros de reforço e escolas de bairro**, otimizando o tempo de ensino
e direcionando o esforço pedagógico ao que importa.

---

## 2. Apresentação do Projeto

- **Nome:** EduMap
- **Tipo:** Plataforma web (frontend + backend) com IA assistiva
- **URL pública:** https://edumap-frontend-nu.vercel.app
- **Repositórios (código aberto):**
  - Frontend: https://github.com/Nerodowble/edumap_frontend
  - Backend: https://github.com/Nerodowble/edumap_ia
- **Custo para o usuário final:** R$ 0,00 (totalmente gratuito)
- **Acesso:** cadastro próprio do professor; sem dependência de
  instalação local

---

## 3. Justificativa

### O problema
Professores da educação básica e do reforço escolar enfrentam uma
limitação prática diária: ao corrigir uma prova, identificam **que** o
aluno errou, mas raramente conseguem mapear sistematicamente **onde**
está a lacuna — qual habilidade específica precisa ser reforçada.

Isso leva a:
- Aulas de revisão pouco direcionadas
- Reforço genérico que repete o que o aluno já sabe
- Tempo perdido com avaliação manual de padrões de erro
- Dificuldade de individualizar o cuidado pedagógico

### O que o EduMap resolve
1. **Automatiza a leitura** das provas (OCR), eliminando trabalho manual
2. **Classifica taxonomicamente** cada questão até o conceito específico
3. **Gera relatórios** apontando os pontos críticos da turma e de cada aluno
4. **Sugere ações** pedagógicas baseadas nos dados (ex: "9 de 28 alunos
   têm dificuldade em Triângulos — dedicar duas aulas")

---

## 4. Objetivos

### Geral
Disponibilizar gratuitamente uma ferramenta de diagnóstico pedagógico
automatizado a professores que atuam fora dos sistemas educacionais com
recursos para tecnologia, ampliando a precisão do cuidado individualizado
oferecido aos alunos.

### Específicos
1. Construir uma plataforma web acessível (qualquer navegador, sem instalação)
2. Implementar OCR de provas em PDF e imagem
3. Estruturar uma taxonomia educacional hierárquica (até 6 níveis)
4. Permitir que professores cadastrem turmas, alunos e respostas
5. Produzir relatórios em formato visual e em PDF para compartilhamento
6. Manter o código aberto, permitindo reuso e adaptação

---

## 5. Metodologia e Funcionamento

### Tecnologias utilizadas
- **Backend:** Python (FastAPI), Tesseract OCR, PyMuPDF, PostgreSQL
- **Frontend:** Next.js 14 (React, TypeScript), Tailwind CSS
- **Infraestrutura:** Render (backend + banco), Vercel (frontend)
- **Autenticação:** JWT com 3 níveis (admin geral, admin escolar, professor)

### Fluxo de uso pelo professor
1. Cadastro próprio na plataforma (gratuito)
2. Criação de turma e cadastro de alunos
3. Upload da prova (PDF/foto)
4. Sistema executa OCR e classifica cada questão
5. Professor define o gabarito oficial
6. Professor lança as respostas dos alunos
7. Sistema gera relatórios:
   - Visão geral da turma
   - Árvore de conteúdo (drill-down até o tópico específico)
   - Por aluno (com pontos críticos personalizados)
   - PDF completo com recomendações pedagógicas

### Taxonomia educacional
A plataforma vem com taxonomias prontas para múltiplas etapas:
- **Ensino Fundamental II** (282 nós): Matemática (com Geometria detalhada),
  Português, Geografia, Ciências, História, Inglês, Artes, Ed. Física
- **Ensino Superior** (361 nós): Psicologia, Saúde Mental, SUS

A taxonomia é totalmente editável pelo administrador via interface
gráfica, permitindo expansão para novas matérias, etapas e cursos.

---

## 6. Impacto Social

### Beneficiários diretos
- **Professores particulares e de reforço escolar** que muitas vezes
  trabalham sozinhos, sem equipe pedagógica de apoio
- **Pequenas escolas de bairro** com recursos tecnológicos limitados
- **Educadores em formação** (estagiários, monitores) que ganham uma
  ferramenta de análise rica para usar em sua prática

### Beneficiários indiretos
- **Alunos:** recebem reforço mais direcionado e eficiente, evitando
  revisões genéricas e ganhando tempo para sanar lacunas reais
- **Famílias:** veem o resultado do reforço com mais clareza, podendo
  apoiar em casa de forma específica
- **Sistema educacional como um todo:** propagação de uma cultura de
  diagnóstico baseado em dados na ponta

### Características que reforçam o caráter de extensão
- **Gratuito** — sem assinatura, paywall ou limite de uso
- **Aberto** — código-fonte público, permite que outros estudantes
  estendam o projeto em trabalhos futuros
- **Acessível** — funciona em qualquer navegador, inclusive em
  celulares modestos
- **Em português** — interface inteiramente em PT-BR, sem barreira
  linguística
- **Sem coleta abusiva de dados** — apenas o necessário para o
  funcionamento (e-mail, senha, dados das turmas/provas do próprio professor)

---

## 7. Atividade Prática Realizada

### Sessão de diagnóstico com professor parceiro

| Campo | Informação |
|-------|------------|
| **Data da ação** | _______________________________________ |
| **Horário (início e término)** | _______________________________________ |
| **Carga horária** | _______________________________________ |
| **Local** | _______________________________________ |
| **Endereço completo** | _______________________________________ |
| **Geolocalização (latitude, longitude)** | _______________________________________ |

### Descrição da atividade
Apresentação do sistema EduMap ao(à) professor(a) parceiro(a),
demonstração do fluxo completo (cadastro → upload de prova →
classificação automática → relatório), aplicação em uma prova real
fornecida pelo(a) docente, análise conjunta dos resultados e coleta
de feedback e validação pedagógica.

### Critérios de avaliação atendidos
- [x] Atividade executada **na prática** com docente parceiro(a)
- [x] **Registro fotográfico** anexado (extensionista presente nas fotos)
- [x] **Geolocalização** registrada (campo acima)
- [x] **Atestado de presencialidade** assinado (próximas seções)
- [x] **Revisão completa** das informações antes da finalização

---

## 8. Resultados Observados

Durante a sessão, o(a) professor(a) parceiro(a) testou o sistema em
uma prova real e validou:

- A correção do **OCR** na leitura das questões
- A precisão da **classificação taxonômica** das questões
- A **clareza dos relatórios** gerados (interface e PDF)
- A **utilidade prática** da ferramenta para o cotidiano docente
- As **recomendações pedagógicas** geradas automaticamente

A devolutiva qualitativa do(a) docente está registrada na seção 11
deste documento.

---

## 9. Considerações Finais e Continuidade

O EduMap nasceu como projeto de extensão universitária mas foi
construído desde o início com **arquitetura escalável** e **código
aberto**, permitindo:

- Uso continuado pelos professores parceiros após o término da extensão
- Estudantes futuros estenderem o projeto (novas taxonomias,
  novas matérias, novas funcionalidades)
- Possibilidade de virar produto/serviço institucional, mantendo a
  versão gratuita aberta

A ferramenta permanecerá no ar e acessível em
**https://edumap-frontend-nu.vercel.app**, e o código continuará
mantido publicamente nos repositórios listados na seção 2.

---

## 10. Identificação do Aluno Extensionista

| Campo | Informação |
|-------|------------|
| **Nome completo** | Willian Vidal Lima |
| **CPF** | _______________________________________ |
| **RA / Matrícula** | _______________________________________ |
| **Curso** | _______________________________________ |
| **Instituição** | _______________________________________ |
| **E-mail** | willian.lima@legalbot.com.br |

**Assinatura do extensionista:**

```
________________________________________
Willian Vidal Lima
Data: ____/____/______
```

---

## 11. Atestado de Presencialidade — Professor(a) Parceiro(a)

> **Eu, abaixo identificado(a), atesto que o(a) aluno(a) Willian Vidal Lima
> realizou comigo, na data e local abaixo informados, uma sessão prática
> de demonstração e validação da plataforma EduMap, no contexto da sua
> atividade de extensão universitária. Aprovo o uso pedagógico da
> ferramenta apresentada e confirmo a presença física do extensionista
> durante toda a ação.**

### Dados do(a) Professor(a) Parceiro(a)

| Campo | Informação |
|-------|------------|
| **Nome completo** | _______________________________________ |
| **CPF** | _______________________________________ |
| **Formação / Titulação** | _______________________________________ |
| **Cargo / Função** | _______________________________________ |
| **Instituição em que atua** | _______________________________________ |
| **E-mail** | _______________________________________ |
| **Telefone** | _______________________________________ |

### Dados da Ação

| Campo | Informação |
|-------|------------|
| **Local da ação** | _______________________________________ |
| **Endereço completo** | _______________________________________ |
| **Geolocalização** | _______________________________________ |
| **Data** | ____/____/______ |
| **Horário (início — término)** | _____ : _____ até _____ : _____ |
| **Carga horária total** | ___________ hora(s) |

### Descrição da Atividade

Aplicação prática do sistema **EduMap** — plataforma web gratuita de
diagnóstico pedagógico via OCR e análise por taxonomia de erros — em
provas reais aplicadas pelo(a) professor(a). A sessão envolveu:

- Demonstração completa da plataforma
- Cadastro de turma e alunos pelo(a) próprio(a) docente
- Upload de prova(s) e leitura automática via OCR
- Classificação taxonômica das questões
- Lançamento de respostas e geração de relatórios
- Análise conjunta dos resultados e devolutiva do(a) professor(a)

### Devolutiva e Aprovação Pedagógica

(Espaço para o(a) professor(a) parceiro(a) registrar comentários,
sugestões e validação pedagógica do uso da ferramenta.)

```
_____________________________________________________________________
_____________________________________________________________________
_____________________________________________________________________
_____________________________________________________________________
_____________________________________________________________________
_____________________________________________________________________
```

### Assinatura

Declaro estar ciente do conteúdo deste documento e atesto a veracidade
das informações prestadas.

```
________________________________________
Assinatura (a mão, com nome completo, ou via GOV.BR)
Nome: ___________________________________________________________
CPF:  ___________________________________________________________
Data: ____/____/______
```

> **Observação para validação GOV.BR:** caso a assinatura seja digital
> via GOV.BR, anexar o arquivo PDF assinado a este documento ou
> mencionar a URL/código de validação no espaço acima.

---

## Anexos

A entrega completa deste projeto inclui, além deste documento:

1. **Fotografias da ação** com o extensionista presente
2. **Captura de geolocalização** (print do mapa ou coordenadas)
3. **Este documento** preenchido e assinado
4. (Opcional) Print do relatório gerado pela plataforma durante a
   sessão de teste, demonstrando o uso real

---

*EduMap — projeto de extensão universitária · diagnóstico educacional ·
código aberto*
