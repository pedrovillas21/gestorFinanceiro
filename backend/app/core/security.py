"""Hash de senha e emissão/validação dos tokens da API web."""

from datetime import UTC, datetime, timedelta
import hashlib
import secrets
import uuid

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.core.config import settings


class InvalidCredentialsError(ValueError):
    pass


MAX_BCRYPT_PASSWORD_BYTES = 72
# Valid bcrypt hash used only to keep login cost stable when the user is absent.
DUMMY_PASSWORD_HASH = "$2b$12$C6UzMDM.H6dfI/f/IKcEe.yrnoaOHB5d4tsM7VZ42CHrv0ZNlqrAu"


def _password_bytes(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError("senha deve ter no máximo 72 bytes em UTF-8")
    return encoded


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: uuid.UUID) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": datetime.now(UTC),
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM), expires_at


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise InvalidCredentialsError("tipo de token inválido")
        return uuid.UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidCredentialsError("token inválido ou expirado") from exc


# 32 bytes de urandom; `token_urlsafe` devolve ~43 caracteres seguros em URL.
REFRESH_TOKEN_BYTES = 32


def generate_refresh_token() -> tuple[str, str, datetime]:
    """Devolve (valor entregue ao cliente, hash guardado no banco, expiração).

    O valor em claro nunca é persistido: só o cliente fica com ele.
    """
    token = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    return token, hash_refresh_token(token), expires_at


def hash_refresh_token(token: str) -> str:
    """SHA-256 em hexadecimal — cabe no `String(64)` e é indexável."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
