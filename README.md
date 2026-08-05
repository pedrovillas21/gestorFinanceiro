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
- ✅ **Bot do Telegram com IA**: webhook `POST /api/v1/telegram/webhook`, vínculo por Deep Link, comandos `/start`, `/ajuda` e `/saldo`, transcrição de áudio pela Cascata do Gemini e persistência das transações — detalhes em [resume/bot-telegram-status.md](resume/bot-telegram-status.md)

> 👉 Para subir e usar o bot no dia a dia, o passo a passo completo (incluindo criar usuário e resolver os erros comuns) está em **[resume/como-rodar-o-bot.md](resume/como-rodar-o-bot.md)**.

## Configuração inicial (contas e segredos)

> As três etapas abaixo **já foram concluídas** neste ambiente. Ficam documentadas para reconstruir o projeto em outra máquina.

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
✅ Feito: a revision `6ca4ec8a71fb` está versionada em `backend/alembic/versions/` e aplicada no Supabase (tabelas `users`, `transactions`, `telegram_tokens`). A partir daqui, `uvicorn app.main:app` aplica sozinho qualquer migration pendente via `lifespan`.

Para recriar o schema do zero em outro banco:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
alembic upgrade head
```
Depois de alterar um model, gere a revision correspondente com `alembic revision --autogenerate -m "descricao"`.

### 4. Criar um usuário
Ainda não existe endpoint de cadastro — use o script:
```powershell
python scripts\criar_usuario.py --email voce@exemplo.com --nome "Seu Nome"
```

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
Copie a URL `https://*.trycloudflare.com` exibida no terminal. É uma URL temporária (Quick Tunnel) — muda a cada execução. Se quiser uma URL fixa, será necessário `cloudflared tunnel login` e criar um túnel nomeado associado a um domínio seu no Cloudflare (gratuito também, mas exige domínio).

**Registrar o bot no Telegram (webhook + menu de comandos + descrição):**
```powershell
cd backend
python scripts/setup_telegram_bot.py --url https://<sua-url>.trycloudflare.com
python scripts/setup_telegram_bot.py --somente-info   # confere o estado atual do webhook
```
O script cobre por HTTP tudo o que o guia pede via @BotFather (`setWebhook`, `setMyCommands`, `setMyDescription`) — basta ter `TELEGRAM_BOT_TOKEN` e `TELEGRAM_WEBHOOK_SECRET` no `.env`.

**Conectar sua conta ao bot (Deep Link):**
```powershell
python scripts/gerar_link_telegram.py --email voce@exemplo.com
```
Abra o link `t.me/<bot>?start=<token>` impresso; o bot grava o `chat_id` e a partir daí aceita áudios e textos.

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
│   │   ├── api/v1/telegram.py # Webhook do Telegram
│   │   ├── core/config.py     # Settings via pydantic-settings
│   │   ├── database.py        # engine, SessionLocal, Base
│   │   ├── models/            # User, Transaction, TelegramToken
│   │   ├── schemas/           # Payload do Update do Telegram
│   │   ├── services/          # Bot API, Cascata do Gemini, regras do bot
│   │   └── main.py            # FastAPI + lifespan (auto-run migrations)
│   ├── scripts/               # setup do bot, criar usuário, gerar Deep Link
│   ├── alembic/
│   │   ├── env.py             # lê DATABASE_URL do .env, target_metadata = Base.metadata
│   │   └── versions/          # 6ca4ec8a71fb (schema inicial)
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
├── frontend/                  # Next.js 14 + TS + Tailwind + App Router
│   └── .env.local.example
├── plan/                      # Especificações
├── resume/                    # Status e runbook do bot
├── .gitignore
└── README.md
```

## Próximos passos do produto

- **Autenticação JWT da API Web** (`/auth/login`, `/auth/register`) — sem ela, cadastrar usuário e gerar o Deep Link continuam sendo scripts de linha de comando.
- **Tela `conectar-telegram`** no front-end, para o vínculo sair do terminal.
- **CRUD de transações** e dashboard.
- **Hospedagem**, para o bot responder sem depender da máquina ligada — ver a análise em [resume/bot-telegram-status.md](resume/bot-telegram-status.md).
- Opcional: token da Braapi, se for usar cotações da B3 (`BRAAPI_TOKEN`); sem ele, dá para usar só `yfinance`.
