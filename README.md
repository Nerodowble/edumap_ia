# EduMap IA

Plataforma web de **diagnóstico taxonômico de aprendizagem** para professores da educação básica. Permite fazer upload de provas em PDF/imagem, classificar automaticamente cada questão por área, subárea, Taxonomia de Bloom e habilidade BNCC, registrar respostas dos alunos (manual ou OCR) e gerar relatórios diagnósticos detalhados.

> **Sem IA paga.** Toda classificação é feita por regras, vocabulário e expressões regulares — funciona 100% offline.

---

## Arquitetura

```
edumap_ia/          ← Backend Python (FastAPI + SQLite)
edumap_frontend/    ← Frontend Next.js 14 (React, TypeScript, Tailwind)
```

O backend expõe uma **API REST** em `localhost:8000`. O frontend consome essa API em `localhost:3000`.

---

## Pré-requisitos

| Ferramenta | Versão mínima | Para que serve |
|---|---|---|
| Python | 3.9+ | Backend |
| Anaconda (recomendado) | — | Gerenciar ambiente Python |
| Node.js | 18+ | Frontend |
| Tesseract OCR | 5.x | OCR de imagens (opcional) |

**Instalar Tesseract (Windows):** baixe o instalador em [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) e instale no caminho padrão `C:\Program Files\Tesseract-OCR\`.

---

## Como Rodar

### 1. Backend (FastAPI)

```bash
cd edumap_ia
pip install -r requirements.txt
uvicorn api:app --reload
```

- API disponível em: `http://localhost:8000`
- Documentação interativa (Swagger): `http://localhost:8000/docs`
- O banco SQLite é criado automaticamente em `data/edumap.db`

### 2. Frontend (Next.js)

```bash
cd edumap_frontend
npm install
npm run dev
```

- Frontend disponível em: `http://localhost:3000`

---

## Fluxo do Professor (4 Passos)

```
1. ANALISAR PROVA    →  Upload PDF + OCR + Classificação automática + Gabarito
2. TURMAS E ALUNOS  →  Cadastrar turma e lista de alunos
3. LANÇAMENTO       →  Registrar respostas por aluno (manual ou OCR de folha)
4. RELATÓRIO        →  Ver diagnóstico: drilldown, por aluno, visão da turma
```

---

## Estrutura de Diretórios

```
edumap_ia/
├── api.py                      # Entrypoint da API FastAPI
├── requirements.txt            # Dependências Python
├── data/
│   └── edumap.db               # Banco SQLite (gerado automaticamente)
├── src/
│   ├── classifier/
│   │   ├── area_classifier.py  # Classifica área do conhecimento
│   │   ├── bloom_classifier.py # Detecta nível de Bloom
│   │   ├── bncc_mapper.py      # Mapeia habilidades BNCC
│   │   ├── segmenter.py        # Segmenta texto OCR em questões
│   │   └── subarea_classifier.py # Classifica subárea curricular
│   ├── database/
│   │   └── db.py               # Camada de acesso ao SQLite
│   ├── ocr/
│   │   └── extractor.py        # Extração de texto (PDF digital ou OCR)
│   └── data/
│       ├── vocabulario_areas.json   # Vocabulário por área
│       ├── verbos_bloom.json        # Verbos por nível de Bloom
│       ├── subareas.json            # Subáreas curriculares
│       └── bncc_habilidades.json    # Habilidades BNCC por série
├── tests/
│   ├── conftest.py             # Fixtures compartilhadas (pytest)
│   ├── test_api.py             # Testes de integração da API (86 testes)
│   └── test_classificadores.py # Testes unitários dos classificadores
├── scripts/
│   ├── gerar_prova_exemplo.py  # Gera PDF de prova exemplo
│   └── popular_dados_ficticios.py # Popula banco com dados de teste
├── provas_exemplo/
│   └── prova_exemplo_8ano.pdf  # Prova exemplo para testes
└── docs/
    ├── arquitetura.md          # Arquitetura detalhada do sistema
    ├── api.md                  # Referência completa da API REST
    ├── frontend.md             # Documentação do frontend Next.js
    ├── fluxo_professor.md      # Fluxo de uso passo a passo
    └── testes.md               # Guia de testes

edumap_frontend/
├── src/
│   ├── app/
│   │   ├── analisar/page.tsx   # Passo 1 — Upload e análise
│   │   ├── turmas/page.tsx     # Passo 2 — Turmas e alunos
│   │   ├── lancar/page.tsx     # Passo 3 — Lançamento de respostas
│   │   └── relatorio/          # Passo 4 — Relatórios
│   ├── components/             # Componentes reutilizáveis
│   └── lib/                    # API client, tipos, constantes
```

---

## Testes

```bash
cd edumap_ia
# Rodar todos os testes (86 no total)
C:\Users\willi\anaconda3\Scripts\pytest tests/ -v

# Apenas testes de API
C:\Users\willi\anaconda3\Scripts\pytest tests/test_api.py -v

# Apenas classificadores
C:\Users\willi\anaconda3\Scripts\pytest tests/test_classificadores.py -v
```

---

## Variáveis de Ambiente (Frontend)

Crie `edumap_frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Documentação Detalhada

| Documento | Conteúdo |
|---|---|
| [docs/arquitetura.md](docs/arquitetura.md) | Arquitetura, banco de dados, módulos |
| [docs/api.md](docs/api.md) | Referência completa dos endpoints REST |
| [docs/frontend.md](docs/frontend.md) | Páginas, componentes e lib do frontend |
| [docs/fluxo_professor.md](docs/fluxo_professor.md) | Fluxo de uso passo a passo |
| [docs/testes.md](docs/testes.md) | Como rodar e entender os testes |
