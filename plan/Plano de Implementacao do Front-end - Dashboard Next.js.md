# Plano de implementação do front-end — Gestor Financeiro

## Passo 0 — Gravar este plano no repositório

Primeira ação ao sair do modo de planejamento: copiar este documento para `plan/Plano de Implementacao do Front-end - Dashboard Next.js.md`, seguindo a convenção de nomes já usada na pasta (`Plano de Arquitetura e Especificação Técnica...`, `Plano de Preparacao do Ambiente...`).

O `plan/` guarda os documentos de arquitetura do projeto; o `resume/` guarda os relatos de milestone. Este documento é de arquitetura, então vai para o `plan/`.

## Context

O back-end está completo e auditado: 33 rotas sob `/api/v1` (mais `GET /health` fora do prefixo), 103 testes passando, e o contrato canônico registrado em `resume/07-lacunas-backend-implementadas.md`. A especificação de interface existe em `resume/05-plano-funcionalidades-dashboard-frontend.md`, com mapa endpoint→tela auditado nos dois sentidos contra o `openapi()` da aplicação.

O que não existe é o front. `frontend/` é o template puro do `create-next-app`: só `app/page.tsx`, `app/layout.tsx` e `app/globals.css`. Nenhuma tela, nenhum cliente HTTP, nenhum fluxo de sessão. Hoje toda a funcionalidade de investimentos é inacessível ao usuário final — não há bot nem interface para ela.

Este plano cobre a construção completa desse front, dividido em 9 fases. Cada fase é um bloco fechado, com entrega verificável e portão de validação próprio, para que nenhuma sessão de implementação precise carregar o projeto inteiro em contexto.

**Regra de precedência**: quando 05 e 07 divergirem, o 07 vence.

## Decisões de arquitetura

Quatro escolhas que nenhum documento do resume havia feito:

| Camada | Escolha | Consequência |
|---|---|---|
| Camada de dados | TanStack Query sobre axios | Cache, revalidação, polling do job de importação e dedupe prontos. O `@tanstack/react-table` v9 traz uma skill `with-tanstack-query` embutida. |
| Sessão | BFF: Route Handlers do Next + cookie httpOnly | O browser nunca vê o token. Muda a árvore de rotas proposta no 05. |
| Formulários | react-hook-form + zod | O schema zod espelha o Pydantic e vira fonte única de tipo + validação. O formulário dinâmico de movimentação é um discriminated union. |
| Testes | Vitest + RTL nos pontos críticos | Prova automatizada do single-flight (exigência de aceite do 05 §7); resto por checklist manual de fase. |

### Como o BFF funciona

```
browser ──(cookie httpOnly, mesma origem)──> Next Route Handlers ──(Bearer)──> FastAPI
```

- Rotas dedicadas (leem/escrevem cookie, nunca devolvem token ao browser): `POST /api/auth/login`, `/register`, `/refresh`, `/logout`, `/change-password`, `DELETE /api/auth/me`, `GET /api/auth/session`, `GET /api/health`.
- Catch-all `app/api/bff/[...path]/route.ts`: repassa todo o resto para `${API_URL}/api/v1/...` injetando o `Authorization` a partir do cookie. Streama corpo e resposta (cobre multipart de importação e blobs de exportação sem bufferizar).
- O catch-all recusa `auth/(login|register|refresh|logout|change-password|me)` — senão vira um caminho para contornar as rotas dedicadas e vazar `TokenResponse` para o browser.

### Ganhos que o BFF traz de graça

O 05 §1 e o inventário do back-end registram três limitações que deixam de existir com mesma origem, porque o backend não declara `expose_headers` no CORS:

- `Content-Disposition` passa a ser legível → nome real do arquivo de exportação, sem hardcode.
- `Retry-After` passa a ser legível → contagem regressiva real no 429 do login, sem backoff fixo chutado.
- Nenhuma requisição de browser cruza origem → `CORS_ORIGINS` do back-end deixa de ser superfície de erro em produção.

### Três armadilhas do Next 16 que este desenho evita

Verificadas em `frontend/node_modules/next/dist/docs/` (o AGENTS.md do projeto exige consultar essa pasta antes de escrever código de rota, cache e data fetching):

