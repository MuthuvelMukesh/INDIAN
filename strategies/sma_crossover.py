"""Simple moving-average crossover reference strategy."""

from collections import deque

from data.models import Candle
from strategies.base import Action, PortfolioContext, Signal, Strategy


class SmaCrossoverStrategy(Strategy):
    """Buy or sell when a short SMA crosses a long SMA."""

    def __init__(
        self,
        short_window: int = 20,
        long_window: int = 50,
        quantity: int = 1,
        instrument_key: str = "NSE_EQ|TEST",
    ) -> None:
        """Configure windows, order size, and the instrument monitored."""
        if short_window < 1 or long_window <= short_window:
            raise ValueError("long_window must be greater than short_window >= 1")
        if quantity < 1:
            raise ValueError("quantity must be positive")
        if not instrument_key or "|" not in instrument_key:
            raise ValueError("instrument_key must be exchange-qualified")
        self.short_window = short_window
        self.long_window = long_window
        self.quantity = quantity
        self.instrument_key = instrument_key
        self._closes: deque[float] = deque(maxlen=long_window + 1)

    def reset(self) -> None:
        """Clear indicator history before starting an independent session."""
        self._closes.clear()

    def on_data(self, candle: Candle, context: PortfolioContext) -> list[Signal]:
        """Evaluate the latest candle and emit only a newly detected crossover."""
        self._closes.append(candle.close)
        if len(self._closes) < self.long_window + 1:
            return []

        previous = list(self._closes)[:-1]
        current = list(self._closes)
        previous_short = self._average(previous[-self.short_window :])
        previous_long = self._average(previous[-self.long_window :])
        current_short = self._average(current[-self.short_window :])
        current_long = self._average(current[-self.long_window :])
        position = context.positions.get(self.instrument_key, 0)

        if previous_short <= previous_long and current_short > current_long:
            return [
                Signal(
                    Action.BUY,
                    self.quantity,
                    "SMA golden crossover",
                    self.instrument_key,
                )
            ]
        if (
            position > 0
            and previous_short >= previous_long
            and current_short < current_long
        ):
            return [
                Signal(
                    Action.SELL,
                    min(position, self.quantity),
                    "SMA death crossover",
                    self.instrument_key,
                )
            ]
        return []

    @staticmethod
    def _average(values: list[float]) -> float:
        """Return the arithmetic mean of a non-empty close window."""
        return sum(values) / len(values)
