"""Configura o bot na Bot API: setWebhook + setMyCommands + setMyDescription.

Tudo o que a seção 2.2 do guia pede via @BotFather também é feito por chamada HTTP
comum — então este script substitui os cliques no app do Telegram.

Pré-requisitos no `backend/.env`:
    TELEGRAM_BOT_TOKEN=...        (obtido no @BotFather)
    TELEGRAM_WEBHOOK_SECRET=...   (string aleatória forte)
    TELEGRAM_WEBHOOK_URL=https://seu-dominio/api/v1/telegram/webhook

Uso (com o venv ativado, a partir de backend/):
    python scripts/setup_telegram_bot.py
    python scripts/setup_telegram_bot.py --url https://abc.trycloudflare.com
    python scripts/setup_telegram_bot.py --somente-info
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.services import telegram_client  # noqa: E402

WEBHOOK_PATH = "/api/v1/telegram/webhook"

DESCRICAO = (
    "Seu assistente financeiro pessoal com IA. "
    "Envie áudios ou textos para gerenciar suas finanças."
)

DESCRICAO_CURTA = "Gestor financeiro com IA por áudio e texto."

COMANDOS = [
    {"command": "start", "description": "Conectar ou autenticar sua conta Web via Deep Link"},
    {
        "command": "ajuda",
        "description": "Instruções de como registrar receitas e despesas por áudio ou texto",
    },
    {"command": "saldo", "description": "Exibir resumo do saldo e despesas do mês atual"},
]


def resolver_url(url_cli: str | None) -> str:
    """Aceita a URL completa do webhook ou apenas a base pública."""
    url = url_cli or settings.TELEGRAM_WEBHOOK_URL
    if not url:
        raise SystemExit(
            "Defina TELEGRAM_WEBHOOK_URL no .env ou passe --url https://seu-dominio"
        )

    url = url.rstrip("/")
    if not url.startswith("https://"):
        raise SystemExit(f"O Telegram exige HTTPS no webhook. Recebido: {url}")
    if not url.endswith(WEBHOOK_PATH):
        url += WEBHOOK_PATH
    return url


async def main(url_cli: str | None, somente_info: bool) -> None:
    me = await telegram_client.get_me()
    print(f"Bot autenticado: @{me['username']} ({me['first_name']})")

    if somente_info:
        info = await telegram_client.get_webhook_info()
        for chave, valor in info.items():
            print(f"  {chave}: {valor}")
        return

    url = resolver_url(url_cli)

    await telegram_client.set_webhook(url, settings.TELEGRAM_WEBHOOK_SECRET)
    print(f"✅ setWebhook -> {url}")

    await telegram_client.set_my_commands(COMANDOS)
    print("✅ setMyCommands -> start, ajuda, saldo")

    await telegram_client.set_my_description(DESCRICAO)
    await telegram_client.set_my_short_description(DESCRICAO_CURTA)
    print("✅ setMyDescription / setMyShortDescription")

    info = await telegram_client.get_webhook_info()
    pendentes = info.get("pending_update_count", 0)
    ultimo_erro = info.get("last_error_message")
    print(f"\ngetWebhookInfo: url={info.get('url')} pendentes={pendentes}")
    if ultimo_erro:
        print(f"⚠️ último erro reportado pelo Telegram: {ultimo_erro}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configura o webhook e o menu do bot.")
    parser.add_argument("--url", help="URL pública HTTPS (base ou já com o caminho do webhook)")
    parser.add_argument(
        "--somente-info", action="store_true", help="Apenas consulta o getWebhookInfo atual"
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(args.url, args.somente_info))
    except telegram_client.TelegramAPIError as exc:
        raise SystemExit(f"❌ Bot API recusou a chamada: {exc}") from exc