1. `middleware.ts` virou `proxy.ts` no Next 16. Não vamos usá-lo. O guia `01-app/02-guides/backend-for-frontend.md` diz textualmente "Do not rely on proxy alone for authentication and authorization", e `proxyClientMaxBodySize` documenta que, com `proxy.ts` ativo, o Next bufferiza o corpo em memória e trunca em 10MB sem devolver erro — a importação de 10 MiB seria cortada em silêncio e o backend receberia uma planilha corrompida. O guard fica no `layout.tsx` (Server Component lendo cookie) + no próprio Route Handler.
2. "Route Handlers cannot share data between requests" (mesma doc, seção Deployment environment). Um mutex em memória no servidor não é single-flight confiável. O single-flight fica no browser — ver abaixo.
3. `cookies()` é assíncrono (`await cookies()`) e `.set()` só funciona em Route Handler ou Server Function, nunca durante render de Server Component.

### Single-flight do refresh — o ponto mais crítico do projeto

O 07 §6 item 18 e o 05 §5.2 registram: dois `POST /auth/refresh` concorrentes com o mesmo token caem na detecção de reuso e derrubam todas as sessões do usuário. Não há janela de graça — o 08 §7 marca isso como decisão fechada, não reabrir.

Desenho, no `lib/api/http.ts`:

- Promessa compartilhada no módulo → serializa dentro da aba.
- `navigator.locks.request('auth-refresh', ...)` → serializa entre abas (mutex real do browser, superior ao BroadcastChannel sugerido no 05).
- Double-checked locking: cookie companheiro `sess_epoch` (não-httpOnly, sem segredo, contém só o `expires_at` do access token). Ao adquirir o lock, relê o cookie; se mudou desde o 401 observado, outra aba já renovou — pula o refresh e só repete a requisição original.
- Como o cookie é compartilhado entre abas, não há valor de token para sincronizar — vantagem estrutural sobre o desenho em localStorage.
- 401 vindo do próprio `/api/auth/refresh` = logout duro; o servidor já encerrou tudo.

## Estrutura de arquivos

Adaptação da árvore do 05 §3 para o BFF:

```
frontend/
  app/
    (public)/login/page.tsx
    (public)/cadastro/page.tsx
    (dashboard)/layout.tsx                 # guard server-side + shell
    (dashboard)/page.tsx                   # visão geral
    (dashboard)/transacoes/page.tsx
    (dashboard)/transacoes/importar/page.tsx
    (dashboard)/investimentos/page.tsx
    (dashboard)/investimentos/ativos/page.tsx
    (dashboard)/investimentos/ativos/[id]/page.tsx
    (dashboard)/ferramentas/juros-compostos/page.tsx
    (dashboard)/configuracoes/page.tsx
    api/auth/{login,register,refresh,logout,change-password,session,me}/route.ts
    api/bff/[...path]/route.ts
    api/health/route.ts
  lib/
    session/cookies.ts                     # nomes, opções e leitura/escrita do TokenResponse
    server/upstream.ts                     # fetch para o FastAPI + injeção do Bearer
    api/http.ts                            # axios -> /api/bff + single-flight
    api/{auth,transactions,dashboard,investments,calculator,telegram}.ts
    api/pagination.ts                      # constantes de limit POR ROTA
    errors.ts · format.ts · types.ts · schemas/*.ts
  components/{ui,charts,forms,tables}/
  proxy.ts                                 # NÃO CRIAR (ver armadilha 1)
```

## Fases

Mapeamento com as fases do 05 §6: F0–F2 aqui = Fase 1 do 05; F3–F4 = restante da Fase 1; F5 = Fase 2; F6–F7 = Fase 3; F8 = Fase 4.

Transações vêm antes da visão geral (invertendo o 05): sem lançamentos cadastrados o dashboard não tem o que mostrar, e o CRUD é o que torna a visão geral verificável de imediato.

### Fase 0 — Higiene e fundação do projeto

**Dependências.** Remover `@supabase/supabase-js` (o 05 §1, o aceite do 05 §7 e o 08 §3 pedem isso em três lugares: a RLS é ENABLE/FORCE com negação por padrão, todo acesso passa pela API). Adicionar `@tanstack/react-query`, `react-hook-form`, `zod`, `decimal.js`, e em dev `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`, `@vitejs/plugin-react`.

