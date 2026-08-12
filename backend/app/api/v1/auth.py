from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    ProfileUpdate,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.sessions import (
    RefreshTokenError,
    issue_refresh_token,
    revoke_all_for_user,
    revoke_refresh_token,
    rotate_refresh_token,
)


router = APIRouter(prefix="/auth", tags=["auth"])


# Rótulo do dispositivo na lista de sessões. Opcional de propósito: um cliente
# sem User-Agent (script, curl) precisa conseguir logar do mesmo jeito.
UserAgent = Annotated[str | None, Header(alias="User-Agent")]


def _token_response(user: User, refresh_token: str, session: RefreshToken) -> TokenResponse:
    access_token, expires_at = create_access_token(user.id)
    return TokenResponse(
        access_token=access_token,
        expires_at=expires_at,
        refresh_token=refresh_token,
        refresh_expires_at=session.expires_at,
        user=user,
    )


def _start_session(
    db: DatabaseSession, user: User, user_agent: str | None = None
) -> TokenResponse:
    refresh_token, session = issue_refresh_token(db, user.id, user_agent=user_agent)
    db.commit()
    db.refresh(session)
    return _token_response(user, refresh_token, session)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest, db: DatabaseSession, user_agent: UserAgent = None
) -> TokenResponse:
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="E-mail já cadastrado") from exc
    db.refresh(user)
    return _start_session(db, user, user_agent)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest, db: DatabaseSession, user_agent: UserAgent = None
) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    password_hash = user.hashed_password if user is not None else DUMMY_PASSWORD_HASH
    password_matches = verify_password(payload.password, password_hash)
    if user is None or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _start_session(db, user, user_agent)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest, db: DatabaseSession, user_agent: UserAgent = None
) -> TokenResponse:
    """Troca o refresh token por um par novo; o apresentado deixa de valer.

    Rota pública de propósito: ela existe justamente para o caso do access token
    já ter expirado, quando o `Authorization` não passaria mais.
    """
    try:
        new_token, session = rotate_refresh_token(
            db, payload.refresh_token, user_agent=user_agent
        )
    except RefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado"
        )
    db.commit()
    db.refresh(session)
    return _token_response(user, new_token, session)


@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: LogoutRequest, current_user: CurrentUser, db: DatabaseSession
) -> MessageResponse:
    """Revoga a sessão informada, ou todas as do usuário.

    O access token em uso continua valendo até expirar — ele é stateless e não
    consulta esta tabela. Por isso o `ACCESS_TOKEN_EXPIRE_MINUTES` é curto.
    """
    if payload.all_devices:
        revoked = revoke_all_for_user(db, current_user.id)
        db.commit()
        return MessageResponse(message=f"{revoked} sessão(ões) encerrada(s)")
    if payload.refresh_token is None:
        raise HTTPException(
            status_code=422,
            detail="Informe o refresh_token ou use all_devices para encerrar tudo",
        )
    revoke_refresh_token(db, payload.refresh_token, current_user.id)
    db.commit()
    # Sem distinguir "revoguei" de "não existia": um token de outro usuário não
    # deve ser confirmado como existente por quem está autenticado aqui.
    return MessageResponse(message="Sessão encerrada")


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdate, current_user: CurrentUser, db: DatabaseSession
) -> User:
    changes = payload.model_dump(exclude_unset=True)
    if "full_name" in changes:
        name = (changes["full_name"] or "").strip()
        # Nome em branco e nome ausente viram a mesma coisa: sem nome.
        current_user.full_name = name or None
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
    user_agent: UserAgent = None,
) -> TokenResponse:
    """Troca a senha e devolve um par novo, para quem trocou seguir logado.

    Com `revoke_other_sessions` (padrão), toda sessão anterior cai — inclusive a
    que fez esta chamada, substituída pelo par devolvido aqui. Os access tokens
    já emitidos continuam válidos até `ACCESS_TOKEN_EXPIRE_MINUTES` passar.
    """
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha atual incorreta")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=422, detail="A nova senha deve ser diferente da atual")
    try:
        current_user.hashed_password = hash_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if payload.revoke_other_sessions:
        revoke_all_for_user(db, current_user.id)
    db.commit()
    return _start_session(db, current_user, user_agent)


@router.delete("/me", response_model=MessageResponse)
def delete_account(current_user: CurrentUser, db: DatabaseSession) -> MessageResponse:
    """Exerce o direito de exclusão; FKs com CASCADE removem todos os dados pessoais."""
    db.delete(current_user)
    db.commit()
    return MessageResponse(message="Conta e dados associados excluídos")
