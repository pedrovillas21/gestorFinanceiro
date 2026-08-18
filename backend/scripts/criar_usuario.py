"""Cria um usuário direto no banco, enquanto não existe endpoint de cadastro.

Uso (a partir de backend/):
    python scripts/criar_usuario.py --email voce@exemplo.com --nome "Seu Nome"

A senha é pedida de forma interativa (não fica no histórico do shell). Se preferir,
passe --senha explicitamente — útil em scripts, ruim para o histórico.
"""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bcrypt  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.schemas.auth import is_password_compliant  # noqa: E402


def hash_senha(senha: str) -> str:
    """Usa o bcrypt direto — o passlib 1.7.4 não é compatível com bcrypt >= 4.1."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def main(email: str, nome: str | None, senha: str | None) -> None:
    senha = senha or getpass.getpass("Senha do novo usuário: ")
    if len(senha) < 8:
        raise SystemExit("❌ Use uma senha de pelo menos 8 caracteres.")

    # Este script contorna o /auth/register (e a validação de complexidade do
    # RegisterRequest junto). Sem marcar a conta aqui, ela nasceria com
    # `must_change_password=False` (o default do modelo, pensado para o
    # cadastro pela API) mesmo com uma senha fraca — e ninguém pediria a troca.
    compliant = is_password_compliant(senha)
    if not compliant:
        print(
            "⚠️  Essa senha não atende à regra atual (8+ caracteres, 1 minúscula, "
            "1 maiúscula, 1 número, 1 caractere especial). A conta será criada assim "
            "mesmo, mas vai pedir a troca no primeiro login."
        )

    db = SessionLocal()
    try:
        if db.scalars(select(User).where(User.email == email)).one_or_none():
            raise SystemExit(f"❌ Já existe um usuário com o e-mail {email}")

        usuario = User(
            email=email,
            full_name=nome,
            hashed_password=hash_senha(senha),
            must_change_password=not compliant,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
    finally:
        db.close()

    print(f"✅ Usuário criado: {usuario.email} (id {usuario.id})")
    print(f"\nPróximo passo:\n  python scripts/gerar_link_telegram.py --email {usuario.email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cria um usuário no banco.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--nome", default=None, help="Nome completo (opcional)")
    parser.add_argument("--senha", default=None, help="Se omitido, é pedida interativamente")
    args = parser.parse_args()
    main(args.email, args.nome, args.senha)
