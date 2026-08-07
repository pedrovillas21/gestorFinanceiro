# Como rodar o bot do Telegram — passo a passo

Runbook operacional do **@financeiroPrivadoGestor_bot**: da máquina zerada até o primeiro áudio virar transação no banco.

> Os comandos estão em **Git Bash** (`MINGW64`), que é o shell usado neste projeto.
> Eles chamam o Python do venv direto (`./venv/Scripts/python.exe`) — assim funcionam
> mesmo em terminal novo, sem depender de ativar o ambiente.
>
> Se preferir ativar o venv: `source venv/Scripts/activate` (no Git Bash é `source` e barra `/`;
> `.\venv\Scripts\Activate.ps1` só funciona no PowerShell).

---

## Parte 1 — Preparação (uma vez só)

Estes passos já estão feitos. Estão aqui para reconstruir o ambiente em outra máquina ou depois de uma formatação.

### 1.1. Ambiente Python

```bash
cd ~/Documents/códigos/gestorFinanceiro/backend
python -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements.txt
```

### 1.2. Túnel HTTPS

```powershell
winget install --id Cloudflare.cloudflared
```

Instala em `C:\Program Files (x86)\cloudflared\cloudflared.exe` e adiciona ao `PATH` da máquina.

> **Se `cloudflared: command not found` depois de instalar:** o terminal só lê o `PATH` ao abrir.
> Dentro do VS Code é pior — ele congela as variáveis de ambiente quando é iniciado e repassa
> essa cópia a todo terminal filho, então **fechar a aba não basta: feche o VS Code inteiro**.
> Alternativa sem reiniciar nada:
> ```bash
> alias cloudflared="/c/Program Files (x86)/cloudflared/cloudflared.exe"
> ```

### 1.3. Variáveis de ambiente

Copie `backend/.env.example` para `backend/.env` e preencha. As que o bot exige:

| Variável | Onde obter |
|---|---|
| `DATABASE_URL` | Supabase → Project Settings → Database → Connection String (URI) |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com) |
| `TELEGRAM_BOT_TOKEN` | @BotFather, ao criar o bot com `/newbot` |
| `TELEGRAM_BOT_USERNAME` | Username do bot, **sem `@`** — sem isso o Deep Link não monta |
| `TELEGRAM_WEBHOOK_SECRET` | Gere com `python -c "import secrets;print(secrets.token_urlsafe(48))"` |

### 1.4. Criar as tabelas no Supabase

```bash
./venv/Scripts/python.exe -m alembic revision --autogenerate -m "create_initial_multi_tenant_tables"
./venv/Scripts/python.exe -m alembic upgrade head
```

Depois da primeira vez, o `lifespan` do FastAPI aplica migrations novas sozinho na subida.

> **Atenção a um falso positivo:** com `alembic/versions/` vazio, o `upgrade head` imprime
> "Migrations aplicadas com sucesso!" sem criar tabela nenhuma — ele conecta, não acha revisão
> e termina. Confira de verdade:
> ```bash
> ./venv/Scripts/python.exe -c "
> from sqlalchemy import inspect; from app.database import engine
> print(inspect(engine).get_table_names(schema='public'))"
> ```
> Esperado: `['alembic_version', 'telegram_tokens', 'transactions', 'users']`.

### 1.5. Criar seu usuário

Hoje existe `POST /api/v1/auth/register`; para o fluxo administrativo por terminal, use o script:

```bash
./venv/Scripts/python.exe scripts/criar_usuario.py --email voce@exemplo.com --nome "Seu Nome"
```

A senha é pedida na hora, sem ecoar na tela e sem entrar no histórico do shell. Mínimo de 8 caracteres. Para automatizar, existe `--senha`, mas aí ela fica no histórico.

---

## Parte 2 — Subir o bot (toda vez)

São três terminais. Os dois primeiros ficam abertos enquanto o bot estiver no ar.

### Terminal 1 — API

