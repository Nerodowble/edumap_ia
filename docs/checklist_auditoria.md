# Checklist de correções — Auditoria EduMap

> **Levantamento:** 2026-09-25, 22:44 (horário de Brasília)
> **Base auditada:** backend `edumap_ia` @ `da6a67c` · frontend `edumap_frontend` @ `a9920d3`
> **Auditores:** 3 agentes (backend, frontend, UI/UX). Leitura de código, testes locais e verificação só leitura em produção.
>
> **Última atualização:** 2026-09-26 — backend em produção @ `2e9b49a`, frontend @ `46d667d`; 200 testes no backend.
>
> Marque `[x]` ao concluir e anote o commit ao lado. `[~]` = parcial/em andamento. Referências `arquivo:linha` valem para os commits acima e podem ter se deslocado.

---

## Como retomar (para uma nova sessão do Claude)

1. Leia este arquivo inteiro e procure o primeiro item `[ ]` da seção **Ordem de execução**.
2. Repositórios:
   - Backend: `C:\Users\willi\OneDrive\Documentos\pessoal\curso_extensao\edumap_ia` (FastAPI)
   - Frontend: `C:\Users\willi\OneDrive\Documentos\pessoal\curso_extensao\edumap_frontend` (Next.js 14)
3. Produção:
   - Backend no Render free (`https://edumap-ia.onrender.com`), com deploy automático por push na `main`
   - Banco no **Neon** (Postgres). O `DATABASE_URL` fica só no painel do Render, nunca no código.
   - Frontend no Vercel (`https://edumap-frontend-nu.vercel.app`), com deploy automático por push
4. Testes do backend:
   - O Python do anaconda não tem `python-jose`, então use uma venv com `pip install -r requirements.txt`.
   - Comando: `python -m pytest tests/ -q`, com 137 testes passando em 2026-09-25.
   - **Atenção:** `tests/conftest.py` define `SKIP_AUTH=true`, então os testes atuais não cobrem autenticação.
5. Testes do frontend: `npx tsc --noEmit` e `npm run build` (o ESLint não está configurado).
6. Regras:
   - Não commitar `data/edumap.db`, `__pycache__` nem segredos.
   - Mostrar ao usuário antes de fazer push.
   - Fim da mensagem de commit: `Co-Authored-By: claude-flow <ruv@ruv.net>`.

---

## Já resolvido

- [x] **Backend fora do ar:** o Postgres free do Render expirou e foi apagado. O banco foi migrado para o Neon (ação do usuário no painel, 2026-09-25) e todos os dados antigos de produção foram perdidos.
- [x] **Boot lento:** o auto-seed da taxonomia (3.859 nós, cerca de 7.700 queries) rodava antes de abrir a porta. Agora roda em thread e só reimporta JSON alterado (tabela `seed_hashes`). Commit `6a54aac`.
- [x] **Restart apagava edições do admin na taxonomia:** resolvido pelo mesmo commit `6a54aac`.
- [x] Conta `admin_geral` do usuário criada no banco novo, e taxonomia com as 7 etapas carregadas.
- [x] `SECRET_KEY` confirmada pelo usuário no Render (2026-09-25).

---

## Ordem de execução

1. ~~C1 (convites)~~ ✅
2. ~~C2, C3, C4~~ ✅ e testes com autenticação real (T1 — iniciado: test_auth_convites.py + test_isolamento.py)
3. ~~C5, C6~~ ✅ (ver pendências de confirmação nos itens)
4. ~~C7, C8, A1, A2, A4, A5, A6~~ ✅ (E2E em navegador: 16 verificações)
5. ~~A3, A7, A8, A17, M9~~ ✅ (E2E /criar-prova: 7 verificações)
6. ~~A9, A10, A11, A13~~ ✅ (em produção)
7. ~~A14, N1~~ ✅
8. **▶ RETOMAR AQUI:** A15, A16, depois os itens Médio e Baixo
9. Melhoria pedida: N2 (detalhar com o usuário antes)

