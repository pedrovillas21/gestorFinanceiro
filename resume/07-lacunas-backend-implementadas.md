# Lacunas do back-end — relatório de implementação

Data: 12/08/2026
Branch: `modelagemFrontEnd`
Origem: decisões tomadas sobre `06-viabilidade-cobertura-lacunas-backend.md`.
Escopo: **apenas back-end**. Nenhuma linha de front-end foi escrita.

---

## 1. Resumo executivo

Das 14 lacunas levantadas no documento 06, **13 foram implementadas**. A restante
(C2, reset de senha por e-mail) ficou fora por decisão registrada na seção 2.

| Métrica | Valor |
| --- | --- |
| Operações novas | 11, em 9 rotas novas |
| Operações alteradas | 6 |
| Migrations | 1 (`a91d3e5c7f60`) |
| Arquivos novos | 5 de código + 1 de teste |
| Arquivos alterados | 19 |
| Linhas | ~913 adicionadas, ~76 removidas |
| Testes | 87 passando (68 antes + 19 novos) |

**O que não está pronto para produção sem mais uma decisão:** a limpeza da tabela
`refresh_tokens` e o comportamento do logout com access token vencido — ambos
detalhados na seção 7.

---

## 2. Decisões tomadas

| # | Questão | Decisão |
| --- | --- | --- |
| C1 | Estratégia de sessão | **(b)** refresh token opaco em tabela, com rotação a cada uso e revogação |
| C1 | Validade dos tokens | Access **30 min**, refresh **30 dias** |
| A8 | Troca de senha e sessões abertas | Revoga todas as outras; a que trocou recebe um par novo. Cliente pode desligar com `revoke_other_sessions: false` |
| A9 | Desvincular Telegram | Preserva a linha e o histórico de consentimento; registra `unlinked_at` |
| B2 | Conteúdo da exportação | Posições **e** movimentações, em abas separadas |
| B3 | Contrato de paginação em investimentos | `limit`/`offset` mantendo **lista pura** (sem envelope, sem `total`) |
| C2 | Reset de senha por e-mail | **Fora do escopo** por ora |
| — | Testes | Padrão da casa agora; suíte de integração desenhada na seção 9 |

### 2.1 Decisão menor tomada sem consulta

Adicionei a coluna `telegram_tokens.unlinked_at` na mesma migration. Sem ela, um
vínculo revogado ficaria indistinguível de um que nunca foi concluído — `chat_id`
é nulo nos dois casos —, e a trilha de auditoria escolhida em A9 não teria o
"quando foi revogado". Custo: uma coluna nullable numa migration que já existia.

---

## 3. Ações necessárias antes de subir

### 3.1 ⚠️ Editar o `.env` do back-end

O `.env` atual tem `ACCESS_TOKEN_EXPIRE_MINUTES=10080`. **Variável de ambiente
vence o padrão do código**, então sem essa edição o access token continuaria
durando 7 dias e a revogação viraria decoração: um token roubado ou uma senha
trocada seguiriam valendo por uma semana.

```env
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=43200
```

O `.env.example` já foi atualizado.

### 3.2 Rodar a migration

```bash
cd backend && alembic upgrade head
```

Revisão `a91d3e5c7f60` (sobre `3c7f1a9b2d84`):

- cria `refresh_tokens` com RLS `ENABLE`/`FORCE` — o padrão do projeto para toda
  tabela com dado de usuário, estabelecido em `b75641c60d56`;
- adiciona `telegram_tokens.unlinked_at`.

O DDL foi conferido offline com `alembic upgrade 3c7f1a9b2d84:head --sql`.
**Não foi executado contra o Supabase.**

O `downgrade` derruba a tabela `refresh_tokens` inteira — ou seja, desfazer a
migration desloga todo mundo. É o comportamento correto, mas não é reversível
sem custo.

### 3.3 Consequência para as sessões existentes

Não há refresh token para quem já está logado. Os JWTs de 7 dias emitidos antes
do deploy continuam válidos até expirarem, mas **não renovam** — na primeira
falha o usuário vai para o login. É um logout diferido de toda a base; como o
front-end ainda não existe, o impacto real hoje é nulo.

---

## 4. Mudanças por área

### 4.1 Autenticação e sessões (C1, A7, A8)

**Tabela `refresh_tokens`** guarda o **SHA-256** do token opaco, nunca o valor
entregue ao cliente. SHA-256 e não bcrypt porque o segredo tem 256 bits de
entropia — não há o que adivinhar por força bruta — e bcrypt impediria a busca
por índice único.

