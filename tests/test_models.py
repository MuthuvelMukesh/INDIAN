from datetime import UTC, date, datetime

import pytest

from data.models import Candle, HistoricalQuery


def test_candle_requires_utc_aware_timestamp() -> None:
    candle = Candle(
        timestamp=datetime(2024, 1, 2, tzinfo=UTC),
        open=100.0,
        high=110.0,
        low=95.0,
        close=105.0,
        volume=1000,
    )

    assert candle.timestamp.tzinfo == UTC


def test_candle_rejects_invalid_ohlc_relationship() -> None:
    with pytest.raises(ValueError, match="high must be"):
        Candle(
            timestamp=datetime(2024, 1, 2, tzinfo=UTC),
            open=100.0,
            high=90.0,
            low=95.0,
            close=105.0,
            volume=1000,
        )


def test_query_rejects_reversed_dates() -> None:
    with pytest.raises(ValueError, match="from_date must be"):
        HistoricalQuery("NSE_EQ|INE002A01018", date(2024, 2, 1), date(2024, 1, 1))


def test_query_accepts_five_minute_interval() -> None:
    query = HistoricalQuery(
        "NSE_EQ|INE002A01018",
        date(2024, 1, 1),
        date(2024, 1, 2),
        interval="5minute",
    )

    assert query.interval == "5minute"


def test_query_rejects_unsupported_interval() -> None:
    with pytest.raises(ValueError, match="supported interval"):
        HistoricalQuery(
            "NSE_EQ|INE002A01018",
            date(2024, 1, 1),
            date(2024, 1, 2),
            interval="7minute",
        )
