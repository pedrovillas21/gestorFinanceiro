# Plano de funcionalidades do dashboard front-end

Data do levantamento: 11/08/2026
Última atualização: 17/08/2026 — auditoria das 33 rotas do back-end contra este
plano: 12 divergências de contrato corrigidas aqui e `GET /auth/sessions`
implementado no back-end.
Base: código do back-end em `backend/app` (rotas `/api/v1`), conforme estado atual do branch `modelagemFrontEnd`.

Este documento define **o que o dashboard precisa ter** para consumir tudo o que o back-end já entrega hoje. Ele complementa `04-funcionalidades-backend-telegram-dashboard.md`, que descreve o back-end; aqui a ótica é a da interface.

> **Contrato válido:** este documento é a visão da interface sobre o mesmo
> contrato descrito em `07-lacunas-backend-implementadas.md` — que é a fonte
> canônica de autenticação, endpoints e mudanças de contrato. Os dois foram
> conciliados em 14/08/2026; quando divergirem, o `07` vence e este aqui precisa
> ser corrigido junto.

---

## 1. Ponto de partida

O front-end (`frontend/`) é um projeto Next.js recém-criado: `app/page.tsx` ainda é a página padrão do template. Não existe nenhuma tela, cliente HTTP ou fluxo de autenticação implementado.

Dependências já instaladas e que este plano assume:

| Pacote | Uso previsto |
| --- | --- |
| `next` 16.3 + `react` 19.2 | App Router, Server/Client Components |
| `tailwindcss` 4 | Estilo |
| `axios` | Cliente HTTP com interceptor de token |
| `@tanstack/react-table` | Tabelas de transações, ativos e movimentações |
| `recharts` | Gráficos de categoria, evolução e juros compostos |
| `lucide-react` | Ícones |
| `@supabase/supabase-js` | **Não deve ser usado.** O back-end aplica RLS `ENABLE`/`FORCE` com negação por padrão no PostgREST; todo acesso a dados passa pela API FastAPI. Recomenda-se remover a dependência para não induzir acesso direto ao banco. |

> Atenção de implementação: o `frontend/AGENTS.md` alerta que esta versão do Next tem quebras em relação a versões anteriores. Consultar `node_modules/next/dist/docs/` antes de escrever código de rotas, cache e data fetching.

Configuração de ambiente: `WEB_APP_URL` e `CORS_ORIGINS` do back-end apontam para `http://localhost:3000`. O front precisa de `NEXT_PUBLIC_API_URL` apontando para a base da API (`http://localhost:8000`), consumindo sempre o prefixo `/api/v1`.

> **Exceção ao prefixo:** `GET /health` está montado na raiz da aplicação
> (`app/main.py`), fora de `/api/v1`. É a única rota nessa condição. O cliente
> HTTP com `baseURL` terminando em `/api/v1` não a alcança — o indicador de
> disponibilidade precisa montar a URL a partir da base sem o prefixo.

---

## 2. Mapa: endpoint do back-end → tela do dashboard

| Endpoint | Método | Tela / componente proposto |
| --- | --- | --- |
| `/auth/register` | POST | Cadastro |
| `/auth/login` | POST | Login |
| `/auth/refresh` | POST | Interceptor HTTP (renovação de sessão) — sem tela |
| `/auth/logout` | POST | Menu do usuário → Sair; Configurações → Encerrar todas as sessões |
| `/auth/sessions` | GET | Configurações → Dispositivos conectados |
| `/auth/me` | GET | Guard de sessão + menu do usuário |
| `/auth/me` | PATCH | Configurações → Conta (editar nome) |
| `/auth/me` | DELETE | Configurações → Excluir conta |
| `/auth/change-password` | POST | Configurações → Alterar senha |
| `/dashboard/summary` | GET | Visão geral (KPIs + gráfico por categoria) |
| `/dashboard/timeseries` | GET | Visão geral → gráfico de evolução |
| `/transactions` | GET | Transações → tabela com filtros, ordenação e paginação |
| `/transactions` | POST | Modal "Novo lançamento" |
| `/transactions/{id}` | GET/PATCH/DELETE | Painel de detalhe / edição inline / confirmação de exclusão |
| `/transactions/categories` | GET | Opções do filtro de categoria |
| `/transactions/import` | POST | Transações → Importar planilha |
| `/transactions/imports` | GET | Transações → Histórico de importações |
| `/transactions/imports/{job_id}` | GET | Cartão de progresso da importação (polling) |
| `/transactions/export` | GET | Botão "Exportar" (CSV/XLSX) |
| `/investments/assets` | GET/POST | Investimentos → Ativos |
| `/investments/assets/{id}` | PATCH/DELETE | Edição e exclusão de ativo |
| `/investments/assets/{id}/movements` | GET/POST | Detalhe do ativo → extrato de movimentações |
| `/investments/movements/{id}` | PATCH/DELETE | Edição e exclusão de movimentação |
| `/investments/portfolio` | GET | Investimentos → Carteira consolidada |
| `/investments/snapshots` | GET | Investimentos → curva de evolução do patrimônio |
| `/investments/export` | GET | Investimentos → Exportar carteira (CSV/XLSX) |
| `/investments/quotes/refresh` | POST | Botão "Atualizar cotações" |
| `/calculators/compound-interest` | POST | Ferramentas → Simulador de juros compostos |
| `/telegram/privacy-policy` e `/{version}` | GET | Modal de consentimento (leitura obrigatória) |
| `/telegram/link` | POST/GET | Configurações → Conectar Telegram |
| `/telegram/link` | DELETE | Configurações → Desconectar Telegram |
| `/health` | GET | Indicador opcional de disponibilidade da API — **fora do prefixo `/api/v1`** |

