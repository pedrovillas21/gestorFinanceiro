"""Regras de negócio do bot do Telegram (seção 4 do guia).

Fluxo: autenticação por `chat_id` -> comandos (/start, /ajuda, /saldo) ->
processamento de áudio/texto pela Cascata do Gemini -> persistência da transação.
"""
import asyncio
import logging
import secrets
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.money import decimal_from_value, quantize_money
from app.core.privacy import get_privacy_policy, has_privacy_policy
from app.database import SessionLocal
from app.models.telegram_token import TelegramToken
from app.models.transaction import Transaction
from app.models.telegram_update import ProcessedTelegramUpdate
from app.models.pending_transaction import PendingTransaction
from app.models.user import User
from app.schemas.telegram import TelegramMessage, TelegramUpdate
from app.services import gemini, telegram_client

logger = logging.getLogger(__name__)

TZ = ZoneInfo("America/Sao_Paulo")

TIPO_POR_EXTENSO = {"receita": "income", "despesa": "expense"}
CONFIRMATION_TTL_MINUTES = 10

MENSAGEM_AJUDA = (
    "*Como usar o Gestor Financeiro IA* 🤖\n\n"
    "Mande um *áudio* ou um *texto* descrevendo o que entrou ou saiu — a IA cuida do resto.\n\n"
    "Exemplos:\n"
    "• _“gastei 42 e noventa no mercado no débito”_\n"
    "• _“recebi 3500 de salário hoje”_\n"
    "• _“paguei 120 reais de energia no pix”_\n\n"
    "*Comandos*\n"
    "/saldo [dia|semana|mês|3meses] — resumo de receitas e despesas do período (padrão: mês)\n"
    "/ajuda — esta mensagem\n"
    "/start — conectar sua conta da Web\n\n"
    "Também dá pra perguntar direto: _“quanto gastei essa semana?”_ ou "
    "_“como tô nos últimos 3 meses?”_"
)


# --------------------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------------------


def formatar_brl(valor: Decimal) -> str:
    """Formata um número no padrão brasileiro: 1234.5 -> 'R$ 1.234,50'."""
    quantizado = valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"R$ {quantizado:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


# O parâmetro `agora` existe para os testes fixarem a data; em produção todas
# são chamadas sem argumento (ver a assinatura de `PERIODOS`).
def _inicio_do_dia(agora: datetime | None = None) -> datetime:
    """Meia-noite de hoje no fuso de São Paulo, em UTC."""
    agora = agora or datetime.now(TZ)
    return agora.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


def _inicio_da_semana(agora: datetime | None = None) -> datetime:
    """Meia-noite da segunda-feira da semana corrente no fuso de São Paulo, em UTC."""
    agora = agora or datetime.now(TZ)
    inicio = agora - timedelta(days=agora.weekday())
    return inicio.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


def _inicio_do_mes(agora: datetime | None = None) -> datetime:
    """Primeiro instante do mês corrente no fuso de São Paulo, em UTC."""
    agora = agora or datetime.now(TZ)
    return agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


def _inicio_3_meses(agora: datetime | None = None) -> datetime:
    """Meia-noite do dia de 3 meses atrás, no fuso de São Paulo, em UTC.

    É uma janela móvel de 3 meses contados da data de hoje — em 5 de agosto ela
    começa em 5 de maio, não em 1º de junho. Quando o dia não existe no mês de
    destino (31 de maio -> fevereiro), `relativedelta` encosta no último dia do
    mês (28 ou 29 de fevereiro).
    """
    agora = agora or datetime.now(TZ)
    inicio = agora - relativedelta(months=3)
    return inicio.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


# Períodos aceitos por `/saldo` e pela consulta em linguagem natural via IA — as
# chaves precisam bater com `gemini.PERIODOS_SALDO`.
PERIODOS: dict[str, tuple[str, Callable[[], datetime]]] = {
    "dia": ("Hoje", _inicio_do_dia),
    "semana": ("Esta semana", _inicio_da_semana),
    "mes": ("Este mês", _inicio_do_mes),
    "3meses": ("Últimos 3 meses", _inicio_3_meses),
}

# Apelidos aceitos no argumento de "/saldo <periodo>" (texto livre digitado à mão).
_APELIDOS_PERIODO = {
    "hoje": "dia",
    "dia": "dia",
    "semana": "semana",
    "mes": "mes",
    "mês": "mes",
    "3meses": "3meses",
    "3 meses": "3meses",
    "trimestre": "3meses",
}


