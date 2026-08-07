# Relatório 02 — Investimentos, cotações e simulador

Data: 07/08/2026

## O que foi feito

- Cadastro de ativos em BRL e movimentações de compra, venda, proventos, JCP, rendimentos de FII, desdobramento, grupamento, bonificação, subscrição, cisão e incorporação.
- Persistência de quantidade, preço unitário, custos, valores bruto/líquido, modalidade swing/day trade e campos de câmbio necessários para evolução futura.
- Cálculo com `Decimal` de preço médio ponderado, ganho realizado, resultado não realizado, proventos e retorno sobre custo.
- Cálculo de TWR a partir de snapshots completos e MWR/XIRR por bisseção, retornando `null` quando faltam dados ou não há convergência confiável.
- Regra de não anualizar períodos menores que 30 dias.
- Histórico de cotações, com preço, moeda, provedor e horário da coleta; o endpoint da carteira sempre devolve o timestamp e marca preço vencido.
- Cliente assíncrono da API v2 da brapi, com timeout explícito e autenticação via header Bearer.
- Fallback operacional: se o provedor falha, nenhuma cotação em cache é apagada e a leitura da carteira continua usando o último preço persistido.
- Script `scripts/refresh_market_quotes.py` para execução periódica por cron/agendador da hospedagem.
- Simulador de juros compostos com taxa mensal ou anual, conversão anual→mensal composta e série mensal de capital investido, juros e valor total.
- Migration com RLS para ativos, movimentações, histórico de preços e snapshots.

## Para que serve

O futuro dashboard pode cadastrar a carteira, mostrar posição e rentabilidade com indicadores corretamente nomeados, exibir a idade da cotação e alimentar gráficos do simulador. O histórico e os snapshots evitam inventar TWR sem avaliações suficientes; enquanto isso, a API devolve ausência explícita em vez de um número enganoso.

## Validação executada

- 42 testes aprovados.
- Casos cobertos: custo médio com múltiplas compras, venda sem alteração do preço médio, custos, proventos bruto/líquido, desdobramento, venda acima da custódia, TWR, XIRR, período mínimo e conversão composta de taxa.
- Contrato da cotação conferido contra a documentação oficial atual da brapi (`/api/v2/stocks/quote`, `results[].data.regularMarketPrice`).

## Pendências e melhorias futuras

- Configurar o script periódico na plataforma de hospedagem; ele foi entregue, mas nenhum agendamento externo foi criado por depender da infraestrutura escolhida.
- Exercitar a integração com um token real da brapi em ambiente de desenvolvimento. Os testes locais não consomem APIs externas.
- O MVP permanece em BRL conforme o plano. Os campos de câmbio já existem, mas consolidar ativos estrangeiros requer também cotação cambial corrente.
- Cisão e incorporação ficam registradas para lançamento manual assistido; não há rateio automático porque a regra depende do comunicado específico da empresa.
- TWR só aparece após duas ou mais atualizações completas da carteira. Sem preço para uma posição aberta, o total e os indicadores dependentes ficam `null` de forma intencional.