---

## 🔴 Crítico

- [x] **C1 — Cadastro aberto a qualquer pessoa: cadastro por convite** *(aprovado pelo usuário em 2026-09-25)* — feito (ver commits `feat: cadastro por convite` nos dois repos)
  - **Backend:**
    - [x] Tabela `convites` (`id`, `codigo` UNIQUE, `role`, `escola`, `usos_max` padrão 1, `usos`, `expira_em` padrão +7 dias, `criado_por`, `ativo`, `criado_em`) nos schemas PG e SQLite de `src/database/db.py`
    - [x] Módulo de acesso (ex.: `src/database/convites.py`): gerar, listar, desativar, validar e consumir. O consumo precisa ser atômico, sem corrida no último uso.
    - [x] O código segue o formato do PIN, sem caracteres ambíguos, ex.: `EDU-7K4P-Q9XM` (ver o gerador de PIN em `api.py`, perto da linha 1021)
    - [x] `POST /auth/register` (`api.py:350`) exige `codigo_convite`, e `role`/`escola` vêm do convite. Exceção: banco sem nenhum usuário, em que o primeiro vira `admin_geral` sem convite.
    - [x] Endpoints:
      - `POST /admin/convites`
      - `GET /admin/convites`
      - `DELETE /admin/convites/{id}` (desativa)
      - `GET /convites/{codigo}` (validação pública: devolve só se é válido + escola, sem outros dados)
    - [x] Permissões:
      - `admin_geral` gera qualquer role e escola
      - `admin_escolar` gera só `professor` para a própria escola
      - `professor` não gera
    - [x] Normalizar o e-mail com `lower().strip()` e recusar senha vazia (ver A12)
  - **Frontend:**
    - [x] `/register` (`src/app/register/page.tsx`): campo "Código de convite", preenchido por `?convite=` na URL
    - [x] Remover o texto "O primeiro usuário registrado torna-se administrador geral." (`register/page.tsx:100`)
    - [x] Painel admin: aba **Convites** (gerar com role, escola, usos e validade; listar com usos e expiração; copiar link; desativar)
    - [x] `lib/api.ts` e `lib/types.ts`: funções e tipos novos
  - **Testes:**
    - [x] Cadastro sem código, com código inválido, expirado ou esgotado, e com código válido
    - [x] Role e escola vindas do convite
    - [x] Permissões por perfil
  - O login do aluno (nome + R.A. + PIN) **não muda**.

- [x] **C2 — IDOR em questões:** *(corrigido; tests/test_isolamento.py)* um professor edita e apaga questões e gabarito de outro professor
  - **Onde:** `api.py:845`, `:1241`, `:1282`. O código só confere o acesso à prova da URL, nunca se `questao_id` pertence a ela.
  - **Correção:** carregar a questão e exigir `q.prova_id == prova_id`, senão 404. Aplicar também em `db.atualizar_tipo_questao`, `atualizar_questao_manual` e `deletar_questao` (`WHERE id=? AND prova_id=?`).

- [x] **C3 — IDOR em respostas, com vazamento de alunos de outras escolas** *(corrigido; `correta` recalculado no servidor)*
  - **Onde:** `api.py:905` e `:931` aceitam qualquer `aluno_id`, e o relatório passa a mostrar nome, RA e turma. Em `api.py:909` o próprio cliente informa `correta`.
  - **Correção:** validar `aluno.turma_id == prova.turma_id` e recalcular `correta` no servidor.

- [x] **C4 — Aluno responde questão de outra prova** *(corrigido; o bloqueio por status da prova já existia no endpoint)*
  - **Onde:** `api.py:1430` e `db.py:1438` (`salvar_resposta_unica` sem filtro por prova). Isso passa por cima de PIN, turma e encerramento.
  - **Correção:** `WHERE id=? AND prova_id=?` e rejeitar se a prova não estiver publicada.

