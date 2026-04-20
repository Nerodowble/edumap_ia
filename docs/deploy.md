# EduMap IA — Guia de Deploy e Infraestrutura

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│  Usuário (navegador)                                        │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS
┌────────────────────▼────────────────────────────────────────┐
│  FRONTEND — Vercel (Next.js 14)                             │
│  https://edumap-frontend-nu.vercel.app                      │
│  Repo: github.com/Nerodowble/edumap_frontend                │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS (API REST + JWT)
┌────────────────────▼────────────────────────────────────────┐
│  BACKEND — Render (Docker / FastAPI)                        │
│  https://edumap-ia.onrender.com                             │
│  Repo: github.com/Nerodowble/edumap_ia                      │
└────────────────────┬────────────────────────────────────────┘
                     │ TCP (PostgreSQL)
┌────────────────────▼────────────────────────────────────────┐
│  BANCO DE DADOS — Render PostgreSQL                         │
│  Nome: edumap-db                                            │
│  Plano: Free                                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Frontend — Vercel

### Onde acessar
- **Aplicação:** https://edumap-frontend-nu.vercel.app
- **Painel Vercel:** https://vercel.com/dashboard → projeto `edumap_frontend`

### Repositório GitHub
- `git@github.com:Nerodowble/edumap_frontend.git`
- Branch de produção: `main`

### Como foi configurado
1. Conta Vercel criada em vercel.com (vinculada ao GitHub)
2. GitHub App do Vercel configurada para acessar o repo `edumap_frontend`
3. Projeto importado no Vercel com as configurações do `vercel.json`
4. Variável de ambiente adicionada:
   - `NEXT_PUBLIC_API_URL` = `https://edumap-ia.onrender.com`

### Arquivo de configuração (`vercel.json`)
```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "installCommand": "npm install"
}
```

### Como fazer redeploy
- **Automático:** qualquer push para `main` no repo `edumap_frontend` aciona novo deploy
- **Manual:** Painel Vercel → projeto → aba "Deployments" → botão "Redeploy"

### Como alterar variáveis de ambiente
Painel Vercel → projeto → aba "Settings" → "Environment Variables"

---

## 2. Backend — Render

### Onde acessar
- **API:** https://edumap-ia.onrender.com
- **Documentação interativa:** https://edumap-ia.onrender.com/docs
- **Painel Render:** https://dashboard.render.com → serviço `edumap_ia`

### Repositório GitHub
- `git@github.com:Nerodowble/edumap_ia.git`
- Branch de produção: `main`

### Como foi configurado
1. Conta Render criada em render.com (vinculada ao GitHub)
2. Serviço criado como **Web Service** do tipo **Docker**
3. Render detecta o `Dockerfile` na raiz do repo automaticamente

### Dockerfile usado
```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p data
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Variáveis de ambiente configuradas no Render
| Variável | Valor | Descrição |
|----------|-------|-----------|
| `DATABASE_URL` | `postgresql://...` | URL interna do PostgreSQL (gerada pelo Render) |
| `ALLOWED_ORIGINS` | `https://edumap-frontend-nu.vercel.app` | Libera CORS para o frontend |
| `SECRET_KEY` | string secreta | Chave para assinar tokens JWT de autenticação |

> **Importante:** `SECRET_KEY` deve ser uma string longa e aleatória. Nunca exponha esse valor publicamente. Exemplo de como gerar uma chave segura:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

### Como acessar as variáveis no Render
Painel → serviço `edumap_ia` → menu lateral **"Environment"**

### Como fazer redeploy
- **Automático:** qualquer push para `main` no repo `edumap_ia`
- **Manual:** Painel → serviço `edumap_ia` → botão **"Manual Deploy"** → "Deploy latest commit"

### Aviso: Free Tier
O plano gratuito do Render **dorme após 15 minutos de inatividade**. A primeira requisição após o sono pode demorar **30–60 segundos** para acordar o serviço. Isso é normal.

---

## 3. Banco de Dados — Render PostgreSQL

### Onde acessar
- **Painel Render:** https://dashboard.render.com → banco `edumap-db`
- **Plano:** Free (90 dias, depois expira — ver seção "Limitações")

