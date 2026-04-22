# Área Administrativa — EduMap IA

> Guia completo da interface `/admin`, acessível apenas para usuários com role
> `admin_geral`.

---

## 1. Acesso

### Como virar admin_geral
O **primeiro usuário** registrado na plataforma recebe role `admin_geral`
automaticamente. Todos os demais são criados como `professor` por padrão.

### Entrar na área admin
1. Faça login em https://edumap-frontend-nu.vercel.app
2. Se você for `admin_geral`, a Sidebar mostra o link **⚙️ Administração**
3. Clique para ir em `/admin`

Se qualquer outro usuário (professor/admin_escolar) acessar a URL direta
`/admin`, é redirecionado para `/`. A API também valida a role no backend
(status 403 se não for admin_geral).

---

## 2. Estrutura da Área Admin

`/admin` tem **4 abas**:

| Aba | Propósito |
|-----|-----------|
| 👥 **Usuários** | Visualizar todos os usuários cadastrados |
| 🏫 **Escolas** | Agregado de escolas com contagem de usuários e turmas |
| 📄 **Provas** | Listar e deletar provas enviadas |
| 🗺️ **Taxonomia** | Visualizar, editar, adicionar e deletar nós taxonômicos |

---

## 3. Aba 👥 Usuários

### O que mostra
Tabela com todos os usuários do sistema:
- **Nome**
- **E-mail**
- **Role** — badge colorido:
  - 🔴 `admin_geral` — acesso total
  - 🟠 `admin_escolar` — futura: vê só da sua escola
  - 🔵 `professor` — vê só suas próprias turmas
- **Escola** (opcional, preenchido no cadastro)
- **Criado em** — data do cadastro

### Endpoint equivalente
```
GET /admin/usuarios
```

---

## 4. Aba 🏫 Escolas

### O que mostra
Agregado automático a partir dos campos `escola` de usuários e turmas:

| Escola | Usuários | Turmas |
|--------|----------|--------|
| E.E. João da Silva | 3 | 5 |
| E.E. Maria Oliveira | 1 | 2 |

### Como são criadas
Escolas **não são cadastradas manualmente** — elas são inferidas dinamicamente
a partir do que os usuários/professores digitam no campo "Escola" ao criar
conta ou criar turma.

Se quiser uniformizar nomes de escolas, oriente os professores a usar o mesmo
nome exato.

### Endpoint equivalente
```
GET /admin/escolas
```

---

## 5. Aba 📄 Provas

### O que mostra
Todas as provas enviadas por todos os professores, ordenadas da mais recente
para a mais antiga:

- **Título** — nome do arquivo ou título informado no upload
- **Turma / Escola**
- **Série / Ano**
- **Total de questões** detectadas pelo OCR
- **Data** do upload
- **Ação**: botão 🗑️ Deletar

### Deletar uma prova
Ao clicar em "Deletar":
1. Confirmação explícita na tela
2. A prova é removida do banco
3. **Em cascata:** todas as questões, respostas de alunos e gabarito são
   apagados também (via FK `ON DELETE CASCADE`)
4. A ação **não pode ser desfeita**

### Quando usar
- Prova foi enviada com a matéria errada selecionada
- O OCR reconheceu o cabeçalho como questão (já corrigido, mas ficou no banco)
- Dados de teste/demo que você quer limpar antes de usar em produção

### Endpoints equivalentes
```
GET    /admin/provas
DELETE /admin/provas/{id}
```

---

## 6. Aba 🗺️ Taxonomia

A mais rica — permite gerenciar toda a árvore de classificação taxonômica.

### 6.1 Estatísticas (topo da aba)
Cards com:
- Total de nós na etapa atual
- Matérias cadastradas
- Níveis de profundidade usados
- Nível máximo alcançado

### 6.2 Ações em massa

**🔄 Re-executar seed**
Roda o seed a partir do `data/taxonomia.json` no servidor. Usa UPSERT —
atualiza nós existentes e adiciona novos, sem apagar nada.

*Quando usar:* depois de um `git pull` que trouxe mudanças no JSON; em uma
primeira instalação.

**📤 Upload de novo JSON**
Escolhe um arquivo JSON do seu computador e envia para o servidor. O backend
faz UPSERT (não deleta nós ausentes).

