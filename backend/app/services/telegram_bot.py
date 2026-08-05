"""Regras de negócio do bot do Telegram (seção 4 do guia).

Fluxo: autenticação por `chat_id` -> comandos (/start, /ajuda, /saldo) ->
processamento de áudio/texto pela Cascata do Gemini -> persistência da transação.
"""
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal
from app.models.telegram_token import TelegramToken
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.telegram import TelegramMessage, TelegramUpdate
from app.services import gemini, telegram_client

logger = logging.getLogger(__name__)

TZ = ZoneInfo("America/Sao_Paulo")

TIPO_POR_EXTENSO = {"receita": "income", "despesa": "expense"}

MENSAGEM_AJUDA = (
    "*Como usar o Gestor Financeiro IA* 🤖\n\n"
    "Mande um *áudio* ou um *texto* descrevendo o que entrou ou saiu — a IA cuida do resto.\n\n"
    "Exemplos:\n"
    "• _“gastei 42 e noventa no mercado no débito”_\n"
    "• _“recebi 3500 de salário hoje”_\n"
    "• _“paguei 120 reais de energia no pix”_\n\n"
    "*Comandos*\n"
    "/saldo — resumo de receitas e despesas do mês\n"
    "/ajuda — esta mensagem\n"
    "/start — conectar sua conta da Web"
)


# --------------------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------------------


def formatar_brl(valor: Decimal | float) -> str:
    """Formata um número no padrão brasileiro: 1234.5 -> 'R$ 1.234,50'."""
    quantizado = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"R$ {quantizado:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _inicio_do_mes() -> datetime:
    """Primeiro instante do mês corrente no fuso de São Paulo, em UTC."""
    agora = datetime.now(TZ)
    return agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


def montar_deep_link(link_token: str) -> str:
    """Deep Link do Telegram que dispara `/start <link_token>` no bot."""
    username = (settings.TELEGRAM_BOT_USERNAME or "").lstrip("@")
    if not username:
        return f"(configure TELEGRAM_BOT_USERNAME no .env) token: {link_token}"
    return f"https://t.me/{username}?start={link_token}"


def criar_link_token(db: Session, user_id: uuid.UUID) -> str:
    """Gera (ou renova) o token de vínculo de um usuário para uso no Deep Link.

    Chamado pela aplicação Web / pelo script `scripts/gerar_link_telegram.py`.
    """
    vinculo = db.scalars(
        select(TelegramToken).where(TelegramToken.user_id == user_id)
    ).one_or_none()

    if vinculo is None:
        vinculo = TelegramToken(user_id=user_id)
        db.add(vinculo)

    vinculo.link_token = secrets.token_urlsafe(24)
    vinculo.link_token_expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.TELEGRAM_LINK_TOKEN_TTL_MINUTES
    )
    db.commit()
    return vinculo.link_token


def _buscar_vinculo(db: Session, chat_id: str) -> TelegramToken | None:
    return db.scalars(
        select(TelegramToken).where(TelegramToken.chat_id == chat_id)
    ).one_or_none()


# --------------------------------------------------------------------------------------
# Comandos
# --------------------------------------------------------------------------------------


