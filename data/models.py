"""Immutable domain objects used by the market-data layer."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import isfinite
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class Candle:
    """Represent one validated OHLCV candle in UTC."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    open_interest: int | None = None

    def __post_init__(self) -> None:
        """Validate the market data invariants required by downstream engines."""
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        normalized_timestamp = self.timestamp.astimezone(timezone.utc)
        object.__setattr__(self, "timestamp", normalized_timestamp)

        prices = (self.open, self.high, self.low, self.close)
        if not all(isfinite(price) and price > 0 for price in prices):
            raise ValueError("OHLC prices must be finite and positive")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be greater than or equal to all OHLC prices")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be less than or equal to all OHLC prices")
        if self.volume < 0:
            raise ValueError("volume must not be negative")
        if self.open_interest is not None and self.open_interest < 0:
            raise ValueError("open_interest must not be negative")


@dataclass(frozen=True, slots=True)
class HistoricalQuery:
    """Identify one inclusive historical candle range."""

    instrument_key: str
    from_date: date
    to_date: date
    interval: str = "1d"

    SUPPORTED_INTERVALS: ClassVar[frozenset[str]] = frozenset(
        {"1d", "1minute", "5minute", "30minute", "day", "week", "month"}
    )

    def __post_init__(self) -> None:
        """Validate the query before it reaches a provider or database."""
        if not self.instrument_key or "|" not in self.instrument_key:
            raise ValueError("instrument_key must contain an exchange-qualified key")
        if self.interval not in self.SUPPORTED_INTERVALS:
            raise ValueError(f"unsupported interval: {self.interval}")
        if self.from_date > self.to_date:
            raise ValueError("from_date must be on or before to_date")