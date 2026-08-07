# Relatório 01 — Fundação, autenticação e gestão financeira

Data: 07/08/2026

## O que foi feito

- API JWT com cadastro, login, consulta do usuário autenticado e exclusão da conta.
- Proteção Bearer e isolamento de todas as consultas por `user_id`.
- CRUD de transações com filtros, paginação, busca e data efetiva (`occurred_at`).
- Resumo de receitas, despesas, saldo e despesas agrupadas por categoria.
- Importação e exportação em CSV/XLSX. Arquivos acima de 5 MB viram jobs em background consultáveis pela API.
- Representação monetária com `Decimal`, conversão segura e `ROUND_HALF_UP`; valores saem como string no JSON.
- Consentimento versionado antes da geração do Deep Link do Telegram.
- Idempotência dos updates do Telegram e execução do fluxo do bot em thread pool, evitando bloquear o event loop da API com SQLAlchemy síncrono.
- Migration para data efetiva, consentimento, jobs de importação, idempotência e índices de consulta.
- CORS configurável e caminho absoluto para o `alembic.ini`.

## Para que serve

Este marco transforma o bot já funcional em um back-end utilizável pelo futuro dashboard. O front-end poderá autenticar usuários, gerenciar lançamentos, montar os principais cards e gráficos, importar/exportar dados e conectar o Telegram com registro de consentimento. A separação entre `occurred_at` e `created_at` preserva a data financeira real sem perder auditoria.

## Validação executada

- Compilação dos módulos Python.
- 35 testes aprovados, incluindo contrato monetário, JWT/senha, CSV/XLSX e registro das rotas.
- A suíte não acessa credenciais ou serviços reais.

## Pendências e melhorias futuras

- Aplicar e validar a migration no PostgreSQL/Supabase de desenvolvimento antes do deploy. Ela não foi executada automaticamente durante os testes para não tocar dados externos.
- Adicionar testes de integração HTTP com um banco PostgreSQL efêmero; os testes atuais cobrem contratos e regras puras.
- Para operação em múltiplas instâncias, mover jobs de importação em memória para uma fila persistente (por exemplo, Celery/RQ/Arq). O registro do job já é persistente, mas os bytes do upload vivem no processo até o background terminar.
- Definir e publicar o texto oficial de privacidade; a API já persiste sua versão e timestamp.