`decimal.js` é necessário onde há aritmética, não formatação: percentual de participação por categoria (M3) e agregação da alocação por tipo de ativo (M6.3). Formatação pura sai de `Intl.NumberFormat` sobre a string.

**Configuração.**

- `app/layout.tsx`: metadata real (hoje é "Create Next App"), `lang="pt-BR"`, tokens de tema claro/escuro.
- `.env.local.example`: trocar por `API_URL=http://localhost:8000` — server-only, sem `NEXT_PUBLIC_`, já que o browser nunca fala com o FastAPI. Remover as variáveis de Supabase.
- `tsconfig.json`: alias `@/*`. `vitest.config.ts` com ambiente jsdom.
- Limpar template: `app/page.tsx`, assets de `public/`.
- Commitar o bloco `nextjs-agent-rules` do `frontend/AGENTS.md` junto (ele é reescrito pelo `next dev`; deixá-lo fora só recria a alteração não commitada).

**Validação**: `npm run build`, `npm run lint` e `npm test` verdes. `grep supabase` não retorna nada em `app/` e `package.json`.

### Fase 1 — BFF, sessão e contrato de tipos

O bloco de maior risco. Nada depois funciona sem ele.

- `lib/session/cookies.ts` — cookies httpOnly, `sameSite: 'lax'`, `secure` em produção, `path: '/'`. Guardar os três valores do `TokenResponse`: `access_token`, `refresh_token` e `session_id` (o 07 §6 item 20: o `session_id` rotaciona a cada refresh e é o que identifica "este dispositivo" em `GET /auth/sessions` — se não for reescrito junto, o destaque quebra). Mais o `sess_epoch` não-httpOnly do double-checked locking.
- `lib/server/upstream.ts` — fetch para `${API_URL}/api/v1`, injeção do Bearer, repasse do `User-Agent` do browser (o back-end o grava como rótulo do dispositivo, truncado em 255).
- Rotas dedicadas de auth. `login`/`register`/`change-password` gravam o par novo em cookie e devolvem ao browser apenas o `user` — o `TokenResponse` já traz o `UserResponse` inteiro, então não há chamada extra a `/auth/me` (07 §6 item 19).
- `POST /api/auth/logout` — sempre chamar o endpoint antes de limpar o cookie; descartar só no cliente deixa a sessão viva por até 30 dias no servidor. Corpo vazio devolve 422: mandar `{refresh_token}` ou `{all_devices: true}`.
- Catch-all `api/bff/[...path]/route.ts` — GET/POST/PATCH/DELETE, streaming de `request.body` e de `response.body`, repasse de `Content-Type`, `Content-Disposition` e `Retry-After`.
- `api/health/route.ts` — o `/health` está montado na raiz do FastAPI, fora de `/api/v1`; é a única rota nessa condição.
- `lib/api/http.ts` — axios com `baseURL: '/api/bff'` + o single-flight descrito acima.
- `lib/errors.ts` — o `detail` do FastAPI é polimórfico: string em erro de negócio, array de objetos em validação do Pydantic. `PATCH /investments/movements/{id}` devolve array até dentro de um 422 levantado à mão. Normalizar com `Array.isArray(detail)` e mapear 401/404/409/413/415/422/429/500/503 para mensagens em português.
- `lib/format.ts` — BRL a partir de string decimal (nunca `Number` antes de formatar: preços têm 6 casas, quantidades 8), datas em `America/Sao_Paulo`, percentual com sinal e cor, e um emissor de ISO sempre com offset explícito.
- `lib/api/pagination.ts` — constantes por rota, jamais uma global: `/transactions` 50/200, `/transactions/imports` 20/100, `/investments/assets` e `/movements` 200/500, `/auth/sessions` 50/200, `/investments/snapshots` 365/1000 (só `limit`, sem `offset`). Um `limit=200` em `/transactions/imports` devolve 422.
- `lib/types.ts` + `lib/schemas/` — espelho dos Pydantic. Atenção: senha valida 8–72 bytes UTF-8, não caracteres — acento conta mais de um byte, validar por `TextEncoder`.
- Distinguir os dois envelopes de lista: `{items,total,limit,offset}` existe só em `/transactions` e `/transactions/imports`; todo o resto é lista pura, e o contrato é pedir até receber menos itens que o `limit`.

