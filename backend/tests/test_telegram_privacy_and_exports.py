from csv import reader
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO, StringIO
from types import SimpleNamespace

from openpyxl import load_workbook

from app.core.config import settings
from app.services.spreadsheets import export_csv, export_xlsx
from app.services.telegram_bot import (
    _buscar_pendencia,
    _consentimento_valido,
    criar_link_token,
)


class PendingDb:
    def __init__(self, pending):
        self.pending = pending
        self.deleted = []
        self.commits = 0

    def scalar(self, statement):
        return self.pending

    def delete(self, value) -> None:
        self.deleted.append(value)

    def commit(self) -> None:
        self.commits += 1


def test_expired_pending_transaction_is_deleted_and_not_returned() -> None:
    pending = SimpleNamespace(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    db = PendingDb(pending)

    assert _buscar_pendencia(db, "123") is None
    assert db.deleted == [pending]
    assert db.commits == 1


def test_active_pending_transaction_is_returned() -> None:
    pending = SimpleNamespace(expires_at=datetime.now(UTC) + timedelta(minutes=1))
    db = PendingDb(pending)

    assert _buscar_pendencia(db, "123") is pending
    assert db.deleted == []
    assert db.commits == 0


def test_only_the_current_published_policy_is_valid_consent() -> None:
    current = SimpleNamespace(
        privacy_consented_at=datetime.now(UTC),
        privacy_consent_version=settings.PRIVACY_POLICY_VERSION,
    )
    stale = SimpleNamespace(
        privacy_consented_at=datetime.now(UTC),
        privacy_consent_version="versao-antiga",
    )

    assert _consentimento_valido(current)
    assert not _consentimento_valido(stale)


def test_link_generation_rejects_unpublished_policy_before_database_access() -> None:
    class UntouchedDb:
        def scalars(self, statement):
            raise AssertionError("o banco não deve ser acessado")

    try:
        criar_link_token(
            UntouchedDb(),
            SimpleNamespace(),
            consent_version="versao-inventada",
        )
    except ValueError as exc:
        assert "vigente" in str(exc)
    else:
        raise AssertionError("uma política desconhecida não pode gerar link")


def _formula_transaction():
    return SimpleNamespace(
        occurred_at=datetime(2026, 8, 10, tzinfo=UTC),
        type="expense",
        description="=HYPERLINK(\"https://example.invalid\")",
        amount=Decimal("10.00"),
        category="+cmd|' /C calc'!A0",
        payment_method="@SUM(1+1)",
    )


def test_csv_export_escapes_formula_prefixes() -> None:
    content = export_csv([_formula_transaction()]).decode("utf-8-sig")
    row = list(reader(StringIO(content), delimiter=";"))[1]

    assert row[2].startswith("'=")
    assert row[4].startswith("'+")
    assert row[5].startswith("'@")


def test_xlsx_export_escapes_formula_prefixes() -> None:
    workbook = load_workbook(BytesIO(export_xlsx([_formula_transaction()])))
    try:
        row = list(workbook.active.iter_rows(min_row=2, max_row=2))[0]
        assert row[2].value.startswith("'=")
        assert row[4].value.startswith("'+")
        assert row[5].value.startswith("'@")
        assert all(row[index].data_type == "s" for index in (2, 4, 5))
    finally:
        workbook.close()
