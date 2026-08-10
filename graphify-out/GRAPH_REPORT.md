# Graph Report - .  (2026-08-10)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 732 nodes · 1372 edges · 52 communities (33 shown, 19 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 73 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `165c6488`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- telegram_bot.py
- test_investments.py
- database.py
- TransacaoExtraida
- spreadsheets.py
- dependencies
- test_issue_hardening.py
- v1/telegram.py
- telegram_client.py
- v1/investments.py
- transactions.py
- main.py
- compilerOptions
- test_periodos.py
- **4\. Regras de Negócio Fundamentais**
- dashboard.py
- schemas/investment.py
- layout.tsx
- Back-end — Gestor Financeiro com IA
- Relatório 01 — Fundação, autenticação e gestão financeira
- Relatório 02 — Investimentos, cotações e simulador
- Relatório 03 — Confirmações do bot, operação e validação final
- Document File Icon
- Globe Icon
- Next.js Wordmark
- Vercel Triangle Mark
- Browser Window Icon
- ImportJobResponse
- rules/graphify.md
- workflows/graphify.md
- api/__init__.py
- schemas/__init__.py
- Regras do agente para Next.js
- eslint.config.mjs
- next.config.ts
- postcss.config.mjs
- CurrentUser
- DatabaseSession
- get
- post
- ValueError
- field_validator
- RuntimeError
- Decimal
- BaseModel
- RLS obrigatÃ³rio

## God Nodes (most connected - your core abstractions)
1. `Base` - 19 edges
2. `TransacaoExtraida` - 19 edges
3. `send_message()` - 18 edges
4. `_tratar_mensagem()` - 17 edges
5. `compilerOptions` - 16 edges
6. `call()` - 15 edges
7. `refresh_user_quotes()` - 15 edges
8. `criar_link_token()` - 14 edges
9. `calculate_position()` - 13 edges
10. `_portfolio()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Descarte de updates pendentes` --rationale_for--> `set_webhook()`  [INFERRED]
  resume/como-rodar-o-bot.md → backend/app/services/telegram_client.py
- `OperaÃ§Ã£o em trÃªs terminais` --references--> `main()`  [EXTRACTED]
  resume/como-rodar-o-bot.md → backend/scripts/setup_telegram_bot.py
- `main()` --implements--> `Provisionamento do Bot do Telegram`  [EXTRACTED]
  backend/scripts/setup_telegram_bot.py → plan/Guia de Criacao e Configuracao - Bot do Telegram com IA.md
- `RotaÃ§Ã£o do Quick Tunnel` --rationale_for--> `main()`  [EXTRACTED]
  resume/como-rodar-o-bot.md → backend/scripts/setup_telegram_bot.py
- `Bot do Telegram com IA implementado` --semantically_similar_to--> `Fluxo implementado do bot`  [INFERRED] [semantically similar]
  README.md → resume/bot-telegram-status.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Multi-Tenant Financial Schema** — backend_app_models_user_user, backend_app_models_transaction_transaction, backend_app_models_telegram_token_telegramtoken [EXTRACTED 1.00]
- **Telegram Financial Message Flow** — backend_app_api_v1_telegram_telegram_webhook, backend_app_services_telegram_bot_processar_update, backend_app_services_telegram_bot_tratar_mensagem, backend_app_services_telegram_bot_registrar_lancamento, backend_app_services_gemini_extrair_transacao, backend_app_services_telegram_bot_persistir, backend_app_services_telegram_client_send_message [EXTRACTED 1.00]
- **Telegram Account Linking Flow** — backend_app_services_telegram_bot_criar_link_token, backend_app_services_telegram_bot_cmd_start, backend_app_services_telegram_bot_buscar_vinculo, backend_app_models_telegram_token_telegramtoken, backend_app_models_user_user [EXTRACTED 1.00]
- **Provisionamento completo do Bot Telegram** — backend_scripts_setup_telegram_bot_main, backend_app_services_telegram_client_set_webhook, backend_app_services_telegram_client_set_my_commands, backend_app_services_telegram_client_set_my_description, backend_app_services_telegram_client_set_my_short_description [EXTRACTED 1.00]
- **OperaÃ§Ã£o local em trÃªs terminais** — resume_como_rodar_o_bot_tres_terminais, backend_scripts_setup_telegram_bot_main, plan_guia_de_criacao_e_configuracao_bot_do_telegram_com_ia_webhook_https [EXTRACTED 1.00]
- **Contrato compartilhado de perÃ­odos de saldo** — backend_app_services_gemini_periodos_saldo, backend_app_services_telegram_bot_periodos, backend_tests_test_periodos_test_periodos_batem_com_o_contrato_da_ia [EXTRACTED 1.00]

