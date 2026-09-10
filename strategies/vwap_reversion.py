"""Intraday VWAP mean-reversion reference strategy."""

from datetime import date, time
from zoneinfo import ZoneInfo

from data.models import Candle
from strategies.base import Action, PortfolioContext, Signal, Strategy

IST = ZoneInfo("Asia/Kolkata")
NSE_OPEN = time(9, 15)
NSE_CLOSE = time(15, 30)


class VwapReversionStrategy(Strategy):
    """Trade deviations from the running session VWAP."""

    def __init__(
        self,
        deviation: float = 0.01,
        quantity: int = 1,
        instrument_key: str = "NSE_EQ|TEST",
    ) -> None:
        """Configure the fractional VWAP deviation and order size."""
        if not 0 < deviation < 1:
            raise ValueError("deviation must be greater than zero and below one")
        if quantity < 1:
            raise ValueError("quantity must be positive")
        if not instrument_key or "|" not in instrument_key:
            raise ValueError("instrument_key must be exchange-qualified")
        self.deviation = deviation
        self.quantity = quantity
        self.instrument_key = instrument_key
        self._session: date | None = None
        self._volume = 0
        self._price_volume = 0.0

    def reset(self) -> None:
        """Clear the current session accumulator before a new run."""
        self._session = None
        self._volume = 0
        self._price_volume = 0.0

    def on_data(self, candle: Candle, context: PortfolioContext) -> list[Signal]:
        """Update session VWAP and emit a reversion entry or exit signal."""
        session = candle.timestamp.astimezone(IST).date()
        local_time = candle.timestamp.astimezone(IST).time()
        if not NSE_OPEN <= local_time < NSE_CLOSE:
            return []
        if session != self._session:
            self._session = session
            self._volume = 0
            self._price_volume = 0.0

        self._volume += candle.volume
        self._price_volume += candle.close * candle.volume
        if self._volume == 0:
            return []
        vwap = self._price_volume / self._volume
        held = context.positions.get(self.instrument_key, 0)
        lower_band = vwap * (1 - self.deviation)
        upper_band = vwap * (1 + self.deviation)
        if candle.close <= lower_band and held == 0:
            return [
                Signal(Action.BUY, self.quantity, "VWAP oversold", self.instrument_key)
            ]
        if candle.close >= upper_band and held > 0:
            return [Signal(Action.SELL, held, "VWAP overbought", self.instrument_key)]
        return []