Endpoints sem tela: `/telegram/webhook` (uso exclusivo do Telegram).

A auditoria de 17/08/2026 conferiu o mapa nos dois sentidos, contra o
`openapi()` da aplicação: nenhum endpoint ficou sem tela prevista e nenhuma tela
aponta para rota inexistente.

---

## 3. Arquitetura de rotas proposta (App Router)

```
app/
  (public)/
    login/page.tsx
    cadastro/page.tsx
  (dashboard)/
    layout.tsx                  # shell: sidebar, topbar, guard de sessão
    page.tsx                    # visão geral
    transacoes/page.tsx
    transacoes/importar/page.tsx
    investimentos/page.tsx      # carteira consolidada
    investimentos/ativos/page.tsx
    investimentos/ativos/[id]/page.tsx
    ferramentas/juros-compostos/page.tsx
    configuracoes/page.tsx      # conta, Telegram, dispositivos conectados, exclusão
lib/
  api/client.ts                 # axios + baseURL + Authorization + tratamento 401
  api/{auth,transactions,dashboard,investments,calculator,telegram}.ts
  format.ts                     # BRL, percentual, data em America/Sao_Paulo
  types.ts                      # espelho dos schemas Pydantic
components/
  ui/, charts/, forms/, tables/
```

---

## 4. Especificação por módulo

### M1 — Autenticação e conta

**Telas:** Login, Cadastro, Configurações → Conta.

Funcionalidades:

1. **Cadastro** (`POST /auth/register`): e-mail, senha e nome opcional. Já retorna o par de tokens — o usuário entra direto no dashboard sem passar pelo login.
   - Validações espelhando o back-end: e-mail com formato `algo@dominio.tld` (normalizado para minúsculas, 5–255 caracteres); senha de 8 a 72 **bytes UTF-8** (acentos contam mais de um byte — validar por `TextEncoder`, não por `length`); nome até 255 caracteres.
   - `409` → "E-mail já cadastrado".
2. **Login** (`POST /auth/login`): 401 → mensagem genérica "E-mail ou senha inválidos", sem revelar se o e-mail existe.
   - **`429` depois de 5 falhas:** o back-end bloqueia de forma progressiva (10 min, depois 3 h, depois 24 h). Mensagem própria — não é "senha inválida" — e contagem regressiva a partir do cabeçalho `Retry-After`, que vem em segundos. Desabilitar o botão enquanto durar evita o usuário insistir e subir o próximo degrau.
   - O bloqueio vale também para e-mail inexistente, de propósito: fosse diferente, o 429 viraria um jeito de descobrir quais contas existem.
3. **Sessão:** `register`, `login`, `refresh` e `change-password` devolvem o mesmo `TokenResponse`: `access_token` + `expires_at`, `refresh_token` + `refresh_expires_at`, `session_id` e **`user` completo**.
   - **O `user` vem embutido na resposta** (`UserResponse` inteiro: `id`, `email`, `full_name`, `created_at`). Depois de logar, cadastrar, renovar ou trocar a senha, o estado do usuário se hidrata direto do `TokenResponse` — **sem chamar `GET /auth/me`**. O `/auth/me` continua necessário só no boot frio, quando a aplicação sobe com um token guardado e ainda não sabe de quem ele é.
   - **`session_id`** identifica a linha desta sessão em `GET /auth/sessions` (M1.8) e é o que permite marcar "este dispositivo" na lista. Não é credencial. Rotaciona junto com o refresh token, então guardar os dois é a mesma operação — ver o item seguinte.
   - **O access token dura 30 minutos** (`ACCESS_TOKEN_EXPIRE_MINUTES=30`); o refresh token dura 30 dias. Uma sessão sem renovação automática cai em meia hora — a renovação não é opcional.
   - **O refresh token é opaco e rotacionado:** cada `POST /auth/refresh` devolve um valor novo e invalida o apresentado. Guardar sempre o último recebido, sobrescrevendo o anterior — e junto com ele o `session_id`, que também muda a cada rotação (a rotação cria uma linha nova de sessão).
   - **Interceptor:** em `401`, chamar `POST /auth/refresh` uma vez e repetir a requisição original; se o refresh falhar, limpar o estado e ir para o login com "Sua sessão expirou". `POST /auth/refresh` é rota **pública** — não mandar `Authorization` nela, ela existe justamente para quando o access token já expirou.
   - **Single-flight obrigatório:** duas requisições que tomem 401 ao mesmo tempo e disparem dois refreshes com o mesmo token fazem o segundo cair na detecção de reuso, que **derruba todas as sessões do usuário**. As chamadas concorrentes têm de aguardar a mesma promessa de refresh. Vale também entre abas (`BroadcastChannel` ou lock no `localStorage`).