Colunas: `token_hash` (único), `expires_at`, `revoked_at`, `replaced_by_id`,
`user_agent`, `last_used_at`, `created_at`.

**Rotação:** cada `POST /auth/refresh` revoga a linha apresentada, cria uma nova e
liga as duas por `replaced_by_id`. Essa coluna é o que distingue "rotacionado" de
"revogado no logout".

**Detecção de reuso:** reapresentar um token já rotacionado significa que duas
partes têm o mesmo segredo — o dono legítimo e quem copiou. Como não há como
saber qual está chamando, a resposta é derrubar **todas** as sessões do usuário.
Token apenas vencido ou desconhecido é rotina e não dispara isso.

`register` e `login` passam a devolver `refresh_token` e `refresh_expires_at`.

O `user_agent` é capturado por header opcional — um cliente sem User-Agent
(script, curl) continua conseguindo logar.

### 4.2 Dashboard (A1, A2)

`GET /dashboard/timeseries` agrega com
`date_trunc(granularidade, occurred_at AT TIME ZONE 'America/Sao_Paulo')`.
Agregar pelo UTC cru jogaria um gasto das 22h de 31/01 (01:00 UTC de 01/02) para
fevereiro.

A aritmética de calendário — quais períodos existem entre duas datas — ficou em
`app/services/timeseries.py`, como função pura. É a única parte desta
funcionalidade que a suíte atual consegue cobrir.

Períodos sem lançamento vêm preenchidos com zero: um mês sem gasto precisa
aparecer como zero no eixo, não sumir do gráfico.

### 4.3 Transações (A3, A4, A5)

A lista branca de ordenação (`ORDERABLE_COLUMNS`) e o `Literal` da query são
verificados por teste — se divergissem, ou uma coluna aceita pelo tipo faltaria
no dicionário (KeyError em produção), ou o dicionário exporia uma coluna que a
API não deveria deixar ordenar.

O desempate por `id` é sempre aplicado: `amount` e `category` repetem muito, e
sem critério estável a paginação por offset devolve a mesma linha em duas
páginas e pula outra.

`GET /transactions/imports` não menciona a coluna `content` — que é `deferred` no
model justamente por guardar o arquivo inteiro em `LargeBinary`.

### 4.4 Investimentos (A6, B1, B2, B3)

`PATCH /investments/movements/{id}` funde o envio parcial com a linha atual e
valida o **resultado inteiro** por `MovementCreate`. A razão: a regra por tipo de
movimento depende do estado final, não do corpo. Trocar só o `movement_type` de
`purchase` para `dividend` muda quais campos passam a ser obrigatórios — validar
o envio isolado deixaria isso passar.

A validação de custódia roda sobre uma cópia **transitória** (fora da sessão do
SQLAlchemy): se a custódia não fecha, a linha persistida não chegou a ser tocada
e não há nada para desfazer. Mesmo padrão do `POST`, inclusive o `FOR UPDATE` no
ativo.

`GET /investments/export`: o XLSX leva as duas abas; o CSV não tem abas, então
`sheet=positions|movements` escolhe qual sai. Reusa a neutralização de textos que
o Excel interpretaria como fórmula.

Na exportação, campo nulo vira célula **vazia**, nunca zero — uma posição sem
cotação tem `market_value` nulo, e escrever 0 diria que ela não vale nada, que é
uma afirmação diferente de "não sei quanto vale".

### 4.5 Telegram (A9)

`DELETE /telegram/link` zera `chat_id`, `link_token`, `link_token_expires_at` e
`linked_at`, preenche `unlinked_at` e **preserva** `privacy_consent_version` e
`privacy_consented_at`.

O que precisa sumir de fato é o `chat_id`: enquanto ele existir, o bot segue
aceitando mensagens daquele chat como se fossem do usuário.

Apaga também a `PendingTransaction` daquele chat — ela guarda dados de uma
transação e ficaria órfã, esperando um "sim" que não pode mais chegar.

---

## 5. Referência dos endpoints

### Novos

