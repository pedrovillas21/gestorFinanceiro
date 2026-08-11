# Funcionalidades do back-end: Telegram e dashboard

Data do levantamento: 10/08/2026

## Resumo executivo

O back-end já cobre autenticação, transações, resumo financeiro, integração com Telegram, importação e exportação de planilhas, carteira de investimentos, cotações e simulador de juros compostos.

Hoje, o Telegram usa somente uma parte desse conjunto: vinculação da conta, ajuda, registro de receitas e despesas por texto ou áudio com IA, confirmação de dados incompletos e consulta de saldo em períodos predefinidos. CRUD completo de transações, planilhas, resumo por categoria, investimentos, cotações e calculadora estão disponíveis somente pela API Web, com a intenção de serem consumidos pelo dashboard.

> Importante: o front-end em `frontend/app/page.tsx` ainda é a tela inicial padrão do Next.js. Portanto, “dashboard” neste documento significa **API pronta para consumo pelo futuro dashboard**, e não uma interface já implementada e integrada.

## Matriz de disponibilidade

| Área | Funcionalidade existente | Telegram hoje | API Web/dashboard |
| --- | --- | --- | --- |
| Conta | Cadastro, login e emissão de JWT | Não | Sim |
| Conta | Consulta do usuário autenticado | Não | Sim |
| Conta | Exclusão da conta e dos dados associados | Não | Sim |
| Privacidade | Consulta pública da política vigente e de versões publicadas | Indireto: requisito para conectar o bot | Sim |
| Vinculação | Geração de Deep Link com consentimento versionado | O `/start <token>` conclui o vínculo | Sim, gera o link e consulta o status |
| Transações | Criação manual de receita ou despesa | Não pela API; o bot grava diretamente no banco | Sim |
| Transações | Criação por texto livre com IA | Sim | Não |
| Transações | Criação por áudio com IA | Sim, até 20 MB | Não |
| Transações | Confirmação de tipo ou valor quando a IA estiver incerta | Sim, por botões e resposta de texto | Não |
| Transações | Listagem, busca, filtros e paginação | Não | Sim |
| Transações | Consulta individual, edição e exclusão | Não | Sim |
| Planilhas | Importação de CSV/XLSX | Não | Sim |
| Planilhas | Acompanhamento de importação assíncrona | Não | Sim |
| Planilhas | Exportação em CSV/XLSX | Não | Sim |
| Resumo financeiro | Receitas, despesas e saldo | Sim, em períodos predefinidos | Sim, com intervalo livre |
| Resumo financeiro | Despesas agrupadas por categoria | Não | Sim |
| Investimentos | Cadastro e manutenção de ativos | Não | Sim |
| Investimentos | Movimentações e validação de custódia | Não | Sim |
| Investimentos | Posição, preço médio, ganhos, proventos e rentabilidade | Não | Sim |
| Investimentos | TWR, TWR anualizado e MWR/XIRR | Não | Sim |
| Cotações | Atualização pela brapi, cache, idade do preço e snapshots | Não | Sim/API e rotina administrativa |
| Calculadora | Simulação de juros compostos com evolução mensal | Não | Sim |
| Operação | Health check, migrations automáticas e worker de importação | Infraestrutura comum | Infraestrutura comum |

## Funcionalidades efetivamente usadas pelo Telegram

### 1. Conexão segura entre conta Web e chat

- A política de privacidade é publicada com versão, data, conteúdo, hash SHA-256 e URL estável.
- O usuário autenticado aceita a versão vigente e solicita um Deep Link em `POST /api/v1/telegram/link`.
- O token de vínculo é temporário e de uso único.
- O comando `/start <token>` associa o `chat_id` do Telegram ao usuário.
- O bot bloqueia comandos e conteúdo livre quando não há vínculo ou quando o consentimento não corresponde à política vigente.
- `GET /api/v1/telegram/link` informa se a conta já está vinculada e registra quando o vínculo e o consentimento ocorreram.

### 2. Registro de receitas e despesas por IA

