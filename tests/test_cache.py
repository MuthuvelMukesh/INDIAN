from datetime import UTC, date, datetime
from pathlib import Path

from data.cache import SQLiteCandleCache
from data.models import Candle, HistoricalQuery


def test_cache_round_trip(tmp_path: Path) -> None:
    cache = SQLiteCandleCache(tmp_path / "market.sqlite3")
    query = HistoricalQuery("NSE_EQ|INE002A01018", date(2024, 1, 1), date(2024, 1, 2))
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

    assert cache.get(query) is None
    cache.put(query, candles)

    assert cache.get(query) == candles


def test_cache_isolated_by_query(tmp_path: Path) -> None:
    cache = SQLiteCandleCache(tmp_path / "market.sqlite3")
    first_query = HistoricalQuery("NSE_EQ|ONE", date(2024, 1, 1), date(2024, 1, 2))
    second_query = HistoricalQuery("NSE_EQ|TWO", date(2024, 1, 1), date(2024, 1, 2))
    candle = Candle(
        timestamp=datetime(2024, 1, 2, tzinfo=UTC),
        open=100.0,
        high=110.0,
        low=95.0,
        close=105.0,
        volume=1000,
    )

    cache.put(first_query, [candle])

    assert cache.get(second_query) is None
