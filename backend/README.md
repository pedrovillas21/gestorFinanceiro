# Back-end — Gestor Financeiro com IA

API FastAPI do gestor financeiro. O contrato interativo fica em `/docs` ao executar o servidor.

## Executar

```powershell
Copy-Item .env.example .env
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

O startup também executa `alembic upgrade head`. Use uma `DATABASE_URL` do papel de backend; as tabelas pessoais têm RLS deny-by-default para acesso direto via PostgREST.

## Áreas da API

- `/api/v1/auth`: cadastro, login, usuário atual e exclusão da conta.
- `/api/v1/transactions`: CRUD, filtros, paginação, CSV/XLSX e consulta de jobs de importação.
- `/api/v1/dashboard/summary`: receitas, despesas, saldo e categorias por período.
- `/api/v1/telegram`: Deep Link com consentimento e webhook autenticado.
- `/api/v1/investments`: ativos, movimentações, carteira, indicadores e atualização de cotações.
- `/api/v1/calculators/compound-interest`: simulação mensal de juros compostos.

Envie o JWT em `Authorization: Bearer <token>`. Dinheiro, quantidades, preços e taxas são strings decimais no JSON.

## Telegram — gerar o Deep Link

Consulte `GET /api/v1/telegram/privacy-policy` antes de qualquer aceite: ele devolve o
texto oficial, o hash e a URL imutável da versão, sem exigir autenticação. Pela API, o
aceite vai em `{"consent": true, "consent_version": "2026-08-10"}` para
`POST /api/v1/telegram/link`. O servidor recusa versões diferentes da política vigente e
só registra versões que tenham conteúdo publicado.

O script administrativo exige aceite explícito e **não tem versão padrão**: os dois
argumentos abaixo são obrigatórios. A versão precisa ser idêntica à
`PRIVACY_POLICY_VERSION` em vigor (hoje `2026-08-10`).

Git Bash / MINGW64:

```bash
./venv/Scripts/python.exe scripts/gerar_link_telegram.py \
  --email voce@exemplo.com \
  --consent-version 2026-08-10 \
  --confirm-privacy-consent
```

PowerShell:

```powershell
.\venv\Scripts\python.exe scripts\gerar_link_telegram.py `
  --email voce@exemplo.com `
  --consent-version 2026-08-10 `
  --confirm-privacy-consent
```

Copie a URL inteira em vez de clicar: o token é longo e o terminal costuma truncá-lo na
quebra de linha. Cada execução invalida o link gerado antes.

Vínculos aceitos sob uma versão anterior deixam de valer assim que
`PRIVACY_POLICY_VERSION` muda — o bot passa a pedir uma nova conexão, e é preciso rodar
o script de novo. Publicar uma política nova, portanto, desconecta todo mundo por
construção.

## Planilhas

CSV e XLSX aceitam os cabeçalhos:

```text
data;tipo;descricao;valor;categoria;metodo_pagamento
2026-08-07;despesa;Mercado;42,90;Alimentação;pix
```

Arquivos até 5 MB são processados no request, que roda em thread pool. Acima disso, a resposta é um job; consulte `GET /api/v1/transactions/imports/{job_id}`.

## Cotações

`POST /api/v1/investments/quotes/refresh` atualiza a carteira do usuário autenticado. Para atualização periódica de todas as carteiras:

```powershell
.\venv\Scripts\python.exe scripts\refresh_market_quotes.py
```

Agende esse comando no cron/Task Scheduler da hospedagem. `BRAPI_TOKEN` é enviado somente no header Bearer. Falhas do provedor não apagam o último preço; a resposta da carteira inclui `collected_at` e `stale`.

## Testes

```powershell
.\venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
```

Os testes substituem todas as credenciais, não chamam serviços externos e usam SQLite em memória para o fluxo HTTP de autenticação/transações.
