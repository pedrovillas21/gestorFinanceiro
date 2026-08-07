# **Plano de Preparação do Ambiente de Desenvolvimento (Setup, Supabase & Alembic Migrations)**

Manual Completo de Ferramentas, Dependências e Automação de Migrations em Python no Supabase

## ---

**1\. Visão Geral da Infraestrutura de Desenvolvimento**

Este documento detalha o ecossistema completo de software, dependências, SDKs e utilitários necessários para estruturar o ambiente de desenvolvimento local e de produção para o **Gestor Financeiro com IA**, adotando o **Supabase (PostgreSQL gerenciado)** com versionamento e execução automática de **Database Migrations via Alembic (Python)**, equivalente ao funcionamento do Flyway no ecossistema Java.

## **2\. Matriz de Ferramentas e Tecnologias**

| Camada | Ferramenta / Tecnologia | Versão / Tipo | Finalidade no Projeto |
| :---- | :---- | :---- | :---- |
| **Linguagem Back-end** | Python | 3.11+ | Execução da API FastAPI, scripts de IA e rotinas de banco. |
| **Framework Back-end** | FastAPI \+ Uvicorn | FastAPI 0.110+ | Servidor assíncrono para endpoints REST, JWT e recebimento de webhooks do Telegram. |
| **Runtime Front-end** | Node.js | 20+ LTS | Ambiente de execução para React / Next.js e gerenciamento de pacotes. |
| **Framework Front-end** | Next.js (React \+ TypeScript) | 14+ (App Router) | Dashboard interativo, autenticação web e tabelas estilo planilha. |
| **Estilização** | Tailwind CSS | 4.0 | Engine de estilização baseada em Rust (Oxide) para a interface. |
| **Banco de Dados & Auth** | Supabase (PostgreSQL) | Managed Cloud / Postgres 15+ | Persistência relacional multi-tenant com isolamento por user\_id. |
| **Migrations Automáticas (Flyway equivalent)** | Alembic \+ SQLAlchemy | Alembic 1.13+ | Versionamento do schema, geração automática de scripts e execução auto-run na inicialização da API. |
| **Motor de IA** | Google GenAI SDK (google-genai) | Mais recente | Integração nativa com a Cascata do Gemini (Gemini Flash Recente → 2.5 Flash). |
| **Túnel Webhook Local** | Ngrok ou Cloudflare Tunnels | Mais recente | Exposição do localhost:8000 em HTTPS para testes de webhook no Telegram. |
| **API do Mercado** | brapi / yfinance | Mais recente | Cotações das ações da B3 e carteira de ativos em tempo real. |

## **3\. Estratégia de Migrations Automáticas com Alembic (Equivalente ao Flyway)**

### **3.1. Por que usar Alembic no lugar do SQL direto no Supabase?**

No ecossistema Java, o **Flyway** gerencia e aplica automaticamente os scripts SQL na subida da aplicação. Em Python, o **Alembic** (ferramenta oficial do SQLAlchemy) desempenha exatamente esse papel. Você **não precisa executar SQLs manualmente no painel web do Supabase**. O Alembic compara suas classes Python com o banco do Supabase, detecta alterações (novas tabelas, colunas, índices) e aplica tudo automaticamente na inicialização do FastAPI.

### **3.2. Configuração e Fluxo de Trabalho do Alembic**

1. **Inicialização do Projeto Alembic:**  
   `alembic init alembic`  
