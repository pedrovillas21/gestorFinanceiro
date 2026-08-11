"""Atualiza cotações e snapshots de todos os usuários com carteira.

Execute periodicamente pelo agendador da hospedagem, cron ou Task Scheduler:
    python scripts/refresh_market_quotes.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import distinct, select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.investment import InvestmentAsset  # noqa: E402
from app.services.market import MarketProviderError  # noqa: E402
from app.services.quote_refresh import refresh_user_quotes  # noqa: E402


def main() -> int:
    db = SessionLocal()
    failures = 0
    try:
        user_ids = list(db.scalars(select(distinct(InvestmentAsset.user_id))).all())
        for user_id in user_ids:
            try:
                result = refresh_user_quotes(db, user_id)
                print(
                    f"{user_id}: {result.updated} atualizadas; "
                    f"falhas={','.join(result.failed_tickers) or '-'}; "
                    f"coleta={result.collected_at.isoformat()}"
                )
            except MarketProviderError as exc:
                db.rollback()
                failures += 1
                print(f"{user_id}: provedor indisponível ({exc})", file=sys.stderr)
    finally:
        db.close()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
