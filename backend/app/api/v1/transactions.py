import uuid
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.money import quantize_money
from app.models.import_job import ImportJob
from app.models.transaction import Transaction
from app.schemas.import_job import ImportJobResponse
from app.schemas.transaction import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.spreadsheets import (
    export_csv,
    export_xlsx,
    import_transactions,
    process_import_job,
)


router = APIRouter(prefix="/transactions", tags=["transactions"])
TZ = ZoneInfo("America/Sao_Paulo")
ASYNC_IMPORT_THRESHOLD = 5 * 1024 * 1024


def _as_utc(value: datetime | None) -> datetime:
    value = value or datetime.now(UTC)
    if value.tzinfo is None:
        value = value.replace(tzinfo=TZ)
    return value.astimezone(UTC)


def _conditions(
    user_id: uuid.UUID,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    category: str | None = None,
    transaction_type: str | None = None,
    search: str | None = None,
) -> list:
    conditions = [Transaction.user_id == user_id]
    if start:
        conditions.append(Transaction.occurred_at >= _as_utc(start))
    if end:
        conditions.append(Transaction.occurred_at < _as_utc(end))
    if category:
        conditions.append(Transaction.category == category)
    if transaction_type:
        conditions.append(Transaction.type == transaction_type)
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(Transaction.description.ilike(pattern), Transaction.category.ilike(pattern))
        )
    return conditions


def _owned_transaction(
    db: DatabaseSession, user_id: uuid.UUID, transaction_id: uuid.UUID
) -> Transaction:
    item = db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id, Transaction.user_id == user_id
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    return item


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    current_user: CurrentUser,
    db: DatabaseSession,
    start: datetime | None = None,
    end: datetime | None = None,
    category: str | None = None,
    transaction_type: Literal["income", "expense"] | None = Query(default=None, alias="type"),
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> TransactionListResponse:
    conditions = _conditions(
        current_user.id,
        start=start,
        end=end,
        category=category,
        transaction_type=transaction_type,
        search=search,
    )
    total = db.scalar(select(func.count()).select_from(Transaction).where(*conditions)) or 0
    items = list(
        db.scalars(
            select(Transaction)
            .where(*conditions)
            .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return TransactionListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate, current_user: CurrentUser, db: DatabaseSession
) -> Transaction:
    try:
        amount = quantize_money(payload.amount)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    item = Transaction(
        user_id=current_user.id,
        description=payload.description.strip(),
        amount=amount,
        category=payload.category,
        type=payload.type,
        payment_method=payload.payment_method,
        source="web",
        occurred_at=_as_utc(payload.occurred_at),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/import", response_model=ImportJobResponse, status_code=status.HTTP_202_ACCEPTED)
def import_file(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DatabaseSession,
    file: UploadFile = File(...),
) -> ImportJob:
    filename = (file.filename or "import.csv")[:255]
    if not filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=415, detail="Envie um arquivo CSV ou XLSX")
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Arquivo vazio")

    job = ImportJob(user_id=current_user.id, filename=filename)
    db.add(job)
    db.commit()
    db.refresh(job)

    if len(content) > ASYNC_IMPORT_THRESHOLD:
        background_tasks.add_task(
            process_import_job, job.id, current_user.id, content, filename
        )
        return job

    try:
        total, imported = import_transactions(db, current_user.id, content, filename)
    except Exception as exc:
        db.rollback()
        is_validation_error = isinstance(exc, ValueError)
        detail = str(exc) if is_validation_error else "Falha ao importar a planilha"
        job = db.get(ImportJob, job.id)
        if job is not None:
            job.status = "failed"
            job.error_message = detail
            job.completed_at = datetime.now(UTC)
            db.commit()
        raise HTTPException(
            status_code=422 if is_validation_error else 500, detail=detail
        ) from exc
    job = db.get(ImportJob, job.id)
    job.status = "completed"
    job.total_rows = total
    job.imported_rows = imported
    job.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)
    return job


@router.get("/imports/{job_id}", response_model=ImportJobResponse)
def get_import_job(
    job_id: uuid.UUID, current_user: CurrentUser, db: DatabaseSession
) -> ImportJob:
    job = db.scalar(
        select(ImportJob).where(
            ImportJob.id == job_id, ImportJob.user_id == current_user.id
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    return job


@router.get("/export")
def export_transactions(
    current_user: CurrentUser,
    db: DatabaseSession,
    format: Literal["csv", "xlsx"] = "csv",
    start: datetime | None = None,
    end: datetime | None = None,
) -> StreamingResponse:
    items = list(
        db.scalars(
            select(Transaction)
            .where(*_conditions(current_user.id, start=start, end=end))
            .order_by(Transaction.occurred_at)
        ).all()
    )
    if format == "xlsx":
        content = export_xlsx(items)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = export_csv(items)
        media_type = "text/csv; charset=utf-8"
    headers = {"Content-Disposition": f'attachment; filename="transacoes.{format}"'}
    return StreamingResponse(BytesIO(content), media_type=media_type, headers=headers)


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: uuid.UUID, current_user: CurrentUser, db: DatabaseSession
) -> Transaction:
    return _owned_transaction(db, current_user.id, transaction_id)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> Transaction:
    item = _owned_transaction(db, current_user.id, transaction_id)
    changes = payload.model_dump(exclude_unset=True)
    if "amount" in changes and changes["amount"] is not None:
        try:
            changes["amount"] = quantize_money(changes["amount"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    if "occurred_at" in changes and changes["occurred_at"] is not None:
        changes["occurred_at"] = _as_utc(changes["occurred_at"])
    for required in ("description", "amount", "type", "occurred_at"):
        if required in changes and changes[required] is None:
            raise HTTPException(status_code=422, detail=f"{required} não pode ser nulo")
    for field, value in changes.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: uuid.UUID, current_user: CurrentUser, db: DatabaseSession
) -> Response:
    item = _owned_transaction(db, current_user.id, transaction_id)
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
