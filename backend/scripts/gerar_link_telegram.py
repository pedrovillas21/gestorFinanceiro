"""Gera o Deep Link de vínculo de um usuário com o bot do Telegram.

Enquanto a tela "Conectar Telegram" do front-end não existe, este script cumpre o
papel dela: cria o `link_token` do usuário e imprime a URL `t.me/<bot>?start=<token>`.

Uso (com o venv ativado, a partir de backend/):
    python scripts/gerar_link_telegram.py --email voce@exemplo.com \
        --consent-version 2026-08-10 --confirm-privacy-consent
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.privacy import get_privacy_policy  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.telegram_bot import criar_link_token, montar_deep_link  # noqa: E402


def main(email: str, consent_version: str, *, consent_confirmed: bool) -> None:
    if not consent_confirmed:
        raise SystemExit(
            "❌ Confirme explicitamente o aceite com --confirm-privacy-consent"
        )
    if consent_version != settings.PRIVACY_POLICY_VERSION:
        raise SystemExit(
            "❌ A versão informada não é a política de privacidade vigente: "
            f"{settings.PRIVACY_POLICY_VERSION}"
        )
    try:
        get_privacy_policy(consent_version)
    except KeyError as exc:
        raise SystemExit("❌ A política informada não foi publicada") from exc

    db = SessionLocal()
    try:
        usuario = db.scalars(select(User).where(User.email == email)).one_or_none()
        if usuario is None:
            raise SystemExit(f"❌ Nenhum usuário com o e-mail {email}")

        token = criar_link_token(db, usuario.id, consent_version=consent_version)
    finally:
        db.close()

    print(f"Usuário: {email}")
    print(f"Válido por: {settings.TELEGRAM_LINK_TOKEN_TTL_MINUTES} minutos")
    print(f"Token ({len(token)} chars): {token}")
    print("\nCOPIE a linha abaixo inteira (não clique — link quebrado no terminal trunca o token):\n")
    # URL sozinha na linha, sem prefixo, para copiar sem risco de cortar.
    print(montar_deep_link(token))
    print("\nCada execução deste script invalida o link gerado antes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera o Deep Link de vínculo do Telegram.")
    parser.add_argument("--email", required=True, help="E-mail do usuário cadastrado")
    parser.add_argument(
        "--consent-version",
        required=True,
        help="Versão do texto de privacidade aceito pelo usuário",
    )
    parser.add_argument(
        "--confirm-privacy-consent",
        action="store_true",
        help="Confirma que o usuário leu e aceitou exatamente a versão informada",
    )
    args = parser.parse_args()
    main(
        args.email,
        args.consent_version,
        consent_confirmed=args.confirm_privacy_consent,
    )