## Communities (52 total, 19 thin omitted)

### Community 0 - "telegram_bot.py"
Cohesion: 0.08
Nodes (58): has_privacy_policy(), PrivacyPolicyResponse, BaseModel, Subconjunto do payload de Update da Bot API do Telegram. Só mapeamos os campos…, Cobre tanto `voice` quanto `audio` — só precisamos do file_id e do tamanho., TelegramBase, TelegramCallbackQuery, TelegramChat (+50 more)

### Community 1 - "test_investments.py"
Cohesion: 0.07
Nodes (48): calculate_compound_interest(), calculate_position(), calculate_twr(), calculate_xirr(), CalculatedPosition, InvestmentCalculationError, movement_cash_flow(), MovementLike (+40 more)

### Community 2 - "database.py"
Cohesion: 0.07
Nodes (37): Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online(), downgrade(), upgrade(), Concurrent Balance Query Index, downgrade() (+29 more)

### Community 3 - "TransacaoExtraida"
Cohesion: 0.06
Nodes (46): Check Extracted Transaction Coherence, _config(), extrair_transacao(), GeminiIndisponivelError, get_client(), _parse(), PERIODOS_SALDO, Balance Period Contract (+38 more)

### Community 4 - "spreadsheets.py"
Cohesion: 0.09
Nodes (35): decimal_from_value(), Decimal, quantize_money(), Converte sem passar por float e entende os formatos 1234.56 e 1.234,56., _csv_rows(), _escape_spreadsheet_formula(), export_csv(), export_xlsx() (+27 more)

### Community 5 - "dependencies"
Cohesion: 0.05
Nodes (42): axios, eslint, eslint-config-next, dependencies, axios, lucide-react, next, react (+34 more)

### Community 6 - "test_issue_hardening.py"
Cohesion: 0.10
Nodes (35): delete_account(), login(), me(), CurrentUser, DatabaseSession, delete, get, post (+27 more)

### Community 7 - "v1/telegram.py"
Cohesion: 0.09
Nodes (36): create_telegram_link(), current_telegram_privacy_policy(), _policy_response(), _published_policy(), Endpoint de webhook do Telegram (seção 3.1 do guia)., Recebe os updates do Telegram. Responde 200 imediatamente e processa a mensagem…, Publica o aviso vigente antes de qualquer coleta de consentimento., Mantém cada aviso publicado acessível por uma URL estável e versionada. (+28 more)

### Community 8 - "telegram_client.py"
Cohesion: 0.09
Nodes (34): Any, Configurações da aplicação carregadas do .env via pydantic-settings., Settings, answer_callback_query(), _api_url(), call(), download_file(), _file_url() (+26 more)

### Community 9 - "v1/investments.py"
Cohesion: 0.16
Nodes (31): AssetCreate, AssetUpdate, _as_utc(), create_asset(), create_movement(), _decimal(), delete_asset(), delete_movement() (+23 more)

### Community 10 - "transactions.py"
Cohesion: 0.15
Nodes (31): _as_utc(), _conditions(), create_transaction(), delete_transaction(), export_transactions(), get_import_job(), get_transaction(), import_file() (+23 more)

### Community 11 - "main.py"
Cohesion: 0.10
Nodes (21): compound_interest(), post, Rotas da versão 1 da API., _cors_origins_with_credentials(), health_check(), lifespan(), get, Executa automaticamente todas as migrations pendentes do Alembic no Supabase. (+13 more)

### Community 12 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 13 - "test_periodos.py"
Cohesion: 0.13
Nodes (25): Serviços de integração externa e regras de negócio., _inicio_3_meses(), _inicio_da_semana(), _inicio_do_dia(), _inicio_do_mes(), datetime, Meia-noite de hoje no fuso de São Paulo, em UTC., Meia-noite da segunda-feira da semana corrente no fuso de São Paulo, em UTC. (+17 more)

