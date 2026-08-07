"""Preparação mínima para importar o pacote `app` nos testes.

Os testes aqui são puros (não abrem conexão nem chamam API), mas importar
`app.services.*` carrega `app.core.config.Settings`, que exige um punhado de
variáveis obrigatórias. Os valores de mentira abaixo entram só quando a variável
não existe no ambiente, para a suíte rodar em máquina limpa e em CI sem `.env`.
"""
import os
import sys
from pathlib import Path

# Permite `import app...` rodando pytest de qualquer diretório.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DATABASE_URL", "postgresql://usuario:senha@localhost:5432/teste")
os.environ.setdefault("SUPABASE_URL", "https://exemplo.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "chave-de-teste")
os.environ.setdefault("SECRET_KEY", "segredo-de-teste")
os.environ.setdefault("GEMINI_API_KEY", "chave-de-teste")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "token-de-teste")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "segredo-de-teste")
