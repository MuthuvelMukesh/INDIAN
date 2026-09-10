"""Read-only Upstox API v2 historical-candle adapter."""

from collections.abc import Sequence
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from data.models import Candle, HistoricalQuery


class UpstoxApiError(RuntimeError):
    """Indicate an HTTP or payload error returned by Upstox."""


class UpstoxCandleProvider:
    """Fetch daily candles from Upstox without exposing trading operations."""

    def __init__(
        self,
        access_token: str,
        transport: httpx.BaseTransport | None = None,
        base_url: str = "https://api.upstox.com",
    ) -> None:
        """Configure a read-only client; an injected transport supports offline tests."""
        if not access_token:
            raise ValueError("UPSTOX_ACCESS_TOKEN is required for market data")
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            transport=transport,
            timeout=30.0,
        )

    def fetch_candles(self, query: HistoricalQuery) -> list[Candle]:
        """Fetch and validate daily historical candles for one instrument and range."""
        path = (
            f"/v2/historical-candle/{quote(query.instrument_key, safe='')}/"
            f"{query.interval}/{query.to_date.isoformat()}/{query.from_date.isoformat()}"
        )
        response = self._client.get(path)
        if response.is_error:
            raise UpstoxApiError(f"Upstox historical candle request failed: HTTP {response.status_code}")

        try:
            payload = response.json()
            raw_candles = payload["data"]["candles"]
            candles = [_parse_candle(raw_candle) for raw_candle in raw_candles]
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise UpstoxApiError("Upstox returned an invalid historical candle payload") from error
        return sorted(candles, key=lambda candle: candle.timestamp)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()


def _parse_candle(raw_candle: Sequence[object]) -> Candle:
    """Map one Upstox candle array into the validated domain model."""
    if len(raw_candle) < 6:
        raise ValueError("candle payload must contain timestamp and OHLCV values")
    timestamp = datetime.fromisoformat(str(raw_candle[0]).replace("Z", "+00:00"))
    return Candle(
        timestamp=timestamp.astimezone(timezone.utc),
        open=float(raw_candle[1]),
        high=float(raw_candle[2]),
        low=float(raw_candle[3]),
        close=float(raw_candle[4]),
        volume=int(raw_candle[5]),
        open_interest=int(raw_candle[6]) if len(raw_candle) > 6 and raw_candle[6] is not None else None,
    )