- [x] **C5 — `SECRET_KEY` com fallback hardcoded** *(código pronto: com DATABASE_URL e sem SECRET_KEY o boot falha; fallback só local. **Push só após o usuário confirmar a variável no Render**)*
  - **Onde:** `api.py:100` (`"edumap-dev-secret-change-in-prod"`). Com essa chave dá para forjar um token de admin.
  - **Correção:** falhar no boot se a variável estiver ausente, exceto com `SKIP_AUTH` ou em ambiente de teste.

- [x] **C6 — `data/edumap.db` versionado num repositório público** *(removido do índice com `git rm --cached`; **limpeza do histórico pendente de decisão do usuário** — perguntar se os dados eram reais ou de teste)*, com 40 alunos e hashes de senha
  - **Correção:** `git rm --cached data/edumap.db`, colocar `data/*.db` no `.gitignore` e avaliar a limpeza do histórico (git filter-repo). A limpeza é destrutiva: **confirmar com o usuário antes**.

- [x] **C7 — PIN ou login errado desloga o aluno com "Sessão expirada"** *(PIN errado → 422; turma checada antes do PIN; front só limpa token em 401 de sessão)*
  - **Onde:** backend `api.py:1382` (401 no PIN errado) e `/aluno/auth`. Frontend `lib/api.ts:453-458` (todo 401 apaga o token).
  - **Correção:** PIN e credencial errados devolvem 400/422, ou o front só limpa o token quando o erro for de token. Mostrar "PIN incorreto" (`aluno/provas/page.tsx:48`) e "Nome ou R.A. incorretos" (`aluno/page.tsx:37`).

- [x] **C8 — Falha de rede na prova faz o aluno perder a resposta** *(fila local `lib/useFilaRespostas.ts` com reenvio a cada 5s e no evento online; finalizar só com fila vazia; validado em E2E com rede desligada)*
  - **Onde:** `aluno/prova/[id]/page.tsx:93-97`. Aparece o erro cru `[500] /aluno/...` ou "Failed to fetch", sem nova tentativa, e o erro continua na tela mesmo depois de um sucesso.
  - **Correção:** salvar local primeiro, com fila de reenvio, mensagem clara ("Sem conexão — será enviada quando voltar") e limpar o erro depois do sucesso.

---

## 🟠 Alto

**Notas e correção**
- [x] **A1 — Nota inflada:** *(relatório usa todas as questões; campo `respondidas`)* o percentual é calculado sobre as respondidas (1 de 2 certas dá 100%). `db.py:779-818`. Usar o total de questões da prova.
- [x] **A2 — Trocar o gabarito não recalcula `respostas.correta`:** *(`_recalcular_corretas`)* `db.py:1122` e `:708`. Rodar um UPDATE de recálculo em `salvar_gabarito` e em `atualizar_questao_manual`.
- [x] **A3 — Gabarito deslocado:** *(vazias no meio recusadas; remover alternativa reajusta a letra)* alternativa vazia no meio, ou alternativa removida, troca a letra correta sem aviso. `criar-prova/page.tsx:147-153` e `:473`.

**Prova do aluno**
- [x] **A4 — Respostas locais vazam entre alunos no mesmo computador:** *(chaves com id do aluno; servidor devolve `respostas`)* a chave `edumap_prova_{id}_*` não inclui o aluno e não é limpa no logout. `aluno/prova/[id]/page.tsx:35-57` e `alunoAuth.ts:16-20`. Além disso, restaurar as respostas **do servidor** (backend devolver as respostas salvas em `/aluno/provas/{id}/questoes`).
- [x] **A5 — Tempo limite decorativo:** *(contagem regressiva, aviso nos 5 min, envio automático; servidor recusa resposta após limite + 60s)* não há contagem regressiva, aviso nem envio automático no front, e nada bloqueia no servidor. `aluno/prova/[id]/page.tsx:62-70`.
- [x] **A6 — Login de aluno só com o nome** enviando `ra="  "`: `db.py:456-463`. Validar depois do strip e exigir RA no cadastro.