**Testes (Vitest)**: N requisições concorrentes com access token expirado produzem exatamente um `POST /api/auth/refresh`; 401 no próprio refresh vira logout duro; normalização das duas formas de `detail`; formatação decimal a partir de string sem passar por `Number`; emissão de ISO com offset.

**Validação**: suíte verde + curl no BFF confirmando que nenhuma resposta ao browser contém `access_token` ou `refresh_token`.

### Fase 2 — Auth UI e shell do dashboard

- Login — 401 genérico ("E-mail ou senha inválidos", nunca revelando se o e-mail existe). 429 com contagem regressiva lida do `Retry-After` (em segundos) e botão desabilitado enquanto durar; o bloqueio é progressivo (10 min → 3 h → 24 h) e vale também para e-mail inexistente, de propósito. Sem link "Esqueci minha senha" — o endpoint não existe (05 §5.1), e link que não leva a lugar nenhum é pior que a ausência dele.
- Cadastro — 409 → "E-mail já cadastrado". Entra direto no dashboard, sem passar pelo login.
- `(dashboard)/layout.tsx` — guard Server Component lendo o cookie e redirecionando; sidebar (Visão geral, Transações, Investimentos, Ferramentas, Configurações); topbar com menu do usuário e Sair.
- Seletor de período global — Hoje, Semana, Mês, 3 meses, Ano, Personalizado. Refletido na query string para links compartilháveis. `start` é inclusivo e `end` é exclusivo (`occurred_at < end`): "Mês" manda o primeiro dia do mês seguinte.
- Primitivas de loading/empty/error, toaster, tema claro/escuro, QueryClientProvider.

**Validação**: login → dashboard → logout. Aba aberta por mais de 30 minutos continua funcionando sem novo login. Logout com access token já expirado revoga a sessão no servidor (conferir em `GET /auth/sessions`).

### Fase 3 — Transações

Maior tela isolada do projeto.

Antes de escrever código de tabela: `@tanstack/react-table` resolveu para 9.0.0, não a v8 conhecida. O pacote traz skills próprias em `node_modules/@tanstack/react-table/skills/` (`getting-started`, `migrate-v8-to-v9`, `table-state`, `with-tanstack-query`) e um export `./legacy` com a API v8. Ler `getting-started` e `with-tanstack-query` primeiro — mesma classe de risco do Next 16.

- Tabela com ordenação server-side via `order_by`/`order` (`occurred_at|amount|description|category|created_at`, default `occurred_at desc`). Ordenar refaz a consulta, não reordena a página carregada.
- Filtros: período, tipo, categoria, busca. A busca do back-end é ILIKE sobre descrição e categoria — dizer isso no placeholder. Opções de categoria vêm de `GET /transactions/categories` (nulos e vazios não geram opção; "Sem categoria" continua sendo estado da linha, não filtro).
- Paginação `limit`/`offset` usando o `total` do envelope.
- Badge de origem com três valores: `web`, `telegram` e `import` — mais fallback para desconhecido. Numa base migrada de planilha, `import` é a maioria das linhas; um badge binário renderiza errado justamente no volume maior.
- Criar/editar/excluir com zod. POST: `amount > 0` com 2 casas, `source` é definido pelo servidor (não enviar). PATCH é parcial, mas `description`, `amount`, `type` e `occurred_at` não aceitam `null` (422). Exclusão com confirmação e undo otimista.
- Exportar — `GET /transactions/export` aceita só `format` (`csv|pdf`), `start` e `end`. `category`, `type` e `search` não são parâmetros. Rotular o botão "Exportar período", nunca "Exportar resultados", e avisar antes do download quando houver filtro ativo. Baixar via blob (rota autenticada não funciona em `<a href>` simples), usando o nome vindo do `Content-Disposition`.
  - Decisão pós-Fase 3: XLSX saiu da exportação de transações (redundante com CSV — os dois só serializavam a mesma tabela) e virou PDF: extrato formatado e paginável (`app/services/spreadsheets.py::export_transactions_pdf`, reportlab), com totais de receita/despesa/saldo calculados em `Decimal` (nunca float). CSV continua para reimportação em planilha; PDF cobre leitura e compartilhamento. `export_xlsx` permanece no back-end só porque a importação de `.xlsx` ainda depende dela nos testes de round-trip — não é mais alcançável por nenhuma rota de exportação de transações.
