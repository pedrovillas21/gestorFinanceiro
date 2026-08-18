# Graph Report - gestorFinanceiro  (2026-08-18)

## Corpus Check
- 160 files · ~76,767 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1411 nodes · 2914 edges · 90 communities (67 shown, 23 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 106 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `10ac3b86`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- telegram_bot.py
- v1/investments.py
- test_investments.py
- TransacaoExtraida
- spreadsheets.py
- dependencies
- v1/auth.py
- schemas/telegram.py
- telegram_client.py
- Funcionalidades disponíveis somente para API Web/dashboard
- dashboard.py
- main.py
- compilerOptions
- test_periodos.py
- **4\. Regras de Negócio Fundamentais**
- 3c7f1a9b2d84_create_missing_processed_telegram_updates.py
- cookies.ts
- theme.tsx
- Back-end — Gestor Financeiro com IA
- Relatório 01 — Fundação, autenticação e gestão financeira
- Relatório 02 — Investimentos, cotações e simulador
- Relatório 03 — Confirmações do bot, operação e validação final
- login_throttle.py
- Lacunas do back-end — relatório de implementação
- timedelta
- test_lacunas_dashboard.py
- User
- 4. Especificação por módulo
- rules/graphify.md
- workflows/graphify.md
- api/__init__.py
- schemas/__init__.py
- Regras do agente para Next.js
- eslint.config.mjs
- next.config.ts
- postcss.config.mjs
- Base
- Base
- RuntimeError
- ValueError
- Fases
- DatabaseSession
- FakeSession
- transactions.py
- devDependencies
- BaseModel
- RLS obrigatÃ³rio
- quote_refresh.py
- Viabilidade de cobrir as lacunas do back-end
- Pendências futuras
- list_snapshots
- v1/telegram.py
- TelegramCard.tsx
- types.ts
- period.ts
- RegisterForm.tsx
- telegram_webhook
- api/auth.ts
- http.ts
- delete_telegram_link
- errors.ts
- LoginForm.tsx
- test_issue_hardening.py
- quantize_money
- test_telegram_privacy_and_exports.py
- LoginBlocked
- package.json
- ComingSoon.tsx
- TelegramToken
- purge_access_lifecycle.py
- Sidebar.tsx
- pagination.ts
- schemas/import_job.py
- react
- react-dom
- @tailwindcss/postcss
- @tanstack/react-table
- jsdom
- @vitejs/plugin-react
- vitest
- Projeto Next.js inicial

## God Nodes (most connected - your core abstractions)
1. `FakeSession` - 28 edges
2. `Base` - 26 edges
3. `User` - 26 edges
4. `Transaction` - 22 edges
5. `readSession()` - 21 edges
6. `RefreshToken` - 20 edges
7. `TransacaoExtraida` - 20 edges
8. `send_message()` - 18 edges
9. `calculate_position()` - 17 edges
10. `_tratar_mensagem()` - 17 edges

## Surprising Connections (you probably didn't know these)
- `Descarte de updates pendentes` --rationale_for--> `set_webhook()`  [INFERRED]
  resume/como-rodar-o-bot.md → backend/app/services/telegram_client.py
- `OperaÃ§Ã£o em trÃªs terminais` --references--> `main()`  [EXTRACTED]
  resume/como-rodar-o-bot.md → backend/scripts/setup_telegram_bot.py
- `Fluxo implementado do bot` --references--> `criar_link_token()`  [EXTRACTED]
  resume/bot-telegram-status.md → backend/app/services/telegram_bot.py
- `main()` --implements--> `Provisionamento do Bot do Telegram`  [EXTRACTED]
  backend/scripts/setup_telegram_bot.py → plan/Guia de Criacao e Configuracao - Bot do Telegram com IA.md
- `RotaÃ§Ã£o do Quick Tunnel` --rationale_for--> `main()`  [EXTRACTED]
  resume/como-rodar-o-bot.md → backend/scripts/setup_telegram_bot.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Multi-Tenant Financial Schema** — backend_app_models_user_user, backend_app_models_transaction_transaction, backend_app_models_telegram_token_telegramtoken [EXTRACTED 1.00]
- **Telegram Financial Message Flow** — backend_app_api_v1_telegram_telegram_webhook, backend_app_services_telegram_bot_processar_update, backend_app_services_telegram_bot_tratar_mensagem, backend_app_services_telegram_bot_registrar_lancamento, backend_app_services_gemini_extrair_transacao, backend_app_services_telegram_bot_persistir, backend_app_services_telegram_client_send_message [EXTRACTED 1.00]
- **Telegram Account Linking Flow** — backend_app_services_telegram_bot_criar_link_token, backend_app_services_telegram_bot_cmd_start, backend_app_services_telegram_bot_buscar_vinculo, backend_app_models_telegram_token_telegramtoken, backend_app_models_user_user [EXTRACTED 1.00]
- **Provisionamento completo do Bot Telegram** — backend_scripts_setup_telegram_bot_main, backend_app_services_telegram_client_set_webhook, backend_app_services_telegram_client_set_my_commands, backend_app_services_telegram_client_set_my_description, backend_app_services_telegram_client_set_my_short_description [EXTRACTED 1.00]
- **OperaÃ§Ã£o local em trÃªs terminais** — resume_como_rodar_o_bot_tres_terminais, backend_scripts_setup_telegram_bot_main, plan_guia_de_criacao_e_configuracao_bot_do_telegram_com_ia_webhook_https [EXTRACTED 1.00]
- **Contrato compartilhado de perÃ­odos de saldo** — backend_app_services_gemini_periodos_saldo, backend_app_services_telegram_bot_periodos, backend_tests_test_periodos_test_periodos_batem_com_o_contrato_da_ia [EXTRACTED 1.00]

## Communities (90 total, 23 thin omitted)

### Community 0 - "telegram_bot.py"
Cohesion: 0.14
Nodes (39): has_privacy_policy(), PendingTransaction, Estado curto para confirmação explícita de extrações incertas do bot., _buscar_pendencia(), _buscar_vinculo(), _cmd_saldo(), _cmd_start(), _concluir_pendencia() (+31 more)

### Community 1 - "v1/investments.py"
Cohesion: 0.13
Nodes (26): _decimal(), get_portfolio(), _latest_quote(), _movement_values(), _portfolio(), Aplica a escala de cada coluna antes de gravar. As casas decimais são as do…, AssetCreate, AssetResponse (+18 more)

### Community 2 - "test_investments.py"
Cohesion: 0.06
Nodes (48): compound_interest(), post, CompoundInterestPoint, CompoundInterestRequest, CompoundInterestResponse, BaseModel, Decimal, field_validator (+40 more)

### Community 3 - "TransacaoExtraida"
Cohesion: 0.06
Nodes (46): Check Extracted Transaction Coherence, _config(), extrair_transacao(), GeminiIndisponivelError, get_client(), _parse(), PERIODOS_SALDO, Balance Period Contract (+38 more)

### Community 4 - "spreadsheets.py"
Cohesion: 0.15
Nodes (25): _csv_rows(), export_movements_csv(), export_portfolio_xlsx(), export_positions_csv(), import_transactions(), _limited_rows(), _movement_row(), _normalized_headers() (+17 more)

### Community 5 - "dependencies"
Cohesion: 0.10
Nodes (21): axios, decimal.js, dependencies, axios, decimal.js, @hookform/resolvers, lucide-react, next (+13 more)

### Community 6 - "v1/auth.py"
Cohesion: 0.19
Nodes (20): logout(), Revoga a sessão informada, ou todas as do usuário. Encerrar **uma** sessão não…, ChangePasswordRequest, is_password_compliant(), LoginRequest, LogoutRequest, MessageResponse, ProfileUpdate (+12 more)

### Community 7 - "schemas/telegram.py"
Cohesion: 0.18
Nodes (16): PrivacyPolicyResponse, BaseModel, Subconjunto do payload de Update da Bot API do Telegram. Só mapeamos os campos…, Cobre tanto `voice` quanto `audio` — só precisamos do file_id e do tamanho., Confirma a revogação e devolve o consentimento que ficou registrado., TelegramBase, TelegramCallbackQuery, TelegramChat (+8 more)

### Community 8 - "telegram_client.py"
Cohesion: 0.09
Nodes (34): Any, Configurações da aplicação carregadas do .env via pydantic-settings., Settings, answer_callback_query(), _api_url(), call(), download_file(), _file_url() (+26 more)

### Community 9 - "Funcionalidades disponíveis somente para API Web/dashboard"
Cohesion: 0.10
Nodes (19): 1. Conexão segura entre conta Web e chat, 2. Registro de receitas e despesas por IA, 3. Consulta de saldo, 4. Comandos e proteção operacional, Arquivos principais usados neste levantamento, Autenticação e conta, Carteira de investimentos, Cotações de mercado (+11 more)

### Community 10 - "dashboard.py"
Cohesion: 0.11
Nodes (30): financial_summary(), financial_timeseries(), CurrentUser, DatabaseSession, date, datetime, Decimal, get (+22 more)

### Community 11 - "main.py"
Cohesion: 0.19
Nodes (12): Rotas da versão 1 da API., _cors_origins_with_credentials(), health_check(), lifespan(), get, Executa automaticamente todas as migrations pendentes do Alembic no Supabase., run_migrations(), Continuously recovers pending jobs and jobs abandoned after a crash. (+4 more)

### Community 12 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 13 - "test_periodos.py"
Cohesion: 0.13
Nodes (25): Serviços de integração externa e regras de negócio., _inicio_3_meses(), _inicio_da_semana(), _inicio_do_dia(), _inicio_do_mes(), datetime, Meia-noite de hoje no fuso de São Paulo, em UTC., Meia-noite da segunda-feira da semana corrente no fuso de São Paulo, em UTC. (+17 more)

### Community 14 - "**4\. Regras de Negócio Fundamentais**"
Cohesion: 0.10
Nodes (20): ---, **2\. Escolha das Tecnologias & Justificativa Técnica**, **3.1. Fronteira de Execução: o que pode rodar no event loop**, **3.2. Fronteira de Privacidade: dados que saem do sistema**, **3\. Arquitetura da Solução**, **4.1. Processamento via Bot de Mensagens**, **4.2.1. Preço médio e ganho de capital**, **4.2.2. Os dois indicadores de rentabilidade (não se confundem)** (+12 more)

### Community 15 - "3c7f1a9b2d84_create_missing_processed_telegram_updates.py"
Cohesion: 0.40
Nodes (4): downgrade(), Cria a tabela de idempotência do webhook nos bancos onde ela não existe.…, Sem efeito: a tabela pertence a `c2d45a0f9e10`, que já a derruba. Esta revisão…, upgrade()

### Community 16 - "cookies.ts"
Cohesion: 0.11
Nodes (38): POST(), POST(), POST(), readAllDevicesFlag(), DELETE(), GET(), PATCH(), unauthorized() (+30 more)

### Community 17 - "theme.tsx"
Cohesion: 0.07
Nodes (31): geistMono, geistSans, metadata, handleAuthErrors(), Providers(), ICON, LABEL, ORDER (+23 more)

### Community 18 - "Back-end — Gestor Financeiro com IA"
Cohesion: 0.25
Nodes (7): Back-end — Gestor Financeiro com IA, Cotações, Executar, Planilhas, Telegram — gerar o Deep Link, Testes, Áreas da API

### Community 19 - "Relatório 01 — Fundação, autenticação e gestão financeira"
Cohesion: 0.33
Nodes (5): O que foi feito, Para que serve, Pendências e melhorias futuras, Relatório 01 — Fundação, autenticação e gestão financeira, Validação executada

### Community 20 - "Relatório 02 — Investimentos, cotações e simulador"
Cohesion: 0.33
Nodes (5): O que foi feito, Para que serve, Pendências e melhorias futuras, Relatório 02 — Investimentos, cotações e simulador, Validação executada

### Community 21 - "Relatório 03 — Confirmações do bot, operação e validação final"
Cohesion: 0.33
Nodes (5): O que foi feito, Para que serve, Pendências e melhorias futuras, Relatório 03 — Confirmações do bot, operação e validação final, Validação executada

### Community 22 - "login_throttle.py"
Cohesion: 0.11
Nodes (34): LoginAttempt, Contador de falhas de login, por escopo, para o bloqueio progressivo. Uma linha…, check_login_allowed(), clear_login_failures(), forget_stale_failures(), lock_duration(), datetime, Session (+26 more)

### Community 23 - "Lacunas do back-end — relatório de implementação"
Cohesion: 0.05
Nodes (41): 10. C2 — reset de senha por e-mail (fora do escopo), 11. Inventário de arquivos, 1.1 Revisão de 14/08/2026, 1.2 Auditoria de 17/08/2026, 1. Resumo executivo, 2.1 Decisão menor tomada sem consulta, 2. Decisões tomadas, 3.1 ⚠️ Editar o `.env` do back-end (+33 more)

### Community 24 - "timedelta"
Cohesion: 0.17
Nodes (20): bucket_range(), bucket_start(), build_series(), next_bucket(), date, Decimal, Granularity, ValueError (+12 more)

### Community 25 - "test_lacunas_dashboard.py"
Cohesion: 0.07
Nodes (28): _existing_purchase(), _position(), Cobertura das lacunas de back-end levantadas em `resume/06`. Mesmo padrão das…, A lista branca e o `Literal` da query precisam andar juntos. Se divergissem, ou…, O front precisa receber os dois tokens; sem isso a sessão não renova., Derrubar tudo é ação sobre a conta, não sobre o token apresentado., Revogada ou vencida não é aparelho conectado. As revogadas continuam na tabela…, A tela é de reconhecimento de aparelho, não de recuperação de credencial. (+20 more)

### Community 26 - "User"
Cohesion: 0.05
Nodes (63): downgrade(), upgrade(), get_client_ip(), get_current_user(), get_optional_user(), DatabaseSession, Request, IP de origem, usado pelo bloqueio progressivo do login. `X-Forwarded-For` só é… (+55 more)

### Community 31 - "4. Especificação por módulo"
Cohesion: 0.08
Nodes (24): 1. Ponto de partida, 2. Mapa: endpoint do back-end → tela do dashboard, 3. Arquitetura de rotas proposta (App Router), 4. Especificação por módulo, 5.1 A única lacuna que permanece, 5.2 Armadilhas de implementação herdadas do back-end, 5. Lacunas do back-end que limitam o dashboard, 6.1 Ativos (`/investments/assets`) (+16 more)

### Community 40 - "Base"
Cohesion: 0.16
Nodes (13): Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online(), Base, Configuração do engine SQLAlchemy e sessão do banco (Supabase PostgreSQL)., Classe base declarativa para todos os models SQLAlchemy., ImportJob (+5 more)

### Community 45 - "Fases"
Cohesion: 0.09
Nodes (22): Como o BFF funciona, Context, Decisões de arquitetura, Estrutura de arquivos, Fase 0 — Higiene e fundação do projeto, Fase 1 — BFF, sessão e contrato de tipos, Fase 2 — Auth UI e shell do dashboard, Fase 3 — Transações (+14 more)

### Community 46 - "DatabaseSession"
Cohesion: 0.17
Nodes (28): _asset_movements(), create_asset(), create_movement(), delete_asset(), delete_movement(), export_portfolio(), list_assets(), list_movements() (+20 more)

### Community 47 - "FakeSession"
Cohesion: 0.08
Nodes (39): list_sessions(), Aparelhos com sessão viva, da atividade mais recente para a mais antiga. Exige…, generate_refresh_token(), hash_refresh_token(), Devolve (valor entregue ao cliente, hash guardado no banco, expiração). O valor…, SHA-256 em hexadecimal — cabe no `String(64)` e é indexável., Sessão de longa duração, revogável, de um usuário. O valor entregue ao cliente…, RefreshToken (+31 more)

### Community 48 - "transactions.py"
Cohesion: 0.18
Nodes (28): _as_utc(), _conditions(), create_transaction(), delete_transaction(), export_transactions(), get_import_job(), get_transaction(), list_categories() (+20 more)

### Community 49 - "devDependencies"
Cohesion: 0.10
Nodes (21): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, tailwindcss, @testing-library/react, @testing-library/user-event (+13 more)

### Community 52 - "quote_refresh.py"
Cohesion: 0.20
Nodes (20): InvestmentAsset, MarketQuote, PortfolioSnapshot, Histórico de cotações; nunca sobrescreve o timestamp anterior., fetch_brapi_quotes(), MarketProviderError, _parse_datetime(), datetime (+12 more)

### Community 53 - "Viabilidade de cobrir as lacunas do back-end"
Cohesion: 0.12
Nodes (15): 1.1 A suíte de testes não toca banco de dados, 1.2 Não existe infraestrutura de e-mail, 1.3 Ponto favorável: o banco é Postgres em todo lugar, 1. Duas descobertas do repositório que mudam a estimativa, 2. Triagem das 14 lacunas, 3. Quadro-resumo, 4. Ordem de execução sugerida, quando houver decisão, 5. Pendências que aguardam decisão (+7 more)

### Community 54 - "Pendências futuras"
Cohesion: 0.12
Nodes (15): 1. O caminho crítico, 2.1 Hospedagem, 2.2 Migrations no Supabase, 2.3 Configuração de ambiente, 2.4 Tarefas agendadas, 2. Deploy e operação, 3. Front-end, 4.1 Validação manual (18 itens) (+7 more)

### Community 55 - "list_snapshots"
Cohesion: 0.50
Nodes (5): _as_utc(), list_snapshots(), datetime, Curva do patrimônio investido, em ordem cronológica. A tabela é alimentada por…, Exige fuso explícito. O módulo de investimentos não assume `America/Sao_Paulo`…

### Community 56 - "v1/telegram.py"
Cohesion: 0.15
Nodes (20): create_telegram_link(), _published_policy(), Endpoint de webhook do Telegram (seção 3.1 do guia)., Gera o Deep Link somente depois do aceite versionado de privacidade., get_privacy_policy(), PrivacyPolicy, Políticas de privacidade publicadas e imutáveis do canal Telegram., Retorna somente políticas efetivamente publicadas. (+12 more)

### Community 57 - "TelegramCard.tsx"
Cohesion: 0.14
Nodes (21): TelegramCard(), formatCountdown(), TelegramConnectFlow(), useCountdownSeconds(), Button(), ButtonProps, Variant, VARIANT_CLASS (+13 more)

### Community 58 - "types.ts"
Cohesion: 0.07
Nodes (26): AssetResponse, AssetType, CategoryOption, CategorySummary, CompoundInterestPoint, CompoundInterestResponse, FinancialSummary, ImportJobListResponse (+18 more)

### Community 59 - "period.ts"
Cohesion: 0.12
Nodes (26): PeriodSelector(), previousLocalDate(), toDateInputValue(), dateFormatter, dateTimeFormatter, formatBRL(), FormatBRLOptions, formatPercent() (+18 more)

### Community 60 - "RegisterForm.tsx"
Cohesion: 0.15
Nodes (17): metadata, ForcePasswordChangeForm(), PasswordChecklist(), RegisterForm(), Alert(), Variant, VARIANT_CLASS, VARIANT_ICON (+9 more)

### Community 61 - "telegram_webhook"
Cohesion: 0.26
Nodes (12): current_telegram_privacy_policy(), _policy_response(), get, post, Request, Recebe os updates do Telegram. Responde 200 imediatamente e processa a mensagem…, Publica o aviso vigente antes de qualquer coleta de consentimento., Mantém cada aviso publicado acessível por uma URL estável e versionada. (+4 more)

### Community 62 - "api/auth.ts"
Cohesion: 0.16
Nodes (14): DashboardLayout(), DashboardShell(), Topbar(), UserMenu(), Skeleton(), authHttp, AuthResult, ChangePasswordPayload (+6 more)

### Community 63 - "http.ts"
Cohesion: 0.27
Nodes (7): attemptRefresh(), axios, ensureFreshSession(), http, InternalAxiosRequestConfig, readSessEpoch(), runExclusive()

### Community 64 - "delete_telegram_link"
Cohesion: 0.29
Nodes (8): delete_telegram_link(), CurrentUser, DatabaseSession, delete, Revoga o vínculo com o Telegram preservando a trilha de consentimento. A linha…, telegram_link_status(), TelegramLinkStatus, TelegramUnlinkResponse

### Community 65 - "errors.ts"
Cohesion: 0.33
Nodes (7): AxiosLikeError, describeApiError(), FieldError, NormalizedApiError, normalizeDetail(), normalizeValidationItem(), STATUS_MESSAGES

### Community 66 - "LoginForm.tsx"
Cohesion: 0.12
Nodes (19): metadata, LoginForm(), PasswordHint(), TextField, TextFieldProps, login(), readRetryAfterSeconds(), changePasswordSchema (+11 more)

### Community 67 - "test_issue_hardening.py"
Cohesion: 0.15
Nodes (14): import_file(), post, field_validator, RegisterRequest, parametrize, test_asset_lock_uses_select_for_update(), test_bcrypt_limit_is_enforced_in_utf8_bytes(), test_import_stops_when_row_limit_is_exceeded() (+6 more)

### Community 68 - "quantize_money"
Cohesion: 0.60
Nodes (5): decimal_from_value(), Decimal, quantize_money(), Converte sem passar por float e entende os formatos 1234.56 e 1.234,56., test_money_uses_commercial_rounding_and_brazilian_input()

### Community 69 - "test_telegram_privacy_and_exports.py"
Cohesion: 0.20
Nodes (10): _escape_spreadsheet_formula(), export_csv(), export_xlsx(), Mantém texto controlado pelo usuário inerte em CSV e XLSX., _formula_transaction(), PendingDb, test_active_pending_transaction_is_returned(), test_csv_export_escapes_formula_prefixes() (+2 more)

### Community 70 - "LoginBlocked"
Cohesion: 0.33
Nodes (5): LoginBlocked, Escopo bloqueado. `retry_after` é o que vai no cabeçalho da resposta., Bloqueio existe para não fazer o trabalho — nem bcrypt, nem consulta., test_blocked_login_answers_429_without_touching_the_password(), Exception

### Community 71 - "package.json"
Cohesion: 0.18
Nodes (10): name, private, scripts, build, dev, lint, start, test (+2 more)

### Community 73 - "TelegramToken"
Cohesion: 0.33
Nodes (6): Concurrent Balance Query Index, downgrade(), Deny-by-Default Row Level Security, upgrade(), Vincula um chat_id do Telegram a um usuário autenticado do sistema. Ciclo de…, TelegramToken

### Community 74 - "purge_access_lifecycle.py"
Cohesion: 0.29
Nodes (8): main(), purge_login_attempts(), purge_refresh_tokens(), datetime, Session, Limpa as tabelas de ciclo de acesso: sessões expiradas e contadores de login.…, Apaga sessões vencidas há mais tempo que a carência., Apaga contadores que já não bloqueiam nem contam nada. O corte é o mesmo…

### Community 75 - "Sidebar.tsx"
Cohesion: 0.40
Nodes (5): isActive(), NAV_ITEMS, NavItem, PERIOD_PARAM_KEYS, Sidebar()

### Community 79 - "schemas/import_job.py"
Cohesion: 0.67
Nodes (3): ImportJobListResponse, ImportJobResponse, BaseModel

## Knowledge Gaps
- **296 isolated node(s):** `metadata`, `metadata`, `BLOCKED_AUTH_SUBPATHS`, `FORWARDED_RESPONSE_HEADERS`, `RouteContext` (+291 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `User` connect `User` to `telegram_bot.py`, `v1/auth.py`, `Base`, `TelegramToken`, `transactions.py`, `v1/telegram.py`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Why does `TransacaoExtraida` connect `TransacaoExtraida` to `telegram_bot.py`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `FakeSession` (e.g. with `RefreshToken` and `ChangePasswordRequest`) actually correct?**
  _`FakeSession` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Base` (e.g. with `ImportJob` and `InvestmentAsset`) actually correct?**
  _`Base` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `timedelta` (e.g. with `_series_bounds()` and `_portfolio()`) actually correct?**
  _`timedelta` has 21 INFERRED edges - model-reasoned connections that need verification._
- **What connects `metadata`, `metadata`, `BLOCKED_AUTH_SUBPATHS` to the rest of the system?**
  _296 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `telegram_bot.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13846153846153847 - nodes in this community are weakly interconnected._