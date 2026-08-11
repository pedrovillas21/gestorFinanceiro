import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.services.spreadsheets import run_import_worker

ALEMBIC_INI_PATH = str(Path(__file__).resolve().parents[1] / "alembic.ini")


def run_migrations() -> None:
    """Executa automaticamente todas as migrations pendentes do Alembic no Supabase."""
    alembic_cfg = Config(ALEMBIC_INI_PATH)
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Roda as migrations no Supabase na inicialização do servidor
    print("Verificando e aplicando migrations no Supabase...")
    run_migrations()
    print("Migrations aplicadas com sucesso!")
    import_worker_stop = asyncio.Event()
    import_worker = asyncio.create_task(run_import_worker(import_worker_stop))
    try:
        yield
    finally:
        import_worker_stop.set()
        await import_worker


app = FastAPI(title="Gestor Financeiro API", lifespan=lifespan)


def _cors_origins_with_credentials(origins: list[str]) -> list[str]:
    if "*" in origins:
        raise ValueError(
            "CORS_ORIGINS nao pode conter '*' quando credenciais estao habilitadas"
        )
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_with_credentials(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
