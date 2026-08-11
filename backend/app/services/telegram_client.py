"""Cliente HTTP fino para a Bot API do Telegram (seções 3.1 e 4.2 do guia)."""
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"
TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# Limite de download de arquivos pela Bot API.
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


class TelegramAPIError(RuntimeError):
    """Erro retornado pela Bot API (campo `ok: false`) ou HTTP não-2xx."""


def _api_url(method: str) -> str:
    return f"{API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"


def _file_url(file_path: str) -> str:
    return f"{API_BASE}/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}"


async def call(method: str, payload: dict[str, Any] | None = None) -> Any:
    """Chama um método da Bot API e devolve o conteúdo de `result`."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(_api_url(method), json=payload or {})

    try:
        body = response.json()
    except ValueError as exc:  # resposta não-JSON (ex.: proxy/erro de rede)
        raise TelegramAPIError(f"{method}: resposta inválida ({response.status_code})") from exc

    if not body.get("ok"):
        raise TelegramAPIError(f"{method}: {body.get('description', 'erro desconhecido')}")

    return body.get("result")


async def send_message(
    chat_id: str | int,
    text: str,
    *,
    disable_preview: bool = True,
    reply_markup: dict[str, Any] | None = None,
) -> None:
    """Envia uma mensagem de texto para o chat.

    Tenta em Markdown; se o Telegram recusar a formatação (texto do usuário pode
    conter `*` ou `_` desbalanceados), reenvia como texto puro em vez de perder a resposta.
    """
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "link_preview_options": {"is_disabled": disable_preview},
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        await call("sendMessage", payload)
    except TelegramAPIError as exc:
        if "parse" not in str(exc).lower():
            raise
        logger.warning("Markdown recusado pelo Telegram, reenviando sem formatação: %s", exc)
        payload.pop("parse_mode")
        await call("sendMessage", payload)


async def send_chat_action(chat_id: str | int, action: str = "typing") -> None:
    """Mostra 'digitando...' enquanto a IA processa. Falha aqui nunca é fatal."""
    try:
        await call("sendChatAction", {"chat_id": chat_id, "action": action})
    except (TelegramAPIError, httpx.HTTPError):
        logger.debug("Falha ao enviar chat action para %s", chat_id, exc_info=True)


async def answer_callback_query(callback_query_id: str, text: str | None = None) -> None:
    payload: dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    await call("answerCallbackQuery", payload)


async def download_file(file_id: str) -> bytes:
    """Resolve o `file_id` via getFile e baixa o binário do arquivo."""
    file_info = await call("getFile", {"file_id": file_id})
    file_path = file_info.get("file_path")
    if not file_path:
        raise TelegramAPIError("getFile: resposta sem file_path")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(_file_url(file_path))
        response.raise_for_status()
        return response.content


# --- Métodos usados apenas pelo script de setup (scripts/setup_telegram_bot.py) ---


async def set_webhook(url: str, secret_token: str) -> Any:
    return await call(
        "setWebhook",
        {
            "url": url,
            "secret_token": secret_token,
            "allowed_updates": ["message", "edited_message", "callback_query"],
            "drop_pending_updates": True,
        },
    )


async def get_webhook_info() -> Any:
    return await call("getWebhookInfo")


async def set_my_commands(commands: list[dict[str, str]]) -> Any:
    return await call("setMyCommands", {"commands": commands})


async def set_my_description(description: str) -> Any:
    return await call("setMyDescription", {"description": description})


async def set_my_short_description(short_description: str) -> Any:
    return await call("setMyShortDescription", {"short_description": short_description})


async def get_me() -> Any:
    return await call("getMe")
