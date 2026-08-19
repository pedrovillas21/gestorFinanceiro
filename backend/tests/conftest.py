"""Isola a suíte de qualquer credencial real antes de importar o pacote `app`.

Os testes aqui são puros (não abrem conexão nem chamam API), mas importar
`app.services.*` carrega `app.core.config.Settings`, que monta o engine do
SQLAlchemy e lê chaves de API. Se alguma dessas variáveis chegasse com valor de
verdade, um teste com defeito passaria a apontar para o banco de produção, gastar
quota do Gemini ou mandar mensagem pelo bot real.

Por isso o ambiente é **sobrescrito**, não completado: `os.environ[...] = ...` em
vez de `setdefault`. `setdefault` preserva o que já existe no shell do
desenvolvedor ou nos secrets do CI — exatamente o caso perigoso. E, como toda
variável de `Settings` passa a existir no ambiente, o `.env` real do diretório
`backend/` não contribui com nada (variável de ambiente vence o arquivo).
"""
import os
import sys
from pathlib import Path

# Permite `import app...` rodando pytest de qualquer diretório.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Marca presente em todo segredo de teste — a checagem no fim do arquivo confirma
# que foi ela que o `Settings` enxergou, e não um valor herdado do ambiente.
SENTINELA = "teste-nao-usar-em-producao"

# Porta 1 em localhost: nada escuta ali, então uma conexão acidental falha na hora
# em vez de acertar um Postgres de desenvolvimento rodando na 5432.
AMBIENTE_DE_TESTE = {
    "DATABASE_URL": f"postgresql://usuario:{SENTINELA}@localhost:1/banco_de_teste",
    "SUPABASE_URL": "https://exemplo.invalid",
    "SUPABASE_KEY": SENTINELA,
    "SECRET_KEY": f"{SENTINELA}-jwt-chave-com-tamanho-seguro",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "REFRESH_TOKEN_EXPIRE_MINUTES": "43200",
    "GEMINI_API_KEY": SENTINELA,
    "GEMINI_MODEL_NIVEL_1": "modelo-de-teste-1",
    "GEMINI_MODEL_NIVEL_2": "modelo-de-teste-2",
    "GEMINI_MODEL_NIVEL_3": "modelo-de-teste-3",
    "GEMINI_MODEL_NIVEL_4": "modelo-de-teste-4",
    "TELEGRAM_BOT_TOKEN": SENTINELA,
    "TELEGRAM_WEBHOOK_SECRET": SENTINELA,
    "TELEGRAM_BOT_USERNAME": "bot_de_teste",
    "TELEGRAM_WEBHOOK_URL": "https://exemplo.invalid/webhook",
    "TELEGRAM_LINK_TOKEN_TTL_MINUTES": "30",
    "PRIVACY_POLICY_VERSION": "2026-08-10",
    "TRUST_PROXY_HEADERS": "false",
    "WEB_APP_URL": "https://exemplo.invalid",
    "CORS_ORIGINS": "https://exemplo.invalid",
    "BRAPI_TOKEN": SENTINELA,
    "MARKET_HTTP_TIMEOUT_SECONDS": "10",
    "QUOTE_STALE_AFTER_MINUTES": "60",
}

for nome, valor in AMBIENTE_DE_TESTE.items():
    os.environ[nome] = valor

from app.core.config import Settings, settings  # noqa: E402  (só depois do ambiente montado)

# Campo novo em `Settings` sem valor de teste voltaria a ser lido do `.env` real:
# falhar aqui é mais barato que descobrir isso quando o teste tocar o banco.
_sem_valor_de_teste = set(Settings.model_fields) - set(AMBIENTE_DE_TESTE)
if _sem_valor_de_teste:
    raise RuntimeError(
        "Settings ganhou campos sem valor de teste: "
        f"{', '.join(sorted(_sem_valor_de_teste))}. "
        "Acrescente cada um em AMBIENTE_DE_TESTE (backend/tests/conftest.py)."
    )

# Confirma que o que o `Settings` carregou foi mesmo o ambiente de teste.
if SENTINELA not in settings.DATABASE_URL or settings.GEMINI_API_KEY != SENTINELA:
    raise RuntimeError(
        "A configuração carregada não é a de teste — abortando antes que algum "
        "teste alcance um serviço real."
    )