def _normalizar_periodo(argumento: str | None) -> str:
    """Converte o argumento digitado em `/saldo <periodo>` numa chave válida de `PERIODOS`.

    Vale só para o texto livre do comando: o `periodo_consulta` vindo da IA já é
    validado contra a lista fechada no schema do Gemini.
    """
    chave = (argumento or "").strip().lower()
    return _APELIDOS_PERIODO.get(chave, "mes")


def montar_deep_link(link_token: str) -> str:
    """Deep Link do Telegram que dispara `/start <link_token>` no bot."""
    username = (settings.TELEGRAM_BOT_USERNAME or "").lstrip("@")
    if not username:
        return f"(configure TELEGRAM_BOT_USERNAME no .env) token: {link_token}"
    return f"https://t.me/{username}?start={link_token}"


def criar_link_token(
    db: Session, user_id: uuid.UUID, *, consent_version: str
) -> str:
    """Gera (ou renova) o token de vínculo de um usuário para uso no Deep Link.

    Chamado pela aplicação Web / pelo script `scripts/gerar_link_telegram.py`.
    """
    if consent_version != settings.PRIVACY_POLICY_VERSION:
        raise ValueError("a versão aceita não é a política de privacidade vigente")
    try:
        get_privacy_policy(consent_version)
    except KeyError as exc:
        raise ValueError("a política de privacidade informada não foi publicada") from exc

    vinculo = db.scalars(
        select(TelegramToken).where(TelegramToken.user_id == user_id)
    ).one_or_none()

    if vinculo is None:
        vinculo = TelegramToken(user_id=user_id)
        db.add(vinculo)

    vinculo.privacy_consent_version = consent_version
    vinculo.privacy_consented_at = datetime.now(UTC)

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


def _consentimento_valido(link: TelegramToken | None) -> bool:
    return bool(
        link
        and link.privacy_consented_at is not None
        and link.privacy_consent_version == settings.PRIVACY_POLICY_VERSION
        and has_privacy_policy(settings.PRIVACY_POLICY_VERSION)
    )


# --------------------------------------------------------------------------------------
# Comandos
# --------------------------------------------------------------------------------------


async def _cmd_start(db: Session, chat_id: str, argumento: str | None) -> None:
    """`/start [token]` — conclui o vínculo do Deep Link (seção 4.1)."""
    if not argumento:
        link = _buscar_vinculo(db, chat_id)
        if _consentimento_valido(link):
            await telegram_client.send_message(
                chat_id, "Sua conta já está conectada. ✅\n\n" + MENSAGEM_AJUDA
            )
        elif link is not None:
            await _pedir_consentimento(chat_id)
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


async def _cmd_saldo(db: Session, chat_id: str, user_id: uuid.UUID, periodo: str = "mes") -> None:
    """`/saldo` (ou pergunta em linguagem natural) — resumo de receitas, despesas e saldo do período."""
    titulo, calcular_inicio = PERIODOS.get(periodo, PERIODOS["mes"])
    inicio = calcular_inicio()
    linhas = db.execute(
        select(Transaction.type, func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.user_id == user_id, Transaction.occurred_at >= inicio)
        .group_by(Transaction.type)
    ).all()

    totais = {tipo: Decimal(str(total)) for tipo, total in linhas}
    receitas = totais.get("income", Decimal("0"))
    despesas = totais.get("expense", Decimal("0"))
    saldo = receitas - despesas
    emoji = "🟢" if saldo >= 0 else "🔴"

    await telegram_client.send_message(
        chat_id,
        f"*Saldo — {titulo}*\n\n"
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
        amount=quantize_money(abs(Decimal(str(extraida.valor)))),
        category=(extraida.categoria or None),
        type=tipo,
        payment_method=(extraida.metodo_pagamento or None),
        source="telegram",
    )
    db.add(transacao)
    db.commit()
    db.refresh(transacao)
    return transacao


async def _confirmar_transacao(chat_id: str, transacao: Transaction) -> None:
    sinal = "📈 Receita" if transacao.type == "income" else "📉 Despesa"
    detalhes = [
        f"{sinal} registrada!",
        f"*{transacao.description}*",
        formatar_brl(transacao.amount),
    ]
    if transacao.category:
        detalhes.append(f"🏷️ {transacao.category}")
    if transacao.payment_method:
        detalhes.append(f"💳 {transacao.payment_method}")
    await telegram_client.send_message(chat_id, "\n".join(detalhes))


