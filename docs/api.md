# EduMap IA — Referência da API REST

**Base URL:** `http://localhost:8000`  
**Docs interativas:** `http://localhost:8000/docs` (Swagger UI)  
**Formato:** JSON (request e response)

---

## Sumário de Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | Status da API |
| **Turmas** | | |
| GET | `/turmas` | Listar turmas |
| POST | `/turmas` | Criar turma |
| DELETE | `/turmas/{id}` | Remover turma |
| **Alunos** | | |
| GET | `/turmas/{id}/alunos` | Listar alunos da turma |
| POST | `/turmas/{id}/alunos` | Adicionar aluno |
| **Provas** | | |
| GET | `/turmas/{id}/provas` | Listar provas da turma |
| POST | `/provas/upload` | Upload + OCR + classificação |
| GET | `/provas/{id}/questoes` | Listar questões da prova |
| **Gabarito** | | |
| POST | `/provas/{id}/gabarito` | Salvar gabarito |
| GET | `/provas/{id}/gabarito` | Recuperar gabarito |
| **Respostas** | | |
| POST | `/provas/{id}/respostas` | Salvar respostas de um aluno (legado) |
| POST | `/provas/{id}/lancar` | Lançar respostas bulk + calcular acertos |
| POST | `/provas/{id}/ocr-aluno` | OCR de folha de respostas do aluno |
| **Relatórios** | | |
| GET | `/provas/{id}/relatorio/turma` | Desempenho por aluno |
| GET | `/provas/{id}/relatorio/drilldown` | Drilldown área→subárea→bloom |

---

## Endpoints Detalhados

### `GET /`
Verifica se a API está no ar.

**Response 200:**
```json
{
  "status": "ok",
  "app": "EduMap IA API",
  "docs": "/docs"
}
```

---

### `GET /turmas`
Lista todas as turmas cadastradas.

**Response 200:** lista de turmas
```json
[
  {
    "id": 1,
    "nome": "8º B",
    "escola": "E.E. São Paulo",
    "disciplina": "Múltiplas",
    "criado_em": "2026-04-19 10:00:00"
  }
]
```

---

### `POST /turmas`
Cria uma nova turma.

**Request body:**
```json
{
  "nome": "8º B",           // obrigatório
  "escola": "E.E. São Paulo", // opcional
  "disciplina": "Múltiplas"  // opcional
}
```

**Response 201:** objeto da turma criada (mesmo formato do GET)

**Response 422:** campo `nome` ausente

---

### `DELETE /turmas/{turma_id}`
Remove uma turma. Os alunos vinculados são removidos por CASCADE.

**Response 204:** sem body  
**Response 404:** turma não encontrada

---

### `GET /turmas/{turma_id}/alunos`
Lista os alunos de uma turma.

**Response 200:**
```json
[
  {
    "id": 5,
    "nome": "Ana Souza",
    "turma_id": 1,
    "criado_em": "2026-04-19 10:05:00"
  }
]
```

---

### `POST /turmas/{turma_id}/alunos`
Adiciona um aluno à turma.

**Request body:**
```json
{ "nome": "Ana Souza" }
```

**Response 201:**
```json
{ "id": 5, "nome": "Ana Souza", "turma_id": 1 }
```

**Response 404:** turma não encontrada  
**Response 422:** campo `nome` ausente

---

### `GET /turmas/{turma_id}/provas`
Lista as provas associadas à turma.

**Response 200:**
```json
[
  {
    "id": 3,
    "titulo": "prova_matematica.pdf",
    "turma_id": 1,
    "disciplina": "matematica",
    "serie": "8º ano EF",
    "total_questoes": 12,
    "criado_em": "2026-04-19 11:00:00"
  }
]
```

---

### `POST /provas/upload`
**Tipo:** `multipart/form-data`

Faz upload de uma prova, extrai texto via OCR e classifica cada questão automaticamente.

**Form fields:**

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `file` | arquivo | sim | PDF ou imagem (JPG, PNG) |
| `year_level` | string | sim | Série/ano (ex: `"8º ano EF"`) |
| `subject` | string | não | Disciplina (ex: `"Matemática"`) — padrão: `"Detectar automaticamente"` |
| `turma_id` | string | não | ID da turma para vincular a prova |

**Response 200:**
```json
{
  "prova_id": 3,
  "ocr_method": "digital",
  "file_name": "prova_matematica.pdf",
  "year_level": "8º ano EF",
  "subject": "Detectar automaticamente",
  "metadata": {
    "Arquivo": "prova_matematica.pdf",
    "Série / Ano": "8º ano EF",
    "Extração": "Texto digital",
    "Questões": "12"
  },
  "questions": [
    {
      "number": 1,
      "text": "Texto completo da questão...",
      "stem": "Enunciado sem alternativas...",
      "alternatives": ["A) opção a", "B) opção b", "C) opção c", "D) opção d"],
      "area_key": "matematica",
      "area_display": "Matemática",
      "area_confidence": 0.87,
      "subarea_key": "algebra",
      "subarea_label": "Álgebra",
      "bloom_level": 3,
      "bloom_name": "Aplicar",
      "bloom_verb": "calcule",
      "bloom_color": "#F59E0B",
      "bncc_skills": [{"codigo": "EF08MA06"}]
    }
  ]
}
```

