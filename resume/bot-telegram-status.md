# Status de Implementação — Bot do Telegram com IA

Situação do bot em relação ao guia [`plan/Guia de Criacao e Configuracao - Bot do Telegram com IA.md`](../plan/Guia%20de%20Criacao%20e%20Configuracao%20-%20Bot%20do%20Telegram%20com%20IA.md).

> **Atualizado em 05/08/2026.** O bot está funcionando ponta a ponta.
> Para rodar, veja o passo a passo em [`como-rodar-o-bot.md`](como-rodar-o-bot.md).

---

## ✅ Validado em produção real

Em 05/08/2026 o fluxo completo foi exercitado contra o Telegram, o Gemini e o Supabase de verdade — não em mock. Duas transações entraram no banco a partir de mensagens no chat:

| tipo | descrição | valor | categoria | pagamento | origem |
|---|---|---|---|---|---|
| despesa | Almoço | R$ 20,00 | Alimentação | crédito | telegram |
| despesa | Janta | R$ 50,00 | Alimentação | — | telegram |

Na segunda mensagem a forma de pagamento não foi citada e a IA devolveu nulo em vez de inventar — comportamento correto do prompt.

- **Bot:** @financeiroPrivadoGestor_bot (id `8638098255`)
- **Webhook:** registrado e sem erros (`pending_update_count: 0`, `last_error_message` vazio)
- **Banco:** migration `6ca4ec8a71fb` aplicada; tabelas `users`, `transactions`, `telegram_tokens` criadas no Supabase
- **Vínculo:** `chat_id` gravado, token de Deep Link consumido corretamente

---

## O que existe no código

| Componente | Arquivo | O que faz |
|---|---|---|
| Endpoint do webhook | [`app/api/v1/telegram.py`](../backend/app/api/v1/telegram.py) | `POST /api/v1/telegram/webhook`, valida `X-Telegram-Bot-Api-Secret-Token` com comparação constante-no-tempo e responde 200 na hora, processando em background |
| Schemas do Update | [`app/schemas/telegram.py`](../backend/app/schemas/telegram.py) | Subconjunto tipado do payload (`message`, `chat`, `voice`, `audio`), com `extra="ignore"` |
| Cliente da Bot API | [`app/services/telegram_client.py`](../backend/app/services/telegram_client.py) | `sendMessage` (com fallback sem Markdown), `sendChatAction`, `getFile` + download do `.ogg`, e os métodos de provisionamento |
| Cascata do Gemini | [`app/services/gemini.py`](../backend/app/services/gemini.py) | Áudio ou texto → JSON estruturado via `response_schema`; tenta `gemini-flash-latest` e cai para `gemini-2.5-flash` |
| Regras do bot | [`app/services/telegram_bot.py`](../backend/app/services/telegram_bot.py) | Autenticação por `chat_id`, `/start <token>`, `/ajuda`, `/saldo`, persistência e confirmação em BRL |
| Modelos | [`app/models/`](../backend/app/models/) | `TelegramToken` com `link_token`/`linked_at`; `Transaction` com `payment_method` e `source` |
| Provisionamento | [`scripts/setup_telegram_bot.py`](../backend/scripts/setup_telegram_bot.py) | `setWebhook` + `setMyCommands` + `setMyDescription` por HTTP, dispensando os cliques no @BotFather |
| Cadastro de usuário | [`scripts/criar_usuario.py`](../backend/scripts/criar_usuario.py) | Cria usuário com hash bcrypt, já que não há endpoint de registro |
| Deep Link | [`scripts/gerar_link_telegram.py`](../backend/scripts/gerar_link_telegram.py) | Gera o token de vínculo e imprime a URL `t.me/<bot>?start=<token>` |

### Fluxo implementado

1. Telegram chama o webhook com o header secreto → validado contra `TELEGRAM_WEBHOOK_SECRET`.
2. O update é validado pelo Pydantic e vai para uma *background task*; o `{"ok": true}` sai imediatamente, para o Telegram não reenviar o update enquanto a IA processa.
3. Busca em `telegram_tokens` pelo `chat_id`. Não encontrado → convite para conectar a conta. `/start <token>` → valida (uso único + 30 min), grava o `chat_id` e confirma.
4. Áudio → `getFile` → download do `.ogg` → Cascata do Gemini. Texto → direto para a Cascata.
5. Não sendo um lançamento claro, o bot explica o que enviar em vez de inventar valor.
6. Sendo, grava em `transactions` com o `user_id` do vínculo e responde com os dados formatados.

---

## 📋 Checklist do guia (seção 5)

- [x] Pacotes Python instalados (`fastapi`, `httpx`, `python-dotenv`, `pydantic`, `sqlalchemy`)
- [x] Conta no Telegram e bot criado no @BotFather
- [x] `GEMINI_API_KEY` configurada e exercitada com áudio real
- [x] Endpoint de webhook, autenticação por `chat_id`, Deep Link, áudio→IA, persistência e comandos
- [x] Provisionamento automatizado (`setWebhook` / `setMyCommands` / `setMyDescription`)
- [x] HTTPS válido — via túnel Cloudflare em desenvolvimento
- [ ] HTTPS em produção com hospedagem própria — **pendente, ver abaixo**

---

## O que falta

### Hospedagem
Hoje o bot só responde com a máquina ligada e os dois processos (uvicorn + cloudflared) rodando. Funciona de qualquer lugar do mundo — o túnel é uma conexão de dentro para fora, então o celular nunca precisa alcançar a rede de casa —, mas depende da máquina estar acesa.

Quando for hospedar, dois pontos pesam mais que domínio próprio:

- **Serviço que hiberna é ruim para webhook.** No cold start a requisição não chega ao app, o Telegram reenvia, e o mesmo áudio pode virar duas transações. Free tier do Render tem esse comportamento; Railway ou Fly com instância sempre ligada, não.
- **Domínio não é requisito técnico.** O Telegram aceita `*.onrender.com`, `*.fly.dev` e afins, porque exige apenas HTTPS com certificado válido. Domínio próprio é cosmético — e, quando comprar, compre separado do host.

### Idempotência do webhook
Guardar o `update_id` já processado e ignorar repetidos. Hoje o risco é teórico (o túnel não hiberna), mas vira concreto em hospedagem com cold start. É a proteção que torna seguro remover o `drop_pending_updates: True` do script de setup.

### Fora do escopo do guia, mas bloqueando o produto
- **Autenticação JWT da API Web** (`/auth/login`, `/auth/register`). É a ausência dela que faz o cadastro de usuário e a geração do Deep Link serem scripts de linha de comando em vez de rotas. Com ela, o `criar_link_token` vira um `POST /api/v1/telegram/link-token` de poucas linhas.
- **Tela `conectar-telegram`** no front-end Next.js, consumindo essa rota — hoje o `WEB_APP_URL` apontado nas mensagens do bot não existe.
- **CRUD de transações** na API Web e o dashboard.