*Quando usar:* importar uma taxonomia editada offline; migrar de outra
instalação.

### 6.3 Visualização e edição da árvore

Um seletor permite escolher a matéria. A árvore aparece abaixo, colapsável.

**Cada nó mostra:**
- Seta ▶/▼ para expandir/colapsar (se tem filhos)
- Label (nome legível)
- Palavras-chave (em itálico, à direita)
- Nível (ex: "nv 5")

**Ao passar o mouse sobre um nó, aparecem 3 botões:**

#### ✏️ Editar
Abre um formulário inline com:
- Campo de texto para o **label**
- Campo de texto para **palavras-chave** (separadas por vírgula)
- Botões Salvar / Cancelar

Salvar envia `PUT /admin/taxonomia/no/{id}` e recarrega a árvore.

#### ➕ Adicionar filho
Abre um formulário inline com:
- **Slug** — identificador único do novo nó (alfanumérico + underscore, ex: `equilatero`)
- **Label** — nome legível (ex: "Triângulo Equilátero")
- **Palavras-chave** — termos para o classificador (ex: "equilátero, três lados iguais")

O código final do novo nó é construído automaticamente:
`<codigo_do_pai>.<slug>` → ex: `ef2.matematica.geometria.figuras_planas.poligonos.triangulos.equilatero`

Salvar envia `POST /admin/taxonomia/no` e recarrega.

#### 🗑️ Deletar
Pede confirmação e, se o nó tem filhos, avisa que eles também serão apagados.
Remove o nó (e descendentes via `ON DELETE CASCADE`).

Envia `DELETE /admin/taxonomia/no/{id}` e recarrega.

### 6.4 Tuning do classificador

Quando uma questão é classificada no nó errado:
1. Clique em ✏️ no nó que deveria ter ganhado
2. Adicione palavras-chave mais específicas
3. Salve

Próximas provas enviadas usam a nova versão. Provas **já salvas** mantêm o
`taxonomia_codigo` antigo (a classificação é feita no upload, não no relatório).
Para reclassificar, delete a prova e envie de novo.

### 6.5 Endpoints equivalentes

| Método | Endpoint |
|--------|----------|
| `GET` | `/admin/taxonomia/stats` |
| `GET` | `/admin/taxonomia/materias` |
| `GET` | `/admin/taxonomia/nos?materia=matematica` |
| `POST` | `/admin/taxonomia/classificar` (teste sem salvar) |
| `POST` | `/admin/seed-taxonomia` (roda seed do JSON em disco) |
| `POST` | `/admin/taxonomia/import-json` (body: JSON completo) |
| `POST` | `/admin/taxonomia/no` (novo filho) |
| `PUT` | `/admin/taxonomia/no/{id}` (editar) |
| `DELETE` | `/admin/taxonomia/no/{id}` (apagar + cascade) |

---

## 7. Fluxo Recomendado de Uso

### Primeira instalação
1. Deploy do backend e frontend
2. Acesse o frontend — vai para `/register`
3. Crie sua conta → vira `admin_geral`
4. Acesse `/admin` → Taxonomia → **Re-executar seed** (popula os 282 nós do JSON)
5. Sistema pronto para uso

### Manutenção diária
1. Professores criam suas turmas e fazem uploads (`/turmas`, `/analisar`)
2. Você, como admin, monitora em `/admin`:
   - Quantos usuários / escolas
   - Provas enviadas (pode deletar spam/testes)
3. Quando o classificador errar, vá em Taxonomia e tune palavras-chave

### Exportar taxonomia para backup
Use o Swagger em https://edumap-ia.onrender.com/docs:
1. Autentique com seu JWT
2. Chame `GET /admin/taxonomia/nos?etapa=ef2` — retorna o flat JSON
3. Salve o resultado como backup local ou commit no git

(Um endpoint dedicado de export pode ser adicionado no futuro.)

---

## 8. Segurança

- **Backend:** todo endpoint `/admin/*` valida role via `_require_admin_geral()`
  e retorna 403 se o usuário não for admin_geral
- **Frontend:** a página `/admin` faz `router.replace("/")` se o usuário
  logado não tiver role `admin_geral`
- **JWT:** tokens expiram em 7 dias; chamadas 401 redirecionam automaticamente
  para `/login`