```bash
cd ~/Documents/códigos/gestorFinanceiro/backend
./venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

Espere ver `Application startup complete`. O `--reload` recarrega o código a cada alteração.

### Terminal 2 — Túnel HTTPS

```bash
cloudflared tunnel --url http://localhost:8000
```

Ele imprime um quadro com a URL no meio:

```
+--------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at:       |
|  https://dance-dependent-fame-thanksgiving.trycloudflare.com  |
+--------------------------------------------------------+
```

**Copie essa URL.** Não feche o terminal — fechar derruba o túnel.

Antes de envolver o Telegram, valide o caminho HTTPS sozinho abrindo no navegador:

```
https://SUA-URL.trycloudflare.com/health
```

Tem que responder `{"status":"ok"}`. Se falhar aqui, não adianta seguir.

### Terminal 3 — Registrar no Telegram

```bash
cd ~/Documents/códigos/gestorFinanceiro/backend
./venv/Scripts/python.exe scripts/setup_telegram_bot.py --url https://SUA-URL.trycloudflare.com
```

O script completa o caminho `/api/v1/telegram/webhook` sozinho e faz, numa tacada: `setWebhook`, `setMyCommands` (menu com start/ajuda/saldo) e `setMyDescription`. Ele recusa URL `http://`, porque o Telegram exige HTTPS.

Para conferir o que o Telegram enxerga:

```bash
./venv/Scripts/python.exe scripts/setup_telegram_bot.py --somente-info
```

Saudável é: `url` preenchida, `pending_update_count: 0`, `last_error_message` vazio.

---

## Parte 3 — Conectar sua conta ao bot (uma vez por conta)

```bash
./venv/Scripts/python.exe scripts/gerar_link_telegram.py --email voce@exemplo.com
```

Saída:

```
Usuário: voce@exemplo.com
Válido por: 30 minutos
Token (32 chars): vXqNjuyU...

COPIE a linha abaixo inteira (não clique — link quebrado no terminal trunca o token):

https://t.me/financeiroPrivadoGestor_bot?start=vXqNjuyU...
```

**Copie com o mouse, não clique.** O link tem ~89 caracteres e quebra em duas linhas em terminal estreito; clicar num link quebrado abre só o primeiro pedaço e o token chega truncado. Cole na barra de busca do Telegram ou no navegador.

Ao abrir, toque em **Iniciar**. A resposta esperada é `✅ Conta conectada`.

Duas regras do token: vale **30 minutos** e é de **uso único**. Cada execução do script invalida o link gerado antes — se gerar dois e clicar no primeiro, ele falha mesmo dentro do prazo.

---

## Parte 4 — Usar

Mande **áudio** ou **texto** no chat:

- *"gastei quarenta e dois e noventa no mercado no débito"*
- *"recebi 3500 de salário hoje"*
- *"paguei 120 de energia no pix"*

O bot responde com a transação registrada: tipo, descrição, valor em BRL, categoria e forma de pagamento. Se a IA não identificar um lançamento claro, ela diz o que enviar em vez de inventar valor.

Comandos: `/saldo` (receitas, despesas e saldo do mês), `/ajuda`, `/start`.

---

## Rotina do dia a dia

Com tudo já configurado, reabrir o bot é:

1. Terminal 1: `uvicorn`
2. Terminal 2: `cloudflared tunnel --url http://localhost:8000`
3. Terminal 3: `setup_telegram_bot.py --url <URL NOVA>` ← **não pule**

O passo 3 é obrigatório **toda vez**, porque a URL do quick tunnel muda a cada execução do `cloudflared`. O Telegram continua entregando no endereço antigo, que já não existe, e o bot parece quebrado sem estar.

O vínculo da sua conta (Parte 3) **não** precisa ser refeito — fica gravado no banco.

### Onde isso funciona

Você pode estar em qualquer lugar: rede móvel, outra cidade, outro país. O túnel é uma conexão de dentro para fora, então seu celular nunca tenta alcançar sua rede. A máquina também não precisa do wifi de casa — qualquer internet serve.

O que o bot exige é só: máquina ligada, sem suspender, com os dois processos vivos.

### Mensagens enviadas com o bot fora do ar

