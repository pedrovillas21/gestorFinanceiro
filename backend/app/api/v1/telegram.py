"""Endpoint de webhook do Telegram (seção 3.1 do guia)."""
import logging
import secrets

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.config import settings
from app.core.privacy import PrivacyPolicy, get_privacy_policy
from app.models.telegram_token import TelegramToken
from app.schemas.telegram import (
    PrivacyPolicyResponse,
    TelegramLinkRequest,
    TelegramLinkResponse,
    TelegramLinkStatus,
    TelegramUpdate,
)
from app.services.telegram_bot import criar_link_token, montar_deep_link, processar_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


def _published_policy(version: str) -> PrivacyPolicy:
    try:
        return get_privacy_policy(version)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A política de privacidade configurada ainda não foi publicada",
        ) from exc


def _policy_response(request: Request, policy: PrivacyPolicy) -> PrivacyPolicyResponse:
    return PrivacyPolicyResponse(
        version=policy.version,
        title=policy.title,
        published_at=policy.published_at,
        content=policy.content,
        content_sha256=policy.content_sha256,
        privacy_policy_url=str(
            request.url_for("telegram_privacy_policy_version", version=policy.version)
        ),
    )


@router.get("/privacy-policy", response_model=PrivacyPolicyResponse)
def current_telegram_privacy_policy(request: Request) -> PrivacyPolicyResponse:
    """Publica o aviso vigente antes de qualquer coleta de consentimento."""
    return _policy_response(request, _published_policy(settings.PRIVACY_POLICY_VERSION))


@router.get(
    "/privacy-policy/{version}",
    response_model=PrivacyPolicyResponse,
    name="telegram_privacy_policy_version",
)
def telegram_privacy_policy_version(
    version: str, request: Request
) -> PrivacyPolicyResponse:
    """Mantém cada aviso publicado acessível por uma URL estável e versionada."""
    try:
        policy = get_privacy_policy(version)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Versão da política de privacidade não encontrada",
        ) from exc
    return _policy_response(request, policy)


@router.post("/link", response_model=TelegramLinkResponse)
def create_telegram_link(
    payload: TelegramLinkRequest,
    request: Request,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> TelegramLinkResponse:
    """Gera o Deep Link somente depois do aceite versionado de privacidade."""
    if not payload.consent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O consentimento é obrigatório para usar o canal Telegram",
        )
    policy = _published_policy(settings.PRIVACY_POLICY_VERSION)
    if payload.consent_version != policy.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A versão aceita não é a política vigente; leia a política atual "
                "antes de confirmar"
            ),
        )
    token = criar_link_token(
        db, current_user.id, consent_version=payload.consent_version
    )
    link = db.scalar(
        select(TelegramToken).where(TelegramToken.user_id == current_user.id)
    )
    return TelegramLinkResponse(
        deep_link=montar_deep_link(token),
        expires_at=link.link_token_expires_at,
        consent_version=link.privacy_consent_version,
        privacy_policy_url=str(
            request.url_for("telegram_privacy_policy_version", version=policy.version)
        ),
    )


@router.get("/link", response_model=TelegramLinkStatus)
def telegram_link_status(
    current_user: CurrentUser, db: DatabaseSession
) -> TelegramLinkStatus:
    link = db.scalar(
        select(TelegramToken).where(TelegramToken.user_id == current_user.id)
    )
    return TelegramLinkStatus(
        linked=bool(link and link.chat_id),
        linked_at=link.linked_at if link else None,
        consent_version=link.privacy_consent_version if link else None,
        consented_at=link.privacy_consented_at if link else None,
    )


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
        logger.debug(
            "Update %s ignorado por não corresponder ao schema", payload.get("update_id")
        )
        return {"ok": True}

    background_tasks.add_task(processar_update, update)
    return {"ok": True}
