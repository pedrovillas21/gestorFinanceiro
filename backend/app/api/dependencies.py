import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import InvalidCredentialsError, decode_access_token
from app.database import get_db
from app.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)
DatabaseSession = Annotated[Session, Depends(get_db)]


def get_client_ip(request: Request) -> str | None:
    """IP de origem, usado pelo bloqueio progressivo do login.

    `X-Forwarded-For` só é lido quando `TRUST_PROXY_HEADERS` está ligado, e a
    escolha importa nos dois sentidos. Confiando no cabeçalho sem proxy na
    frente, qualquer um forja um IP novo a cada tentativa e o escopo de IP deixa
    de existir — pior, dá para forjar o IP de outra pessoa e bloqueá-la de
    propósito. Ignorando o cabeçalho **atrás** de um proxy, todo mundo chega com
    o IP do proxy e um único atacante bloquearia a base inteira.

    Ligue a variável quando houver proxy confiável na frente; deixe desligada
    quando o Uvicorn recebe a conexão direto.
    """
    if settings.TRUST_PROXY_HEADERS:
        encaminhado = request.headers.get("X-Forwarded-For", "")
        # O primeiro da lista é o cliente; os demais são os proxies do caminho.
        primeiro = encaminhado.split(",")[0].strip()
        if primeiro:
            return primeiro
    return request.client.host if request.client else None


ClientIp = Annotated[str | None, Depends(get_client_ip)]


def get_optional_user(
    db: DatabaseSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> User | None:
    """Identifica quem chama, sem exigir que a identificação exista.

    Credencial ausente, malformada ou **vencida** devolve `None` em vez de 401.
    Isso é o que permite a rotas como `/auth/logout` atenderem o cliente que ainda
    manda o access token velho no header: para elas, o access token é um extra, e
    quem autoriza a operação é o refresh token apresentado no corpo.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        user_id: uuid.UUID = decode_access_token(credentials.credentials)
    except InvalidCredentialsError:
        return None
    return db.get(User, user_id)


def get_current_user(user: Annotated[User | None, Depends(get_optional_user)]) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_password_compliant_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Barra toda ação autenticada de quem está com `must_change_password=True`.

    Sem isso, o sinalizador (app/models/user.py, ligado em `login`/scripts
    de criação de conta) era só um convite educado que o front podia mostrar
    ou não — um token roubado, ou alguém se passando pelo dono da conta,
    continuaria com acesso irrestrito aos dados enquanto a pessoa real não
    resolvesse a troca. Este é o ponto único que fecha a porta de verdade:
    todo router que importa `CurrentUser` passa por aqui.

    Exceção: o punhado de rotas que a própria pessoa bloqueada precisa
    alcançar para sair da pendência usa `CurrentUserPendingAllowed`
    (app/api/v1/auth.py: `GET /auth/me`, `POST /auth/change-password`,
    `DELETE /auth/me`) — sem elas, ninguém teria como cumprir a exigência.
    """
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Sua senha não atende aos requisitos de segurança atuais. "
                "Troque a senha em POST /auth/change-password antes de continuar."
            ),
        )
    return user


CurrentUser = Annotated[User, Depends(require_password_compliant_user)]
# Só para as rotas listadas na docstring de `require_password_compliant_user`
# acima — em qualquer outro lugar, isso reabriria o buraco que a dependência
# existe para fechar.
CurrentUserPendingAllowed = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
