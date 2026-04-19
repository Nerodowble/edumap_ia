# EduMap IA — Guia de Testes

---

## Instalação

```bash
cd edumap_ia
C:\Users\willi\anaconda3\python.exe -m pip install pytest httpx starlette
```

---

## Executar os Testes

```bash
# Todos os testes (86 testes de integração da API)
C:\Users\willi\anaconda3\Scripts\pytest tests/ -v

# Apenas testes da API
C:\Users\willi\anaconda3\Scripts\pytest tests/test_api.py -v

# Apenas classificadores (sem servidor, muito rápido)
C:\Users\willi\anaconda3\Scripts\pytest tests/test_classificadores.py -v

# Uma classe específica
C:\Users\willi\anaconda3\Scripts\pytest tests/test_api.py::TestGabarito -v

# Um teste específico
C:\Users\willi\anaconda3\Scripts\pytest tests/test_api.py::TestLancar::test_lancar_todos_corretos -v

# Com output de print()
C:\Users\willi\anaconda3\Scripts\pytest tests/test_api.py -v -s
```

---

## Arquitetura dos Testes

### `tests/conftest.py` — Fixtures Compartilhadas

Configura o ambiente de teste isolado:

1. **Banco isolado:** cria um DB SQLite temporário (`/tmp/edumap_test_XXXXX/test_edumap.db`) e substitui o `DB_PATH` antes de qualquer import da API
2. **TestClient:** usa `starlette.testclient.TestClient` para fazer requisições HTTP in-process (sem servidor real)

**Fixtures de sessão** (criadas uma única vez para toda a suíte):

| Fixture | Descrição |
|---|---|
| `client` | TestClient da API |
| `prova_pdf` | Caminho para `provas_exemplo/prova_exemplo_8ano.pdf` (gera se não existir) |
| `turma_criada` | Turma "8ºB Teste" criada via API |
| `aluno_criado` | Aluno "Aluno Teste" na turma criada |
| `prova_enviada` | Prova do PDF de exemplo, enviada via `/provas/upload` |
| `prova_com_gabarito` | Segunda prova + gabarito alternando A/B/C/D |
| `aluno_gabarito` | Aluno dedicado para testes de lançamento |
| `aluno_gabarito2` | Segundo aluno para testes multi-aluno |

### `tests/test_api.py` — Testes de Integração

86 testes organizados em 9 classes:

| Classe | Nº de testes | O que verifica |
|---|---|---|
| `TestRoot` | 3 | Endpoint `/`, `/docs`, `/openapi.json` |
| `TestTurmas` | 8 | CRUD turmas, validação, performance |
| `TestAlunos` | 5 | CRUD alunos, validação, turma inexistente |
| `TestUpload` | 9 | Upload PDF, campos retornados, Bloom, área, performance |
| `TestProvas` | 3 | Listagem, questões, performance |
| `TestRelatorios` | 7 | Salvar respostas, relatório turma, drilldown, idempotência |
| `TestGabarito` | 9 | Salvar/recuperar gabarito, normalização maiúsculas, duplicatas, performance |
| `TestLancar` | 11 | Acertos corretos, todos certos/errados, case-insensitive, bulk, idempotência, performance |
| `TestOcrAluno` | 5 | OCR de folha, estrutura da resposta, performance |
| `TestValidacaoEdgeCases` | 15 | Unicode, caracteres especiais, nomes longos, alternativas inválidas, aluno inexistente, invariantes matemáticos |
| `TestFluxoCompleto` | 5 | Fluxo end-to-end completo, drilldown, cascade delete, recalculo de gabarito |
| `TestStress` | 6 | 20 turmas sequenciais, 30 alunos, 100 GETs, 10 drilldowns, gabarito 10x, 10 alunos em uma requisição |

### `tests/test_classificadores.py`

Testes unitários dos módulos de classificação (sem banco de dados):
- `classify_area()` com textos de diferentes disciplinas
- `classify_bloom()` com diferentes verbos
- `segment_questions()` com diferentes formatos de numeração

---

## Detalhes por Classe