async def _cmd_start(db: Session, chat_id: str, argumento: str | None) -> None:
    """`/start [token]` — conclui o vínculo do Deep Link (seção 4.1)."""
    if not argumento:
        if _buscar_vinculo(db, chat_id):
            await telegram_client.send_message(
                chat_id, "Sua conta já está conectada. ✅\n\n" + MENSAGEM_AJUDA
            )
        else:
            await _pedir_vinculo(chat_id)
        return

    agora = datetime.now(UTC)
    pendente = db.scalars(
        select(TelegramToken).where(TelegramToken.link_token == argumento)
    ).one_or_none()

    expirado = (
        pendente is not None
        and pendente.link_token_expires_at is not None
        and pendente.link_token_expires_at < agora
    )
    if pendente is None or expirado:
        # Sem isto, "token não bateu" e "token venceu" viram a mesma mensagem no log.
        logger.warning(
            "Vínculo recusado no chat %s: token de %d chars, encontrado=%s, expirado=%s",
            chat_id,
            len(argumento),
            pendente is not None,
            expirado,
        )
        await telegram_client.send_message(
            chat_id,
            "❌ Esse link de conexão é inválido ou expirou.\n"
            f"Gere um novo em {settings.WEB_APP_URL}/conectar-telegram",
        )
        return

    # O chat_id é único: se este chat estava ligado a outro usuário, o vínculo antigo é desfeito.
    anterior = _buscar_vinculo(db, chat_id)
    if anterior is not None and anterior.id != pendente.id:
        anterior.chat_id = None
        anterior.linked_at = None
        db.flush()

    pendente.chat_id = chat_id
    pendente.linked_at = agora
    pendente.link_token = None
    pendente.link_token_expires_at = None
    db.commit()

    usuario = db.get(User, pendente.user_id)
    nome = (usuario.full_name or usuario.email) if usuario else "por aqui"
    await telegram_client.send_message(
        chat_id,
        f"✅ Conta conectada, *{nome}*!\n\n{MENSAGEM_AJUDA}",
    )


async def _pedir_vinculo(chat_id: str) -> None:
    """Resposta padrão para quem ainda não vinculou a conta Web (seção 4.1, passo 3)."""
    await telegram_client.send_message(
        chat_id,
        "🔒 Não encontrei uma conta conectada a este chat.\n\n"
        f"Acesse {settings.WEB_APP_URL}/conectar-telegram, faça login e toque em "
        "*Conectar Telegram* — o link te traz de volta aqui já autenticado.",
    )


async def _cmd_saldo(db: Session, chat_id: str, user_id: uuid.UUID) -> None:
    """`/saldo` — resumo de receitas, despesas e saldo do mês corrente."""
    inicio = _inicio_do_mes()
    linhas = db.execute(
        select(Transaction.type, func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.user_id == user_id, Transaction.created_at >= inicio)
        .group_by(Transaction.type)
    ).all()

    totais = {tipo: Decimal(str(total)) for tipo, total in linhas}
    receitas = totais.get("income", Decimal("0"))
    despesas = totais.get("expense", Decimal("0"))
    saldo = receitas - despesas
    emoji = "🟢" if saldo >= 0 else "🔴"
    mes = datetime.now(TZ).strftime("%m/%Y")

    await telegram_client.send_message(
        chat_id,
        f"*Resumo de {mes}*\n\n"
        f"📈 Receitas: {formatar_brl(receitas)}\n"
        f"📉 Despesas: {formatar_brl(despesas)}\n"
        f"{emoji} Saldo: {formatar_brl(saldo)}",
    )


# --------------------------------------------------------------------------------------
# Lançamentos via IA
# --------------------------------------------------------------------------------------


def _normalizar_tipo(tipo: str | None) -> str | None:
    """Converte "Receita"/"despesa " no valor persistido ("income"/"expense")."""
    return TIPO_POR_EXTENSO.get((tipo or "").strip().lower())


def _persistir(
    db: Session, user_id: uuid.UUID, extraida: gemini.TransacaoExtraida, tipo: str
) -> Transaction:
    transacao = Transaction(
        user_id=user_id,
        description=(extraida.descricao or "Lançamento via Telegram")[:255],
        amount=abs(Decimal(str(extraida.valor))),
        category=(extraida.categoria or None),
        type=tipo,
        payment_method=(extraida.metodo_pagamento or None),
        source="telegram",
    )
    db.add(transacao)
    db.commit()
    db.refresh(transacao)
    return transacao