### Como foi criado
1. Painel Render → **"New +"** → **"PostgreSQL"**
2. Nome: `edumap-db`, Region: Oregon (US West), Plan: Free
3. Após criar, a **Internal Database URL** foi copiada e adicionada como variável `DATABASE_URL` no serviço `edumap_ia`

### Tabelas criadas automaticamente
O sistema cria todas as tabelas no primeiro start via `init_db()`. Migrações (ex: novas colunas) também são aplicadas automaticamente:

| Tabela | Descrição |
|--------|-----------|
| `usuarios` | Usuários da plataforma (nome, email, senha hash, role, escola) |
| `turmas` | Turmas cadastradas (nome, escola, disciplina, dono) |
| `alunos` | Alunos vinculados a turmas |
| `provas` | Provas enviadas via OCR |
| `questoes` | Questões extraídas de cada prova (com Bloom, área, BNCC) |
| `respostas` | Respostas de cada aluno por questão |
| `gabarito` | Gabarito oficial de cada prova |

### Como acessar o banco diretamente (se precisar)
1. Painel Render → banco `edumap-db`
2. Clique em **"Connect"** → copie a **"External Database URL"**
3. Use qualquer cliente PostgreSQL (DBeaver, pgAdmin, psql):
   ```bash
   psql "postgresql://usuario:senha@host:5432/dbname"
   ```

### Limitações do Free Tier
- **Expira após 90 dias** da criação — o Render avisa por e-mail antes
- Máximo 1 GB de dados
- Quando expirar: criar um novo banco, copiar a nova `DATABASE_URL` no serviço

### Backup manual dos dados
```bash
# Exportar (rodar localmente com a External URL)
pg_dump "postgresql://..." > backup_edumap.sql

# Restaurar em novo banco
psql "postgresql://..." < backup_edumap.sql
```

---

## 4. Autenticação e Usuários

### Como funciona
O sistema usa **JWT (JSON Web Token)** para autenticação. Ao fazer login, o backend retorna um token que o frontend armazena no `localStorage` e envia em todas as requisições via cabeçalho `Authorization: Bearer <token>`.

Os tokens expiram em **7 dias**. Após isso, o usuário é redirecionado para o login automaticamente.

### Níveis de acesso (roles)

| Role | Quem é | O que pode ver |
|------|--------|----------------|
| `admin_geral` | Administrador da plataforma | Todas as turmas, todos os dados |
| `admin_escolar` | Coordenador/diretor de escola | Turmas da sua escola (filtro por campo `escola`) |
| `professor` | Professor comum | Apenas suas próprias turmas |

### Primeiro acesso — criando o Admin Geral
1. Acesse https://edumap-frontend-nu.vercel.app/register
2. Preencha nome, e-mail e senha
3. **O primeiro usuário cadastrado vira `admin_geral` automaticamente**
4. Usuários seguintes são criados como `professor` por padrão

### Fluxo de login
```
1. Usuário acessa qualquer página
2. AuthGuard detecta que não há token → redireciona para /login
3. Usuário insere e-mail e senha
4. Backend valida credenciais e retorna JWT
5. Frontend armazena token e dados do usuário no localStorage
6. Usuário é redirecionado para a página inicial
```

### Endpoints de autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/auth/register` | Cadastra novo usuário |
| `POST` | `/auth/login` | Autentica e retorna token |
| `GET` | `/auth/me` | Retorna dados do usuário logado |

Todos os outros endpoints exigem o token no cabeçalho.

### Páginas de autenticação no frontend

| Página | URL | Descrição |
|--------|-----|-----------|
| Login | `/login` | Formulário de e-mail e senha |
| Registro | `/register` | Cadastro de novo usuário |

### Variável de ambiente necessária no backend
```
SECRET_KEY=<string-longa-e-aleatória>
```
Sem essa variável, o sistema usa uma chave padrão insegura. **Sempre configure em produção.**

### Como desativar a autenticação (apenas para testes locais)
```bash
export SKIP_AUTH=true
uvicorn api:app --reload
```
Com `SKIP_AUTH=true`, todos os endpoints aceitam requisições sem token e operam como `admin_geral`.