- O bot aceita texto, legenda, mensagem de voz ou arquivo de áudio.
- Áudios são baixados da API do Telegram e enviados ao Gemini; o conteúdo não é armazenado pelo back-end.
- Uma cascata de dois modelos Gemini tenta devolver um objeto estruturado com tipo, valor, descrição, categoria e método de pagamento.
- A transação confirmada é persistida com origem `telegram`.
- Quando tipo ou valor não podem ser determinados com segurança, o bot cria uma pendência de até 10 minutos e solicita a informação faltante.
- O usuário pode escolher receita/despesa, informar o valor ou cancelar por botões inline.
- Mensagens que não representam lançamento nem consulta financeira recebem uma orientação curta em vez de serem persistidas.

### 3. Consulta de saldo

- O comando `/saldo` retorna receitas, despesas e saldo.
- São aceitos os períodos `dia`, `semana`, `mes` e `3meses`; sem argumento, o padrão é o mês atual.
- Perguntas em linguagem natural, como “quanto gastei essa semana?”, passam pelo Gemini e acionam a mesma consulta.
- O Telegram não retorna lista de lançamentos nem agrupamento por categoria; mostra somente os três totais do período.

### 4. Comandos e proteção operacional

- `/ajuda` e comandos desconhecidos exibem instruções de uso.
- O webhook `POST /api/v1/telegram/webhook` valida o secret enviado pelo Telegram.
- O endpoint responde rapidamente e processa a mensagem em background.
- Cada `update_id` é persistido para impedir processamento duplicado em reenvios do Telegram.
- Falhas são tratadas sem devolver erro ao Telegram e sem registrar o conteúdo financeiro completo nos logs.

## Funcionalidades disponíveis somente para API Web/dashboard

### Autenticação e conta

- `POST /api/v1/auth/register`: cria usuário e já devolve JWT.
- `POST /api/v1/auth/login`: autentica por e-mail e senha.
- `GET /api/v1/auth/me`: retorna o usuário atual.
- `DELETE /api/v1/auth/me`: exclui a conta; as chaves estrangeiras com `CASCADE` removem os dados associados.
- Senhas usam bcrypt e as rotas privadas exigem `Authorization: Bearer <token>`.

O Telegram não cadastra, autentica por senha nem exclui contas. Ele depende de uma conta criada previamente pela API Web.

### Gestão completa de transações

- `GET /api/v1/transactions`: lista transações com paginação e filtros de data, categoria, tipo e busca por descrição/categoria.
- `POST /api/v1/transactions`: cria um lançamento manual com origem `web`.
- `GET /api/v1/transactions/{id}`: consulta um lançamento específico.
- `PATCH /api/v1/transactions/{id}`: altera os campos do lançamento.
- `DELETE /api/v1/transactions/{id}`: exclui o lançamento.
- Todas as operações verificam a propriedade do dado pelo usuário autenticado.

O Telegram atualmente só cria lançamentos; não lista, edita nem exclui transações.

### Importação e exportação de planilhas

- `POST /api/v1/transactions/import` aceita CSV ou XLSX de até 10 MiB e até 10.000 linhas.
- Arquivos de até 5 MiB são processados no próprio request.
- Arquivos maiores que 5 MiB viram jobs persistentes e recuperáveis após falha do processo.
- `GET /api/v1/transactions/imports/{job_id}` retorna estado, totais e eventual erro.
- `GET /api/v1/transactions/export?format=csv|xlsx` exporta os lançamentos, com filtro opcional de período.
- A exportação neutraliza textos que poderiam ser interpretados como fórmula pelo Excel ou outro leitor de planilhas.

Não existem comandos do Telegram para enviar, importar, gerar ou receber planilhas.

### Resumo detalhado do dashboard

- `GET /api/v1/dashboard/summary` calcula receitas, despesas e saldo para qualquer intervalo `start`/`end`.
- Também retorna despesas agrupadas por categoria, ordenadas do maior para o menor total.

O conceito de saldo é compartilhado com o Telegram, mas não o endpoint nem todo o contrato: o bot possui períodos fechados e não devolve categorias.

