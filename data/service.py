"""Cache-first orchestration for historical market data."""

from data.models import Candle, HistoricalQuery
from data.ports import CandleCache, MarketDataProvider


class MarketDataService:
    """Coordinate cache lookup and provider fetches without knowing either
    implementation.
    """

    def __init__(self, provider: MarketDataProvider, cache: CandleCache) -> None:
        """Build a service from swappable provider and cache implementations."""
        self.provider = provider
        self.cache = cache

    def get_candles(self, query: HistoricalQuery) -> list[Candle]:
        """Return candles from cache or fetch and cache them exactly once."""
        cached = self.cache.get(query)
        if cached is not None:
            return cached

        candles = sorted(
            self.provider.fetch_candles(query), key=lambda item: item.timestamp
        )
        self.cache.put(query, candles)
        return list(candles)
