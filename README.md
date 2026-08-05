# Gestor Financeiro com IA

Ambiente de desenvolvimento preparado conforme [plan/Plano de Preparacao do Ambiente - Supabase e Alembic Migrations Automatica.md](plan/Plano%20de%20Preparacao%20do%20Ambiente%20-%20Supabase%20e%20Alembic%20Migrations%20Automatica.md).

## O que já está pronto

- ✅ Python 3.12 instalado (via winget)
- ✅ cloudflared instalado (via winget) — usado como túnel de webhook no lugar do ngrok
- ✅ `backend/venv` criado com todas as dependências instaladas (`backend/requirements.txt`)
- ✅ Estrutura FastAPI em `backend/app/` (`main.py`, `core/config.py`, `database.py`, `models/`)
- ✅ Alembic inicializado e configurado em `backend/alembic/` (autogenerate + auto-run no `lifespan` do FastAPI)
- ✅ Models iniciais criados: `User`, `Transaction`, `TelegramToken` (`backend/app/models/`)
- ✅ Frontend Next.js 14 (TypeScript + Tailwind + ESLint + App Router) em `frontend/`, com `recharts`, `lucide-react`, `axios`, `@tanstack/react-table`, `@supabase/supabase-js` instalados
- ✅ `.gitignore` na raiz (protege `.env`, `venv/`, `node_modules/`, `.next/`)
- ✅ `backend/.env.example` e `frontend/.env.local.example` como modelos

## O que só você pode fazer (contas e segredos)

### 1. Criar o projeto no Supabase
1. Acesse https://supabase.com e crie um projeto gratuito.
2. Vá em **Project Settings → Database** e copie a **Connection String (URI)** (porta 5432, ou 6543 se usar pool).
3. Vá em **Project Settings → API** e copie a `URL` e a `anon key` (e a `service_role key`, se for usar no backend).

### 2. Preencher as variáveis de ambiente
```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.local.example frontend\.env.local
```
Edite os dois arquivos com os valores reais (Supabase, `SECRET_KEY` do JWT, `GEMINI_API_KEY` do [Google AI Studio](https://aistudio.google.com), `TELEGRAM_BOT_TOKEN` do [@BotFather](https://t.me/BotFather), etc).

> `backend/.env` e `frontend/.env.local` nunca devem ser commitados — já estão no `.gitignore`.

### 3. Gerar e aplicar a primeira migration
Isso só funciona depois do `backend/.env` estar preenchido com uma `DATABASE_URL` válida do Supabase:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
alembic revision --autogenerate -m "create_initial_multi_tenant_tables"
alembic upgrade head
```
Nas próximas execuções, `uvicorn app.main:app` já aplica sozinho qualquer migration pendente (via `lifespan`) — mas a **primeira** revision precisa ser gerada manualmente com `--autogenerate` (o Alembic ainda não tem nenhum arquivo de versão em `backend/alembic/versions/`).

## Como rodar o ambiente

**Backend (API FastAPI):**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

**Túnel para o webhook do Telegram (cloudflared, 100% gratuito):**
```powershell
cloudflared tunnel --url http://localhost:8000
```
Copie a URL `https://*.trycloudflare.com` exibida no terminal e registre como webhook no BotFather/API do Telegram. É uma URL temporária (Quick Tunnel) — muda a cada execução. Se quiser uma URL fixa, será necessário `cloudflared tunnel login` e criar um túnel nomeado associado a um domínio seu no Cloudflare (gratuito também, mas exige domínio).

**Frontend (Next.js):**
```powershell
cd frontend
npm run dev
```

## Estrutura criada

```
gestorFinanceiro/
├── backend/
│   ├── venv/                  (gitignored)
│   ├── app/
│   │   ├── core/config.py     # Settings via pydantic-settings
│   │   ├── database.py        # engine, SessionLocal, Base
│   │   ├── models/             # User, Transaction, TelegramToken
│   │   └── main.py            # FastAPI + lifespan (auto-run migrations)
│   ├── alembic/
│   │   ├── env.py             # lê DATABASE_URL do .env, target_metadata = Base.metadata
│   │   └── versions/          # (vazio até o primeiro --autogenerate)
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
├── frontend/                  # Next.js 14 + TS + Tailwind + App Router
│   └── .env.local.example
├── plan/
├── .gitignore
└── README.md
```

## Pendências que ficam por sua conta

- Criar o projeto no Supabase e obter as credenciais (passo 1 acima).
- Preencher os `.env` (passo 2 acima).
- Rodar o primeiro `alembic revision --autogenerate` + `alembic upgrade head` (passo 3 acima).
- Obter `GEMINI_API_KEY` (Google AI Studio) e `TELEGRAM_BOT_TOKEN` (BotFather).
- Opcional: registrar conta no ngrok caso prefira usá-lo no lugar do cloudflared (o projeto já usa cloudflared por ser gratuito sem conta).
- Opcional: token da Braapi, se for usar cotações da B3 (`BRAAPI_TOKEN`); sem ele, dá para usar só `yfinance`.