### Carteira de investimentos

- CRUD de ativos: listar, criar, alterar e excluir.
- Listagem, criação e exclusão de movimentações.
- Movimentações aceitas: compra, venda, dividendos, JCP, rendimento de FII, desdobramento, grupamento, bonificação, subscrição, cisão e incorporação.
- Validações impedem vendas sem custódia suficiente e exigem os campos próprios de cada tipo de movimento.
- A carteira calcula quantidade, preço médio, custo investido, ganho realizado e não realizado, proventos, valor de mercado e retorno sobre custo.
- A resposta também pode incluir TWR, TWR anualizado e MWR/XIRR, retornando ausência explícita quando faltam dados suficientes.
- O MVP consolida a carteira em BRL; campos de câmbio existem para evolução futura, mas ativos em outra moeda são rejeitados no cadastro atual.

Rotas principais: `/api/v1/investments/assets`, `/api/v1/investments/assets/{id}/movements` e `/api/v1/investments/portfolio`.

Não há nenhum comando, intenção da IA ou callback do Telegram ligado a investimentos.

### Cotações de mercado

- `POST /api/v1/investments/quotes/refresh` consulta a brapi para os ativos do usuário.
- Cotações são armazenadas com preço, moeda, provedor e horário de coleta.
- A carteira informa quando o preço está desatualizado e conserva a última cotação se o provedor estiver indisponível.
- Atualizações completas geram snapshots utilizados no cálculo de TWR.
- `scripts/refresh_market_quotes.py` permite atualização periódica de todas as carteiras por cron ou Task Scheduler.

Essa integração alimenta a carteira da API Web e não é usada pelo bot.

### Simulador de juros compostos

- `POST /api/v1/calculators/compound-interest` aceita valor inicial, aporte mensal, taxa mensal ou anual e duração em meses ou anos.
- A resposta contém taxa mensal equivalente, total investido, juros, valor final e série mês a mês para gráficos.
- O período máximo é de 100 anos.

Não existe comando equivalente no Telegram.

## Infraestrutura compartilhada

- FastAPI com contrato OpenAPI em `/docs`.
- `GET /health` para verificação de disponibilidade.
- PostgreSQL/Supabase via SQLAlchemy e migrations Alembic executadas no startup.
- RLS `ENABLE` e `FORCE` nas tabelas com dados pessoais, em modo de negação por padrão para acesso direto via PostgREST.
- Valores financeiros tratados com `Decimal` e normalização monetária centralizada.
- Isolamento dos dados pelo `user_id` nas consultas da API e pelo vínculo `chat_id -> user_id` no bot.
- Worker interno para jobs duráveis de importação de planilhas.
- CORS configurável, sem aceitar origem curinga quando credenciais estão habilitadas.

## Fronteira atual entre os canais

Em termos práticos, o Telegram é hoje um canal rápido de **entrada de lançamentos** e **consulta resumida de saldo**. A API Web/dashboard concentra **administração da conta**, **consulta e manutenção detalhada dos dados**, **planilhas**, **análises por categoria**, **investimentos**, **cotações** e **simulações**.

Embora ambos os canais usem as mesmas tabelas de usuários e transações, o bot não chama internamente as rotas REST do dashboard: ele acessa os serviços e o banco diretamente. Por isso, uma funcionalidade existir na API não a torna automaticamente disponível no Telegram; é necessário criar comando, intenção e resposta específicos no fluxo de `app/services/telegram_bot.py`.

## Arquivos principais usados neste levantamento

- `backend/app/api/v1/auth.py`
- `backend/app/api/v1/transactions.py`
- `backend/app/api/v1/dashboard.py`
- `backend/app/api/v1/investments.py`
- `backend/app/api/v1/calculator.py`
- `backend/app/api/v1/telegram.py`
- `backend/app/services/telegram_bot.py`
- `backend/app/services/gemini.py`
- `backend/app/services/spreadsheets.py`
- `backend/app/services/quote_refresh.py`
- `backend/app/main.py`
- `frontend/app/page.tsx`
