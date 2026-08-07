"""Subconjunto do payload de Update da Bot API do Telegram.

Só mapeamos os campos que o fluxo do bot usa; `extra="ignore"` garante que
qualquer campo novo enviado pelo Telegram seja descartado sem quebrar o webhook.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TelegramBase(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class TelegramChat(TelegramBase):
    id: int
    type: str | None = None
    username: str | None = None
    first_name: str | None = None


class TelegramUser(TelegramBase):
    id: int
    is_bot: bool = False
    first_name: str | None = None
    username: str | None = None


class TelegramFile(TelegramBase):
    """Cobre tanto `voice` quanto `audio` — só precisamos do file_id e do tamanho."""

    file_id: str
    mime_type: str | None = None
    duration: int | None = None
    file_size: int | None = None


class TelegramMessage(TelegramBase):
    message_id: int
    chat: TelegramChat
    from_user: TelegramUser | None = Field(default=None, alias="from")
    text: str | None = None
    caption: str | None = None
    voice: TelegramFile | None = None
    audio: TelegramFile | None = None


class TelegramCallbackQuery(TelegramBase):
    id: str
    from_user: TelegramUser = Field(alias="from")
    message: TelegramMessage | None = None
    data: str | None = None


class TelegramUpdate(TelegramBase):
    update_id: int
    message: TelegramMessage | None = None
    edited_message: TelegramMessage | None = None
    callback_query: TelegramCallbackQuery | None = None


class TelegramLinkRequest(BaseModel):
    consent: bool


class TelegramLinkResponse(BaseModel):
    deep_link: str
    expires_at: datetime
    consent_version: str


class TelegramLinkStatus(BaseModel):
    linked: bool
    linked_at: datetime | None
    consent_version: str | None
    consented_at: datetime | None