---

## 5. Fluxo Completo de Uso (Professor)

```
1. Acessar https://edumap-frontend-nu.vercel.app
   └─ Se não logado → redirecionado para /login

2. Login ou criação de conta (/register)

3. Criar turma → cadastrar alunos (página "Turmas e Alunos")

4. Upload da prova (página "Analisar Prova")
   └─ OCR extrai texto → IA classifica questões por Bloom + área + BNCC

5. Definir gabarito (letra correta de cada questão)

6. Lançar respostas dos alunos (página "Lançamento")

7. Visualizar relatórios (página "Relatório do Professor"):
   ├─ Diagnóstico por conteúdo: drill-down área → subárea → Bloom
   ├─ Por aluno: acertos, erros, pontos críticos
   └─ Visão geral da turma: média e alunos que precisam de atenção
```

---

## 6. Como Fazer Atualizações de Código

### Frontend
```bash
cd edumap_frontend
# ... editar código ...
git add .
git commit -m "descrição da mudança"
git push origin main
# Vercel detecta e faz deploy automático (~2 min)
```

### Backend
```bash
cd edumap_ia
# ... editar código ...
git add .
git commit -m "descrição da mudança"
git push origin main
# Render detecta e faz deploy automático (~5 min, inclui build Docker)
```

---

## 7. Diagnóstico de Problemas

### Usuário não consegue fazer login
1. Verificar se `SECRET_KEY` está configurada no Render
2. Verificar se o backend está acordado: https://edumap-ia.onrender.com/
3. Ver logs do Render para erros de autenticação

### Frontend redireciona para login em loop
1. Limpar o `localStorage` do navegador (F12 → Application → Local Storage → Clear)
2. Tentar fazer login novamente

### Frontend não carrega / erro de CORS
1. Verificar se o backend está acordado: acessar https://edumap-ia.onrender.com/
2. Se demorar 30-60s, é o "cold start" do free tier — aguardar
3. Se erro de CORS persistir: Render → serviço `edumap_ia` → Environment → confirmar que `ALLOWED_ORIGINS` contém a URL do Vercel

### Backend retorna erro 500
1. Render → serviço `edumap_ia` → menu **"Logs"** → ver mensagem de erro
2. Causas comuns:
   - `DATABASE_URL` não configurada ou incorreta
   - `SECRET_KEY` ausente
   - Tesseract não instalado (problema de build)
   - Arquivo de prova com formato não suportado

### Banco de dados não conecta
1. Render → banco `edumap-db` → verificar se está **"Available"** (não expirado)
2. Verificar se a `DATABASE_URL` no serviço é a **Internal URL** (não External)
3. Ambos (serviço + banco) devem estar na **mesma region** (Oregon)

### Deploy falhou no Render
1. Render → serviço `edumap_ia` → aba **"Events"** → clicar no deploy com ❌
2. Ver os logs de build para identificar o erro
3. Corrigir no código local, fazer push — novo deploy inicia automaticamente

---

## 8. Credenciais e Acessos

| Serviço | URL de acesso | Login |
|---------|---------------|-------|
| Vercel | https://vercel.com | GitHub (Nerodowble) |
| Render | https://dashboard.render.com | GitHub (Nerodowble) |
| GitHub (frontend) | https://github.com/Nerodowble/edumap_frontend | GitHub (Nerodowble) |
| GitHub (backend) | https://github.com/Nerodowble/edumap_ia | GitHub (Nerodowble) |

---

## 9. Resumo Rápido de URLs

| O que | URL |
|-------|-----|
| Aplicação (usar) | https://edumap-frontend-nu.vercel.app |
| Login | https://edumap-frontend-nu.vercel.app/login |
| Registro | https://edumap-frontend-nu.vercel.app/register |
| API (testar) | https://edumap-ia.onrender.com/docs |
| Health check | https://edumap-ia.onrender.com/ |
| Painel frontend | https://vercel.com/dashboard |
| Painel backend + DB | https://dashboard.render.com |
