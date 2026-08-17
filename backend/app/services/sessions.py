"""Emissão, rotação e revogação das sessões de refresh token.

Concentrar isto num serviço mantém `app/api/v1/auth.py` legível e deixa a regra
de reuso — a parte sutil — num lugar só.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.security import generate_refresh_token, hash_refresh_token
from app.models.refresh_token import RefreshToken


class RefreshTokenError(ValueError):
    """Refresh token ausente, expirado, revogado ou já rotacionado."""


MAX_USER_AGENT_LENGTH = 255


def issue_refresh_token(
    db: Session, user_id: uuid.UUID, *, user_agent: str | None = None
) -> tuple[str, RefreshToken]:
    """Cria uma sessão nova. Não faz commit — quem chama decide a transação."""
    token, token_hash, expires_at = generate_refresh_token()
    session = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=(user_agent or None) and user_agent[:MAX_USER_AGENT_LENGTH],
    )
    db.add(session)
    return token, session


def rotate_refresh_token(
    db: Session, token: str, *, user_agent: str | None = None
) -> tuple[str, RefreshToken]:
    """Troca um refresh token válido por um novo, invalidando o apresentado.

    Reapresentar um token já rotacionado significa que duas partes têm o mesmo
    segredo — o legítimo e quem o copiou. Como não dá para saber qual das duas
    está chamando agora, a única resposta segura é derrubar todas as sessões do
    usuário e exigir login novo.
    """
    stored = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(token))
        # `FOR UPDATE` serializa duas chamadas que apresentem o mesmo token. Sem o
        # lock, as duas leem `revoked_at is None`, as duas rotacionam, e a segunda
        # sobrescreve `revoked_at`/`replaced_by_id` da primeira: sobram dois tokens
        # vivos para uma rotação só e a detecção de reuso nunca dispara. Com ele, a
        # segunda espera e enxerga a linha já revogada — que é o sinal esperado.
        .with_for_update()
    )
    if stored is None:
        raise RefreshTokenError("refresh token inválido")

    now = datetime.now(UTC)
    if stored.revoked_at is not None:
        if stored.replaced_by_id is not None:
            revoke_all_for_user(db, stored.user_id)
            db.commit()
            raise RefreshTokenError(
                "refresh token já utilizado; todas as sessões foram encerradas por segurança"
            )
        raise RefreshTokenError("refresh token revogado")
    if stored.expires_at <= now:
        raise RefreshTokenError("refresh token expirado")

    new_token, new_session = issue_refresh_token(
        db, stored.user_id, user_agent=user_agent or stored.user_agent
    )
    # `flush` atribui o id da linha nova antes de referenciá-la em replaced_by_id.
    db.flush()
    stored.revoked_at = now
    stored.last_used_at = now
    stored.replaced_by_id = new_session.id
    return new_token, new_session


def list_active_sessions(
    db: Session, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
) -> list[RefreshToken]:
    """Sessões ainda válidas do usuário, da mais recente para a mais antiga.

    Ativa é a linha não revogada e ainda dentro da validade. As revogadas
    continuam na tabela — a detecção de reuso depende delas — mas não são
    aparelho conectado nenhum e ficariam de fora de qualquer lista útil.

    `created_at` aqui é a **última atividade** da sessão, não o primeiro login:
    cada rotação cria uma linha nova e revoga a anterior. Por isso
    `last_used_at`, que só é carimbado na linha que está sendo revogada, seria
    sempre nulo numa sessão ativa e não entra na resposta.
    """
    return list(
        db.scalars(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(UTC),
            )
            .order_by(RefreshToken.created_at.desc(), RefreshToken.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )


def revoke_refresh_token(
    db: Session, token: str, user_id: uuid.UUID | None = None
) -> bool:
    """Revoga uma sessão específica. Devolve se havia algo ativo para revogar.

    Sem `user_id`, apresentar o token é a própria prova de posse — é assim que o
    logout funciona para quem já está com o access token vencido. Quando o
    chamador está autenticado, o `user_id` restringe a revogação às sessões dele.
    """
    conditions = [RefreshToken.token_hash == hash_refresh_token(token)]
    if user_id is not None:
        conditions.append(RefreshToken.user_id == user_id)
    stored = db.scalar(
        # Mesmo motivo da rotação: ler e escrever a linha sem lock deixa dois
        # caminhos concorrentes decidirem sobre o mesmo estado.
        select(RefreshToken).where(*conditions).with_for_update()
    )
    if stored is None or stored.revoked_at is not None:
        return False
    stored.revoked_at = datetime.now(UTC)
    return True


def revoke_all_for_user(
    db: Session, user_id: uuid.UUID, *, except_id: uuid.UUID | None = None
) -> int:
    """Revoga todas as sessões ativas do usuário. Devolve quantas caíram."""
    conditions = [RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)]
    if except_id is not None:
        conditions.append(RefreshToken.id != except_id)
    result = db.execute(
        update(RefreshToken).where(*conditions).values(revoked_at=datetime.now(UTC))
    )
    return result.rowcount or 0
