import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    status: str
    total_rows: int
    imported_rows: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
