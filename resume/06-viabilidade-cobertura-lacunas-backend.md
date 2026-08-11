# Viabilidade de cobrir as lacunas do back-end

Data do levantamento: 11/08/2026
Origem: análise das 14 lacunas listadas na seção 5 de `05-plano-funcionalidades-dashboard-frontend.md`.

Este documento responde a uma pergunta: **é possível implementar no back-end o que falta para o dashboard?** Ele é material de decisão — nenhuma alteração de código foi feita. A conclusão é que 12 das 14 lacunas são implementáveis com o que já existe no projeto, 1 depende de uma escolha de arquitetura e 1 está bloqueada por falta de infraestrutura.

---

## 1. Duas descobertas do repositório que mudam a estimativa

### 1.1 A suíte de testes não toca banco de dados

`backend/tests/conftest.py` aponta o `DATABASE_URL` para `postgresql://...@localhost:1/banco_de_teste` **de propósito**: a porta 1 não escuta nada, então qualquer conexão acidental falha na hora em vez de acertar um banco real. Os testes existentes cobrem funções puras (dinheiro, JWT, períodos), contratos de schema Pydantic e o registro das rotas (`test_expected_backend_routes_are_registered`).

Consequências práticas:

- Endpoints novos podem ser entregues com testes no mesmo padrão da casa: registro de rota, validação de schema e lógica pura extraída para `app/services/`.
- **Comportamento de SQL não fica coberto por teste automatizado** — agregação por período, `DISTINCT` de categorias, ordenação e paginação precisariam de validação manual contra o Supabase, ou de uma decisão de introduzir testes de integração com banco (hoje inexistentes).
- O `conftest` tem um guard: todo campo novo em `Settings` precisa ser registrado em `AMBIENTE_DE_TESTE`, senão a suíte inteira falha com `RuntimeError`. Qualquer lacuna que exija configuração nova já entra sabendo disso.

### 1.2 Não existe infraestrutura de e-mail

Busca por `smtp|sendgrid|mailgun|resend|email_host|fastapi-mail` em `backend/app/`, `backend/scripts/`, `requirements.txt` e `.env.example`: **nenhuma ocorrência**. Não há provedor, dependência, template nem variável de configuração de e-mail no projeto.

Isso bloqueia especificamente o fluxo de recuperação de senha, e nada além dele.

### 1.3 Ponto favorável: o banco é Postgres em todo lugar

`psycopg2-binary` no `requirements.txt`, Supabase em produção e tipos `UUID` do dialeto PostgreSQL nos models. Como os testes não abrem conexão, não existe restrição de compatibilidade com SQLite. Recursos específicos do Postgres — em especial `date_trunc(..., occurred_at AT TIME ZONE 'America/Sao_Paulo')` — podem ser usados livremente. Isso importa: agregar por UTC erraria a virada do mês para lançamentos da noite, e o `AT TIME ZONE` resolve isso no próprio banco.

---

## 2. Triagem das 14 lacunas

### Grupo A — implementação direta, sem migration e sem decisão pendente

Nove endpoints. Nenhum exige alteração de schema do banco.

| # | Endpoint | Abordagem |
| --- | --- | --- |
| A1 | `GET /dashboard/timeseries` | `date_trunc(granularidade, occurred_at AT TIME ZONE 'America/Sao_Paulo')` agrupado por tipo, com `granularity` em `day`/`week`/`month`. Preencher no servidor os períodos sem lançamento, para o gráfico não sair com buracos. |
| A2 | `type` no `/dashboard/summary` | Hoje `by_category` é fixo em despesas (`dashboard.py:42`). Um parâmetro com valor padrão `expense` mantém o contrato atual intacto e libera a composição de receitas. |
| A3 | `GET /transactions/categories` | `SELECT DISTINCT category` do usuário, ignorando nulos. Vale devolver também a contagem de uso, para o filtro ordenar por frequência em vez de alfabeticamente. |
| A4 | `order_by` em `/transactions` | Lista branca de colunas (`occurred_at`, `amount`, `description`, `category`, `created_at`) mais direção. **Manter sempre o desempate por `id`**: sem critério estável, a paginação por `offset` repete e pula linhas entre páginas. |
| A5 | `GET /transactions/imports` | Listagem paginada por `created_at` decrescente. Cuidado obrigatório: não carregar a coluna `content`, que guarda o arquivo em `LargeBinary` e é `deferred` no model justamente por isso. |
| A6 | `GET /investments/snapshots` | Leitura direta de `PortfolioSnapshot` (`total_value`, `net_cash_flow`, `captured_at`) em ordem crescente. A tabela já é alimentada por `refresh_user_quotes`. |
| A7 | `PATCH /auth/me` | Apenas `full_name`. Alterar e-mail muda a identidade de login e merece decisão própria. |
| A8 | `POST /auth/change-password` | Senha atual + nova, reusando `verify_password`/`hash_password` e o limite de 72 bytes UTF-8. **Consequência a registrar:** como o JWT é stateless e não há tabela de sessão, tokens emitidos antes da troca continuam válidos até expirar. Isso é contraintuitivo para o usuário e só se resolve junto com o item C1. |
| A9 | `DELETE /telegram/link` | Decisão menor embutida: apagar a linha de `telegram_tokens` (mais simples, e `criar_link_token` recria depois) ou apenas zerar `chat_id`/`link_token` preservando o histórico de consentimento. A segunda opção é melhor para trilha de auditoria de privacidade. |

### Grupo B — implementação moderada, sem migration

