import asyncio

from app.schemas.telegram import TelegramUpdate
from app.services import telegram_client


def test_callback_query_is_accepted_by_schema() -> None:
    update = TelegramUpdate.model_validate(
        {
            "update_id": 123,
            "callback_query": {
                "id": "callback-1",
                "from": {"id": 10, "is_bot": False},
                "message": {
                    "message_id": 20,
                    "chat": {"id": 30, "type": "private"},
                    "text": "confirmar",
                },
                "data": "tx:type:expense",
            },
        }
    )
    assert update.callback_query is not None
    assert update.callback_query.data == "tx:type:expense"
    assert update.callback_query.message.chat.id == 30


def test_inline_keyboard_is_sent_to_telegram(monkeypatch) -> None:
    captured = {}

    async def fake_call(method, payload=None):
        captured["method"] = method
        captured["payload"] = payload
        return True

    monkeypatch.setattr(telegram_client, "call", fake_call)
    keyboard = {
        "inline_keyboard": [[{"text": "Despesa", "callback_data": "tx:type:expense"}]]
    }
    asyncio.run(telegram_client.send_message("30", "Confirme", reply_markup=keyboard))
    assert captured["method"] == "sendMessage"
    assert captured["payload"]["reply_markup"] == keyboard