- Ações em lote ficam fora: hoje exigiriam N chamadas; aguardar endpoint em lote.

**Validação**: criar, editar, excluir e desfazer; ordenar por cada coluna conferindo que a consulta é refeita; paginar até o fim; exportar CSV e PDF.

### Fase 4 — Visão geral

- KPIs de receitas, despesas e saldo, coloridos por sinal.
- Gráfico por categoria a partir de `by_category` (já vem ordenado desc; nulo já chega como a string "Sem categoria"). O parâmetro `type` (default `expense`) escolhe o que o `by_category` agrega — rotular o gráfico com o campo `by_category_type` da resposta, não assumir despesas.
- Gráfico de evolução (`/dashboard/timeseries`, `granularity=day|week|month`, períodos vazios já preenchidos com zero pelo servidor). Acima de 1000 pontos o back-end devolve 422: derivar a granularidade do tamanho do período em vez de deixar o usuário cair no erro.
- Tabela compacta de categorias com participação percentual calculada no front (decimal.js).
- Bloco resumo da carteira (`/investments/portfolio`) e atalhos que carregam o mesmo período.
- Estado vazio orientando o primeiro lançamento e a conexão com o Telegram.

**Validação**: trocar o período reflete na URL e nos dois gráficos; selecionar um ano inteiro em granularidade diária não produz 422; alternar receita/despesa muda o rótulo do gráfico.

### Fase 5 — Importação e exportação

- Upload drag-and-drop, só `.csv` e `.xlsx`, limites de 10 MiB e 10.000 linhas validados no cliente antes de enviar.
- Guia de formato na tela (o back-end aceita cabeçalhos PT e EN) e template CSV gerado no front.
- Dois caminhos de resposta, divididos em 5 MiB:
  - > 5 MiB (assíncrono): 202 com o job; polling em `GET /transactions/imports/{job_id}` a cada ~3 s. Aqui — e só aqui — `status: "failed"` chega dentro de um 202.
  - ≤ 5 MiB (síncrono): sucesso é 202 com `status: "completed"`; arquivo inválido é 422 ou 500, sem corpo de job. O catch não pode supor que existe um `job_id` para consultar; precisa exibir o `detail` direto.
- Mensagens distintas para 415, 413, 422, 500.
- Histórico via `GET /transactions/imports` (limit 20, teto 100) — permite retomar um job pendente sem depender do localStorage.

**Validação**: importar um arquivo de cada lado do corte de 5 MiB; recarregar a página no meio de um job grande e confirmar que o acompanhamento sobrevive; forçar 415, 413 e 422 e conferir mensagem própria em cada.

### Fase 6 — Investimentos: ativos e movimentações

Ativos — lista ordenada por ticker, com paginação real (limit padrão 200, teto 500): a primeira página não é a carteira inteira, e o padrão trunca em silêncio. Ticker em maiúsculas, tipos `stock|fii|etf|bdr|crypto|bond|fund|other`. Moeda travada em BRL: campo visível porém desabilitado, com nota "moedas estrangeiras em evolução futura" (o MVP rejeita outras com 422). 409 → "Ativo já cadastrado". Edição altera só nome e tipo. Exclusão cascateia movimentações — avisar.

Movimentações — formulário dinâmico por tipo, discriminated union no zod:

| Tipo | Campos obrigatórios |
|---|---|
| purchase, sale, subscription | quantidade > 0 e preço unitário > 0 |
| purchase, sale | trade_kind (swing_trade padrão, ou day_trade) |
| dividend, jcp, fii_income | valor bruto ou líquido |
| split, reverse_split | factor = nova quantidade / antiga |
| bonus | quantidade e custo unitário atribuído |
| spinoff, merger | notes com as instruções do lançamento manual |

`occurred_at` precisa incluir fuso horário, senão 422. Investimentos rejeitam data ingênua; transações e dashboard a interpretam como `America/Sao_Paulo`. Divergência conhecida e fechada (08 §7) — por isso o `lib/format.ts` da Fase 1 sempre emite offset explícito.

`fx_rate` e `fx_rate_date` só fazem sentido juntos; manter escondidos no MVP em BRL.