4. **Logout** (`POST /auth/logout`):
   - **Sessão atual:** `{refresh_token}`. Rota **pública** nesse modo — apresentar o refresh token já é a prova de posse. Funciona mesmo com o access token vencido, que é o caso comum de quem volta ao app depois de horas. Sempre chamar o endpoint antes de limpar o estado local: descartar o token só no cliente deixa a sessão viva no servidor por até 30 dias.
   - **Todos os dispositivos:** `{all_devices: true}` exige `Authorization` com access token válido; sem ele, `401`. Se o usuário tomar esse 401, renovar via refresh e repetir.
   - **Corpo vazio é `422`:** sem `refresh_token` e sem `all_devices: true` o back-end responde "Informe o refresh_token ou use all_devices para encerrar tudo". Um `POST /auth/logout {}` não é "sair de qualquer jeito" — o cliente que perdeu o refresh token precisa mandar `all_devices: true` explicitamente.
   - A resposta é `{message}` e é sempre a mesma para token inexistente ou já revogado — não usar o texto para inferir estado.
   - O access token em uso continua valendo até expirar (é stateless); o logout encerra a sessão, não o token já emitido.
5. **Perfil:** exibir nome, e-mail e data de criação vindos de `GET /auth/me`; editar o nome por `PATCH /auth/me` (**só `full_name`** — trocar e-mail não existe no back-end). Nome em branco vira `null`.
6. **Alterar senha** (`POST /auth/change-password`): `{current_password, new_password, revoke_other_sessions?}`. `401` → "Senha atual incorreta"; `422` → nova senha igual à atual ou acima de 72 bytes. `revoke_other_sessions` tem padrão `true` e derruba os outros aparelhos — a resposta traz um par de tokens novo, que **precisa substituir o guardado**, senão o próprio usuário se desloga.
7. **Excluir conta** (`DELETE /auth/me`): ação destrutiva, exige confirmação digitando o e-mail. Deixar explícito que transações, investimentos e o vínculo do Telegram são apagados em cascata.
8. **Dispositivos conectados** (`GET /auth/sessions`): lista das sessões ainda válidas, da atividade mais recente para a mais antiga. Cada item traz `id`, `user_agent`, `created_at` e `expires_at`.
   - `user_agent` é o rótulo do aparelho e **pode ser nulo** (cliente sem cabeçalho `User-Agent`: script, `curl`). Cair para "Dispositivo desconhecido" em vez de deixar a linha sem título.
   - `created_at` é a **última atividade**, não o primeiro login: cada renovação de token cria uma sessão nova e revoga a anterior. Rotular como "Ativa desde", não como "Conectado em".
   - **Marcar a sessão atual comparando `id` com o `session_id` guardado** (M1.3). O servidor não sabe qual é a atual — o access token é stateless e não guarda de qual sessão nasceu.
   - Lista pura, sem `total`, com `limit` (padrão 50, máx 200) e `offset`. Na prática cabe numa página só; paginar até receber menos itens que o `limit` se quiser garantir.
   - Sessões revogadas e vencidas **não** aparecem: a lista é de aparelhos conectados agora, não de histórico.
   - A única ação disponível sobre a lista é **Encerrar todas as sessões** (`POST /auth/logout {all_devices: true}`) — não existe endpoint para derrubar uma sessão específica. Não desenhar um botão "encerrar" por linha.

### M2 — Shell do dashboard

- Sidebar com Visão geral, Transações, Investimentos, Ferramentas, Configurações.
- Seletor global de período (Hoje, Semana, Mês, 3 meses, Ano, Personalizado) alimentando `start`/`end` da visão geral e das transações. Refletir o período na URL (query string) para links compartilháveis e recarregamento consistente.
- Estados globais de *loading*, *empty* e *erro*, mais um toaster para sucesso/falha.
- Formatação centralizada: valores em BRL, datas em `America/Sao_Paulo`, percentuais com sinal e cor.

### M3 — Visão geral

Fonte: `GET /dashboard/summary?start=&end=&type=` e `GET /dashboard/timeseries`.

- Três KPIs: receitas, despesas e saldo (com cor conforme sinal).
- Gráfico de despesas por categoria (`by_category`, já ordenado do maior para o menor). Rótulo "Sem categoria" já vem tratado pelo back-end.
- **Composição de receitas:** o parâmetro `type` (padrão `expense`) escolhe o que `by_category` agrega, e a resposta traz `by_category_type` dizendo qual tipo foi agregado — usar esse campo no rótulo do gráfico em vez de assumir despesas.
- **Gráfico de evolução** (`GET /dashboard/timeseries?granularity=day|week|month&start=&end=`, padrão `month`): períodos sem lançamento já vêm com zero, então o eixo não tem buracos. Acima de 1000 pontos o back-end devolve `422` — a UI deve escolher a granularidade a partir do tamanho do período em vez de deixar o usuário cair no erro.
- Tabela compacta das categorias com valor e participação percentual (calculada no front sobre o total de despesas).
- Atalhos: "Novo lançamento", "Importar planilha", "Ver todas as transações" (levando o mesmo período).
- Bloco resumido da carteira (`GET /investments/portfolio`): valor de mercado, custo investido e ganho não realizado, com link para Investimentos.
- Estado vazio orientando o primeiro lançamento e a conexão do Telegram.

> Semântica de período a respeitar: `start` é inclusivo e `end` é **exclusivo** (`occurred_at < end`). O seletor "Mês" deve enviar o primeiro dia do mês seguinte como `end`.

### M4 — Transações

Fonte: `GET /transactions` com `start`, `end`, `category`, `type`, `search`, `limit` (1–200, padrão 50), `offset`.