| Método | Rota | Autenticado | Observações |
| --- | --- | --- | --- |
| POST | `/auth/refresh` | Não | Público de propósito: existe para quando o access token já expirou. Corpo `{refresh_token}`. Devolve par novo |
| POST | `/auth/logout` | Sim | `{refresh_token}` ou `{all_devices: true}` |
| POST | `/auth/change-password` | Sim | `{current_password, new_password, revoke_other_sessions?}`. 401 se a senha atual erra; 422 se a nova é igual à anterior |
| PATCH | `/auth/me` | Sim | Só `full_name`. Nome em branco vira `null` |
| GET | `/dashboard/timeseries` | Sim | `granularity=day\|week\|month` (padrão `month`), `start`, `end`. 422 acima de 1000 pontos |
| GET | `/transactions/categories` | Sim | `start`, `end`, `type`. Lista `{category, count}` por frequência. Nulos e vazios não geram opção |
| GET | `/transactions/imports` | Sim | Envelope `{items, total, limit, offset}` |
| GET | `/investments/snapshots` | Sim | `start`, `end`, `limit`. Lista pura, cronológica |
| GET | `/investments/export` | Sim | `format=csv\|xlsx`, `sheet=positions\|movements` |
| PATCH | `/investments/movements/{id}` | Sim | Envio parcial. 422 na custódia negativa |
| DELETE | `/telegram/link` | Sim | 404 se não havia vínculo |

> São 11 linhas para 9 endpoints novos: `PATCH /auth/me` e `DELETE /telegram/link`
> são métodos novos em rotas que já existiam.

### Alterados

| Rota | Mudança | Quebra contrato? |
| --- | --- | --- |
| `POST /auth/register` | Resposta ganhou `refresh_token`, `refresh_expires_at` | Não (aditivo) |
| `POST /auth/login` | Idem | Não (aditivo) |
| `GET /dashboard/summary` | Parâmetro `type` (padrão `expense`); resposta ganhou `by_category_type` | Não (aditivo, padrão preserva o comportamento) |
| `GET /transactions` | Parâmetros `order_by` e `order` | Não (aditivo, padrão preserva a ordem) |
| `GET /investments/assets` | Parâmetros `limit` (padrão 200) e `offset` | **Sim, na prática:** carteira com mais de 200 ativos passa a truncar |
| `GET /investments/assets/{id}/movements` | Idem | **Sim, na prática:** ativo com mais de 200 movimentações passa a truncar |

---

## 6. Mudanças de contrato para o front-end

Quando o dashboard for escrito, três pontos divergem do que
`05-plano-funcionalidades-dashboard-frontend.md` descreve hoje:

1. **A seção M1, item 3 está desatualizada.** Ela diz "não existe refresh token"
   e "logout é client-side; não há revogação no servidor". Os dois mudaram.
2. **O access token dura 30 minutos, não 7 dias.** Uma sessão sem renovação
   automática cai em meia hora.
3. **`by_category_type`** é campo novo em `/dashboard/summary`.

### 6.1 Como o interceptor precisa se comportar

Em `401`: tentar `POST /auth/refresh` uma vez e repetir a requisição original. Se
o refresh falhar, limpar o estado e ir para o login.

**Cuidado obrigatório — ver seção 7.2:** as chamadas de refresh precisam ser
serializadas (*single-flight*). Duas requisições paralelas que tomem 401 ao mesmo
tempo e disparem dois refreshes com o mesmo token fazem o segundo cair na
detecção de reuso e **derrubar todas as sessões do usuário**.

### 6.2 Divergência de fuso entre módulos

Comportamento pré-existente que se estende aos endpoints novos:

- **Transações e dashboard:** data sem fuso é interpretada como `America/Sao_Paulo`.
- **Investimentos:** data sem fuso é **rejeitada com 422**.

O mais seguro é o front sempre enviar ISO com offset explícito.

---

## 7. Pontos a considerar

### 7.1 A tabela `refresh_tokens` cresce sem limite

**Não há rotina de limpeza.** Cada login cria uma linha e cada rotação cria outra;
nenhuma é removida. Com access token de 30 minutos, um usuário ativo 8 horas por
dia rotaciona ~16 vezes/dia — algo como 6 mil linhas por usuário por ano, e as
revogadas e expiradas ficam todas lá.

Não é urgente na escala atual, mas é dívida certa. Opções:

- script em `backend/scripts/` no padrão do `refresh_market_quotes.py`, apagando
  `expires_at < now() - 30 dias`, chamado por cron;
- `DELETE` oportunista dentro do próprio `rotate_refresh_token`, limitado às
  linhas do usuário — mais simples, sem infraestrutura nova, mas põe custo de
  escrita no caminho quente.

Recomendo a primeira. **Não implementei porque não estava no escopo das lacunas.**

### 7.2 Rotação pode derrubar sessão legítima em condição de corrida

Consequência inerente à detecção de reuso: se o cliente disparar dois refreshes
com o mesmo token — duas abas, ou duas requisições que tomaram 401 juntas —, o
segundo é lido como vazamento e todas as sessões caem.

É o preço da opção (b), e a defesa é no cliente: *single-flight* no interceptor,
com as chamadas concorrentes aguardando a mesma promessa de refresh. Está
registrado na seção 6.1 para quando o front for escrito.

