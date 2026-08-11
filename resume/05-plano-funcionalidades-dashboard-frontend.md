# Plano de funcionalidades do dashboard front-end

Data do levantamento: 11/08/2026
Base: código do back-end em `backend/app` (rotas `/api/v1`), conforme estado atual do branch `modelagemFrontEnd`.

Este documento define **o que o dashboard precisa ter** para consumir tudo o que o back-end já entrega hoje. Ele complementa `04-funcionalidades-backend-telegram-dashboard.md`, que descreve o back-end; aqui a ótica é a da interface.

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

---

## 2. Mapa: endpoint do back-end → tela do dashboard

| Endpoint | Método | Tela / componente proposto |
| --- | --- | --- |
| `/auth/register` | POST | Cadastro |
| `/auth/login` | POST | Login |
| `/auth/me` | GET | Guard de sessão + menu do usuário |
| `/auth/me` | DELETE | Configurações → Excluir conta |
| `/dashboard/summary` | GET | Visão geral (KPIs + gráfico por categoria) |
| `/transactions` | GET | Transações → tabela com filtros e paginação |
| `/transactions` | POST | Modal "Novo lançamento" |
| `/transactions/{id}` | GET/PATCH/DELETE | Painel de detalhe / edição inline / confirmação de exclusão |
| `/transactions/import` | POST | Transações → Importar planilha |
| `/transactions/imports/{job_id}` | GET | Cartão de progresso da importação (polling) |
| `/transactions/export` | GET | Botão "Exportar" (CSV/XLSX) |
| `/investments/assets` | GET/POST | Investimentos → Ativos |
| `/investments/assets/{id}` | PATCH/DELETE | Edição e exclusão de ativo |
| `/investments/assets/{id}/movements` | GET/POST | Detalhe do ativo → extrato de movimentações |
| `/investments/movements/{id}` | DELETE | Exclusão de movimentação |
| `/investments/portfolio` | GET | Investimentos → Carteira consolidada |
| `/investments/quotes/refresh` | POST | Botão "Atualizar cotações" |
| `/calculators/compound-interest` | POST | Ferramentas → Simulador de juros compostos |
| `/telegram/privacy-policy` e `/{version}` | GET | Modal de consentimento (leitura obrigatória) |
| `/telegram/link` | POST/GET | Configurações → Conectar Telegram |
| `/health` | GET | Indicador opcional de disponibilidade da API |

Endpoints sem tela: `/telegram/webhook` (uso exclusivo do Telegram).

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
    configuracoes/page.tsx      # conta, Telegram, exclusão
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

1. **Cadastro** (`POST /auth/register`): e-mail, senha e nome opcional. Já retorna o JWT — o usuário entra direto no dashboard sem passar pelo login.
   - Validações espelhando o back-end: e-mail com formato `algo@dominio.tld` (normalizado para minúsculas, 5–255 caracteres); senha de 8 a 72 **bytes UTF-8** (acentos contam mais de um byte — validar por `TextEncoder`, não por `length`); nome até 255 caracteres.
   - `409` → "E-mail já cadastrado".
2. **Login** (`POST /auth/login`): 401 → mensagem genérica "E-mail ou senha inválidos", sem revelar se o e-mail existe.
3. **Sessão:** guardar `access_token` e `expires_at` (validade padrão de 7 dias — `ACCESS_TOKEN_EXPIRE_MINUTES=10080`). O layout do dashboard valida a sessão com `GET /auth/me`.
   - Não existe refresh token: ao chegar em `expires_at`, ou ao receber `401`, limpar o estado e redirecionar para o login com aviso "Sua sessão expirou".
   - Logout é client-side (descarte do token); não há revogação no servidor.
4. **Perfil:** exibir nome, e-mail e data de criação vindos de `GET /auth/me`.
5. **Excluir conta** (`DELETE /auth/me`): ação destrutiva, exige confirmação digitando o e-mail. Deixar explícito que transações, investimentos e o vínculo do Telegram são apagados em cascata.

### M2 — Shell do dashboard

- Sidebar com Visão geral, Transações, Investimentos, Ferramentas, Configurações.
- Seletor global de período (Hoje, Semana, Mês, 3 meses, Ano, Personalizado) alimentando `start`/`end` da visão geral e das transações. Refletir o período na URL (query string) para links compartilháveis e recarregamento consistente.
- Estados globais de *loading*, *empty* e *erro*, mais um toaster para sucesso/falha.
- Formatação centralizada: valores em BRL, datas em `America/Sao_Paulo`, percentuais com sinal e cor.

### M3 — Visão geral

Fonte: `GET /dashboard/summary?start=&end=`.

- Três KPIs: receitas, despesas e saldo (com cor conforme sinal).
- Gráfico de despesas por categoria (`by_category`, já ordenado do maior para o menor). Rótulo "Sem categoria" já vem tratado pelo back-end.
- Tabela compacta das categorias com valor e participação percentual (calculada no front sobre o total de despesas).
- Atalhos: "Novo lançamento", "Importar planilha", "Ver todas as transações" (levando o mesmo período).
- Bloco resumido da carteira (`GET /investments/portfolio`): valor de mercado, custo investido e ganho não realizado, com link para Investimentos.
- Estado vazio orientando o primeiro lançamento e a conexão do Telegram.