1. **Tabela** (`@tanstack/react-table`) com data, descrição, categoria, tipo, forma de pagamento, origem e valor. Ordenação vem do servidor por `order_by` e `order` (padrão: data decrescente); o desempate por `id` é sempre aplicado, então paginar por offset não repete nem pula linhas. Ordenar a tabela deve refazer a consulta, não reordenar a página carregada.
2. **Filtros:** período, tipo (receita/despesa), categoria e busca textual. A busca do back-end é `ILIKE` sobre descrição **e** categoria — explicitar isso no placeholder.
   - As opções do filtro de categoria vêm de `GET /transactions/categories?start=&end=&type=`, que devolve `{category, count}` por frequência. Nulos e vazios não geram opção — "Sem categoria" continua sendo um estado da linha, não uma opção de filtro.
3. **Paginação** por `limit`/`offset`, usando `total` para calcular as páginas.
4. **Badge de origem:** `source` tem **três** valores, não dois — `web`, `telegram` e `import`. Quem entrou por planilha grava `source="import"` (`services/spreadsheets.py`), e numa base migrada de planilha esse é o volume maior. Um badge binário renderiza vazio ou errado justamente na maioria das linhas. Tratar os três explicitamente e ter um rótulo de fallback para valor desconhecido.
5. **Criar** (`POST /transactions`): descrição (1–255), valor > 0 com 2 casas, categoria opcional (até 100), tipo, forma de pagamento opcional (até 50), data/hora opcional.
   - Enviar `occurred_at` em ISO. Datas sem fuso são interpretadas como `America/Sao_Paulo` pelo back-end; o mais seguro é enviar o offset explícito.
   - `source` é definido pelo servidor como `web` — não enviar.
6. **Editar** (`PATCH`): envio parcial. Campos `description`, `amount`, `type` e `occurred_at` não aceitam `null` (422).
7. **Excluir** (`DELETE`): confirmação e remoção otimista com desfazer.
8. **Ações em lote:** desejáveis (excluir várias, recategorizar), mas hoje exigiriam N chamadas — implementar apenas se aceitarmos o custo, ou aguardar endpoint em lote.
9. **Exportar** (`GET /transactions/export?format=csv|xlsx&start=&end=`): o endpoint é autenticado, então **não funciona em `<a href>` simples** — baixar via `axios` com `responseType: "blob"` e disparar o download a partir do objeto URL.
   - **A exportação aceita só `format`, `start` e `end`.** `category`, `type` e `search` **não** são parâmetros dessa rota — mandá-los é inofensivo e inútil, o servidor ignora. Quem filtrou por "Mercado" e clicou em Exportar recebe o período inteiro, sem filtro de categoria.
   - Por isso o botão não pode se chamar "Exportar resultados". Rotular pelo que ele faz de verdade — "Exportar período" — e, quando houver filtro de categoria, tipo ou busca ativo, avisar antes do download que o arquivo sai com o período completo. Um alerta ao lado do botão custa menos que um usuário conferindo a planilha errada.

### M5 — Importação de planilhas

Fonte: `POST /transactions/import` e `GET /transactions/imports/{job_id}`.

- Upload por arrastar-e-soltar aceitando **apenas `.csv` e `.xlsx`**, com limite de **10 MiB** e **10.000 linhas** validados no cliente antes do envio (evita 413/422 tardios).
- Guia de formato exibido na tela, com as colunas aceitas (o back-end reconhece cabeçalhos em português e inglês):

  | Campo | Cabeçalhos aceitos |
  | --- | --- |
  | Descrição | `description`, `descricao`, `descrição` |
  | Valor | `amount`, `valor` |
  | Categoria | `category`, `categoria` |
  | Tipo | `type`, `tipo` — valores `income`/`receita`/`entrada` e `expense`/`despesa`/`saida`/`saída` |
  | Forma de pagamento | `payment_method`, `metodo_pagamento`, `método_pagamento` |
  | Data | `occurred_at`, `data`, `date` — formato `AAAA-MM-DD` |

  Oferecer download de um modelo CSV gerado no front.
- **Há dois caminhos de resposta, não um.** O que decide é o tamanho do arquivo (corte em 5 MiB), e o front precisa tratar os dois:
  - **Assíncrono (acima de 5 MiB):** `202` com o job, e o processamento acontece depois. Aqui, e só aqui, `status: "failed"` chega **dentro de um `202`** — o erro é do processamento, que já não estava mais na requisição. Acompanhar por `GET /transactions/imports/{job_id}`.
  - **Síncrono (até 5 MiB):** a importação roda na própria requisição. Se der certo, `202` com `status: "completed"`. Se o arquivo for inválido, a resposta é **`422`** (mensagem de validação em `detail`) ou **`500`** ("Falha ao importar a planilha") — **sem corpo de job**. O `catch` não pode assumir que existe um `job_id` para consultar; ele precisa exibir o `detail` direto.
  - Em ambos os casos o job fica gravado com `status: "failed"` e aparece no histórico — mas na resposta síncrona o cliente descobre isso pelo código HTTP, não pelo corpo.
- Estados do campo `status`, quando há corpo de job:
  - `completed` → mostrar `imported_rows` de `total_rows` e recarregar a lista;
  - `pending`/`processing` → cartão de progresso com *polling* em `GET /transactions/imports/{job_id}` a cada ~3 s;
  - `failed` → exibir `error_message`.
