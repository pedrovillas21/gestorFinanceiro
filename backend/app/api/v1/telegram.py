"""Endpoint de webhook do Telegram (seção 3.1 do guia)."""
import logging
import secrets

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.telegram import TelegramUpdate
from app.services.telegram_bot import processar_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    secret_token: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> dict[str, bool]:
    """Recebe os updates do Telegram.

    Responde 200 imediatamente e processa a mensagem em background — o Telegram
    reenvia o update caso a resposta demore, e a IA pode levar alguns segundos.
    """
    if not secrets.compare_digest(secret_token or "", settings.TELEGRAM_WEBHOOK_SECRET):
        logger.warning("Webhook recebido com secret token inválido")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Assinatura inválida")

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Corpo não é JSON"
        ) from exc

    try:
        update = TelegramUpdate.model_validate(payload)
    except ValidationError:
        # Tipos de update que não mapeamos (callback_query, my_chat_member, ...) são ignorados.
        logger.debug("Update ignorado por não corresponder ao schema: %s", payload)
        return {"ok": True}

    background_tasks.add_task(processar_update, update)
    return {"ok": True}
