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
| Migrations | 2 (`a91d3e5c7f60`, `b8f2c1d90a44`) |
| Arquivos novos | 8 de código + 1 de teste |
| Arquivos alterados | 23 |
| Testes | 99 passando (68 antes + 19 das lacunas + 12 da revisão de 14/08) |

**O que ainda depende de você:** agendar o cron da limpeza (seção 7.1) e decidir
`TRUST_PROXY_HEADERS` conforme o deploy (seção 7.5.1).

### 1.1 Revisão de 14/08/2026

Cinco pontos resolvidos depois da entrega original — três de revisão de código e
dois que estavam registrados aqui como pendentes:

| Ponto | Onde | Resolução |
| --- | --- | --- |
| Rotação sem lock permitia dois tokens vivos e furava a detecção de reuso | `app/services/sessions.py` | `SELECT … FOR UPDATE` na leitura — seção 7.2 |
| Logout inalcançável com access token vencido | `app/api/v1/auth.py`, `app/api/dependencies.py` | Logout de sessão única virou público — seção 7.3 |
| `05` e `07` descreviam contratos divergentes | `resume/05-…md`, seção 6 daqui | Documentos conciliados; `07` é a fonte canônica |
| Tabelas de acesso cresciam sem limite | `scripts/purge_access_lifecycle.py` | Limpeza agendada, em lotes — seção 7.1 |
| `/auth/login` sem defesa contra força bruta | `app/services/login_throttle.py`, migration `b8f2c1d90a44` | Bloqueio progressivo 10 min → 3 h → 24 h — seção 7.5 |

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
# Decisão de deploy — ver seção 7.5.1 antes de mudar para true.
TRUST_PROXY_HEADERS=false
```

O `.env.example` já foi atualizado.

### 3.2 Rodar as migrations

```bash
cd backend && alembic upgrade head
```

> Na prática o `lifespan` do `app/main.py` roda `upgrade head` na subida do
> servidor, então o deploy aplica as duas sozinho.

Revisão `a91d3e5c7f60` (sobre `3c7f1a9b2d84`):

- cria `refresh_tokens` com RLS `ENABLE`/`FORCE` — o padrão do projeto para toda
  tabela com dado de usuário, estabelecido em `b75641c60d56`;
- adiciona `telegram_tokens.unlinked_at`.

Revisão `b8f2c1d90a44` (sobre `a91d3e5c7f60`):

- cria `login_attempts`, também com RLS `ENABLE`/`FORCE`. Ela não tem `user_id`,
  mas quem lê essa tabela sabe quais contas estão sob ataque e quais estão
  bloqueadas — motivo de sobra para o mesmo padrão.

O DDL das duas foi conferido offline com
`alembic upgrade <revisão anterior>:head --sql`. **Não foi executado contra o
Supabase.**

O `downgrade` de `a91d3e5c7f60` derruba a tabela `refresh_tokens` inteira — ou
seja, desfazer a migration desloga todo mundo. É o comportamento correto, mas não
é reversível sem custo. O de `b8f2c1d90a44` só perde contadores de bloqueio:
desfazê-la libera quem estava bloqueado, e nada além disso.


### 3.3 Consequência para as sessões existentes

Não há refresh token para quem já está logado. Os JWTs de 7 dias emitidos antes
do deploy continuam válidos até expirarem, mas **não renovam** — na primeira
falha o usuário vai para o login. É um logout diferido de toda a base; como o
front-end ainda não existe, o impacto real hoje é nulo.

### 3.4 Agendar a limpeza

```bash
0 4 * * * cd /app/backend && python scripts/purge_access_lifecycle.py
```

Sem isso, `refresh_tokens` e `login_attempts` crescem para sempre (seção 7.1).
Nada quebra por adiar; a conta chega depois.

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
"revogado no logout". A linha é lida com `FOR UPDATE`: sem o lock, duas chamadas
concorrentes com o mesmo token rotacionariam as duas (seção 7.2).

**Detecção de reuso:** reapresentar um token já rotacionado significa que duas
partes têm o mesmo segredo — o dono legítimo e quem copiou. Como não há como
saber qual está chamando, a resposta é derrubar **todas** as sessões do usuário.
Token apenas vencido ou desconhecido é rotina e não dispara isso.

`register` e `login` passam a devolver `refresh_token` e `refresh_expires_at`.

O `user_agent` é capturado por header opcional — um cliente sem User-Agent
(script, curl) continua conseguindo logar.

**Bloqueio progressivo do login** (`app/services/login_throttle.py`, tabela
`login_attempts`): 5 falhas bloqueiam por 10 min, mais 5 por 3 h, mais 5 por 24 h,
com teto em 24 h. Conta em dois escopos — e-mail e IP —, guarda só o SHA-256 de
cada escopo e devolve 429 com `Retry-After` antes de tocar no bcrypt. O detalhe
das decisões está na seção 7.5.

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
| POST | `/auth/logout` | **Parcial** | `{refresh_token}` encerra a sessão apresentada e **não exige access token** — a posse do token é a prova. `{all_devices: true}` exige access token válido (401 sem ele) |
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
| `POST /auth/login` | Idem, mais **429 com `Retry-After`** após 5 falhas (seção 7.5) | Não no corpo; o cliente precisa **tratar 429** |
| `GET /dashboard/summary` | Parâmetro `type` (padrão `expense`); resposta ganhou `by_category_type` | Não (aditivo, padrão preserva o comportamento) |
| `GET /transactions` | Parâmetros `order_by` e `order` | Não (aditivo, padrão preserva a ordem) |
| `GET /investments/assets` | Parâmetros `limit` (padrão 200) e `offset` | **Sim, na prática:** carteira com mais de 200 ativos passa a truncar |
| `GET /investments/assets/{id}/movements` | Idem | **Sim, na prática:** ativo com mais de 200 movimentações passa a truncar |

---

## 6. Mudanças de contrato para o front-end

`05-plano-funcionalidades-dashboard-frontend.md` foi **atualizado em 14/08/2026**
para refletir tudo o que está abaixo — os dois documentos descrevem o mesmo
contrato. Este aqui continua sendo a fonte canônica: se divergirem, o `05` é que
está errado.

A lista completa do que mudou em relação ao levantamento de 11/08:

**Sessão e autenticação**

1. **Existe refresh token.** `register`, `login`, `refresh` e `change-password`
   devolvem `refresh_token` e `refresh_expires_at` junto do access token.
2. **O access token dura 30 minutos, não 7 dias.** Uma sessão sem renovação
   automática cai em meia hora — o interceptor deixou de ser opcional.
3. **O refresh token é rotacionado:** cada `POST /auth/refresh` devolve valor novo
   e invalida o apresentado. Guardar sempre o último recebido.
4. **`POST /auth/refresh` é rota pública** — não mandar `Authorization` nela.
5. **Logout existe e revoga no servidor.** Descartar o token só no cliente deixa
   a sessão viva por até 30 dias. Sessão única (`{refresh_token}`) é **pública**;
   `{all_devices: true}` exige access token válido e devolve 401 sem ele.
6. **`POST /auth/change-password`** devolve um par de tokens novo, que precisa
   substituir o guardado — com `revoke_other_sessions` (padrão `true`), o par
   antigo do próprio chamador também cai.
7. **`PATCH /auth/me`** edita apenas `full_name`; nome em branco vira `null`.

**Dados**

8. **`by_category_type`** é campo novo em `/dashboard/summary`, e o parâmetro
   `type` (padrão `expense`) escolhe o que `by_category` agrega.
9. **`GET /dashboard/timeseries`** existe, preenche períodos vazios com zero e
   devolve 422 acima de 1000 pontos.
10. **`GET /transactions/categories`** passa a ser a fonte do filtro de categoria.
11. **`GET /transactions/imports`** dispensa guardar o `job_id` no `localStorage`.
    Envelope `{items, total, limit, offset}`, ao contrário da lista pura de
    `/transactions`.
12. **`order_by`/`order` em `/transactions`**: ordenar passou a ser consulta nova
    no servidor, não reordenação da página carregada.
13. **`PATCH /investments/movements/{id}`** existe — o fluxo "excluir e recriar"
    deixou de ser necessário.
14. **`GET /investments/snapshots`** e **`GET /investments/export`** existem.
15. **`DELETE /telegram/link`** existe.

16. **`POST /auth/login` pode devolver 429** com `Retry-After` em segundos, depois
    de 5 falhas. A tela de login precisa desse caso: mensagem própria (não é
    "senha inválida") e, de preferência, contagem regressiva a partir do
    cabeçalho. Ver seção 7.5.

**Quebras silenciosas — atenção**

17. **`limit` padrão 200** em `/investments/assets` e
    `/investments/assets/{id}/movements`. Carteira maior que isso **trunca sem
    aviso** se o cliente não paginar.
18. **Detecção de reuso derruba todas as sessões** quando dois refreshes correm
    com o mesmo token. Ver 6.1.

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

### 7.1 Crescimento sem limite das tabelas de acesso — **resolvido**

`refresh_tokens` ganha uma linha por login **e outra por rotação**: um usuário
ativo 8 horas por dia rotaciona ~16 vezes/dia, algo como 6 mil linhas por usuário
por ano, e nenhuma saía. `login_attempts` (seção 7.5) tem o mesmo problema.

Implementada a primeira opção — **script agendado**, não `DELETE` oportunista na
rotação. O motivo é o caminho quente: apagar durante a rotação põe escrita e um
lock a mais na chamada que todo cliente faz a cada 30 minutos, para resolver um
problema que não tem pressa. O trabalho agendado limpa fora do pico, em lotes, e
pode ser interrompido sem deixar nada pela metade.

`backend/scripts/purge_access_lifecycle.py`, no padrão do
`refresh_market_quotes.py`:

```bash
python scripts/purge_access_lifecycle.py            # apaga
python scripts/purge_access_lifecycle.py --dry-run  # só conta

