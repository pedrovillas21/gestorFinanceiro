# **Plano de Arquitetura e Especificação Técnica: Gestor Financeiro com IA**

Documento de Visão de Produto, Regras de Negócio e Roadmap de Desenvolvimento

## ---

**1\. Visão Geral do Sistema**

O **Gestor Financeiro Inteligente** é uma plataforma omnicanal que permite o gerenciamento passivo e ágil de finanças pessoais via mensagens de texto e áudio (Telegram/WhatsApp), integrando um dashboard web de alta performance para análise de investimentos, simulações financeiras e monitoramento de ativos do mercado em tempo real.

## **2\. Escolha das Tecnologias & Justificativa Técnica**

### **Back-end: Python (FastAPI)**

**Por que Python é a melhor escolha para este projeto?**

* **Nativo para Inteligência Artificial:** Suporte de primeira classe para a SDK oficial do Gemini (google-genai) e manipulação nativa de fluxos de dados de áudio.  
* **Ecossistema de Dados e Finanças:** Bibliotecas consolidada para cálculo financeiro, processamento de planilhas (pandas, openpyxl) e integração com APIs de mercado financeiro (yfinance, brapi).  
* **Performance com FastAPI:** Framework assíncrono, adequado para webhooks de bots (Telegram/WhatsApp) — desde que cada chamada síncrona longa (pandas, openpyxl, yfinance, SQLAlchemy síncrono) seja empurrada para fora do event loop. O framework não torna assíncrono o código bloqueante escrito dentro de uma rota `async def`; a fronteira operação a operação está definida na **seção 3.1**.

### **Front-end: TypeScript \+ React / Next.js \+ Tailwind CSS 4.0**

* **TypeScript:** Garante tipagem estática rigorosa no contrato de dados (formato, campos obrigatórios, unidades), tornando previsível o que trafega entre API e tela. Não substitui a regra de representação monetária: a checagem é estática e some em runtime, e o `Number` do JavaScript continua sendo IEEE 754 (`0.1 + 0.2 !== 0.3`). Valor em dinheiro segue a **seção 4.4** — nunca é somado como `Number`.  
* **Tailwind CSS 4.0:** Utiliza a nova engine pré-compilada em Rust (Oxide), garantindo compilação ultra-rápida, consumo de memória reduzido e sintaxe simplificada sem a necessidade de tailwind.config.js complexo.  
* **Componentes Visuais & Gráficos:** Integração nativa com bibliotecas como Recharts ou Tremor para dashboards interativos de alta fidelidade visual.

## **3\. Arquitetura da Solução**

| Camada | Tecnologia / Ferramenta | Responsabilidade |
| :---- | :---- | :---- |
| **Canais de Entrada** | Telegram Bot API / WhatsApp Cloud API | Recepção de mensagens de texto e arquivos de áudio (.ogg). |
| **Motor de IA** | Google Gemini 2.5 Flash | Processamento direto de áudio/texto e extração de JSON estruturado com response\_schema. |
| **Back-end API** | Python (FastAPI \+ Pydantic) | Gerenciamento de regras de negócio, webhooks, autenticação e integração com APIs de mercado. |
| **Banco de Dados** | PostgreSQL / Supabase (SQLAlchemy) | Armazenamento de transações, carteira de investimentos e categorias. |
| **Front-end Web** | TypeScript \+ React (Next.js) \+ Tailwind 4.0 | Dashboard interativo, visualização de planilhas, simuladores e cotações em tempo real. |
| **Provedor de Mercado** | brapi / Yahoo Finance API | Consumo de cotações de ações (B3 / Mercado Internacional) em tempo real. |

### **3.1. Fronteira de Execução: o que pode rodar no event loop**

O event loop do FastAPI é **uma única thread**. Qualquer chamada síncrona demorada dentro de uma rota `async def` (ou de uma `BackgroundTask` declarada como `async def`) congela *todas* as requisições em andamento, inclusive os webhooks do bot. `async def` não delega nada para thread nenhuma: só o `await` de um cliente assíncrono devolve o controle ao loop.