Custódia: 422 na criação de venda sem custódia suficiente, 409 na exclusão que deixaria vendas descobertas.

PATCH de movimentação funde o envio com a linha atual e valida o resultado — trocar só o `movement_type` pode tornar obrigatórios campos ausentes no corpo. O formulário de edição segue a mesma tabela. Em 422 de custódia a linha não é alterada.

**Validação**: lançar um exemplar de cada um dos 11 tipos; forçar venda sem custódia e conferir o 422; editar um `purchase` para `dividend` e conferir que o formulário exige os campos novos; cadastrar mais de 200 ativos (ou baixar o limit) e conferir que a paginação não trunca.

### Fase 7 — Investimentos: carteira, cotações e evolução

- Cartões: valor de mercado, custo investido, ganho realizado, ganho não realizado, retorno sobre custo, TWR, TWR anualizado, MWR (XIRR).
- Campos nulos são estado de negócio, não erro. `total_market_value` e `total_unrealized_gain` vêm `null` quando algum ativo com custódia está sem cotação → exibir "carteira parcial — atualize as cotações", nunca R$ 0,00. TWR exige duas fotografias completas; MWR exige fluxos cobrindo ≥30 dias.
- `profitability_note` é texto fixo e vem sempre — é a nota metodológica da seção. Rodapé permanente do bloco de rentabilidade; mostrá-lo "só quando houver nulo" faz o texto sumir exatamente quando os indicadores aparecem.
- Tabela de posições: quantidade, preço médio, custo investido, cotação atual, valor de mercado, ganho não realizado, ganho realizado, proventos (bruto e líquido), total vendido (`sales_proceeds`), retorno sobre custo.
- Posições encerradas continuam na resposta com `quantity: 0`, `average_price: null` e `market_value` forçado a 0. Filtrar por `quantity > 0` nos gráficos de alocação e cartões por posição, mas não descartar da tabela: seção "Posições encerradas" recolhida por padrão. `average_price` nulo renderiza "—".
- Selo de cotação: `quote.stale` (padrão 60 min) e `quote.collected_at` → "atualizado há X", amarelo quando velho, "sem cotação" quando `quote` é ausente.
- Gráficos de alocação por ativo e por tipo (agregação no front, com decimal.js).
- Curva de evolução (`/investments/snapshots`): `start` e `end` exigem fuso explícito aqui; limit padrão 365, teto 1000, e corta as fotografias mais antigas. Série voltando com exatamente `limit` pontos provavelmente está truncada à esquerda — sinalizar.
- Atualizar cotações — mostrar `updated` e horário; `failed_tickers` não vazio vira alerta com a lista (normalmente erro de digitação); 503 nunca derruba a página, é "provedor indisponível; a carteira mantém as últimas cotações em cache". Registrar na UI que um refresh bem-sucedido também gera a fotografia usada pelo TWR.
- Exportar carteira (`format=csv|xlsx`, `sheet=positions|movements`; XLSX traz as duas abas). Campo nulo vira célula vazia, nunca zero.

**Validação**: carteira com um ativo sem cotação mostra "parcial" e não R$ 0,00; posição totalmente vendida não gera fatia zerada no gráfico mas continua consultável na tabela; dois refreshes de cotação fazem TWR aparecer; 503 simulado mantém a página de pé.

### Fase 8 — Ferramentas, configurações e acabamento

