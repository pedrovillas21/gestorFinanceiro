# Status de Implementação — Bot do Telegram com IA

Resumo do que já está pronto no código, do que ainda pode ser feito por mim (Claude) e do que só você consegue fazer, com base no guia [`plan/Guia de Criacao e Configuracao - Bot do Telegram com IA.md`](../plan/Guia%20de%20Criacao%20e%20Configuracao%20-%20Bot%20do%20Telegram%20com%20IA.md).

> Verificação feita em 05/08/2026, direto no código do repositório (`backend/app`).

---

## ✅ O que já está feito no repositório

| Item | Onde está | Observação |
|---|---|---|
| Modelo de vínculo `chat_id ↔ usuário` | [`backend/app/models/telegram_token.py`](../backend/app/models/telegram_token.py) | Tabela `telegram_tokens` com `user_id` (FK) e `chat_id` únicos — é exatamente o que a seção 4.1 do guia pede para "verificar se existe usuário com aquele `telegram_chat_id`". |
| Variáveis de ambiente já mapeadas | [`backend/app/core/config.py`](../backend/app/core/config.py) e [`backend/.env.example`](../backend/.env.example) | `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN` e `TELEGRAM_WEBHOOK_SECRET` já existem como placeholders/settings, prontos para receber os valores reais. |
| Dependências Python do checklist (seção 5) | [`backend/requirements.txt`](../backend/requirements.txt) | `fastapi`, `httpx`, `python-dotenv`, `pydantic`, `sqlalchemy` ✅ já instalados. `google-genai` também já está no requirements (necessário para a "Cascata do Gemini"). |
| Base do FastAPI | [`backend/app/main.py`](../backend/app/main.py) | App já sobe e roda as migrations do Alembic automaticamente no startup. Falta só registrar as rotas do bot nela. |
| Modelos auxiliares que o fluxo do bot vai usar | [`backend/app/models/user.py`](../backend/app/models/user.py), [`backend/app/models/transaction.py`](../backend/app/models/transaction.py) | Já existem `User` e `Transaction` para persistir o resultado da IA (seção 4.2, passo 5). |

**Resumindo:** a base de dados e a configuração já estão prontas para o bot existir. O que falta é a parte "viva": o endpoint do webhook, a lógica de negócio e a integração com a API do Telegram/Gemini.

---

## 🤖 O que eu (Claude) ainda posso fazer — código, sem precisar dos seus segredos

Nada disso exige que você me entregue tokens reais para eu **escrever** o código (só para você **testar** depois):

1. **Endpoint `POST /api/v1/telegram/webhook`** no FastAPI (seção 3.1), incluindo validação do header `X-Telegram-Bot-Api-Secret-Token` contra `TELEGRAM_WEBHOOK_SECRET`.
2. **Lógica de autenticação por `chat_id`** (seção 4.1): consulta em `telegram_tokens`, e resposta com link de Deep Link quando o usuário não for encontrado.
3. **Fluxo de vínculo via Deep Link** (`/start <token>`) para conectar a conta Web ao `chat_id` do Telegram.
4. **Download do áudio `.ogg`** via API de arquivos do Telegram e envio para a "Cascata do Gemini" (`google-genai` já está instalado).
5. **Persistência da transação** extraída pela IA (tipo, valor, categoria, método de pagamento) e mensagem de confirmação de volta ao chat.
6. **Comandos `/ajuda` e `/saldo`** (lógica de negócio, resumo do mês).
7. **Script de setup automático via Bot API** — depois que você tiver o token, `setWebhook`, `setMyCommands` e `setMyDescription` **são chamadas HTTP comuns** (não precisam do app do BotFather), então posso escrever um script `httpx`/`requests` que configura tudo isso automaticamente assim que o token estiver no `.env`.

👉 Se quiser, no próximo passo eu já implemento os itens 1–6 (o webhook completo). Só peça.

---

## 🙋 O que só você consegue fazer (ações manuais, fora do meu alcance)

| # | Ação | Por quê só você pode fazer |
|---|---|---|
| 1 | Criar o bot no **@BotFather** (`/newbot`, nome, username) — seção 2.1 | Exige sua conta pessoal do Telegram; é uma interação dentro do app do Telegram. |
| 2 | Copiar o **HTTP API Token** gerado pelo BotFather | Só existe depois do passo 1, e é um segredo que só você deve manusear. |
| 3 | Obter a **`GEMINI_API_KEY`** no Google AI Studio | Requer login na sua conta Google e aceite dos termos da API. |
| 4 | Colar os valores reais no `backend/.env` (`TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`) | Eu posso editar o arquivo se você me passar os valores, mas não posso gerá-los — são credenciais vinculadas à sua conta. Se preferir, você mesmo cola direto no `.env` sem nunca me enviar o segredo. |
| 5 | Definir um `TELEGRAM_WEBHOOK_SECRET` forte | Posso gerar uma string aleatória segura para você, mas a decisão/posse final é sua (é um segredo de produção). |
| 6 | **Disponibilizar o backend em um domínio HTTPS válido em produção** (deploy + certificado SSL) — seção 3 e checklist item 4 | Decisão de infraestrutura/hosting (ex: Railway, Render, Fly.io, VPS próprio) que envolve contas externas, custos e escolha de provedor — não posso decidir nem provisionar isso por você. |
| 7 | Rodar o `POST /setWebhook` apontando para a URL pública real, depois que o deploy estiver no ar | O script eu posso escrever, mas ele só funciona depois que existe uma URL HTTPS pública de verdade respondendo — isso depende do passo 6 estar concluído. |
| 8 (dev local) | Se for testar localmente, subir um túnel (**Ngrok** ou **Cloudflare Tunnel**) apontando pro FastAPI local — seção 3 | Requer instalar/rodar uma ferramenta na sua máquina e criar conta no serviço de túnel, se aplicável. |

---

## 📋 Checklist do guia (seção 5) — situação atual

- [x] Pacotes Python instalados (`fastapi`, `httpx`, `python-dotenv`, `pydantic`, `sqlalchemy`)
- [ ] Conta no Telegram ativada e acesso ao @BotFather — **manual**
- [ ] Credencial `GEMINI_API_KEY` configurada com valor real — **manual** (variável já existe, falta o valor)
- [ ] Certificado SSL válido / HTTPS em produção — **manual** (depende de escolha de hospedagem)

---

## Próximo passo sugerido

1. Você faz os itens manuais 1–3 (BotFather + Gemini API Key) e me passa (ou cola direto no `.env`) os valores.
2. Enquanto isso, eu já posso adiantar e implementar o endpoint do webhook e a lógica de negócio (itens 1–6 da seção "O que eu ainda posso fazer"), deixando tudo pronto para testar assim que as credenciais existirem.
3. Quando tiver domínio/deploy definido, eu escrevo o script de `setWebhook` + `setMyCommands` + `setMyDescription`.