> Semântica de período a respeitar: `start` é inclusivo e `end` é **exclusivo** (`occurred_at < end`). O seletor "Mês" deve enviar o primeiro dia do mês seguinte como `end`.

### M4 — Transações

Fonte: `GET /transactions` com `start`, `end`, `category`, `type`, `search`, `limit` (1–200, padrão 50), `offset`.

1. **Tabela** (`@tanstack/react-table`) com data, descrição, categoria, tipo, forma de pagamento, origem e valor. Ordenação do back-end é fixa (data decrescente, depois id) — ordenar por outras colunas exige ordenação local da página ou novo parâmetro na API.
2. **Filtros:** período, tipo (receita/despesa), categoria e busca textual. A busca do back-end é `ILIKE` sobre descrição **e** categoria — explicitar isso no placeholder.
3. **Paginação** por `limit`/`offset`, usando `total` para calcular as páginas.
4. **Badge de origem:** `web` × `telegram`, para o usuário reconhecer o que entrou pelo bot.
5. **Criar** (`POST /transactions`): descrição (1–255), valor > 0 com 2 casas, categoria opcional (até 100), tipo, forma de pagamento opcional (até 50), data/hora opcional.
   - Enviar `occurred_at` em ISO. Datas sem fuso são interpretadas como `America/Sao_Paulo` pelo back-end; o mais seguro é enviar o offset explícito.
   - `source` é definido pelo servidor como `web` — não enviar.
6. **Editar** (`PATCH`): envio parcial. Campos `description`, `amount`, `type` e `occurred_at` não aceitam `null` (422).
7. **Excluir** (`DELETE`): confirmação e remoção otimista com desfazer.
8. **Ações em lote:** desejáveis (excluir várias, recategorizar), mas hoje exigiriam N chamadas — implementar apenas se aceitarmos o custo, ou aguardar endpoint em lote.
9. **Exportar** (`GET /transactions/export?format=csv|xlsx&start=&end=`): o endpoint é autenticado, então **não funciona em `<a href>` simples** — baixar via `axios` com `responseType: "blob"` e disparar o download a partir do objeto URL. Respeitar o período ativo nos filtros.

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
- **A resposta é sempre HTTP 202**, mesmo quando o processamento foi síncrono. A UI deve olhar o campo `status`:
  - `completed` → mostrar `imported_rows` de `total_rows` e recarregar a lista;
  - `pending`/`processing` (arquivos acima de 5 MiB) → cartão de progresso com *polling* em `GET /transactions/imports/{job_id}` a cada ~3 s;
  - `failed` → exibir `error_message` (o back-end devolve a mensagem de validação quando o erro é do arquivo).
- Tratar `415` (extensão inválida), `413` (acima de 10 MiB) e `422` (arquivo vazio ou linha inválida) com mensagens distintas.
- Como não há endpoint que liste importações, **persistir o `job_id` no `localStorage`** para retomar o acompanhamento se o usuário sair da página.

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
- **Não existe PATCH de movimentação.** A correção é excluir e recriar; a UI deve oferecer um fluxo "Corrigir lançamento" que faça esses dois passos e trate a falha de custódia no meio do caminho.

#### 6.3 Carteira consolidada (`GET /investments/portfolio`)

Cartões de topo: valor de mercado total, custo investido, ganho realizado, ganho não realizado, retorno sobre custo, TWR, TWR anualizado e MWR (XIRR).

Comportamentos obrigatórios:

- **Campos nulos são estado de negócio, não erro.** `total_market_value` e `total_unrealized_gain` vêm `null` quando algum ativo com quantidade em custódia está sem cotação. Nesse caso, exibir "carteira parcial — atualize as cotações" em vez de `R$ 0,00`.
- `twr`/`twr_annualized` exigem ao menos duas fotografias completas da carteira; `mwr` exige fluxos com 30 dias ou mais. Quando nulos, mostrar o texto de `profitability_note`, que o back-end já devolve pronto.
- Tabela de posições com quantidade, preço médio, custo investido, cotação atual, valor de mercado, ganho não realizado, ganho realizado, proventos (bruto e líquido) e retorno sobre custo.
- **Selo de cotação desatualizada:** cada posição traz `quote.stale` (calculado com `QUOTE_STALE_AFTER_MINUTES`, padrão 60 min) e `quote.collected_at` — mostrar "atualizado há X" e destacar em amarelo quando `stale` for verdadeiro. Posição sem `quote` recebe selo "sem cotação".
- Gráficos: alocação por ativo e por tipo de ativo (agregação feita no front a partir de `market_value`).

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

### M9 — Requisitos transversais

