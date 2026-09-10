"""RSI mean-reversion reference strategy."""

from collections import deque
from itertools import pairwise

from data.models import Candle
from strategies.base import Action, PortfolioContext, Signal, Strategy


class RsiReversionStrategy(Strategy):
    """Buy oversold instruments and exit held positions when overbought."""

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30,
        overbought: float = 70,
        quantity: int = 1,
        instrument_key: str = "NSE_EQ|TEST",
    ) -> None:
        """Configure RSI thresholds, order size, and monitored instrument."""
        if period < 1 or not 0 <= oversold < overbought <= 100:
            raise ValueError("RSI period and thresholds are invalid")
        if quantity < 1:
            raise ValueError("quantity must be positive")
        if not instrument_key or "|" not in instrument_key:
            raise ValueError("instrument_key must be exchange-qualified")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.quantity = quantity
        self.instrument_key = instrument_key
        self._closes: deque[float] = deque(maxlen=period + 1)

    def reset(self) -> None:
        """Clear price history before a new independent session."""
        self._closes.clear()

    def on_data(self, candle: Candle, context: PortfolioContext) -> list[Signal]:
        """Evaluate RSI and return an entry or exit decision when thresholds trigger."""
        self._closes.append(candle.close)
        if len(self._closes) < self.period + 1:
            return []
        rsi = self._rsi(tuple(self._closes))
        held = context.positions.get(self.instrument_key, 0)
        if rsi < self.oversold and held == 0:
            return [
                Signal(Action.BUY, self.quantity, "RSI oversold", self.instrument_key)
            ]
        if rsi > self.overbought and held > 0:
            return [Signal(Action.SELL, held, "RSI overbought", self.instrument_key)]
        return []

    @staticmethod
    def _rsi(closes: tuple[float, ...]) -> float:
        """Calculate RSI using simple average gains and losses."""
        changes = [
            current - previous
            for previous, current in pairwise(closes)
        ]
        gains = [change for change in changes if change > 0]
        losses = [-change for change in changes if change < 0]
        average_gain = sum(gains) / len(changes)
        average_loss = sum(losses) / len(changes)
        if average_loss == 0:
            return 100.0 if average_gain else 50.0
        return 100 - (100 / (1 + average_gain / average_loss))
