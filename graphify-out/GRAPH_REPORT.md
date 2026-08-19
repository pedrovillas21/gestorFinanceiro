# Graph Report - gestorFinanceiro  (2026-08-18)

## Corpus Check
- 172 files · ~81,462 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1478 nodes · 3126 edges · 107 communities (84 shown, 23 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 111 edges (avg confidence: 0.65)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bbf35e4b`
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
- v1/telegram.py
- telegram_client.py
- Funcionalidades disponíveis somente para API Web/dashboard
- dashboard.py
- FakeSession
- compilerOptions
- test_periodos.py
- **4\. Regras de Negócio Fundamentais**
- 3c7f1a9b2d84_create_missing_processed_telegram_updates.py
- cookies.ts
- toast.tsx
- Back-end — Gestor Financeiro com IA
- Relatório 01 — Fundação, autenticação e gestão financeira
- Relatório 02 — Investimentos, cotações e simulador
- Relatório 03 — Confirmações do bot, operação e validação final
- ThrottleState
- Lacunas do back-end — relatório de implementação
- build_series
- test_lacunas_dashboard.py
- login
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
- RefreshToken
- transactions.py
- devDependencies
- BaseModel
- RLS obrigatÃ³rio
- quote_refresh.py
- Viabilidade de cobrir as lacunas do back-end
- Pendências futuras
- list_snapshots
- User
- TelegramConnectFlow.tsx
- types.ts
- period.ts
- RegisterForm.tsx
- get_privacy_policy
- api/auth.ts
- http.ts
- create_telegram_link
- errors.ts
- LoginForm.tsx
- test_issue_hardening.py
- quantize_money
- test_telegram_privacy_and_exports.py
- login_throttle.py
- package.json
- ComingSoon.tsx
- Deny-by-Default Row Level Security
- purge_refresh_tokens
- Sidebar.tsx
- transactions.ts
- schemas/import_job.py
- react
- react-dom
- @tailwindcss/postcss
- @tanstack/react-table
- jsdom
- @vitejs/plugin-react
- vitest
- Projeto Next.js inicial
- TransactionsTable.tsx
- TransactionForm.tsx
- security.py
- QuoteRefreshDb
- transacoes/page.tsx
- dependencies.py
- schemas/transaction.py
- v1/calculator.py
- format.ts
- SimpleNamespace
- schemas/auth.ts
- timedelta
- _portfolio
- telegram_webhook
- config.py
- lock_duration
- upgrade

## God Nodes (most connected - your core abstractions)
1. `FakeSession` - 28 edges
2. `Base` - 26 edges
3. `User` - 26 edges
4. `Transaction` - 23 edges
5. `readSession()` - 21 edges
6. `RefreshToken` - 20 edges
7. `TransacaoExtraida` - 20 edges
8. `describeError()` - 19 edges
9. `send_message()` - 18 edges
10. `calculate_position()` - 17 edges

## Surprising Connections (you probably didn't know these)
- `Descarte de updates pendentes` --rationale_for--> `set_webhook()`  [INFERRED]
  resume/como-rodar-o-bot.md → backend/app/services/telegram_client.py
- `Fluxo implementado do bot` --references--> `criar_link_token()`  [EXTRACTED]
  resume/bot-telegram-status.md → backend/app/services/telegram_bot.py
- `main()` --implements--> `Provisionamento do Bot do Telegram`  [EXTRACTED]
  backend/scripts/setup_telegram_bot.py → plan/Guia de Criacao e Configuracao - Bot do Telegram com IA.md
- `RotaÃ§Ã£o do Quick Tunnel` --rationale_for--> `main()`  [EXTRACTED]
  resume/como-rodar-o-bot.md → backend/scripts/setup_telegram_bot.py
- `OperaÃ§Ã£o em trÃªs terminais` --references--> `main()`  [EXTRACTED]
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

## Communities (107 total, 23 thin omitted)

### Community 0 - "telegram_bot.py"
Cohesion: 0.16
Nodes (34): Vincula um chat_id do Telegram a um usuário autenticado do sistema. Ciclo de…, TelegramToken, _buscar_pendencia(), _buscar_vinculo(), _cmd_saldo(), _cmd_start(), _concluir_pendencia(), _confirmar_transacao() (+26 more)

### Community 1 - "v1/investments.py"
Cohesion: 0.19
Nodes (17): AssetCreate, AssetResponse, AssetUpdate, MovementCreate, MovementResponse, MovementUpdate, PortfolioResponse, PositionResponse (+9 more)

### Community 2 - "test_investments.py"
Cohesion: 0.14
Nodes (27): calculate_compound_interest(), calculate_position(), calculate_twr(), calculate_xirr(), CalculatedPosition, InvestmentCalculationError, movement_cash_flow(), MovementLike (+19 more)

### Community 3 - "TransacaoExtraida"
Cohesion: 0.06
Nodes (46): Check Extracted Transaction Coherence, _config(), extrair_transacao(), GeminiIndisponivelError, get_client(), _parse(), PERIODOS_SALDO, Balance Period Contract (+38 more)

### Community 4 - "spreadsheets.py"
Cohesion: 0.14
Nodes (24): _csv_rows(), export_movements_csv(), import_transactions(), _limited_rows(), _movement_row(), _normalized_headers(), _optional(), _parse_datetime() (+16 more)

### Community 5 - "dependencies"
Cohesion: 0.10
Nodes (21): axios, decimal.js, dependencies, axios, decimal.js, @hookform/resolvers, lucide-react, next (+13 more)

### Community 6 - "v1/auth.py"
Cohesion: 0.20
Nodes (19): patch, update_profile(), ChangePasswordRequest, is_password_compliant(), LoginRequest, LogoutRequest, MessageResponse, ProfileUpdate (+11 more)

### Community 7 - "v1/telegram.py"
Cohesion: 0.18
Nodes (18): Endpoint de webhook do Telegram (seção 3.1 do guia)., PrivacyPolicyResponse, BaseModel, Subconjunto do payload de Update da Bot API do Telegram. Só mapeamos os campos…, Cobre tanto `voice` quanto `audio` — só precisamos do file_id e do tamanho., Confirma a revogação e devolve o consentimento que ficou registrado., TelegramBase, TelegramCallbackQuery (+10 more)

### Community 8 - "telegram_client.py"
Cohesion: 0.07
Nodes (42): Any, Settings, SessionLocal, montar_deep_link(), Deep Link do Telegram que dispara `/start <link_token>` no bot., answer_callback_query(), _api_url(), call() (+34 more)

### Community 9 - "Funcionalidades disponíveis somente para API Web/dashboard"
Cohesion: 0.10
Nodes (19): 1. Conexão segura entre conta Web e chat, 2. Registro de receitas e despesas por IA, 3. Consulta de saldo, 4. Comandos e proteção operacional, Arquivos principais usados neste levantamento, Autenticação e conta, Carteira de investimentos, Cotações de mercado (+11 more)

### Community 10 - "dashboard.py"
Cohesion: 0.19
Nodes (18): financial_summary(), financial_timeseries(), CurrentUser, DatabaseSession, date, datetime, Decimal, get (+10 more)

### Community 11 - "FakeSession"
Cohesion: 0.11
Nodes (20): hash_refresh_token(), SHA-256 em hexadecimal — cabe no `String(64)` e é indexável., FakeSession, Sessão mínima do SQLAlchemy: só o que `app.services.sessions` usa. Suficiente…, Reapresentar um token já rotacionado é o sinal clássico de vazamento. Duas…, Sem `FOR UPDATE`, duas chamadas com o mesmo token rotacionam as duas. As duas…, Quem está com o access token vencido ainda precisa conseguir deslogar., O caso que motivou a mudança: access token vencido, sessão viva no servidor. (+12 more)

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

### Community 17 - "toast.tsx"
Cohesion: 0.07
Nodes (32): geistMono, geistSans, metadata, handleAuthErrors(), Providers(), ICON, LABEL, ORDER (+24 more)

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

### Community 22 - "ThrottleState"
Cohesion: 0.21
Nodes (17): forget_stale_failures(), datetime, Aplica uma falha à escada e devolve a situação nova., Situação de um escopo. Sem banco e sem I/O — só a aritmética da escada., Quanto falta do bloqueio, arredondado para cima. 0 quando liberado., Esquece o que já não diz mais nada sobre quem está chamando agora., register_failure(), seconds_until_release() (+9 more)

### Community 23 - "Lacunas do back-end — relatório de implementação"
Cohesion: 0.05
Nodes (41): 10. C2 — reset de senha por e-mail (fora do escopo), 11. Inventário de arquivos, 1.1 Revisão de 14/08/2026, 1.2 Auditoria de 17/08/2026, 1. Resumo executivo, 2.1 Decisão menor tomada sem consulta, 2. Decisões tomadas, 3.1 ⚠️ Editar o `.env` do back-end (+33 more)

### Community 24 - "build_series"
Cohesion: 0.17
Nodes (19): bucket_range(), bucket_start(), build_series(), next_bucket(), date, Decimal, Granularity, ValueError (+11 more)

### Community 25 - "test_lacunas_dashboard.py"
Cohesion: 0.11
Nodes (22): export_portfolio_xlsx(), export_positions_csv(), _position_row(), Carteira em duas abas: consolidado e extrato. Cada uma responde a uma pergunta…, _existing_purchase(), _position(), Cobertura das lacunas de back-end levantadas em `resume/06`. Mesmo padrão das…, A lista branca e o `Literal` da query precisam andar juntos. Se divergissem, ou… (+14 more)

### Community 26 - "login"
Cohesion: 0.14
Nodes (27): change_password(), delete_account(), list_sessions(), login(), logout(), me(), CurrentUser, DatabaseSession (+19 more)

### Community 31 - "4. Especificação por módulo"
Cohesion: 0.08
Nodes (24): 1. Ponto de partida, 2. Mapa: endpoint do back-end → tela do dashboard, 3. Arquitetura de rotas proposta (App Router), 4. Especificação por módulo, 5.1 A única lacuna que permanece, 5.2 Armadilhas de implementação herdadas do back-end, 5. Lacunas do back-end que limitam o dashboard, 6.1 Ativos (`/investments/assets`) (+16 more)

### Community 40 - "Base"
Cohesion: 0.18
Nodes (12): Base, Configuração do engine SQLAlchemy e sessão do banco (Supabase PostgreSQL)., Classe base declarativa para todos os models SQLAlchemy., ImportJob, Acompanha imports grandes processados fora do request HTTP., Importa todos os models para que Base.metadata os enxergue (necessário para o…, PendingTransaction, Estado curto para confirmação explícita de extrações incertas do bot. (+4 more)

### Community 45 - "Fases"
Cohesion: 0.09
Nodes (22): Como o BFF funciona, Context, Decisões de arquitetura, Estrutura de arquivos, Fase 0 — Higiene e fundação do projeto, Fase 1 — BFF, sessão e contrato de tipos, Fase 2 — Auth UI e shell do dashboard, Fase 3 — Transações (+14 more)

### Community 46 - "DatabaseSession"
Cohesion: 0.22
Nodes (23): _asset_movements(), create_asset(), create_movement(), delete_asset(), delete_movement(), _latest_quote(), list_movements(), _movements_with_ticker() (+15 more)

### Community 47 - "RefreshToken"
Cohesion: 0.14
Nodes (20): Sessão de longa duração, revogável, de um usuário. O valor entregue ao cliente…, RefreshToken, issue_refresh_token(), list_active_sessions(), Session, UUID, ValueError, Emissão, rotação e revogação das sessões de refresh token. Concentrar isto num… (+12 more)

### Community 48 - "transactions.py"
Cohesion: 0.17
Nodes (28): _conditions(), create_transaction(), delete_transaction(), export_transactions(), get_import_job(), get_transaction(), list_categories(), list_import_jobs() (+20 more)

### Community 49 - "devDependencies"
Cohesion: 0.10
Nodes (21): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, tailwindcss, @testing-library/react, @testing-library/user-event (+13 more)

### Community 52 - "quote_refresh.py"
Cohesion: 0.29
Nodes (14): InvestmentAsset, MarketQuote, PortfolioSnapshot, Histórico de cotações; nunca sobrescreve o timestamp anterior., _create_snapshot(), _latest_quote(), datetime, Session (+6 more)

### Community 53 - "Viabilidade de cobrir as lacunas do back-end"
Cohesion: 0.12
Nodes (15): 1.1 A suíte de testes não toca banco de dados, 1.2 Não existe infraestrutura de e-mail, 1.3 Ponto favorável: o banco é Postgres em todo lugar, 1. Duas descobertas do repositório que mudam a estimativa, 2. Triagem das 14 lacunas, 3. Quadro-resumo, 4. Ordem de execução sugerida, quando houver decisão, 5. Pendências que aguardam decisão (+7 more)

### Community 54 - "Pendências futuras"
Cohesion: 0.12
Nodes (15): 1. O caminho crítico, 2.1 Hospedagem, 2.2 Migrations no Supabase, 2.3 Configuração de ambiente, 2.4 Tarefas agendadas, 2. Deploy e operação, 3. Front-end, 4.1 Validação manual (18 itens) (+7 more)

### Community 55 - "list_snapshots"
Cohesion: 0.29
Nodes (8): _as_utc(), _decimal(), list_snapshots(), _movement_values(), datetime, Curva do patrimônio investido, em ordem cronológica. A tabela é alimentada por…, Exige fuso explícito. O módulo de investimentos não assume `America/Sao_Paulo`…, Aplica a escala de cada coluna antes de gravar. As casas decimais são as do…

### Community 56 - "User"
Cohesion: 0.20
Nodes (10): get_db(), Dependency do FastAPI para obter uma sessão de banco por requisição., User, Gera o Deep Link de vínculo de um usuário com o bot do Telegram. Enquanto a…, Conta anterior à regra de complexidade: o login é o único ponto que ainda vê a…, Senha antiga que por acaso já cumpre a regra nova não pede troca à toa., `must_change_password=True` barra o resto da API, mas não vira uma cela: a…, test_blocked_account_keeps_the_right_to_leave() (+2 more)

### Community 57 - "TelegramConnectFlow.tsx"
Cohesion: 0.24
Nodes (11): formatCountdown(), TelegramConnectFlow(), useCountdownSeconds(), http, createTelegramLink(), CreateTelegramLinkPayload, getTelegramPrivacyPolicy(), PrivacyPolicyResponse (+3 more)

### Community 58 - "types.ts"
Cohesion: 0.08
Nodes (24): SOURCE_META, UNKNOWN_META, AssetResponse, AssetType, CategorySummary, CompoundInterestPoint, CompoundInterestResponse, FinancialSummary (+16 more)

### Community 59 - "period.ts"
Cohesion: 0.23
Nodes (16): PeriodSelector(), previousLocalDate(), toDateInputValue(), addDays(), computePeriodRange(), PERIOD_PRESET_LABELS, PERIOD_PRESETS, PeriodPreset (+8 more)

### Community 60 - "RegisterForm.tsx"
Cohesion: 0.15
Nodes (15): metadata, ForcePasswordChangeForm(), PasswordChecklist(), RegisterForm(), Alert(), Variant, VARIANT_CLASS, VARIANT_ICON (+7 more)

### Community 61 - "get_privacy_policy"
Cohesion: 0.20
Nodes (14): current_telegram_privacy_policy(), _policy_response(), _published_policy(), get, Request, Publica o aviso vigente antes de qualquer coleta de consentimento., Mantém cada aviso publicado acessível por uma URL estável e versionada., telegram_privacy_policy_version() (+6 more)

### Community 62 - "api/auth.ts"
Cohesion: 0.17
Nodes (15): DashboardLayout(), DashboardShell(), Topbar(), UserMenu(), authHttp, AuthResult, ChangePasswordPayload, fetchCurrentUser() (+7 more)

### Community 63 - "http.ts"
Cohesion: 0.31
Nodes (6): attemptRefresh(), axios, ensureFreshSession(), InternalAxiosRequestConfig, readSessEpoch(), runExclusive()

### Community 64 - "create_telegram_link"
Cohesion: 0.22
Nodes (11): create_telegram_link(), delete_telegram_link(), CurrentUser, DatabaseSession, delete, Revoga o vínculo com o Telegram preservando a trilha de consentimento. A linha…, Gera o Deep Link somente depois do aceite versionado de privacidade., telegram_link_status() (+3 more)

### Community 65 - "errors.ts"
Cohesion: 0.33
Nodes (7): AxiosLikeError, describeApiError(), FieldError, NormalizedApiError, normalizeDetail(), normalizeValidationItem(), STATUS_MESSAGES

### Community 66 - "LoginForm.tsx"
Cohesion: 0.20
Nodes (9): metadata, LoginForm(), PasswordHint(), TextField, TextFieldProps, login(), readRetryAfterSeconds(), LoginInput (+1 more)

### Community 67 - "test_issue_hardening.py"
Cohesion: 0.11
Nodes (20): Rotas da versão 1 da API., _cors_origins_with_credentials(), health_check(), lifespan(), get, Executa automaticamente todas as migrations pendentes do Alembic no Supabase., run_migrations(), field_validator (+12 more)

### Community 68 - "quantize_money"
Cohesion: 0.60
Nodes (5): decimal_from_value(), Decimal, quantize_money(), Converte sem passar por float e entende os formatos 1234.56 e 1.234,56., test_money_uses_commercial_rounding_and_brazilian_input()

### Community 69 - "test_telegram_privacy_and_exports.py"
Cohesion: 0.16
Nodes (21): _escape_spreadsheet_formula(), export_csv(), export_transactions_pdf(), export_xlsx(), _format_brl(), _format_date_ptbr(), _format_datetime_ptbr(), _format_period_label() (+13 more)

### Community 70 - "login_throttle.py"
Cohesion: 0.11
Nodes (24): LoginAttempt, Contador de falhas de login, por escopo, para o bloqueio progressivo. Uma linha…, check_login_allowed(), clear_login_failures(), LoginBlocked, Session, Bloqueio progressivo do login — a defesa contra força bruta na senha. A senha é…, SHA-256 de `tipo:valor` — a tabela nunca vê o e-mail nem o IP em claro. (+16 more)

### Community 71 - "package.json"
Cohesion: 0.18
Nodes (10): name, private, scripts, build, dev, lint, start, test (+2 more)

### Community 73 - "Deny-by-Default Row Level Security"
Cohesion: 0.50
Nodes (4): Concurrent Balance Query Index, downgrade(), Deny-by-Default Row Level Security, upgrade()

### Community 74 - "purge_refresh_tokens"
Cohesion: 0.33
Nodes (7): main(), purge_login_attempts(), purge_refresh_tokens(), datetime, Session, Apaga sessões vencidas há mais tempo que a carência., Apaga contadores que já não bloqueiam nem contam nada. O corte é o mesmo…

### Community 75 - "Sidebar.tsx"
Cohesion: 0.40
Nodes (5): isActive(), NAV_ITEMS, NavItem, PERIOD_PARAM_KEYS, Sidebar()

### Community 78 - "transactions.ts"
Cohesion: 0.16
Nodes (13): TransactionFiltersValue, PAGINATION, PaginationKey, EXPORT_FILENAME_FALLBACK, ExportFormat, ExportResult, ExportTransactionsParams, ListTransactionCategoriesParams (+5 more)

### Community 79 - "schemas/import_job.py"
Cohesion: 0.67
Nodes (3): ImportJobListResponse, ImportJobResponse, BaseModel

### Community 90 - "TransactionsTable.tsx"
Cohesion: 0.17
Nodes (17): TelegramCard(), downloadBlob(), ExportButton(), SourceBadge(), COLUMNS, SortableColumn, SortState, TransactionsTable() (+9 more)

### Community 91 - "TransactionForm.tsx"
Cohesion: 0.16
Nodes (16): TransactionFilters(), pad(), toDateTimeLocalValue(), TransactionForm(), TransactionFormProps, TransactionFormModal(), Select, SelectProps (+8 more)

### Community 92 - "security.py"
Cohesion: 0.22
Nodes (14): create_access_token(), decode_access_token(), generate_refresh_token(), hash_password(), InvalidCredentialsError, _password_bytes(), datetime, UUID (+6 more)

### Community 93 - "QuoteRefreshDb"
Cohesion: 0.17
Nodes (10): fetch_brapi_quotes(), FetchedQuote, MarketProviderError, _parse_datetime(), datetime, RuntimeError, Fetch quotes keyed by stripped, upper-case ticker symbols., QuoteRefreshDb (+2 more)

### Community 94 - "transacoes/page.tsx"
Cohesion: 0.19
Nodes (10): TransactionsPageContent(), TransactionsPagination(), Button(), ButtonProps, Variant, VARIANT_CLASS, ErrorState(), Spinner() (+2 more)

### Community 95 - "dependencies.py"
Cohesion: 0.19
Nodes (14): get_client_ip(), get_current_user(), get_optional_user(), DatabaseSession, Request, IP de origem, usado pelo bloqueio progressivo do login. `X-Forwarded-For` só é…, Identifica quem chama, sem exigir que a identificação exista. Credencial…, Barra toda ação autenticada de quem está com `must_change_password=True`. Sem… (+6 more)

### Community 96 - "schemas/transaction.py"
Cohesion: 0.21
Nodes (12): CategoryOption, FinancialSummary, BaseModel, Decimal, field_validator, Categoria já usada pelo usuário, com a frequência para ordenar o filtro., TimeseriesResponse, TransactionBase (+4 more)

### Community 97 - "v1/calculator.py"
Cohesion: 0.23
Nodes (10): compound_interest(), post, CompoundInterestPoint, CompoundInterestRequest, CompoundInterestResponse, BaseModel, Decimal, field_validator (+2 more)

### Community 98 - "format.ts"
Cohesion: 0.27
Nodes (9): dateFormatter, dateTimeFormatter, formatBRL(), FormatBRLOptions, formatPercent(), FormatPercentOptions, formatQuantity(), groupThousands() (+1 more)

### Community 99 - "SimpleNamespace"
Cohesion: 0.20
Nodes (10): import_file(), post, test_twr_chains_subperiods_and_annualizes_only_after_30_days(), test_large_upload_payload_is_persisted_for_worker(), test_upload_read_is_bounded(), test_link_generation_rejects_unpublished_policy_before_database_access(), test_only_the_current_published_policy_is_valid_consent(), MonkeyPatch (+2 more)

### Community 100 - "schemas/auth.ts"
Cohesion: 0.27
Nodes (9): changePasswordSchema, isPasswordCompliant(), PASSWORD_REQUIREMENTS, PasswordRequirement, passwordSchema, ProfileUpdateInput, profileUpdateSchema, registerSchema (+1 more)

### Community 101 - "timedelta"
Cohesion: 0.22
Nodes (6): criar_link_token(), Gera (ou renova) o token de vínculo de um usuário para uso no Deep Link.…, PendingDb, test_active_pending_transaction_is_returned(), test_expired_pending_transaction_is_deleted_and_not_returned(), timedelta

### Community 102 - "_portfolio"
Cohesion: 0.28
Nodes (9): export_portfolio(), get_portfolio(), list_assets(), _portfolio(), get, StreamingResponse, Ativos do usuário, por ticker. A resposta segue sendo uma lista pura, e não um…, Exporta a carteira. O XLSX leva as duas abas — posições consolidadas e extrato… (+1 more)

### Community 103 - "telegram_webhook"
Cohesion: 0.25
Nodes (8): post, Recebe os updates do Telegram. Responde 200 imediatamente e processa a mensagem…, telegram_webhook(), processar_update(), _processar_update_async(), Ponto de entrada do webhook. Roda em background: nunca propaga exceção., Executa o fluxo em uma thread com event loop privado. Por ser uma…, BackgroundTasks

### Community 104 - "config.py"
Cohesion: 0.29
Nodes (5): Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online(), Configurações da aplicação carregadas do .env via pydantic-settings.

### Community 105 - "lock_duration"
Cohesion: 0.50
Nodes (4): lock_duration(), Duração do bloqueio de número `lock_level` (1 = o primeiro)., `LEVEL_DECAY` tem de ser maior que o maior bloqueio. Iguais, a escada zerava no…, test_waiting_out_the_longest_block_does_not_reset_the_ladder()

## Knowledge Gaps
- **300 isolated node(s):** `metadata`, `metadata`, `BLOCKED_AUTH_SUBPATHS`, `FORWARDED_RESPONSE_HEADERS`, `RouteContext` (+295 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `User` connect `User` to `telegram_bot.py`, `v1/auth.py`, `Base`, `Deny-by-Default Row Level Security`, `upgrade`, `telegram_client.py`, `transactions.py`, `login`, `dependencies.py`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `Transaction` connect `transactions.py` to `telegram_bot.py`, `spreadsheets.py`, `test_telegram_privacy_and_exports.py`, `Base`, `Deny-by-Default Row Level Security`, `upgrade`, `dashboard.py`, `User`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Why does `TransacaoExtraida` connect `TransacaoExtraida` to `telegram_bot.py`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `FakeSession` (e.g. with `RefreshToken` and `ChangePasswordRequest`) actually correct?**
  _`FakeSession` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Base` (e.g. with `ImportJob` and `InvestmentAsset`) actually correct?**
  _`Base` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `timedelta` (e.g. with `_series_bounds()` and `_portfolio()`) actually correct?**
  _`timedelta` has 22 INFERRED edges - model-reasoned connections that need verification._
- **What connects `metadata`, `metadata`, `BLOCKED_AUTH_SUBPATHS` to the rest of the system?**
  _300 weakly-connected nodes found - possible documentation gaps or missing edges._