- Juros compostos — rota pública, sem token. Área empilhada (investido × juros) a partir do `schedule` e tabela mês a mês expansível. Não replicar a fórmula no front: o cálculo é do servidor, e reimplementar diverge do Decimal do back-end no arredondamento.
- Conta — nome, e-mail e `created_at`; `PATCH /auth/me` edita só `full_name` (não existe troca de e-mail); nome em branco vira `null`.
- Alterar senha — 401 → "Senha atual incorreta"; 422 → nova igual à atual ou acima de 72 bytes. `revoke_other_sessions` default `true`. A resposta traz par de tokens novo, que precisa substituir o guardado, senão o próprio usuário se desloga.
- Dispositivos conectados — `user_agent` pode ser `null` → "Dispositivo desconhecido". `created_at` é a última atividade, não o primeiro login: rotular "Ativa desde", não "Conectado em". Sessão atual identificada comparando `id` com o `session_id` do cookie — o servidor não sabe qual é. Não existe rota para encerrar uma sessão específica: não desenhar botão "encerrar" por linha. A única ação é "Encerrar todas as sessões".
- Excluir conta — destrutiva, exige digitar o e-mail. Deixar explícito que transações, investimentos e o vínculo do Telegram são apagados em cascata.
- Telegram, na ordem exata que o back-end exige:
  1. `GET /telegram/link` — se vinculado, mostrar status, `linked_at`, versão e data do consentimento.
  2. Se não: `GET /telegram/privacy-policy` e renderizar o texto na tela; o aceite só habilita após a leitura.
  3. `POST /telegram/link` com `consent: true` e `consent_version` igual à exibida. 409 → a política mudou com a tela aberta, recarregar e pedir de novo; 422 → consentimento não marcado; 503 → política ainda não publicada.
  4. `deep_link` como botão "Abrir no Telegram" e como QR Code, com contagem regressiva até `expires_at` (30 min) e botão "Gerar novo link". Adicionar dep de QR (`qrcode`, build de browser).
  5. Explicar o que o bot faz: registrar receitas/despesas por texto ou áudio, consultar saldo com `/saldo dia|semana|mes|3meses`.
  6. Desvincular (DELETE) — 404 se não havia vínculo. Avisar que a conversa pendente é descartada e que reconectar exige aceitar a política de novo.
- Acabamento — estado "não encontrado" próprio nas rotas de detalhe. O 404 existe em cinco rotas (transação, ativo, movimentação, job de importação, vínculo do Telegram) e o caso comum não é digitação errada, é aba antiga apontando para registro já excluído — `/investimentos/ativos/[id]` é onde isso mais acontece. Mais: tabelas com rolagem horizontal própria, foco visível, contraste válido nos dois temas, responsividade.

**Validação**: varrer os nove códigos de erro (401, 404, 409, 413, 415, 422, 429, 500, 503) confirmando mensagem específica em português para cada; abrir `/investimentos/ativos/<uuid-inexistente>` e conferir a tela de "não encontrado" com caminho de volta.

## Verificação end-to-end

Pré-requisito operacional (08 §2.3): `CORS_ORIGINS` do back-end precisa incluir `http://localhost:3000` — já está no `.env`. Com o BFF, só o servidor Next fala com o FastAPI, mas a variável continua obrigatória para o app subir (o back-end levanta `ValueError` em `*`).

```
# Terminal 1 — API
cd backend; .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — Front
cd frontend; npm run dev
```

Contrato de referência: `http://localhost:8000/docs`.

- Suíte do front: `npm test` (Vitest). Suíte do back: `cd backend; python -m pytest tests -q` (103 testes).
- Build de produção a cada fim de fase: `npm run build` e `npm run lint`.

Aceite crítico, do 05 §7 — o teste que não pode faltar: com access token expirado, disparar várias requisições ao mesmo tempo e provar que sai um único `POST /auth/refresh`. A falha aqui desloga o usuário de todos os aparelhos.

Demais critérios de aceite: nenhum valor monetário formatado a partir de `float`; nenhum campo nulo da carteira exibido como R$ 0,00; nenhum `source` renderizando badge vazio; datas exibidas em `America/Sao_Paulo` e enviadas em ISO com offset; períodos respeitando `end` exclusivo; nenhuma chamada a Supabase direto do navegador.

## Fora de escopo

- Reset de senha por e-mail (C2) — única lacuna funcional aberta, sem provedor de e-mail no projeto. Por isso a tela de login não tem "Esqueci minha senha".
- Ações em lote de transações — exigiriam N chamadas hoje; aguardar endpoint.
- Moedas estrangeiras — o MVP rejeita não-BRL com 422.
- Playwright / E2E — validação manual por checklist de fase, conforme decidido.

## Risco conhecido a registrar

O single-flight desenhado é do lado do browser (Web Locks + double-check por cookie), então não depende de memória compartilhada no servidor e sobrevive a deploy multi-instância. Ainda assim, se o front for para um host que execute Route Handlers como lambdas, vale confirmar que os cookies `Set-Cookie` de refresh estão sendo propagados corretamente sob concorrência — é o único ponto do desenho que a suíte automatizada cobre por simulação e não contra a infraestrutura real.
