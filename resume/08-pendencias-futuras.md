# Pendências futuras

Data: 14/08/2026
Branch: `modelagemFrontEnd`

Este documento existe para uma coisa só: **não perder de vista o que ainda falta**.
Ele é um índice de pendências, não uma especificação — cada item aponta para o
documento onde a decisão e o detalhe já estão escritos.

> **Regra para não recriar o problema que já tivemos:** aqui não se copia conteúdo
> de outro documento, só se aponta para ele. Duas cópias da mesma regra divergem
> em duas semanas — foi exatamente o que aconteceu entre o `05` e o `07` e custou
> uma issue de revisão. Ao fechar um item, marque aqui **e** no documento de
> origem.

Legenda de quando: **P** = antes de ir a produção · **F** = antes/durante o
front-end · **D** = dívida, quando doer.

---

## 1. O caminho crítico

Se for fazer só cinco coisas, são estas — em ordem:

| # | Pendência | Quando | Seção |
| --- | --- | --- | --- |
| 1 | Hospedar back-end e bot com HTTPS estável | P | [2.1](#21-hospedagem) |
| 2 | Aplicar as migrations no Supabase | P | [2.2](#22-migrations-no-supabase) |
| 3 | Decidir `TRUST_PROXY_HEADERS` conforme a hospedagem | P | [2.3](#23-configuração-de-ambiente) |
| 4 | Agendar os dois scripts de manutenção | P | [2.4](#24-tarefas-agendadas) |
| 5 | Rodar a validação manual do que a suíte não alcança | P | [4.1](#41-validação-manual-18-itens) |

O front-end é o maior bloco de trabalho ([seção 3](#3-front-end)), mas não bloqueia
nada acima — e nada acima bloqueia ele, porque a API já está de pé.

---

## 2. Deploy e operação

### 2.1 Hospedagem

**Situação:** o bot só responde com a máquina ligada, via túnel Cloudflare. A API
idem. Detalhe em `bot-telegram-status.md` → "O que falta".

Dois critérios pesam na escolha, mais que domínio próprio:

- **Serviço que hiberna é ruim para webhook.** No *cold start* a requisição
  atrasa e o Telegram reenvia. A idempotência (`processed_telegram_updates`)
  impede duplicidade, mas o usuário percebe a indisponibilidade.
- **Domínio próprio é cosmético.** O Telegram exige HTTPS com certificado
  válido, e aceita `*.onrender.com`, `*.fly.dev` e afins.

### 2.2 Migrations no Supabase

**Nunca foram executadas contra o banco remoto** — só conferidas offline
(`alembic upgrade <rev>:head --sql`). São duas: `a91d3e5c7f60` (`refresh_tokens`
+ `telegram_tokens.unlinked_at`) e `b8f2c1d90a44` (`login_attempts`).

O `lifespan` do `app/main.py` roda `upgrade head` na subida, então **o primeiro
deploy aplica as duas sozinho**. O que exige atenção é o que isso significa em
produção — inclusive o logout diferido de toda a base: `07`, seções 3.2 e 3.3.

### 2.3 Configuração de ambiente

| Variável | Pendência | Onde |
| --- | --- | --- |
| `TRUST_PROXY_HEADERS` | Decidir conforme a hospedagem. Errar deixa o bloqueio por IP inútil **ou** bloqueia a base inteira | `07` §7.5.1 |
| `CORS_ORIGINS` | Apontar para o domínio real do front (não aceita curinga) | `05` §1 |
| `WEB_APP_URL` | Idem, usado no link enviado a quem não conectou a conta | `05` §1 |
| `TELEGRAM_WEBHOOK_URL` | URL pública definitiva + rodar `scripts/setup_telegram_bot.py` | `backend/README.md` |

### 2.4 Tarefas agendadas

Dois scripts existem e **nenhum está agendado**:

| Script | O que faz | Se não rodar |
| --- | --- | --- |
| `scripts/purge_access_lifecycle.py` | Limpa sessões vencidas e contadores de login | Tabelas crescem para sempre; nada quebra (`07` §7.1) |
| `scripts/refresh_market_quotes.py` | Atualiza cotações e gera as fotografias da carteira | Carteira fica com cotação velha, e **TWR/MWR nunca aparecem** — dependem de duas fotografias |

O segundo é mais urgente que o primeiro: ele não é manutenção, é funcionalidade.

---

## 3. Front-end

**Nada existe além do template do Next.** `frontend/app/` tem só `page.tsx`,
`layout.tsx` e `globals.css` — nenhuma tela, cliente HTTP ou fluxo de sessão.

O plano completo está em `05-plano-funcionalidades-dashboard-frontend.md`, em
quatro fases. O que vale destacar aqui, por ser fácil de esquecer e caro de
descobrir depois:

| Pendência | Quando | Por quê |
| --- | --- | --- |
| Interceptor com refresh **single-flight** | F | Pré-requisito de tudo: com access token de 30 min, qualquer tela testada por meia hora começa a tomar 401. Sem single-flight, dois refreshes simultâneos **derrubam todas as sessões** (`05` M1.3) |
| Tratar `429` na tela de login | F | Bloqueio progressivo devolve 429 + `Retry-After`; sem tratamento vira "erro desconhecido" (`05` M1.2) |
| Paginar ativos e movimentações | F | `limit` padrão 200 trunca **em silêncio** (`05` §5.2) |
| Remover `@supabase/supabase-js` | F | Todo acesso passa pela API; a dependência induz acesso direto ao banco, que a RLS nega (`05` §1) |
| Tela "conectar Telegram" | F | O back-end já exige e persiste consentimento versionado (`bot-telegram-status.md`) |

---

## 4. Testes

### 4.1 Validação manual (18 itens)

A suíte **não abre conexão com banco**, por desenho (`backend/tests/conftest.py`).
Tudo que é `date_trunc`, `DISTINCT`, ordenação estável, `rowcount`, `FOR UPDATE` e
unicidade depende de conferência manual contra um Postgres de verdade.

A lista fica em **`07` §8.1** — checklist com caixas, para marcar conforme rodar.
Vale a pena fazê-la na primeira subida a um ambiente com banco real.

### 4.2 Suíte de integração

Adiada por decisão (exige Docker na máquina e no CI). O desenho está pronto em
`07` §9: `testcontainers[postgresql]`, `alembic upgrade head` uma vez por sessão,
cada teste numa transação com rollback, marcada `@pytest.mark.integration` e
desligada por padrão.

Ela substituiria a checklist de 4.1 por algo que roda sozinho. Enquanto não
existir, **toda mudança em SQL volta a exigir conferência na mão**.

---

## 5. Funcionalidade que falta no back-end

| Pendência | Quando | Situação |
| --- | --- | --- |
| **C2 — reset de senha por e-mail** | P | Única lacuna funcional aberta. Sem provedor de e-mail no projeto. Quem esquece a senha **não tem caminho de recuperação** (`07` §10) |
| Ações em lote de transações | D | Excluir/recategorizar várias hoje exige N chamadas (`05` M4.8) |
| Moedas estrangeiras em investimentos | D | O MVP rejeita tudo que não é BRL com 422 (`05` M6.1) |

Sobre o C2, o que falta é concreto: escolher provedor, chave em `Settings` (**e no
`AMBIENTE_DE_TESTE` do `conftest`**, senão a suíte inteira falha), tabela de token
de uso único e template. O rate limit não precisa nascer do zero —
`app/services/login_throttle.py` é genérico por escopo, basta um `reset:<e-mail>`.

Enquanto não existir, a tela de login **não deve ter** "Esqueci minha senha": um
link que não leva a lugar nenhum é pior que a ausência dele.

---

## 6. Dívida técnica conhecida

Nada aqui está quebrado; tudo aqui envelhece mal.

| Item | Quando | Detalhe |
| --- | --- | --- |
| Exportação e carteira carregam tudo em memória, com N+1 pré-existente por ativo | D | `07` §7.6 |
| `MAX_POINTS = 1000` no timeseries é arbitrário | D | Se uma tela precisar de mais, o número muda junto (`07` §7.7) |
| Sem rate limit em `/auth/register` | D | Registro em massa é spam de contas, não roubo de acesso |

---

## 7. Decisões fechadas — **não são pendências**

Esta seção existe para você não reabrir discussão já resolvida, e para eu não
"corrigir" no futuro algo que foi escolhido de propósito.

| Comportamento | Por que é assim |
| --- | --- |
| Access token revogado vale até expirar (até 30 min) | Fechar a janela exigiria consultar o banco a cada requisição autenticada. Foi por isso que o token caiu de 7 dias para 30 min (`07` §7.4) |
| Dois refreshes simultâneos derrubam todas as sessões | É a detecção de reuso funcionando. A defesa é single-flight no cliente; a "janela de graça" foi **recusada** por enfraquecer a detecção (`07` §7.2) |
| Sem banimento permanente de IP | Com NAT/CGNAT puniria inocentes, e um atacante poderia provocá-lo para derrubar terceiros (`07` §7.5) |
| Login certo não zera o contador do IP | Senão bastaria ter conta própria para limpar o contador entre rajadas (`07` §7.5) |
| Investimentos rejeitam data sem fuso; transações assumem `America/Sao_Paulo` | Divergência pré-existente; o front sempre manda ISO com offset (`07` §6.2) |
| Paginação de investimentos é lista pura, sem envelope | Decisão B3 (`07` §2) |
| A suíte não toca banco | Decisão de projeto, com o guard no `conftest` que aborta se a configuração real vazar |

---

## 8. Onde cada coisa está documentada

| Documento | Papel |
| --- | --- |
| `04-funcionalidades-backend-telegram-dashboard.md` | O que o back-end faz |
| `05-plano-funcionalidades-dashboard-frontend.md` | O que o dashboard precisa ter |
| `06-viabilidade-cobertura-lacunas-backend.md` | Material de decisão das lacunas (histórico) |
| `07-lacunas-backend-implementadas.md` | **Fonte canônica do contrato da API** e das decisões de sessão/segurança |
| `bot-telegram-status.md` | Estado do bot e o que falta para produção |
| `como-rodar-o-bot.md` | Operação em desenvolvimento |
| **`08-pendencias-futuras.md`** | Este índice |