O Telegram guarda os updates por até 24h e fica reenviando. Mas o `setup_telegram_bot.py` registra o webhook com `drop_pending_updates: True` — ou seja, **ao reconectar, essa fila é descartada**.

É deliberado: sem isso, abrir o túnel de manhã despejaria todos os áudios da noite anterior de uma vez, virando transações datadas de hoje. Se preferir o contrário, é só mudar esse parâmetro em `scripts/setup_telegram_bot.py`.

---

## Quando algo dá errado

| Sintoma | Causa | Correção |
|---|---|---|
| `bash: .venvScriptsActivate.ps1: command not found` | Sintaxe do PowerShell no Git Bash | `source venv/Scripts/activate` (barra `/`, não `\`) |
| `cloudflared: command not found` (recém-instalado) | `PATH` congelado no terminal/VS Code | Feche o **VS Code inteiro** e reabra, ou use o `alias` da seção 1.2 |
| `cloudflare: command not found` | Falta o "d" | O binário é `cloudflared`, de *daemon* |
| Erro 502 na URL do túnel | Túnel de pé, API não | Suba o `uvicorn` (Terminal 1) |
| "Migrations aplicadas com sucesso" mas sem tabelas | `alembic/versions/` vazio | Rode o `revision --autogenerate` (seção 1.4) |
| Bot mudo, sem erro em lugar nenhum | URL do túnel mudou | Rode o `setup_telegram_bot.py` com a URL nova |
| `❌ link inválido ou expirou` | Token truncado, rotacionado ou vencido | Veja o log do uvicorn (abaixo) |
| `🔒 Não encontrei uma conta conectada` | `/start` sem token, conta não vinculada | Refaça a Parte 3 |
| Bot não responde nada e o log fica em silêncio | Secret do webhook divergente | O log mostra `Webhook recebido com secret token inválido`; reexecute o setup |

### Diagnóstico do vínculo

Quando um Deep Link é recusado, o log do uvicorn diz exatamente o motivo:

```
Vínculo recusado no chat 6543845024: token de 18 chars, encontrado=False, expirado=False
```

Como ler:

- **menos de 32 chars** → o link foi truncado no caminho (clicou em vez de copiar)
- **`encontrado=False` com 32 chars** → link antigo; uma execução posterior do script rotacionou o token
- **`expirado=True`** → passou dos 30 minutos; gere outro

### Inspecionar o banco

```bash
./venv/Scripts/python.exe -c "
from sqlalchemy import select
from app.database import SessionLocal
from app.models.transaction import Transaction
from app.models.telegram_token import TelegramToken
db = SessionLocal()
v = db.scalars(select(TelegramToken)).first()
print('vínculo:', v.chat_id if v else '(nenhum)')
for x in db.scalars(select(Transaction).order_by(Transaction.occurred_at)).all():
    print(f'[{x.type}] {x.description} | R\$ {x.amount} | {x.category} | {x.payment_method}')
db.close()"
```

---

## Mapa dos arquivos

| Caminho | Papel |
|---|---|
| [`app/api/v1/telegram.py`](../backend/app/api/v1/telegram.py) | Endpoint do webhook e validação do header secreto |
| [`app/services/telegram_bot.py`](../backend/app/services/telegram_bot.py) | Comandos, vínculo e persistência |
| [`app/services/gemini.py`](../backend/app/services/gemini.py) | Cascata do Gemini e o prompt de extração |
| [`app/services/telegram_client.py`](../backend/app/services/telegram_client.py) | Chamadas à Bot API |
| [`scripts/setup_telegram_bot.py`](../backend/scripts/setup_telegram_bot.py) | Registra webhook, comandos e descrição |
| [`scripts/criar_usuario.py`](../backend/scripts/criar_usuario.py) | Cria usuário (não há endpoint de cadastro ainda) |
| [`scripts/gerar_link_telegram.py`](../backend/scripts/gerar_link_telegram.py) | Gera o Deep Link de vínculo |

Para ajustar como a IA interpreta as mensagens — categorias aceitas, formas de pagamento, tom da resposta — o lugar é a constante `PROMPT` em [`app/services/gemini.py`](../backend/app/services/gemini.py).