**Regra:** dentro de código `async`, só entram operações que se resolvem com `await` de I/O assíncrono. Toda chamada síncrona acima de ~50 ms vai para thread pool (`starlette.concurrency.run_in_threadpool` / `asyncio.to_thread`), para uma rota declarada com `def` (o Starlette já joga em thread pool automaticamente) ou para um worker fora do processo da API.

| Operação | Biblioteca | Natureza | Onde roda |
| :---- | :---- | :---- | :---- |
| Webhook do Telegram | FastAPI | I/O assíncrono | `async def`; valida o secret token, responde `200` na hora e delega o processamento a `BackgroundTasks`, porque o Telegram reenvia o update se a resposta demorar. |
| Chamadas à Bot API (enviar mensagem, baixar áudio) | `httpx.AsyncClient` | I/O assíncrono | Event loop, via `await`. |
| Extração de transação pela IA | `google-genai` (`client.aio.*`) | I/O assíncrono | Event loop, via `await`. É a chamada mais longa do fluxo (segundos) — usar o cliente `aio` aqui não é opcional. |
| Persistência das transações | SQLAlchemy síncrono + `psycopg2` | **Bloqueante** | ⚠️ Dívida técnica conhecida: hoje a sessão síncrona é usada dentro de `processar_update`, que é `async def`. Com o volume atual (um usuário, consultas indexadas de poucos ms) é tolerável; **antes de abrir para mais usuários**, migrar para `asyncpg` + `AsyncSession` ou envolver o trecho em `run_in_threadpool`. |
| Migrations no startup | Alembic | Bloqueante | Roda no `lifespan`, antes de a aplicação aceitar tráfego — bloquear ali é o comportamento desejado. |
| Import/export de planilhas (CSV/XLSX) | `pandas`, `openpyxl` | Bloqueante, CPU-bound | Rota declarada com `def` (thread pool). Acima de ~5 MB ou ~50 mil linhas, sai do request: upload → job assíncrono → notificação, para não ocupar uma thread do pool por minutos. |
| Cotações da B3 / internacionais | `yfinance` (usa `requests`, síncrono) | Bloqueante | Thread pool, **nunca** dentro do request do usuário: um job periódico atualiza um cache (preço + timestamp) e o dashboard lê o cache. Provedor fora do ar não pode derrubar a tela. |
| Cotações via API HTTP direta | `httpx.AsyncClient` (brapi) | I/O assíncrono | Event loop, com timeout explícito e fallback para o último preço em cache. |
| Cálculos da carteira e simulações de juros | Python puro / `pandas` | Bloqueante, CPU-bound | Thread pool. Se passar de centenas de ms, pré-calcular na escrita em vez de na leitura. |

Toda integração HTTP externa declara timeout (hoje: 30 s no cliente do Telegram) — sem timeout, uma chamada pendurada consome a thread ou o slot do loop indefinidamente.

### **3.2. Fronteira de Privacidade: dados que saem do sistema**

O sistema trata dado financeiro pessoal (LGPD, art. 5º, I). Três terceiros veem esse dado, cada um com um controle diferente:

| Terceiro | O que recebe | Controle |
| :---- | :---- | :---- |
| **Telegram** | Toda mensagem trocada com o bot (áudio e texto), por natureza do canal. | Fora do nosso controle — informado ao usuário no aceite. Bots não usam criptografia ponta a ponta. |
| **Google Gemini** | Apenas o binário do áudio (`.ogg`) ou o texto da mensagem atual. | Minimização e termos contratuais, detalhados abaixo. |
| **Supabase (PostgreSQL)** | Dados em repouso: transações, e-mail, hash de senha, vínculo do Telegram. | RLS habilitada em todas as tabelas com dado de usuário; acesso direto pelos papéis `anon`/`authenticated` negado (migration `b75641c60d56`). |

**Minimização — o que é enviado ao Gemini:** só o conteúdo da mensagem em processamento. Nunca acompanham o prompt: `user_id`, `chat_id`, e-mail, nome, saldo, histórico de transações ou qualquer resultado de consulta ao banco. A resposta de saldo é montada **depois**, no backend, a partir do período que a IA classificou — a IA não vê os números do usuário.