| # | Endpoint | Abordagem e ponto de atenção |
| --- | --- | --- |
| B1 | `PATCH /investments/movements/{id}` | Reusa exatamente o padrão que já existe em `create_movement` e `delete_movement`: trava o ativo com `_owned_asset(..., for_update=True)`, aplica as mudanças e roda `calculate_position` sobre o conjunto resultante, devolvendo 422 se a custódia ficar negativa. Precisa repetir as quantizações por campo do POST (`investments.py:173-179`). |
| B2 | `GET /investments/export` | Reusa o padrão de `export_csv`/`export_xlsx` de `spreadsheets.py`, inclusive a neutralização de textos que o Excel interpretaria como fórmula. Decisão de conteúdo: exportar posições consolidadas, movimentações, ou ambos em abas separadas. |
| B3 | Paginação em ativos e movimentações | Tecnicamente trivial, **porém muda a forma da resposta**: `list[AssetResponse]` viraria um envelope com `items`/`total`, quebrando o contrato já documentado no plano do front-end. Alternativa não destrutiva: aceitar `limit`/`offset` mantendo a lista pura, abrindo mão do total. |

### Grupo C — exigem decisão antes de qualquer código

#### C1 — Refresh token

Hoje o JWT dura 7 dias (`ACCESS_TOKEN_EXPIRE_MINUTES=10080`) e não há renovação nem revogação. Três caminhos:

| Opção | O que envolve | Trade-off |
| --- | --- | --- |
| (a) `POST /auth/refresh` simples | Troca um access token ainda válido por outro. Sem tabela, sem migration. | Não ajuda quem já expirou e estende a sessão indefinidamente enquanto o usuário estiver ativo. Não resolve A8. |
| (b) Refresh token opaco em tabela | Token de longa duração persistido, com rotação a cada uso e revogação. Exige migration e habilita logout de verdade. | O caminho correto para produção; resolve também a pendência do A8. Maior esforço. |
| (c) Não fazer | O front detecta `expires_at` e avisa antes de cair. | Zero custo no back-end; experiência pior, mas aceitável em MVP. |

Recomendação: **(b)** se a aplicação vai para produção com usuários reais; **(c)** enquanto for uso próprio. A opção (a) entrega a aparência de sessão renovável sem as garantias de segurança que a justificariam.

Qualquer variável nova de configuração precisa ser adicionada ao `AMBIENTE_DE_TESTE` do `conftest`.

#### C2 — Reset de senha por e-mail

**Único item não entregável com o que existe hoje.** Depende de:

1. escolha de provedor (Resend, SendGrid, SMTP do próprio Supabase);
2. chave de API nova em `Settings` e no `.env`;
3. template de mensagem;
4. tabela de token de uso único com expiração;
5. rate limit, para o endpoint não virar vetor de spam ou de enumeração de contas.

Enquanto isso não for decidido, a troca de senha autenticada (A8) cobre o caso do usuário que lembra a senha atual. Fica descoberto apenas o caso de senha esquecida.

---

## 3. Quadro-resumo

| Situação | Quantidade | Itens |
| --- | --- | --- |
| Direto, sem migration | 9 | A1–A9 |
| Moderado, sem migration | 3 | B1–B3 |
| Depende de decisão de arquitetura | 1 | C1 (refresh token) |
| Bloqueado por infraestrutura ausente | 1 | C2 (reset de senha por e-mail) |

**12 das 14 lacunas não exigem nenhuma migration do Alembic.** A única que exigiria é o refresh token na modalidade (b).

---

## 4. Ordem de execução sugerida, quando houver decisão

1. **A1, A2, A3, A6** — são os que destravam os gráficos e filtros das fases 1 a 3 do plano do dashboard. Maior retorno por esforço.
2. **A4, A5, A7, A8, A9** — completam a experiência de listagem e de configurações da conta.
3. **B1, B2** — qualidade de vida no módulo de investimentos; B1 elimina o fluxo de "excluir e recriar" para corrigir um lançamento.
4. **B3 e C1** — dependem das decisões de contrato e de arquitetura registradas acima.
5. **C2** — depois da escolha de provedor de e-mail.

---

## 5. Pendências que aguardam decisão

- [ ] Escopo a implementar (grupo A, A+B, ou apenas o subconjunto de gráficos).
- [ ] C1: estratégia de sessão — (a), (b) ou (c).
- [ ] B3: aceitar a mudança de contrato para envelope paginado em ativos/movimentações?
- [ ] A9: apagar a linha do vínculo do Telegram ou preservar o histórico de consentimento?
- [ ] B2: a exportação da carteira leva posições, movimentações ou ambas?
- [ ] C2: haverá provedor de e-mail no projeto?
- [ ] Introduzir testes de integração com banco, dado que a suíte atual não cobre comportamento de SQL?

---

## 6. Arquivos consultados

- `backend/tests/conftest.py` (isolamento da suíte, guard de `Settings`)
- `backend/tests/test_web_api_foundation.py` (padrão de teste existente)
- `backend/requirements.txt` (ausência de dependência de e-mail; Postgres via `psycopg2`)
- `backend/app/api/v1/dashboard.py`, `transactions.py`, `investments.py`, `auth.py`, `telegram.py`
- `backend/app/models/import_job.py` (coluna `content` deferida), `investment.py`
- `backend/app/services/spreadsheets.py`, `quote_refresh.py`
- `backend/app/core/config.py`, `security.py`
- `resume/05-plano-funcionalidades-dashboard-frontend.md`