- **Dinheiro:** valores chegam como string decimal no JSON. Não converter para `Number` antes de formatar em telas de investimento (preços têm até 6 casas e quantidades até 8) — formatar a partir da string ou usar uma biblioteca decimal.
- **Fuso horário:** o back-end guarda tudo em UTC e interpreta datas sem fuso como `America/Sao_Paulo`. Exibir sempre em `America/Sao_Paulo`.
- **Erros:** o FastAPI devolve `{"detail": "..."}` em string para os erros de negócio e uma lista de objetos para os 422 de validação do Pydantic — o interceptor precisa tratar os dois formatos.
- **Segurança:** token no cabeçalho `Authorization: Bearer`. `CORS_ORIGINS` não aceita curinga, então a origem do front precisa estar declarada no `.env` do back-end.
- **Acessibilidade e responsividade:** tabelas com rolagem horizontal própria, foco visível, contraste válido nos temas claro e escuro.

---

## 5. Lacunas do back-end que limitam o dashboard

Estas funcionalidades são naturais em um dashboard, mas **não têm endpoint hoje**. Cada uma vem com a alternativa possível no front e a sugestão de API.

| Lacuna | Impacto na UI | Alternativa imediata | Endpoint sugerido |
| --- | --- | --- | --- |
| Sem série temporal de receitas/despesas | Não há gráfico de evolução mensal, o gráfico mais esperado da visão geral | Paginar `/transactions` (200 por página) e agregar no cliente — caro e impreciso com muitos dados | `GET /dashboard/timeseries?granularity=month` |
| `by_category` cobre só despesas | Não há gráfico de composição de receitas | Agregar no cliente | Parâmetro `type` em `/dashboard/summary` |
| Sem lista de categorias distintas | O filtro de categoria não tem opções confiáveis | Montar a partir de `by_category` (só despesas) e das transações carregadas | `GET /transactions/categories` |
| Sem listagem de importações | Histórico de importações impossível; é preciso guardar o `job_id` localmente | `localStorage` | `GET /transactions/imports` |
| Sem `PATCH` de movimentação | Correção exige excluir e recriar, com risco de erro de custódia no meio | Fluxo guiado de excluir + recriar | `PATCH /investments/movements/{id}` |
| `portfolio_snapshots` não exposto | Sem curva de evolução do patrimônio investido | Nenhuma | `GET /investments/snapshots` |
| Sem alteração de senha ou recuperação | Configurações incompletas | Nenhuma | `POST /auth/change-password`, fluxo de reset |
| Sem atualização de perfil (`full_name`) | Nome fixo no cadastro | Nenhuma | `PATCH /auth/me` |
| Sem desvinculação do Telegram | Só é possível revogar excluindo a conta inteira | Nenhuma | `DELETE /telegram/link` |
| Sem refresh token | Sessão cai de forma abrupta após 7 dias | Detectar `expires_at`/401 e avisar antes | `POST /auth/refresh` |
| Sem paginação/filtro em ativos e movimentações | Carteiras grandes carregam tudo de uma vez | Filtrar no cliente | `limit`/`offset` nas rotas de investimentos |
| Exportação só de transações | Não é possível exportar a carteira | Gerar CSV no cliente a partir do `portfolio` | `GET /investments/export` |
| Ordenação da lista de transações é fixa | Ordenar por valor exige ordenar apenas a página atual | Ordenação local | Parâmetro `order_by` em `/transactions` |

Nenhuma dessas lacunas bloqueia as fases 1 a 4 abaixo — elas apenas limitam gráficos e conveniências específicas.

---

## 6. Fases de entrega sugeridas

**Fase 1 — Fundação utilizável**
Cliente HTTP com token, login, cadastro, guard de sessão, shell do dashboard, visão geral (`/dashboard/summary`) e CRUD completo de transações com filtros e paginação.
*Entrega: o usuário consegue viver no dashboard sem depender do Telegram.*

**Fase 2 — Dados para dentro e para fora**
Importação com acompanhamento de job, exportação CSV/XLSX autenticada e conexão com o Telegram (política, consentimento, deep link, status).
*Entrega: migração de planilhas existentes e ativação do bot pela interface.*

**Fase 3 — Investimentos**
Ativos, movimentações com formulário dinâmico por tipo, carteira consolidada com indicadores e nulos tratados, atualização de cotações e selo de cotação desatualizada.
*Entrega: a parte do back-end hoje totalmente inacessível ao usuário final passa a ser utilizável.*

**Fase 4 — Ferramentas e acabamento**
Simulador de juros compostos, configurações de conta (incluindo exclusão), tema claro/escuro, estados vazios, acessibilidade e responsividade.

---

## 7. Critérios de aceite

- Toda rota autenticada do back-end tem, no dashboard, um caminho de uso pela interface — ou uma justificativa registrada aqui.
- Nenhum valor monetário é formatado a partir de `float`; nenhum campo nulo da carteira aparece como `R$ 0,00`.
- Erros `401`, `409`, `413`, `415`, `422` e `503` têm mensagem específica em português; `503` de cotação nunca derruba a página da carteira.
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
- `backend/app/core/config.py` (CORS, TTL do link do Telegram, validade da cotação)
- `frontend/package.json`, `frontend/AGENTS.md`
- `resume/04-funcionalidades-backend-telegram-dashboard.md`
