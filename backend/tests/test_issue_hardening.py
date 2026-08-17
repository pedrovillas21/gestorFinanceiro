from contextlib import nullcontext
from io import BytesIO
from types import SimpleNamespace
import uuid

from fastapi import HTTPException
from openpyxl import Workbook
from pydantic import ValidationError
import pytest

from app.api.v1 import auth, investments, transactions
from app import main
from app.core.security import DUMMY_PASSWORD_HASH, hash_password
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.spreadsheets import parse_rows


def test_bcrypt_limit_is_enforced_in_utf8_bytes() -> None:
    password = "á" * 37  # 37 characters, but 74 UTF-8 bytes.

    with pytest.raises(ValueError, match="72 bytes"):
        hash_password(password)
    with pytest.raises(ValidationError, match="72 bytes"):
        RegisterRequest(email="pessoa@example.com", password=password)


def test_unknown_login_runs_dummy_bcrypt_comparison(monkeypatch) -> None:
    compared = {}

    def fake_verify(password: str, password_hash: str) -> bool:
        compared.update(password=password, password_hash=password_hash)
        return False

    monkeypatch.setattr(auth, "verify_password", fake_verify)
    # O login falho registra a tentativa no bloqueio progressivo, então a sessão
    # falsa precisa aceitar escrita — só a comparação de senha é o assunto aqui.
    db = SimpleNamespace(
        scalar=lambda statement: None,
        scalars=lambda statement: SimpleNamespace(all=lambda: []),
        add=lambda row: None,
        flush=lambda: None,
        commit=lambda: None,
        # O INSERT do escopo novo roda dentro de um savepoint; sem banco aqui,
        # basta um contexto que não faça nada.
        begin_nested=nullcontext,
    )

    with pytest.raises(HTTPException) as exc_info:
        auth.login(LoginRequest(email="missing@example.com", password="secret"), db)

    assert exc_info.value.status_code == 401
    assert compared == {
        "password": "secret",
        "password_hash": DUMMY_PASSWORD_HASH,
    }


def test_registration_relies_on_database_unique_constraint(monkeypatch) -> None:
    class RecordingDb:
        added = None

        def scalar(self, statement):
            raise AssertionError("registration must not pre-query the e-mail")

        def add(self, user) -> None:
            self.added = user

        def commit(self) -> None:
            return None

        def refresh(self, user) -> None:
            return None

    db = RecordingDb()
    monkeypatch.setattr(auth, "hash_password", lambda password: "hashed")
    monkeypatch.setattr(auth, "_start_session", lambda db, user, user_agent=None: "token")

    result = auth.register(
        RegisterRequest(email="new@example.com", password="safe-password"), db
    )

    assert result == "token"
    assert db.added.email == "new@example.com"


def test_asset_lock_uses_select_for_update() -> None:
    class RecordingDb:
        statement = None

        def scalar(self, statement):
            self.statement = statement
            return SimpleNamespace(id=uuid.uuid4())

    db = RecordingDb()
    investments._owned_asset(db, uuid.uuid4(), uuid.uuid4(), for_update=True)

    assert db.statement._for_update_arg is not None


@pytest.mark.parametrize("extension", ["csv", "xlsx"])
def test_import_stops_when_row_limit_is_exceeded(extension: str) -> None:
    if extension == "csv":
        content = (
            "data;tipo;descricao;valor\n"
            "2026-08-01;despesa;Um;1\n"
            "2026-08-02;despesa;Dois;2\n"
            "2026-08-03;despesa;Três;3\n"
        ).encode()
    else:
        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet("Transações")
        sheet.append(["data", "tipo", "descricao", "valor"])
        for day in range(1, 4):
            sheet.append([f"2026-08-0{day}", "despesa", str(day), day])
        output = BytesIO()
        workbook.save(output)
        content = output.getvalue()

    with pytest.raises(ValueError, match="limite de 2 linhas"):
        parse_rows(content, f"import.{extension}", max_rows=2)


def test_upload_read_is_bounded(monkeypatch) -> None:
    monkeypatch.setattr(transactions, "MAX_IMPORT_UPLOAD_BYTES", 8)

    class OversizedStream:
        requested = None

        def read(self, size: int) -> bytes:
            self.requested = size
            return b"x" * size

    stream = OversizedStream()
    upload = SimpleNamespace(filename="large.csv", file=stream)

    with pytest.raises(HTTPException) as exc_info:
        transactions.import_file(
            current_user=SimpleNamespace(id=uuid.uuid4()), db=None, file=upload
        )

    assert exc_info.value.status_code == 413
    assert stream.requested == 9


def test_large_upload_payload_is_persisted_for_worker(monkeypatch) -> None:
    monkeypatch.setattr(transactions, "ASYNC_IMPORT_THRESHOLD", 3)
    monkeypatch.setattr(transactions, "MAX_IMPORT_UPLOAD_BYTES", 8)

    class RecordingDb:
        job = None

        def add(self, job) -> None:
            self.job = job

        def commit(self) -> None:
            return None

        def refresh(self, job) -> None:
            job.status = "pending"

    db = RecordingDb()
    content = b"1234"
    result = transactions.import_file(
        current_user=SimpleNamespace(id=uuid.uuid4()),
        db=db,
        file=SimpleNamespace(filename="large.csv", file=BytesIO(content)),
    )

    assert result is db.job
    assert result.status == "pending"
    assert result.content == content


def test_cors_wildcard_is_rejected_when_credentials_are_enabled() -> None:
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        main._cors_origins_with_credentials(["*"])