**Criar prova**
- [x] **A7 — "Voltar" + "Continuar" cria uma segunda prova:** *(novo `PUT /provas/{id}` para rascunho; turma obrigatória no passo 1)* `criar-prova/page.tsx:105-125` e `:535`. Atualizar a prova existente quando `provaId` já existe e validar a turma no passo 1.
- [x] **A8 — Rascunho sem saída:** *(`/criar-prova?id=` + link em Turmas, só provas manuais)* não há como retomar, editar ou publicar. Link "Continuar editando" (`/criar-prova?id=`).

**Classificação e taxonomia**
- [x] **A9 — Classificação ignora a etapa e a disciplina:** *(label da disciplina resolvido via raiz da taxonomia filtrada pela etapa da turma; etapa repassada ao classificador em criar/editar/reclassificar/upload; fallback com ORDER BY)*
  - 19 labels enviados pelo front não existem no `SUBJECT_TO_KEY` (`api.py:1147`);
  - `classify_taxonomia` não recebe `turma.etapa`;
  - o fallback em `taxonomia_classifier.py:111-115` usa `LIMIT 1` sem ORDER BY, com 7 slugs repetidos entre cursos.
  - **Correção:** guardar o slug da matéria e passar a etapa.

**Upload e segmentação**
- [x] **A10 — Upload devolve 500 para erro do cliente e checa acesso depois do OCR:** *(`_ler_upload`: extensão 415, tamanho 413 (MAX_UPLOAD_MB=15), vazio 422; turma validada antes do OCR)* `api.py:737-833`. Validar antes do `try`, re-levantar `HTTPException` e limitar tamanho e extensão.
- [x] **A11 — Segmentador perde questões:** *(marcador por extenso vale sozinho na linha; numeração fora de sequência é conteúdo; tests/test_segmenter.py)* "Questão N" sozinha na linha é rejeitada (`segmenter.py:30`), e uma lista numerada no enunciado substitui as questões reais na deduplicação (`segmenter.py:125-130`).

**Contrato front↔back**
- [x] **A12 — Exclusões mostram erro mesmo quando deram certo:** *(corrigido junto com C1: `req()` trata 204)* `req()` faz `res.json()` numa resposta 204. `lib/api.ts:25-37`. Afeta `deleteTurma`, `deleteAluno`, `deleteQuestao` e `adminDeleteUsuario`.
- [x] **A13 — Editar aluno apaga CPF e data de nascimento:** *(campos omitidos mantêm o valor)* o front manda só `{nome, ra}` (`turmas/page.tsx:436`) e o backend sobrescreve os dois campos com "" (`api.py:282` e `db.py:482`). Fazer um update parcial.

**UX**
- [x] **A14 — Fluxo de prova online invisível:** *(GET /provas/online + página `/provas` "Minhas provas online"; Sidebar em seções Prova online / Prova impressa / Resultados; Home com os dois caminhos; FlowBanner rotulado; E2E com prints desktop e 375px)*
- [ ] **A15 — Contraste abaixo do WCAG AA:** `PctBadge` e cores de Bloom (`BloomBadge.tsx:24`, `criar-prova:386`). Usar tons 700 e rótulo em texto.
- [ ] **A16 — `/aplicar` no celular:** nomes cortados, botão "Liberar" de 12px, "Encerrar" colado em "Copiar PIN", nenhum aviso quando o polling falha e a URL aparece relativa. Adicionar URL completa + QR.
- [x] **A17 — `/turmas` no celular:** os botões editar e remover do aluno usam `opacity-0 group-hover` e ficam invisíveis no toque (`turmas/page.tsx:586`, `:594`).

---

## 🟡 Médio