**Retenção:** o áudio baixado do Telegram existe apenas em memória durante o processamento; não é gravado em disco nem em bucket. Persistem somente os campos extraídos (valor, descrição, categoria, método, tipo). Não guardamos transcrição bruta.

**Redação prévia:** áudio não permite redação antes do envio — a extração depende do conteúdo original. Portanto o controle não é técnico e sim de consentimento e de escopo: a mensagem de ajuda orienta a enviar apenas o lançamento. Para o canal de texto, o mesmo vale — o texto vai como o usuário escreveu.

**Uso para treinamento:** a chave da API precisa estar em projeto com faturamento ativo (tier pago). Os termos da API do Gemini distinguem o tier gratuito — em que o conteúdo pode ser usado para melhorar os produtos do Google — do tier pago, em que não é. **Item obrigatório antes de qualquer usuário além do desenvolvedor:** confirmar o tier da chave e registrar a data da verificação junto aos Termos Adicionais vigentes da API do Gemini, que mudam com o tempo.

**Consentimento:** o vínculo da conta (`/start` com Deep Link) é o momento do aceite. A tela `conectar-telegram` deve exibir, antes de gerar o link, quais dados saem do sistema e para quem, com link para a política de privacidade; a coluna de aceite (versão do texto + timestamp) fica na tabela de vínculo. Sem esse registro, não há prova de consentimento.

**Logs:** proibido logar áudio, transcrição ou o JSON completo devolvido pela IA. Mensagens de erro de validação podem conter trechos dos campos extraídos — por isso o log da aplicação é tratado como dado pessoal: sem envio para serviços de terceiros sem revisão, e retenção curta.

**Direitos do titular:** exclusão de conta remove as transações em cascata (`ON DELETE CASCADE` em `transactions.user_id`); exportação é atendida pelo próprio export de planilha da Fase 2.

## **4\. Regras de Negócio Fundamentais**

### **4.1. Processamento via Bot de Mensagens**

* **Entrada Multimodal:** O sistema deve aceitar comandos de voz e texto sem formatação pré-definida.  
* **Classificação Automática:** A IA deve identificar o tipo (Receita/Despesa), valor, categoria (Alimentação, Transporte, Moradia, Lazer, etc.) e meio de pagamento.  
* **Confirmação Instantânea:** O bot deve responder com o resumo formatado da transação e o saldo atualizado da categoria.  
* **Fallback de Incerteza:** Se a IA não identificar com clareza o valor ou tipo, o bot deve solicitar confirmação do usuário com botões de opção.

### **4.2. Módulo de Investimentos e Cotações**

* **Atualização em Tempo Real:** Ações e fundos imobiliários registrados pelo usuário devem ter seus preços atualizados via API financeira. "Tempo real" aqui significa **último preço em cache, com o horário da coleta sempre visível na tela** — nenhum número aparece sem carimbo de quando foi obtido.  
* **Dados que precisam ser registrados:** cada movimentação guarda data, tipo (compra, venda, provento, evento corporativo), quantidade, preço unitário e custos (corretagem, emolumentos, taxas). Sem esses campos desde o primeiro lançamento, nenhum dos indicadores abaixo é reconstituível depois.

#### **4.2.1. Preço médio e ganho de capital**

Aporte sozinho não define rentabilidade. As fórmulas são estas, e valem por ativo:

* **Preço médio (custo médio ponderado, critério da Receita Federal):**
  `PM = (Σ quantidade_compra × preço_compra + custos_de_aquisição) ÷ Σ quantidade_compra`
  Venda **não altera o preço médio** — reduz apenas a quantidade em custódia. Custos de compra entram no PM; custos de venda reduzem o resultado da venda.
* **Ganho de capital realizado (na venda):** `quantidade_vendida × (preço_venda − PM) − custos_da_venda`.
* **Resultado não realizado (posição em aberto):** `quantidade × (preço_atual − PM)`.

#### **4.2.2. Os dois indicadores de rentabilidade (não se confundem)**

Cada método trata aportes e retiradas de um jeito; exibir um só, sem rótulo, é o erro clássico. A tela mostra os dois, nomeados:

