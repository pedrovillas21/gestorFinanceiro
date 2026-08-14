"""Bloqueio progressivo do login — a defesa contra força bruta na senha.

A senha é o único segredo de baixa entropia do sistema: o refresh token tem 256
bits e não se adivinha, mas "senha123" se adivinha em milhares de tentativas.
Sem limite, `/auth/login` aceita essas milhares de tentativas por minuto.

**A escada** (por escopo, ver `LoginAttempt`): a cada `FAILURES_PER_LOCK` falhas o
escopo é bloqueado, e cada bloqueio novo dura mais que o anterior —
10 minutos, 3 horas, 24 horas, e daí em diante 24 horas. O atacante paga um custo
que cresce; o usuário que errou a senha duas vezes não paga nada.

**Por que dois escopos:** bloquear só por e-mail deixa passar quem varre muitas
contas com a mesma senha (*credential stuffing*), e bloquear só por IP não segura
um ataque distribuído contra uma conta. O escopo de IP tolera
`IP_TOLERANCE` vezes mais falhas porque um IP pode ser um escritório inteiro
saindo por NAT — o mesmo motivo pelo qual **não existe bloqueio permanente de
IP** aqui: seria punir vizinhos de NAT/CGNAT por um vizinho errado, e um atacante
poderia usá-lo de propósito para derrubar o acesso de terceiros.

O núcleo da decisão é puro (`ThrottleState` e as funções que operam sobre ela),
para caber na suíte sem banco; a persistência é a casca em volta.
"""

import hashlib
import math
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.login_attempt import LoginAttempt


# Falhas toleradas antes de cada bloqueio, no escopo do e-mail.
FAILURES_PER_LOCK = 5
# Duração de cada bloqueio; do último degrau em diante, repete o último.
LOCK_DURATIONS = (timedelta(minutes=10), timedelta(hours=3), timedelta(days=1))
# Sem falha nova por esse tempo, a contagem parcial é esquecida. Não perdoa o
# degrau já conquistado: senão bastaria esperar a janela para tentar de novo em
# blocos de 4 falhas, para sempre.
FAILURE_WINDOW = timedelta(hours=1)
# Sem falha nova por esse tempo, o escopo volta à estaca zero. Precisa ser
# **estritamente maior** que o maior bloqueio: com 1 dia, a escada zerava no
# instante exato em que o bloqueio de 24 h terminava, e o atacante voltava para
# degraus de 10 minutos só por ter esperado a punição passar — o teto nunca valia.
LEVEL_DECAY = timedelta(days=7)
# O escopo de IP tolera mais: um IP pode ser um escritório inteiro atrás de NAT.
IP_TOLERANCE = 4