### TestGabarito

```python
test_get_gabarito_vazio_retorna_dict        # Prova sem gabarito → {}
test_salvar_gabarito_retorna_201            # POST retorna 201
test_get_gabarito_retorna_dados_corretos    # Valores salvos são recuperados corretamente
test_gabarito_normaliza_para_uppercase      # "c" → "C" ao salvar
test_gabarito_sobrescreve_sem_duplicar      # Salvar 2x não duplica
test_gabarito_parcial_aceito                # Gabarito com < todas as questões
test_gabarito_sem_body_retorna_422          # Payload vazio → 422
test_performance_salvar_gabarito            # < 500ms
test_performance_get_gabarito               # < 200ms
```

### TestLancar

```python
test_lancar_retorna_201                     # POST básico funciona
test_lancar_calcula_acertos_corretamente    # Math exata: metade correta → metade de acertos
test_lancar_todos_corretos                  # 100% acertos
test_lancar_todos_errados                   # 0% acertos
test_lancar_alternativas_case_insensitive   # "a" == "A" → acerto
test_lancar_questao_inexistente_ignorada    # Número inválido é ignorado silenciosamente
test_lancar_multiplos_alunos_um_request    # 5 alunos em um POST, < 2s
test_lancar_idempotente                     # Lançar 2x não duplica respostas
test_lancar_sem_respostas_retorna_201       # Payload vazio é aceito
test_lancar_sem_body_retorna_422            # Sem body → 422
test_performance_lancar                     # < 500ms
```

### TestValidacaoEdgeCases

Verifica invariantes matemáticos do banco:
- `percentual == round(acertos / total * 100)` para todo aluno
- `acertos <= total` sempre
- `pct_turma` no drilldown sempre entre 0 e 100
- Alunos no drilldown ordenados por pct crescente
- Soma de `por_bloom.total` == `total` do aluno
- Soma de `por_bloom.acertos` == `acertos` do aluno

### TestFluxoCompleto

Simula o fluxo real de um professor:
1. Criar turma + 3 alunos
2. Upload da prova
3. Definir gabarito (todos = "A")
4. Lançar: Ana tudo certo, Bruno metade, Carla tudo errado
5. Verificar: Ana 100%, Carla 0%, Bruno ~50%

### TestStress

| Teste | Limite |
|---|---|
| 20 POSTs `/turmas` | P95 < 500ms |
| 30 alunos em uma turma | Todos aparecem na listagem |
| 100 GETs `/turmas` | P95 < 200ms |
| 10 GETs drilldown | P95 < 1s |
| Gabarito salvo 10x | Média < 300ms |
| 10 alunos em `/lancar` | < 3s |

---

## Notas Importantes

### Banco Isolado

Os testes **nunca tocam** o banco de produção (`data/edumap.db`). Um banco temporário é criado por sessão de teste e descartado no final.

### Duplicação de Números de Questão

O PDF de exemplo pode gerar um marcador de questão extra (provavelmente do cabeçalho da página), resultando em 13 "chunks" onde dois têm o mesmo número. Isso é tratado nos testes de fluxo completo com deduplicação explícita:

```python
seen: set = set()
questions = [q for q in questions if not (q["number"] in seen or seen.add(q["number"]))]
```

### Idempotência

`POST /provas/{id}/lancar` usa `ON CONFLICT(aluno_id, questao_id) DO UPDATE` — pode ser chamado quantas vezes quiser; a última chamada prevalece.

`POST /provas/{id}/gabarito` faz DELETE + INSERT — substitui completamente.

---

## Cobertura Estimada

| Área | Cobertura |
|---|---|
| Endpoints REST | ~100% (todos os endpoints têm ao menos 1 teste) |
| Códigos de status | 200, 201, 204, 404, 422, 500 |
| Edge cases | Unicode, strings longas, payloads vazios, IDs inválidos |
| Performance | Limites definidos para cada endpoint crítico |
| Stress | Volumes de 5–100 operações repetidas |
| Invariantes | Matemática dos relatórios verificada automaticamente |