* **Rentabilidade da carteira — TWR (time-weighted):** neutraliza o efeito de aportes e retiradas, é o número comparável a CDI/IBOV. Quebra-se o período em sub-períodos delimitados por cada fluxo de caixa e encadeia-se:
  `TWR = Π [ (V_fim − FC) ÷ V_ini ] − 1`, onde `FC` é o fluxo (aporte positivo, retirada negativa) ocorrido no sub-período.
* **Rentabilidade do investidor — MWR (money-weighted / XIRR):** taxa que zera o valor presente líquido dos fluxos datados, incluindo o valor de mercado atual como fluxo final. Responde "quanto **o meu dinheiro** rendeu" e é sensível ao momento dos aportes. Resolvida numericamente (Newton), com salvaguarda para não convergência (carteiras muito novas ou fluxos extremos ⇒ exibir "—", nunca um número inventado).
* **Retorno sobre custo (simples, para leitura rápida):** `(valor_de_mercado + vendas + proventos − aportes) ÷ aportes`. Não é comparável a benchmark; rotulado como tal.
* **Anualização:** por dias corridos, base 365 — `(1 + r) ^ (365 ÷ dias) − 1`. Não anualizar períodos menores que 30 dias.

#### **4.2.3. Fluxos que entram no cálculo**

* **Proventos:** dividendos (isentos na pessoa física), JCP (retenção de IR na fonte — registrar valor bruto **e** líquido) e rendimentos de FII. Entram como fluxo de caixa positivo na data do pagamento e **não reduzem o preço médio**.
* **Custos:** corretagem, emolumentos e taxas da B3 e ISS somam ao custo de aquisição na compra e subtraem do resultado na venda. Por padrão, os indicadores são exibidos **líquidos de custos e brutos de imposto de renda**, e a tela diz isso explicitamente.
* **Eventos corporativos:** desdobramento e grupamento ajustam quantidade e preço médio na razão inversa (valor total em custódia inalterado); bonificação entra pela quantidade nova com o custo unitário informado pela empresa; subscrição entra como aporte novo na data da liquidação. Cisão/incorporação exigem lançamento manual assistido.
* **Impostos:** o cálculo de IR (isenção mensal de vendas de ações em swing trade, alíquota de day trade, FII sem isenção) fica **fora do escopo das Fases 1-3** — as alíquotas e faixas mudam por legislação. O que é obrigatório desde já é **guardar os dados que tornam esse cálculo possível depois**: data, quantidade, preço e custos de cada operação, separando swing trade de day trade.
* **Ativos em moeda estrangeira:** guardar o valor na moeda original, a moeda e a taxa de câmbio usada na conversão, com a data. Conversão não é recalculada retroativamente.

### **4.3. Calculadora de Investimentos (Juros Compostos)**

* Permitir simulações alterando: Aporte Inicial, Aporte Mensal, Taxa de Juros (Anual/Mensal) e Período (Anos/Meses).  
* Gerar gráfico comparativo de Valor Total Investido vs. Juros Acumulados.  
* Conversão de taxa anual para mensal é **composta**, nunca dividida por 12: `i_mensal = (1 + i_anual) ^ (1/12) − 1`.

### **4.4. Representação Monetária (regra transversal)**

Dinheiro nunca é ponto flutuante binário. A regra vale nas três camadas — banco, API e navegador — porque basta uma delas converter para `float`/`Number` para o erro entrar e não sair mais.

**Escalas e tipos por camada**

| Grandeza | Banco (PostgreSQL) | Backend (Python) | API (JSON) | Front-end |
| :---- | :---- | :---- | :---- | :---- |
| Valor em reais | `NUMERIC(12, 2)` (já aplicado em `transactions.amount`) | `decimal.Decimal` | **string** decimal com ponto: `"1234.50"` | string até a exibição |
| Preço unitário de ativo | `NUMERIC(18, 6)` | `Decimal` | string | string |
| Quantidade de ativo | `NUMERIC(18, 8)` (frações de cripto/ETF) | `Decimal` | string | string |
| Taxas e percentuais | `NUMERIC(9, 6)` (fração: 0.135000 = 13,5 %) | `Decimal` | string | string |