def _buscar_pendencia(db: Session, chat_id: str) -> PendingTransaction | None:
    pending = db.scalar(
        select(PendingTransaction).where(PendingTransaction.chat_id == chat_id)
    )
    if pending is not None and pending.expires_at <= datetime.now(UTC):
        db.delete(pending)
        db.commit()
        return None
    return pending


async def _pedir_consentimento(chat_id: str) -> None:
    await telegram_client.send_message(
        chat_id,
        "🔐 Sua conta foi vinculada antes do registro de consentimento.\n\n"
        f"Acesse {settings.WEB_APP_URL}/conectar-telegram, leia a política e gere "
        "um novo link para continuar.",
    )


async def _pedir_tipo(chat_id: str) -> None:
    await telegram_client.send_message(
        chat_id,
        "Não consegui determinar o tipo. Foi uma receita ou uma despesa?",
        reply_markup={
            "inline_keyboard": [
                [
                    {"text": "📈 Receita", "callback_data": "tx:type:income"},
                    {"text": "📉 Despesa", "callback_data": "tx:type:expense"},
                ],
                [{"text": "Cancelar", "callback_data": "tx:cancel"}],
            ]
        },
    )


async def _pedir_valor(chat_id: str) -> None:
    await telegram_client.send_message(
        chat_id,
        "Não consegui determinar o valor. Toque abaixo e depois envie apenas o valor.",
        reply_markup={
            "inline_keyboard": [
                [{"text": "⌨️ Informar valor", "callback_data": "tx:amount"}],
                [{"text": "Cancelar", "callback_data": "tx:cancel"}],
            ]
        },
    )


async def _concluir_pendencia(db: Session, pending: PendingTransaction) -> Transaction:
    if pending.amount is None or pending.transaction_type is None:
        raise ValueError("pendência ainda incompleta")
    transaction = Transaction(
        user_id=pending.user_id,
        description=(pending.description or "Lançamento via Telegram")[:255],
        amount=pending.amount,
        category=pending.category,
        type=pending.transaction_type,
        payment_method=pending.payment_method,
        source="telegram",
    )
    chat_id = pending.chat_id
    db.add(transaction)
    db.delete(pending)
    db.commit()
    db.refresh(transaction)
    await _confirmar_transacao(chat_id, transaction)
    return transaction


async def _criar_pendencia(
    db: Session,
    chat_id: str,
    user_id: uuid.UUID,
    extraida: gemini.TransacaoExtraida,
    tipo: str | None,
) -> None:
    pending = _buscar_pendencia(db, chat_id)
    if pending is None:
        pending = PendingTransaction(user_id=user_id, chat_id=chat_id, awaiting="type")
        db.add(pending)
    pending.description = (extraida.descricao or "Lançamento via Telegram")[:255]
    pending.amount = (
        quantize_money(abs(Decimal(str(extraida.valor))))
        if extraida.valor is not None
        else None
    )
    pending.category = extraida.categoria or None
    pending.transaction_type = tipo
    pending.payment_method = extraida.metodo_pagamento or None
    pending.awaiting = "type" if tipo is None else "amount"
    pending.expires_at = datetime.now(UTC) + timedelta(minutes=CONFIRMATION_TTL_MINUTES)
    db.commit()
    if pending.awaiting == "type":
        await _pedir_tipo(chat_id)
    else:
        await _pedir_valor(chat_id)


async def _receber_valor_pendente(
    db: Session, pending: PendingTransaction, text: str
) -> None:
    try:
        amount = quantize_money(abs(decimal_from_value(text)))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await telegram_client.send_message(
            pending.chat_id, "Valor inválido. Envie somente um valor positivo, como `42,90`."
        )
        return
    pending.amount = amount
    pending.expires_at = datetime.now(UTC) + timedelta(minutes=CONFIRMATION_TTL_MINUTES)
    if pending.transaction_type is None:
        pending.awaiting = "type"
        db.commit()
        await _pedir_tipo(pending.chat_id)
    else:
        await _concluir_pendencia(db, pending)


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

    if extraida.eh_consulta_saldo:
        # `periodo_consulta` já veio validado contra `PERIODOS` pelo schema do
        # Gemini — não passa por `_normalizar_periodo`, que é para o texto livre
        # digitado em "/saldo <periodo>".
        await _cmd_saldo(db, chat_id, user_id, periodo=extraida.periodo_consulta)
        return

    tipo = _normalizar_tipo(extraida.tipo)
    if extraida.eh_transacao and (extraida.valor is None or tipo is None):
        await _criar_pendencia(db, chat_id, user_id, extraida, tipo)
        return
    if not extraida.eh_transacao:
        await telegram_client.send_message(
            chat_id,
            extraida.observacao
            or "🤔 Não consegui identificar um lançamento nessa mensagem.\n\n" + MENSAGEM_AJUDA,
        )
        return

    transacao = _persistir(db, user_id, extraida, tipo)
    await _confirmar_transacao(chat_id, transacao)


