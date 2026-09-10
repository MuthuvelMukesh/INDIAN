from collections.abc import Sequence
from datetime import UTC, date, datetime

from data.models import Candle, HistoricalQuery
from data.service import MarketDataService


class FakeProvider:
    def __init__(self, candles: list[Candle]) -> None:
        self.candles = candles
        self.calls = 0

    def fetch_candles(self, query: HistoricalQuery) -> list[Candle]:
        self.calls += 1
        return self.candles


class MemoryCache:
    def __init__(self) -> None:
        self.values: dict[HistoricalQuery, list[Candle]] = {}

    def get(self, query: HistoricalQuery) -> list[Candle] | None:
        return self.values.get(query)

    def put(self, query: HistoricalQuery, candles: Sequence[Candle]) -> None:
        self.values[query] = list(candles)


def test_service_uses_cache_on_repeated_request() -> None:
    query = HistoricalQuery("NSE_EQ|ONE", date(2024, 1, 1), date(2024, 1, 2))
    candles = [
        Candle(
            timestamp=datetime(2024, 1, 2, tzinfo=UTC),
            open=100.0,
            high=110.0,
            low=95.0,
            close=105.0,
            volume=1000,
        )
    ]
    provider = FakeProvider(candles)
    service = MarketDataService(provider, MemoryCache())

    assert service.get_candles(query) == candles
    assert service.get_candles(query) == candles
    assert provider.calls == 1