- Tratar `415` (extensão inválida), `413` (acima de 10 MiB), `422` (arquivo vazio ou linha inválida) e `500` (falha inesperada do processamento síncrono) com mensagens distintas.
- **Histórico de importações:** `GET /transactions/imports` devolve o envelope `{items, total, limit, offset}` — é a fonte da tela de histórico e permite retomar um job pendente sem depender do `localStorage`. O conteúdo do arquivo enviado **não** vem nessa listagem, por desenho.
  - **Atenção ao `limit`:** aqui o padrão é **20** e o teto é **100** — diferente dos 50/200 de `/transactions` e dos 200/500 de investimentos. Não reaproveitar a constante de paginação das outras telas; um `limit=200` aqui volta `422`.

### M6 — Investimentos

#### 6.1 Ativos (`/investments/assets`)

- Lista ordenada por ticker com ticker, nome, tipo e moeda.
- Cadastro: ticker (1–32, enviado em maiúsculas), nome opcional, tipo entre `stock`, `fii`, `etf`, `bdr`, `crypto`, `bond`, `fund`, `other`.
- **Moeda travada em BRL** no formulário: o MVP rejeita outras moedas com 422. Deixar o campo visível porém desabilitado, com nota "moedas estrangeiras em evolução futura".
- `409` no cadastro → "Ativo já cadastrado" (a unicidade é por usuário + ticker + moeda).
- Edição permite apenas nome e tipo (`asset_type` não pode ser nulo).
- Exclusão remove as movimentações em cascata — avisar isso na confirmação.

#### 6.2 Movimentações (`/investments/assets/{id}/movements`)

Extrato por ativo, ordenado por data. O formulário deve ser **dinâmico por tipo de movimento**, porque cada tipo tem exigências próprias validadas no servidor:

| Tipo | Campos obrigatórios |
| --- | --- |
| `purchase`, `sale`, `subscription` | quantidade > 0 e preço unitário > 0 |
| `purchase`, `sale` | `trade_kind` (`swing_trade` padrão, ou `day_trade`) |
| `dividend`, `jcp`, `fii_income` | valor bruto **ou** líquido |
| `split`, `reverse_split` | `factor` = nova quantidade / antiga |
| `bonus` | quantidade e custo unitário atribuído |
| `spinoff`, `merger` | `notes` com as instruções do lançamento manual |

Regras adicionais para a UI:

- `occurred_at` **precisa incluir fuso horário**, caso contrário o servidor devolve 422. Usar sempre ISO com offset.
- `costs` é opcional, padrão 0, e nunca negativo.
- `fx_rate` e `fx_rate_date` só fazem sentido juntos (validação servidor). Como o MVP é BRL, manter esses campos ocultos ou em uma seção avançada.
- Erros de custódia chegam como `422` na criação ("venda sem custódia suficiente") e como `409` na exclusão ("a exclusão deixaria vendas sem custódia suficiente") — traduzir para linguagem clara e sugerir corrigir a movimentação anterior.
- **Edição** (`PATCH /investments/movements/{id}`): envio parcial, sem precisar reenviar a movimentação inteira. O servidor funde o envio com a linha atual e valida o **resultado**, então trocar só o `movement_type` pode tornar obrigatórios campos que não estavam no corpo — o formulário de edição deve seguir a mesma tabela de exigências por tipo acima. `422` na custódia negativa, e nesse caso a linha **não** é alterada.
- **Paginação:** a lista de ativos e o extrato aceitam `limit` (padrão **200**, teto **500**) e `offset`. O padrão trunca silenciosamente carteiras maiores que isso — a UI precisa paginar de fato, não confiar na primeira página.
  - **As duas respostas são lista pura, sem envelope e sem `total`.** Não existe contagem para calcular número de páginas: o contrato é **pedir até receber menos itens que o `limit`**. Quem procurar um `total` nessas rotas não vai achar — é decisão de contrato, não omissão. As rotas que têm envelope `{items, total, limit, offset}` são `/transactions` e `/transactions/imports`, e só elas.

#### 6.3 Carteira consolidada (`GET /investments/portfolio`)

Cartões de topo: valor de mercado total, custo investido, ganho realizado, ganho não realizado, retorno sobre custo, TWR, TWR anualizado e MWR (XIRR).

Comportamentos obrigatórios:

- **Campos nulos são estado de negócio, não erro.** `total_market_value` e `total_unrealized_gain` vêm `null` quando algum ativo com quantidade em custódia está sem cotação. Nesse caso, exibir "carteira parcial — atualize as cotações" em vez de `R$ 0,00`.
- `twr`/`twr_annualized` exigem ao menos duas fotografias completas da carteira; `mwr` exige fluxos com 30 dias ou mais.
  - **`profitability_note` é texto fixo e vem sempre**, em toda resposta, independentemente de haver indicador nulo — é a nota metodológica da seção ("indicadores líquidos de custos e brutos de IR; TWR exige duas fotografias; MWR exige 30 dias"), não uma explicação gerada para o caso. Exibir como rodapé permanente do bloco de rentabilidade. Mostrá-lo "só quando houver nulo" faz o texto sumir exatamente quando os indicadores aparecem — e ele explica o que os números significam, não a ausência deles.
  - Para o indicador nulo em si, a mensagem é do front: "aguardando a segunda atualização de cotações" para TWR, "aguardando 30 dias de histórico" para MWR.