**Segurança e acesso**
- [ ] M1 — Sem rate limit em `/auth/login`, `/aluno/auth` e no PIN (262.144 combinações, `api.py:1021`).
- [ ] M2 — Fingerprint frágil:
  - usa o primeiro valor de X-Forwarded-For, que o cliente controla (`api.py:1005`);
  - a troca de Wi-Fi para 4G gera 409;
  - depois de `liberar-relogin`, `fingerprint=NULL` deixa qualquer dispositivo responder.
- [ ] M3 — Prova editável durante e depois da aplicação:
  - dá para republicar uma prova encerrada;
  - aceita gabarito `"Z"`, tipo inválido e `tempo_limite_min` negativo;
  - aceita a resposta `"ZZZZ"` do aluno.
- [ ] M4 — `admin_escolar` com escola vazia acessa turmas de professores sem escola (`db.py:620-621`).
- [ ] M5 — Excluir usuário ou escola deixa provas órfãs: a FK `provas.turma_id` é SET NULL (`usuarios.py:128-151`, `db.py:53`).
- [ ] M6 — Cadastro: e-mail diferencia maiúsculas, senha vazia é aceita, nome de turma vazio e etapa inexistente são aceitos. Parte disso entra em C1.
- [ ] M7 — Nome acentuado não loga no SQLite: o `LOWER()` do SQLite só trata ASCII (`db.py:462`). Só afeta o ambiente local.

**Formulários e navegação**
- [ ] M8 — 41 `<label>` sem `htmlFor`/`id` (login, register, criar-prova, turmas, lancar, relatorio). Só `/aluno` está correto.
- [x] M9 — Scroll horizontal em `/criar-prova` a 360px: o stepper corta "Publicar".
- [ ] M10 — `/analisar`: h1 "EduMap", "arraste o arquivo" sem `onDrop`, área de upload inacessível por teclado, jargão "Extração: TESSERACT".
- [ ] M11 — Sem página inicial pública (`/` redireciona para `/login`) e sem "Esqueci minha senha".

**Mensagens e textos**
- [ ] M12 — Erros de backend aparecem crus nos toasts (`[status] /path: {json}`, `lib/api.ts:34`). Criar um helper de erro amigável.
- [ ] M13 — Feedback inconsistente: toast, `alert()` e `confirm()` misturados, com "Deletar" e "Apagar" alternados.
- [ ] M14 — Erro de digitação "questãoões" (`analisar/page.tsx`, TabRecomendacoes). A etapa aparece como slug cru (`turmas:466`) e as datas em ISO.

**Telas específicas**
- [ ] M15 — `/lancar`:
  - não avisa sobre alterações não salvas;
  - certo e errado aparecem só por cor;
  - o aviso "sem gabarito" manda ir em Analisar mesmo quando a prova é online.
- [~] M16 — *(erro de rede com botão Tentar de novo feito; placeholder ETEC pendente)* `/aluno/provas`: erro de rede aparece como "Nenhuma prova em aberto", sem botão de atualizar, e o placeholder "O número que a ETEC te deu" exclui outras escolas.
- [ ] M17 — Modais (PIN, Finalizar) sem `role="dialog"`, sem foco preso e sem fechar com Esc.

---

## ⚪ Baixo

**Backend**
- [ ] B1 — `/docs`, `/redoc` e `/openapi.json` públicos em produção. Desligar via variável de ambiente.
- [ ] B2 — Endpoints de leitura `/admin/taxonomia/*` não exigem admin.
- [ ] B3 — `_score` não bate com a docstring (`taxonomia_classifier.py:96`).
- [ ] B4 — PG: o rollback de um ALTER que falhe em `init_schema` (`db.py:348-351`) desfaz também os CREATEs pendentes.
- [x] B5 — *(timer usa `segundos_decorridos` do servidor)* Datas: o SQLite grava sem fuso e o PG em ISO. Isso gera NaN no timer do aluno no Safari.
- [ ] B6 — N+1 em `relatorio_turma`. O relatório expõe CPF e data de nascimento, e o monitor expõe IP e User-Agent.