async def _tratar_callback(db: Session, callback) -> None:
    if callback.message is None or not callback.data:
        await telegram_client.answer_callback_query(callback.id)
        return
    chat_id = str(callback.message.chat.id)
    link = _buscar_vinculo(db, chat_id)
    pending = _buscar_pendencia(db, chat_id)
    if (
        not _consentimento_valido(link)
        or pending is None
        or pending.user_id != link.user_id
    ):
        await telegram_client.answer_callback_query(callback.id, "Confirmação expirada")
        await telegram_client.send_message(
            chat_id, "Essa confirmação expirou. Envie o lançamento novamente."
        )
        return

    data = callback.data
    if data == "tx:cancel":
        db.delete(pending)
        db.commit()
        await telegram_client.answer_callback_query(callback.id, "Lançamento cancelado")
        await telegram_client.send_message(chat_id, "Lançamento cancelado.")
        return
    if data == "tx:amount":
        pending.awaiting = "amount"
        pending.expires_at = datetime.now(UTC) + timedelta(minutes=CONFIRMATION_TTL_MINUTES)
        db.commit()
        await telegram_client.answer_callback_query(callback.id)
        await telegram_client.send_message(chat_id, "Envie agora apenas o valor, como `42,90`.")
        return
    if data in {"tx:type:income", "tx:type:expense"}:
        pending.transaction_type = data.rsplit(":", 1)[-1]
        pending.expires_at = datetime.now(UTC) + timedelta(minutes=CONFIRMATION_TTL_MINUTES)
        await telegram_client.answer_callback_query(callback.id, "Tipo confirmado")
        if pending.amount is None:
            pending.awaiting = "amount"
            db.commit()
            await _pedir_valor(chat_id)
        else:
            await _concluir_pendencia(db, pending)
        return
    await telegram_client.answer_callback_query(callback.id, "Opção inválida")


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
        if not _consentimento_valido(vinculo):
            await _pedir_consentimento(chat_id)
            return

        if comando == "/saldo":
            await _cmd_saldo(db, chat_id, vinculo.user_id, periodo=_normalizar_periodo(argumento))
        else:  # /ajuda, /help e qualquer comando desconhecido
            await telegram_client.send_message(chat_id, MENSAGEM_AJUDA)
        return

    # Daqui para baixo é conteúdo livre: exige conta vinculada (seção 4.1).
    vinculo = _buscar_vinculo(db, chat_id)
    if vinculo is None:
        await _pedir_vinculo(chat_id)
        return
    if not _consentimento_valido(vinculo):
        await _pedir_consentimento(chat_id)
        return

    pending = _buscar_pendencia(db, chat_id)
    if pending is not None and pending.awaiting == "amount" and texto:
        await _receber_valor_pendente(db, pending, texto)
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


async def _processar_update_async(update: TelegramUpdate) -> None:
    """Ponto de entrada do webhook. Roda em background: nunca propaga exceção."""
    mensagem = update.message or update.edited_message
    callback = update.callback_query
    if mensagem is None and callback is None:
        return

    db = SessionLocal()
    try:
        db.add(ProcessedTelegramUpdate(update_id=update.update_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            logger.info("Update %s ignorado por já ter sido processado", update.update_id)
            return
        if callback is not None:
            await _tratar_callback(db, callback)
        elif mensagem is not None:
            await _tratar_mensagem(db, mensagem)
    except Exception:  # noqa: BLE001 — o Telegram não deve receber erro e reenviar o update
        db.rollback()
        logger.exception("Falha ao processar update %s", update.update_id)
        try:
            error_message = mensagem or (callback.message if callback else None)
            if error_message is None:
                return
            await telegram_client.send_message(
                str(error_message.chat.id),
                "⚠️ Tive um problema ao processar sua mensagem. Tente novamente.",
            )
        except Exception:  # noqa: BLE001
            logger.exception("Falha também ao notificar o chat")
    finally:
        db.close()


def processar_update(update: TelegramUpdate) -> None:
    """Executa o fluxo em uma thread com event loop privado.

    Por ser uma BackgroundTask síncrona, o Starlette a envia ao thread pool.
    Assim as chamadas SQLAlchemy/psycopg2 não bloqueiam o event loop da API.
    """
    asyncio.run(_processar_update_async(update))
