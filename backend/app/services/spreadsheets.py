"""Importação e exportação de transações sem executar pandas no event loop."""

import csv
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
import uuid
from zoneinfo import ZoneInfo

from openpyxl import Workbook, load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.money import quantize_money
from app.database import SessionLocal
from app.models.import_job import ImportJob
from app.models.transaction import Transaction


TZ = ZoneInfo("America/Sao_Paulo")
COLUMN_ALIASES = {
    "description": ("description", "descricao", "descrição"),
    "amount": ("amount", "valor"),
    "category": ("category", "categoria"),
    "type": ("type", "tipo"),
    "payment_method": ("payment_method", "metodo_pagamento", "método_pagamento"),
    "occurred_at": ("occurred_at", "data", "date"),
}
TYPE_ALIASES = {
    "income": "income",
    "receita": "income",
    "entrada": "income",
    "expense": "expense",
    "despesa": "expense",
    "saida": "expense",
    "saída": "expense",
}


def _normalized_headers(row: dict[object, object]) -> dict[str, object]:
    raw = {str(key).strip().lower(): value for key, value in row.items() if key is not None}
    return {
        canonical: next((raw[name] for name in aliases if name in raw), None)
        for canonical, aliases in COLUMN_ALIASES.items()
    }


def _parse_datetime(value: object) -> datetime:
    if value in (None, ""):
        return datetime.now(UTC)
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, date):
        result = datetime.combine(value, datetime.min.time())
    else:
        text = str(value).strip()
        try:
            result = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"data inválida: {text}; use AAAA-MM-DD") from exc
    if result.tzinfo is None:
        result = result.replace(tzinfo=TZ)
    return result.astimezone(UTC)


def _csv_rows(content: bytes) -> list[dict[object, object]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
    except csv.Error:
        dialect = csv.excel
    return list(csv.DictReader(StringIO(text), dialect=dialect))


def _xlsx_rows(content: bytes) -> list[dict[object, object]]:
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)
    headers = next(rows, None)
    if not headers:
        return []
    return [dict(zip(headers, values, strict=False)) for values in rows]


def parse_rows(content: bytes, filename: str) -> list[dict[str, object]]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        source_rows = _csv_rows(content)
    elif suffix == ".xlsx":
        source_rows = _xlsx_rows(content)
    else:
        raise ValueError("formato não suportado; envie CSV ou XLSX")

    parsed: list[dict[str, object]] = []
    for row_number, raw_row in enumerate(source_rows, start=2):
        row = _normalized_headers(raw_row)
        description = str(row["description"] or "").strip()
        transaction_type = TYPE_ALIASES.get(str(row["type"] or "").strip().lower())
        if not description or transaction_type is None or row["amount"] in (None, ""):
            raise ValueError(
                f"linha {row_number}: descrição, valor e tipo (receita/despesa) são obrigatórios"
            )
        amount = quantize_money(row["amount"])
        if amount <= 0:
            raise ValueError(f"linha {row_number}: valor deve ser positivo")
        parsed.append(
            {
                "description": description[:255],
                "amount": amount,
                "category": str(row["category"]).strip()[:100]
                if row["category"] not in (None, "")
                else None,
                "type": transaction_type,
                "payment_method": str(row["payment_method"]).strip()[:50]
                if row["payment_method"] not in (None, "")
                else None,
                "occurred_at": _parse_datetime(row["occurred_at"]),
            }
        )
    return parsed


def import_transactions(
    db: Session, user_id: uuid.UUID, content: bytes, filename: str
) -> tuple[int, int]:
    rows = parse_rows(content, filename)
    for row in rows:
        db.add(Transaction(user_id=user_id, source="import", **row))
    db.commit()
    return len(rows), len(rows)


def process_import_job(
    job_id: uuid.UUID, user_id: uuid.UUID, content: bytes, filename: str
) -> None:
    db = SessionLocal()
    try:
        job = db.get(ImportJob, job_id)
        if job is None or job.user_id != user_id:
            return
        job.status = "processing"
        db.commit()
        try:
            total, imported = import_transactions(db, user_id, content, filename)
            job = db.get(ImportJob, job_id)
            if job is not None:
                job.status = "completed"
                job.total_rows = total
                job.imported_rows = imported
                job.completed_at = datetime.now(UTC)
                db.commit()
        except Exception as exc:  # o estado do job precisa registrar qualquer falha
            db.rollback()
            job = db.get(ImportJob, job_id)
            if job is not None:
                job.status = "failed"
                job.error_message = str(exc)[:2000]
                job.completed_at = datetime.now(UTC)
                db.commit()
    finally:
        db.close()


def export_csv(transactions: list[Transaction]) -> bytes:
    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["data", "tipo", "descricao", "valor", "categoria", "metodo_pagamento"])
    for item in transactions:
        writer.writerow(
            [
                item.occurred_at.isoformat(),
                item.type,
                item.description,
                str(item.amount),
                item.category or "",
                item.payment_method or "",
            ]
        )
    return output.getvalue().encode("utf-8-sig")


def export_xlsx(transactions: list[Transaction]) -> bytes:
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Transações")
    sheet.append(["data", "tipo", "descricao", "valor", "categoria", "metodo_pagamento"])
    for item in transactions:
        sheet.append(
            [
                item.occurred_at.replace(tzinfo=None),
                item.type,
                item.description,
                str(item.amount),
                item.category or "",
                item.payment_method or "",
            ]
        )
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
