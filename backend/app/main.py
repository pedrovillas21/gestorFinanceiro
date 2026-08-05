from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from app.api.v1 import api_router

ALEMBIC_INI_PATH = "alembic.ini"


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
    yield


app = FastAPI(title="Gestor Financeiro API", lifespan=lifespan)

app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