### Community 14 - "**4\. Regras de Negócio Fundamentais**"
Cohesion: 0.10
Nodes (20): ---, **2\. Escolha das Tecnologias & Justificativa Técnica**, **3.1. Fronteira de Execução: o que pode rodar no event loop**, **3.2. Fronteira de Privacidade: dados que saem do sistema**, **3\. Arquitetura da Solução**, **4.1. Processamento via Bot de Mensagens**, **4.2.1. Preço médio e ganho de capital**, **4.2.2. Os dois indicadores de rentabilidade (não se confundem)** (+12 more)

### Community 15 - "dashboard.py"
Cohesion: 0.19
Nodes (15): financial_summary(), CurrentUser, DatabaseSession, datetime, get, CategorySummary, FinancialSummary, BaseModel (+7 more)

### Community 16 - "schemas/investment.py"
Cohesion: 0.19
Nodes (13): AssetCreate, AssetResponse, AssetUpdate, MovementCreate, MovementResponse, PortfolioResponse, PositionResponse, BaseModel (+5 more)

### Community 17 - "layout.tsx"
Cohesion: 0.25
Nodes (6): geistMono, geistSans, metadata, RootLayout(), Home(), Projeto Next.js inicial

### Community 18 - "Back-end — Gestor Financeiro com IA"
Cohesion: 0.29
Nodes (6): Back-end — Gestor Financeiro com IA, Cotações, Executar, Planilhas, Testes, Áreas da API

### Community 19 - "Relatório 01 — Fundação, autenticação e gestão financeira"
Cohesion: 0.33
Nodes (5): O que foi feito, Para que serve, Pendências e melhorias futuras, Relatório 01 — Fundação, autenticação e gestão financeira, Validação executada

### Community 20 - "Relatório 02 — Investimentos, cotações e simulador"
Cohesion: 0.33
Nodes (5): O que foi feito, Para que serve, Pendências e melhorias futuras, Relatório 02 — Investimentos, cotações e simulador, Validação executada

### Community 21 - "Relatório 03 — Confirmações do bot, operação e validação final"
Cohesion: 0.33
Nodes (5): O que foi feito, Para que serve, Pendências e melhorias futuras, Relatório 03 — Confirmações do bot, operação e validação final, Validação executada

### Community 22 - "Document File Icon"
Cohesion: 0.50
Nodes (4): Document File Icon, Document Text Lines, File or Document UI Affordance, Folded Page Corner

### Community 23 - "Globe Icon"
Cohesion: 0.50
Nodes (4): Global or Internet UI Affordance, Globe Icon, Latitude Bands, Longitude Meridians

### Community 24 - "Next.js Wordmark"
Cohesion: 0.50
Nodes (4): Framework Branding UI Element, Geometric NEXT.JS Lettering, Next.js Brand, Next.js Wordmark

### Community 25 - "Vercel Triangle Mark"
Cohesion: 0.50
Nodes (4): Branding UI Element, Upward White Triangle, Vercel Brand, Vercel Triangle Mark

### Community 26 - "Browser Window Icon"
Cohesion: 0.67
Nodes (4): Browser Window Icon, Three Title-Bar Controls, Web Interface Affordance, Rounded Window Frame

## Knowledge Gaps
- **106 isolated node(s):** `geistSans`, `geistMono`, `metadata`, `eslintConfig`, `nextConfig` (+101 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `_portfolio()` connect `v1/investments.py` to `schemas/investment.py`, `test_investments.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `TransacaoExtraida` connect `TransacaoExtraida` to `telegram_bot.py`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `criar_link_token()` connect `telegram_bot.py` to `telegram_client.py`, `TransacaoExtraida`, `spreadsheets.py`, `v1/telegram.py`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `Base` (e.g. with `InvestmentAsset` and `InvestmentMovement`) actually correct?**
  _`Base` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `geistSans`, `geistMono`, `metadata` to the rest of the system?**
  _106 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `telegram_bot.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08196721311475409 - nodes in this community are weakly interconnected._
- **Should `test_investments.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06721215663354763 - nodes in this community are weakly interconnected._