Uma alternativa que suaviza isso, se virar problema real, é uma janela de graça
de poucos segundos em que o token recém-rotacionado ainda é aceito. Ela enfraquece
a detecção — por isso não entrou agora.

### 7.3 `/auth/logout` exige access token válido

O endpoint usa `CurrentUser`, então quem está com o access token vencido **não
consegue revogar o próprio refresh token** — ele continua valendo por até 30 dias
enquanto o cliente apenas o descarta localmente.

Apresentar o refresh token já é prova de posse, então o desenho usual é: logout
de sessão única **público** (autenticado pelo próprio token apresentado, como o
`/auth/refresh`), mantendo `all_devices` atrás do `CurrentUser`.

**Recomendo essa mudança.** Não a fiz porque muda o contrato de um endpoint que
acabei de entregar e a decisão é sua.

### 7.4 Janela de 30 minutos do access token revogado

Como o JWT é stateless e não consulta a tabela de sessões, um access token já
revogado — por logout ou troca de senha — continua sendo aceito até expirar.

É a consequência aceita ao escolher 30 minutos. Fechar essa janela exigiria
consultar o banco a cada requisição autenticada, custo que não se justifica aqui.
Foi por isso que o access token encurtou de 7 dias para 30 minutos.

### 7.5 Sem rate limit em `/auth/login` e `/auth/refresh`

Pré-existente no login, e agora vale também para o refresh. Adivinhar um refresh
token por força bruta é inviável (256 bits de entropia), mas o login segue
exposto a tentativa em massa. Fora do escopo destas lacunas; vale registrar junto
do C2, que também precisa de rate limit.

### 7.6 Exportação e carteira carregam tudo em memória

`GET /investments/export` monta a carteira inteira e, no XLSX, todas as
movimentações do usuário. `_portfolio` já fazia uma consulta de movimentações
**por ativo** (N+1 pré-existente) e agora é chamado também pela exportação.

Aceitável para carteiras pessoais; não é o desenho certo para milhares de
movimentações. O join em `_movements_with_ticker` já evita o N+1 na parte nova.

### 7.7 O teto de 1000 pontos no timeseries é arbitrário

`MAX_POINTS = 1000` protege o payload: `granularity=day` num intervalo de dez
anos geraria ~3650 pontos, que nenhum gráfico desenha. Acima disso a API devolve
422 pedindo intervalo menor ou granularidade maior. Se o front tiver uma tela que
legitimamente precise de mais, o número precisa ser revisto junto.

### 7.8 Comportamento de SQL segue sem cobertura automatizada

A suíte não abre conexão — por desenho, documentado no `conftest`. Tudo que é
`date_trunc`, `DISTINCT`, ordenação e `rowcount` depende de validação manual
(seção 8.1) ou da suíte de integração (seção 9).

---

## 8. Cobertura de teste

`backend/tests/test_lacunas_dashboard.py` — 19 testes, no padrão da casa: função
pura, contrato de schema e registro de rota. Suíte completa: **87 passando**.

Cobre:

- calendário da série temporal — semana ISO começando na segunda (para bater com
  o `date_trunc('week')` do Postgres), virada de ano, preenchimento de buracos,
  teto de pontos;
- opacidade do refresh token e o fato de só o hash ser persistido;
- a máquina de estados da rotação, incluindo a detecção de reuso **e os casos em
  que ela não deve disparar** (token vencido ou desconhecido);
- a fusão do PATCH de movimentação, incluindo virar o tipo para `dividend` sem
  informar valor;
- neutralização de fórmulas e distinção entre nulo e zero na exportação;
- paridade entre a lista branca de ordenação e o `Literal` da query.

Dois testes existentes em `test_issue_hardening.py` foram ajustados: eles
monkeypatchavam `auth._token_for`, que virou `auth._start_session`. As asserções
de comportamento seguem idênticas.

### 8.1 Validação manual necessária

- [ ] `date_trunc` com `AT TIME ZONE`: lançar algo às 22h de 31/01 e conferir que cai em janeiro, não em fevereiro
- [ ] `GET /transactions/categories` ignorando nulos e ordenando por frequência
- [ ] `order_by=amount` com valores repetidos, paginando: nenhuma linha repetida ou pulada entre páginas
- [ ] `GET /transactions/imports` — confirmar no log de SQL que `content` não aparece no SELECT
- [ ] `PATCH` de movimentação que deixaria a custódia negativa devolve 422 **e não altera a linha**
- [ ] Rotação real: usar o mesmo refresh token duas vezes derruba todas as sessões
- [ ] Unicidade de `token_hash` e `rowcount` real da revogação em massa
- [ ] Troca de senha derruba as outras sessões e mantém quem trocou
- [ ] `DELETE /telegram/link` e, em seguida, mandar mensagem pelo bot: precisa pedir vínculo de novo
- [ ] Exportação XLSX abrindo no Excel com as duas abas