class LoginBlocked(Exception):
    """Escopo bloqueado. `retry_after` é o que vai no cabeçalho da resposta."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"login bloqueado por mais {retry_after}s")
        self.retry_after = retry_after


@dataclass(frozen=True)
class ThrottleState:
    """Situação de um escopo. Sem banco e sem I/O — só a aritmética da escada."""

    failures: int = 0
    lock_level: int = 0
    last_failure_at: datetime | None = None
    locked_until: datetime | None = None


def lock_duration(lock_level: int) -> timedelta:
    """Duração do bloqueio de número `lock_level` (1 = o primeiro)."""
    degrau = min(max(lock_level, 1), len(LOCK_DURATIONS))
    return LOCK_DURATIONS[degrau - 1]


def seconds_until_release(state: ThrottleState, now: datetime) -> int:
    """Quanto falta do bloqueio, arredondado para cima. 0 quando liberado."""
    if state.locked_until is None or state.locked_until <= now:
        return 0
    return math.ceil((state.locked_until - now).total_seconds())


def forget_stale_failures(state: ThrottleState, now: datetime) -> ThrottleState:
    """Esquece o que já não diz mais nada sobre quem está chamando agora."""
    if state.last_failure_at is None:
        return state
    ocioso = now - state.last_failure_at
    if ocioso >= LEVEL_DECAY:
        return ThrottleState()
    if ocioso >= FAILURE_WINDOW:
        return replace(state, failures=0)
    return state


def register_failure(
    state: ThrottleState, now: datetime, *, failures_per_lock: int = FAILURES_PER_LOCK
) -> ThrottleState:
    """Aplica uma falha à escada e devolve a situação nova."""
    state = forget_stale_failures(state, now)
    failures = state.failures + 1
    if failures < failures_per_lock:
        return replace(state, failures=failures, last_failure_at=now)
    # Fechou um bloqueio: sobe o degrau e recomeça a contagem parcial.
    lock_level = state.lock_level + 1
    return ThrottleState(
        failures=0,
        lock_level=lock_level,
        last_failure_at=now,
        locked_until=now + lock_duration(lock_level),
    )


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


def scope_hash(kind: str, value: str) -> str:
    """SHA-256 de `tipo:valor` — a tabela nunca vê o e-mail nem o IP em claro."""
    return hashlib.sha256(f"{kind}:{value}".encode("utf-8")).hexdigest()


def _scopes(email: str | None, ip: str | None) -> list[tuple[str, str, int]]:
    """Escopos vigiados nesta chamada: (tipo, hash, falhas toleradas)."""
    scopes: list[tuple[str, str, int]] = []
    if email:
        scopes.append(("email", scope_hash("email", email.strip().lower()), FAILURES_PER_LOCK))
    if ip:
        scopes.append(("ip", scope_hash("ip", ip), FAILURES_PER_LOCK * IP_TOLERANCE))
    return scopes


def _to_state(row: LoginAttempt) -> ThrottleState:
    return ThrottleState(
        failures=row.failures,
        lock_level=row.lock_level,
        last_failure_at=row.last_failure_at,
        locked_until=row.locked_until,
    )


def check_login_allowed(db: Session, *, email: str | None, ip: str | None) -> None:
    """Levanta `LoginBlocked` se algum escopo desta chamada está bloqueado.

    Roda **antes** de verificar a senha: o objetivo é não fazer o trabalho, nem
    o bcrypt nem a consulta do usuário.
    """
    now = datetime.now(UTC)
    hashes = [hash_ for _, hash_, _ in _scopes(email, ip)]
    if not hashes:
        return
    rows = db.scalars(
        select(LoginAttempt).where(LoginAttempt.scope_hash.in_(hashes))
    ).all()
    espera = max((seconds_until_release(_to_state(row), now) for row in rows), default=0)
    if espera:
        raise LoginBlocked(espera)


def register_failed_login(db: Session, *, email: str | None, ip: str | None) -> None:
    """Conta a falha nos dois escopos. Não faz commit — quem chama decide."""
    now = datetime.now(UTC)
    for kind, hash_, failures_per_lock in _scopes(email, ip):
        row = db.scalar(
            # Mesmo cuidado da rotação de sessão: a linha é lida para ser
            # reescrita, e duas tentativas simultâneas contariam uma só sem lock.
            select(LoginAttempt).where(LoginAttempt.scope_hash == hash_).with_for_update()
        )
        if row is None:
            # Contadores explícitos: os defaults do model só valem no flush, e
            # até lá os atributos seriam `None` na aritmética da escada.
            row = LoginAttempt(
                id=uuid.uuid4(),
                scope_kind=kind,
                scope_hash=hash_,
                failures=0,
                lock_level=0,
            )
            db.add(row)
            try:
                db.flush()
            except IntegrityError:
                # Outra requisição criou a mesma linha entre o SELECT e o INSERT.
                # Seguro desfazer: neste ponto a transação só tem esta escrita.
                db.rollback()
                row = db.scalar(
                    select(LoginAttempt)
                    .where(LoginAttempt.scope_hash == hash_)
                    .with_for_update()
                )
                if row is None:  # pragma: no cover - a linha existe por definição
                    continue
        state = register_failure(_to_state(row), now, failures_per_lock=failures_per_lock)
        row.failures = state.failures
        row.lock_level = state.lock_level
        row.last_failure_at = state.last_failure_at
        row.locked_until = state.locked_until


def clear_login_failures(db: Session, *, email: str | None, ip: str | None) -> None:
    """Login certo zera o escopo do e-mail. Não faz commit.

    O escopo de IP **não** é zerado: quem tem conta própria poderia usá-la para
    limpar o contador entre rajadas contra as contas dos outros. Ele sai sozinho
    pela janela ociosa de `FAILURE_WINDOW`, que é curta o bastante para não
    incomodar um escritório atrás de NAT.
    """
    if not email:
        return
    db.execute(
        delete(LoginAttempt).where(
            LoginAttempt.scope_hash == scope_hash("email", email.strip().lower())
        )
    )