**Frontend**
- [ ] B7 — ESLint não configurado: `next lint` fica esperando um prompt. Com a config padrão aparecem 6 erros e 3 warnings.
- [ ] B8 — Sem CSP no Vercel, com o JWT guardado em `localStorage`.
- [ ] B9 — Títulos de página genéricos ("EduMap"), alvos de toque pequenos em login e register, emojis misturados com ícones, e termos inconsistentes (prova/avaliação, disciplina/matéria).

**Repositório**
- [~] B10 — *(`__pycache__` removidos do índice)* Arquivo vazio `Dict[str` e `test_report.pdf` soltos na raiz. `__pycache__/*.pyc` versionados.

---

## 🧪 Testes

- [ ] **T1 — Suite com autenticação real:** hoje tudo roda com `SKIP_AUTH=true`. Cobrir:
  - login e registro;
  - convites;
  - 403 entre professores e escopo do `admin_escolar`;
  - os IDORs de C2–C4.
- [ ] T2 — Cobertura do fluxo online: `/provas/manual`, CRUD de questões, publicar e encerrar, monitor, liberar-relogin, `/aluno/*` completo (PIN, fingerprint, finalizar, responder depois de finalizar).
- [ ] T3 — `/turmas/{id}/contexto`, `/etapas`, admin (usuários, escolas, reclassificar, import de taxonomia).
- [ ] T4 — Casos de regressão:
  - nota com questões em branco (A1);
  - troca de gabarito (A2; o teste atual passa porque relança as respostas);
  - segmentador com "Questão N" em linha própria;
  - V/F na prova online.

---

## ✨ Melhorias pedidas pelo usuário

- [x] **N1 — Rótulo da validade do convite** *(pedido em 2026-09-26; fazer junto com o A14)*
  - A validade do convite é só o **prazo para usar o código e criar a conta** (`expira_em`, checado em `convites.registrar_com_convite`). A conta criada não expira.
  - Trocar o rótulo "Validade (dias)" por **"Prazo para usar o convite (dias)"** em `src/components/admin/ConvitesPanel.tsx`, e a coluna "Expira em" por "Prazo do convite".

- [ ] **N2 — Acesso temporário (conta com data de expiração)** *(pedido em 2026-09-26; funcionalidade nova, a detalhar com o usuário)*
  - Caso de uso: professor de escola parceira que só pode usar o sistema por um período (ex.: até o fim do semestre).
  - Proposta inicial (confirmar com o usuário antes de implementar):
    - coluna `acesso_ate` (texto ISO UTC, opcional) em `usuarios`, nos schemas PG e SQLite (`src/database/db.py`);
    - convite com campo opcional "Acesso válido até" → copiado para o usuário no cadastro;
    - `get_current_user` e `/auth/login` recusam (403 "Seu acesso expirou em DD/MM/AAAA. Fale com o administrador.") quando `acesso_ate` já passou; `admin_geral` nunca expira;
    - Admin → Usuários: mostrar e editar a data (prorrogar/remover); lista destacando contas expiradas;
    - dados do professor (turmas, provas, relatórios) continuam guardados após a expiração.
  - Decisões em aberto: o admin_escolar pode definir/prorrogar? avisar o professor X dias antes? o que acontece com provas publicadas quando a conta expira?
  - Testes: login/rota protegida antes e depois da data, admin_geral isento, prorrogação.

---

## Pendências operacionais (usuário)

- [ ] Configurar um monitor gratuito (ex.: UptimeRobot) chamando `https://edumap-ia.onrender.com/admin/version` a cada 10 min, para evitar o cold start do Render.
- [ ] Atualizar a documentação (`README.md`, `docs/arquitetura.md`, `docs/deploy.md`): ainda descreve SQLite puro e não fala de Neon, prova online nem convites.