**Regras de cálculo**

1. **Backend:** todo valor monetário é `Decimal`. Conversão a partir de texto ou de JSON é sempre `Decimal(str(x))` — `Decimal(0.1)` carrega o erro do binário. `float` é proibido em qualquer trecho que faça conta com dinheiro, inclusive em agregações do SQLAlchemy (o `Numeric` do Postgres já devolve `Decimal`; não converter de volta).
2. **Única exceção — a fronteira de desserialização:** o JSON devolvido pela IA chega com o valor como número JSON, logo como `float` no campo `TransacaoExtraida.valor`. Ele vira `Decimal(str(valor))` **antes de qualquer aritmética**, no momento de persistir. Nenhuma soma, comparação ou arredondamento acontece enquanto o número ainda é `float`.
3. **Arredondamento:** `ROUND_HALF_UP` (padrão comercial brasileiro), duas casas, **apenas na fronteira** — ao persistir um valor final e ao formatar para exibição. Truncar é proibido.
4. **Cálculos intermediários** (preço médio, rateio, conversão de câmbio, juros compostos) mantêm no mínimo 6 casas decimais e só arredondam no resultado final. Arredondar a cada passo produz centavos perdidos que não fecham com o extrato.
5. **Divisões e rateios** conferem o fechamento: a soma das partes arredondadas tem de bater com o total; a diferença de centavos vai para a última parcela.
6. **A IA não faz aritmética.** O Gemini extrai o valor da mensagem (`"quarenta e dois e noventa"` → `42.90`); toda soma, saldo e rentabilidade é calculada em Python sobre `Decimal`.

**Fronteira API ⇄ front-end**

O valor trafega como **string** no JSON, não como número. Se for número, `JSON.parse` já entrega um `Number` IEEE 754 e a perda acontece antes de qualquer código nosso rodar. No front-end:

* TypeScript tipa esses campos como `string` (um alias `Money = string` deixa a intenção explícita). A tipagem evita a atribuição errada na hora de compilar; quem preserva a precisão em runtime é a representação escolhida — string, `bigint` em centavos ou decimal —, não o TypeScript.
* Somas e comparações no cliente usam inteiros em centavos (`bigint`) ou uma biblioteca decimal (`decimal.js`, `dinero.js`). `reduce((a, b) => a + b)` sobre `Number` é bug, não estilo.
* Exibição usa `Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })`. O backend também formata (`formatar_brl`) para as mensagens do bot, com o mesmo arredondamento — as duas saídas precisam bater no centavo.

**Moeda:** BRL é a moeda base e única do MVP; o campo de moeda existe desde o início nos ativos (seção 4.2.3) para não exigir migration destrutiva quando entrarem ativos internacionais.

## **5\. Roadmap de Desenvolvimento (Fases)**

### **Fase 1: Core Backend & Bot Telegram (Semanas 1-2)**

* Configuração do ambiente Python (FastAPI, Pydantic, SQLAlchemy).  
* Integração da SDK do Gemini 2.5 Flash com suporte a Structured Outputs e áudio.  
* Criação do Webhook do Bot do Telegram para captura de voz/texto e persistência no banco de dados.

### **Fase 2: Dashboard Web & Gestão Financeira (Semanas 3-4)**

* Setup do projeto Front-end (Next.js/React \+ TypeScript \+ Tailwind 4.0).  
* Construção das telas de Dashboard: resumo de receitas/despesas, visão de tabela estilo planilha e filtros por período.  
* Exportação e importação de planilhas (CSV / XLSX).

### **Fase 3: Módulo de Investimentos & Cotações em Tempo Real (Semanas 5-6)**

* Integração com API de mercado de ações (brapi / yfinance).  
* Criação da tabela interativa da carteira com atualização ao vivo.  
* Implementação da Calculadora Interativa de Juros Compostos e Simulações.

**Nota de Arquitetura:** A escolha do stack Python no back-end e TypeScript/Tailwind 4.0 no front-end garante a separação ideal de responsabilidades: alto desempenho em processamento de dados e IA no servidor, alinhado a uma experiência de usuário moderna, rápida e responsiva no navegador.