"""Opening Range Breakout reference strategy for NSE intraday candles."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from data.models import Candle
from strategies.base import Action, PortfolioContext, Signal, Strategy

IST = ZoneInfo("Asia/Kolkata")
NSE_OPEN = time(9, 15)
NSE_CLOSE = time(15, 30)


class OpeningRangeBreakoutStrategy(Strategy):
    """Trade breaks above or below the first configured minutes of a session."""

    def __init__(
        self,
        opening_minutes: int = 15,
        quantity: int = 1,
        instrument_key: str = "NSE_EQ|TEST",
    ) -> None:
        """Configure the opening range duration and order size."""
        if opening_minutes < 5 or opening_minutes % 5 != 0:
            raise ValueError("opening_minutes must be a positive five-minute multiple")
        if quantity < 1:
            raise ValueError("quantity must be positive")
        if not instrument_key or "|" not in instrument_key:
            raise ValueError("instrument_key must be exchange-qualified")
        self.opening_minutes = opening_minutes
        self.quantity = quantity
        self.instrument_key = instrument_key
        self._session: date | None = None
        self._range_high: float | None = None
        self._range_low: float | None = None

    def reset(self) -> None:
        """Clear the opening range before a new independent run."""
        self._session = None
        self._range_high = None
        self._range_low = None

    def on_data(self, candle: Candle, context: PortfolioContext) -> list[Signal]:
        """Track the opening range and emit post-range breakout signals."""
        local_timestamp = candle.timestamp.astimezone(IST)
        if not NSE_OPEN <= local_timestamp.time() < NSE_CLOSE:
            return []
        session = local_timestamp.date()
        if session != self._session:
            self._session = session
            self._range_high = None
            self._range_low = None

        opening = datetime.combine(session, NSE_OPEN, tzinfo=IST)
        range_end = opening + timedelta(minutes=self.opening_minutes)
        if opening <= local_timestamp < range_end:
            self._range_high = max(self._range_high or candle.high, candle.high)
            self._range_low = min(self._range_low or candle.low, candle.low)
            return []
        if (
            local_timestamp < range_end
            or self._range_high is None
            or self._range_low is None
        ):
            return []

        held = context.positions.get(self.instrument_key, 0)
        if candle.close > self._range_high and held == 0:
            return [
                Signal(
                    Action.BUY,
                    self.quantity,
                    "ORB upside breakout",
                    self.instrument_key,
                )
            ]
        if candle.close < self._range_low and held > 0:
            return [
                Signal(Action.SELL, held, "ORB downside breakout", self.instrument_key)
            ]
        return []
