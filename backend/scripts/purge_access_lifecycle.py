"""Limpa as tabelas de ciclo de acesso: sessões expiradas e contadores de login.

Nenhuma das duas tem limpeza no caminho quente, de propósito. `refresh_tokens`
ganha uma linha por login **e outra por rotação** — um usuário ativo 8 horas por
dia rotaciona ~16 vezes/dia, algo como 6 mil linhas por usuário por ano —, e
`login_attempts` ganha uma linha por escopo que falhou. Nada disso é apagado
sozinho.

Por que aqui e não um `DELETE` oportunista dentro de `rotate_refresh_token`:
apagar durante a rotação põe custo de escrita — e um lock a mais — no caminho
que todo cliente percorre a cada 30 minutos, para resolver um problema que não
tem pressa nenhuma. Um trabalho agendado faz a mesma limpeza fora do horário de
pico, em lotes, e pode ser interrompido sem deixar nada pela metade.

Execute pelo agendador da hospedagem, cron ou Task Scheduler — diariamente é
mais que suficiente:

    python scripts/purge_access_lifecycle.py            # apaga
    python scripts/purge_access_lifecycle.py --dry-run  # só conta

    # cron, todo dia às 4h:
    0 4 * * * cd /app/backend && python scripts/purge_access_lifecycle.py
"""

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, or_, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.login_attempt import LoginAttempt  # noqa: E402
from app.models.refresh_token import RefreshToken  # noqa: E402
from app.services.login_throttle import LEVEL_DECAY  # noqa: E402


# Carência depois do vencimento. A linha vencida já não autentica nada, mas
# guardá-la um tempo preserva a trilha de quem rotacionou o quê — inclusive a
# evidência de reuso, que é o sinal de token vazado.
DEFAULT_RETENTION_DAYS = 30
# Lotes: um DELETE único de centenas de milhares de linhas segura a tabela por
# minutos e cresce o WAL de uma vez só.
DEFAULT_BATCH_SIZE = 5_000


def purge_refresh_tokens(
    db: Session, *, cutoff: datetime, batch_size: int, dry_run: bool
) -> int:
    """Apaga sessões vencidas há mais tempo que a carência."""
    vencidas = RefreshToken.expires_at < cutoff
    if dry_run:
        return db.scalar(select(func.count()).select_from(RefreshToken).where(vencidas)) or 0

    apagadas = 0
    while True:
        lote = select(RefreshToken.id).where(vencidas).limit(batch_size)
        resultado = db.execute(delete(RefreshToken).where(RefreshToken.id.in_(lote)))
        db.commit()
        apagadas += resultado.rowcount or 0
        if not resultado.rowcount:
            return apagadas


def purge_login_attempts(db: Session, *, batch_size: int, dry_run: bool) -> int:
    """Apaga contadores que já não bloqueiam nem contam nada.

    O corte é o mesmo `LEVEL_DECAY` do serviço: passado esse tempo sem falha
    nova, a escada volta à estaca zero — a linha remanescente é só lixo.
    """
    agora = datetime.now(UTC)
    ocioso = agora - LEVEL_DECAY
    inerte = (
        or_(
            LoginAttempt.last_failure_at < ocioso,
            LoginAttempt.last_failure_at.is_(None),
        )
        # Nunca apagar bloqueio em vigor: apagar é liberar.
        & or_(LoginAttempt.locked_until.is_(None), LoginAttempt.locked_until < agora)
        & (LoginAttempt.created_at < ocioso)
    )
    if dry_run:
        return db.scalar(select(func.count()).select_from(LoginAttempt).where(inerte)) or 0

    apagadas = 0
    while True:
        lote = select(LoginAttempt.id).where(inerte).limit(batch_size)
        resultado = db.execute(delete(LoginAttempt).where(LoginAttempt.id.in_(lote)))
        db.commit()
        apagadas += resultado.rowcount or 0
        if not resultado.rowcount:
            return apagadas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=f"carência após o vencimento da sessão (padrão: {DEFAULT_RETENTION_DAYS})",
    )
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--dry-run", action="store_true", help="apenas conta o que seria apagado"
    )
    args = parser.parse_args()

    if args.days < 0 or args.batch < 1:
        print("--days não pode ser negativo e --batch precisa ser >= 1", file=sys.stderr)
        return 2

    cutoff = datetime.now(UTC) - timedelta(days=args.days)
    db = SessionLocal()
    try:
        sessoes = purge_refresh_tokens(
            db, cutoff=cutoff, batch_size=args.batch, dry_run=args.dry_run
        )
        tentativas = purge_login_attempts(db, batch_size=args.batch, dry_run=args.dry_run)
    finally:
        db.close()

    verbo = "seriam apagadas" if args.dry_run else "apagadas"
    print(f"refresh_tokens: {sessoes} {verbo} (vencidas antes de {cutoff.isoformat()})")
    print(f"login_attempts: {tentativas} {verbo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
