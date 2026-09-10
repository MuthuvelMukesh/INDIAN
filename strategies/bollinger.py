"""Bollinger squeeze and momentum reference strategy."""

from collections import deque
from statistics import mean, pstdev

from data.models import Candle
from strategies.base import Action, PortfolioContext, Signal, Strategy


class BollingerSqueezeStrategy(Strategy):
    """Trade breakouts after a narrow Bollinger-band squeeze."""

    def __init__(
        self,
        period: int = 20,
        standard_deviations: float = 2.0,
        squeeze_bandwidth: float = 0.05,
        quantity: int = 1,
        instrument_key: str = "NSE_EQ|TEST",
    ) -> None:
        """Configure the rolling bands, squeeze width, and order size."""
        if period < 2 or standard_deviations <= 0 or squeeze_bandwidth <= 0:
            raise ValueError("Bollinger parameters must be positive")
        if quantity < 1:
            raise ValueError("quantity must be positive")
        if not instrument_key or "|" not in instrument_key:
            raise ValueError("instrument_key must be exchange-qualified")
        self.period = period
        self.standard_deviations = standard_deviations
        self.squeeze_bandwidth = squeeze_bandwidth
        self.quantity = quantity
        self.instrument_key = instrument_key
        self._closes: deque[float] = deque(maxlen=period)
        self._previous_squeeze = False

    def reset(self) -> None:
        """Clear rolling prices before a new independent run."""
        self._closes.clear()
        self._previous_squeeze = False

    def on_data(self, candle: Candle, context: PortfolioContext) -> list[Signal]:
        """Evaluate breakouts against the prior completed rolling window."""
        signal: list[Signal] = []
        if len(self._closes) == self.period:
            middle = mean(self._closes)
            spread = self.standard_deviations * pstdev(self._closes)
            upper = middle + spread
            lower = middle - spread
            held = context.positions.get(self.instrument_key, 0)
            if self._previous_squeeze and candle.close > upper and held == 0:
                signal = [
                    Signal(
                        Action.BUY,
                        self.quantity,
                        "Bollinger upside momentum",
                        self.instrument_key,
                    )
                ]
            elif candle.close < lower and held > 0:
                signal = [
                    Signal(
                        Action.SELL,
                        held,
                        "Bollinger downside momentum",
                        self.instrument_key,
                    )
                ]
        self._closes.append(candle.close)
        if len(self._closes) == self.period:
            middle = mean(self._closes)
            spread = self.standard_deviations * pstdev(self._closes)
            bandwidth = (2 * spread) / middle
            self._previous_squeeze = bandwidth <= self.squeeze_bandwidth
        return signal