2. **Configuração do env.py:** Apontar a variável target\_metadata para a \`Base.metadata\` dos seus modelos SQLAlchemy e carregar a \`DATABASE\_URL\` diretamente do \`.env\`.  
3. **Geração Automática de Migration (Diff):**  
   `alembic revision --autogenerate -m "create_initial_multi_tenant_tables"`*O Alembic lerá suas classes Python (\`User\`, \`Transaction\`, \`TelegramToken\`) e criará o arquivo de versão contendo o SQL e código de migration.*

### **3.3. Execução Automática na Subida da Aplicação (Auto-Run Startup Event)**

Para garantir que o Supabase receba e aplique todas as migrations pendentes assim que a API FastAPI for iniciada (comportamento idêntico ao Flyway no Spring Boot), adiciona-se a execução programática das migrations no ciclo de vida (Lifespan) do FastAPI:

`from contextlib import asynccontextmanager`  
`from fastapi import FastAPI`  
`from alembic.config import Config`  
`from alembic import command`

`def run_migrations():`  
    `"""Executa automaticamente todas as migrations pendentes do Alembic no Supabase."""`  
    `alembic_cfg = Config("alembic.ini")`  
    `command.upgrade(alembic_cfg, "head")`

`@asynccontextmanager`  
`async def lifespan(app: FastAPI):`  
    `# Roda as migrations no Supabase na inicialização do servidor`  
    `print("Verificando e aplicando migrations no Supabase...")`  
    `run_migrations()`  
    `print("Migrations aplicadas com sucesso!")`  
    `yield`

`app = FastAPI(lifespan=lifespan)`


## **4\. Passo a Passo de Preparação do Ambiente Local**

### **4.1. Configuração do Supabase (Banco de Dados)**

1. Acessar https://supabase.com e criar um projeto gratuito.  
2. Ir em **Project Settings \> Database** e copiar a URI do PostgreSQL na seção **Connection String (URI)** usando a porta 5432 (ou porta de pool 6543).  
3. Adicionar a URI de conexão diretamente na variável DATABASE\_URL no arquivo \`.env\`. Nenhuma tabela precisa ser criada manualmente no painel do Supabase.

### **4.2. Instalação de Dependências Back-end (Python / FastAPI)**

`pip install fastapi "uvicorn[standard]" google-genai sqlalchemy alembic psycopg2-binary pydantic pydantic-settings "python-jose[cryptography]" "passlib[bcrypt]" httpx python-multipart yfinance supabase`

### **4.3. Configuração do Front-end (Next.js / TypeScript / Tailwind 4.0)**

`npx create-next-app@latest frontend --typescript --tailwind --eslint --app`  
`cd frontend`  
`npm install recharts lucide-react axios @tanstack/react-table @supabase/supabase-js`

## **5\. Arquivo de Variáveis de Ambiente (\`.env\`)**

`# Servidor e Conexão Direta Supabase PostgreSQL (Usado pelo Alembic e FastAPI)`  
`DATABASE_URL=postgresql://postgres:[SUA_SENHA]@db.[SEU_PROJECT_REF].supabase.co:5432/postgres`  
`SUPABASE_URL=https://[SEU_PROJECT_REF].supabase.co`  
`SUPABASE_KEY=sua_anon_ou_service_role_key`

`# Autenticação JWT`  
`SECRET_KEY=sua_chave_secreta_jwt_super_segura`  
`ALGORITHM=HS256`  
`ACCESS_TOKEN_EXPIRE_MINUTES=10080`

`# Chaves de APIs`  
`GEMINI_API_KEY=sua_chave_do_google_ai_studio`  
`TELEGRAM_BOT_TOKEN=seu_token_obtido_no_botfather`  
`TELEGRAM_WEBHOOK_SECRET=token_secreto_para_validar_webhook`

`# Mercado Financeiro`  
`BRAAPI_TOKEN=seu_token_opcional_da_braapi`

## **6\. Fluxo de Inicialização e Desenvolvimento**

1. **Iniciar a API FastAPI:** uvicorn app.main:app \--reload \--port 8000  
   *O evento \`lifespan\` do FastAPI detectará automaticamente as alterações nos seus modelos Python e aplicará as tabelas/migrations no Supabase.*  
2. **Expor Webhook Local:** ngrok http 8000 (copiar URL HTTPS para registrar no Telegram).  
3. **Rodar Front-end Web:** npm run dev (no diretório frontend).