---

## 9. Suíte de integração — desenho para decisão futura

Adiada por decisão, mas o desenho é este:

- **Banco:** `testcontainers[postgresql]` ou um serviço Postgres no CI. Exige
  Docker na máquina e no CI — foi o custo que motivou o adiamento.
- **Fixture:** container por sessão de teste, `alembic upgrade head` uma vez, e
  cada teste dentro de uma transação com rollback ao final. Sem `create_all`:
  rodar as migrations de verdade também testa as migrations.
- **Isolamento:** o guard do `conftest` continua valendo; a URL do container
  substituiria a da porta 1 apenas dentro dessa suíte, marcada com
  `@pytest.mark.integration` e desligada por padrão.
- **Alvo:** exatamente os itens de 8.1 — comportamento de SQL, não regra de
  negócio, que já está coberta por função pura.

---

## 10. C2 — reset de senha por e-mail (fora do escopo)

Continua sendo a única lacuna aberta. Não há provedor, dependência, template nem
variável de e-mail no projeto.

`POST /auth/change-password` cobre quem lembra a senha atual. **Fica descoberto o
caso de senha esquecida:** hoje esse usuário não tem como recuperar a conta pela
interface.

Quando houver decisão de provedor, o que falta é: chave em `Settings` (e no
`AMBIENTE_DE_TESTE` do `conftest`, senão a suíte inteira falha), tabela de token
de uso único com expiração, template, e rate limit — sem ele o endpoint vira
vetor de spam e de enumeração de contas.

---

## 11. Inventário de arquivos

### Novos

| Arquivo | Papel |
| --- | --- |
| `app/models/refresh_token.py` | Tabela de sessões |
| `app/services/sessions.py` | Emissão, rotação, revogação e detecção de reuso |
| `app/services/timeseries.py` | Aritmética de calendário da série temporal (pura) |
| `alembic/versions/a91d3e5c7f60_...py` | `refresh_tokens` + `telegram_tokens.unlinked_at` |
| `tests/test_lacunas_dashboard.py` | 19 testes |
| `resume/07-lacunas-backend-implementadas.md` | Este documento |

### Alterados

| Arquivo | Mudança |
| --- | --- |
| `app/core/config.py` | `ACCESS_TOKEN_EXPIRE_MINUTES` 10080 → 30; `REFRESH_TOKEN_EXPIRE_MINUTES` novo |
| `app/core/security.py` | `generate_refresh_token`, `hash_refresh_token` |
| `app/api/v1/auth.py` | `/refresh`, `/logout`, `/change-password`, `PATCH /me`; `_token_for` → `_start_session` |
| `app/api/v1/dashboard.py` | `/timeseries`; `type` no `/summary` |
| `app/api/v1/transactions.py` | `/categories`, `/imports`, `order_by` |
| `app/api/v1/investments.py` | `/snapshots`, `/export`, `PATCH /movements/{id}`, paginação; helpers `_movement_values` e `_asset_movements` extraídos |
| `app/api/v1/telegram.py` | `DELETE /link` |
| `app/models/telegram_token.py` | Coluna `unlinked_at` |
| `app/models/__init__.py` | Registra `RefreshToken` |
| `app/schemas/auth.py` | `RefreshRequest`, `LogoutRequest`, `ProfileUpdate`, `ChangePasswordRequest`; `TokenResponse` ganhou o par |
| `app/schemas/transaction.py` | `CategoryOption`, `TimeseriesPoint`, `TimeseriesResponse`, `by_category_type` |
| `app/schemas/investment.py` | `MovementUpdate`, `SnapshotResponse` |
| `app/schemas/import_job.py` | `ImportJobListResponse` |
| `app/schemas/telegram.py` | `TelegramUnlinkResponse` |
| `app/services/spreadsheets.py` | Exportação de posições e movimentações (CSV e XLSX) |
| `tests/conftest.py` | `AMBIENTE_DE_TESTE` com os dois campos novos de `Settings` |
| `tests/test_issue_hardening.py` | Ajuste do monkeypatch renomeado |
| `.env.example` | Novas variáveis, com o porquê |
| `resume/06-...md` | Pendências marcadas como resolvidas |