- Tabela de posições com quantidade, preço médio, custo investido, cotação atual, valor de mercado, ganho não realizado, ganho realizado, proventos (bruto e líquido), **total vendido (`sales_proceeds`)** e retorno sobre custo. O `sales_proceeds` já vem em `PositionResponse` e é a coluna que fecha a leitura do que saiu da posição.
- **Posições encerradas continuam na resposta.** O back-end percorre todos os ativos cadastrados, inclusive os totalmente vendidos: eles voltam com `quantity: 0`, `average_price: null` e `market_value` forçado a **0** (não nulo — a posição realmente não vale nada, o zero é informação e não ausência de cotação). Sem tratamento, o gráfico de alocação ganha fatias de valor zero e a tabela ganha linhas mortas.
  - Filtrar por `quantity > 0` para os **gráficos de alocação** e para os cartões de topo por posição.
  - **Não descartar essas linhas da tabela:** `realized_gain`, `dividends_net`, `sales_proceeds` e `return_on_cost` seguem significativos — vêm das vendas e dos proventos, e são justamente o resultado consolidado da operação. A saída é uma seção "Posições encerradas", recolhida por padrão, ou um filtro "mostrar encerradas" desligado por padrão.
  - Nessas linhas, `average_price` nulo é estado normal (não há mais custódia para ter preço médio) — exibir "—", nunca `R$ 0,00`.
- **Selo de cotação desatualizada:** cada posição traz `quote.stale` (calculado com `QUOTE_STALE_AFTER_MINUTES`, padrão 60 min) e `quote.collected_at` — mostrar "atualizado há X" e destacar em amarelo quando `stale` for verdadeiro. Posição sem `quote` recebe selo "sem cotação".
- Gráficos: alocação por ativo e por tipo de ativo (agregação feita no front a partir de `market_value`).
- **Curva de evolução** (`GET /investments/snapshots?start=&end=&limit=`): lista pura, em ordem cronológica, das fotografias da carteira. As fotografias são geradas na atualização de cotações — por isso a curva só começa a existir depois da primeira atualização, o mesmo motivo que segura o TWR.
  - **`limit` tem padrão 365 e teto 1000, e corta as fotografias mais antigas — não as mais recentes.** É o comportamento certo para um gráfico de evolução (a curva precisa terminar em hoje), mas significa que o começo da série pode estar faltando sem nenhum aviso na resposta. Se a série voltar com exatamente `limit` pontos, o histórico provavelmente está truncado à esquerda: subir o `limit` ou marcar o início do gráfico como parcial.
  - **`start` e `end` aqui exigem fuso horário explícito; sem ele, `422`.** É a mesma regra do restante de investimentos e o oposto de `/dashboard/*` e `/transactions`, que aceitam data ingênua e assumem `America/Sao_Paulo`. O seletor global de período alimenta as duas famílias com o mesmo valor — se ele emitir data sem offset, o dashboard funciona e só esta curva quebra. Emitir sempre ISO com offset resolve os dois de uma vez (M9).
- **Exportar carteira** (`GET /investments/export?format=csv|xlsx&sheet=positions|movements`): o XLSX traz as duas abas; no CSV o `sheet` escolhe qual sai. Endpoint autenticado — mesmo tratamento de download por blob do M4.9. Campo nulo vem como célula vazia, nunca zero.

#### 6.4 Cotações (`POST /investments/quotes/refresh`)

- Botão "Atualizar cotações" com estado de carregamento; ao concluir, exibir `updated` e a hora de coleta e recarregar a carteira.
- `failed_tickers` não vazio → alerta listando os tickers não encontrados na brapi (normalmente ticker digitado errado).
- `503` → aviso "Provedor indisponível; a carteira mantém as últimas cotações em cache". Nunca tratar como erro fatal da página.
- Vale registrar na UI que a atualização bem-sucedida também gera a fotografia da carteira usada no cálculo do TWR — isso explica por que o indicador aparece só depois de duas atualizações.

### M7 — Simulador de juros compostos

Fonte: `POST /calculators/compound-interest` (rota **pública**, não exige token).

- Formulário: valor inicial (≥ 0), aporte mensal (≥ 0), taxa (> -1) com seletor mensal/anual, e duração com seletor meses/anos (máximo equivalente a 100 anos / 1200 meses).
- Resultado: taxa mensal equivalente, total investido, total em juros e valor final.
- Gráfico de área empilhada (investido × juros) a partir de `schedule`, mais tabela mês a mês expansível.
- Cálculo é feito no servidor — não replicar a fórmula no front, para evitar divergência de arredondamento com o `Decimal` do back-end.

### M8 — Conexão com o Telegram

Fluxo em Configurações, seguindo exatamente a ordem que o back-end exige:

1. `GET /telegram/link` → se `linked` for verdadeiro, exibir status "conectado", `linked_at`, versão do consentimento e data do aceite.
2. Se não estiver conectado: buscar `GET /telegram/privacy-policy` e **renderizar o conteúdo da política na tela** (o back-end devolve texto, versão, data de publicação, hash SHA-256 e URL estável). O aceite só deve ser habilitado após a leitura.
3. `POST /telegram/link` com `consent: true` e `consent_version` igual à versão exibida. Tratar:
   - `409` → a política mudou enquanto a tela estava aberta: recarregar o texto e pedir novo aceite;
   - `422` → consentimento não marcado;
   - `503` → política ainda não publicada no servidor.
4. Exibir o `deep_link` como botão "Abrir no Telegram" **e** como QR Code, com contagem regressiva até `expires_at` (validade padrão de 30 minutos) e botão "Gerar novo link".
5. Explicar o que o bot faz: registrar receitas/despesas por texto ou áudio e consultar saldo por `/saldo dia|semana|mes|3meses`.
6. **Desconectar** (`DELETE /telegram/link`): `404` se não havia vínculo. Avisar na confirmação que a conversa pendente com o bot é descartada e que reconectar exige aceitar a política de novo. O histórico de consentimento é preservado no servidor — o que sai é o `chat_id`, ou seja, o bot para de aceitar mensagens daquele chat.

