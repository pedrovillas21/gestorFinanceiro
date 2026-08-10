from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import httpx

from app.core.config import settings


BRAPI_QUOTE_URL = "https://brapi.dev/api/v2/stocks/quote"


class MarketProviderError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FetchedQuote:
    ticker: str
    price: Decimal
    currency: str
    collected_at: datetime


def _parse_datetime(value: object) -> datetime:
    if not value:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


async def fetch_brapi_quotes(tickers: list[str]) -> dict[str, FetchedQuote]:
    """Fetch quotes keyed by stripped, upper-case ticker symbols."""
    symbols = sorted({ticker.strip().upper() for ticker in tickers if ticker.strip()})
    if not symbols:
        return {}
    headers = {}
    if settings.BRAPI_TOKEN:
        headers["Authorization"] = f"Bearer {settings.BRAPI_TOKEN}"
    timeout = httpx.Timeout(settings.MARKET_HTTP_TIMEOUT_SECONDS)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                BRAPI_QUOTE_URL,
                params={"symbols": ",".join(symbols)},
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise MarketProviderError("não foi possível consultar a brapi") from exc

    result: dict[str, FetchedQuote] = {}
    try:
        requested_at = _parse_datetime(payload.get("requestedAt"))
        for item in payload.get("results", []):
            data = item.get("data") or {}
            ticker = str(
                item.get("symbol") or item.get("requestedSymbol") or ""
            ).strip().upper()
            raw_price = data.get("regularMarketPrice")
            if not ticker or raw_price is None:
                continue
            price = Decimal(str(raw_price))
            if not price.is_finite():
                raise InvalidOperation
            result[ticker] = FetchedQuote(
                ticker=ticker,
                price=price,
                currency=str(data.get("currency") or "BRL").upper(),
                collected_at=_parse_datetime(data.get("regularMarketTime"))
                if data.get("regularMarketTime")
                else requested_at,
            )
    except (AttributeError, InvalidOperation, TypeError, ValueError) as exc:
        raise MarketProviderError("a brapi retornou uma cotacao invalida") from exc
    return result
