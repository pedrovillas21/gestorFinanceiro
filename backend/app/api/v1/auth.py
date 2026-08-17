from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import ClientIp, CurrentUser, DatabaseSession, OptionalUser
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
    SessionResponse,
    TokenResponse,
    UserResponse,
)
from app.services.login_throttle import (
    LoginBlocked,
    check_login_allowed,
    clear_login_failures,
    register_failed_login,
)
from app.services.sessions import (
    RefreshTokenError,
    issue_refresh_token,
    list_active_sessions,
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
        session_id=session.id,
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
    payload: LoginRequest,
    db: DatabaseSession,
    client_ip: ClientIp = None,
    user_agent: UserAgent = None,
) -> TokenResponse:
    """Autentica e abre sessão, com bloqueio progressivo por e-mail e por IP.

    A senha é o único segredo de baixa entropia do sistema — ver
    `app/services/login_throttle.py` para a escada de bloqueio.
    """
    try:
        check_login_allowed(db, email=payload.email, ip=client_ip)
    except LoginBlocked as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc

    user = db.scalar(select(User).where(User.email == payload.email))
    password_hash = user.hashed_password if user is not None else DUMMY_PASSWORD_HASH
    password_matches = verify_password(payload.password, password_hash)
    if user is None or not password_matches:
        register_failed_login(db, email=payload.email, ip=client_ip)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    clear_login_failures(db, email=payload.email, ip=client_ip)
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
    payload: LogoutRequest, db: DatabaseSession, current_user: OptionalUser
) -> MessageResponse:
    """Revoga a sessão informada, ou todas as do usuário.

    Encerrar **uma** sessão não exige access token: apresentar o refresh token já
    é prova de posse, do mesmo jeito que em `/auth/refresh`. Exigir `CurrentUser`
    aqui deixaria quem está com o access token vencido — 30 minutos depois — sem
    como revogar um refresh token que ainda vale por 30 dias; descartá-lo no
    cliente não encerra sessão nenhuma no servidor.

    `all_devices` continua exigindo access token válido: derrubar todas as
    sessões é uma ação sobre a conta inteira, não sobre o token apresentado.

    O access token em uso continua valendo até expirar — ele é stateless e não
    consulta esta tabela. Por isso o `ACCESS_TOKEN_EXPIRE_MINUTES` é curto.
    """
    if payload.all_devices:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Encerrar todas as sessões exige um access token válido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        revoked = revoke_all_for_user(db, current_user.id)
        db.commit()
        return MessageResponse(message=f"{revoked} sessão(ões) encerrada(s)")
    if payload.refresh_token is None:
        raise HTTPException(
            status_code=422,
            detail="Informe o refresh_token ou use all_devices para encerrar tudo",
        )
    # Autenticado, a revogação fica restrita às sessões de quem está chamando;
    # anônimo, quem autoriza é a posse do próprio token apresentado.
    revoke_refresh_token(
        db, payload.refresh_token, current_user.id if current_user else None
    )
    db.commit()
    # Sem distinguir "revoguei" de "não existia": um token de outro usuário não
    # deve ser confirmado como existente por quem está autenticado aqui.
    return MessageResponse(message="Sessão encerrada")


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    current_user: CurrentUser,
    db: DatabaseSession,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[RefreshToken]:
    """Aparelhos com sessão viva, da atividade mais recente para a mais antiga.

    Exige access token válido, e não o refresh token: ver a lista de aparelhos é
    ação sobre a conta inteira, o mesmo critério do `logout` com `all_devices`.

    Lista pura, sem `total` — mesmo contrato de `/investments/assets`: o cliente
    pagina até receber menos itens que o `limit`. Na prática uma conta tem
    poucas sessões vivas, já que cada uma expira em
    `REFRESH_TOKEN_EXPIRE_MINUTES`.

    Não há campo dizendo qual é a sessão atual, porque o access token é stateless
    e não sabe de qual linha nasceu. Quem sabe é o cliente: o `session_id` do
    `TokenResponse` que ele guardou identifica a própria linha nesta lista.
    """
    return list_active_sessions(db, current_user.id, limit=limit, offset=offset)


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