### M9 — Requisitos transversais

- **Dinheiro:** valores chegam como string decimal no JSON. Não converter para `Number` antes de formatar em telas de investimento (preços têm até 6 casas e quantidades até 8) — formatar a partir da string ou usar uma biblioteca decimal.
- **Fuso horário:** o back-end guarda tudo em UTC e interpreta datas sem fuso como `America/Sao_Paulo`. Exibir sempre em `America/Sao_Paulo`.
- **Erros:** o FastAPI devolve `{"detail": "..."}` em string para os erros de negócio e uma lista de objetos para os 422 de validação do Pydantic — o interceptor precisa tratar os dois formatos.
- **`404` é estado de tela, não erro genérico.** Cinco rotas o devolvem: transação, ativo, movimentação, job de importação e vínculo do Telegram. O caso comum não é digitação errada — é **link ou aba antiga apontando para um registro já excluído**, e `/investimentos/ativos/[id]` é onde isso mais acontece. As rotas de detalhe precisam de um estado "não encontrado" próprio, com caminho de volta para a lista; um toaster de erro sobre uma página vazia não é suficiente. Vale para o mesmo registro excluído em outra aba, não só para deep link.
- **Segurança:** token no cabeçalho `Authorization: Bearer`. `CORS_ORIGINS` não aceita curinga, então a origem do front precisa estar declarada no `.env` do back-end.
- **Acessibilidade e responsividade:** tabelas com rolagem horizontal própria, foco visível, contraste válido nos temas claro e escuro.

---

## 5. Lacunas do back-end que limitam o dashboard

O levantamento de 11/08/2026 listou 13 lacunas. **Doze foram implementadas** no
back-end (detalhe em `07-lacunas-backend-implementadas.md`) e estão descritas nos
módulos acima; a tabela abaixo fica como rastro do que era lacuna e virou o quê.

| Lacuna de 11/08 | Situação | Onde está no plano |
| --- | --- | --- |
| Sem série temporal de receitas/despesas | ✅ `GET /dashboard/timeseries` | M3 |
| `by_category` cobre só despesas | ✅ `type` + `by_category_type` em `/dashboard/summary` | M3 |
| Sem lista de categorias distintas | ✅ `GET /transactions/categories` | M4.2 |
| Sem listagem de importações | ✅ `GET /transactions/imports` | M5 |
| Sem `PATCH` de movimentação | ✅ `PATCH /investments/movements/{id}` | M6.2 |
| `portfolio_snapshots` não exposto | ✅ `GET /investments/snapshots` | M6.3 |
| Sem atualização de perfil (`full_name`) | ✅ `PATCH /auth/me` | M1.5 |
| Sem alteração de senha | ✅ `POST /auth/change-password` | M1.6 |
| Sem desvinculação do Telegram | ✅ `DELETE /telegram/link` | M8.6 |
| Sem refresh token | ✅ `POST /auth/refresh` + `POST /auth/logout` com revogação no servidor | M1.3, M1.4 |
| Sem paginação em ativos e movimentações | ✅ `limit`/`offset` | M6.2 |
| Exportação só de transações | ✅ `GET /investments/export` | M6.3 |
| Ordenação da lista de transações é fixa | ✅ `order_by`/`order` | M4.1 |
| **Sem recuperação de senha esquecida** | ❌ **Continua aberta** | — |

A auditoria de 17/08/2026 achou uma lacuna nova e ela **também já foi fechada**:

| Lacuna de 17/08 | Situação | Onde está no plano |
| --- | --- | --- |
| `refresh_tokens` guardava `user_agent`, `created_at` e `last_used_at` para uma lista de sessões que nenhuma rota expunha | ✅ `GET /auth/sessions` + `session_id` no `TokenResponse` | M1.8 |

### 5.1 A única lacuna que permanece

**Reset de senha por e-mail não existe** e ficou fora do escopo por decisão
registrada (não há provedor de e-mail no projeto). `POST /auth/change-password`
atende só quem lembra a senha atual.

Consequência para a interface: a tela de login **não deve ter** "Esqueci minha
senha" enquanto não houver endpoint — um link que leva a lugar nenhum é pior que
a ausência dele. O usuário que esquecer a senha hoje não tem caminho de
recuperação pela interface.

### 5.2 Armadilhas de implementação herdadas do back-end

Não são lacunas, são comportamentos que o front precisa respeitar:

