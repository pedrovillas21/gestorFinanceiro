from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
import json
import uuid

from app.core.money import decimal_from_value, quantize_money
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.main import app
from app.schemas.transaction import TransactionResponse
from app.services.spreadsheets import export_xlsx, parse_rows


def test_money_uses_commercial_rounding_and_brazilian_input() -> None:
    assert decimal_from_value("R$ 1.234,567") == Decimal("1234.567")
    assert quantize_money("1.005") == Decimal("1.01")
    assert quantize_money(0.1) == Decimal("0.10")


def test_password_and_jwt_round_trip() -> None:
    password_hash = hash_password("senha-segura")
    assert verify_password("senha-segura", password_hash)
    assert not verify_password("senha-errada", password_hash)

    user_id = uuid.uuid4()
    token, expires_at = create_access_token(user_id)
    assert decode_access_token(token) == user_id
    assert expires_at > datetime.now(UTC)


def test_money_is_serialized_as_json_string() -> None:
    response = TransactionResponse.model_validate(
        {
            "id": uuid.uuid4(),
            "description": "Mercado",
            "amount": Decimal("42.90"),
            "category": "Alimentação",
            "type": "expense",
            "payment_method": "pix",
            "source": "web",
            "occurred_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
        }
    )
    assert json.loads(response.model_dump_json())["amount"] == "42.90"


def test_csv_and_xlsx_import_contract() -> None:
    csv_content = (
        "data;tipo;descricao;valor;categoria;metodo_pagamento\n"
        "2026-08-07;despesa;Mercado;42,90;Alimentação;pix\n"
    ).encode("utf-8")
    rows = parse_rows(csv_content, "transacoes.csv")
    assert rows[0]["type"] == "expense"
    assert rows[0]["amount"] == Decimal("42.90")
    assert rows[0]["occurred_at"].tzinfo is UTC

    item = SimpleNamespace(
        occurred_at=datetime(2026, 8, 7, tzinfo=UTC),
        type="expense",
        description="Mercado",
        amount=Decimal("42.90"),
        category="Alimentação",
        payment_method="pix",
    )
    xlsx_content = export_xlsx([item])
    imported = parse_rows(xlsx_content, "transacoes.xlsx")
    assert imported[0]["amount"] == Decimal("42.90")


def test_expected_backend_routes_are_registered() -> None:
    paths = set(app.openapi()["paths"])
    assert {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/transactions",
        "/api/v1/transactions/import",
        "/api/v1/transactions/export",
        "/api/v1/dashboard/summary",
        "/api/v1/telegram/link",
        "/api/v1/telegram/webhook",
        "/api/v1/investments/assets",
        "/api/v1/investments/portfolio",
        "/api/v1/investments/quotes/refresh",
        "/api/v1/calculators/compound-interest",
    } <= paths