**Response 422:** campos obrigatórios ausentes  
**Response 500:** erro ao processar o arquivo (ex: PDF corrompido)

---

### `GET /provas/{prova_id}/questoes`
Lista as questões de uma prova com todas as classificações.

**Response 200:** lista de questões (campos: `id`, `prova_id`, `numero`, `texto`, `stem`, `area_key`, `area_display`, `subarea_key`, `subarea_label`, `bloom_nivel`, `bloom_nome`, `bloom_verbo`, `bncc_skills`)

---

### `POST /provas/{prova_id}/gabarito`
Salva (ou substitui) o gabarito da prova.

**Request body:**
```json
{
  "gabarito": {
    "1": "A",
    "2": "C",
    "3": "B"
  }
}
```

Aceita gabarito parcial (apenas as questões necessárias). Chamadas repetidas substituem o gabarito anterior completamente.

**Response 201:**
```json
{ "ok": true }
```

---

### `GET /provas/{prova_id}/gabarito`
Recupera o gabarito salvo.

**Response 200:**
```json
{
  "1": "A",
  "2": "C",
  "3": "B"
}
```

Retorna dicionário vazio `{}` se nenhum gabarito foi definido.

---

### `POST /provas/{prova_id}/lancar`
Lança respostas de um ou mais alunos em uma única requisição. Calcula os acertos automaticamente comparando com o gabarito salvo.

**Request body:**
```json
{
  "respostas": {
    "5": { "1": "A", "2": "B", "3": "C" },
    "6": { "1": "C", "2": "C", "3": "B" }
  }
}
```

- Chave externa: `str(aluno_id)`
- Chave interna: `str(numero_questao)`
- Valor: alternativa escolhida (case-insensitive)

**Response 201:**
```json
{
  "ok": true,
  "erros": []
}
```

O campo `erros` lista alunos que falharam (ex: aluno inexistente), sem interromper o processamento dos demais.

---

### `POST /provas/{prova_id}/ocr-aluno`
**Tipo:** `multipart/form-data`

Faz OCR de uma folha de respostas física e extrai os pares `numero_questao → alternativa`.

**Form fields:**

| Campo | Tipo | Descrição |
|---|---|---|
| `file` | arquivo | Foto ou scan da folha (JPG, PNG, PDF) |

**Padrões reconhecidos pelo OCR:**
- `1. A` | `1) B` | `1- C` | `1: D`
- `Q1 A` | `Q1: B`
- `01.A`

**Response 200:**
```json
{
  "respostas": { "1": "A", "2": "C", "3": "B" },
  "total_detectado": 3,
  "ocr_method": "ocr",
  "texto_bruto": "Primeiros 800 caracteres extraídos..."
}
```

---

### `GET /provas/{prova_id}/relatorio/turma`
Retorna o desempenho individual de cada aluno que tem respostas registradas para a prova.

**Response 200:**
```json
[
  {
    "aluno": { "id": 5, "nome": "Ana Souza" },
    "total": 12,
    "acertos": 10,
    "percentual": 83,
    "por_bloom": {
      "Lembrar": { "total": 3, "acertos": 3 },
      "Compreender": { "total": 5, "acertos": 4 },
      "Aplicar": { "total": 4, "acertos": 3 }
    },
    "por_area": {
      "Matemática": { "total": 7, "acertos": 6 },
      "Português": { "total": 5, "acertos": 4 }
    },
    "detalhes": [
      {
        "numero": 1,
        "area_display": "Matemática",
        "bloom_nivel": 3,
        "bloom_nome": "Aplicar",
        "correta": 1,
        "resposta": "A",
        "gabarito": "A"
      }
    ]
  }
]
```

---

### `GET /provas/{prova_id}/relatorio/drilldown`
Retorna a estrutura hierárquica completa para o relatório de diagnóstico.

**Response 200:**
```json
{
  "Matemática": {
    "algebra": {
      "label": "Álgebra",
      "bloom": {
        "3": {
          "nome": "Aplicar",
          "pct_turma": 65,
          "alunos": [
            {
              "aluno_id": 6,
              "nome": "Carlos Lima",
              "ok": 1,
              "total": 2,
              "pct": 50
            }
          ]
        }
      }
    }
  }
}
```

- `pct_turma`: percentual médio da turma naquela subárea + nível de Bloom
- `alunos`: lista ordenada por `pct` crescente (pior desempenho primeiro)

---

## Códigos de Status

| Código | Significado |
|---|---|
| 200 | Sucesso (GET) |
| 201 | Criado com sucesso (POST) |
| 204 | Deletado com sucesso (DELETE) |
| 404 | Recurso não encontrado |
| 422 | Payload inválido (campo obrigatório ausente) |
| 500 | Erro interno (ex: falha no OCR) |

---

## CORS

A API aceita requisições de:
- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://localhost:3001`