async def _registrar_lancamento(
    db: Session,
    chat_id: str,
    user_id: uuid.UUID,
    *,
    texto: str | None = None,
    audio: bytes | None = None,
    mime_type: str = "audio/ogg",
) -> None:
    await telegram_client.send_chat_action(chat_id)

    try:
        extraida = await gemini.extrair_transacao(texto=texto, audio=audio, mime_type=mime_type)
    except gemini.GeminiIndisponivelError:
        logger.exception("Cascata do Gemini indisponível para o chat %s", chat_id)
        await telegram_client.send_message(
            chat_id, "⚠️ A IA está indisponível no momento. Tente novamente em instantes."
        )
        return

    tipo = _normalizar_tipo(extraida.tipo)
    if not extraida.eh_transacao or extraida.valor is None or tipo is None:
        await telegram_client.send_message(
            chat_id,
            extraida.observacao
            or "🤔 Não consegui identificar um lançamento nessa mensagem.\n\n" + MENSAGEM_AJUDA,
        )
        return

    transacao = _persistir(db, user_id, extraida, tipo)

    sinal = "📈 Receita" if transacao.type == "income" else "📉 Despesa"
    detalhes = [f"{sinal} registrada!", f"*{transacao.description}*", formatar_brl(transacao.amount)]
    if transacao.category:
        detalhes.append(f"🏷️ {transacao.category}")
    if transacao.payment_method:
        detalhes.append(f"💳 {transacao.payment_method}")

    await telegram_client.send_message(chat_id, "\n".join(detalhes))


# --------------------------------------------------------------------------------------
# Dispatcher
# --------------------------------------------------------------------------------------


async def _tratar_mensagem(db: Session, mensagem: TelegramMessage) -> None:
    chat_id = str(mensagem.chat.id)
    texto = (mensagem.text or mensagem.caption or "").strip()

    if texto.startswith("/"):
        partes = texto.split(maxsplit=1)
        comando = partes[0].lower().split("@", 1)[0]
        argumento = partes[1].strip() if len(partes) > 1 else None

        if comando == "/start":
            await _cmd_start(db, chat_id, argumento)
            return

        vinculo = _buscar_vinculo(db, chat_id)
        if vinculo is None:
            await _pedir_vinculo(chat_id)
            return

        if comando == "/saldo":
            await _cmd_saldo(db, chat_id, vinculo.user_id)
        else:  # /ajuda, /help e qualquer comando desconhecido
            await telegram_client.send_message(chat_id, MENSAGEM_AJUDA)
        return

    # Daqui para baixo é conteúdo livre: exige conta vinculada (seção 4.1).
    vinculo = _buscar_vinculo(db, chat_id)
    if vinculo is None:
        await _pedir_vinculo(chat_id)
        return

    audio = mensagem.voice or mensagem.audio
    if audio is not None:
        if audio.file_size and audio.file_size > telegram_client.MAX_FILE_SIZE_BYTES:
            await telegram_client.send_message(
                chat_id, "⚠️ Áudio muito grande (limite de 20 MB). Envie um trecho menor."
            )
            return
        conteudo = await telegram_client.download_file(audio.file_id)
        await _registrar_lancamento(
            db,
            chat_id,
            vinculo.user_id,
            audio=conteudo,
            mime_type=audio.mime_type or "audio/ogg",
        )
        return

    if texto:
        await _registrar_lancamento(db, chat_id, vinculo.user_id, texto=texto)
        return

    await telegram_client.send_message(
        chat_id, "Só entendo *áudio* e *texto* por enquanto. 🙂\n\n" + MENSAGEM_AJUDA
    )


async def processar_update(update: TelegramUpdate) -> None:
    """Ponto de entrada do webhook. Roda em background: nunca propaga exceção."""
    mensagem = update.message or update.edited_message
    if mensagem is None:
        return

    db = SessionLocal()
    try:
        await _tratar_mensagem(db, mensagem)
    except Exception:  # noqa: BLE001 — o Telegram não deve receber erro e reenviar o update
        db.rollback()
        logger.exception("Falha ao processar update %s", update.update_id)
        try:
            await telegram_client.send_message(
                str(mensagem.chat.id),
                "⚠️ Tive um problema ao processar sua mensagem. Tente novamente.",
            )
        except Exception:  # noqa: BLE001
            logger.exception("Falha também ao notificar o chat %s", mensagem.chat.id)
    finally:
        db.close()
