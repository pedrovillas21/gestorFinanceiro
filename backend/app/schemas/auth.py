import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("e-mail inválido")
        return value

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("senha deve ter no máximo 72 bytes em UTF-8")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    # Opaco e rotacionado: cada POST /auth/refresh devolve um valor novo e
    # invalida o anterior. Guardar sempre o último recebido.
    refresh_token: str
    refresh_expires_at: datetime
    # Identifica a linha desta sessão em GET /auth/sessions, para o cliente
    # marcar "este dispositivo" na lista. Não é credencial: nenhuma rota
    # autoriza nada a partir dele. Rotaciona junto com o refresh token — cada
    # rotação cria uma linha nova —, então precisa ser guardado do mesmo jeito.
    session_id: uuid.UUID
    user: UserResponse


class SessionResponse(BaseModel):
    """Uma sessão ativa, do jeito que o usuário a reconhece na tela.

    Sem `last_used_at`: ele só é carimbado na linha revogada pela rotação, então
    numa sessão ativa seria sempre nulo. `created_at` é que faz esse papel aqui.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_agent: str | None
    created_at: datetime
    expires_at: datetime


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=512)


class LogoutRequest(BaseModel):
    # Ausente quando o cliente perdeu o refresh token e só quer derrubar tudo —
    # caso que exige access token válido, ao contrário do logout de sessão única.
    refresh_token: str | None = Field(default=None, max_length=512)
    all_devices: bool = False


class ProfileUpdate(BaseModel):
    """Só o nome. Trocar e-mail muda a identidade de login e é decisão à parte."""

    full_name: str | None = Field(default=None, max_length=255)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)
    # Padrão verdadeiro: quem troca a senha normalmente quer derrubar os outros
    # aparelhos. A sessão que fez a troca é substituída pelo par devolvido aqui.
    revoke_other_sessions: bool = True

    @field_validator("new_password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("senha deve ter no máximo 72 bytes em UTF-8")
        return value


class MessageResponse(BaseModel):
    message: str