# cron, todo dia às 4h:
0 4 * * * cd /app/backend && python scripts/purge_access_lifecycle.py
```

Decisões dentro dele:

- **Carência de 30 dias após o vencimento** (`--days`). A linha vencida já não
  autentica nada, mas guardá-la um tempo preserva a cadeia de rotação — inclusive
  a evidência de reuso, que é o sinal de token vazado.
- **Lotes de 5 000** com commit por lote (`--batch`): um `DELETE` único de
  centenas de milhares de linhas segura a tabela por minutos e estoura o WAL de
  uma vez.
- **Nunca apaga bloqueio em vigor** de `login_attempts` — apagar seria liberar.
  O corte é o mesmo `LEVEL_DECAY` do serviço: passado esse tempo sem falha nova, a
  linha não bloqueia nem conta mais nada.
- A ordem de exclusão não fere o `replaced_by_id`: o sucessor sempre expira depois
  do antecessor, então o `ON DELETE SET NULL` nunca é acionado sobre uma cadeia
  ainda viva.

**Ainda é preciso agendar de fato** — o script existe, o cron é seu.

### 7.2 Rotação pode derrubar sessão legítima em condição de corrida

Consequência inerente à detecção de reuso: se o cliente disparar dois refreshes
com o mesmo token — duas abas, ou duas requisições que tomaram 401 juntas —, o
segundo é lido como vazamento e todas as sessões caem.

É o preço da opção (b), e a defesa é no cliente: *single-flight* no interceptor,
com as chamadas concorrentes aguardando a mesma promessa de refresh. Está
registrado na seção 6.1 e agora também nos critérios de aceite do `05`.

Uma alternativa que suaviza isso, se virar problema real, é uma janela de graça
de poucos segundos em que o token recém-rotacionado ainda é aceito. Ela enfraquece
a detecção — **decidido não adotar**: a corrida legítima custa um login novo, e a
janela de graça custa aceitar um token sabidamente vazado.

**Correção aplicada (14/08/2026): a leitura da rotação agora é `SELECT … FOR
UPDATE`.** Sem o lock o problema era pior que "derrubar sessão legítima" — era o
oposto. Duas requisições concorrentes com o mesmo token liam as duas
`revoked_at is None`, as duas passavam, as duas criavam sessão nova e a segunda
sobrescrevia `revoked_at`/`replaced_by_id` da primeira: **dois refresh tokens
vivos para uma rotação só, e o alarme de reuso nunca disparando naquele par** —
exatamente o cenário que um atacante de posse de um token copiado quer produzir.
Com o lock, a segunda chamada espera a primeira comitar e enxerga a linha
revogada, que é o caminho da detecção. O mesmo lock foi aplicado à revogação por
token no logout, que também lê e escreve a mesma linha.

### 7.3 `/auth/logout` com access token vencido — **resolvido**

Era o caso de quem volta ao app depois de 30 minutos: o endpoint exigia
`CurrentUser`, então o usuário **não conseguia revogar o próprio refresh token**,
que seguia valendo por até 30 dias enquanto o cliente só o descartava localmente.

Implementado o desenho recomendado: logout de sessão única **público**,
autenticado pela posse do refresh token apresentado — o mesmo raciocínio de
`/auth/refresh` —, com `all_devices` continuando atrás do access token válido,
porque derrubar tudo é ação sobre a conta, não sobre o token apresentado.

Como o cliente com token vencido **continua mandando o header antigo**, uma
credencial vencida não pode virar 401 na rota: a dependência `get_optional_user`
devolve `None` nesse caso, e `get_current_user` passou a ser uma casca em cima
dela que só transforma `None` em 401. Sem isso a correção não teria efeito
nenhum — o 401 viria do header, não do corpo.

Quando autenticado, a revogação segue restrita às sessões de quem chama;
anônimo, quem autoriza é o token apresentado.

### 7.4 Janela de 30 minutos do access token revogado

Como o JWT é stateless e não consulta a tabela de sessões, um access token já
revogado — por logout ou troca de senha — continua sendo aceito até expirar.

É a consequência aceita ao escolher 30 minutos. Fechar essa janela exigiria
consultar o banco a cada requisição autenticada, custo que não se justifica aqui.
Foi por isso que o access token encurtou de 7 dias para 30 minutos.

### 7.5 Rate limit contra força bruta no login — **implementado**

A senha é o único segredo de baixa entropia do sistema. Um refresh token tem 256
bits e não se adivinha; "senha123" se adivinha em milhares de tentativas, e
`/auth/login` aceitava milhares por minuto.

**Bloqueio progressivo**, em `app/services/login_throttle.py`:

| Bloqueio | Depois de | Dura |
| --- | --- | --- |
| 1º | 5 falhas | 10 minutos |
| 2º | mais 5 falhas | 3 horas |
| 3º | mais 5 falhas | 24 horas |
| 4º em diante | mais 5 falhas | 24 horas (teto) |

Bloqueado, o endpoint devolve **429** com `Retry-After` em segundos e **não faz o
trabalho**: nem consulta o usuário, nem roda o bcrypt. É metade do ponto de ter
rate limit — a outra metade é a espera.

**Dois escopos, e o motivo de cada um.** Bloquear só por e-mail deixa passar quem
varre muitas contas com a mesma senha (*credential stuffing*); bloquear só por IP
não segura um ataque distribuído contra uma conta. Então cada tentativa conta nos
dois. O escopo de IP tolera **4× mais** falhas, porque um IP pode ser um
escritório inteiro saindo por NAT.

**Não existe bloqueio permanente de IP.** Foi uma decisão, não um esquecimento:
com NAT e CGNAT, banir um IP pune vizinhos que não fizeram nada — e um atacante
pode provocar o banimento de propósito para tirar terceiros do ar. O teto de 24 h
repetidas já torna a força bruta inviável sem criar essa arma.

**Esquecimento com dois tempos.** Sem falha nova por 1 hora, a contagem parcial
zera — quem errou a senha três vezes ontem não começa hoje a um passo do bloqueio.
Mas o **degrau já conquistado só cai depois de 7 dias** de silêncio. Os dois
tempos precisam ser diferentes: se o degrau caísse junto com a contagem, bastaria
esperar a janela para tentar de novo em blocos de 4, para sempre. E os 7 dias
precisam ser **maiores que o maior bloqueio** — na primeira versão eram 24 horas,
iguais ao bloqueio mais longo, e a escada zerava no instante exato em que a
punição terminava: cumprir as 24 h devolvia degraus de 10 minutos e o teto nunca
valia. Está fixado por teste.

**A tabela não guarda e-mail nem IP**, só o SHA-256 de `tipo:valor`. Ela é um
contador defensivo, não trilha de auditoria: com o hash responde "este escopo está
bloqueado?" sem que um dump vire lista de contas cadastradas — que é justamente o
que a mensagem genérica de login evita revelar.

**Login certo zera o escopo do e-mail, não o do IP.** Quem tem conta própria
poderia usá-la para limpar o contador entre rajadas contra as contas dos outros;
o escopo de IP sai sozinho pela janela de 1 hora.

#### 7.5.1 ⚠️ `TRUST_PROXY_HEADERS` precisa de decisão no deploy

Variável nova, padrão `false`. Ela decide de onde vem o IP, e erra feio nos dois
sentidos:

- **Ligada sem proxy na frente:** qualquer cliente forja `X-Forwarded-For`, ganha
  um IP novo a cada tentativa e o escopo de IP deixa de existir — pior, dá para
  forjar o IP de outra pessoa e bloqueá-la de propósito.
- **Desligada atrás de proxy:** todas as requisições chegam com o IP do load
  balancer, viram um escopo só, e **um atacante bloquearia a base inteira**.

Deixe `false` com Uvicorn recebendo a conexão direto; ligue quando houver proxy
confiável. O escopo por e-mail funciona igual nos dois casos — é o que garante que
uma configuração errada não deixe o login sem defesa nenhuma.

#### 7.5.2 O que continua sem rate limit

`/auth/refresh` (adivinhar 256 bits é inviável), `/auth/register` e
`/auth/change-password` — este último já exige access token válido. O C2, quando
existir, precisa do seu próprio: sem ele o reset por e-mail vira vetor de spam e
de enumeração de contas.

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

`backend/tests/test_lacunas_dashboard.py` — 31 testes, no padrão da casa: função
pura, contrato de schema e registro de rota. Suíte completa: **99 passando**.

Cobre:

- calendário da série temporal — semana ISO começando na segunda (para bater com
  o `date_trunc('week')` do Postgres), virada de ano, preenchimento de buracos,
  teto de pontos;
- opacidade do refresh token e o fato de só o hash ser persistido;
- a máquina de estados da rotação, incluindo a detecção de reuso **e os casos em
  que ela não deve disparar** (token vencido ou desconhecido);
- o `FOR UPDATE` na rotação e na revogação por token — o teste inspeciona a
  cláusula do statement, no mesmo padrão do lock de ativo em
  `test_issue_hardening.py`;
- o logout: sessão única sem usuário identificado revoga; `all_devices` sem
  access token válido dá 401; credencial vencida vira usuário anônimo em
  `get_optional_user` em vez de 401, e continua sendo 401 em `get_current_user`;
- a escada do bloqueio de login — os três degraus e o teto, o esquecimento em dois
  tempos, a tolerância maior do escopo de IP, o fato de o hash não conter o e-mail,
  e o 429 sem consultar usuário nem rodar bcrypt. Inclui a **invariante que
  quebrou na primeira versão**: `LEVEL_DECAY` maior que o maior bloqueio;
- a fusão do PATCH de movimentação, incluindo virar o tipo para `dividend` sem
  informar valor;
- neutralização de fórmulas e distinção entre nulo e zero na exportação;
- paridade entre a lista branca de ordenação e o `Literal` da query.

Três testes existentes em `test_issue_hardening.py` foram ajustados: dois
monkeypatchavam `auth._token_for`, que virou `auth._start_session`, e o do bcrypt
dummy precisou de uma sessão falsa que aceite escrita, porque o login falho agora
registra a tentativa. As asserções de comportamento seguem idênticas.

### 8.1 Validação manual necessária

- [ ] `date_trunc` com `AT TIME ZONE`: lançar algo às 22h de 31/01 e conferir que cai em janeiro, não em fevereiro
- [ ] `GET /transactions/categories` ignorando nulos e ordenando por frequência
- [ ] `order_by=amount` com valores repetidos, paginando: nenhuma linha repetida ou pulada entre páginas
- [ ] `GET /transactions/imports` — confirmar no log de SQL que `content` não aparece no SELECT
- [ ] `PATCH` de movimentação que deixaria a custódia negativa devolve 422 **e não altera a linha**
- [ ] Rotação real: usar o mesmo refresh token duas vezes derruba todas as sessões
- [ ] **Rotação concorrente:** disparar dois `POST /auth/refresh` simultâneos com o mesmo token — um devolve par novo, o outro cai na detecção de reuso; nunca os dois com sucesso (é o que o `FOR UPDATE` garante e a suíte não alcança)
- [ ] **Logout sem access token:** esperar o access token vencer (ou mandar um lixo no `Authorization`) e chamar `/auth/logout` com `{refresh_token}` — deve encerrar a sessão; em seguida `/auth/refresh` com o mesmo token tem de falhar
- [ ] **Logout `all_devices` sem access token válido:** precisa dar 401
- [ ] **Bloqueio do login:** errar a senha 5 vezes → 429 com `Retry-After` ~600; acertar a senha antes da 5ª e conferir que o contador zerou
- [ ] **Bloqueio não vaza existência de conta:** 5 falhas num e-mail que não existe também devolvem 429 (mesma resposta de um e-mail real)
- [ ] **Escopo de IP:** falhar em contas diferentes do mesmo IP acumula no escopo de IP; conferir que precisa de 20 falhas, não 5
- [ ] **`TRUST_PROXY_HEADERS`:** com a variável em `false`, mandar `X-Forwarded-For` forjado **não** deve trocar o escopo de IP
- [ ] **Limpeza:** rodar `purge_access_lifecycle.py --dry-run` e conferir a contagem; depois rodar de verdade e confirmar que nenhum bloqueio em vigor sumiu
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

O rate limit já não precisa nascer do zero: `app/services/login_throttle.py` é
genérico por escopo (`scope_kind`), então basta um escopo novo — algo como
`reset:<e-mail>` — reusando a mesma escada e a mesma tabela.

---

## 11. Inventário de arquivos

### Novos

| Arquivo | Papel |
| --- | --- |
| `app/models/refresh_token.py` | Tabela de sessões |
| `app/models/login_attempt.py` | Contadores do bloqueio progressivo, por escopo |
| `app/services/sessions.py` | Emissão, rotação, revogação e detecção de reuso |
| `app/services/login_throttle.py` | Escada de bloqueio do login (núcleo puro + persistência) |
| `app/services/timeseries.py` | Aritmética de calendário da série temporal (pura) |
| `alembic/versions/a91d3e5c7f60_...py` | `refresh_tokens` + `telegram_tokens.unlinked_at` |
| `alembic/versions/b8f2c1d90a44_...py` | `login_attempts` |
| `scripts/purge_access_lifecycle.py` | Limpeza agendada das duas tabelas de acesso |
| `tests/test_lacunas_dashboard.py` | 31 testes |
| `resume/07-lacunas-backend-implementadas.md` | Este documento |

### Alterados

| Arquivo | Mudança |
| --- | --- |
| `app/core/config.py` | `ACCESS_TOKEN_EXPIRE_MINUTES` 10080 → 30; `REFRESH_TOKEN_EXPIRE_MINUTES` e `TRUST_PROXY_HEADERS` novos |
| `app/core/security.py` | `generate_refresh_token`, `hash_refresh_token` |
| `app/api/dependencies.py` | `get_optional_user` e `get_client_ip`; `get_current_user` virou casca sobre a primeira |
| `app/api/v1/auth.py` | `/refresh`, `/logout` (sessão única pública), `/change-password`, `PATCH /me`; bloqueio progressivo no `/login`; `_token_for` → `_start_session` |
| `app/api/v1/dashboard.py` | `/timeseries`; `type` no `/summary` |
| `app/api/v1/transactions.py` | `/categories`, `/imports`, `order_by` |
| `app/api/v1/investments.py` | `/snapshots`, `/export`, `PATCH /movements/{id}`, paginação; helpers `_movement_values` e `_asset_movements` extraídos |
| `app/api/v1/telegram.py` | `DELETE /link` |
| `app/models/telegram_token.py` | Coluna `unlinked_at` |
| `app/models/__init__.py` | Registra `RefreshToken` e `LoginAttempt` |
| `app/schemas/auth.py` | `RefreshRequest`, `LogoutRequest`, `ProfileUpdate`, `ChangePasswordRequest`; `TokenResponse` ganhou o par |
| `app/schemas/transaction.py` | `CategoryOption`, `TimeseriesPoint`, `TimeseriesResponse`, `by_category_type` |
| `app/schemas/investment.py` | `MovementUpdate`, `SnapshotResponse` |
| `app/schemas/import_job.py` | `ImportJobListResponse` |
| `app/schemas/telegram.py` | `TelegramUnlinkResponse` |
| `app/services/spreadsheets.py` | Exportação de posições e movimentações (CSV e XLSX) |
| `tests/conftest.py` | `AMBIENTE_DE_TESTE` com os três campos novos de `Settings` |
| `tests/test_issue_hardening.py` | Monkeypatch renomeado; sessão falsa do login aceita escrita |
| `tests/test_lacunas_dashboard.py` | 12 testes da revisão de 14/08 (lock, logout e bloqueio de login) |
| `.env.example` | Novas variáveis, com o porquê |
| `resume/05-...md` | Contrato conciliado com este documento (14/08) |
| `resume/06-...md` | Pendências marcadas como resolvidas |
