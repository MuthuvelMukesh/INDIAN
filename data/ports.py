"""Protocols that keep the service independent from providers and storage."""

from collections.abc import Sequence
from typing import Protocol

from data.models import Candle, HistoricalQuery


class MarketDataProvider(Protocol):
    """Provide validated historical candles for a query."""

    def fetch_candles(self, query: HistoricalQuery) -> Sequence[Candle]:
        """Fetch candles from an external or local market-data source."""


class CandleCache(Protocol):
    """Store and retrieve complete historical query results."""

    def get(self, query: HistoricalQuery) -> list[Candle] | None:
        """Return a cached result or ``None`` when the exact range is absent."""

    def put(self, query: HistoricalQuery, candles: Sequence[Candle]) -> None:
        """Persist a result for future exact-range lookups."""