| Ponto | O que fazer |
| --- | --- |
| Rotação do refresh token derruba tudo se dois refreshes correrem juntos | Single-flight no interceptor, inclusive entre abas (M1.3) |
| `limit` padrão 200 em ativos e movimentações | Paginar de verdade; a primeira página não é a carteira inteira (M6.2) |
| Teto de 1000 pontos no `timeseries` | Derivar a granularidade do tamanho do período (M3) |
| Access token revogado ainda vale até expirar | Não tratar logout/troca de senha como corte imediato de acesso; a janela é de até 30 min |
| Login bloqueia progressivamente após 5 falhas | Tratar `429` com `Retry-After` na tela de login (M1.2) |
| Fuso: transações/dashboard assumem `America/Sao_Paulo`, investimentos **rejeitam** data sem fuso | Enviar sempre ISO com offset explícito (M9) |
| `source` tem três valores (`web`, `telegram`, `import`) | Badge com três rótulos e fallback; planilha importada é o volume maior (M4.4) |
| Exportação de transações só aceita `format`, `start` e `end` | Não prometer "exportar resultados filtrados"; avisar quando houver filtro ativo (M4.9) |
| Importação até 5 MiB falha com `422`/`500` sem corpo de job | O `catch` não pode assumir `job_id`; exibir o `detail` (M5) |
| Posições zeradas voltam na carteira com `market_value: 0` | Filtrar dos gráficos, manter em "posições encerradas" (M6.3) |
| `404` existe em cinco rotas e não estava na lista de erros tratados | Estado "não encontrado" nas rotas de detalhe (M9) |
| `limit` padrão difere por rota: 50/200, 200/500, 20/100, 365/1000 | Constante por rota, não uma global (M5, M6.2, M6.3) |
| `profitability_note` é texto fixo e sempre presente | Rodapé permanente do bloco de rentabilidade (M6.3) |
| `/health` está fora do prefixo `/api/v1` | Montar a URL a partir da base sem prefixo (§1) |
| `POST /auth/logout` com corpo vazio devolve `422` | Mandar `refresh_token` ou `all_devices: true` (M1.4) |

---

## 6. Fases de entrega sugeridas

**Fase 1 — Fundação utilizável**
Cliente HTTP com o par de tokens, **interceptor de refresh com single-flight**, login, cadastro, logout com revogação no servidor, guard de sessão, shell do dashboard, visão geral (`/dashboard/summary` + `/dashboard/timeseries`) e CRUD completo de transações com filtros, ordenação e paginação.
*Entrega: o usuário consegue viver no dashboard sem depender do Telegram.*

> O interceptor é pré-requisito de tudo o que vem depois: com access token de 30 minutos, qualquer tela testada por mais de meia hora começa a receber 401.

**Fase 2 — Dados para dentro e para fora**
Importação com acompanhamento de job, exportação CSV/XLSX autenticada e conexão com o Telegram (política, consentimento, deep link, status).
*Entrega: migração de planilhas existentes e ativação do bot pela interface.*

**Fase 3 — Investimentos**
Ativos, movimentações com formulário dinâmico por tipo, carteira consolidada com indicadores e nulos tratados, atualização de cotações e selo de cotação desatualizada.
*Entrega: a parte do back-end hoje totalmente inacessível ao usuário final passa a ser utilizável.*

**Fase 4 — Ferramentas e acabamento**
Simulador de juros compostos, configurações de conta (alterar senha, editar nome, dispositivos conectados, encerrar todas as sessões, excluir conta), tema claro/escuro, estados vazios, acessibilidade e responsividade.

---

## 7. Critérios de aceite

- Toda rota autenticada do back-end tem, no dashboard, um caminho de uso pela interface — ou uma justificativa registrada aqui.
- **Sessão:** uma aba aberta por mais de 30 minutos continua funcionando sem novo login, e o refresh token guardado é sempre o último recebido.
- **Single-flight:** com o access token vencido, disparar várias requisições ao mesmo tempo produz **um** `POST /auth/refresh` — não vários. Um teste que force esse cenário faz parte do aceite, porque a falha aqui desloga o usuário de todos os aparelhos.
- **Logout:** sair da conta com o access token já vencido revoga a sessão no servidor (o refresh token deixa de renovar), e não apenas limpa o estado local.
- Nenhum valor monetário é formatado a partir de `float`; nenhum campo nulo da carteira aparece como `R$ 0,00`.
- Erros `401`, `404`, `409`, `413`, `415`, `422`, `429`, `500` e `503` têm mensagem específica em português; `429` no login mostra a espera restante; `503` de cotação nunca derruba a página da carteira; `404` em rota de detalhe rende uma tela "não encontrado" com volta para a lista.
- Nenhum valor de `source` renderiza badge vazio: `web`, `telegram` e `import` têm rótulo próprio.
- A carteira com posição totalmente vendida não mostra fatia de valor zero no gráfico de alocação, e o resultado realizado dessa posição continua consultável.
- Datas exibidas em `America/Sao_Paulo`; datas enviadas em ISO com offset, e os períodos respeitam `end` exclusivo.
- Importação acima de 5 MiB acompanha o job até `completed` ou `failed`, sobrevivendo a um recarregamento da página.
- O aceite da política do Telegram só é possível após o texto ter sido apresentado, e a versão enviada é a mesma exibida.
- Nenhuma chamada a Supabase direto do navegador.

---

## 8. Arquivos de referência

- `backend/app/api/v1/auth.py`, `transactions.py`, `dashboard.py`, `investments.py`, `calculator.py`, `telegram.py`
- `backend/app/schemas/` (contratos que o front deve espelhar em `lib/types.ts`)
- `backend/app/services/spreadsheets.py` (aliases de colunas e limites de importação)
- `backend/app/services/quote_refresh.py` (cotações, fotografias e TWR)
- `backend/app/services/sessions.py` (emissão, rotação e revogação de refresh token)
- `backend/app/core/config.py` (validade dos tokens, CORS, TTL do link do Telegram, validade da cotação)
- `frontend/package.json`, `frontend/AGENTS.md`
- `resume/04-funcionalidades-backend-telegram-dashboard.md`
- `resume/07-lacunas-backend-implementadas.md` — **fonte canônica do contrato**
